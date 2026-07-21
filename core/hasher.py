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
# Version: 0.7.0
# Last Modified: 2026-07-20 by Tim Canady
#
# Revision History:
# - 0.7.0 (2026-07-20): Multithreaded hashing (--workers), batch checkpoints (--batch-size), DB cache resume (skip unchanged already-hashed files), graceful Ctrl+C — Tim Canady
# - 0.6.0 (2025-11-14): Added directory hashing support for atomic packages (.app, .pkg) — Tim Canady
# - 0.5.0 (2025-11-12): Added detailed progress logging and DB integration — Tim Canady
# - 0.4.0 (2025-11-06): Implemented chunked reading for large files — Tim Canady
# - 0.3.0 (2025-11-06): Added FileInfo return type for pipeline consistency — Tim Canady
# - 0.1.0 (2025-09-28): Initial hasher implementation — Tim Canady
###################################################################

import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from models.file_info import FileInfo
from utils.path_metadata import extract_path_metadata

# Read files in 64KB chunks to avoid memory issues
CHUNK_SIZE = 65536

# Defaults for parallel hashing; override via --workers / --batch-size
DEFAULT_WORKERS = 4
DEFAULT_BATCH_SIZE = 500


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

def generate_hashes(file_paths, use_db=False, metadata_only_size=None,
                    workers=DEFAULT_WORKERS, batch_size=DEFAULT_BATCH_SIZE):
    """
    Hash files in parallel batches.

    - Files are processed by a thread pool (hashing is I/O-bound, so threads
      give a real speedup, especially on network volumes).
    - Work proceeds in batches of `batch_size`; each completed file is
      committed to the database immediately (with use_db), so an interrupted
    run loses at most the files in flight.
    - With use_db, files whose path+mtime match a cached entry are skipped
      entirely (no read) — re-running after an interruption resumes where
      the previous run left off.
    """
    total = len(file_paths)
    hashed_files = []
    counter = {"done": 0, "cache_hits": 0}
    counter_lock = threading.Lock()

    # Import DB functions only if needed
    if use_db:
        from core.db import cache_file_entry, get_cached_hash

    def process_one(path):
        try:
            is_directory = path.is_dir()

            if is_directory:
                # Atomic package (.app, .pkg, ...) — hash entire directory
                file_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                # Drop microseconds: MySQL DATETIME truncates them, which would
                # break the mtime equality check on cache lookups
                mtime = datetime.fromtimestamp(path.stat().st_mtime).replace(microsecond=0)
                is_metadata_only = metadata_only_size is not None and file_size > metadata_only_size

                if is_metadata_only:
                    sha256 = "METADATA_ONLY"
                else:
                    logging.debug(f"    📦 Hashing atomic package: {path.name}")
                    sha256 = hash_directory(path)
                from_cache = False
            else:
                stat_info = path.stat()
                file_size = stat_info.st_size
                mtime = datetime.fromtimestamp(stat_info.st_mtime).replace(microsecond=0)
                is_metadata_only = metadata_only_size is not None and file_size > metadata_only_size

                # Resume support: skip files already hashed with unchanged mtime
                sha256 = None
                from_cache = False
                if use_db:
                    try:
                        cached = get_cached_hash(path, mtime)
                        # Ignore a cached METADATA_ONLY marker if the file now
                        # falls under the hashing threshold
                        if cached and not (cached == "METADATA_ONLY" and not is_metadata_only):
                            sha256 = cached
                            from_cache = True
                    except Exception as db_err:
                        logging.debug(f"    Cache lookup failed for {path.name}: {db_err}")

                if sha256 is None:
                    if is_metadata_only:
                        sha256 = "METADATA_ONLY"
                    else:
                        sha256_hash = hashlib.sha256()
                        with open(path, "rb") as f:
                            while True:
                                chunk = f.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                sha256_hash.update(chunk)
                        sha256 = sha256_hash.hexdigest()

            path_metadata = extract_path_metadata(path)
            file_info = FileInfo(path=path, size=file_size, hash=sha256,
                                 path_metadata=path_metadata)

            # Persist immediately so an interrupted run loses nothing
            if use_db and not from_cache:
                try:
                    cache_file_entry(path, file_size, mtime, sha256,
                                     metadata_only=is_metadata_only)
                except Exception as db_err:
                    logging.warning(f"    ⚠️ Failed to write to DB: {db_err}")

            with counter_lock:
                counter["done"] += 1
                if from_cache:
                    counter["cache_hits"] += 1
                idx = counter["done"]
            suffix = " (cached)" if from_cache else ""
            logging.info(f"  [{idx}/{total}] {path.name}{suffix}")
            return file_info

        except PermissionError:
            logging.warning(f"⚠️ Permission denied: {path}")
        except OSError as e:
            logging.warning(f"⚠️ OS error reading {path}: {e}")
        except Exception as e:
            logging.warning(f"⚠️ Skipping {path}: {e}")
        with counter_lock:
            counter["done"] += 1
        return None

    batches = [file_paths[i:i + batch_size] for i in range(0, total, batch_size)]
    logging.info(f"🧵 Hashing with {workers} worker threads in {len(batches)} "
                 f"batch(es) of up to {batch_size} files")

    try:
        for batch_num, batch in enumerate(batches, 1):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(process_one, batch))
            hashed_files.extend(r for r in results if r is not None)
            if len(batches) > 1:
                logging.info(f"💾 Batch {batch_num}/{len(batches)} checkpoint: "
                             f"{len(hashed_files):,}/{total:,} files done"
                             f" ({counter['cache_hits']:,} from cache)")
    except KeyboardInterrupt:
        logging.warning(
            f"🛑 Interrupted during hashing: {counter['done']:,}/{total:,} files "
            f"processed{' and saved to the database' if use_db else ''}. "
            f"Re-run the same command to resume from the cache.")
        raise

    if counter["cache_hits"]:
        logging.info(f"⚡ {counter['cache_hits']:,} files skipped via DB cache "
                     f"(unchanged since last run)")
    logging.info(f"✅ Successfully hashed {len(hashed_files)}/{total} files")
    return hashed_files