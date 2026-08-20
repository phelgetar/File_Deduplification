#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: pipeline.py
# Purpose: The scan-to-execute pipeline as a callable library
#
# Description:
# core/main.py used to be both the CLI and the pipeline: it parsed
# arguments and then ran every stage inline, printing as it went. That
# made the pipeline impossible to drive from anything except a terminal,
# and it left four stages running one file at a time.
#
# This module is the pipeline itself, with no argparse and no print.
# Callers pass a PipelineConfig and a progress callback, and get back a
# PipelineResult. core/main.py is now a thin CLI over this, and
# server/jobs.py drives the same code from the web front end, so the two
# can never drift apart.
#
# The stages that were serial (rule classification, AI tagging, image
# metadata) now run through core/parallel.py. Worker processes do pure
# computation only and never open a database connection; the parent
# collects their results and writes them in batches.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Extracted from core/main.py; parallelised the classify, tag and image-metadata stages — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from core import parallel
from core.classifier import classify_file
from core.deduplicator import detect_duplicates, filter_duplicates, report_duplicates
from core.hasher import generate_hashes
from core.organizer import plan_organization
from core.scanner import scan_directory
from models.file_info import FileInfo

logger = logging.getLogger(__name__)


# ------------------------------ config ------------------------------


@dataclass
class PipelineConfig:
    """Everything one pipeline run needs to know.

    Mirrors the CLI flags of core/main.py one-for-one so the terminal and
    the web UI cannot diverge in behaviour.
    """

    source: Path
    base_dir: Path

    # Selection
    filter_names: Optional[List[str]] = None
    max_files: Optional[int] = None
    allowed_extensions: Optional[set] = None
    metadata_only_size: Optional[int] = None

    # Behaviour
    use_db: bool = False
    skip_duplicates: bool = False
    duplicate_report: Optional[str] = None
    llm_classify: bool = False
    # Cloud escalation: the last rung of classify/engine.py's ladder.
    # Off by default because it is the only tier that costs money.
    cloud_classify: bool = False
    cloud_cost_limit_usd: float = 1.00
    cloud_model: Optional[str] = None
    ai_tagging: bool = False
    analyze_images: bool = False
    image_content_tagging: bool = False

    # Execution — off by default; moving files is never implicit.
    execute: bool = False
    write_metadata: bool = False

    # Overrides. None means "use the core/parallel.py policy", which is
    # sized for this machine; the CLI's historical --workers maps here.
    hash_workers: Optional[int] = None
    hash_batch_size: int = 500

    def __post_init__(self):
        self.source = Path(self.source).expanduser().resolve()
        self.base_dir = Path(self.base_dir).expanduser().resolve()


@dataclass
class PipelineResult:
    """What a run produced. Serialisable for the API and the job log."""

    files_scanned: int = 0
    files_hashed: int = 0
    unique_files: int = 0
    duplicate_files: int = 0
    reclaimable_bytes: int = 0
    classified: int = 0
    classified_from_cache: int = 0
    llm_resolved: int = 0
    still_other: int = 0
    cloud_resolved: int = 0
    cloud_spent_usd: float = 0.0
    cloud_capped: bool = False
    files_tagged: int = 0
    tags_written: int = 0
    images_analyzed: int = 0
    planned_operations: int = 0
    executed: bool = False
    cancelled: bool = False
    duration_seconds: float = 0.0
    category_counts: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


# ----------------------------- progress -----------------------------


class Progress:
    """Emits structured events to a callback, throttled.

    A million-file run would otherwise emit a million events, which
    swamps both the SSE stream and the browser. Per-file updates are
    coalesced to at most `interval` seconds apart; stage boundaries and
    the final update of each stage always get through.
    """

    def __init__(self, sink: Optional[Callable[[dict], None]] = None,
                 interval: float = 0.25):
        self._sink = sink
        self._interval = interval
        self._last_emit = 0.0
        self._stage_started = 0.0
        self.stage = None

    def _emit(self, event: dict) -> None:
        if self._sink is None:
            return
        try:
            self._sink(event)
        except Exception as e:  # a broken UI must never kill a long run
            logger.debug("Progress sink raised (ignored): %s", e)

    def log(self, message: str, level: str = "info") -> None:
        getattr(logger, level, logger.info)(message)
        self._emit({"type": "log", "level": level, "message": message,
                    "stage": self.stage})

    def stage_start(self, stage: str, label: str, total: Optional[int] = None) -> None:
        self.stage = stage
        self._stage_started = time.monotonic()
        self._last_emit = 0.0
        pol = None
        try:
            pol = parallel.policy(stage).describe()
        except KeyError:
            pass
        self._emit({"type": "stage_start", "stage": stage, "label": label,
                    "total": total, "policy": pol})

    def update(self, done: int, total: int) -> None:
        now = time.monotonic()
        if done < total and (now - self._last_emit) < self._interval:
            return
        self._last_emit = now
        elapsed = max(1e-6, now - self._stage_started)
        rate = done / elapsed
        remaining = (total - done) / rate if rate > 0 else None
        self._emit({"type": "progress", "stage": self.stage, "done": done,
                    "total": total, "rate": round(rate, 1),
                    "eta_seconds": round(remaining) if remaining else None})

    def stage_end(self, summary: str = "", **extra) -> None:
        self._emit({"type": "stage_end", "stage": self.stage,
                    "summary": summary,
                    "elapsed": round(time.monotonic() - self._stage_started, 2),
                    **extra})


# -------------------------- worker functions --------------------------
#
# These run inside worker PROCESSES. Python 3.14 spawns rather than forks
# on macOS, so each worker re-imports this module: they must be
# module-level, their arguments and results must be picklable, and they
# must not touch the database (20 workers opening MySQL connections would
# be both slow and pointless — the parent writes in batches instead).


def _classify_worker(file_info: FileInfo) -> FileInfo:
    """Rule-based classification only: no DB, no LLM.

    The DB resume check that classify_file() would normally do per file
    is hoisted into the parent as one bulk query, and LLM fallback is a
    separate stage, because it is bound by Ollama rather than by CPU.
    """
    return classify_file(file_info, use_db=False, llm_classifier=None)


# Built once per worker process and reused across every chunked item, so
# the YAML config load is paid once per worker rather than once per file.
_tagger = None


def _tag_worker(file_info: FileInfo) -> Tuple[str, List[str]]:
    """Generate path/context tags for one file. Returns (path, tags)."""
    global _tagger
    if _tagger is None:
        from core.ai_tagger import AITagger
        _tagger = AITagger()
    try:
        return (str(file_info.path), _tagger.generate_tags(file_info))
    except Exception as e:
        logger.debug("Tagging failed for %s: %s", file_info.path, e)
        return (str(file_info.path), [])


_image_analyzer = None


def _image_worker(file_info: FileInfo):
    """Extract image metadata for one file. Returns (path, metadata|None)."""
    global _image_analyzer
    if _image_analyzer is None:
        from core.image_analyzer import ImageAnalyzer
        _image_analyzer = ImageAnalyzer()
    try:
        if not _image_analyzer.can_analyze(file_info.path):
            return (str(file_info.path), None)
        return (str(file_info.path), _image_analyzer.analyze(file_info.path))
    except Exception as e:
        logger.debug("Image analysis failed for %s: %s", file_info.path, e)
        return (str(file_info.path), None)


# ------------------------------ pipeline ------------------------------


def run_pipeline(
    config: PipelineConfig,
    progress: Optional[Callable[[dict], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Tuple[PipelineResult, List[Tuple[FileInfo, Path]]]:
    """Run scan -> hash -> dedup -> classify -> tag -> plan (-> execute).

    Returns the result summary and the organization plan. The plan is
    returned rather than applied unless config.execute is set, so the
    caller (CLI prompt, or the web UI's review screen) always gets to
    look before anything moves.

    `cancel()` is polled between and within stages; a cancelled run
    returns what it completed with `cancelled=True` set.
    """
    started = time.monotonic()
    p = Progress(progress)
    result = PipelineResult()
    cancelled = lambda: bool(cancel and cancel())

    # A path under /Volumes that is not actually mounted is an empty
    # directory, not an error: scanning it "succeeds" over nothing, and
    # executing into it fills the boot disk instead of the volume. This
    # check is offline and cheap, so every caller gets it — the CLI also
    # tries to mount first (see utils/mounts.ensure_mounts).
    from utils.mounts import unmounted_volume_for
    for label, candidate in (("source", config.source), ("destination", config.base_dir)):
        missing = unmounted_volume_for(candidate)
        if missing:
            raise RuntimeError(
                f"The {label} is on {missing}, which is not mounted. "
                f"Mount it and re-run — continuing would "
                f"{'scan an empty directory' if label == 'source' else 'write to the local disk'}.")

    if config.use_db:
        from core.db import init_db
        init_db()
        p.log("Database initialised")

    p.log(f"Hardware: {parallel.hardware()}")
    for line in parallel.describe_all():
        logger.debug("  %s", line)

    # --- scan ---
    p.stage_start(parallel.SCAN, "Scanning files")
    files = scan_directory(
        str(config.source),
        filter_names=config.filter_names,
        max_files=config.max_files,
        allowed_extensions=config.allowed_extensions,
    )
    result.files_scanned = len(files)
    p.stage_end(f"{len(files):,} files matched")
    if cancelled():
        return _finish(result, started, cancelled=True), []
    if not files:
        p.log("Nothing to do — no files matched.", "warning")
        return _finish(result, started), []

    # --- hash ---
    hash_workers = config.hash_workers or parallel.policy(parallel.HASH).workers
    p.stage_start(parallel.HASH, "Hashing files", total=len(files))
    hashed = generate_hashes(
        files,
        use_db=config.use_db,
        metadata_only_size=config.metadata_only_size,
        workers=hash_workers,
        batch_size=config.hash_batch_size,
    )
    result.files_hashed = len(hashed)
    p.stage_end(f"{len(hashed):,} files hashed with {hash_workers} threads")
    if cancelled():
        return _finish(result, started, cancelled=True), []

    # --- duplicates ---
    p.stage_start("dedup", "Detecting duplicates", total=len(hashed))
    hashed = detect_duplicates(hashed, use_db=config.use_db)
    result.duplicate_files = sum(1 for f in hashed if f.is_duplicate)
    result.unique_files = len(hashed) - result.duplicate_files
    result.reclaimable_bytes = sum(f.size or 0 for f in hashed if f.is_duplicate)
    if config.duplicate_report:
        report_duplicates(hashed, config.duplicate_report)
        p.log(f"Duplicate report written to {config.duplicate_report}")
    if config.skip_duplicates:
        hashed = filter_duplicates(hashed, keep_duplicates=False)
    p.stage_end(f"{result.unique_files:,} unique, {result.duplicate_files:,} duplicate "
                f"({_human(result.reclaimable_bytes)} reclaimable)")
    if cancelled():
        return _finish(result, started, cancelled=True), []

    # --- classify (parallel, was a serial list comprehension) ---
    classified = _stage_classify(config, hashed, p, cancelled, result)
    if cancelled():
        return _finish(result, started, cancelled=True), []

    # --- tag (parallel, was a serial for loop) ---
    if config.ai_tagging:
        _stage_tag(config, classified, p, cancelled, result)
        if cancelled():
            return _finish(result, started, cancelled=True), []

    # --- image metadata (parallel, was a serial for loop) ---
    if config.analyze_images:
        _stage_images(config, classified, p, cancelled, result)
        if cancelled():
            return _finish(result, started, cancelled=True), []

    # --- plan ---
    p.stage_start("plan", "Planning folder structure")
    # Pass the scanned root so the planner can keep each file's
    # position inside it rather than flattening by category.
    plan = plan_organization(classified, config.base_dir,
                             source_root=config.source)
    result.planned_operations = len(plan)
    p.stage_end(f"{len(plan):,} operations planned")

    # --- execute (opt in only) ---
    if config.execute:
        _stage_execute(config, plan, p, result)

    return _finish(result, started), plan


def _stage_classify(config, hashed, p, cancelled, result) -> List[FileInfo]:
    """Rule classification in processes, then LLM fallback in threads."""
    todo = hashed

    # Resume: one bulk query replaces the per-file lookup classify_file()
    # would otherwise do, which was a full round trip per file.
    #
    # The cached category is read back onto the FileInfo, not just used
    # to skip work. Skipping without restoring it left every resumed
    # file with type=None, so a re-run planned the whole tree as
    # unclassified.
    if config.use_db:
        from core.db import get_classified_categories
        known = get_classified_categories(f.path for f in hashed) or {}
        if known:
            for f in hashed:
                category = known.get(str(f.path))
                if category:
                    f.type = category
            todo = [f for f in hashed if str(f.path) not in known]
            result.classified_from_cache = len(hashed) - len(todo)
            p.log(f"Resuming: {result.classified_from_cache:,} files already "
                  f"classified (categories restored from the database)")

    p.stage_start(parallel.CLASSIFY, "Classifying files", total=len(todo))
    fresh = list(parallel.map_stage(
        parallel.CLASSIFY, _classify_worker, todo,
        progress=p.update, cancel=cancelled,
    ))
    p.stage_end(f"{len(fresh):,} files classified")

    # LLM fallback for whatever the rules left as "other". This is a
    # separate stage because it is bound by the Ollama server, not the
    # CPU, so it wants a small thread pool rather than 20 processes.
    if config.llm_classify and fresh and not cancelled():
        fresh = _stage_llm(config, fresh, p, cancelled, result)

    # Cloud escalation — the only tier that costs money, so it runs last
    # and only on what the free tiers could not place.
    if config.cloud_classify and fresh and not cancelled():
        _stage_cloud(config, fresh, p, cancelled, result)

    if config.use_db and fresh:
        from core.db import save_classifications_bulk
        written = save_classifications_bulk(
            (f.path, f.type, f.owner, f.year, None) for f in fresh)
        p.log(f"Wrote {written:,} classifications to the database")

    # Reunite with the files we skipped, preserving the original order.
    by_path = {str(f.path): f for f in fresh}
    classified = [by_path.get(str(f.path), f) for f in hashed]

    result.classified = len(classified)
    counts = {}
    for f in classified:
        counts[f.type or "unclassified"] = counts.get(f.type or "unclassified", 0) + 1
    result.category_counts = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    return classified


def _stage_llm(config, files, p, cancelled, result) -> List[FileInfo]:
    """Send the leftover 'other' files to a local Ollama model."""
    from core.llm_client import LLMClassifier

    others = [f for f in files if f.type == "other"]
    if not others:
        return files

    llm = LLMClassifier()
    if not llm.is_available():
        p.log(f"Ollama not reachable at {llm.host} — skipping LLM classification. "
              f"Start it with: ollama serve", "warning")
        return files

    p.stage_start(parallel.LLM, f"LLM classifying {len(others):,} unresolved files",
                  total=len(others))
    pol = parallel.policy(parallel.LLM)
    p.log(f"Using {pol.workers} concurrent requests to {llm.model} @ {llm.host}. "
          f"Raise OLLAMA_NUM_PARALLEL to use more.")

    def resolve(file_info: FileInfo) -> FileInfo:
        answer = llm.classify(file_info)
        if answer:
            file_info.type = answer[0]
        return file_info

    resolved = list(parallel.map_stage(
        parallel.LLM, resolve, others, progress=p.update, cancel=cancelled))

    result.llm_resolved = sum(1 for f in resolved if f.type != "other")
    result.still_other = sum(1 for f in resolved if f.type == "other")
    p.stage_end(f"LLM resolved {result.llm_resolved:,}; "
                f"{result.still_other:,} remain 'other'")

    updated = {str(f.path): f for f in resolved}
    return [updated.get(str(f.path), f) for f in files]


def _stage_cloud(config, files, p, cancelled, result) -> None:
    """Escalate the leftovers to Claude, under a hard spend cap."""
    from classify import engine

    ladder = engine.LadderConfig(
        use_cloud=True,
        cloud_cost_limit_usd=config.cloud_cost_limit_usd,
        cloud_model=config.cloud_model,
    )
    candidates = engine.escalation_candidates(files)
    if not candidates:
        p.log("Nothing left for the cloud tier — the free tiers placed everything.")
        return

    quote = engine.preflight(candidates, ladder)
    p.stage_start(parallel.LLM,
                  f"Cloud classifying {len(candidates):,} unresolved files",
                  total=len(candidates))
    p.log(f"{quote['files']:,} files, ~${quote['estimated_cost_usd']:.2f} estimated "
          f"on {quote['model']} (cap ${config.cloud_cost_limit_usd:.2f})")

    if not quote["within_budget"]:
        # Stop before the first request rather than partway through: a
        # half-classified batch that hit the cap is worse than a clear
        # refusal the user can act on.
        p.log(f"Estimate exceeds the ${config.cloud_cost_limit_usd:.2f} cap — "
              f"skipping the cloud tier. Raise the cap or narrow the run.",
              "warning")
        p.stage_end("skipped (over budget)")
        return

    summary = engine.run_cloud_tier(candidates, ladder,
                                    progress=p.update, cancel=cancelled)
    result.cloud_resolved = summary["resolved"]
    result.cloud_spent_usd = summary["spent_usd"]
    result.cloud_capped = summary["capped"]
    result.still_other = sum(1 for f in files if f.type == "other")
    p.stage_end(f"Cloud resolved {summary['resolved']:,} of {summary['attempted']:,}; "
                f"spent ${summary['spent_usd']:.2f}"
                + (" (hit the cap)" if summary["capped"] else ""))


def _stage_tag(config, classified, p, cancelled, result) -> None:
    if not config.use_db:
        p.log("AI tagging needs the database (tags are stored there) — skipped.",
              "warning")
        return

    from core.db import save_file_tags_bulk

    p.stage_start(parallel.TAG, "Generating tags", total=len(classified))
    written = 0
    tagged = 0
    for batch in parallel.batched(
        parallel.map_stage(parallel.TAG, _tag_worker, classified,
                           progress=p.update, cancel=cancelled),
        500,
    ):
        rows = [(path, tags) for path, tags in batch if tags]
        tagged += len(rows)
        written += save_file_tags_bulk(rows, tag_source="ai_tagger", confidence=0.9)

    result.files_tagged = tagged
    result.tags_written = written
    p.stage_end(f"{tagged:,} files tagged, {written:,} tags written")


def _stage_images(config, classified, p, cancelled, result) -> None:
    if not config.use_db:
        p.log("Image analysis needs the database — skipped.", "warning")
        return

    from core.image_db import save_image_metadata

    p.stage_start(parallel.IMAGE_META, "Extracting image metadata",
                  total=len(classified))
    analyzed = 0
    for path, metadata in parallel.map_stage(
        parallel.IMAGE_META, _image_worker, classified,
        progress=p.update, cancel=cancelled,
    ):
        if metadata is not None and save_image_metadata(Path(path), metadata):
            analyzed += 1

    result.images_analyzed = analyzed
    p.stage_end(f"{analyzed:,} images analysed")


def _stage_execute(config, plan, p, result) -> None:
    """Apply the plan. Callers gate this; we re-check the DB guard."""
    from core.executor import execute_plan

    if config.use_db:
        from core.db import is_db_down
        if is_db_down():
            # Same refusal core/main.py has always made: moving files
            # without an operations row makes the run unauditable.
            raise RuntimeError(
                "The database connection was lost during this run (circuit "
                "breaker tripped). Refusing to move files without operation "
                "logging. Restore the database and re-run — hashes completed "
                "before the outage are cached, so the re-run will be fast.")

    p.stage_start("execute", "Applying changes", total=len(plan))
    execute_plan(plan, write_metadata=config.write_metadata, use_db=config.use_db)
    result.executed = True
    p.stage_end(f"{len(plan):,} operations applied")


def _finish(result: PipelineResult, started: float, cancelled: bool = False):
    result.duration_seconds = round(time.monotonic() - started, 2)
    result.cancelled = cancelled
    return result


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def apply_plan(config: PipelineConfig, plan, progress=None) -> None:
    """Execute an already-reviewed plan.

    Split out from run_pipeline so a caller can show the plan, get a
    human decision, and only then move files — which is what both the
    CLI prompt and the web UI's review screen do.
    """
    p = Progress(progress)
    _stage_execute(config, plan, p, PipelineResult())
