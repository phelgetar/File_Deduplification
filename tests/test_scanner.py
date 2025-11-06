#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: scanner.py
# Purpose: Scans directories recursively and collects file metadata.
#
# Description:
# Recursively walks through directories and returns a list of FileInfo
# objects for actual files only (excluding directories and symlinks).
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial scanner logic — Tim Canady
###################################################################

from pathlib import Path
from typing import List
from models.file_info import FileInfo


def scan_directory(directory: Path) -> List[FileInfo]:
    files = []
    for path in directory.rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                file_info = FileInfo(path=path, size=path.stat().st_size)
                files.append(file_info)
            except Exception as e:
                print(f"⚠️ Skipping {path}: {e}")
    return files
