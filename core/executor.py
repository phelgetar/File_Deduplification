#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: executor.py
# Purpose: Execute file organization plan with robust error handling
#
# Description:
# Executes the file organization plan by copying files to target
# destinations. Provides comprehensive error handling, validation,
# database logging, and metadata sidecar file generation.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.6.0
# Last Modified: 2026-07-20 by Tim Canady
#
# Revision History:
# - 0.6.0 (2026-07-20): Fail fast if the DB circuit breaker trips mid-execution — stop before the next file move rather than continue unlogged — Tim Canady
# - 0.5.0 (2025-11-12): Added DB logging and improved error handling — Tim Canady
# - 0.4.3 (2025-11-06): Basic file operation logger added — Tim Canady
# - 0.1.0 (2025-09-28): Initial executor implementation — Tim Canady
###################################################################

import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from models.file_info import FileInfo

logger = logging.getLogger(__name__)

def execute_plan(plan: List[Tuple[FileInfo, Path]], write_metadata: bool = False, use_db: bool = False) -> None:
    """
    Execute the file organization plan.

    Args:
        plan: List of tuples containing (FileInfo, destination_path)
        write_metadata: Whether to write metadata to moved files
        use_db: Whether to log operations to database
    """
    success_count = 0
    error_count = 0

    # Import DB function if needed
    if use_db:
        from core.db import log_operation, is_db_down

    for file_info, dest in plan:
        # Fail fast: if the database died mid-execution, stop cleanly before
        # the next move rather than continue with unlogged operations.
        if use_db and is_db_down():
            logger.error(
                "🛑 Database connection lost mid-execution (circuit breaker "
                "tripped). Stopping before the next file operation — "
                f"{success_count} operations completed and logged so far. "
                "Restore the database and re-run to continue; already-copied "
                "files are skipped automatically (destination exists).")
            break
        src = file_info.path
        try:
            # Validate source file exists
            if not src.exists():
                logger.error(f"Source file does not exist: {src}")
                error_count += 1
                continue

            # Create destination directory
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Check if destination already exists
            if dest.exists():
                logger.warning(f"Destination already exists, skipping: {dest}")
                continue

            # Copy with metadata preserved. Atomic packages (.app,
            # .framework, bundle-style .pkg) are directories, and the
            # scanner deliberately hands them over whole rather than
            # descending into them — so copy2 would raise IsADirectoryError
            # and the bundle would silently never arrive.
            #
            # symlinks=True is load-bearing for macOS bundles: a
            # .framework's Versions/Current is a symlink, and resolving
            # it instead of copying it both duplicates the payload and
            # produces a bundle that no longer matches the original.
            if src.is_dir():
                shutil.copytree(src, dest, symlinks=True)
                logger.info(f"✅ Copied bundle: {src} -> {dest}")
            else:
                shutil.copy2(src, dest)
                logger.info(f"✅ Copied: {src} -> {dest}")
            success_count += 1

            # Log operation to database if enabled
            if use_db:
                try:
                    log_operation(src, 'MOVE', dest)
                    logger.debug(f"  💾 Logged operation to DB")
                except Exception as db_err:
                    logger.warning(f"  ⚠️ Failed to log operation to DB: {db_err}")

            # Optionally write metadata
            if write_metadata:
                try:
                    write_file_metadata(dest, file_info)
                except Exception as meta_err:
                    logger.warning(f"Failed to write metadata for {dest}: {meta_err}")

        except PermissionError as e:
            logger.error(f"❌ Permission denied: {src} -> {dest}: {e}")
            error_count += 1
        except OSError as e:
            logger.error(f"❌ OS error moving {src} -> {dest}: {e}")
            error_count += 1
        except Exception as e:
            logger.error(f"❌ Unexpected error moving {src} -> {dest}: {e}")
            error_count += 1

    # Summary
    logger.info(f"\n📊 Execution Summary:")
    logger.info(f"   ✅ Successful: {success_count}")
    logger.info(f"   ❌ Failed: {error_count}")
    logger.info(f"   📂 Total: {len(plan)}")

def write_file_metadata(file_path: Path, file_info: FileInfo) -> None:
    """
    Write metadata to a sidecar file.

    Args:
        file_path: Path to the file
        file_info: FileInfo object containing metadata
    """
    import json

    metadata = {
        "original_path": str(file_info.path),
        "hash": file_info.hash,
        "size": file_info.size,
        "type": file_info.type,
        "owner": file_info.owner,
        "year": file_info.year,
        "is_duplicate": file_info.is_duplicate,
        "path_metadata": file_info.path_metadata  # Include extracted path metadata
    }

    metadata_path = file_path.with_suffix(file_path.suffix + ".meta.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.debug(f"Written metadata to {metadata_path}")

    # Log path metadata if present
    if file_info.path_metadata and file_info.path_metadata.get('tags'):
        logger.debug(f"  Tags: {', '.join(file_info.path_metadata['tags'])}")
