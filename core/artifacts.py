#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: artifacts.py
# Purpose: The on-disk record of a run, written by both entry points
#
# Description:
# A run produces a plan, a set of duplicate groups and a result summary.
# Those were written only by the web server, so a command-line run left
# nothing the UI could show — and --dry-run-log wrote str(tuple), a
# Python repr that cannot be read back.
#
# Both entry points now write the same four files here:
#
#   job.json         what the run was for
#   plan.jsonl       one JSON object per planned operation
#   duplicates.jsonl duplicate groups, largest reclaim first
#   result.json      the summary counters
#
# The Jobs tab rebuilds itself from this directory, so a terminal run
# appears there alongside the others and its plan stays reviewable and
# executable afterwards.
#
# Author: Tim Canady
# Created: 2026-08-20
#
# Version: 0.1.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-20): Extracted from server/jobs.py so the CLI records runs too — Tim Canady
###################################################################

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

JOBS_DIR = Path(__file__).resolve().parent.parent / ".workbench" / "jobs"
MANIFEST = "job.json"


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def write_manifest(job_id: str, kind: str, config: dict,
                   created_at: Optional[float] = None) -> None:
    """Record what the run was for. Written at start, so an interrupted
    run still leaves evidence it existed."""
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        (directory / MANIFEST).write_text(json.dumps({
            "id": job_id, "kind": kind, "config": config,
            "created_at": created_at or time.time(),
        }, indent=2, default=str))
    except OSError as e:
        # Losing the manifest costs history, not correctness.
        logger.warning("Could not write job manifest for %s: %s", job_id, e)


def write_plan(directory: Path, plan) -> None:
    """One JSON object per operation, so the UI can page a large plan
    without holding it in memory."""
    with (directory / "plan.jsonl").open("w", encoding="utf-8") as fh:
        for file_info, dest in plan:
            fh.write(json.dumps({
                "src": str(file_info.path),
                "dest": str(dest),
                "type": file_info.type,
                "size": file_info.size,
                "hash": file_info.hash,
                "is_duplicate": bool(file_info.is_duplicate),
                "duplicate_of": str(file_info.original_path) if file_info.original_path else None,
            }) + "\n")


def write_duplicates(directory: Path, plan) -> None:
    """Duplicate groups by hash, largest reclaimable space first.

    Derived from the plan rather than recomputed, so the review screen
    and the execution always agree about which files are in a group.
    """
    groups: Dict[str, dict] = {}
    for file_info, _dest in plan:
        if not file_info.hash or file_info.hash == "METADATA_ONLY":
            continue
        g = groups.setdefault(file_info.hash, {
            "hash": file_info.hash, "size": file_info.size or 0, "paths": [],
        })
        g["paths"].append({"path": str(file_info.path),
                           "is_duplicate": bool(file_info.is_duplicate)})

    rows = []
    for g in groups.values():
        if len(g["paths"]) < 2:
            continue
        g["count"] = len(g["paths"])
        # Keeping one copy is the point, so the reclaim is n-1 copies.
        g["reclaimable"] = g["size"] * (g["count"] - 1)
        rows.append(g)
    rows.sort(key=lambda r: -r["reclaimable"])

    with (directory / "duplicates.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def write_result(directory: Path, result_dict: dict) -> None:
    (directory / "result.json").write_text(json.dumps(result_dict, indent=2))


def record_run(job_id: str, kind: str, config: dict, result, plan) -> Path:
    """Write every artifact for a finished run. Returns its directory."""
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    write_plan(directory, plan)
    write_duplicates(directory, plan)
    write_result(directory, result.as_dict() if hasattr(result, "as_dict") else dict(result))
    return directory
