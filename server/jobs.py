#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: jobs.py
# Purpose: Run pipeline jobs in child processes, stream their progress
#
# Description:
# A scan can run for hours and saturate 20 cores. Running that inside
# the uvicorn worker would block the event loop and make the UI
# unresponsive, so every job runs in its own SPAWNED child process:
#
#   parent (uvicorn)                child (pipeline)
#     JobRegistry                     run_pipeline(...)
#     drain thread  <-- mp.Queue --   progress events
#     ring buffer                     writes plan.jsonl on completion
#     SSE endpoint                    honours a shared cancel Event
#
# Two consequences worth knowing:
#
#  - The plan is written to disk by the child, not returned through the
#    queue. A million-row plan does not belong in a pipe or in the API
#    process's memory; the UI pages it from the file instead.
#  - Cancellation is cooperative (a multiprocessing.Event the pipeline
#    polls between items) with terminate() as the backstop, so a
#    cancelled run stops at a clean boundary and keeps its work.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Initial job engine — Tim Canady
###################################################################

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import queue as queue_mod
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Where per-job artifacts live. Beside the repo rather than in /tmp so a
# plan survives a reboot and can still be reviewed and executed.
JOBS_DIR = Path(__file__).resolve().parent.parent / ".workbench" / "jobs"

# Events kept per job for SSE replay. Progress events are already
# throttled to ~4/s by core.pipeline.Progress, so this is a generous
# window while staying bounded.
EVENT_BUFFER = 4000

QUEUED, RUNNING, DONE, ERROR, CANCELLED = "queued", "running", "done", "error", "cancelled"
TERMINAL = {DONE, ERROR, CANCELLED}


# --------------------------- child process ---------------------------
#
# Everything below runs in the child. It must be importable at module
# level (spawn re-imports this file) and must not touch parent state.


def _write_plan(job_dir: Path, plan) -> None:
    """Persist the plan as JSONL so the UI can page it without loading it all."""
    with (job_dir / "plan.jsonl").open("w", encoding="utf-8") as fh:
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


def _write_duplicates(job_dir: Path, plan) -> None:
    """Group duplicates by hash, largest reclaim first.

    Written from the plan rather than recomputed so the review screen and
    the execution both see the same set.
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

    with (job_dir / "duplicates.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _watch_parent(cancel_event, poll: float = 2.0) -> None:
    """Stop the job if the API process disappears.

    The job process is deliberately non-daemonic (it needs to spawn a
    pool of its own), so nothing kills it automatically when the server
    dies — a `kill -9` on uvicorn would otherwise leave a 20-process
    hashing run consuming the machine with no way to reach it. Watching
    for reparenting to init covers that.
    """
    import os

    original = os.getppid()
    while not cancel_event.is_set():
        if os.getppid() != original:
            logger.warning("Parent process exited; stopping this job.")
            cancel_event.set()
            return
        time.sleep(poll)


def _child_main(kind: str, config_dict: dict, job_dir_str: str,
                event_q, cancel_event) -> None:
    """Entry point for the job child process."""
    job_dir = Path(job_dir_str)
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=_watch_parent, args=(cancel_event,),
                     name="parent-watchdog", daemon=True).start()

    def emit(event: dict) -> None:
        try:
            event_q.put(event, block=False)
        except queue_mod.Full:
            # Dropping a throttled progress tick is preferable to
            # stalling the pipeline on a slow or absent reader.
            pass

    def cancelled() -> bool:
        return cancel_event.is_set()

    try:
        from core.pipeline import PipelineConfig, apply_plan, run_pipeline

        if kind == "execute":
            # Re-materialise the plan the review screen approved rather
            # than re-deriving it, so what runs is what was shown.
            config = PipelineConfig(**config_dict["pipeline"])
            plan = _load_plan_for_execution(Path(config_dict["plan_path"]),
                                            config_dict.get("selected"))
            emit({"type": "log", "level": "info",
                  "message": f"Applying {len(plan):,} approved operations"})
            apply_plan(config, plan, progress=emit)
            emit({"type": "done", "result": {"executed": True,
                                             "operations": len(plan)}})
            return

        config = PipelineConfig(**config_dict)
        result, plan = run_pipeline(config, progress=emit, cancel=cancelled)

        _write_plan(job_dir, plan)
        _write_duplicates(job_dir, plan)
        (job_dir / "result.json").write_text(json.dumps(result.as_dict(), indent=2))

        emit({"type": "cancelled" if result.cancelled else "done",
              "result": result.as_dict()})

    except Exception as e:  # surface the failure instead of dying silently
        logger.exception("Job failed")
        emit({"type": "error", "message": f"{type(e).__name__}: {e}"})


def _load_plan_for_execution(plan_path: Path, selected: Optional[List[str]]):
    """Rebuild (FileInfo, dest) pairs from plan.jsonl, optionally filtered."""
    from models.file_info import FileInfo

    keep = set(selected) if selected else None
    plan = []
    with plan_path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if keep is not None and row["src"] not in keep:
                continue
            info = FileInfo(path=Path(row["src"]), size=row["size"] or 0,
                            hash=row.get("hash"), type=row.get("type"))
            info.is_duplicate = row.get("is_duplicate", False)
            plan.append((info, Path(row["dest"])))
    return plan


# ---------------------------- parent side ----------------------------


@dataclass
class Job:
    id: str
    kind: str
    config: dict
    status: str = QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    seq: int = 0
    events: deque = field(default_factory=lambda: deque(maxlen=EVENT_BUFFER))

    _process: Any = None
    _queue: Any = None
    _cancel: Any = None
    _lock: Any = field(default_factory=threading.Lock)

    @property
    def dir(self) -> Path:
        return JOBS_DIR / self.id

    def summary(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "status": self.status,
            "created_at": self.created_at, "started_at": self.started_at,
            "finished_at": self.finished_at,
            "source": self.config.get("source"),
            "base_dir": self.config.get("base_dir"),
            "result": self.result, "error": self.error,
            "events_seen": self.seq,
        }


class JobRegistry:
    """Owns every job's process, drain thread, and event buffer."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        # Spawn (the 3.14 default on macOS) keeps the child free of the
        # parent's imported state — notably any inherited DB handles.
        self._ctx = mp.get_context("spawn")
        JOBS_DIR.mkdir(parents=True, exist_ok=True)

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> List[dict]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: -j.created_at)
        return [j.summary() for j in jobs]

    def start(self, kind: str, config: dict) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, config=config)
        job.dir.mkdir(parents=True, exist_ok=True)

        job._queue = self._ctx.Queue(maxsize=10_000)
        job._cancel = self._ctx.Event()
        # NOT daemonic. A daemonic process cannot create children of its
        # own, and the pipeline's CPU stages need a ProcessPoolExecutor —
        # marking this daemon fails the run with "daemonic processes are
        # not allowed to have children". The orphan protection daemon
        # would have given us is replaced by _watch_parent() in the child
        # plus registry.shutdown() here.
        job._process = self._ctx.Process(
            target=_child_main,
            args=(kind, config, str(job.dir), job._queue, job._cancel),
            daemon=False,
        )
        job.status = RUNNING
        job.started_at = time.time()
        job._process.start()

        threading.Thread(target=self._drain, args=(job,),
                         name=f"job-{job.id}", daemon=True).start()

        with self._lock:
            self._jobs[job.id] = job
        logger.info("Started %s job %s (pid %s)", kind, job.id, job._process.pid)
        return job

    def _drain(self, job: Job) -> None:
        """Move events from the child's queue into the job's ring buffer."""
        while True:
            try:
                event = job._queue.get(timeout=0.5)
            except queue_mod.Empty:
                # The child can die without emitting a terminal event
                # (OOM kill, SIGKILL). Notice, and don't hang forever.
                if not job._process.is_alive():
                    with job._lock:
                        if job.status not in TERMINAL:
                            job.status = (CANCELLED if job._cancel.is_set() else ERROR)
                            if job.status == ERROR:
                                job.error = (f"worker exited unexpectedly "
                                             f"(exit code {job._process.exitcode})")
                            job.finished_at = time.time()
                    self._append(job, {"type": job.status,
                                       "message": job.error or "cancelled"})
                    return
                continue

            self._append(job, event)

            kind = event.get("type")
            if kind in ("done", "error", "cancelled"):
                with job._lock:
                    job.status = {"done": DONE, "error": ERROR,
                                  "cancelled": CANCELLED}[kind]
                    job.result = event.get("result")
                    job.error = event.get("message")
                    job.finished_at = time.time()
                job._process.join(timeout=10)
                return

    def _append(self, job: Job, event: dict) -> None:
        with job._lock:
            job.seq += 1
            event = {**event, "seq": job.seq}
            job.events.append(event)

    def events_since(self, job: Job, after_seq: int) -> List[dict]:
        with job._lock:
            return [e for e in job.events if e["seq"] > after_seq]

    def cancel(self, job: Job) -> bool:
        """Ask the job to stop; escalate if it does not."""
        if job.status in TERMINAL:
            return False
        job._cancel.set()
        self._append(job, {"type": "log", "level": "warning",
                           "message": "Cancellation requested — finishing the "
                                      "current item and stopping."})

        def escalate():
            # The pipeline polls the cancel flag between items, so a
            # stage with a slow item (a large file being hashed) can take
            # a moment. Past that, terminate.
            job._process.join(timeout=30)
            if job._process.is_alive():
                logger.warning("Job %s ignored cancellation; terminating", job.id)
                job._process.terminate()

        threading.Thread(target=escalate, daemon=True).start()
        return True

    def shutdown(self) -> None:
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            if job.status not in TERMINAL and job._process.is_alive():
                job._cancel.set()
                job._process.join(timeout=5)
                if job._process.is_alive():
                    job._process.terminate()


registry = JobRegistry()

# Backstop for exits that never reach FastAPI's shutdown hook (Ctrl-C,
# SIGTERM). Not sufficient on SIGKILL — the child's parent watchdog
# covers that case.
import atexit
atexit.register(registry.shutdown)
