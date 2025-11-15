#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: deduplicator.py
# Purpose: Detect and mark duplicate files based on hash comparison
#
# Description:
# Compares file hashes to identify duplicates. Marks duplicates in
# the database and optionally filters them from processing pipeline.
#
# Author: Tim Canady
# Created: 2025-11-13
#
# Version: 0.7.1
# Last Modified: 2025-11-13 by Tim Canady
###################################################################

import logging
from collections import defaultdict
from typing import List
from models.file_info import FileInfo

def detect_duplicates(files: List[FileInfo], use_db: bool = False) -> List[FileInfo]:
    """
    Detect duplicate files based on hash comparison.

    Args:
        files: List of FileInfo objects with hashes
        use_db: If True, mark duplicates in database

    Returns:
        List of FileInfo objects with duplicates marked (is_duplicate=True)
    """
    # Group files by hash
    hash_groups = defaultdict(list)

    for file_info in files:
        # Skip metadata-only files (no hash)
        if file_info.hash == "METADATA_ONLY":
            continue

        hash_groups[file_info.hash].append(file_info)

    # Mark duplicates
    duplicate_count = 0
    unique_count = 0

    for hash_value, file_list in hash_groups.items():
        if len(file_list) > 1:
            # Multiple files with same hash = duplicates
            # Keep first file as original, mark others as duplicates
            original = file_list[0]
            duplicates = file_list[1:]

            unique_count += 1
            duplicate_count += len(duplicates)

            logging.info(f"\n🔍 Found {len(duplicates)} duplicate(s) of: {original.path.name}")
            logging.info(f"   Hash: {hash_value[:16]}...")
            logging.info(f"   Original: {original.path}")

            for dup_file in duplicates:
                dup_file.is_duplicate = True
                dup_file.original_path = original.path

                logging.info(f"   Duplicate: {dup_file.path}")

                # Mark in database if enabled
                if use_db:
                    try:
                        from core.db import mark_duplicate
                        mark_duplicate(str(dup_file.path), str(original.path))
                    except Exception as e:
                        logging.warning(f"   ⚠️ Failed to mark duplicate in DB: {e}")
        else:
            unique_count += 1

    logging.info(f"\n📊 Duplicate Detection Results:")
    logging.info(f"   Unique files: {unique_count}")
    logging.info(f"   Duplicate files: {duplicate_count}")
    logging.info(f"   Total files: {len(files)}")

    return files


def filter_duplicates(files: List[FileInfo], keep_duplicates: bool = False) -> List[FileInfo]:
    """
    Filter out duplicate files from list.

    Args:
        files: List of FileInfo objects with is_duplicate flag set
        keep_duplicates: If True, keep duplicates in list (but marked)

    Returns:
        List of unique files (or all files if keep_duplicates=True)
    """
    if keep_duplicates:
        return files

    unique_files = [f for f in files if not f.is_duplicate]
    removed_count = len(files) - len(unique_files)

    if removed_count > 0:
        logging.info(f"🗑️  Filtered out {removed_count} duplicate files")

    return unique_files


def find_duplicates_by_name(files: List[FileInfo]) -> dict:
    """
    Find files with identical names (may or may not be duplicates by content).

    Args:
        files: List of FileInfo objects

    Returns:
        Dictionary mapping filename to list of paths
    """
    name_groups = defaultdict(list)

    for file_info in files:
        name_groups[file_info.path.name].append(file_info.path)

    # Return only files that have duplicate names
    duplicate_names = {name: paths for name, paths in name_groups.items() if len(paths) > 1}

    if duplicate_names:
        logging.info(f"\n📝 Found {len(duplicate_names)} filename(s) that appear multiple times:")
        for name, paths in duplicate_names.items():
            logging.info(f"   {name}: {len(paths)} occurrences")

    return duplicate_names


def report_duplicates(files: List[FileInfo], output_file: str = None):
    """
    Generate a detailed report of duplicate files.

    Args:
        files: List of FileInfo objects
        output_file: Optional path to save report
    """
    # Group files by hash
    hash_groups = defaultdict(list)

    for file_info in files:
        if file_info.hash != "METADATA_ONLY":
            hash_groups[file_info.hash].append(file_info)

    # Find duplicate groups
    duplicate_groups = {h: files for h, files in hash_groups.items() if len(files) > 1}

    if not duplicate_groups:
        logging.info("✅ No duplicates found!")
        return

    # Generate report
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("                    DUPLICATE FILES REPORT")
    report_lines.append("="*80)
    report_lines.append("")

    total_duplicates = sum(len(files) - 1 for files in duplicate_groups.values())
    total_wasted_space = 0

    for idx, (hash_value, file_list) in enumerate(sorted(duplicate_groups.items()), 1):
        original = file_list[0]
        duplicates = file_list[1:]

        wasted_space = original.size * len(duplicates)
        total_wasted_space += wasted_space

        report_lines.append(f"Duplicate Group #{idx}")
        report_lines.append(f"  Hash: {hash_value}")
        report_lines.append(f"  Size: {original.size:,} bytes ({original.size / 1_048_576:.2f} MB)")
        report_lines.append(f"  Count: {len(file_list)} files")
        report_lines.append(f"  Wasted: {wasted_space:,} bytes ({wasted_space / 1_048_576:.2f} MB)")
        report_lines.append("")
        report_lines.append(f"  Original: {original.path}")
        for dup in duplicates:
            report_lines.append(f"  Duplicate: {dup.path}")
        report_lines.append("")
        report_lines.append("-"*80)
        report_lines.append("")

    report_lines.append("="*80)
    report_lines.append("SUMMARY")
    report_lines.append("="*80)
    report_lines.append(f"Total duplicate groups: {len(duplicate_groups)}")
    report_lines.append(f"Total duplicate files: {total_duplicates}")
    report_lines.append(f"Total wasted space: {total_wasted_space:,} bytes ({total_wasted_space / 1_073_741_824:.2f} GB)")
    report_lines.append("="*80)

    report = "\n".join(report_lines)

    # Print to console
    print("\n" + report)

    # Save to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        logging.info(f"\n📄 Duplicate report saved to: {output_file}")
