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
# Version: 0.6.0
# Last Modified: 2025-11-14 by Tim Canady
#
# Revision History:
# - 0.6.0 (2025-11-14): Added directory hashing support for atomic packages (.app, .pkg) — Tim Canady
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
from utils.path_metadata import extract_path_metadata

# Read files in 64KB chunks to avoid memory issues
CHUNK_SIZE = 65536


def hash_directory(dir_path):
    """
    Hash an entire directory (atomic package) as a single unit.

    Recursively hashes all files within the directory in a deterministic order
    to create a consistent hash for the entire package.

    Args:
        dir_path: Path to directory to hash

    Returns:
        SHA256 hash of all directory contents
    """
    sha256_hash = hashlib.sha256()

    # Get all files in directory, sorted for deterministic ordering
    all_files = sorted(dir_path.rglob("*"))

    for file_path in all_files:
        # Skip directories themselves, only hash files
        if not file_path.is_file():
            continue

        try:
            # Include relative path in hash for uniqueness
            relative_path = file_path.relative_to(dir_path)
            sha256_hash.update(str(relative_path).encode('utf-8'))

            # Hash file contents
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)

        except (PermissionError, OSError) as e:
            # Include error in hash to maintain consistency
            logging.debug(f"    ⚠️ Could not read {file_path}: {e}")
            sha256_hash.update(f"ERROR:{file_path}".encode('utf-8'))
            continue

    return sha256_hash.hexdigest()

def generate_hashes(file_paths, use_db=False, metadata_only_size=None):
    hashed_files = []

    # Import DB functions only if needed
    if use_db:
        from core.db import cache_file_entry

    for idx, path in enumerate(file_paths, 1):
        try:
            # Log current file being processed
            logging.info(f"  [{idx}/{len(file_paths)}] Processing: {path.name}")

            # Check if this is a directory (atomic package)
            is_directory = path.is_dir()

            if is_directory:
                # This is an atomic package (.app, .pkg, etc.) - hash entire directory
                logging.info(f"    📦 Atomic package detected - hashing entire directory")

                # Calculate total size of all files in directory
                file_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                mtime = datetime.fromtimestamp(path.stat().st_mtime)

                # Check if total size exceeds metadata-only threshold
                is_metadata_only = metadata_only_size is not None and file_size > metadata_only_size

                if is_metadata_only:
                    logging.info(f"    📏 Total package size: {file_size // 1_000_000}MB (metadata-only, skipping hash)")
                    sha256 = "METADATA_ONLY"
                else:
                    if file_size > 10_000_000:
                        logging.info(f"    Large package detected: {file_size // 1_000_000}MB")

                    # Hash entire directory
                    sha256 = hash_directory(path)
                    logging.info(f"    ✅ Package hashed successfully")

            else:
                # Regular file - process normally
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

            # Extract metadata from path structure
            path_metadata = extract_path_metadata(path)

            file_info = FileInfo(
                path=path,
                size=file_size,
                hash=sha256,
                path_metadata=path_metadata
            )
            hashed_files.append(file_info)

            # Log extracted metadata
            if path_metadata and path_metadata.get('tags'):
                logging.debug(f"    🏷️  Path tags: {', '.join(path_metadata['tags'])}")

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