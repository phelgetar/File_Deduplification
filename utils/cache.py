#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: cache.py
# Purpose: JSON-based cache for file hashes
#
# Description:
# Provides local JSON file caching for file hashes to speed up
# re-processing of previously scanned files. Cache is stored in
# .file_dedup_cache.json in the project root.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.5.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.5.0 (2025-11-12): Implemented full JSON-based caching system — Tim Canady
# - 0.1.0 (2025-09-28): Initial stub implementation — Tim Canady
###################################################################

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CACHE_FILE = Path(".file_dedup_cache.json")

def load_cache() -> Dict[str, str]:
    """Load hash cache from disk."""
    if not CACHE_FILE.exists():
        logger.info("No cache file found, starting fresh.")
        return {}

    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            logger.info(f"🔁 Loaded {len(cache)} cached file hashes.")
            return cache
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return {}

def save_cache(cache: Dict[str, str]) -> None:
    """Save hash cache to disk."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
            logger.info(f"💾 Saved {len(cache)} file hashes to cache.")
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")

def get_cached_hash(file_path: Path, cache: Dict[str, str]) -> Optional[str]:
    """Get cached hash for a file if it hasn't been modified."""
    key = str(file_path)
    if key in cache:
        return cache[key]
    return None

def update_cache(file_path: Path, file_hash: str, cache: Dict[str, str]) -> None:
    """Update cache with new file hash."""
    cache[str(file_path)] = file_hash