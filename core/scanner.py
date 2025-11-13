#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: scanner.py
# Purpose: Scan directories for files with ignore pattern support
#
# Description:
# Scans directories recursively, respecting .dedupignore patterns.
# Supports glob patterns (*.tmp), absolute paths, and wildcards.
# Provides filtering by root-level directory names.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.5.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.5.0 (2025-11-12): Added .dedupignore support with glob patterns — Tim Canady
# - 0.4.0 (2025-11-06): Fixed filter logic for root directories — Tim Canady
# - 0.1.0 (2025-09-28): Initial scanner implementation — Tim Canady
###################################################################

from pathlib import Path
import logging
from fnmatch import fnmatch

logger = logging.getLogger(__name__)

def load_ignore_patterns(ignore_file=".dedupignore"):
    """
    Load ignore patterns from .dedupignore file.

    Supports:
    - Glob patterns (*.tmp, *.mp4)
    - Absolute paths (/Users/canadytw/.viminfo)
    - Path patterns with wildcards (/Users/canadytw/Library/Caches*)

    Args:
        ignore_file: Path to the ignore file (default: .dedupignore)

    Returns:
        List of patterns to ignore
    """
    patterns = []
    ignore_path = Path(ignore_file)

    if not ignore_path.exists():
        logger.debug(f"No {ignore_file} file found")
        return patterns

    try:
        with open(ignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    patterns.append(line)

        logger.info(f"Loaded {len(patterns)} ignore patterns from {ignore_file}")
    except Exception as e:
        logger.warning(f"Failed to read {ignore_file}: {e}")

    return patterns

def should_ignore(file_path, ignore_patterns):
    """
    Check if a file should be ignored based on patterns.

    Args:
        file_path: Path object to check
        ignore_patterns: List of patterns from .dedupignore

    Returns:
        True if file should be ignored, False otherwise
    """
    file_str = str(file_path)
    file_name = file_path.name

    for pattern in ignore_patterns:
        # Check absolute path patterns
        if pattern.startswith('/'):
            # Handle wildcard at end (e.g., /path/to/dir*)
            if pattern.endswith('*'):
                if file_str.startswith(pattern[:-1]):
                    return True
            # Exact absolute path match
            elif file_str == pattern:
                return True
        # Check glob patterns (*.tmp, *.mp4, etc.)
        elif fnmatch(file_name, pattern):
            return True

    return False

def scan_directory(root, filter_names=None, max_files=None, ignore_file=".dedupignore"):
    """
    Scan directory for files, optionally filtering by root-level directory names.

    Args:
        root: Root directory to scan
        filter_names: List of root-level directory names to include (if None, include all)
        max_files: Maximum number of files to return (if None, no limit)
        ignore_file: Path to ignore patterns file (default: .dedupignore)

    Returns:
        List of Path objects for matching files
    """
    results = []
    root_path = Path(root).resolve()

    # Load ignore patterns
    ignore_patterns = load_ignore_patterns(ignore_file)
    ignored_count = 0

    # If filter_names provided, only scan those subdirectories
    if filter_names:
        # Get direct children of root that match filter
        for filter_name in filter_names:
            filter_path = root_path / filter_name
            if filter_path.exists() and filter_path.is_dir():
                logger.info(f"Scanning filtered directory: {filter_path}")
                for p in filter_path.rglob("*"):
                    if p.is_file():
                        # Check if file should be ignored
                        if should_ignore(p, ignore_patterns):
                            ignored_count += 1
                            continue

                        results.append(p)
                        if max_files and len(results) >= max_files:
                            logger.info(f"Reached max_files limit. Ignored {ignored_count} files based on patterns.")
                            return results
            else:
                logger.warning(f"Filtered directory does not exist: {filter_path}")
    else:
        # Scan entire root directory
        for p in root_path.rglob("*"):
            if p.is_file():
                # Check if file should be ignored
                if should_ignore(p, ignore_patterns):
                    ignored_count += 1
                    continue

                results.append(p)
                if max_files and len(results) >= max_files:
                    break

    if ignored_count > 0:
        logger.info(f"Ignored {ignored_count} files based on .dedupignore patterns")

    return results
