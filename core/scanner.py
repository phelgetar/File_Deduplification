#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: scanner.py
# Purpose: Scans filesystem with optional filtering.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.4.4
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.4 (2025-11-06): Corrected filter_names param usage — Tim Canady
###################################################################

from pathlib import Path
from typing import List, Optional

def scan_directory(source: str, filter_names: Optional[List[str]] = None) -> List[Path]:
    base = Path(source)
    all_files = []

    if not base.exists():
        return []

    for path in base.rglob("*"):
        if path.is_file():
            if filter_names:
                if not any(f in str(path) for f in filter_names):
                    continue
            all_files.append(path)

    return all_files
