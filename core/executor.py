#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: executor.py
# Purpose: Execute file moves and delete exact duplicates.
#
# Description of code and how it works:
# Based on the plan generated, move non-duplicate files to their
# destination folders, and remove duplicate files if flagged.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial executor logic — Tim Canady
###################################################################

import shutil
from pathlib import Path
from models.file_info import FileInfo


def execute_plan(plan: dict[Path, list[FileInfo]], delete_duplicates: bool = True):
    for target_dir, files in plan.items():
        target_dir.mkdir(parents=True, exist_ok=True)

        for fi in files:
            target_path = target_dir / fi.path.name
            if fi.is_duplicate and delete_duplicates:
                try:
                    fi.path.unlink()  # Delete duplicate file
                    print(f"Deleted duplicate: {fi.path}")
                except Exception as e:
                    print(f"Failed to delete {fi.path}: {e}")
            else:
                try:
                    shutil.move(str(fi.path), str(target_path))
                    print(f"Moved: {fi.path} -> {target_path}")
                except Exception as e:
                    print(f"Failed to move {fi.path}: {e}")