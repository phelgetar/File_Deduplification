#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: file_type_filter.py
# Purpose: Load and parse file type groups for selective scanning
#
# Description:
# Loads file type groups from YAML configuration and provides
# utilities to filter files by type groups (e.g., images, docs, media).
#
# Author: Tim Canady
# Created: 2025-11-15
#
# Version: 1.0.0
# Last Modified: 2025-11-15 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-15): Initial file type filter utility — Tim Canady
###################################################################

from pathlib import Path
from typing import Set, List, Optional
import yaml
import logging

logger = logging.getLogger(__name__)


class FileTypeFilter:
    """Utility for filtering files by type groups."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize file type filter.

        Args:
            config_path: Path to file_type_groups.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "file_type_groups.yaml"

        self.config = self._load_config(config_path)
        self.groups = self.config.get('file_type_groups', {})

    def _load_config(self, config_path: Path) -> dict:
        """Load file type groups configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded file type groups from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {'file_type_groups': {}}

    def get_extensions(self, group_names: List[str]) -> Set[str]:
        """
        Get all file extensions for given group names.

        Args:
            group_names: List of group names (e.g., ['images', 'videos'])

        Returns:
            Set of file extensions (e.g., {'.jpg', '.png', '.mp4'})
        """
        extensions = set()

        for group_name in group_names:
            group = self.groups.get(group_name)
            if not group:
                logger.warning(f"Unknown file type group: {group_name}")
                continue

            # Check if this group includes other groups
            if 'includes_groups' in group:
                included_groups = group['includes_groups']
                # Recursively get extensions from included groups
                included_extensions = self.get_extensions(included_groups)
                extensions.update(included_extensions)

            # Add direct extensions
            if 'extensions' in group:
                group_extensions = group['extensions']
                extensions.update(group_extensions)

        return extensions

    def list_available_groups(self) -> List[str]:
        """Get list of all available group names."""
        return sorted(list(self.groups.keys()))

    def get_group_description(self, group_name: str) -> Optional[str]:
        """Get description for a group."""
        group = self.groups.get(group_name)
        if group:
            return group.get('description')
        return None

    def print_available_groups(self):
        """Print all available file type groups."""
        print("\n📂 Available File Type Groups:")
        print("=" * 80)

        for group_name in self.list_available_groups():
            description = self.get_group_description(group_name)
            extensions = self.get_extensions([group_name])

            print(f"\n{group_name}")
            print(f"  Description: {description}")
            if extensions:
                ext_list = sorted(list(extensions))
                if len(ext_list) <= 10:
                    print(f"  Extensions: {', '.join(ext_list)}")
                else:
                    print(f"  Extensions: {', '.join(ext_list[:10])}... ({len(ext_list)} total)")
            else:
                print(f"  Extensions: (all files)")

        print("\n" + "=" * 80)
        print("\nUsage: --file-types <group1>,<group2>,...")
        print("Example: --file-types images,videos\n")


def parse_file_types_arg(file_types_str: str) -> List[str]:
    """
    Parse --file-types argument string into list of group names.

    Args:
        file_types_str: Comma-separated list of group names

    Returns:
        List of group names

    Example:
        "images,videos" -> ['images', 'videos']
    """
    if not file_types_str:
        return []

    # Split by comma and strip whitespace
    groups = [g.strip().lower() for g in file_types_str.split(',')]
    return [g for g in groups if g]  # Remove empty strings


if __name__ == "__main__":
    # Test/demo mode
    filter = FileTypeFilter()
    filter.print_available_groups()

    # Test some groups
    print("\n🧪 Testing Groups:")
    print("=" * 80)

    test_groups = ['images', 'media', 'docs', 'word_docs']
    for group in test_groups:
        extensions = filter.get_extensions([group])
        print(f"\n{group}:")
        print(f"  {len(extensions)} extensions")
        if len(extensions) <= 15:
            print(f"  {sorted(list(extensions))}")
