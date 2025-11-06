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
from models.file_info import FileInfo
from typing import List, Tuple, Dict
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def organize_files(file_infos: list[FileInfo], base_dir: Path) -> dict:
    plan = defaultdict(list)

    for file_info in file_infos:
        category = file_info.type or "Unknown"
        owner = file_info.owner or "Unknown_Owner"
        year = file_info.year or "Unknown_Year"

        target_dir = base_dir / category / owner / year
        plan[target_dir].append(file_info)

    return plan

def plan_organization(
    files: List[FileInfo],
    base_dir: Path
) -> List[Tuple[FileInfo, Path]]:
    """
    Determines target paths for files based on classification results.

    Args:
        files (List[FileInfo]): List of classified files.
        base_dir (Path): The base path where files will be organized.

    Returns:
        List[Tuple[FileInfo, Path]]: Mapping of file to destination path.
    """
    plan = []

    for file_info in files:
        subfolders = []

        # Grouping logic based on metadata
        if file_info.year:
            subfolders.append(str(file_info.year))

        if file_info.type:
            subfolders.append(file_info.type.replace(" ", "_"))

        if file_info.owner:
            subfolders.append(file_info.owner.replace(" ", "_"))

        if not subfolders:
            subfolders.append("Unclassified")

        destination = base_dir.joinpath(*subfolders, file_info.path.name)
        plan.append((file_info, destination))

        logger.debug(f"Planned: {file_info.path} → {destination}")

    return plan
