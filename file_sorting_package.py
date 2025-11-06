#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: scanner.py
# Purpose: Walk directories and collect file paths with metadata.
#
# Description of code and how it works:
# Scans all subdirectories recursively and collects information on
# files including path and size. Used for deduplication and classification.
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

import os
from pathlib import Path
from models.file_info import FileInfo


def scan_directory(root_path: Path) -> list[FileInfo]:
    files = []
    for dirpath, _, filenames in os.walk(root_path):
        for name in filenames:
            full_path = Path(dirpath) / name
            try:
                size = full_path.stat().st_size
                files.append(FileInfo(path=full_path, size=size))
            except (FileNotFoundError, PermissionError):
                continue
    return files
