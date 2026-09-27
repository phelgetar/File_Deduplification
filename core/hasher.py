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
import os
import stat
import logging
from collections import defaultdict
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


# Files at or above this size get a cheap sample first. Below it the
# whole file is roughly one or two reads anyway, so sampling would cost
# an extra seek to save nothing.
SAMPLE_THRESHOLD = 4 * 1024 * 1024        # 4 MB
SAMPLE_EDGE = 65536                        # 64 KB from each end


def sample_hash(path, size):
    """SHA-256 of the first 64 KB, the last 64 KB and the size.

    Two files differing at either end, or in length, cannot be
    identical, so only files colliding here need the full read. The
    size goes into the digest so a short file cannot collide with a
    long one whose ends happen to match.

    Returns None when the file is too small to be worth sampling, or
    unreadable; callers fall back to a full hash.
    """
    if size < SAMPLE_THRESHOLD:
        return None
    digest = hashlib.sha256()
    digest.update(str(size).encode())
    try:
        with open(path, "rb") as handle:
            digest.update(handle.read(SAMPLE_EDGE))
            if size > SAMPLE_EDGE * 2:
                handle.seek(-SAMPLE_EDGE, os.SEEK_END)
                digest.update(handle.read(SAMPLE_EDGE))
    except OSError:
        return None
    return digest.hexdigest()


def _walk_no_links(dir_path):
    """Every regular file under dir_path, never crossing a symlink."""
    for dirpath, dirnames, filenames in os.walk(dir_path, followlinks=False):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
        for name in filenames:
            candidate = here / name
            if not candidate.is_symlink() and candidate.is_file():
                yield candidate


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

    # Walk without following symlinks.
    #
    # rglob("*") follows them, so hashing a directory could leave that
    # directory entirely. That is how 488 sandbox container links to one
    # Pictures library were each read as a 44 GB object: 21.47 TB of the
    # 25.77 TB that scan read. os.walk defaults to followlinks=False.
    all_files = []
    for dirpath, dirnames, filenames in os.walk(dir_path, followlinks=False):
        here = Path(dirpath)
        # Prune symlinked subdirectories too: os.walk lists them even
        # though it will not descend, and we must not stat through them.
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
        for name in filenames:
            candidate = here / name
            if not candidate.is_symlink():
                all_files.append(candidate)
    all_files.sort()

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

def _sample_seen_elsewhere(size, sample, path):
    """Does the database already know another file with these ends?

    Without this the optimisation is a correctness bug across runs: a
    file that is the only one of its shape today gets no full hash, and
    when its twin is scanned next month there is nothing to compare it
    to. One indexed lookup (idx_files_sample_hash) buys that back.
    """
    try:
        from core.db import sample_hash_exists
        return sample_hash_exists(size, sample, str(path))
    except Exception:
        # Cannot prove it is unique, so do not skip the read.
        return True


def sample_prefilter(file_paths, workers, metadata_only_size=None,
                     use_db=False):
    """Paths big enough to sample that provably have no duplicate.

    Returns {path: sample_hash}. A file whose first 64 KB, last 64 KB
    and size match nothing else cannot be byte-identical to anything,
    so reading the middle of it proves nothing. On a NAS that middle is
    the entire cost.

    Small files are left alone: below a few megabytes the whole file is
    one or two reads anyway, and the extra seek would cost more than it
    saves.
    """
    candidates = []
    for path in file_paths:
        try:
            if path.is_symlink():
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                continue
            size = info.st_size
        except OSError:
            continue
        if size < SAMPLE_THRESHOLD:
            continue
        if metadata_only_size is not None and size > metadata_only_size:
            continue
        candidates.append((path, size))

    if not candidates:
        return {}

    def _one(item):
        path, size = item
        return path, size, sample_hash(path, size)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        sampled = list(pool.map(_one, candidates))

    groups = defaultdict(list)
    for path, size, digest in sampled:
        if digest:
            groups[(size, digest)].append(path)

    unique = {}
    for (size, digest), members in groups.items():
        if len(members) != 1:
            continue
        if use_db and _sample_seen_elsewhere(size, digest, members[0]):
            continue
        unique[members[0]] = digest

    if unique:
        saved = sum(p.lstat().st_size for p in unique if p.exists())
        logging.info(f"🔎 {len(unique):,} large files are unique by their first "
                     f"and last 64 KB, so the full read is unnecessary "
                     f"({saved / 1e9:.1f} GB not read)")
    return unique


def generate_hashes(file_paths, use_db=False, metadata_only_size=None,
                    workers=DEFAULT_WORKERS, batch_size=DEFAULT_BATCH_SIZE,
                    sample_first=True):
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

    # Two-tier hashing: sample the ends of every large file first, and
    # skip the full read for those that already prove unique.
    sample_unique = {}
    if sample_first and file_paths:
        try:
            sample_unique = sample_prefilter(file_paths, workers,
                                             metadata_only_size, use_db)
        except Exception as e:
            logging.warning(f"⚠️ Sample prefilter failed, hashing everything "
                            f"in full: {e}")
            sample_unique = {}

    def process_one(path):
        try:
            is_directory = path.is_dir()

            if is_directory:
                # Atomic package (.app, .pkg, ...) — hash entire directory
                # Same reason as hash_directory: never size through a link.
                file_size = sum(f.stat().st_size for f in _walk_no_links(path))
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
                dev = inode = None
                sample = None
            else:
                # lstat, not stat: the scanner already excluded symlinks,
                # and lstat cannot be tricked into describing a target.
                stat_info = path.lstat()
                file_size = stat_info.st_size
                # Device + inode. Two paths sharing both are one file on
                # disk (hardlink, or an APFS clone), so they are not two
                # copies and deleting one reclaims nothing.
                dev, inode = stat_info.st_dev, stat_info.st_ino
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

                sample = None
                if sha256 is None:
                    if is_metadata_only:
                        sha256 = "METADATA_ONLY"
                    elif path in sample_unique:
                        # Nothing else shares this file's ends and length,
                        # so it cannot be byte-identical to anything and
                        # the middle need never be read.
                        sample = sample_unique[path]
                        sha256 = "SAMPLE_ONLY"
                    else:
                        sample = sample_hash(path, file_size)
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
            file_info.dev = dev
            file_info.inode = inode
            file_info.sample_hash = sample

            # Persist immediately so an interrupted run loses nothing
            if use_db and not from_cache:
                try:
                    cache_file_entry(path, file_size, mtime, sha256,
                                     metadata_only=is_metadata_only,
                                     dev=dev, inode=inode, sample=sample)
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