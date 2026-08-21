#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: import_cli_runs.py
# Purpose: Bring historical --dry-run-log previews into the Jobs tab
#
# Description:
# Command-line runs have recorded proper job artifacts since
# core/artifacts.py landed, but everything before that only left a
# dry_run_preview_*.json behind: a JSON array whose every element is
# the repr() of a (FileInfo, PosixPath) tuple. Unreadable to the web
# UI, and awkward even to grep.
#
# This converts them. The repr is parsed through the AST rather than
# eval() — the files are ours, but a 5 GB file is not something to
# hand to the interpreter — and written out as the same plan.jsonl
# and job.json the server already understands.
#
# Streamed line by line throughout: the largest preview here is 5.5 GB
# and 6,992,105 rows, and json.load() on it would want tens of GB.
#
# IMPORTANT: an imported plan is a HISTORICAL RECORD, not a proposal.
# It says what the rules decided on the day it ran, and the rules have
# changed since — the oldest of these still plans files into
# Desktop/Desktop/Desktop/. Runs older than the newest rule file are
# flagged stale so the UI can say so.
#
# Author: Tim Canady
# Created: 2026-08-21
#
# Version: 1.0.0
# Last Modified: 2026-08-21 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-21): Initial CLI-run importer — Tim Canady
###################################################################

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterator, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.artifacts import JOBS_DIR  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Where previews were written, over the years.
SEARCH_GLOBS = ("dry_run_preview_*.json", "dry_run_preview_*.txt",
                "output/dry_run_preview_*.json", "output/dry_run_preview_*.txt")

# Files that decide where anything goes. A preview older than the newest
# of these was produced by a ruleset that no longer exists.
RULE_FILES = ("config/rules.yaml", "config/semantic_paths.yaml",
              "config/image_ai_categories.yaml", "config/folder_mapping.py",
              "core/organizer.py", "core/classifier.py", "core/projects.py")

# Only these may appear in a preview's repr. Anything else means the file
# is not what we think it is, and parsing stops rather than guessing.
ALLOWED_CALLS = {"FileInfo", "PosixPath", "WindowsPath", "PurePosixPath", "Path"}


def rules_changed_at() -> float:
    return max((REPO / f).stat().st_mtime
               for f in RULE_FILES if (REPO / f).exists())


def _value(node):
    """Evaluate one AST node, allowing only the constructors we expect."""
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name not in ALLOWED_CALLS:
            raise ValueError(f"unexpected call: {name}")
        if name != "FileInfo":
            return _value(node.args[0])          # PosixPath('x') -> 'x'
        return {kw.arg: _value(kw.value) for kw in node.keywords}
    if isinstance(node, ast.Tuple):
        return [_value(e) for e in node.elts]
    return ast.literal_eval(node)


def parse_entry(text: str):
    return _value(ast.parse(text.strip(), mode="eval").body)


def iter_records(path: Path) -> Iterator[Tuple[dict, str]]:
    """Yield (file_info_fields, destination) for every row in a preview.

    Handles both shapes: a JSON array with one quoted repr per line (the
    common case), and a bare text file with one repr per line.
    """
    with path.open("r", errors="replace") as fh:
        for raw in fh:
            line = raw.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            if line.startswith('"'):
                try:
                    line = json.loads(line)
                except json.JSONDecodeError:
                    continue
            if not line.startswith("("):
                continue
            try:
                parsed = parse_entry(line)
            except (SyntaxError, ValueError, MemoryError):
                continue
            if isinstance(parsed, list) and len(parsed) == 2:
                info, dest = parsed
                if isinstance(info, dict):
                    yield info, str(dest)


def job_id_for(path: Path) -> str:
    """Stable id, so re-importing updates in place instead of duplicating."""
    return hashlib.sha256(f"cli-import:{path.name}".encode()).hexdigest()[:12]


def common_root(paths) -> Optional[str]:
    try:
        return os.path.commonpath(list(paths)) or None
    except (ValueError, TypeError):
        return None


def import_one(preview: Path, dry_run: bool = False,
               max_rows: Optional[int] = None) -> Optional[dict]:
    job_id = job_id_for(preview)
    directory = JOBS_DIR / job_id
    started = preview.stat().st_mtime
    stale = started < rules_changed_at()

    if not dry_run:
        directory.mkdir(parents=True, exist_ok=True)

    rows = dupes = 0
    sources, dests, categories = [], [], {}
    plan_fh = None
    dup_fh = None
    try:
        if not dry_run:
            plan_fh = (directory / "plan.jsonl").open("w")
            dup_fh = (directory / "duplicates.jsonl").open("w")

        for info, dest in iter_records(preview):
            src = info.get("path")
            if not src:
                continue
            rows += 1
            category = info.get("type")
            categories[category] = categories.get(category, 0) + 1
            # Sample the first rows only — commonpath over seven million
            # strings costs more than it tells us.
            if rows <= 2000:
                sources.append(src)
                dests.append(dest)
            record = {
                "src": src, "dest": dest, "type": category,
                "size": info.get("size"), "hash": info.get("hash"),
                "is_duplicate": bool(info.get("is_duplicate")),
                "duplicate_of": info.get("original_path"),
            }
            if plan_fh:
                plan_fh.write(json.dumps(record) + "\n")
            if record["is_duplicate"]:
                dupes += 1
                if dup_fh:
                    dup_fh.write(json.dumps(record) + "\n")
            if max_rows and rows >= max_rows:
                break
    finally:
        for fh in (plan_fh, dup_fh):
            if fh:
                fh.close()

    if rows == 0:
        if not dry_run:
            for name in ("plan.jsonl", "duplicates.jsonl"):
                (directory / name).unlink(missing_ok=True)
            try:
                directory.rmdir()
            except OSError:
                pass
        return None

    summary = {
        "id": job_id, "preview": preview.name, "rows": rows,
        "duplicates": dupes, "source": common_root(sources),
        "base_dir": common_root(dests), "started": started, "stale": stale,
        "categories": dict(sorted(categories.items(),
                                  key=lambda kv: -kv[1])[:8]),
    }
    if dry_run:
        return summary

    manifest = {
        "id": job_id,
        "kind": "scan",
        "config": {
            "source": summary["source"],
            "base_dir": summary["base_dir"],
            "use_db": None,
            "max_files": None,
            "file_types": None,
            "via": "cli-import",
            "imported_from": preview.name,
            # The reason this flag exists: an imported plan says what the
            # rules decided that day. Acting on a stale one re-creates
            # bugs that have since been fixed.
            "ruleset": "historical" if stale else "current",
        },
        "created_at": started,
        "imported_at": time.time(),
    }
    (directory / "job.json").write_text(json.dumps(manifest, indent=2))
    (directory / "result.json").write_text(json.dumps({
        "status": "imported",
        "planned": rows,
        "duplicates": dupes,
        "note": ("Imported from a command-line dry-run preview. This is a "
                 "record of what the rules decided on "
                 f"{time.strftime('%Y-%m-%d', time.localtime(started))}"
                 + (", under a ruleset that has since changed."
                    if stale else ".")),
    }, indent=2))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import historical CLI dry-run previews into the Jobs tab.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be imported without writing")
    ap.add_argument("--max-rows", type=int,
                    help="Stop each preview after N rows (for a quick look)")
    ap.add_argument("--max-size-mb", type=float,
                    help="Skip previews larger than this, so the multi-GB "
                         "ones can be left for a deliberate run")
    ap.add_argument("--only", help="Substring: import just the matching previews")
    args = ap.parse_args()

    previews = sorted({p for pattern in SEARCH_GLOBS for p in REPO.glob(pattern)})
    if args.only:
        previews = [p for p in previews if args.only in p.name]
    if not previews:
        print("No dry_run_preview_* files found.")
        return

    print(f"{'DRY RUN — ' if args.dry_run else ''}"
          f"{len(previews)} preview file(s)\n")
    imported = skipped = 0
    total_rows = 0
    for preview in previews:
        mb = preview.stat().st_size / 1e6
        if args.max_size_mb and mb > args.max_size_mb:
            print(f"  skip   {preview.name:<40} {mb:8.1f} MB  "
                  f"(over --max-size-mb)")
            skipped += 1
            continue
        started = time.time()
        summary = import_one(preview, dry_run=args.dry_run,
                             max_rows=args.max_rows)
        if summary is None:
            print(f"  empty  {preview.name:<40} {mb:8.1f} MB")
            skipped += 1
            continue
        imported += 1
        total_rows += summary["rows"]
        flag = "historical" if summary["stale"] else "current   "
        print(f"  ok     {preview.name:<40} {summary['rows']:>9,} rows  "
              f"{flag}  {time.time() - started:5.1f}s")
        print(f"         id={summary['id']}  source={summary['source']}")

    print(f"\n  imported {imported}, skipped {skipped}, "
          f"{total_rows:,} plan rows total")
    if not args.dry_run and imported:
        print(f"  Restart the server (or reload the Jobs tab) to see them.")


if __name__ == "__main__":
    main()
