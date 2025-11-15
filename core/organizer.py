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
# Version: 0.3.0
# Last Modified: 2025-11-14 by Tim Canady
#
# Revision History:
# - 0.3.0 (2025-11-14): Added application structure preservation (PacketTracer, etc.) — Tim Canady
# - 0.2.0 (2025-11-14): Added web project structure preservation (http, www, website directories) — Tim Canady
# - 0.1.0 (2025-11-04): Initial organizer logic — Tim Canady
###################################################################

from collections import defaultdict
from models.file_info import FileInfo
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Global variable to store the base scan path for root structure preservation
_base_scan_path: Optional[Path] = None


def set_base_scan_path(path: Path):
    """Set the base scan path for preserving root structure."""
    global _base_scan_path
    _base_scan_path = path.resolve()


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
    base_dir: Path,
    preserve_root_structure: bool = True
) -> List[Tuple[FileInfo, Path]]:
    """
    Determines target paths for files based on classification results.

    Preserves Apple backup root structure (e.g., "Desktop - 2996KD") if enabled.
    Preserves full directory structure for web projects.

    Args:
        files (List[FileInfo]): List of classified files.
        base_dir (Path): The base path where files will be organized.
        preserve_root_structure (bool): If True, preserves root folder names
                                       from source path (e.g., "Desktop - 2996KD")

    Returns:
        List[Tuple[FileInfo, Path]]: Mapping of file to destination path.
    """
    plan = []

    for file_info in files:
        # Special handling for web projects - preserve directory structure
        if file_info.type == "web":
            destination = _plan_web_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (web): {file_info.path} → {destination}")
            continue

        # Special handling for application directories - preserve directory structure
        if file_info.type == "application":
            destination = _plan_application_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (application): {file_info.path} → {destination}")
            continue

        subfolders = []

        # Extract root structure folder if preserving
        root_folder = None
        if preserve_root_structure and file_info.path_metadata:
            root_folder = file_info.path_metadata.get('root_folder')

        # Add root structure folder first (e.g., "Desktop - 2996KD")
        if root_folder:
            subfolders.append(root_folder)

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


def _plan_web_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for web project files, preserving directory structure.

    Example:
        Source: /Users/canadytw/Desktop/http/site1/index.html
        Destination: /organized/Desktop/web/http/site1/index.html

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved web structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the web root directory (http, www, website, etc.)
    file_path_str = str(file_info.path)
    web_roots = ['/http/', '/https/', '/www/', '/website/', '/websites/', '/web/',
                 '/html/', '/public_html/', '/htdocs/', '/web-projects/', '/sites/']

    web_root_found = None
    web_root_idx = -1

    for web_root in web_roots:
        if web_root in file_path_str:
            web_root_found = web_root.strip('/')
            web_root_idx = file_path_str.find(web_root)
            break

    if web_root_found and web_root_idx >= 0:
        # Extract the path from web root onwards
        relative_from_web_root = file_path_str[web_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/web/relative_path
        subfolders = []
        if root_folder:
            subfolders.append(root_folder)
        subfolders.append("web")  # Category folder

        destination = base_dir.joinpath(*subfolders, relative_from_web_root)
    else:
        # Fallback if web root not found
        subfolders = []
        if root_folder:
            subfolders.append(root_folder)
        subfolders.append("web")
        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination


def _plan_application_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for application files, preserving directory structure.

    Example:
        Source: /Users/canadytw/Desktop/PacketTracer/lib/libssl.so.1
        Destination: /organized/Desktop/application/PacketTracer/lib/libssl.so.1

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved application structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the application root directory (packettracer, etc.)
    file_path_str = str(file_info.path).lower()
    app_roots = ['/packettracer/', '/packet tracer/']

    app_root_found = None
    app_root_idx = -1

    for app_root in app_roots:
        if app_root in file_path_str:
            # Get the original case version from the actual path
            actual_path_str = str(file_info.path)
            app_root_idx = file_path_str.find(app_root)
            # Extract the actual directory name from the original path
            app_root_found = actual_path_str[app_root_idx:app_root_idx+len(app_root)].strip('/')
            break

    if app_root_found and app_root_idx >= 0:
        # Extract the path from app root onwards
        relative_from_app_root = str(file_info.path)[app_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/application/relative_path
        subfolders = []
        if root_folder:
            subfolders.append(root_folder)
        subfolders.append("application")  # Category folder

        destination = base_dir.joinpath(*subfolders, relative_from_app_root)
    else:
        # Fallback if app root not found
        subfolders = []
        if root_folder:
            subfolders.append(root_folder)
        subfolders.append("application")
        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination
