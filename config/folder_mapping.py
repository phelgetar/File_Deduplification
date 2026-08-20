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
    # Documents. 'document' is the generic fallback and must NOT be
    # Docs/Word — that is what filed every PDF and .txt under Word.
    'document': 'Docs',
    'document_word': 'Docs/Word',
    'document_pdf': 'Docs/PDF',
    'document_text': 'Docs/Text',
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
# Matched against the file's DIRECTORY names, not its filename.
#
# These were filename substrings, and 'clip' appears in an enormous range
# of ordinary video names — "vacation-clip.mov" was being filed as a wolf
# video. A directory is a deliberate act of organisation; a substring of a
# filename is a coincidence.
VIDEO_PATTERNS = {
    'security_camera_video': [
        'securitycameravideos', 'security_cam', 'securitycam',
        'svr_video_recorder', 'camera_recording',
    ],
    'wolf_video': [
        'wolfvids', 'wolf_vids', 'wolfvid',
    ]
}


def detect_video_subcategory(path_or_name) -> Optional[str]:
    """Which special video collection this file belongs to, if any.

    Decided by the folders the file sits in rather than by its name.
    Accepts a full path; a bare filename simply matches nothing, which
    is the safe answer.
    """
    directories = {part.lower().replace(" ", "").replace("-", "_")
                   for part in Path(str(path_or_name)).parts[:-1]}
    if not directories:
        return None

    for category, patterns in VIDEO_PATTERNS.items():
        for pattern in patterns:
            if pattern in directories:
                return category
    return None
