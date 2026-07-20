#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: organizer.py
# Purpose: Plan target folder structure based on classified metadata.
#
# Description of code and how it works:
# Generates a dictionary mapping target folder paths to lists of
# files based on file type, owner, and year. Prepares plan for moving.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial organizer logic — Tim Canady
###################################################################

from collections import defaultdict
from pathlib import Path
from models.file_info import FileInfo


def organize_files(file_infos: list[FileInfo], base_dir: Path) -> dict:
    plan = defaultdict(list)

    for file_info in file_infos:
        category = file_info.type or "Unknown"
        owner = file_info.owner or "Unknown_Owner"
        year = file_info.year or "Unknown_Year"

        target_dir = base_dir / category / owner / year
        plan[target_dir].append(file_info)

    return plan
