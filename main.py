#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Application entry point with CLI interface
#
# Description:
# Main entry point for the file deduplication system. Orchestrates
# the complete pipeline: scanning, hashing, classification, organization,
# and execution. Supports database persistence, caching, notifications,
# and GUI preview mode.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.5.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.5.0 (2025-11-12): Added DB support, input validation, max-files param — Tim Canady
# - 0.4.5 (2025-11-06): Implemented Slack notifications — Tim Canady
# - 0.4.4 (2025-11-06): Restore full CLI and fix scan_directory param — Tim Canady
# - 0.1.0 (2025-09-28): Initial release — Tim Canady
###################################################################

import argparse
from dotenv import load_dotenv
import logging
import sys
from core.scanner import scan_directory
from core.hasher import generate_hashes
from core.deduplicator import detect_duplicates, filter_duplicates, report_duplicates
from core.classifier import classify_file
from core.organizer import plan_organization
from core.previewer import preview_plan, print_tree_structure
from core.executor import execute_plan
from utils.cache import load_cache, save_cache
from utils.notifications import send_slack_notification
from utils.versioning import get_version
from utils.gui import launch_gui
from pathlib import Path
import os
from datetime import datetime
import json

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
    import re
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

def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Root source directory")
    parser.add_argument("--base-dir", required=True, help="Base output directory")
    parser.add_argument("--filter", nargs="*", help="Root-level directory name patterns to include")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--dry-run-log", action="store_true", help="Log preview to file")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json")
    parser.add_argument("--notify", choices=["email", "slack"])
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-metadata", action="store_true")
    parser.add_argument("--ignore-errors", action="store_true", help="Skip files with access errors")
    parser.add_argument("--use-db", action="store_true", help="Enable database logging")
    parser.add_argument("--metadata-only-size", type=str, help="Files larger than this size will only have metadata stored (no hashing). Format: 75MB, 1GB, etc. Default: no limit")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicate files (only process unique files)")
    parser.add_argument("--duplicate-report", type=str, help="Generate duplicate report and save to file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Parse metadata-only size threshold
    metadata_only_size = None
    if args.metadata_only_size:
        try:
            metadata_only_size = parse_size(args.metadata_only_size)
            logging.info(f"📏 Files larger than {args.metadata_only_size} ({metadata_only_size:,} bytes) will be metadata-only")
        except ValueError as e:
            logging.error(f"❌ {e}")
            sys.exit(1)

    # Initialize database if enabled
    if args.use_db:
        try:
            from core.db import init_db
            init_db()
            logging.info("✅ Database initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize database: {e}")
            logging.error("   Check your .env file for correct DATABASE_URL and DB_PASSWORD")
            sys.exit(1)

    # Input validation
    source_path = Path(args.source).resolve()
    base_dir_path = Path(args.base_dir).resolve()

    # Validate source directory
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
        # Check if parent directory exists and is writable
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

    print("🔍 Scanning files...")
    files = scan_directory(str(source_path), filter_names=args.filter, max_files=args.max_files)
    print(f"🔎 Matched root folders: {set(p.parent for p in files)}")
    print(f"🧮 Files matched: {len(files)}")

    print("🔑 Generating file hashes...")
    hashed_files = generate_hashes(files, use_db=args.use_db, metadata_only_size=metadata_only_size)
    print(f"📂 Files hashed: {len(hashed_files)}")

    print("🔍 Detecting duplicates...")
    hashed_files = detect_duplicates(hashed_files, use_db=args.use_db)

    # Generate duplicate report if requested
    if args.duplicate_report:
        report_duplicates(hashed_files, args.duplicate_report)

    # Filter duplicates if requested
    if args.skip_duplicates:
        hashed_files = filter_duplicates(hashed_files, keep_duplicates=False)
        print(f"📂 Unique files (duplicates filtered): {len(hashed_files)}")
    else:
        unique_count = sum(1 for f in hashed_files if not f.is_duplicate)
        duplicate_count = sum(1 for f in hashed_files if f.is_duplicate)
        print(f"📂 Unique files: {unique_count}, Duplicates: {duplicate_count}")

    print("🤖 Classifying files with AI...")
    classified = [classify_file(f, use_db=args.use_db) for f in hashed_files]
    print(f"🔎 Files classified: {len(classified)}")

    print("🗂️ Planning folder structure...")
    plan = plan_organization(classified, base_dir_path)
    print(f"📦 Planned operations: {len(plan)}")

    print("🧪 Previewing changes...\n")
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
            execute_plan(plan, write_metadata=args.write_metadata, use_db=args.use_db)
            # Save cache after successful execution
            save_cache(cache)
        else:
            print("❌ Execution cancelled.")
    else:
        print("\n⚠️ Dry run complete. Use --execute to apply changes.")
        print("To proceed, run the same command with --execute flag")

if __name__ == "__main__":
    main()
