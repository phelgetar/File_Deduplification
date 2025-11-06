#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: main.py
# Purpose: Orchestrate full deduplication, classification, and sorting flow.
#
# Description of code and how it works:
# Runs the entire pipeline: scan, hash, classify, organize, preview,
# optionally write metadata and execute plan based on user confirmation.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.4.0 (2025-11-04): Debug diagnostics, text log support, stubbed Slack/email/GUI — Tim Canady
# - 0.3.0 (2025-11-04): JSON logging, timestamped log, auto mkdir — Tim Canady
# - 0.2.0 (2025-11-04): Added --filter, --dry-run-log, execution confirmation, tree preview — Tim Canady
# - 0.1.0 (2025-11-04): Initial orchestrator logic — Tim Canady
###################################################################

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from core.scanner import scan_directory
from core.hasher import generate_hashes
from core.classifier import classify_file
from core.organizer import organize_files
from core.previewer import preview_plan, print_tree_structure
from core.executor import execute_plan
from core.metadata_writer import write_metadata

# Optional: Stubbed future support for notification or GUI
def send_notification(channel, message):
    print(f"[Notification to {channel}]: {message}")

def launch_gui_preview(plan):
    print("[GUI preview not implemented yet]")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="File Deduplication & Classification Tool")
    parser.add_argument("source", type=Path, help="Source directory to scan")
    parser.add_argument("--execute", action="store_true", help="Apply changes (move files/delete duplicates)")
    parser.add_argument("--write-metadata", action="store_true", help="Embed metadata into supported files")
    parser.add_argument("--base-dir", type=Path, default=Path("sorted_root"), help="Target base directory")
    parser.add_argument("--filter", type=str, help="Only include subdirectories matching this string")
    parser.add_argument("--dry-run-log", type=Path, nargs="?", const=True, help="Save preview output to a file (optionally specify path or use timestamp)")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json", help="Log file format: json or txt")
    parser.add_argument("--notify", choices=["email", "slack"], help="Send summary notification to selected channel")
    parser.add_argument("--gui", action="store_true", help="Launch GUI preview interface (stub)")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"❌ Source directory does not exist: {args.source}")
        return

    args.base_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Scanning files...")
    files = scan_directory(args.source, name_filter=args.filter)
    print(f"🧮 Files matched: {len(files)}")

    print("🔑 Generating file hashes...")
    hashed_files = generate_hashes(files)
    print(f"📂 Unique or non-duplicate files: {len([f for f in hashed_files if not f.is_duplicate])}")

    print("🤖 Classifying files with AI...")
    classified_files = [classify_file(f) for f in hashed_files if not f.is_duplicate]
    print(f"🔎 Files classified: {len(classified_files)}")

    if args.write_metadata:
        print("🏷️ Writing metadata...")
        for f in classified_files:
            write_metadata(f)

    print("🗂️ Planning folder structure...")
    plan = organize_files(classified_files, base_dir=args.base_dir)
    print(f"📦 Planned operations: {len(plan)}")

    print("🧪 Previewing changes...")
    print("\nProposed Directory Structure:\n")
    print_tree_structure(plan)
    preview_plan(plan)

    if args.gui:
        launch_gui_preview(plan)

    if args.dry_run_log:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = (
            Path(f"dry_run_{timestamp}.{args.log_format}")
            if args.dry_run_log is True else Path(args.dry_run_log)
        )
        if args.log_format == "json":
            with open(log_path, "w") as f:
                json.dump([
                    {"source": str(fi.path), "target": str(tp)} for fi, tp in plan
                ], f, indent=2)
        else:
            with open(log_path, "w") as f:
                for fi, tp in plan:
                    f.write(f"{fi.path} → {tp}\n")
        print(f"📄 Dry run saved to: {log_path}")

    if args.notify:
        send_notification(args.notify, f"Dry run completed: {len(plan)} operations previewed.")

    if args.execute:
        confirm = input("Are you sure you want to proceed with executing changes? [y/N]: ").strip().lower()
        if confirm == 'y':
            print("🚀 Executing plan...")
            execute_plan(plan)
            if args.notify:
                send_notification(args.notify, f"✅ Execution complete: {len(plan)} files moved.")
        else:
            print("❌ Execution cancelled.")
    else:
        print("⚠️ Dry run complete. Use --execute to apply changes.")


if __name__ == "__main__":
    main()