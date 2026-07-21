#!/usr/bin/env python3

###################################################################
# Project: File_Deduplification
# File: main.py
# Purpose: Application entry point with CLI interface
#
# Description:
# Main entry point for the file deduplication system. Orchestrates
# the complete pipeline: scanning, hashing, classification, organization,
# and execution. Supports database persistence, caching, notifications,
# and GUI preview mode.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.10.0
# Last Modified: 2026-07-20 by Tim Canady
#
# Revision History:
# - 0.10.0 (2026-07-20): Added --llm-classify (local Ollama fallback), --workers/--batch-size (parallel resumable hashing), graceful Ctrl+C handling — Tim Canady
# - 0.9.0 (2025-11-19): Added AI-based tagging for ALL files (not just images); Fixed root_folder double-nesting issue — Tim Canady
# - 0.8.0 (2025-11-15): Added --file-types filter for selective scanning by file type groups — Tim Canady
# - 0.7.0 (2025-11-15): Added AI content tagging with --ai-tagging flag — Tim Canady
# - 0.6.0 (2025-11-15): Added image metadata extraction with --analyze-images flag — Tim Canady
# - 0.5.0 (2025-11-12): Added DB support, input validation, max-files param — Tim Canady
# - 0.4.5 (2025-11-06): Implemented Slack notifications — Tim Canady
# - 0.4.4 (2025-11-06): Restore full CLI and fix scan_directory param — Tim Canady
# - 0.1.0 (2025-09-28): Initial release — Tim Canady
###################################################################

import argparse
from dotenv import load_dotenv
import logging
import sys

logger = logging.getLogger(__name__)
from core.scanner import scan_directory
from core.hasher import generate_hashes
from core.deduplicator import detect_duplicates, filter_duplicates, report_duplicates
from core.classifier import classify_file
from core.organizer import plan_organization
from core.previewer import preview_plan, print_tree_structure
from core.executor import execute_plan
from utils.cache import load_cache, save_cache
from utils.notifications import send_slack_notification
from utils.versioning import get_version
from utils.gui import launch_gui
from pathlib import Path
import os
from datetime import datetime
import json

def parse_size(size_str):
    """Parse human-readable size string to bytes (e.g., '75MB' -> 78643200)"""
    if not size_str:
        return None

    size_str = size_str.upper().strip()
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4
    }

    # Extract number and unit
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}. Use format like: 75MB, 1GB, 500KB")

    number = float(match.group(1))
    unit = match.group(2) if match.group(2) else 'B'

    # Add 'B' if only K, M, G, T specified
    if unit in ['K', 'M', 'G', 'T']:
        unit += 'B'

    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}. Use: B, KB, MB, GB, TB")

    return int(number * units[unit])

def main():
    load_dotenv()

    # Handle --list-file-types early (before requiring other args)
    if '--list-file-types' in sys.argv:
        from utils.file_type_filter import FileTypeFilter
        filter = FileTypeFilter()
        filter.print_available_groups()
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Root source directory")
    parser.add_argument("--base-dir", required=True, help="Base output directory")
    parser.add_argument("--filter", nargs="*", help="Root-level directory name patterns to include")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--dry-run-log", action="store_true", help="Log preview to file")
    parser.add_argument("--log-format", choices=["json", "txt"], default="json")
    parser.add_argument("--notify", choices=["email", "slack"])
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-metadata", action="store_true")
    parser.add_argument("--ignore-errors", action="store_true", help="Skip files with access errors")
    parser.add_argument("--use-db", action="store_true", help="Enable database logging")
    parser.add_argument("--metadata-only-size", type=str, help="Files larger than this size will only have metadata stored (no hashing). Format: 75MB, 1GB, etc. Default: no limit")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel hashing threads (default: 4). Higher values can speed up network volumes; try 8 for a fast NAS.")
    parser.add_argument("--batch-size", type=int, default=500, help="Files per hashing batch checkpoint (default: 500). Each completed file is saved to the DB immediately; batches add periodic progress summaries.")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicate files (only process unique files)")
    parser.add_argument("--duplicate-report", type=str, help="Generate duplicate report and save to file")
    parser.add_argument("--analyze-images", action="store_true", help="Extract and store comprehensive metadata from image files")
    parser.add_argument("--ai-tagging", action="store_true", help="Use AI to automatically identify image content (objects, scenes, people, locations)")
    parser.add_argument("--llm-classify", action="store_true", help="Use a local Ollama LLM to classify files that fall into the 'other' category (requires a running Ollama server; see OLLAMA_HOST/LLM_MODEL in .env)")
    parser.add_argument("--file-types", type=str, help="Filter by file type groups (e.g., 'images', 'media', 'docs', 'word_docs'). Use comma for multiple: 'images,videos'")
    parser.add_argument("--list-file-types", action="store_true", help="List all available file type groups and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Parse file types filter
    allowed_extensions = None
    if args.file_types:
        from utils.file_type_filter import FileTypeFilter, parse_file_types_arg
        filter = FileTypeFilter()
        group_names = parse_file_types_arg(args.file_types)

        if not group_names:
            logging.error(f"❌ Invalid --file-types argument: {args.file_types}")
            sys.exit(1)

        allowed_extensions = filter.get_extensions(group_names)
        if not allowed_extensions:
            logging.info(f"📂 Scanning all file types (no filtering)")
        else:
            logging.info(f"📂 Filtering by file types: {', '.join(group_names)}")
            logging.info(f"   Extensions: {', '.join(sorted(list(allowed_extensions))[:20])}")
            if len(allowed_extensions) > 20:
                logging.info(f"   ... and {len(allowed_extensions) - 20} more")

    # Parse metadata-only size threshold
    metadata_only_size = None
    if args.metadata_only_size:
        try:
            metadata_only_size = parse_size(args.metadata_only_size)
            logging.info(f"📏 Files larger than {args.metadata_only_size} ({metadata_only_size:,} bytes) will be metadata-only")
        except ValueError as e:
            logging.error(f"❌ {e}")
            sys.exit(1)

    # Initialize database if enabled
    if args.use_db:
        try:
            from core.db import init_db
            init_db()
            logging.info("✅ Database initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize database: {e}")
            logging.error("   Check your .env file for correct DATABASE_URL and DB_PASSWORD")
            sys.exit(1)

    # Input validation
    source_path = Path(args.source).resolve()
    base_dir_path = Path(args.base_dir).resolve()

    # Validate source directory
    if not source_path.exists():
        logging.error(f"❌ Source directory does not exist: {source_path}")
        sys.exit(1)

    if not source_path.is_dir():
        logging.error(f"❌ Source path is not a directory: {source_path}")
        sys.exit(1)

    if not os.access(source_path, os.R_OK):
        logging.error(f"❌ Source directory is not readable: {source_path}")
        sys.exit(1)

    # Validate base directory (create if doesn't exist)
    if not base_dir_path.exists():
        # Check if parent directory exists and is writable
        parent_dir = base_dir_path.parent
        if not parent_dir.exists():
            logging.error(f"❌ Parent directory does not exist: {parent_dir}")
            logging.error(f"   Please ensure the parent directory exists before running this command.")
            logging.error(f"   You can create it with: mkdir -p {parent_dir}")
            sys.exit(1)

        if not os.access(parent_dir, os.W_OK):
            logging.error(f"❌ Parent directory is not writable: {parent_dir}")
            logging.error(f"   Please check permissions or choose a different base directory.")
            sys.exit(1)

        try:
            base_dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"✅ Created base directory: {base_dir_path}")
        except Exception as e:
            logging.error(f"❌ Failed to create base directory {base_dir_path}: {e}")
            sys.exit(1)

    if not os.access(base_dir_path, os.W_OK):
        logging.error(f"❌ Base directory is not writable: {base_dir_path}")
        sys.exit(1)

    # Load cache for faster processing
    cache = load_cache()

    print("🔍 Scanning files...")
    files = scan_directory(
        str(source_path),
        filter_names=args.filter,
        max_files=args.max_files,
        allowed_extensions=allowed_extensions
    )
    print(f"🔎 Matched root folders: {set(p.parent for p in files)}")
    print(f"🧮 Files matched: {len(files)}")

    print("🔑 Generating file hashes...")
    try:
        hashed_files = generate_hashes(files, use_db=args.use_db,
                                       metadata_only_size=metadata_only_size,
                                       workers=args.workers,
                                       batch_size=args.batch_size)
    except KeyboardInterrupt:
        print("\n🛑 Run interrupted. All completed hashes are saved"
              + (" in the database — re-run the same command to resume." if args.use_db
                 else ". Enable --use-db to make interrupted runs resumable."))
        sys.exit(130)
    print(f"📂 Files hashed: {len(hashed_files)}")

    print("🔍 Detecting duplicates...")
    hashed_files = detect_duplicates(hashed_files, use_db=args.use_db)

    # Generate duplicate report if requested
    if args.duplicate_report:
        report_duplicates(hashed_files, args.duplicate_report)

    # Filter duplicates if requested
    if args.skip_duplicates:
        hashed_files = filter_duplicates(hashed_files, keep_duplicates=False)
        print(f"📂 Unique files (duplicates filtered): {len(hashed_files)}")
    else:
        unique_count = sum(1 for f in hashed_files if not f.is_duplicate)
        duplicate_count = sum(1 for f in hashed_files if f.is_duplicate)
        print(f"📂 Unique files: {unique_count}, Duplicates: {duplicate_count}")

    # Set up local LLM classification fallback if requested
    llm_classifier = None
    if args.llm_classify:
        from core.llm_client import LLMClassifier
        llm_classifier = LLMClassifier()
        if llm_classifier.is_available():
            print(f"🦙 Local LLM fallback enabled ({llm_classifier.model} @ {llm_classifier.host})")
        else:
            print(f"⚠️  Ollama server not reachable at {llm_classifier.host} — LLM classification skipped.")
            print("   Start it with: ollama serve")
            llm_classifier = None

    print("🤖 Classifying files with AI...")
    classified = [classify_file(f, use_db=args.use_db, llm_classifier=llm_classifier) for f in hashed_files]
    print(f"🔎 Files classified: {len(classified)}")
    if llm_classifier is not None:
        other_count = sum(1 for f in classified if f.type == "other")
        print(f"🦙 LLM resolved {len(llm_classifier._cache)} unique hard-to-classify files; {other_count} remain 'other'")

    # AI-based tagging for ALL files (path-based semantic analysis)
    if args.use_db:
        print("🏷️  Generating AI tags for all files...")
        try:
            from core.ai_tagger import AITagger
            from core.db import save_file_tags

            tagger = AITagger()
            total_tags = 0
            tagged_files = 0

            for file_info in classified:
                try:
                    # Generate tags using AI semantic analysis
                    tags = tagger.generate_tags(file_info)

                    if tags:
                        # Save tags to database
                        saved = save_file_tags(file_info.path, tags, tag_source='ai_tagger', confidence=0.9)
                        if saved > 0:
                            total_tags += saved
                            tagged_files += 1
                            logger.debug(f"✅ Tagged {file_info.path.name} with {saved} tags: {', '.join(tags[:5])}")

                except Exception as e:
                    logger.error(f"Error tagging {file_info.path}: {e}")
                    continue

            print(f"🏷️  Files tagged: {tagged_files}")
            print(f"🏷️  Total tags generated: {total_tags}")

        except ImportError as e:
            print(f"⚠️  AI tagging skipped: {e}")
    elif not args.use_db:
        print("ℹ️  AI tagging requires --use-db flag. Skipping general file tagging.")

    # Analyze images if requested
    if args.analyze_images and args.use_db:
        print("📸 Analyzing image metadata...")
        try:
            from core.image_analyzer import ImageAnalyzer
            from core.image_db import save_image_metadata

            analyzer = ImageAnalyzer()
            analyzed_count = 0
            error_count = 0

            for file_info in classified:
                if analyzer.can_analyze(file_info.path):
                    try:
                        metadata = analyzer.analyze(file_info.path)
                        if metadata:
                            if save_image_metadata(file_info.path, metadata):
                                analyzed_count += 1
                            else:
                                error_count += 1
                    except Exception as e:
                        logger.error(f"Error analyzing {file_info.path}: {e}")
                        error_count += 1

            print(f"📸 Images analyzed: {analyzed_count}")
            if error_count > 0:
                print(f"⚠️  Image analysis errors: {error_count}")

        except ImportError as e:
            print(f"⚠️  Image analysis skipped: {e}")
            print("   Install Pillow with: pip install Pillow")
    elif args.analyze_images and not args.use_db:
        print("⚠️  Image analysis requires --use-db flag. Skipping image analysis.")

    # AI-based content tagging if requested
    if args.ai_tagging and args.use_db:
        print("🤖 AI tagging image content...")
        try:
            from core.image_content_analyzer import ImageContentAnalyzer
            from core.image_analyzer import ImageAnalyzer
            from core.image_db import save_image_metadata, get_image_metadata

            # Check if CLIP is available
            if not ImageContentAnalyzer.is_available():
                print("⚠️  AI tagging requires additional libraries.")
                print("   Install with: pip install torch transformers")
                print("   or: pip install torch torchvision transformers")
            else:
                content_analyzer = ImageContentAnalyzer()
                image_analyzer = ImageAnalyzer()

                tagged_count = 0
                error_count = 0
                total_keywords = 0

                for file_info in classified:
                    if image_analyzer.can_analyze(file_info.path):
                        try:
                            # Get AI-generated keywords
                            keywords = content_analyzer.analyze(file_info.path)

                            if keywords:
                                # Get existing metadata or create minimal metadata
                                metadata = get_image_metadata(file_info.path)

                                if metadata:
                                    # Add AI keywords to existing keywords
                                    existing_keywords = set(metadata.keywords) if metadata.keywords else set()
                                    existing_keywords.update(keywords)
                                    metadata.keywords = sorted(list(existing_keywords))

                                    # Save updated metadata
                                    if save_image_metadata(file_info.path, metadata):
                                        tagged_count += 1
                                        total_keywords += len(keywords)
                                        logger.info(f"✅ Tagged {file_info.path.name} with: {', '.join(keywords)}")

                                        # Also save as file tags for unified tagging system
                                        from core.db import save_file_tags
                                        save_file_tags(file_info.path, keywords, tag_source='image_content', confidence=0.85)
                                else:
                                    # If no metadata exists yet, we need to create it first
                                    # This happens if --analyze-images wasn't used
                                    logger.warning(f"No metadata for {file_info.path.name}, skipping AI tagging (use --analyze-images first)")
                                    error_count += 1

                        except Exception as e:
                            logger.error(f"Error AI tagging {file_info.path}: {e}")
                            error_count += 1

                print(f"🤖 Images AI-tagged: {tagged_count}")
                print(f"🏷️  Total keywords added: {total_keywords}")
                if error_count > 0:
                    print(f"⚠️  AI tagging errors: {error_count}")

        except ImportError as e:
            print(f"⚠️  AI tagging skipped: {e}")
            print("   Install with: pip install torch transformers")
    elif args.ai_tagging and not args.use_db:
        print("⚠️  AI tagging requires --use-db flag. Skipping AI tagging.")

    print("🗂️ Planning folder structure...")
    plan = plan_organization(classified, base_dir_path)
    print(f"📦 Planned operations: {len(plan)}")

    print("🧪 Previewing changes...\n")
    preview_plan(plan)

    print("\nProposed Directory Structure:\n")
    print_tree_structure(plan)

    if args.dry_run_log:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_name = f"dry_run_preview_{timestamp}.{args.log_format}"
        with open(log_name, "w") as f:
            if args.log_format == "json":
                json.dump([str(p) for p in plan], f, indent=2)
            else:
                for op in plan:
                    f.write(str(op) + "\n")
        print(f"📄 Dry run log saved: {log_name}")

    if args.notify:
        message = f"Dry run complete with {len(plan)} operations."
        if args.notify == "slack":
            send_slack_notification(message)
        elif args.notify == "email":
            from utils.notifications import send_email_notification
            send_email_notification("File Deduplication Dry Run", message)

    if args.gui:
        launch_gui(plan)

    if args.execute:
        confirm = input("⚠️ Are you sure you want to apply these changes? (y/N): ")
        if confirm.lower() == 'y':
            execute_plan(plan, write_metadata=args.write_metadata, use_db=args.use_db)
            # Save cache after successful execution
            save_cache(cache)
        else:
            print("❌ Execution cancelled.")
    else:
        print("\n⚠️ Dry run complete. Use --execute to apply changes.")
        print("To proceed, run the same command with --execute flag")

if __name__ == "__main__":
    main()
