#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Command-line interface over core/pipeline.py
#
# Description:
# Argument parsing, validation and terminal output for the file
# deduplication system. The pipeline itself lives in core/pipeline.py
# so that the CLI and the web front end (server/) drive exactly the
# same code and cannot drift apart.
#
# Every flag documented for previous versions still works and still
# means the same thing.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.11.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.11.0 (2026-08-17): Pipeline moved to core/pipeline.py; CLI is now a thin wrapper. Classification, tagging and image analysis run in parallel; --workers now applies to hashing only, with per-stage sizing handled automatically — Tim Canady
# - 0.10.0 (2026-07-20): Added --llm-classify (local Ollama fallback), --workers/--batch-size (parallel resumable hashing), graceful Ctrl+C handling — Tim Canady
# - 0.9.0 (2025-11-19): Added AI-based tagging for ALL files (not just images); Fixed root_folder double-nesting issue — Tim Canady
# - 0.8.0 (2025-11-15): Added --file-types filter for selective scanning by file type groups — Tim Canady
# - 0.7.0 (2025-11-15): Added AI content tagging with --ai-tagging flag — Tim Canady
# - 0.6.0 (2025-11-15): Added image metadata extraction with --analyze-images flag — Tim Canady
# - 0.5.0 (2025-11-12): Added DB support, input validation, max-files param — Tim Canady
# - 0.4.5 (2025-11-06): Implemented Slack notifications — Tim Canady
# - 0.4.4 (2025-11-06): Restore full CLI and fix scan_directory param — Tim Canady
# - 0.1.0 (2025-09-28): Initial release — Tim Canady
###################################################################

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from core.pipeline import PipelineConfig, apply_plan, run_pipeline
from core.previewer import preview_plan, print_tree_structure
from utils.cache import load_cache, save_cache
from utils.gui import launch_gui
from utils.notifications import send_slack_notification

logger = logging.getLogger(__name__)


def parse_size(size_str):
    """Parse human-readable size string to bytes (e.g., '75MB' -> 78643200)"""
    if not size_str:
        return None

    size_str = size_str.upper().strip()
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }

    # Extract number and unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}. Use format like: 75MB, 1GB, 500KB")

    number = float(match.group(1))
    unit = match.group(2) if match.group(2) else 'B'

    # Add 'B' if only K, M, G, T specified
    if unit in ['K', 'M', 'G', 'T']:
        unit += 'B'

    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}. Use: B, KB, MB, GB, TB")

    return int(number * units[unit])


def _console_progress(event):
    """Render pipeline events as the terminal output this CLI always had."""
    kind = event.get("type")
    if kind == "stage_start":
        policy = event.get("policy")
        suffix = f"   [{policy}]" if policy else ""
        print(f"\n{event['label']}...{suffix}")
    elif kind == "stage_end":
        summary = event.get("summary")
        if summary:
            print(f"  {summary}  ({event.get('elapsed', 0)}s)")
    elif kind == "log":
        level = event.get("level", "info")
        prefix = {"warning": "⚠️ ", "error": "❌ "}.get(level, "  ")
        print(f"{prefix}{event['message']}")
    elif kind == "progress":
        # Single rewritten line so a long run does not scroll the terminal.
        done, total = event["done"], event["total"]
        rate = event.get("rate") or 0
        eta = event.get("eta_seconds")
        eta_txt = f" eta {eta}s" if eta else ""
        sys.stdout.write(f"\r  {done:,}/{total:,}  {rate:,.0f}/s{eta_txt}   ")
        sys.stdout.flush()
        if done >= total:
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()


def main():
    load_dotenv()

    # Handle --list-file-types early (before requiring other args)
    if '--list-file-types' in sys.argv:
        from utils.file_type_filter import FileTypeFilter
        filter = FileTypeFilter()
        filter.print_available_groups()
        sys.exit(0)

    parser = argparse.ArgumentParser()
    # Optional at parse time so the informational flags below (--show-mounts,
    # --show-project-roots, --list-file-types, …) work on their own; they are
    # required for a real run and validated once those have had their chance
    # to exit.
    parser.add_argument("source", nargs="?", help="Root source directory")
    parser.add_argument("--base-dir", help="Base output directory")
    parser.add_argument("--filter", nargs="*", help="Root-level directory name patterns to include")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--dry-run-log", action="store_true", help="Log preview to file")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json", help="Format for --dry-run-log (default: json). Job records under .workbench/jobs/ are written regardless and are the readable ones")
    parser.add_argument("--notify", choices=["email", "slack"], help="Send a summary when the run finishes. Needs SLACK_WEBHOOK_URL or the EMAIL_* settings in .env")
    parser.add_argument("--gui", action="store_true", help="Preview the plan in a PySimpleGUI window. Superseded by the web UI (python -m server.app); kept for existing workflows")
    parser.add_argument("--execute", action="store_true", help="COPY files to their planned destinations. Without this the run is a dry run and nothing is written. Sources are never deleted or moved")
    parser.add_argument("--write-metadata", action="store_true", help="Alongside each copied file, write a <name>.meta.json sidecar recording its original path, hash, size, category and tags")
    parser.add_argument("--ignore-errors", action="store_true", help="Skip files with access errors")
    parser.add_argument("--use-db", action="store_true", help="Enable database logging")
    parser.add_argument("--metadata-only-size", type=str, help="Files larger than this size will only have metadata stored (no hashing). Format: 75MB, 1GB, etc. Default: no limit")
    parser.add_argument("--workers", type=int, help="Number of parallel hashing threads. Defaults to a value sized for this machine (see --show-parallelism). Other stages size themselves; override any of them with WORKBENCH_<STAGE>_WORKERS.")
    parser.add_argument("--batch-size", type=int, default=500, help="Files per hashing batch checkpoint (default: 500). Each completed file is saved to the DB immediately; batches add periodic progress summaries.")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicate files (only process unique files)")
    parser.add_argument("--duplicate-report", type=str, help="Generate duplicate report and save to file")
    parser.add_argument("--analyze-images", action="store_true", help="Extract and store comprehensive metadata from image files")
    parser.add_argument("--ai-tagging", action="store_true", help="Use AI to automatically identify image content (objects, scenes, people, locations)")
    parser.add_argument("--llm-classify", action="store_true", help="Use a local Ollama LLM to classify files that fall into the 'other' category (requires a running Ollama server; see OLLAMA_HOST/LLM_MODEL in .env)")
    parser.add_argument("--cloud-classify", action="store_true", help="Escalate files that neither the rules nor the local LLM could place to Claude. Costs money: bounded by --cloud-cost-limit and skipped entirely if the estimate exceeds it. Needs ANTHROPIC_API_KEY (or `ant auth login`)")
    parser.add_argument("--cloud-cost-limit", type=float, default=1.00, help="Hard spend ceiling in USD for --cloud-classify (default: 1.00). Enforced against actual token usage, not the estimate")
    parser.add_argument("--cloud-model", type=str, help="Model for --cloud-classify (default: claude-opus-5; also honours the CLOUD_MODEL env var)")
    parser.add_argument("--file-types", type=str, help="Filter by file type groups (e.g., 'images', 'media', 'docs', 'word_docs'). Use comma for multiple: 'images,videos'")
    parser.add_argument("--list-file-types", action="store_true", help="List all available file type groups and exit")
    parser.add_argument("--no-auto-mount", action="store_true", help="Do not attempt to mount missing network volumes; fail instead. The check that they ARE mounted still runs")
    parser.add_argument("--no-record", action="store_true", help="Do not record this run under .workbench/jobs/. By default every run is recorded so it appears in the web UI's Jobs tab and its plan stays reviewable")
    parser.add_argument("--show-mounts", action="store_true", help="Show whether the required network volumes are mounted, and exit")
    parser.add_argument("--show-project-roots", action="store_true", help="Show which directory trees are kept intact as projects, and exit")
    parser.add_argument("--no-project-roots", action="store_true", help="Do not keep project trees together; file every file by category as before")
    parser.add_argument("--show-parallelism", action="store_true", help="Show how each stage will be parallelised on this machine, and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.show_mounts:
        from utils import mounts
        print("Required volumes:\n")
        print(mounts.describe())
        sys.exit(0)

    if args.show_project_roots:
        from core import projects
        print("Trees kept intact (these outrank every other rule):\n")
        print(projects.describe())
        print("\nEdit the project_roots section of config/rules.yaml to add your own, or pass "
              "--no-project-roots for one run.")
        sys.exit(0)

    if args.no_project_roots:
        os.environ["WORKBENCH_NO_PROJECT_ROOTS"] = "1"

    if args.show_parallelism:
        from core import parallel
        print(f"Detected: {parallel.hardware()}\n")
        for line in parallel.describe_all():
            print(f"  {line}")
        print("\nOverride any stage with WORKBENCH_<STAGE>_WORKERS "
              "(e.g. WORKBENCH_HASH_WORKERS=32). Setting one to 1 forces it serial.")
        sys.exit(0)

    if args.list_file_types:
        from utils.file_type_filter import FileTypeFilter
        FileTypeFilter().print_available_groups()
        sys.exit(0)

    missing = [name for name, value in
               (("source", args.source), ("--base-dir", args.base_dir))
               if not value]
    if missing:
        parser.error("the following arguments are required: " + ", ".join(missing))

    # Parse file types filter
    allowed_extensions = None
    if args.file_types:
        from utils.file_type_filter import FileTypeFilter, parse_file_types_arg
        filter = FileTypeFilter()
        group_names = parse_file_types_arg(args.file_types)

        if not group_names:
            logging.error(f"❌ Invalid --file-types argument: {args.file_types}")
            sys.exit(1)

        allowed_extensions = filter.get_extensions(group_names)
        if not allowed_extensions:
            logging.info(f"📂 Scanning all file types (no filtering)")
        else:
            logging.info(f"📂 Filtering by file types: {', '.join(group_names)}")
            logging.info(f"   Extensions: {', '.join(sorted(list(allowed_extensions))[:20])}")
            if len(allowed_extensions) > 20:
                logging.info(f"   ... and {len(allowed_extensions) - 20} more")

    # Parse metadata-only size threshold
    metadata_only_size = None
    if args.metadata_only_size:
        try:
            metadata_only_size = parse_size(args.metadata_only_size)
            logging.info(f"📏 Files larger than {args.metadata_only_size} ({metadata_only_size:,} bytes) will be metadata-only")
        except ValueError as e:
            logging.error(f"❌ {e}")
            sys.exit(1)

    # Mount preflight. This runs before path validation because the
    # source and destination normally live on these volumes: an
    # unmounted /Volumes/home is an empty directory, so a scan would
    # "succeed" over nothing, and --execute would write to the boot disk.
    from utils import mounts
    mount_problems = mounts.ensure_mounts(auto_mount=not args.no_auto_mount)
    if mount_problems:
        for problem in mount_problems:
            logging.error(f"❌ {problem}")
        logging.error("   Refusing to run: the volumes this scan needs are "
                      "not available. Mount them in Finder and re-run, or "
                      "pass --show-mounts to see the current state.")
        sys.exit(1)

    # Input validation
    source_path = Path(args.source).resolve()
    base_dir_path = Path(args.base_dir).resolve()

    if not source_path.exists():
        logging.error(f"❌ Source directory does not exist: {source_path}")
        sys.exit(1)

    if not source_path.is_dir():
        logging.error(f"❌ Source path is not a directory: {source_path}")
        sys.exit(1)

    if not os.access(source_path, os.R_OK):
        logging.error(f"❌ Source directory is not readable: {source_path}")
        sys.exit(1)

    # Validate base directory (create if doesn't exist)
    if not base_dir_path.exists():
        parent_dir = base_dir_path.parent
        if not parent_dir.exists():
            logging.error(f"❌ Parent directory does not exist: {parent_dir}")
            logging.error(f"   Please ensure the parent directory exists before running this command.")
            logging.error(f"   You can create it with: mkdir -p {parent_dir}")
            sys.exit(1)

        if not os.access(parent_dir, os.W_OK):
            logging.error(f"❌ Parent directory is not writable: {parent_dir}")
            logging.error(f"   Please check permissions or choose a different base directory.")
            sys.exit(1)

        try:
            base_dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"✅ Created base directory: {base_dir_path}")
        except Exception as e:
            logging.error(f"❌ Failed to create base directory {base_dir_path}: {e}")
            sys.exit(1)

    if not os.access(base_dir_path, os.W_OK):
        logging.error(f"❌ Base directory is not writable: {base_dir_path}")
        sys.exit(1)

    # Load cache for faster processing
    cache = load_cache()

    config = PipelineConfig(
        source=source_path,
        base_dir=base_dir_path,
        filter_names=args.filter,
        max_files=args.max_files,
        allowed_extensions=allowed_extensions,
        metadata_only_size=metadata_only_size,
        use_db=args.use_db,
        skip_duplicates=args.skip_duplicates,
        duplicate_report=args.duplicate_report,
        llm_classify=args.llm_classify,
        cloud_classify=args.cloud_classify,
        cloud_cost_limit_usd=args.cloud_cost_limit,
        cloud_model=args.cloud_model,
        ai_tagging=args.ai_tagging,
        analyze_images=args.analyze_images,
        write_metadata=args.write_metadata,
        hash_workers=args.workers,
        hash_batch_size=args.batch_size,
        # Execution is deliberately not passed through: the plan is shown
        # and confirmed first, then applied below.
        execute=False,
    )

    # Record the run the same way the web UI does, so a terminal run
    # shows up in the Jobs tab and its plan can be reviewed — or executed
    # — later. The manifest is written first: a run killed part-way then
    # still leaves evidence it happened.
    job_id = None
    if not args.no_record:
        from core import artifacts
        job_id = artifacts.new_job_id()
        # Everything that changes what the run does, not just where it
        # pointed. Without the ladder flags a record cannot answer "did
        # this one use cloud escalation?" or "was that scan hashing
        # everything?" — and the two front ends do not always default the
        # same way, so the answer is not inferable from the source alone.
        artifacts.write_manifest(job_id, "scan", {
            "source": str(source_path), "base_dir": str(base_dir_path),
            "use_db": args.use_db, "max_files": args.max_files,
            "file_types": args.file_types, "via": "cli",
            "metadata_only_size": args.metadata_only_size,
            "hash_workers": args.workers,
            "skip_duplicates": args.skip_duplicates,
            "llm_classify": args.llm_classify,
            "cloud_classify": args.cloud_classify,
            "cloud_cost_limit_usd": args.cloud_cost_limit,
            "cloud_model": args.cloud_model,
            "ai_tagging": args.ai_tagging,
            "analyze_images": args.analyze_images,
            "project_roots": not args.no_project_roots,
        })

    try:
        result, plan = run_pipeline(config, progress=_console_progress)
    except KeyboardInterrupt:
        print("\n🛑 Run interrupted. All completed hashes are saved"
              + (" in the database — re-run the same command to resume." if args.use_db
                 else ". Enable --use-db to make interrupted runs resumable."))
        sys.exit(130)
    except RuntimeError as e:
        logging.error(f"❌ {e}")
        sys.exit(1)

    if job_id:
        from core import artifacts
        try:
            directory = artifacts.record_run(job_id, "scan", config.__dict__, result, plan)
            print(f"\n📁 Run recorded as {job_id} — open it in the Jobs tab, "
                  f"or find it at {directory}")
        except OSError as e:
            logging.warning(f"Could not record this run: {e}")

    print("\n🧪 Previewing changes...\n")
    preview_plan(plan)

    print("\nProposed Directory Structure:\n")
    print_tree_structure(plan)

    if args.dry_run_log:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_name = f"dry_run_preview_{timestamp}.{args.log_format}"
        with open(log_name, "w") as f:
            if args.log_format == "json":
                json.dump([str(p) for p in plan], f, indent=2)
            else:
                for op in plan:
                    f.write(str(op) + "\n")
        print(f"📄 Dry run log saved: {log_name}")

    if args.notify:
        message = f"Dry run complete with {len(plan)} operations."
        if args.notify == "slack":
            send_slack_notification(message)
        elif args.notify == "email":
            from utils.notifications import send_email_notification
            send_email_notification("File Deduplication Dry Run", message)

    if args.gui:
        launch_gui(plan)

    if args.execute:
        confirm = input("⚠️ Are you sure you want to apply these changes? (y/N): ")
        if confirm.lower() == 'y':
            try:
                apply_plan(config, plan, progress=_console_progress)
            except RuntimeError as e:
                # Losing the DB mid-run means moves would go unlogged.
                print(f"❌ {e}")
                sys.exit(1)
            save_cache(cache)
        else:
            print("❌ Execution cancelled.")
    else:
        print("\n⚠️ Dry run complete. Use --execute to apply changes.")
        print("To proceed, run the same command with --execute flag")


if __name__ == "__main__":
    main()
