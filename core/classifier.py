#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: classifier.py
# Purpose: Classify files by MIME type with database persistence
#
# Description:
# Classifies files into categories (image, video, audio, document, other)
# based on MIME type detection. Supports database persistence for
# classification results with confidence scoring.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 1.9.0
# Last Modified: 2026-08-08 by Tim Canady
#
# Revision History:
# - 1.9.0 (2026-08-08): Resume support (skip files already classified in DB); email/message archive extensions (.emlx, .olk14/15*, .ichat) classified by rule instead of falling through to the LLM — Tim Canady
# - 1.8.0 (2026-07-20): Added optional local-LLM (Ollama) fallback for files classified as "other" — Tim Canady
# - 1.7.1 (2025-11-14): Added DICOM medical imaging file extensions (.dcm, .dicom) to scientific category — Tim Canady
# - 1.7.0 (2025-11-14): Added special video subcategories (security_camera_video, wolf_video) with filename pattern detection — Tim Canady
# - 1.6.1 (2025-11-14): Added AI language extensions (.fasl, .lsp, .asd for Lisp; .pro, .prolog for Prolog) — Tim Canady
# - 1.6.0 (2025-11-14): Added backup directory preservation and Xcode project detection (xcode, .xcodeproj, .xcworkspace) — Tim Canady
# - 1.5.0 (2025-11-14): Separated code/scripts directories to use "code" category instead of "application" — Tim Canady
# - 1.4.0 (2025-11-14): CRITICAL FIX - Moved structure-preserving checks to HIGHEST priority (before all other classification) — Tim Canady
# - 1.3.0 (2025-11-14): Added code/scripts directory preservation (scripts, code, src, lib, modules, etc.) — Tim Canady
# - 1.2.0 (2025-11-14): Expanded application category to preserve ALL installer/software directory structures — Tim Canady
# - 1.1.0 (2025-11-14): Added comprehensive disk image formats and Linux installers (.flatpak, .snap, .appimage) — Tim Canady
# - 1.0.0 (2025-11-14): Added application category for PacketTracer and .mpkg support (22 categories total) — Tim Canady
# - 0.9.0 (2025-11-14): Added web category for preserving website directory structures — Tim Canady
# - 0.8.0 (2025-11-14): Added financial category with all Quicken and tax extensions (10+ formats) — Tim Canady
# - 0.7.2 (2025-11-14): Added .qel extension for Quicken application files — Tim Canady
# - 0.7.1 (2025-11-14): Added .wzd extension for Encryption Wizard files — Tim Canady
# - 0.7.0 (2025-11-14): Added education category for course files (CS, CEG, STAT, MAT, etc.) — Tim Canady
# - 0.6.0 (2025-11-12): Enhanced classification with 10 categories including spreadsheet, presentation, archive, data, code — Tim Canady
# - 0.5.0 (2025-11-12): Added database integration for classifications — Tim Canady
# - 0.3.0 (2025-11-06): Changed to return FileInfo instead of dict — Tim Canady
# - 0.1.0 (2025-09-28): Initial classifier implementation — Tim Canady
###################################################################

import mimetypes
import re
import logging

# A PDF, a Word file and a plain-text note are all "documents", but they
# do not belong in the same folder — the single `document` category is
# what put PDFs and .txt files under Docs/Word. Split at classification
# time so the folder map has something specific to key on.
WORD_EXTENSIONS = {".doc", ".docx", ".docm", ".rtf", ".odt", ".pages", ".wpd"}
PDF_EXTENSIONS = {".pdf", ".ps", ".djvu", ".epub", ".mobi", ".azw", ".azw3"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".log", ".readme", ".rst",
                   ".tex", ".nfo"}


# Extensions whose meaning does not depend on where the file sits. A
# JPEG is a photograph in a folder called src just as much as anywhere
# else, and the path-based code/web/application rules run before any
# extension check — which is how photo albums under a folder named src
# were classified as code.
#
# Deliberately excludes .txt, .md, .json, .xml and friends: those really
# are part of a project when they live in one, and keeping them with it
# is right.
UNAMBIGUOUS_EXTENSIONS = {
    # images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    ".heic", ".heif", ".raw", ".cr2", ".nef", ".dng", ".psd",
    # video
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp",
    # audio
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".alac",
    # documents and office
    ".pdf", ".doc", ".docx", ".docm", ".rtf", ".odt", ".pages",
    ".xls", ".xlsx", ".xlsm", ".ods", ".numbers",
    ".ppt", ".pptx", ".pptm", ".key",
    ".epub", ".mobi", ".azw", ".azw3", ".djvu",
}


# Anchored so a two-letter course prefix cannot swallow ordinary words:
# "mat" must be MAT233 or MAT-233, never "matthew-wedding.jpg".
_COURSE_PREFIX = re.compile(
    r"^(cs|ceg|stat|mat|math|econ|phys|chem|bio|eng)[\s._-]?\d", re.IGNORECASE)

# Whole words only. \b around "w2" is what stops sample.rw2 being a tax file.
_FINANCIAL_WORDS = re.compile(
    r"\b(tax|taxes|1040|w2|w-2|1099|quicken|finance|financial|invoice|"
    r"receipt|banking|investment|retirement|401k|ira)\b", re.IGNORECASE)

# .tax2024, .q2023, .t225, .h226 — the digits are the point.
_YEAR_STAMPED_FINANCIAL = re.compile(r"^\.(tax|q|t|h)\d{2,4}$", re.IGNORECASE)


def _document_category(file_extension: str) -> str:
    """Which kind of document this is, defaulting to the generic bucket."""
    ext = (file_extension or "").lower()
    if ext in WORD_EXTENSIONS:
        return "document_word"
    if ext in PDF_EXTENSIONS:
        return "document_pdf"
    if ext in TEXT_EXTENSIONS:
        return "document_text"
    return "document"
from models.file_info import FileInfo
from core import rules

def classify_file(file_info: FileInfo, use_db: bool = False, llm_classifier=None) -> FileInfo:
    """
    Comprehensive file classification based on MIME type and file extension.

    Categories:
    - image, video, audio: Media files
    - document, spreadsheet, presentation: Office/productivity
    - code: Source code and scripts
    - archive: Compressed files
    - data: Structured data (JSON, XML, CSV, databases)
    - font: Font files
    - installer: Installation packages and executables
    - certificate: Security certificates and keys
    - shortcut: Links and shortcuts
    - scientific: Scientific computing files
    - education: Educational course files (CS, CEG, STAT, MAT prefixed files)
    - financial: Financial and tax files (Quicken, TurboTax, TaxAct, H&R Block)
    - web: Web projects and websites (preserve directory structure)
    - application: Installed applications (PacketTracer, etc.) (preserve directory structure)
    - backup: Backup files
    - temporary: Temporary and cache files
    - system: System and configuration files
    - other: Unclassified files
    """
    # Resume support: skip files already classified in a previous run
    # (avoids re-doing rule work and, critically, repeat LLM calls).
    if use_db:
        from core.db import get_classification
        existing = get_classification(file_info.path)
        if existing is not None:
            file_info.type = existing[0]
            logging.debug(f"  ⏩ Already classified ({existing[0]}): {file_info.path.name}")
            return file_info

    mime_type, _ = mimetypes.guess_type(str(file_info.path))
    file_extension = file_info.path.suffix.lower()
    file_name = file_info.path.name.lower()
    file_path_str = str(file_info.path)
    category = "unknown"

    # ====================================================================
    # STRUCTURE-PRESERVING DIRECTORY DETECTION (HIGHEST PRIORITY)
    # These must be checked FIRST before any other classification
    # to ensure complete directory structure is preserved
    # ====================================================================

    # Backup directories (preserve structure - use "backup" category)
    if any(backup_dir in file_path_str.lower() for backup_dir in [
        "/backup/", "/backups/", "/backup_", "/backups_"
    ]):
        category = "backup"

    # Web project directories (preserve structure)
    elif any(web_dir in file_path_str for web_dir in [
        "/http/", "/https/", "/www/", "/website/", "/websites/", "/web/",
        "/html/", "/public_html/", "/htdocs/", "/web-projects/", "/sites/"
    ]):
        category = "web"

    # Code/Scripts directories (preserve structure - use "code" category).
    # Skipped for extensions that mean the same thing anywhere.
    elif file_extension not in UNAMBIGUOUS_EXTENSIONS and any(
        code_dir in file_path_str.lower() for code_dir in [
        "/scripts/", "/script/", "/code/", "/src/", "/source/",
        "/lib/", "/libs/", "/libraries/", "/modules/", "/packages/",
        "/bin/", "/dist/", "/build/", "/out/", "/target/",
        "/xcode/", "xcode", ".xcodeproj", ".xcworkspace"
    ]):
        category = "code"

    # Application and installer directories (preserve structure - use "application" category)
    elif file_extension not in UNAMBIGUOUS_EXTENSIONS and any(
        app_dir in file_path_str.lower() for app_dir in [
        # Installed applications
        "/packettracer/", "/packet tracer/",
        # Common installer/software directory names
        "/installers/", "/installer/", "/software/", "/applications/", "/apps/",
        "/setup/", "/install/", "/programs/", "/program files/",
        # Vendor-specific directories
        "/adobe/", "/microsoft/", "/oracle/", "/vmware/", "/cisco/",
        "/autodesk/", "/corel/", "/intuit/", "/quicken/"
    ]):
        category = "application"

    # ====================================================================
    # STANDARD CLASSIFICATION (only if not in structure-preserving directory)
    # ====================================================================

    # The extension table comes FIRST, and is authoritative.
    #
    # It used to come last, behind MIME, and that ordering was the whole
    # bug: mimetypes calls .py "text/x-python", the startswith("text")
    # branch below claimed it as prose, and the specific text/x-python
    # branch further down could never be reached. 43,701 source files —
    # .java, .html, .js, .c, .py — were filed as documents because of it.
    #
    # config/rules.yaml lists each extension exactly once and derives the
    # --file-types groups and destination folders from the same rows, so
    # the three can no longer disagree the way they did on .py, .rw2
    # and .docm.
    if category == "unknown":
        category = rules.category_for_extension(file_extension)

        # Year-stamped tax and accounting files: .tax2024, .q2023, .t225,
        # .h226. Anchored to digits so .ts and .h are not swept in.
        if category is None and _YEAR_STAMPED_FINANCIAL.match(file_extension):
            category = "financial"

    # MIME type, for extensions the table does not know
    if (category is None or category == "unknown") and mime_type:
        if mime_type.startswith("image"):
            category = "image"
        elif mime_type.startswith("video"):
            category = "video"
        elif mime_type.startswith("audio"):
            category = "audio"
        elif mime_type.startswith("font"):
            category = "font"
        elif mime_type.startswith("text"):
            if mime_type == "text/csv" or file_extension == ".csv":
                category = "spreadsheet"
            else:
                category = _document_category(file_extension)
        elif mime_type in ["application/pdf", "application/msword",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/rtf"]:
            category = _document_category(file_extension)
        elif mime_type in ["application/vnd.ms-excel",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          "text/csv"]:
            category = "spreadsheet"
        elif mime_type in ["application/vnd.ms-powerpoint",
                          "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
            category = "presentation"
        elif mime_type in ["application/zip", "application/x-tar", "application/x-gzip",
                          "application/x-bzip2", "application/x-7z-compressed", "application/x-rar-compressed",
                          "application/x-iso9660-image"]:
            category = "archive"
        elif mime_type in ["application/json", "application/xml", "text/xml"]:
            category = "data"
        elif mime_type in ["application/x-executable", "application/x-mach-binary",
                          "application/x-msdownload"]:
            category = "installer"
        elif mime_type in ["application/x-sh", "text/x-python", "text/x-script"]:
            category = "code"
        else:
            category = None  # Will fall through to extension-based

    # Name and path heuristics, for files whose extension and MIME type
    # both say nothing.
    if category is None or category == "unknown":
        # System files by name (no extension)
        if file_info.path.name in ["CodeResources", "Info.plist", "PkgInfo", "version.plist",
                                     "Makefile", "makefile", "Dockerfile", "Vagrantfile",
                                     "Gemfile", "Rakefile", ".gitignore", ".dockerignore",
                                     "bootstrap", "jquery", "LICENSE", "README", "CHANGELOG"]:
            if file_info.path.name in ["Makefile", "makefile", "Rakefile", "Gemfile"]:
                category = "code"
            else:
                category = "system"

        # Files inside macOS app bundles
        elif "/Contents/MacOS/" in file_path_str and not file_extension:
            category = "installer"
        elif "/Contents/PlugIns/" in file_path_str or "/Contents/Resources/" in file_path_str:
            category = "system"

        # Alias files (macOS)
        elif "alias" in file_name or file_extension == ".alias":
            category = "shortcut"

        # Log files
        elif ".log" in file_name or file_extension in [".log", ".log2"]:
            category = "system"

        # IDE workspace and settings directories
        elif any(pattern in file_path_str for pattern in [
            "/.metadata/", "/.vscode/", "/.idea/", "/.eclipse/", "/.settings/",
            "/workspace/", "/.project", "/.classpath", "/nbproject/"
        ]):
            category = "data"

        # Education files (course prefixes), e.g. CS4850, MATH-233. The
        # prefix must be followed by a digit or separator: plain
        # startswith("mat") also matched "matthew-wedding.jpg", and
        # startswith("bio") matched every "bio.txt".
        elif _COURSE_PREFIX.match(file_name):
            category = "education"

        # Financial files by name or path. Matched on word boundaries: a
        # bare substring test made "w2" fire on sample.rw2 and bmw2, "ira"
        # on any path through a folder named Miranda, and "tax" on
        # syntax.txt. Those only surfaced for files no other rule claimed,
        # but they were still wrong.
        elif _FINANCIAL_WORDS.search(file_name) or _FINANCIAL_WORDS.search(file_path_str.lower()):
            category = "financial"

        else:
            category = "other"

    # Special handling for video subcategories
    if category == "video":
        from config.folder_mapping import detect_video_subcategory
        # Full path, not just the name: the collection is decided by the
        # folders the file sits in.
        video_subcategory = detect_video_subcategory(file_info.path)
        if video_subcategory:
            category = video_subcategory

    # LLM fallback: ask a local model about files nothing else could place
    confidence = 0.8
    if category == "other" and llm_classifier is not None:
        llm_result = llm_classifier.classify(file_info)
        if llm_result and llm_result[0] != "other":
            category, confidence = llm_result
            logging.debug(f"  🦙 LLM classified {file_info.path.name} as '{category}' ({confidence:.2f})")

    # Update the FileInfo object with classification
    file_info.type = category

    # Save classification to database if enabled
    if use_db:
        try:
            from core.db import save_classification
            save_classification(
                file_info.path,
                category=category,
                owner=file_info.owner,
                year=int(file_info.year) if file_info.year else None,
                confidence=confidence
            )
            logging.debug(f"  💾 Saved classification to DB: {file_info.path.name}")
        except Exception as db_err:
            logging.warning(f"  ⚠️ Failed to save classification to DB for {file_info.path}: {db_err}")

    return file_info