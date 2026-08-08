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
import logging
from models.file_info import FileInfo

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

    # Code/Scripts directories (preserve structure - use "code" category)
    elif any(code_dir in file_path_str.lower() for code_dir in [
        "/scripts/", "/script/", "/code/", "/src/", "/source/",
        "/lib/", "/libs/", "/libraries/", "/modules/", "/packages/",
        "/bin/", "/dist/", "/build/", "/out/", "/target/",
        "/xcode/", "xcode", ".xcodeproj", ".xcworkspace"
    ]):
        category = "code"

    # Application and installer directories (preserve structure - use "application" category)
    elif any(app_dir in file_path_str.lower() for app_dir in [
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

    # MIME type based classification
    if category == "unknown" and mime_type:
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
            elif file_extension in [".txt", ".md", ".log", ".readme"]:
                category = "document"
            else:
                category = "document"
        elif mime_type in ["application/pdf", "application/msword",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/rtf"]:
            category = "document"
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

    # Extension-based classification (if MIME type didn't match or wasn't found)
    if category is None or category == "unknown":
        # Images
        if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".tif",
                             ".ico", ".heic", ".heif", ".raw", ".cr2", ".nef", ".dng", ".psd", ".ai",
                             ".eps", ".indd"]:
            category = "image"

        # Videos
        elif file_extension in [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v",
                               ".mpg", ".mpeg", ".3gp", ".ogv", ".vob", ".ts", ".mts", ".m2ts"]:
            category = "video"

        # Audio
        elif file_extension in [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus",
                               ".ape", ".alac", ".aiff", ".mid", ".midi"]:
            category = "audio"

        # Documents
        elif file_extension in [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".tex",
                               ".pages", ".epub", ".mobi", ".azw", ".djvu"]:
            category = "document"

        # Spreadsheets
        elif file_extension in [".csv", ".xlsx", ".xls", ".ods", ".numbers", ".tsv"]:
            category = "spreadsheet"

        # Presentations
        elif file_extension in [".ppt", ".pptx", ".odp", ".key"]:
            category = "presentation"

        # Code and Scripts (including compiled code)
        elif file_extension in [".py", ".js", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb",
                               ".go", ".rs", ".sh", ".bash", ".zsh", ".php", ".swift", ".kt", ".scala",
                               ".r", ".m", ".vb", ".pl", ".lua", ".groovy", ".ts", ".jsx", ".tsx",
                               ".sql", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".vue",
                               ".dart", ".f90", ".f", ".asm", ".s", ".lisp", ".cl", ".lsp", ".fasl", ".asd",
                               ".scm", ".el", ".clj", ".coffee", ".hs", ".ml", ".erl", ".ex", ".jl", ".nim",
                               ".pro", ".prolog",
                               ".scpt", ".applescript", ".bat", ".cmd", ".ps1", ".psm1",
                               ".class", ".pyc", ".pyo", ".pyd", ".o", ".obj", ".a", ".lib",
                               ".jar", ".war", ".ear"]:
            category = "code"

        # Archives and Disk Images
        elif file_extension in [".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz", ".lz", ".lzma",
                               ".iso", ".dmg", ".img", ".vhd", ".vmdk", ".vdi", ".ova", ".ovf", ".qcow2",
                               ".toast", ".cdr", ".nrg", ".mds", ".mdf",
                               ".mdzip", ".sitx", ".cab", ".ace", ".arj", ".cpio"]:
            category = "archive"

        # Data files
        elif file_extension in [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg",
                               ".csv", ".tsv", ".sql", ".sqlite", ".db", ".mdb", ".accdb",
                               ".sqlite3", ".sqlite-wal", ".sqlite-shm", ".dat", ".data",
                               ".prefs", ".properties", ".config", ".settings"]:
            category = "data"

        # Fonts
        elif file_extension in [".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon", ".dfont"]:
            category = "font"

        # Installers and Executables
        elif file_extension in [".exe", ".msi", ".app", ".pkg", ".mpkg", ".deb", ".rpm", ".apk", ".ipa",
                               ".run", ".bin", ".out", ".elf", ".dll", ".so", ".dylib",
                               ".msu", ".cab", ".appx", ".msix",
                               ".flatpak", ".snap", ".appimage"]:  # Linux package formats
            category = "installer"

        # Certificates and Security
        elif file_extension in [".p7b", ".p12", ".pfx", ".cer", ".crt", ".pem", ".der", ".key",
                               ".csr", ".p7c", ".spc", ".pub", ".wzd"]:
            category = "certificate"

        # Shortcuts and Links
        elif file_extension in [".lnk", ".url", ".webloc", ".desktop", ".rdp", ".vncloc"]:
            category = "shortcut"

        # Scientific/Engineering/Medical
        elif file_extension in [".mat", ".fig", ".hdf5", ".h5", ".nc", ".fits", ".npy", ".npz",
                               ".rdata", ".rds", ".sav", ".dta", ".pkl", ".pickle",
                               ".dcm", ".dicom"]:  # DICOM medical imaging files
            category = "scientific"

        # Financial and Tax files
        elif file_extension in [
            # Quicken files
            ".qdf", ".qel", ".qfx", ".qif", ".qpb", ".qsd", ".qph", ".qxf", ".qmtf", ".qnx",
            # Tax software files
            ".tax", ".txf",  # TurboTax
            ".t23", ".t24", ".t25", ".t26",  # TaxAct (year-specific)
            ".h23", ".h24", ".h25", ".h26",  # H&R Block (year-specific)
        ]:
            category = "financial"
        # Check for year-specific financial files (e.g., .tax2024, .q2023)
        elif (file_extension.startswith(".tax") or
              file_extension.startswith(".q2") or
              file_extension.startswith(".t2") or
              file_extension.startswith(".h2")):
            category = "financial"

        # Email and message archives (Apple Mail, Outlook for Mac, iChat).
        # Classified as "data" for consistency with the LLM's category for
        # the ~1M such files it classified before this rule existed.
        elif file_extension in [".emlx", ".olk14message", ".olk15message",
                                ".olk15msgsource", ".ichat"]:
            category = "data"

        # Backup files
        elif file_extension in [".bak", ".backup", ".old", ".orig", ".save", ".swp", ".tmp~"]:
            category = "backup"

        # Temporary files
        elif file_extension in [".tmp", ".temp", ".cache", ".crdownload", ".part", ".download",
                               ".partial", ".filepart"]:
            category = "temporary"

        # macOS/iOS specific files
        elif file_extension in [".strings", ".plist", ".nib", ".xib", ".storyboard", ".mobileprovision",
                               ".entitlements", ".car", ".tbd", ".framework", ".bundle", ".xcuserstate",
                               ".xcworkspacedata", ".xcscheme", ".xcbkptlist"]:
            category = "system"

        # Xcode project files
        elif file_extension in [".xcodeproj", ".xcworkspace", ".pbxproj"]:
            category = "code"

        # System files by name (no extension)
        elif file_info.path.name in ["CodeResources", "Info.plist", "PkgInfo", "version.plist",
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

        # Education files (course prefixes)
        elif any(file_name.startswith(prefix.lower()) for prefix in [
            "cs", "ceg", "stat", "mat", "econ", "phys", "chem", "bio", "eng", "math"
        ]):
            category = "education"

        # Financial files by name/path (tax returns, financial documents, etc.)
        elif any(keyword in file_name or keyword in file_path_str.lower() for keyword in [
            "tax", "taxes", "1040", "w2", "w-2", "1099", "quicken", "finance", "financial",
            "invoice", "receipt", "banking", "investment", "retirement", "401k", "ira"
        ]):
            category = "financial"

        else:
            category = "other"

    # Special handling for video subcategories
    if category == "video":
        from config.folder_mapping import detect_video_subcategory
        video_subcategory = detect_video_subcategory(file_name)
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