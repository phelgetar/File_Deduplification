#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: hasher.py
# Purpose: Generate file hashes to detect exact duplicates.
#
# Description of code and how it works:
# Uses SHA-256 content hashing to find files with identical content.
# Flags duplicates for later removal.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial hashing logic — Tim Canady
###################################################################

import hashlib
from pathlib import Path
from models.file_info import FileInfo
from concurrent.futures import ThreadPoolExecutor, as_completed


def hash_file(file_path: Path, block_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (FileNotFoundError, PermissionError):
        return ""


def generate_hashes(file_infos: list[FileInfo], max_threads: int = 8) -> list[FileInfo]:
    hash_map = {}
    results = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_map = {executor.submit(hash_file, fi.path): fi for fi in file_infos}
        for future in as_completed(future_map):
            file_info = future_map[future]
            file_hash = future.result()
            file_info.hash = file_hash
            if file_hash and file_hash in hash_map:
                file_info.is_duplicate = True
                file_info.original_path = hash_map[file_hash].path
            elif file_hash:
                hash_map[file_hash] = file_info
            results.append(file_info)
    return results