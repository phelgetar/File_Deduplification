#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: organizer.py
# Purpose: Plan target folder structure based on classified metadata.
#
# Description of code and how it works:
# Generates a dictionary mapping target folder paths to lists of
# files based on file type, owner, and year. Prepares plan for moving.
#
# Author: Tim Canady
# Created: 2025-09-28
#
# Version: 0.10.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 0.10.0 (2026-08-20): Project roots (Priority 0) — whole trees kept intact, outranking every other rule — Tim Canady
# - 0.9.0 (2025-11-14): MAJOR - Added semantic context detection (Priority 1 organization) for Personal/Disability/VA, Work, Education contexts — Tim Canady
# - 0.8.0 (2025-11-14): Added custom folder mapping support and special video subcategories (SecurityCameraVideos, WolfVids) — Tim Canady
# - 0.7.0 (2025-11-14): Added backup directory preservation and Xcode project support (xcode, .xcodeproj, .xcworkspace) — Tim Canady
# - 0.6.0 (2025-11-14): Separated code/scripts to use "code" category folder instead of "application" — Tim Canady
# - 0.5.0 (2025-11-14): Added code/scripts directory preservation (scripts, code, src, lib, modules, bin, dist, build, etc.) — Tim Canady
# - 0.4.0 (2025-11-14): Expanded application preservation to ALL installer/software directories (Adobe, Microsoft, etc.) — Tim Canady
# - 0.3.0 (2025-11-14): Added application structure preservation (PacketTracer, etc.) — Tim Canady
# - 0.2.0 (2025-11-14): Added web project structure preservation (http, www, website directories) — Tim Canady
# - 0.1.0 (2025-11-04): Initial organizer logic — Tim Canady
###################################################################

from collections import defaultdict
from functools import lru_cache
from models.file_info import FileInfo
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from config.folder_mapping import get_custom_folder, is_structure_preserving_category
from core.context_detector import ContextDetector
from core.projects import project_root_for
import os
import logging

logger = logging.getLogger(__name__)

# Initialize context detector with configuration
_context_detector = None

def _get_context_detector() -> ContextDetector:
    """Get or create the context detector instance."""
    global _context_detector
    if _context_detector is None:
        config_path = Path(__file__).parent.parent / "config" / "semantic_paths.yaml"
        _context_detector = ContextDetector(config_path)
    return _context_detector

# Global variable to store the base scan path for root structure preservation
_base_scan_path: Optional[Path] = None


def set_base_scan_path(path: Path):
    """Set the base scan path for preserving root structure."""
    global _base_scan_path
    _base_scan_path = path.resolve()


def _should_add_root_folder(base_dir: Path, root_folder: Optional[str]) -> bool:
    """
    Check if root folder should be added to the path.

    Prevents double nesting when base_dir already contains the root folder.
    Example: If base_dir is "/organized/Documents - 42739", don't add "Documents - 42739" again.

    Args:
        base_dir: The base output directory
        root_folder: The root folder name to potentially add

    Returns:
        True if root_folder should be added, False otherwise
    """
    if not root_folder:
        return False

    # Check if base_dir already ends with the root_folder
    base_dir_str = str(base_dir)
    return not base_dir_str.endswith(root_folder)


def organize_files(file_infos: list[FileInfo], base_dir: Path) -> dict:
    plan = defaultdict(list)

    for file_info in file_infos:
        category = file_info.type or "Unknown"
        owner = file_info.owner or "Unknown_Owner"
        year = file_info.year or "Unknown_Year"

        target_dir = base_dir / category / owner / year
        plan[target_dir].append(file_info)

    return plan

# Files that mean "a developer built this here". A folder called src,
# bin or lib is not evidence on its own — those names are common in
# photo libraries, installers and course exports, and trusting them
# filed JPEGs under Code/. Requiring a marker costs one directory
# listing per candidate folder and is cached.
CODE_PROJECT_MARKERS = {
    ".git", ".hg", ".svn", "package.json", "pyproject.toml", "setup.py",
    "setup.cfg", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "Gemfile", "composer.json",
    "Makefile", "CMakeLists.txt", "tsconfig.json", ".xcodeproj",
    ".xcworkspace", "Package.swift", "mix.exs", "build.sbt",
}


@lru_cache(maxsize=50_000)
def _has_code_marker(directory: str) -> bool:
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name in CODE_PROJECT_MARKERS:
                    return True
                if any(entry.name.endswith(m) for m in (".xcodeproj", ".xcworkspace")):
                    return True
    except OSError:
        pass
    return False


def _looks_like_code_project(path: Path, levels: int = 4) -> bool:
    """True when a project marker sits at or above this file.

    Bounded to a few levels so a marker at the repository root still
    counts without walking to /.
    """
    for parent in list(path.parents)[:levels]:
        if _has_code_marker(str(parent)):
            return True
    return False


def _plan_project_root(file_info: FileInfo, base_dir: Path, project) -> Path:
    """Everything under a project root, copied verbatim beneath its name.

    No category folder and no context folder: the point is that the tree
    arrives exactly as it left, so a spec, its screenshots and the code
    they describe are still next to each other.
    """
    try:
        relative = file_info.path.resolve().relative_to(project.root)
    except (ValueError, OSError):
        relative = Path(file_info.path.name)
    return base_dir.joinpath(project.destination, project.name, relative)


def _category_folder(category: str) -> list:
    """Folder segments for a category, from the one mapping that owns it.

    The structure-preserving planners each hardcoded their own literal
    ("web", "backup", "application"), which disagreed with
    CATEGORY_FOLDER_MAP ("Web", "Backups", "Applications") — so a .pkg
    could land in application/ while a .app landed in Installers/.
    """
    folder = get_custom_folder(category)
    if folder:
        return str(folder).split('/')
    return [category.replace(" ", "_")]


def _relative_under_source(file_path: Path, source_root: Optional[Path]) -> Optional[Path]:
    """The file's path relative to the scanned root, if it sits under it.

    This is what lets the general case keep a file's directory structure
    instead of collapsing every file of a category into one folder. Two
    files named IMG_0001.jpg from different albums are different files;
    flattening them makes the second one unplaceable.
    """
    if source_root is None:
        return None
    try:
        return file_path.resolve().relative_to(Path(source_root).resolve())
    except (ValueError, OSError):
        return None


def plan_organization(
    files: List[FileInfo],
    base_dir: Path,
    preserve_root_structure: bool = True,
    source_root: Optional[Path] = None
) -> List[Tuple[FileInfo, Path]]:
    """
    Determines target paths for files based on classification results.

    Preserves Apple backup root structure (e.g., "Desktop - 2996KD") if enabled.
    Preserves full directory structure for web projects.

    Args:
        files (List[FileInfo]): List of classified files.
        base_dir (Path): The base path where files will be organized.
        preserve_root_structure (bool): If True, preserves root folder names
                                       from source path (e.g., "Desktop - 2996KD")

    Returns:
        List[Tuple[FileInfo, Path]]: Mapping of file to destination path.
    """
    plan = []
    detector = _get_context_detector()

    for file_info in files:
        # ====================================================================
        # PRIORITY 0: PROJECT ROOTS (OUTRANKS EVERYTHING)
        #
        # A project is not a category. Source, a README, design PDFs and
        # screenshots under one project root are a single working thing;
        # filing them by type scatters it and nothing reassembles it. So
        # the whole subtree travels verbatim, whatever it contains.
        # ====================================================================
        project = project_root_for(file_info.path)
        if project:
            destination = _plan_project_root(file_info, base_dir, project)
            plan.append((file_info, destination))
            logger.debug(f"Project: {project.name} | {file_info.path} → {destination}")
            continue

        # ====================================================================
        # PRIORITY 1: SEMANTIC CONTEXT DETECTION
        # Check for semantic path contexts BEFORE any other organization
        # Examples: Personal/Disability/VA, Work, Education
        # ====================================================================
        context = detector.detect_context(file_info.path)
        if context:
            destination = _plan_context_based(file_info, base_dir, preserve_root_structure, context)
            plan.append((file_info, destination))
            logger.info(f"Context-based: {context.context_name} | {file_info.path} → {destination}")
            continue

        # ====================================================================
        # PRIORITY 2: EXISTING STRUCTURE-PRESERVING CATEGORIES
        # ====================================================================

        # Special handling for backup directories - preserve directory structure
        if file_info.type == "backup" and any(backup_dir in str(file_info.path).lower() for backup_dir in [
            "/backup/", "/backups/", "/backup_", "/backups_"
        ]):
            destination = _plan_backup_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (backup): {file_info.path} → {destination}")
            continue

        # Special handling for web projects - preserve directory structure
        if file_info.type == "web":
            destination = _plan_web_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (web): {file_info.path} → {destination}")
            continue

        # Special handling for code/scripts directories - preserve directory structure
        # A code-shaped folder name AND a real project marker nearby.
        # The name alone was enough before, which is why a photo album
        # under a folder called src was planned into Code/.
        if file_info.type == "code" and any(code_dir in str(file_info.path).lower() for code_dir in [
            "/scripts/", "/script/", "/code/", "/src/", "/source/",
            "/lib/", "/libs/", "/libraries/", "/modules/", "/packages/",
            "/bin/", "/dist/", "/build/", "/out/", "/target/",
            "/xcode/", "xcode", ".xcodeproj", ".xcworkspace"
        ]) and _looks_like_code_project(file_info.path):
            destination = _plan_code_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (code): {file_info.path} → {destination}")
            continue

        # Special handling for application directories - preserve directory structure
        if file_info.type == "application":
            destination = _plan_application_project(file_info, base_dir, preserve_root_structure)
            plan.append((file_info, destination))
            logger.debug(f"Planned (application): {file_info.path} → {destination}")
            continue

        # Special handling for security camera videos - preserve directory structure
        if file_info.type == "security_camera_video":
            destination = _plan_video_subcategory(file_info, base_dir, preserve_root_structure, "security_camera_video")
            plan.append((file_info, destination))
            logger.debug(f"Planned (security_camera_video): {file_info.path} → {destination}")
            continue

        # Special handling for wolf videos - preserve directory structure
        if file_info.type == "wolf_video":
            destination = _plan_video_subcategory(file_info, base_dir, preserve_root_structure, "wolf_video")
            plan.append((file_info, destination))
            logger.debug(f"Planned (wolf_video): {file_info.path} → {destination}")
            continue

        # Regular file organization with custom folder mapping
        subfolders = []

        # Where the file sits inside the scanned tree. When this is
        # known we keep it, so this branch behaves like the
        # structure-preserving ones above rather than flattening.
        relative = _relative_under_source(file_info.path, source_root)

        # Extract root structure folder if preserving
        root_folder = None
        if preserve_root_structure and file_info.path_metadata:
            root_folder = file_info.path_metadata.get('root_folder')

        # Add root structure folder first (e.g., "Desktop - 2996KD"),
        # but skip it when `relative` already starts with that folder —
        # otherwise the destination repeats the segment.
        if relative is None and _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)

        # Use custom folder mapping for category
        if file_info.type:
            custom_folder = get_custom_folder(file_info.type)
            if custom_folder:
                # Custom folder mapping exists (e.g., "Docs/Word")
                subfolders.append(str(custom_folder))
            else:
                # Fallback to category name if no mapping
                subfolders.append(file_info.type.replace(" ", "_"))

        if not subfolders:
            subfolders.append("Unclassified")

        # Keeping the relative path is what prevents two files with the
        # same name from resolving to one destination, where the executor
        # would skip the second as "already exists".
        tail = relative if relative is not None else Path(file_info.path.name)
        destination = base_dir.joinpath(*subfolders, tail)
        plan.append((file_info, destination))

        logger.debug(f"Planned: {file_info.path} → {destination}")

    return plan


def _plan_web_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for web project files, preserving directory structure.

    Example:
        Source: /Users/canadytw/Desktop/http/site1/index.html
        Destination: /organized/Desktop/web/http/site1/index.html

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved web structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the web root directory (http, www, website, etc.)
    file_path_str = str(file_info.path)
    web_roots = ['/http/', '/https/', '/www/', '/website/', '/websites/', '/web/',
                 '/html/', '/public_html/', '/htdocs/', '/web-projects/', '/sites/']

    web_root_found = None
    web_root_idx = -1

    for web_root in web_roots:
        if web_root in file_path_str:
            web_root_found = web_root.strip('/')
            web_root_idx = file_path_str.find(web_root)
            break

    if web_root_found and web_root_idx >= 0:
        # Extract the path from web root onwards
        relative_from_web_root = file_path_str[web_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/web/relative_path
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("web"))

        destination = base_dir.joinpath(*subfolders, relative_from_web_root)
    else:
        # Fallback if web root not found
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("web"))
        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination


def _plan_backup_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for backup files, preserving complete directory structure.

    Example:
        Source: /Users/canadytw/Desktop/backup/2024-11-14/Documents/file.txt
        Destination: /organized/Desktop/backup/backup/2024-11-14/Documents/file.txt

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved backup structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the backup root directory
    file_path_str = str(file_info.path).lower()
    backup_roots = ['/backup/', '/backups/', '/backup_', '/backups_']

    backup_root_found = None
    backup_root_idx = -1

    for backup_root in backup_roots:
        if backup_root in file_path_str:
            # Get the original case version from the actual path
            actual_path_str = str(file_info.path)
            backup_root_idx = file_path_str.find(backup_root)
            # Extract the actual directory name from the original path
            backup_root_found = actual_path_str[backup_root_idx:backup_root_idx+len(backup_root)].strip('/')
            break

    if backup_root_found and backup_root_idx >= 0:
        # Extract the path from backup root onwards
        relative_from_backup_root = str(file_info.path)[backup_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/backup/relative_path
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("backup"))

        destination = base_dir.joinpath(*subfolders, relative_from_backup_root)
    else:
        # Fallback if backup root not found
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("backup"))
        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination


def _plan_code_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for code/scripts files, preserving directory structure.

    Example:
        Source: /Users/canadytw/Documents/scripts/swift-master/validation-test/compiler_crashers_fixed/00060-adjust-function-type.swift
        Destination: /organized/Documents/Code/scripts/swift-master/validation-test/compiler_crashers_fixed/00060-adjust-function-type.swift

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved code structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the code root directory (scripts, code, src, xcode, etc.)
    file_path_str = str(file_info.path).lower()
    code_roots = [
        '/scripts/', '/script/', '/code/', '/src/', '/source/',
        '/lib/', '/libs/', '/libraries/', '/modules/', '/packages/',
        '/bin/', '/dist/', '/build/', '/out/', '/target/',
        '/xcode/', '.xcodeproj', '.xcworkspace'
    ]

    code_root_found = None
    code_root_idx = -1

    for code_root in code_roots:
        if code_root in file_path_str:
            # Get the original case version from the actual path
            actual_path_str = str(file_info.path)
            code_root_idx = file_path_str.find(code_root)
            # Extract the actual directory name from the original path
            code_root_found = actual_path_str[code_root_idx:code_root_idx+len(code_root)].strip('/')
            break

    if code_root_found and code_root_idx >= 0:
        # Extract the path from code root onwards
        relative_from_code_root = str(file_info.path)[code_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/Code/relative_path (using custom folder mapping)
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)

        # Use custom folder mapping for code category
        subfolders.extend(_category_folder("code"))

        destination = base_dir.joinpath(*subfolders, relative_from_code_root)
    else:
        # Fallback if code root not found
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)

        # Use custom folder mapping for code category
        subfolders.extend(_category_folder("code"))

        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination


def _plan_application_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for application and installer files, preserving directory structure.

    Example:
        Source: /Users/canadytw/Desktop/Adobe/Photoshop/setup.exe
        Destination: /organized/Desktop/application/Adobe/Photoshop/setup.exe

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure

    Returns:
        Destination path with preserved application structure
    """
    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Find the application/installer root directory
    file_path_str = str(file_info.path).lower()
    app_roots = [
        # Installed applications
        '/packettracer/', '/packet tracer/',
        # Common installer/software directory names
        '/installers/', '/installer/', '/software/', '/applications/', '/apps/',
        '/setup/', '/install/', '/programs/', '/program files/',
        # Vendor-specific directories
        '/adobe/', '/microsoft/', '/oracle/', '/vmware/', '/cisco/',
        '/autodesk/', '/corel/', '/intuit/', '/quicken/',
        # Code/Scripts directories (path-dependent)
        '/scripts/', '/script/', '/code/', '/src/', '/source/',
        '/lib/', '/libs/', '/libraries/', '/modules/', '/packages/',
        '/bin/', '/dist/', '/build/', '/out/', '/target/'
    ]

    app_root_found = None
    app_root_idx = -1

    for app_root in app_roots:
        if app_root in file_path_str:
            # Get the original case version from the actual path
            actual_path_str = str(file_info.path)
            app_root_idx = file_path_str.find(app_root)
            # Extract the actual directory name from the original path
            app_root_found = actual_path_str[app_root_idx:app_root_idx+len(app_root)].strip('/')
            break

    if app_root_found and app_root_idx >= 0:
        # Extract the path from app root onwards
        relative_from_app_root = str(file_info.path)[app_root_idx:].lstrip('/')

        # Build destination: base_dir/root_folder/application/relative_path
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("application"))

        destination = base_dir.joinpath(*subfolders, relative_from_app_root)
    else:
        # Fallback if app root not found
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)
        subfolders.extend(_category_folder("application"))
        destination = base_dir.joinpath(*subfolders, file_info.path.name)

    return destination


def _plan_context_based(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool, context) -> Path:
    """
    Plan organization for files detected via semantic context.

    This function handles files that belong to semantic contexts like:
    - Personal/Disability/VA (medical records, VA documents)
    - Work (work-related files, scripts, documents)
    - Education (course materials, assignments)
    - Personal/Family (family photos, documents)

    Example:
        Source: /personal/Disability/VA_IMG_CANADY_MRI_CERVICAL_SPINE.../DICOM/SERIES_4/95934524.dcm
        Destination: /organized/Personal/Disability/VA/VA_IMG_CANADY_MRI.../DICOM/SERIES_4/95934524.dcm

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure
        context: Detected ContextInfo object

    Returns:
        Destination path with preserved context structure
    """
    from core.context_detector import ContextDetector

    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Get the path segment from where the context pattern was found
    file_path_str = str(file_info.path)
    file_path_lower = file_path_str.lower()

    # Find where the matched pattern appears
    pattern_idx = file_path_lower.find(context.matched_pattern.lower())

    if pattern_idx >= 0:
        # Find the directory level where the pattern starts
        path_before_pattern = file_path_str[:pattern_idx]
        path_from_pattern = file_path_str[pattern_idx:]

        # Split path from pattern onwards
        parts_from_pattern = Path(path_from_pattern).parts

        # Build destination: base_dir/context_destination/preserved_structure
        subfolders = []

        # The context destination is itself the grouping (e.g. "Desktop"),
        # so adding root_folder as well just repeats it — the source of
        # destinations like Desktop/Desktop/… .
        context_parts = context.destination.split('/')

        # group_by_category puts the file under its category first, so a
        # photo on the Desktop lands in Media/Images/Desktop/… rather than
        # in Desktop/ with its type recorded only in the database.
        # Contexts that are a record set rather than a location set it
        # False, so a medical series and its cover letter stay together
        # instead of being split across Media/Images and Docs.
        if getattr(context, "group_by_category", True) and file_info.type:
            category_folder = get_custom_folder(file_info.type)
            if category_folder:
                subfolders.extend(str(category_folder).split('/'))
            else:
                subfolders.append(file_info.type.replace(" ", "_"))

        if (_should_add_root_folder(base_dir, root_folder)
                and root_folder not in context_parts
                and root_folder not in subfolders):
            subfolders.append(root_folder)

        # Add context destination (e.g., "Personal/Disability/VA")
        subfolders.extend(context_parts)

        # Preserve the structure below the matched directory.
        #
        # The patterns carry surrounding slashes ("/desktop/"), so
        # path_from_pattern begins with a separator and Path().parts
        # yields ("/", "Desktop", …). Slicing [1:] therefore dropped the
        # root slash and kept the matched directory — which is what put
        # it in the destination a second time.
        tail = [p for p in parts_from_pattern if p not in ("/", "\\")]
        if len(tail) > 1:
            tail = tail[1:]                   # skip the matched directory
            # The destination may already spell out folders the tail
            # repeats: matching "/disability/" under a destination of
            # "Personal/Disability/VA" leaves a tail starting with "VA",
            # giving …/VA/VA/. Drop the longest overlap between the end
            # of the destination and the start of the tail.
            overlap = 0
            for k in range(min(len(context_parts), len(tail)), 0, -1):
                if ([p.lower() for p in context_parts[-k:]]
                        == [p.lower() for p in tail[:k]]):
                    overlap = k
                    break
            subfolders.extend(tail[overlap:])
        else:
            subfolders.append(file_info.path.name)

        destination = base_dir.joinpath(*subfolders)
    else:
        # Fallback: pattern not found in exact case, use basic structure
        subfolders = []
        if _should_add_root_folder(base_dir, root_folder):
            subfolders.append(root_folder)

        for part in context.destination.split('/'):
            subfolders.append(part)

        subfolders.append(file_info.path.name)
        destination = base_dir.joinpath(*subfolders)

    return destination


def _plan_video_subcategory(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool, category: str) -> Path:
    """
    Plan organization for special video subcategories (SecurityCameraVideos, WolfVids).

    These videos maintain their directory structure within their designated category folder.

    Example:
        Source: /Users/canadytw/Desktop/SecurityCameraVideos/2024/SVR_Video_Recorder_001.mp4
        Destination: /organized/Desktop/Media/Videos/SecurityCameraVideos/2024/SVR_Video_Recorder_001.mp4

    Args:
        file_info: File information
        base_dir: Base output directory
        preserve_root_structure: Whether to preserve root structure
        category: The video subcategory (security_camera_video or wolf_video)

    Returns:
        Destination path with preserved video structure
    """
    # Get custom folder from mapping (e.g., "Media/Videos/SecurityCameraVideos")
    custom_folder = get_custom_folder(category)

    # Extract root structure folder if preserving
    root_folder = None
    if preserve_root_structure and file_info.path_metadata:
        root_folder = file_info.path_metadata.get('root_folder')

    # Build destination path
    subfolders = []
    if _should_add_root_folder(base_dir, root_folder):
        subfolders.append(root_folder)

    if custom_folder:
        destination = base_dir.joinpath(*subfolders, str(custom_folder), file_info.path.name)
    else:
        # Fallback to category name
        destination = base_dir.joinpath(*subfolders, category, file_info.path.name)

    return destination
