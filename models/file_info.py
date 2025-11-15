#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: file_info.py
# Purpose: Data structure to represent file metadata.
#
# Description of code and how it works:
# Used to store and share metadata about each file throughout the
# pipeline: path, size, hash, classification labels, and duplication info.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial version — Tim Canady
###################################################################

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileInfo:
    path: Path
    size: int
    hash: Optional[str] = None
    type: Optional[str] = None
    owner: Optional[str] = None
    year: Optional[str] = None
    is_duplicate: bool = False
    original_path: Optional[Path] = None
    path_metadata: Optional[dict] = None  # Metadata extracted from directory structure