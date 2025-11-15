#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: reclassify_files.py
# Purpose: Reclassify existing files in database using updated classifier
#
# Description:
# Reads files from database with specific categories (e.g., "other")
# and re-classifies them using the improved classification system.
# Updates the classifications table without re-scanning files.
#
# Author: Tim Canady
# Created: 2025-11-13
#
# Version: 0.7.1
# Last Modified: 2025-11-13 by Tim Canady
###################################################################

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from core.db import Session, File, Classification, save_classification
from core.classifier import classify_file
from models.file_info import FileInfo

# Load environment variables
load_dotenv()

def reclassify_files(
    categories_to_update=None,
    all_files=False,
    dry_run=False,
    verbose=False,
    skip_cloud=False
):
    """
    Reclassify existing files in the database.

    Args:
        categories_to_update: List of category names to reclassify (e.g., ['other', 'unknown'])
        all_files: If True, reclassify all files regardless of current category
        dry_run: If True, show what would be changed without updating database
        verbose: If True, show detailed progress
        skip_cloud: If True, skip files in cloud storage directories (Google Drive, Dropbox, etc.)
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(message)s'
    )

    # Initialize statistics
    stats = {
        'total_files': 0,
        'files_checked': 0,
        'files_updated': 0,
        'files_unchanged': 0,
        'files_missing': 0,
        'files_skipped': 0,
        'files_error': 0,
        'category_changes': defaultdict(lambda: defaultdict(int))
    }

    # Cloud storage paths to skip if skip_cloud is True
    cloud_paths = [
        'Google Drive',
        'Dropbox',
        'OneDrive',
        'iCloud Drive',
        'Box Sync',
        'Library/CloudStorage'
    ]

    session = Session()

    try:
        # Build query
        query = session.query(File, Classification).join(
            Classification,
            File.id == Classification.file_id,
            isouter=True
        )

        # Filter by categories if specified
        if categories_to_update and not all_files:
            query = query.filter(Classification.category.in_(categories_to_update))

        files_to_process = query.all()
        stats['total_files'] = len(files_to_process)

        if stats['total_files'] == 0:
            logging.info("✅ No files found matching criteria")
            return stats

        logging.info(f"\n{'='*70}")
        logging.info(f"  RECLASSIFICATION {'DRY RUN' if dry_run else 'STARTED'}")
        logging.info(f"{'='*70}")
        logging.info(f"Files to process: {stats['total_files']:,}")
        logging.info(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE UPDATE'}")
        logging.info(f"{'='*70}\n")

        # Process each file
        for idx, (file, classification) in enumerate(files_to_process, 1):
            try:
                stats['files_checked'] += 1
                file_path = Path(file.path)

                # Skip cloud storage files if requested
                if skip_cloud and any(cloud in str(file_path) for cloud in cloud_paths):
                    stats['files_skipped'] += 1
                    if verbose:
                        logging.info(f"[{idx}/{stats['total_files']}] ⏭️  Skipped (cloud): {file_path.name}")
                    continue

                # Check if file still exists (with timeout handling)
                try:
                    if not file_path.exists():
                        stats['files_missing'] += 1
                        if verbose:
                            logging.warning(f"[{idx}/{stats['total_files']}] ⚠️  File not found: {file.path}")
                        continue
                except OSError as e:
                    # Handle timeout, permission denied, etc.
                    stats['files_error'] += 1
                    if verbose:
                        logging.warning(f"[{idx}/{stats['total_files']}] ⚠️  Cannot access: {file_path.name} ({e})")
                    continue

                # Get old category
                old_category = classification.category if classification else 'unknown'

                # Create FileInfo object for classification
                file_info = FileInfo(
                    path=file_path,
                    size=file.size,
                    hash=file.hash
                )

                # Reclassify the file (use extension-only classification for cloud files)
                classified_file = classify_file(file_info, use_db=False)
                new_category = classified_file.type

                # Check if category changed
                if new_category != old_category:
                    stats['files_updated'] += 1
                    stats['category_changes'][old_category][new_category] += 1

                    # Log the change
                    if verbose or (idx % 100 == 0):
                        logging.info(
                            f"[{idx}/{stats['total_files']}] "
                            f"📝 {old_category} → {new_category}: "
                            f"{file_path.name}"
                        )
                    elif idx % 10 == 0:
                        logging.info(f"  Processing... {idx}/{stats['total_files']}")

                    # Update database if not dry run
                    if not dry_run:
                        save_classification(
                            file.path,
                            category=new_category,
                            owner=classification.owner if classification else None,
                            year=classification.year if classification else None,
                            confidence=0.9  # Higher confidence for reclassification
                        )
                else:
                    stats['files_unchanged'] += 1
                    if verbose:
                        logging.debug(
                            f"[{idx}/{stats['total_files']}] "
                            f"✓ Unchanged: {old_category} - {file_path.name}"
                        )

            except KeyboardInterrupt:
                logging.warning(f"\n⚠️  Interrupted at file {idx}/{stats['total_files']}")
                raise
            except Exception as e:
                stats['files_error'] += 1
                logging.warning(f"[{idx}/{stats['total_files']}] ❌ Error: {file_path.name} - {e}")
                continue

        # Print summary
        print_summary(stats, dry_run)

    except Exception as e:
        logging.error(f"\n❌ Error during reclassification: {e}")
        raise
    finally:
        session.close()

    return stats


def print_summary(stats, dry_run):
    """Print summary of reclassification results."""
    print(f"\n{'='*70}")
    print(f"  RECLASSIFICATION {'DRY RUN ' if dry_run else ''}COMPLETE")
    print(f"{'='*70}")
    print(f"\n📊 SUMMARY:")
    print(f"  Total files in database: {stats['total_files']:,}")
    print(f"  Files checked: {stats['files_checked']:,}")
    print(f"  Files updated: {stats['files_updated']:,}")
    print(f"  Files unchanged: {stats['files_unchanged']:,}")
    print(f"  Files missing: {stats['files_missing']:,}")

    if stats.get('files_skipped', 0) > 0:
        print(f"  Files skipped (cloud): {stats['files_skipped']:,}")

    if stats.get('files_error', 0) > 0:
        print(f"  Files with errors: {stats['files_error']:,}")

    if stats['files_updated'] > 0:
        print(f"\n📈 CATEGORY CHANGES:")
        for old_cat, new_cats in sorted(stats['category_changes'].items()):
            print(f"\n  From '{old_cat}':")
            for new_cat, count in sorted(new_cats.items(), key=lambda x: x[1], reverse=True):
                print(f"    → {new_cat}: {count:,} files")

    if dry_run and stats['files_updated'] > 0:
        print(f"\n💡 This was a DRY RUN. Run without --dry-run to apply changes.")

    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Reclassify existing files in database using updated classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reclassify only files currently marked as "other"
  python scripts/reclassify_files.py --categories other

  # Reclassify "other" and "data" files
  python scripts/reclassify_files.py --categories other data

  # Skip cloud storage files (Google Drive, Dropbox, etc.)
  python scripts/reclassify_files.py --categories other --skip-cloud

  # Reclassify all files in database
  python scripts/reclassify_files.py --all

  # Dry run to see what would change
  python scripts/reclassify_files.py --categories other --dry-run

  # Verbose output with cloud files skipped
  python scripts/reclassify_files.py --categories other --skip-cloud --verbose
        """
    )

    parser.add_argument(
        '--categories',
        nargs='+',
        help='Categories to reclassify (e.g., other unknown). Default: other'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Reclassify ALL files in database (ignores --categories)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would change without updating database'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress for each file'
    )

    parser.add_argument(
        '--skip-cloud',
        action='store_true',
        help='Skip files in cloud storage (Google Drive, Dropbox, OneDrive, etc.)'
    )

    args = parser.parse_args()

    # Default to "other" if no categories specified and not --all
    if not args.categories and not args.all:
        args.categories = ['other']

    try:
        # Initialize database
        from core.db import init_db
        init_db()
        logging.info("✅ Database connection established")

        # Run reclassification
        stats = reclassify_files(
            categories_to_update=args.categories if not args.all else None,
            all_files=args.all,
            dry_run=args.dry_run,
            verbose=args.verbose,
            skip_cloud=args.skip_cloud
        )

        # Exit with appropriate code
        if stats['files_updated'] > 0:
            sys.exit(0)  # Success
        else:
            logging.info("ℹ️  No files needed reclassification")
            sys.exit(0)

    except KeyboardInterrupt:
        logging.warning("\n⚠️  Reclassification interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"\n❌ Reclassification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
