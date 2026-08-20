#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: dupes.py
# Purpose: Database-backed duplicate tree explorer API
#
# Description:
# Read-only routes over the MySQL `files` table (populated by CLI and
# workbench runs alike) that power the Dup Trees screen: drill into any
# directory, see per-child duplicate ratios and where the duplicates'
# originals live, and page through the actual file pairs.
#
# A broad prefix aggregates millions of rows, which can take minutes
# while a pipeline run has the database busy — so /tree never blocks:
# it starts the aggregation on a worker thread and returns
# {status: "computing"} until the result is ready, and the front end
# polls. Everything is a single scan per prefix, cached in-process.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.2.0
# Last Modified: 2026-08-18 by Tim Canady
#
# Revision History:
# - 0.2.0 (2026-08-18): Async compute + poll (no long-held HTTP requests);
#   single-scan aggregation; cheap LENGTH() dir detection — Tim Canady
# - 0.1.0 (2026-08-17): Initial duplicate tree explorer API — Tim Canady
###################################################################

from __future__ import annotations

import logging
import threading
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/db/duplicates", tags=["duplicates-db"])

DEFAULT_PREFIX = "/Volumes/home"
CACHE_TTL_SECONDS = 15 * 60
MAX_CHILDREN = 300

# prefix -> {"status": "computing"|"ready"|"error",
#            "data": ..., "error": ..., "started": ts, "ts": ts}
_tree_cache: dict = {}
_cache_lock = threading.Lock()

# The headline totals need an aggregate over every row in `files`. On a
# multi-million-row table that takes minutes, so it gets exactly the same
# treatment as the tree: computed on a worker thread, cached, and polled
# by the client. Running it inline made the banner hang the request.
_status_cache: dict = {}


def _session():
    """A DB session, or a 503 that says why there isn't one."""
    try:
        from core.db import Session
        return Session()
    except Exception as e:
        raise HTTPException(503, f"Database unavailable: {e}")


def _like_escape(prefix: str) -> str:
    """Escape LIKE metacharacters so a path is matched literally."""
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _norm_prefix(prefix: str) -> str:
    prefix = (prefix or DEFAULT_PREFIX).strip()
    if not prefix.startswith("/"):
        raise HTTPException(400, "Prefix must be an absolute path.")
    return prefix.rstrip("/") or "/"


# The tree an original lives in: its top-level directory under
# /Volumes/home when it is there, otherwise its first two components.
_ORIG_ROOT_SQL = f"""
    CASE WHEN duplicate_of LIKE '{DEFAULT_PREFIX}/%'
         THEN SUBSTRING_INDEX(SUBSTRING(duplicate_of, {len(DEFAULT_PREFIX) + 2}), '/', 1)
         ELSE SUBSTRING_INDEX(duplicate_of, '/', 3)
    END
"""


def _compute_tree(prefix: str) -> dict:
    """One scan of everything under `prefix`, grouped by (child, original
    tree). Folded in Python into per-child stats + containment targets."""
    seg_start = len(prefix) + 2          # 1-indexed, past the trailing '/'
    like = _like_escape(prefix) + "/%"
    started = time.time()

    from core.db import Session
    with Session() as s:
        s.execute(text("SET SESSION max_execution_time = 3000000"))
        rows = s.execute(text(f"""
            SELECT SUBSTRING_INDEX(SUBSTRING(path, {seg_start}), '/', 1) AS seg,
                   CASE WHEN is_duplicate = 1 THEN {_ORIG_ROOT_SQL} END AS orig_root,
                   COUNT(*) n,
                   SUM(is_duplicate = 1) dups,
                   SUM(size) bytes,
                   SUM(CASE WHEN is_duplicate = 1 THEN size ELSE 0 END) dup_bytes,
                   SUM(metadata_only = 1) unhashed,
                   MIN(LENGTH(path)) min_len
            FROM files
            WHERE path LIKE :like
            GROUP BY seg, orig_root"""),
            {"like": like}).all()

    # Fold (seg, orig_root) groups into per-child rows.
    children: dict = {}
    for r in rows:
        c = children.setdefault(r.seg, {
            "name": r.seg, "files": 0, "duplicates": 0, "bytes": 0,
            "duplicate_bytes": 0, "unhashed": 0, "min_len": 10 ** 9,
            "targets": {},
        })
        c["files"] += int(r.n or 0)
        c["duplicates"] += int(r.dups or 0)
        c["bytes"] += int(r.bytes or 0)
        c["duplicate_bytes"] += int(r.dup_bytes or 0)
        c["unhashed"] += int(r.unhashed or 0)
        c["min_len"] = min(c["min_len"], int(r.min_len or 10 ** 9))
        if r.orig_root:
            c["targets"][r.orig_root] = c["targets"].get(r.orig_root, 0) + int(r.dups or 0)

    out = []
    for c in sorted(children.values(),
                    key=lambda c: (-c["duplicates"], -c["files"]))[:MAX_CHILDREN]:
        dups = c["duplicates"]
        targets = sorted(c["targets"].items(), key=lambda t: -t[1])[:3]
        out.append({
            "name": c["name"],
            # The shortest path in the group being longer than
            # "<prefix>/<name>" means every entry is deeper — a directory.
            "is_dir": c["min_len"] > len(prefix) + 1 + len(c["name"]),
            "files": c["files"],
            "duplicates": dups,
            "dup_pct": round(100.0 * dups / c["files"], 1) if c["files"] else 0.0,
            "bytes": c["bytes"],
            "duplicate_bytes": c["duplicate_bytes"],
            "unhashed": c["unhashed"],
            "originals_in": [
                {"tree": t, "files": n,
                 "pct": round(100.0 * n / dups, 1) if dups else 0.0}
                for t, n in targets],
        })

    return {
        "prefix": prefix,
        "children": out,
        "truncated": len(children) > MAX_CHILDREN,
        "computed_at": time.time(),
        "elapsed_seconds": round(time.time() - started, 1),
    }


def _compute_in_thread(prefix: str):
    try:
        data = _compute_tree(prefix)
        with _cache_lock:
            _tree_cache[prefix] = {"status": "ready", "data": data,
                                   "ts": time.time()}
    except Exception as e:
        logger.warning("tree aggregation failed for %s: %s", prefix, e)
        with _cache_lock:
            _tree_cache[prefix] = {"status": "error", "error": str(e),
                                   "ts": time.time()}


def _compute_status() -> dict:
    """Totals across the whole table. Minutes on a large database."""
    started = time.time()
    with _session() as s:
        s.execute(text("SET SESSION max_execution_time = 3000000"))
        row = s.execute(text("""
            SELECT COUNT(*) n,
                   SUM(is_duplicate = 1) dups,
                   SUM(CASE WHEN is_duplicate = 1 THEN size ELSE 0 END) dup_bytes
            FROM files""")).one()
    return {
        "files": int(row.n or 0),
        "duplicates": int(row.dups or 0),
        "duplicate_bytes": int(row.dup_bytes or 0),
        "default_prefix": DEFAULT_PREFIX,
        "elapsed_seconds": round(time.time() - started, 1),
    }


def _compute_status_in_thread():
    try:
        data = _compute_status()
        with _cache_lock:
            _status_cache.update({"status": "ready", "data": data,
                                  "ts": time.time()})
    except Exception as e:
        logger.warning("status aggregation failed: %s", e)
        with _cache_lock:
            _status_cache.update({"status": "error", "error": str(e),
                                  "ts": time.time()})


@router.get("/status")
def api_status(refresh: bool = False):
    """Headline numbers for the screen's banner.

    Never blocks. A cache miss starts the aggregation on a worker thread
    and returns {status: "computing"}; the client polls until it flips to
    ready, exactly as it does for the tree.
    """
    with _cache_lock:
        entry = dict(_status_cache) if _status_cache else None
        if entry:
            fresh = time.time() - entry["ts"] < CACHE_TTL_SECONDS
            if entry["status"] == "computing":
                return {"status": "computing",
                        "elapsed_seconds": round(time.time() - entry["started"], 1)}
            if entry["status"] == "ready" and fresh and not refresh:
                return {"status": "ready", **entry["data"]}
            if entry["status"] == "error" and fresh and not refresh:
                raise HTTPException(500, f"Aggregation failed: {entry['error']}")
        _status_cache.clear()
        _status_cache.update({"status": "computing", "started": time.time(),
                              "ts": time.time()})

    threading.Thread(target=_compute_status_in_thread, daemon=True,
                     name="dup-status").start()
    return {"status": "computing", "elapsed_seconds": 0}


@router.get("/tree")
def api_tree(prefix: str = DEFAULT_PREFIX, refresh: bool = False):
    """Children of `prefix` with duplicate stats — or {status: computing}.

    Never blocks: a cache miss starts the aggregation on a worker thread
    and the client polls until status flips to ready.
    """
    prefix = _norm_prefix(prefix)

    with _cache_lock:
        entry = _tree_cache.get(prefix)
        if entry:
            fresh = time.time() - entry["ts"] < CACHE_TTL_SECONDS
            if entry["status"] == "computing":
                return {"status": "computing",
                        "elapsed_seconds": round(time.time() - entry["started"], 1)}
            if entry["status"] == "ready" and fresh and not refresh:
                return {"status": "ready", **entry["data"]}
            if entry["status"] == "error" and fresh and not refresh:
                raise HTTPException(500, f"Aggregation failed: {entry['error']}")
        # (Re)start the computation.
        _tree_cache[prefix] = {"status": "computing", "started": time.time(),
                               "ts": time.time()}

    threading.Thread(target=_compute_in_thread, args=(prefix,),
                     daemon=True, name=f"dup-tree:{prefix}").start()
    return {"status": "computing", "elapsed_seconds": 0}


class ResolutionRequest(BaseModel):
    hash: str
    keep: list          # paths to keep — at least one


@router.get("/resolutions")
def api_resolutions():
    """All resolved duplicate groups: {hash: [kept paths]}."""
    from core.db import get_duplicate_resolutions
    return {"resolutions": get_duplicate_resolutions() or {}}


@router.post("/resolutions")
def api_save_resolution(req: ResolutionRequest):
    """Record which copies of a group to keep; the group stops appearing
    in reviews and future runs settle it automatically."""
    if not req.keep:
        raise HTTPException(400, "Choose at least one copy to keep.")
    if not req.hash or req.hash == "METADATA_ONLY":
        raise HTTPException(400, "Not a resolvable duplicate group.")
    from core.db import save_duplicate_resolution
    if not save_duplicate_resolution(req.hash, req.keep):
        raise HTTPException(503, "Could not save — database unavailable.")
    return {"resolved": req.hash, "kept": req.keep}


@router.delete("/resolutions/{hash_val}")
def api_delete_resolution(hash_val: str):
    """Forget a decision so the group is reviewable again."""
    from core.db import delete_duplicate_resolution
    if not delete_duplicate_resolution(hash_val):
        raise HTTPException(404, "No resolution recorded for that group.")
    return {"unresolved": hash_val}


@router.get("/files")
def api_files(prefix: str = DEFAULT_PREFIX, after: Optional[str] = None,
              limit: int = 100, dups_only: bool = True):
    """Files under `prefix`, keyset-paginated by path (`after` = last path
    of the previous page). Keyset rather than OFFSET so deep pages stay
    fast over millions of rows."""
    prefix = _norm_prefix(prefix)
    limit = max(1, min(limit, 500))
    like = _like_escape(prefix) + "/%"

    dup_clause = "AND is_duplicate = 1" if dups_only else ""
    after_clause = "AND path > :after" if after else ""

    with _session() as s:
        rows = s.execute(text(f"""
            SELECT path, size, is_duplicate, duplicate_of, metadata_only
            FROM files
            WHERE path LIKE :like {dup_clause} {after_clause}
            ORDER BY path
            LIMIT {limit + 1}"""),
            {"like": like, **({"after": after} if after else {})}).all()

    page = rows[:limit]
    return {
        "prefix": prefix,
        "rows": [{
            "path": r.path,
            "size": int(r.size or 0),
            "is_duplicate": bool(r.is_duplicate),
            "duplicate_of": r.duplicate_of,
            "unhashed": bool(r.metadata_only),
        } for r in page],
        "next_after": page[-1].path if len(rows) > limit else None,
    }


# ----------------------------- deletion -----------------------------
#
# The only destructive surface in the project. Three rules hold:
#   - files are moved to the Trash, never unlinked;
#   - a group must be resolved first, and its kept copies are never
#     touched, so a group can never lose its last copy;
#   - protected companions (utils/protected.py) are excluded even when
#     hash-identical, because the media beside them still needs them.

class DeleteRequest(BaseModel):
    confirm: str                 # must equal "TRASH THEM"
    hashes: Optional[list] = None   # None = every resolved group


def _deletion_candidates(only: Optional[list] = None) -> dict:
    """What a delete would trash, without touching anything.

    Drives both the confirmation screen and the deletion itself, so the
    numbers shown are the numbers acted on.

    One query for every group, not one per group: `files.hash` is
    unindexed, so a per-group lookup is a full table scan each time —
    148 resolved groups took the endpoint past two minutes before this
    was batched. See migration 004, which indexes the column.
    """
    from core.db import get_duplicate_resolutions
    from utils.protected import protection_reason

    resolutions = get_duplicate_resolutions() or {}
    if only:
        wanted = set(only)
        resolutions = {h: k for h, k in resolutions.items() if h in wanted}
    empty = {"groups": 0, "files": 0, "bytes": 0, "paths": [],
             "protected": [], "missing": 0}
    if not resolutions:
        return empty

    # Fetch every group's members in one pass.
    by_hash: dict = {}
    hashes = list(resolutions)
    with _session() as s:
        s.execute(text("SET SESSION max_execution_time = 900000"))
        for i in range(0, len(hashes), 500):
            chunk = hashes[i:i + 500]
            placeholders = ", ".join(f":h{n}" for n in range(len(chunk)))
            params = {f"h{n}": h for n, h in enumerate(chunk)}
            rows = s.execute(text(
                f"SELECT hash, path, size FROM files WHERE hash IN ({placeholders})"),
                params).all()
            for r in rows:
                by_hash.setdefault(r.hash, []).append((r.path, int(r.size or 0)))

    delete_paths, protected, total_bytes, groups = [], [], 0, 0

    # Zero-byte files all share this hash, so a single resolved group can
    # hold six figures of them. Deleting them frees nothing and breaks
    # marker files, so they are refused here as well as in the detector —
    # a resolution saved before that rule existed must not act on them.
    EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    skipped_empty = 0

    for hash_val, kept in resolutions.items():
        if hash_val == EMPTY_SHA256:
            skipped_empty += len(by_hash.get(hash_val, []))
            continue
        members = by_hash.get(hash_val, [])
        if len(members) < 2:
            continue
        kept_set = {str(k) for k in kept}
        # Never empty a group: if not one kept copy is actually present in
        # this hash group, leave the whole group alone.
        if not any(path in kept_set for path, _ in members):
            continue

        candidates = [(path, size) for path, size in members if path not in kept_set]
        if not candidates:
            continue
        groups += 1
        for path, size in candidates:
            reason = protection_reason(path)
            if reason:
                protected.append({"path": path, "reason": reason})
                continue
            delete_paths.append(path)
            total_bytes += size

    # Existence is checked in parallel: these live on a network volume,
    # where a serial stat per file dominates everything else.
    missing = 0
    if delete_paths:
        from core import parallel
        present = list(parallel.map_stage(
            parallel.SCAN, os.path.exists, delete_paths))
        missing = sum(1 for ok in present if not ok)
        delete_paths = [p for p, ok in zip(delete_paths, present) if ok]
        # total_bytes still counts only what we will actually try to move
        total_bytes = 0
        sizes = {path: size for members in by_hash.values() for path, size in members}
        for path in delete_paths:
            total_bytes += sizes.get(path, 0)

    return {"groups": groups, "files": len(delete_paths), "bytes": total_bytes,
            "paths": delete_paths, "protected": protected, "missing": missing,
            "skipped_empty": skipped_empty}


@router.get("/pending")
def api_pending():
    """Final-confirmation summary: what would be trashed, and what won't."""
    summary = _deletion_candidates()
    from core.db import count_trashed
    return {
        "groups": summary["groups"],
        "files": summary["files"],
        "bytes": summary["bytes"],
        "protected": summary["protected"][:200],
        "protected_total": len(summary["protected"]),
        "missing": summary["missing"],
        "skipped_empty": summary.get("skipped_empty", 0),
        "already_trashed": count_trashed(),
        "sample": summary["paths"][:20],
    }


@router.post("/delete")
def api_delete(req: DeleteRequest):
    """Move the non-kept copies of resolved groups to the Trash."""
    if req.confirm != "TRASH THEM":
        raise HTTPException(400, 'Confirmation phrase required: "TRASH THEM".')

    from core.db import is_db_down, log_deletions_bulk
    if is_db_down():
        raise HTTPException(
            409, "The database is unreachable, so deletions could not be "
                 "logged — and an unlogged deletion cannot be undone. "
                 "Restore it and retry.")

    summary = _deletion_candidates(req.hashes)
    if not summary["paths"]:
        return {"trashed": 0, "failed": 0, "bytes": 0,
                "message": "Nothing to trash — no resolved group had a "
                           "deletable copy."}

    from datetime import datetime
    from utils.trash import trash_many

    batch_at = datetime.utcnow()
    results = trash_many(summary["paths"])
    ok = [r for r in results if r.ok]
    failed = [{"path": r.path, "error": r.error} for r in results if not r.ok]

    logged = log_deletions_bulk([(r.path, r.trashed_to) for r in ok], batch_at)
    if ok and not logged:
        logger.error("Trashed %d files but logged 0 — undo will not see them", len(ok))

    return {
        "trashed": len(ok),
        "failed": len(failed),
        "failures": failed[:20],
        "bytes": summary["bytes"],
        "logged": logged,
        "protected_skipped": len(summary["protected"]),
        "batch_at": batch_at.isoformat(),
    }


@router.get("/undo")
def api_undo_preview():
    """What the undo button would put back."""
    from core.db import last_deletion_batch
    batch = last_deletion_batch()
    if not batch:
        return {"available": False}
    return {
        "available": True,
        "at": batch["at"].isoformat() if batch["at"] else None,
        "files": len(batch["items"]),
        "sample": [i["original"] for i in batch["items"][:10]],
    }


@router.post("/undo")
def api_undo():
    """Put the most recent trashed batch back where it came from."""
    from core.db import last_deletion_batch, mark_deletions_restored
    from utils.trash import restore

    batch = last_deletion_batch()
    if not batch:
        raise HTTPException(404, "Nothing to undo.")

    restored_ids, failures = [], []
    for item in batch["items"]:
        problem = restore(item["trash"], item["original"])
        if problem is None:
            restored_ids.append(item["operation_id"])
        else:
            failures.append({"path": item["original"], "error": problem})

    mark_deletions_restored(restored_ids)
    return {"restored": len(restored_ids), "failed": len(failures),
            "failures": failures[:20]}
