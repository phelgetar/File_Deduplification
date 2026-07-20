#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: folder_mapping.py
# Purpose: Custom folder mapping configuration for organized output
#
# Description:
# Maps classification categories to custom folder structures.
# Allows users to define their own organizational hierarchy
# instead of using default category names.
#
# Author: Tim Canady
# Created: 2025-11-14
#
# Version: 1.0.0
# Last Modified: 2025-11-14 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-14): Initial folder mapping configuration — Tim Canady
###################################################################

from pathlib import Path
from typing import Dict, Optional

# Custom folder mapping: category -> relative path
# This maps classification categories to your desired folder structure
CATEGORY_FOLDER_MAP: Dict[str, str] = {
    # Documents
    'document': 'Docs/Word',
    'presentation': 'Docs/PowerPoints',
    'spreadsheet': 'Docs/Spreadsheets',

    # Media
    'image': 'Media/Images',
    'audio': 'Media/Music',
    'video': 'Media/Videos',
    'security_camera_video': 'Media/Videos/SecurityCameraVideos',
    'wolf_video': 'Media/Videos/WolfVids',

    # Code (will preserve internal structure)
    'code': 'Code',

    # Backups (will preserve internal structure)
    'backup': 'Backups',

    # Web (will preserve internal structure)
    'web': 'Web',

    # Applications (will preserve internal structure)
    'application': 'Applications',

    # Other categories
    'archive': 'Archives',
    'installer': 'Installers',
    'certificate': 'Certs',
    'data': 'Data',
    'font': 'Fonts',
    'scientific': 'Scientific',
    'education': 'Education',
    'financial': 'Financial',
    'temporary': 'Temp',
    'system': 'System',
    'shortcut': 'Shortcuts',
    'other': 'Other',
    'unknown': 'Unclassified'
}


def get_custom_folder(category: str) -> Optional[Path]:
    """
    Get the custom folder path for a given category.

    Args:
        category: The classification category

    Returns:
        Path object for the custom folder, or None if no mapping exists
    """
    folder_str = CATEGORY_FOLDER_MAP.get(category)
    if folder_str:
        return Path(folder_str)
    return None


def is_structure_preserving_category(category: str) -> bool:
    """
    Check if a category preserves its internal directory structure.

    Args:
        category: The classification category

    Returns:
        True if the category preserves structure, False otherwise
    """
    structure_preserving = {
        'code', 'backup', 'web', 'application',
        'security_camera_video', 'wolf_video'
    }
    return category in structure_preserving


# Video filename patterns for special categorization
VIDEO_PATTERNS = {
    'security_camera_video': [
        'svr_video_recorder',  # SecurityCameraVideos
        'security_cam',
        'camera_recording'
    ],
    'wolf_video': [
        'clip',  # WolfVids (clip*.mov, clip*)
        'wolf',
        'wolfvid'
    ]
}


def detect_video_subcategory(filename: str) -> Optional[str]:
    """
    Detect if a video file belongs to a special subcategory.

    Args:
        filename: The filename to check (lowercase)

    Returns:
        Special category name if detected, None otherwise
    """
    filename_lower = filename.lower()

    for category, patterns in VIDEO_PATTERNS.items():
        for pattern in patterns:
            if pattern in filename_lower:
                return category

    return None
