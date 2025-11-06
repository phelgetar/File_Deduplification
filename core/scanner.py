#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: scanner.py
# Purpose: Scan directories and collect files based on filters
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.3
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.3 (2025-11-06): Reinstated scan_directory and added filter matching — Tim Canady
###################################################################

from pathlib import Path
from typing import List, Union, Optional
import fnmatch

def scan_directory(
    source_dir: Union[str, Path],
    filters: Optional[List[str]] = None,
    recursive: bool = True
) -> List[Path]:
    matched_files = []
    source_path = Path(source_dir)

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    dirs_to_scan = [p for p in source_path.iterdir() if p.is_dir()]

    if filters:
        dirs_to_scan = [d for d in dirs_to_scan if any(fnmatch.fnmatch(d.name, f"*{f}*") for f in filters)]

    for directory in dirs_to_scan:
        files = list(directory.rglob("*")) if recursive else list(directory.glob("*"))
        matched_files.extend(f for f in files if f.is_file())

    return matched_files
