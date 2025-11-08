#!/usr/bin/env python3

import hashlib
from pathlib import Path
import logging

HASH_BLOCK_SIZE = 65536

def compute_hash(file_path):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(HASH_BLOCK_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logging.warning(f"⚠️ Skipping {file_path}: {e}")
        return None

def generate_hashes(files):
    unique = {}
    for f in files:
        h = compute_hash(f)
        if not h:
            continue
        if h not in unique:
            unique[h] = f
    return list(unique.values())
