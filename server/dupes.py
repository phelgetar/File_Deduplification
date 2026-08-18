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
import time
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
