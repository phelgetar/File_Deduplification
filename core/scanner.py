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
# Version: 0.7.1
# Last Modified: 2025-11-21 by Tim Canady
#
# Revision History:
# - 0.7.1 (2025-11-21): Added .framework to atomic packages, improved timeout error handling — Tim Canady
# - 0.7.0 (2025-11-14): Added comprehensive disk image support (.iso, .img, .vhd, .vmdk, .vdi, .ova, .ovf, .toast, .cdr, .nrg, .mds, .mdf) — Tim Canady
# - 0.6.2 (2025-11-14): Added .mpkg to atomic package detection — Tim Canady
# - 0.6.1 (2025-11-14): Added hidden file detection (skip files starting with '.') — Tim Canady
# - 0.6.0 (2025-11-14): Added atomic package detection (.app, .pkg, .dmg) to stop scanning internals — Tim Canady
# - 0.5.0 (2025-11-12): Added .dedupignore support with glob patterns — Tim Canady
# - 0.4.0 (2025-11-06): Fixed filter logic for root directories — Tim Canady
# - 0.1.0 (2025-09-28): Initial scanner implementation — Tim Canady
###################################################################

from pathlib import Path
import logging
import os
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

def is_hidden(path):
    """
    Check if a file or directory is hidden (starts with a period).

    Args:
        path: Path object to check

    Returns:
        True if file/directory is hidden, False otherwise
    """
    # Check if the file itself is hidden
    if path.name.startswith('.'):
        return True

    # Check if any parent directory in the path is hidden
    for parent in path.parents:
        if parent.name.startswith('.'):
            return True

    return False


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

def is_atomic_package(path):
    """
    Check if path is an atomic package that should not be scanned internally.

    Atomic packages:
    - .app (macOS application bundles)
    - .framework (macOS framework bundles)
    - .pkg (macOS installer packages)
    - .mpkg (macOS meta-package installers)
    - .dmg, .iso, .img (disk images)
    - .vhd, .vmdk, .vdi (virtual machine disk images)
    - .ova, .ovf (virtual appliances)
    - .toast, .cdr (macOS disk images)
    - .nrg (Nero disk images)
    - .mds, .mdf (Media Descriptor Files)

    Args:
        path: Path object to check

    Returns:
        True if path is an atomic package, False otherwise
    """
    atomic_extensions = {
        '.app', '.framework', '.pkg', '.mpkg',  # macOS packages and frameworks
        '.dmg', '.iso', '.img',                 # Disk images
        '.vhd', '.vmdk', '.vdi',                # VM disk images
        '.ova', '.ovf',                         # Virtual appliances
        '.toast', '.cdr',                       # macOS disk images
        '.nrg',                                 # Nero disk images
        '.mds', '.mdf'                          # Media Descriptor Files
    }
    return path.suffix.lower() in atomic_extensions


def scan_directory(root, filter_names=None, max_files=None, ignore_file=".dedupignore", allowed_extensions=None):
    """
    Scan directory for files, optionally filtering by root-level directory names and file types.

    Treats atomic packages (.app, .framework, .pkg, .mpkg, .dmg) as single units without scanning internals.
    When an atomic package is encountered, it's added to results as a single item and
    all its internal contents are skipped to avoid thousands of unnecessary file scans.

    Args:
        root: Root directory to scan
        filter_names: Optional list of root-level directory names to include
        max_files: Optional maximum number of files to scan
        ignore_file: Path to .dedupignore file (default: .dedupignore)
        allowed_extensions: Optional set of file extensions to include (e.g., {'.jpg', '.png'})
                          If None, all file types are included

    Example:
        HP Easy Start.app will be scanned as one unit at:
        /Users/canadytw/Documents/Installers/HP Easy Start.app

        Rather than scanning all internal files like:
        /Users/canadytw/Documents/Installers/HP Easy Start.app/Contents/MacOS/...

    Args:
        root: Root directory to scan
        filter_names: List of root-level directory names to include (if None, include all)
        max_files: Maximum number of files to return (if None, no limit)
        ignore_file: Path to ignore patterns file (default: .dedupignore)

    Returns:
        List of Path objects for matching files and atomic packages
    """
    results = []
    root_path = Path(root).resolve()

    # Load ignore patterns
    ignore_patterns = load_ignore_patterns(ignore_file)
    ignored_count = 0
    hidden_count = 0
    atomic_package_count = 0

    # Track paths we've already processed to avoid duplicates
    processed_paths = set()

    # If filter_names provided, only scan those subdirectories
    if filter_names:
        # Get direct children of root that match filter
        for filter_name in filter_names:
            filter_path = root_path / filter_name
            if filter_path.exists() and filter_path.is_dir():
                logger.info(f"Scanning filtered directory: {filter_path}")
                try:
                    for dirpath, dirnames, filenames in os.walk(filter_path, topdown=True, onerror=None):
                        try:
                            current_path = Path(dirpath)

                            # Skip hidden directories
                            if is_hidden(current_path):
                                hidden_count += 1
                                dirnames[:] = []  # Don't descend into hidden directories
                                continue

                            # Check directories for atomic packages and filter out problematic ones
                            dirs_to_remove = []
                            for dirname in dirnames[:]:  # Make a copy to iterate
                                dir_path = current_path / dirname

                                # Skip if already processed
                                if dir_path in processed_paths:
                                    dirs_to_remove.append(dirname)
                                    continue

                                # Skip hidden directories
                                if dirname.startswith('.'):
                                    hidden_count += 1
                                    dirs_to_remove.append(dirname)
                                    continue

                                # Check if this is an atomic package
                                if is_atomic_package(dir_path):
                                    # Don't descend into atomic packages
                                    dirs_to_remove.append(dirname)

                                    if should_ignore(dir_path, ignore_patterns):
                                        ignored_count += 1
                                        continue

                                    results.append(dir_path)
                                    processed_paths.add(dir_path)
                                    atomic_package_count += 1
                                    logger.debug(f"  📦 Atomic package: {dir_path.name}")

                                    if max_files and len(results) >= max_files:
                                        logger.info(f"Reached max_files limit. Ignored {ignored_count} files, skipped {hidden_count} hidden files, found {atomic_package_count} atomic packages.")
                                        return results

                            # Remove directories we don't want to descend into
                            for dirname in dirs_to_remove:
                                dirnames.remove(dirname)

                            # Process files in current directory
                            for filename in filenames:
                                try:
                                    file_path = current_path / filename

                                    # Skip if already processed
                                    if file_path in processed_paths:
                                        continue

                                    # Skip hidden files
                                    if filename.startswith('.'):
                                        hidden_count += 1
                                        continue

                                    # Check if file should be ignored
                                    if should_ignore(file_path, ignore_patterns):
                                        ignored_count += 1
                                        continue

                                    # Check file extension filter
                                    if allowed_extensions is not None:
                                        if file_path.suffix.lower() not in allowed_extensions:
                                            continue

                                    results.append(file_path)
                                    processed_paths.add(file_path)

                                    if max_files and len(results) >= max_files:
                                        logger.info(f"Reached max_files limit. Ignored {ignored_count} files, skipped {hidden_count} hidden files, found {atomic_package_count} atomic packages.")
                                        return results

                                except (OSError, TimeoutError, PermissionError) as e:
                                    logger.warning(f"Error accessing file {filename}: {e}")
                                    continue

                        except (OSError, TimeoutError, PermissionError) as e:
                            logger.warning(f"Error accessing directory {dirpath}: {e}")
                            continue

                except (OSError, TimeoutError, PermissionError) as e:
                    logger.warning(f"Error walking {filter_path}: {e}")
                    continue
            else:
                logger.warning(f"Filtered directory does not exist: {filter_path}")
    else:
        # Scan entire root directory using os.walk for better control
        try:
            for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, onerror=None):
                try:
                    current_path = Path(dirpath)

                    # Skip hidden directories
                    if is_hidden(current_path):
                        hidden_count += 1
                        dirnames[:] = []  # Don't descend into hidden directories
                        continue

                    # Check directories for atomic packages and filter out problematic ones
                    dirs_to_remove = []
                    for dirname in dirnames[:]:  # Make a copy to iterate
                        dir_path = current_path / dirname

                        # Skip if already processed
                        if dir_path in processed_paths:
                            dirs_to_remove.append(dirname)
                            continue

                        # Skip hidden directories
                        if dirname.startswith('.'):
                            hidden_count += 1
                            dirs_to_remove.append(dirname)
                            continue

                        # Check if this is an atomic package
                        if is_atomic_package(dir_path):
                            # Don't descend into atomic packages
                            dirs_to_remove.append(dirname)

                            if should_ignore(dir_path, ignore_patterns):
                                ignored_count += 1
                                continue

                            results.append(dir_path)
                            processed_paths.add(dir_path)
                            atomic_package_count += 1
                            logger.debug(f"  📦 Atomic package: {dir_path.name}")

                            if max_files and len(results) >= max_files:
                                return results

                    # Remove directories we don't want to descend into
                    for dirname in dirs_to_remove:
                        dirnames.remove(dirname)

                    # Process files in current directory
                    for filename in filenames:
                        try:
                            file_path = current_path / filename

                            # Skip if already processed
                            if file_path in processed_paths:
                                continue

                            # Skip hidden files
                            if filename.startswith('.'):
                                hidden_count += 1
                                continue

                            # Check if file should be ignored
                            if should_ignore(file_path, ignore_patterns):
                                ignored_count += 1
                                continue

                            # Check file extension filter
                            if allowed_extensions is not None:
                                if file_path.suffix.lower() not in allowed_extensions:
                                    continue

                            results.append(file_path)
                            processed_paths.add(file_path)

                            if max_files and len(results) >= max_files:
                                return results

                        except (OSError, TimeoutError, PermissionError) as e:
                            logger.warning(f"Error accessing file {filename}: {e}")
                            continue

                except (OSError, TimeoutError, PermissionError) as e:
                    logger.warning(f"Error accessing directory {dirpath}: {e}")
                    continue

        except (OSError, TimeoutError, PermissionError) as e:
            logger.error(f"Error walking {root_path}: {e}")
            return results

    if ignored_count > 0:
        logger.info(f"Ignored {ignored_count} files based on .dedupignore patterns")

    if hidden_count > 0:
        logger.info(f"Skipped {hidden_count} hidden files (starting with '.')")

    if atomic_package_count > 0:
        logger.info(f"Found {atomic_package_count} atomic packages (.app, .framework, .pkg, .dmg) treated as single units")

    return results
