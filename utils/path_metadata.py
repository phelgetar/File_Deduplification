#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: path_metadata.py
# Purpose: Extract metadata from file path directory structure
#
# Description:
# Extracts meaningful metadata from directory names in the file path.
# For Apple backup structures, preserves root folder names and extracts
# tags from subdirectory names.
#
# Author: Tim Canady
# Created: 2025-11-14
#
# Version: 0.1.0
# Last Modified: 2025-11-14 by Tim Canady
###################################################################

from pathlib import Path
from typing import Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)


def extract_path_metadata(file_path: Path, base_path: Optional[Path] = None) -> Dict:
    """
    Extract metadata from directory structure in the file path.

    Example:
        Path: /Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG

        Returns:
        {
            'root_folder': 'Documents - 2996KD',
            'relative_path': 'Pictures/Land-Pics/8May16',
            'parent_folders': ['Pictures', 'Land-Pics', '8May16'],
            'tags': ['Land-Pics', '8May16'],
            'date_tags': ['8May16'],
            'category_tags': ['Pictures', 'Land-Pics']
        }

    Args:
        file_path: Full path to the file
        base_path: Base directory path to calculate relative path from

    Returns:
        Dictionary containing extracted metadata
    """
    parts = file_path.parts
    metadata = {
        'root_folder': None,
        'relative_path': None,
        'parent_folders': [],
        'tags': [],
        'date_tags': [],
        'category_tags': []
    }

    # Find the root structure folder (e.g., "Documents - 2996KD", "Desktop - Teufelshunde")
    # These typically contain a dash or are standard Apple folders
    apple_folders = {'Desktop', 'Documents', 'Downloads', 'Pictures', 'Movies', 'Music'}
    root_folder_idx = None

    for idx, part in enumerate(parts):
        # Check if this is a root structure folder
        if part in apple_folders:
            root_folder_idx = idx
            metadata['root_folder'] = part
            break
        # Check for Apple backup style (e.g., "Desktop - 2996KD")
        elif ' - ' in part and any(apple in part for apple in apple_folders):
            root_folder_idx = idx
            metadata['root_folder'] = part
            break

    # Extract parent folders (everything between root and filename)
    if root_folder_idx is not None and root_folder_idx < len(parts) - 1:
        parent_folders = parts[root_folder_idx + 1:-1]  # Exclude root and filename
        metadata['parent_folders'] = list(parent_folders)
        metadata['relative_path'] = '/'.join(parent_folders)

        # Extract tags from parent folders
        for folder in parent_folders:
            # Skip generic folder names
            if folder.lower() in {'files', 'data', 'stuff', 'misc', 'other', 'folder'}:
                continue

            metadata['tags'].append(folder)

            # Check if folder looks like a date (e.g., "8May16", "2024-01-15")
            if is_date_like(folder):
                metadata['date_tags'].append(folder)
            else:
                metadata['category_tags'].append(folder)

    return metadata


def is_date_like(text: str) -> bool:
    """
    Check if a text string looks like a date.

    Patterns:
    - 8May16, 15Dec24
    - 2024-01-15, 01-15-2024
    - 20240115
    - Jan2024, December2023

    Args:
        text: String to check

    Returns:
        True if text appears to be a date
    """
    # Common date patterns
    patterns = [
        r'\d{1,2}[A-Za-z]{3}\d{2,4}',  # 8May16, 15Dec2024
        r'\d{4}-\d{2}-\d{2}',          # 2024-01-15
        r'\d{2}-\d{2}-\d{4}',          # 01-15-2024
        r'\d{8}',                      # 20240115
        r'[A-Za-z]{3,9}\d{4}',         # Jan2024, December2023
        r'\d{4}[A-Za-z]{3,9}',         # 2024Jan
    ]

    for pattern in patterns:
        if re.match(pattern, text):
            return True

    return False


def format_metadata_tags(metadata: Dict) -> str:
    """
    Format metadata tags as a readable string.

    Args:
        metadata: Metadata dictionary from extract_path_metadata()

    Returns:
        Formatted string of tags
    """
    tags = []

    if metadata.get('root_folder'):
        tags.append(f"Root: {metadata['root_folder']}")

    if metadata.get('category_tags'):
        tags.append(f"Categories: {', '.join(metadata['category_tags'])}")

    if metadata.get('date_tags'):
        tags.append(f"Dates: {', '.join(metadata['date_tags'])}")

    return ' | '.join(tags)


def extract_owner_from_path(file_path: Path) -> Optional[str]:
    """
    Extract owner/device identifier from path.

    Looks for patterns like:
    - "Desktop - 2996KD" → "2996KD"
    - "Documents - Teufelshunde" → "Teufelshunde"
    - "Photos - iPhone" → "iPhone"

    Args:
        file_path: Full path to the file

    Returns:
        Owner/device identifier or None
    """
    parts = file_path.parts

    for part in parts:
        # Look for "FolderName - Identifier" pattern
        if ' - ' in part:
            # Split on the dash
            components = part.split(' - ')
            if len(components) >= 2:
                # Return everything after the first dash
                return ' - '.join(components[1:])

    return None


def preserve_root_structure(file_path: Path, base_scan_path: Path) -> Optional[str]:
    """
    Identify the root structure folder that should be preserved.

    Example:
        file_path: /Users/canadytw/Documents/Documents - 2996KD/Pictures/file.jpg
        base_scan_path: /Users/canadytw/Documents

        Returns: "Documents - 2996KD"

    Args:
        file_path: Full path to the file
        base_scan_path: Base path that was scanned

    Returns:
        Root folder name to preserve, or None
    """
    try:
        # Get relative path from base
        rel_path = file_path.relative_to(base_scan_path)

        # First component is the root structure folder
        if rel_path.parts:
            return rel_path.parts[0]
    except ValueError:
        # file_path is not relative to base_scan_path
        pass

    return None


# Example usage and testing
if __name__ == "__main__":
    # Test examples
    test_paths = [
        Path("/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG"),
        Path("/Users/canadytw/Desktop/Desktop - Teufelshunde/Projects/CS101/Assignment1/main.py"),
        Path("/Users/canadytw/Documents/Documents - 42739/Work/Reports/2024-Q1/report.pdf"),
    ]

    for path in test_paths:
        print(f"\nPath: {path}")
        metadata = extract_path_metadata(path)
        print(f"Metadata: {metadata}")
        print(f"Formatted: {format_metadata_tags(metadata)}")
        print(f"Owner: {extract_owner_from_path(path)}")
