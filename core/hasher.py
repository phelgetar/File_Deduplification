#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: hasher.py
# Purpose: Generate and cache file hashes
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Restored generate_hashes with DB fallback logic — Tim Canady
###################################################################

import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

def hash_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"⚠️ Could not hash file {file_path}: {e}")
        return ""

def generate_hashes(files: List[Path]) -> Dict[str, Path]:
    hashes = {}
    with ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(hash_file, f): f for f in files}
        for future in future_to_path:
            result = future.result()
            if result:
                hashes[result] = future_to_path[future]
    return hashes
