#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: parallel.py
# Purpose: Stage-aware parallel execution policy
#
# Description:
# One place that decides HOW each pipeline stage runs in parallel.
#
# A single global worker count is the wrong model, because each stage
# is limited by a different resource:
#
#   - scanning and hashing wait on disk, so threads are right (and
#     hashlib releases the GIL on large buffers, so threads scale);
#   - rule classification, tagging and text extraction are pure Python
#     CPU work, so only separate PROCESSES actually use more cores;
#   - Ollama work is limited by the Ollama server's own concurrency, so
#     fanning out more clients than it will serve buys nothing;
#   - CLIP/vision runs on the Apple GPU, where competing processes
#     thrash the device instead of sharing it.
#
# Callers ask for a stage by name and get an executor sized for this
# machine. Every count can be overridden per stage with an environment
# variable, e.g. WORKBENCH_HASH_WORKERS=32.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Initial stage-aware executor policy — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
import pickle
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

# Stage identifiers. Use these constants rather than bare strings so a
# typo is an AttributeError instead of a silently serial stage.
SCAN = "scan"
HASH = "hash"
CLASSIFY = "classify"
TAG = "tag"
EXTRACT = "extract"
IMAGE_META = "image_meta"
LLM = "llm"
VISION_GPU = "vision_gpu"

THREAD = "thread"
PROCESS = "process"
SERIAL = "serial"


# ----------------------------- hardware -----------------------------


@dataclass(frozen=True)
class Hardware:
    """What this machine actually has, for sizing pools."""

    logical: int          # all logical CPUs
    performance: int      # P-cores (full cores on Intel/non-Apple)
    efficiency: int       # E-cores (0 on non-Apple silicon)
    memory_gb: int

    @property
    def cpu_workers(self) -> int:
        """Workers for CPU-saturating work.

        On Apple silicon we size to the P-cores. E-cores are markedly
        slower, and loading them adds scheduling contention and heat for
        little throughput; leaving them free also keeps the UI and the
        API process responsive during a long run.
        """
        if self.performance:
            return max(1, self.performance)
        return max(1, self.logical - 2)


def _sysctl_int(key: str) -> int:
    try:
        out = subprocess.run(["sysctl", "-n", key], capture_output=True,
                             text=True, timeout=2)
        if out.returncode == 0:
            return int(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0


_hardware: Optional[Hardware] = None


def hardware() -> Hardware:
    """Detect (once) the CPU and memory available to us."""
    global _hardware
    if _hardware is None:
        logical = os.cpu_count() or 4
        perf = _sysctl_int("hw.perflevel0.logicalcpu")
        eff = _sysctl_int("hw.perflevel1.logicalcpu")
        mem = _sysctl_int("hw.memsize")
        _hardware = Hardware(
            logical=logical,
            performance=perf,
            efficiency=eff,
            memory_gb=round(mem / (1024 ** 3)) if mem else 0,
        )
        logger.debug("Detected hardware: %s", _hardware)
    return _hardware


def ollama_parallel() -> int:
    """How many requests the Ollama server will genuinely serve at once.

    Client concurrency above this just queues inside Ollama, so we read
    the server's own setting instead of guessing. Ollama's own default
    when unset is 1-4 depending on free memory; we assume the
    conservative end so we do not oversubscribe a busy server.
    """
    raw = os.getenv("OLLAMA_NUM_PARALLEL")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            logger.warning("OLLAMA_NUM_PARALLEL=%r is not an integer; using 4", raw)
    return 4


# ------------------------------ policy ------------------------------


@dataclass(frozen=True)
class StagePolicy:
    """How one stage should be executed."""

    stage: str
    kind: str      # THREAD | PROCESS | SERIAL
    workers: int
    reason: str    # human-readable, surfaced in the UI and logs

    def describe(self) -> str:
        if self.kind == SERIAL:
            return f"{self.stage}: serial ({self.reason})"
        return f"{self.stage}: {self.workers}x {self.kind} ({self.reason})"


def _policies() -> dict:
    hw = hardware()
    cpu = hw.cpu_workers
    return {
        # Directory walking waits on the filesystem, and on network
        # volumes latency dominates. Threads overlap that wait; more
        # than ~8 mostly adds seek contention on a single volume.
        SCAN: StagePolicy(SCAN, THREAD, 8, "directory I/O bound"),

        # Reading bytes off disk is the cost; hashlib releases the GIL
        # while digesting, so threads overlap read and digest. Sized
        # generously because NVMe and NAS both reward queue depth.
        HASH: StagePolicy(HASH, THREAD, min(16, max(4, cpu)), "disk read bound, GIL released in hashlib"),

        # Pure Python CPU work: MIME lookups, string and path analysis.
        # Threads would serialise on the GIL, so this must be processes.
        CLASSIFY: StagePolicy(CLASSIFY, PROCESS, cpu, "pure CPU, GIL-bound in threads"),
        TAG: StagePolicy(TAG, PROCESS, cpu, "pure CPU, GIL-bound in threads"),

        # PDF/docx/xlsx parsing is the heaviest CPU stage in the app.
        EXTRACT: StagePolicy(EXTRACT, PROCESS, cpu, "heavy CPU parsing"),

        # Mixed: reads the file, then decodes EXIF. Fewer workers than
        # full CPU so image decoding does not starve the rest.
        IMAGE_META: StagePolicy(IMAGE_META, PROCESS, max(2, cpu // 2), "mixed I/O and CPU"),

        # Bounded by the Ollama server, not by us.
        LLM: StagePolicy(LLM, THREAD, ollama_parallel(), "bounded by Ollama server concurrency"),

        # One GPU. Concurrent processes thrash it; batch within a single
        # worker instead.
        VISION_GPU: StagePolicy(VISION_GPU, SERIAL, 1, "single Apple GPU, batch instead of fan out"),
    }


def policy(stage: str) -> StagePolicy:
    """The execution policy for `stage`, honouring env overrides.

    Override any stage with WORKBENCH_<STAGE>_WORKERS. Setting it to 1
    forces that stage serial, which is the quickest way to isolate a
    stage while debugging.
    """
    base = _policies().get(stage)
    if base is None:
        raise KeyError(f"Unknown pipeline stage: {stage!r}")

    override = os.getenv(f"WORKBENCH_{stage.upper()}_WORKERS")
    if override:
        try:
            n = max(1, int(override))
        except ValueError:
            logger.warning("WORKBENCH_%s_WORKERS=%r is not an integer; ignoring",
                           stage.upper(), override)
            return base
        kind = SERIAL if n == 1 else base.kind
        return StagePolicy(stage, kind, n, f"{base.reason} (overridden)")

    return base


def describe_all() -> list:
    """Every stage policy, for logging at startup and for the UI."""
    return [policy(s).describe() for s in
            (SCAN, HASH, CLASSIFY, TAG, EXTRACT, IMAGE_META, LLM, VISION_GPU)]


# ---------------------------- execution -----------------------------


# Spawning N worker processes costs real time (each re-imports the
# module) and every item crosses a pickle boundary in both directions.
# That only pays off when the work per item is big enough to dwarf it.
# Measured on an M3 Ultra: ~0.25s to bring up 20 spawned workers.
POOL_STARTUP_SECONDS = 0.25

# Items run serially first to learn the per-item cost before committing
# to a pool. Small enough to be noise on an expensive stage, large
# enough to average out a cheap one.
SAMPLE_ITEMS = 48


def _worth_a_pool(per_item_seconds: float, remaining: int, workers: int) -> bool:
    """Would a process pool finish the remainder sooner than staying serial?

    Compares projected serial time against pool startup plus the
    parallel run. Deliberately conservative: staying serial when a pool
    would have been marginally faster costs little, while spinning up 20
    processes for microsecond-per-item work is a measurable regression
    (observed: 0.12s serial becoming 0.27s pooled on 8,000 small files).
    """
    if remaining <= 0:
        return False
    serial = per_item_seconds * remaining
    pooled = POOL_STARTUP_SECONDS + (serial / max(1, workers))
    return serial > pooled * 1.5


def _chunksize(total: int, workers: int) -> int:
    """Batch size per task hand-off to a process pool.

    Sending a million one-file tasks across a process boundary costs far
    more in pickling than the work itself. Chunking amortises that, but
    over-large chunks leave workers idle at the tail, so cap it.
    """
    if total <= 0 or workers <= 1:
        return 1
    return max(1, min(256, total // (workers * 8) or 1))


def map_stage(
    stage: str,
    fn: Callable[[T], R],
    items: Sequence[T],
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Iterator[R]:
    """Apply `fn` across `items` using this stage's policy, in order.

    Yields results in input order as they become available, so callers
    can stream them into the database instead of buffering everything.

    `progress(done, total)` is called as results arrive. `cancel()` is
    polled between results; returning True stops the run early (already
    completed work is still yielded).

    For PROCESS stages, `fn` must be a module-level function and both
    arguments and results must be picklable. Python 3.14 spawns rather
    than forks on macOS, so worker processes re-import the module: keep
    import side effects out of anything a worker touches.

    Any failure to build a pool degrades to serial rather than aborting
    the run.
    """
    total = len(items)
    if total == 0:
        return

    pol = policy(stage)

    if pol.kind == SERIAL or total == 1:
        yield from _map_serial(fn, items, total, progress, cancel)
        return

    start_at = 0
    if pol.kind == PROCESS:
        # Measure before committing. A process pool is a bet that the
        # work per item exceeds the cost of shipping it to a worker; on
        # cheap items that bet loses badly, so sample first and only
        # build the pool when the numbers support it.
        sample_n = min(SAMPLE_ITEMS, total)
        sampled = 0
        t0 = time.perf_counter()
        for result in _map_serial(fn, items[:sample_n], total, progress, cancel):
            sampled += 1
            yield result
        elapsed = time.perf_counter() - t0

        if sampled < sample_n:
            return                      # cancelled during the sample
        start_at = sample_n
        if start_at >= total:
            return                      # the sample was the whole job

        per_item = elapsed / max(1, sampled)
        if not _worth_a_pool(per_item, total - start_at, pol.workers):
            logger.info("Stage %s: staying serial (%.0f us/item — a pool would "
                        "cost more than it saves)", stage, per_item * 1e6)
            yield from _map_serial(fn, items[start_at:], total, progress, cancel,
                                   done_offset=start_at)
            return
        logger.debug("Stage %s: %.1f ms/item — using a pool for the remaining %d",
                     stage, per_item * 1e3, total - start_at)

    work = items[start_at:]
    factory = ThreadPoolExecutor if pol.kind == THREAD else ProcessPoolExecutor
    kwargs = {"max_workers": pol.workers}
    if pol.kind == THREAD:
        kwargs["thread_name_prefix"] = f"wb-{stage}"

    try:
        pool = factory(**kwargs)
    except (OSError, ValueError) as e:
        logger.warning("Could not start %s pool for stage %s (%s); running serial",
                       pol.kind, stage, e)
        yield from _map_serial(fn, items, total, progress, cancel)
        return

    logger.info("Stage %s: %s", stage, pol.describe())
    done = start_at
    try:
        map_kwargs = {}
        if pol.kind == PROCESS:
            map_kwargs["chunksize"] = _chunksize(len(work), pol.workers)

        try:
            for result in pool.map(fn, work, **map_kwargs):
                done += 1
                if progress is not None:
                    progress(done, total)
                yield result
                if cancel is not None and cancel():
                    logger.info("Stage %s cancelled after %d/%d", stage, done, total)
                    break
        except (BrokenProcessPool, RuntimeError, pickle.PickleError) as e:
            # A process pool reports most startup problems here rather
            # than at construction: an unpicklable function or argument
            # (PickleError), a worker that dies on import
            # (BrokenProcessPool), or a caller that spawned us from an
            # unguarded __main__ (RuntimeError). Falling back keeps the
            # run alive instead of losing the whole stage.
            #
            # Only safe before the first result: once we have yielded,
            # restarting would hand the caller duplicates, so a failure
            # that late is a real error and must propagate.
            if done > start_at:
                raise
            logger.warning("Stage %s pool failed before any result (%s); running serial",
                           stage, e)
            yield from _map_serial(fn, work, total, progress, cancel,
                                   done_offset=start_at)
            return
    finally:
        # cancel_futures drops queued work so a cancelled stage stops
        # promptly instead of draining the whole queue first.
        pool.shutdown(wait=True, cancel_futures=True)


def _map_serial(fn, items, total, progress, cancel, done_offset: int = 0):
    for i, item in enumerate(items, start=1):
        done = done_offset + i
        result = fn(item)
        if progress is not None:
            progress(done, total)
        yield result
        if cancel is not None and cancel():
            break


def collect(
    stage: str,
    fn: Callable[[T], R],
    items: Sequence[T],
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> list:
    """map_stage() gathered into a list, for callers that want it all."""
    return list(map_stage(stage, fn, items, progress=progress, cancel=cancel))


def batched(items: Iterable[T], size: int) -> Iterator[list]:
    """Group an iterable into lists of at most `size`.

    Used to amortise database round trips: one INSERT of 500 rows beats
    500 INSERTs by a wide margin at this scale.
    """
    batch: list = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
