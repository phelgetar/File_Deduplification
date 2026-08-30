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
from core.artifacts import (JOBS_DIR, MANIFEST, write_duplicates,
                            write_manifest, write_plan, write_result)

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

        write_plan(job_dir, plan)
        write_duplicates(job_dir, plan)
        write_result(job_dir, result.as_dict())

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
        # Directory mtime at the last refresh, so listing costs one stat
        # when nothing has changed.
        self._dir_mtime: float = 0.0
        self._lock = threading.Lock()
        # Spawn (the 3.14 default on macOS) keeps the child free of the
        # parent's imported state — notably any inherited DB handles.
        self._ctx = mp.get_context("spawn")
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    def _refresh_from_disk(self) -> None:
        """Pick up job directories that appeared since we last looked.

        Reading disk only at startup meant a command-line run never
        showed up in a server that was already running — which defeats
        the point of recording CLI runs at all. One user's server had
        been up for ten days and listed 13 jobs against 54 on disk.

        Only unseen directories are read, and only when the directory's
        own mtime has moved, so the common case is a single stat.
        """
        try:
            stamp = JOBS_DIR.stat().st_mtime
        except OSError:
            return
        if stamp == self._dir_mtime:
            return
        self._dir_mtime = stamp
        for job_dir in JOBS_DIR.glob("*"):
            if not job_dir.is_dir() or job_dir.name in self._jobs:
                continue
            try:
                job = _job_from_disk(job_dir)
            except Exception as e:
                logger.debug("Skipping unreadable job dir %s: %s", job_dir.name, e)
                continue
            if job is not None:
                self._jobs[job.id] = job

    def _load_from_disk(self) -> None:
        """Rebuild the job list from what previous runs left on disk.

        The plans, duplicate groups and results were always written to
        .workbench/jobs/<id>/ and survive a restart — but the registry
        was memory-only, so restarting emptied the Jobs tab and made
        finished work look lost. Reading the directory back means a
        completed plan can still be reviewed and executed days later.
        """
        for job_dir in sorted(JOBS_DIR.glob("*"), key=lambda d: -d.stat().st_mtime):
            if not job_dir.is_dir():
                continue
            try:
                job = _job_from_disk(job_dir)
            except Exception as e:
                logger.debug("Skipping unreadable job dir %s: %s", job_dir.name, e)
                continue
            if job is not None:
                self._jobs[job.id] = job
        if self._jobs:
            logger.info("Recovered %d job(s) from %s", len(self._jobs), JOBS_DIR)

    def get(self, job_id: str) -> Optional[Job]:
        """A job by id, looking on disk if this process has not seen it."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                self._refresh_from_disk()
                job = self._jobs.get(job_id)
            return job

    def list(self) -> List[dict]:
        with self._lock:
            self._refresh_from_disk()
            jobs = sorted(self._jobs.values(), key=lambda j: -j.created_at)
        return [j.summary() for j in jobs]

    def start(self, kind: str, config: dict) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, config=config)
        job.dir.mkdir(parents=True, exist_ok=True)
        write_manifest(job.id, job.kind, job.config, job.created_at)

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


# ------------------------- persistence on disk -------------------------
#
# A job's artifacts (plan.jsonl, duplicates.jsonl, result.json) were
# always written here; only the index of them lived in memory. The
# manifest adds the bit that was missing — what the job was for — so the
# Jobs tab can be rebuilt after a restart instead of coming back empty.



def _job_from_disk(job_dir: Path) -> Optional["Job"]:
    """Reconstruct one job from its directory, or None if there is nothing."""
    manifest_path = job_dir / MANIFEST
    result_path = job_dir / "result.json"
    plan_path = job_dir / "plan.jsonl"

    if not any(p.exists() for p in (manifest_path, result_path, plan_path)):
        return None

    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    config = manifest.get("config", {})
    if not config.get("source") and plan_path.exists():
        # Jobs from before manifests existed: recover a usable label from
        # the plan itself rather than showing a blank row.
        with plan_path.open(encoding="utf-8") as fh:
            first = fh.readline()
        if first:
            try:
                config = {**config,
                          "source": str(Path(json.loads(first)["src"]).parent),
                          "recovered": True}
            except (ValueError, KeyError):
                pass

    job = Job(id=manifest.get("id", job_dir.name),
              kind=manifest.get("kind", "scan"),
              config=config,
              created_at=manifest.get("created_at", job_dir.stat().st_mtime))

    if result_path.exists():
        job.result = json.loads(result_path.read_text())
        job.status = CANCELLED if job.result.get("cancelled") else DONE
        job.finished_at = result_path.stat().st_mtime
    else:
        # A manifest with no result means the process was killed mid-run;
        # it cannot still be running, because it died with the server.
        job.status = ERROR
        job.error = "interrupted — the server stopped before this run finished"
        job.finished_at = job_dir.stat().st_mtime

    return job

registry = JobRegistry()

# Backstop for exits that never reach FastAPI's shutdown hook (Ctrl-C,
# SIGTERM). Not sufficient on SIGKILL — the child's parent watchdog
# covers that case.
import atexit
atexit.register(registry.shutdown)

