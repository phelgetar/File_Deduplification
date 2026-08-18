#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: app.py
# Purpose: FastAPI backend for the workbench UI
#
# Description:
# A thin JSON/SSE layer over core/pipeline.py. It holds no pipeline
# logic of its own — jobs run in child processes (server/jobs.py) and
# every route either starts one, reports on one, or pages the artifacts
# one produced.
#
# Everything that could touch the filesystem goes through
# server/security.py, and file moves are only ever performed by an
# explicit execute call against an already-reviewed plan.
#
# Run it:
#   ./.venv/bin/python -m server.app            # first free port from 8000
#   ./.venv/bin/python -m server.app --port 9000
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Initial API — Tim Canady
###################################################################

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import parallel
from server import security
from server.jobs import TERMINAL, registry

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="File Workbench")


# ------------------------------ models ------------------------------


class ScanRequest(BaseModel):
    source: str
    base_dir: str
    file_types: Optional[str] = None
    max_files: Optional[int] = None
    metadata_only_size: Optional[str] = None
    use_db: bool = False
    skip_duplicates: bool = False
    llm_classify: bool = False
    cloud_classify: bool = False
    cloud_cost_limit_usd: float = 1.00
    cloud_model: Optional[str] = None
    ai_tagging: bool = False
    analyze_images: bool = False
    hash_workers: Optional[int] = None


class ExecuteRequest(BaseModel):
    confirm: str                      # must equal the literal "COPY FILES"
    selected: Optional[List[str]] = None   # None = the whole plan
    write_metadata: bool = False


# ------------------------------ helpers -----------------------------


def _read_jsonl(path: Path, offset: int, limit: int) -> dict:
    """Page a JSONL artifact without loading the whole file."""
    if not path.exists():
        return {"rows": [], "total": 0, "offset": offset}
    rows, total = [], 0
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            total += 1
            if offset <= i < offset + limit:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return {"rows": rows, "total": total, "offset": offset, "limit": limit}


def _job_or_404(job_id: str):
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(404, "No such job.")
    return job


# ------------------------------- routes ------------------------------


@app.get("/", response_class=HTMLResponse)
def home():
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise HTTPException(500, "web/index.html is missing.")
    return index.read_text(encoding="utf-8")


@app.get("/api/system")
def api_system():
    """Hardware and per-stage parallelism, for the Run screen."""
    hw = parallel.hardware()
    return {
        "hardware": {
            "logical_cpus": hw.logical, "performance_cores": hw.performance,
            "efficiency_cores": hw.efficiency, "memory_gb": hw.memory_gb,
        },
        "stages": [
            {"stage": s, "kind": parallel.policy(s).kind,
             "workers": parallel.policy(s).workers,
             "reason": parallel.policy(s).reason}
            for s in (parallel.SCAN, parallel.HASH, parallel.CLASSIFY,
                      parallel.TAG, parallel.EXTRACT, parallel.IMAGE_META,
                      parallel.LLM, parallel.VISION_GPU)
        ],
        "ollama_parallel": parallel.ollama_parallel(),
    }


@app.get("/api/file-types")
def api_file_types():
    try:
        from utils.file_type_filter import FileTypeFilter
        return {"groups": sorted(FileTypeFilter().groups.keys())}
    except Exception as e:
        logger.debug("file type groups unavailable: %s", e)
        return {"groups": []}


@app.get("/api/jobs")
def api_jobs():
    return {"jobs": registry.list()}


@app.post("/api/jobs")
def api_start_scan(req: ScanRequest):
    try:
        source = security.safe_scan_root(req.source)
        base_dir = security.safe_output_dir(req.base_dir)
    except security.PathRejected as e:
        raise HTTPException(400, str(e))

    allowed_extensions = None
    if req.file_types:
        from utils.file_type_filter import FileTypeFilter, parse_file_types_arg
        groups = parse_file_types_arg(req.file_types)
        if not groups:
            raise HTTPException(400, f"Unknown file type group: {req.file_types}")
        allowed_extensions = FileTypeFilter().get_extensions(groups)

    metadata_only_size = None
    if req.metadata_only_size:
        from core.main import parse_size
        try:
            metadata_only_size = parse_size(req.metadata_only_size)
        except ValueError as e:
            raise HTTPException(400, str(e))

    config = {
        "source": str(source),
        "base_dir": str(base_dir),
        "max_files": req.max_files,
        # A set is not JSON, but this dict is pickled to the child, and
        # PipelineConfig wants a set — so keep it as one.
        "allowed_extensions": allowed_extensions,
        "metadata_only_size": metadata_only_size,
        "use_db": req.use_db,
        "skip_duplicates": req.skip_duplicates,
        "llm_classify": req.llm_classify,
        "cloud_classify": req.cloud_classify,
        "cloud_cost_limit_usd": req.cloud_cost_limit_usd,
        "cloud_model": req.cloud_model,
        "ai_tagging": req.ai_tagging,
        "analyze_images": req.analyze_images,
        "hash_workers": req.hash_workers,
        # Never set from the API. Moving files requires the separate,
        # explicitly-confirmed execute call below.
        "execute": False,
    }
    job = registry.start("scan", config)
    return job.summary()


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    return _job_or_404(job_id).summary()


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel(job_id: str):
    job = _job_or_404(job_id)
    if not registry.cancel(job):
        raise HTTPException(409, f"Job is already {job.status}.")
    return {"cancelling": True}


@app.get("/api/jobs/{job_id}/stream")
async def api_stream(job_id: str, after: int = 0):
    """Server-sent events: replay from `after`, then follow live.

    Reconnect-safe — the client passes the last seq it saw, so a dropped
    connection resumes without a gap and without duplicates.
    """
    job = _job_or_404(job_id)

    async def gen():
        last = after
        idle = 0
        while True:
            events = registry.events_since(job, last)
            for event in events:
                last = event["seq"]
                yield f"data: {json.dumps(event)}\n\n"
                idle = 0
            if not events:
                idle += 1
                if job.status in TERMINAL:
                    # One last drain, then close: the terminal event may
                    # have landed between the check and the read.
                    for event in registry.events_since(job, last):
                        last = event["seq"]
                        yield f"data: {json.dumps(event)}\n\n"
                    yield f"data: {json.dumps({'type': 'stream_end', 'status': job.status})}\n\n"
                    return
                if idle % 30 == 0:
                    yield ": keepalive\n\n"   # keep proxies from timing out
            await asyncio.sleep(0.2)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/api/jobs/{job_id}/plan")
def api_plan(job_id: str, offset: int = 0, limit: int = 200,
             category: Optional[str] = None, q: Optional[str] = None):
    job = _job_or_404(job_id)
    page = _read_jsonl(job.dir / "plan.jsonl", offset, limit)
    # Filtering is applied to the page rather than the file: the common
    # case is browsing, and re-scanning a million-line file per keystroke
    # would be worse than a slightly coarse filter.
    if category or q:
        page["rows"] = [
            r for r in page["rows"]
            if (not category or r.get("type") == category)
            and (not q or q.lower() in r["src"].lower())
        ]
    return page


@app.get("/api/jobs/{job_id}/duplicates")
def api_duplicates(job_id: str, offset: int = 0, limit: int = 100):
    job = _job_or_404(job_id)
    page = _read_jsonl(job.dir / "duplicates.jsonl", offset, limit)
    page["total_reclaimable"] = sum(r.get("reclaimable", 0) for r in page["rows"])
    return page


@app.post("/api/jobs/{job_id}/execute")
def api_execute(job_id: str, req: ExecuteRequest):
    """Apply a reviewed plan — the only route that writes files.

    core/executor.py copies (shutil.copy2) rather than moves, so the
    source tree is left untouched and the operation is recoverable by
    deleting the destination. It still needs confirmation: a large plan
    can consume a lot of disk.
    """
    job = _job_or_404(job_id)

    if req.confirm != "COPY FILES":
        raise HTTPException(400, 'Confirmation phrase required: "COPY FILES".')
    if job.status != "done":
        raise HTTPException(409, f"Job is {job.status}; only a completed scan "
                                 f"can be executed.")

    plan_path = job.dir / "plan.jsonl"
    if not plan_path.exists():
        raise HTTPException(404, "This job has no plan to execute.")

    # Same refusal the CLI has always made: without operation logging the
    # moves are unauditable, so don't start.
    if job.config.get("use_db"):
        try:
            from core.db import is_db_down
            if is_db_down():
                raise HTTPException(
                    409, "The database is unreachable, so the operations could "
                         "not be logged. Restore it and retry — cached hashes "
                         "make the re-run fast.")
        except ImportError:
            pass

    config = dict(job.config)
    config["write_metadata"] = req.write_metadata
    child = registry.start("execute", {
        "pipeline": config,
        "plan_path": str(plan_path),
        "selected": req.selected,
    })
    return child.summary()


@app.get("/api/jobs/{job_id}/file")
def api_file(job_id: str, path: str):
    """Preview a file — only if it appears in this job's plan."""
    job = _job_or_404(job_id)
    resolved = security.allowed_file(job.dir, path)
    if resolved is None:
        raise HTTPException(403, "That file is not part of this job's plan.")
    if not resolved.exists():
        raise HTTPException(404, "File no longer exists on disk.")
    return FileResponse(resolved)


@app.post("/api/jobs/{job_id}/reveal")
def api_reveal(job_id: str, path: str):
    """Reveal a file in Finder. Allowlisted the same way as preview."""
    job = _job_or_404(job_id)
    resolved = security.allowed_file(job.dir, path)
    if resolved is None:
        raise HTTPException(403, "That file is not part of this job's plan.")
    subprocess.run(["open", "-R", str(resolved)], capture_output=True, timeout=5)
    return {"revealed": str(resolved)}


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.on_event("shutdown")
def _shutdown():
    registry.shutdown()


# ------------------------------- runner ------------------------------


def _first_free_port(start: int, tries: int = 20) -> int:
    for port in range(start, start + tries):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"No free port in {start}..{start + tries}")


def main():
    ap = argparse.ArgumentParser(description="File Workbench server")
    ap.add_argument("--port", type=int, default=8000,
                    help="Port to start searching from (default: 8000)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address (default: localhost only)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    port = _first_free_port(args.port)
    hw = parallel.hardware()
    print(f"\n  File Workbench  →  http://{args.host}:{port}")
    print(f"  {hw.performance}P + {hw.efficiency}E cores, {hw.memory_gb} GB\n")

    import uvicorn
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
