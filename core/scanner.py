#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: scanner.py
# Purpose: Scan the root directory and find candidate files for deduplication.
#
# Description:
# Scans directories filtered at the top-level of the root and walks them recursively,
# collecting only files under those matched roots. Supports multiple filters and regex.
# Uses caching to avoid redundant rescans.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.4.0 (2025-11-04): Multi-filter, regex, and caching — Tim Canady
# - 0.3.0 (2025-11-04): Filter now applies to root-level subdirectories only — Tim Canady
# - 0.2.0 (2025-11-04): Multi-threaded collection + filtering — Tim Canady
# - 0.1.0 (2025-09-28): Basic recursive file collector — Tim Canady
###################################################################

import re
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Union
from models.file_info import FileInfo
import concurrent.futures

CACHE_FILE = ".scan_cache.json"

def collect_files_from_root(root: Path) -> List[FileInfo]:
    files = []
    for path in root.rglob("*"):
        if path.is_file():
            try:
                size = path.stat().st_size
                files.append(FileInfo(path=path, size=size))
            except Exception as e:
                print(f"⚠️ Skipped: {path} ({e})")
    return files

def hash_filters(filters: List[str]) -> str:
    return hashlib.md5("|".join(sorted(filters)).encode()).hexdigest()

def load_cache(cache_key: str) -> Optional[List[FileInfo]]:
    if not Path(CACHE_FILE).exists():
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            if cache_key in data:
                return [FileInfo(path=Path(p["path"]), size=p["size"]) for p in data[cache_key]]
    except Exception:
        return None

    return None

def save_cache(cache_key: str, files: List[FileInfo]) -> None:
    try:
        data = {}
        if Path(CACHE_FILE).exists():
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)

        data[cache_key] = [{"path": str(f.path), "size": f.size} for f in files]
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not write scan cache: {e}")

def matches_filters(name: str, filters: List[str]) -> bool:
    return any(re.search(pattern, name, re.IGNORECASE) for pattern in filters)

def scan_directory(source: Path, name_filter: Optional[Union[str, List[str]]] = None) -> List[FileInfo]:
    filters = []
    if isinstance(name_filter, str):
        filters = [name_filter]
    elif isinstance(name_filter, list):
        filters = name_filter

    cache_key = f"{source.resolve()}__{hash_filters(filters)}"
    cached = load_cache(cache_key)
    if cached:
        print("💾 Loaded file list from scan cache.")
        return cached

    matching_roots = []
    for sub in source.iterdir():
        if sub.is_dir():
            if not filters or matches_filters(sub.name, filters):
                matching_roots.append(sub)

    print(f"🔎 Matched root folders: {[str(r) for r in matching_roots]}")

    all_files = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(collect_files_from_root, root) for root in matching_roots]
        for future in concurrent.futures.as_completed(futures):
            all_files.extend(future.result())

    save_cache(cache_key, all_files)
    return all_files