#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Application entry point
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.4
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.5 (2025-11-06): Implemented Slack notifications
# - 0.4.4 (2025-11-06): Restore full CLI and fix scan_directory param
###################################################################

import argparse
from dotenv import load_dotenv
import logging
import sys
from core.scanner import scan_directory
from core.hasher import generate_hashes
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

def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Root source directory")
    parser.add_argument("--base-dir", required=True, help="Base output directory")
    parser.add_argument("--filter", nargs="*", help="Root-level directory name patterns to include")
    parser.add_argument("--dry-run-log", action="store_true", help="Log preview to file")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json")
    parser.add_argument("--notify", choices=["email", "slack"])
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-metadata", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    print("🔍 Scanning files...")
    files = scan_directory(args.source, filter_names=args.filter)
    print(f"🔎 Matched root folders: {set(p.parent for p in files)}")
    print(f"🧮 Files matched: {len(files)}")

    print("🔑 Generating file hashes...")
    hashed_files = generate_hashes(files)
    print(f"📂 Unique or non-duplicate files: {len(hashed_files)}")

    print("🤖 Classifying files with AI...")
    classified = [classify_file(f) for f in hashed_files]
    print(f"🔎 Files classified: {len(classified)}")

    print("🗂️ Planning folder structure...")
    plan = plan_organization(classified, args.base_dir)
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
        send_slack_notification(args.notify, f"Dry run complete with {len(plan)} operations.")

    if args.gui:
        launch_gui(plan)

    if args.execute:
        confirm = input("⚠️ Are you sure you want to apply these changes? (y/N): ")
        if confirm.lower() == 'y':
            execute_plan(plan, write_metadata=args.write_metadata)
        else:
            print("❌ Execution cancelled.")
    else:
        print("\nTo proceed, run: python executor.py --execute")
        print("\n⚠️ Dry run complete. Use --execute to apply changes.")

if __name__ == "__main__":
    main()
