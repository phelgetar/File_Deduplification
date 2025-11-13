#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: hasher.py
# Purpose: Generate SHA256 hashes for files with database caching
#
# Description:
# Hashes files in chunks to avoid memory issues with large files.
# Supports database caching for faster re-processing.
# Provides progress logging for long-running operations.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.5.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.5.0 (2025-11-12): Added detailed progress logging and DB integration — Tim Canady
# - 0.4.0 (2025-11-06): Implemented chunked reading for large files — Tim Canady
# - 0.3.0 (2025-11-06): Added FileInfo return type for pipeline consistency — Tim Canady
# - 0.1.0 (2025-09-28): Initial hasher implementation — Tim Canady
###################################################################

import hashlib
import logging
from pathlib import Path
from datetime import datetime
from models.file_info import FileInfo

# Read files in 64KB chunks to avoid memory issues
CHUNK_SIZE = 65536

def generate_hashes(file_paths, use_db=False, metadata_only_size=None):
    hashed_files = []

    # Import DB functions only if needed
    if use_db:
        from core.db import cache_file_entry

    for idx, path in enumerate(file_paths, 1):
        try:
            # Log current file being processed
            logging.info(f"  [{idx}/{len(file_paths)}] Processing: {path.name}")

            # Get file stats
            stat_info = path.stat()
            file_size = stat_info.st_size
            mtime = datetime.fromtimestamp(stat_info.st_mtime)

            # Check if file exceeds metadata-only threshold
            is_metadata_only = metadata_only_size is not None and file_size > metadata_only_size

            if is_metadata_only:
                # File is too large - store metadata only, skip hashing
                logging.info(f"    📏 File size: {file_size // 1_000_000}MB (metadata-only, skipping hash)")
                sha256 = "METADATA_ONLY"
            else:
                # Log file size for large files
                if file_size > 10_000_000:
                    logging.info(f"    Large file detected: {file_size // 1_000_000}MB")

                # Hash file in chunks to avoid loading large files into memory
                sha256_hash = hashlib.sha256()
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        sha256_hash.update(chunk)

                sha256 = sha256_hash.hexdigest()

            file_info = FileInfo(
                path=path,
                size=file_size,
                hash=sha256
            )
            hashed_files.append(file_info)

            # Write to database if enabled
            if use_db:
                try:
                    logging.info(f"    Writing to database...")
                    cache_file_entry(path, file_size, mtime, sha256, metadata_only=is_metadata_only)
                    logging.info(f"    ✅ Saved to DB")
                except Exception as db_err:
                    logging.warning(f"    ⚠️ Failed to write to DB: {db_err}")

        except PermissionError as e:
            logging.warning(f"⚠️ Permission denied: {path}")
        except OSError as e:
            logging.warning(f"⚠️ OS error reading {path}: {e}")
        except Exception as e:
            logging.warning(f"⚠️ Skipping {path}: {e}")

    logging.info(f"✅ Successfully hashed {len(hashed_files)}/{len(file_paths)} files")
    return hashed_files