#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: protected.py
# Purpose: Files that must never be deleted as duplicates
#
# Description:
# Hash-identical is not the same as redundant. A player script, caption
# track or manifest shipped alongside a video is byte-identical in every
# export folder, so it looks like a perfect duplicate — but each copy is
# required by the media file next to it, and deleting all-but-one breaks
# every other package.
#
# Two shapes are covered, because media "files" come as both:
#   - a companion beside a media file:  lecture.mp4 + lecture.js
#   - anything inside a media-named directory:  lecture.mp4/tmp/...
#     (this project's own data has .mp4 directories containing the video)
#
# Protected files are still detected and reported as duplicates — the
# information is useful. They are simply never offered for deletion.
#
# Author: Tim Canady
# Created: 2026-08-19
#
# Version: 0.1.0
# Last Modified: 2026-08-19 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-19): Initial sidecar protection — Tim Canady
###################################################################

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Media whose companion files must survive. A directory carrying one of
# these suffixes is treated as a package and everything inside it is
# protected.
MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".wmv", ".flv", ".webm",
    ".mpg", ".mpeg", ".3gp", ".m2ts", ".ts", ".vob",
}

# Extensions that are typically a companion rather than content in their
# own right. Only these are protected by proximity to media — a .pdf
# next to a video is a real document and stays deletable.
SIDECAR_EXTENSIONS = {
    ".js", ".css", ".html", ".htm", ".xml", ".json", ".plist",
    ".vtt", ".srt", ".sbv", ".ass", ".ssa", ".cue", ".m3u8", ".mpd",
    ".nfo", ".bif", ".sidx",
}

# Directory-name endings that mark a browser save-page asset folder.
# "<page>_files" is what Chrome, Edge and Safari all produce; the others
# are the localized equivalents that turn up in mixed-language exports.
COMPANION_DIR_SUFFIXES = ("_files", "_fichiers", "_dateien", "_archivos", "-filer")

# Escape hatch: WORKBENCH_PROTECT_SIDECARS=0 disables the whole check.
def _enabled() -> bool:
    return os.getenv("WORKBENCH_PROTECT_SIDECARS", "1") not in ("0", "false", "no")


@lru_cache(maxsize=100_000)
def _directory_holds_media(directory: str) -> Optional[str]:
    """Name of a media file directly inside `directory`, if any.

    Cached per directory: without this, an export tree with thousands of
    companions would stat the same folder thousands of times.
    """
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if (entry.is_file(follow_symlinks=False)
                        and Path(entry.name).suffix.lower() in MEDIA_EXTENSIONS):
                    return entry.name
    except OSError:
        pass
    return None


def protection_reason(path) -> Optional[str]:
    """Why `path` must not be deleted as a duplicate, or None if it may be.

    Returns a human-readable reason so the UI can explain the exclusion
    rather than silently omitting the row.
    """
    if not _enabled():
        return None

    p = Path(path)

    for parent in p.parents:
        name = parent.name
        lowered = name.lower()

        # A media-named directory — the whole package must stay intact.
        if parent.suffix.lower() in MEDIA_EXTENSIONS:
            return f"inside the media package {name}"

        # A browser "Save Page Complete" companion directory. Saving a
        # page writes <page>_files/ beside it holding the scripts and
        # images the page needs. Those assets are byte-identical across
        # every saved page from the same site, so they look like perfect
        # duplicates — but each copy is what makes its own page work.
        #
        # This is the real shape behind "the .js belongs to the .mp4":
        # e.g. "SENG520_Wk4_1 of 4.mp4_files/odsp.knockout.lib-*.js".
        for marker in COMPANION_DIR_SUFFIXES:
            if lowered.endswith(marker):
                owner = name[: -len(marker)]
                if Path(owner).suffix.lower() in MEDIA_EXTENSIONS:
                    return f"asset of the saved page for {owner}"
                return f"asset of the saved page {owner}"

    # A companion sitting beside a media file in the same folder.
    if p.suffix.lower() in SIDECAR_EXTENSIONS:
        media = _directory_holds_media(str(p.parent))
        if media:
            return f"companion to {media}"

    return None


def is_protected(path) -> bool:
    return protection_reason(path) is not None


def partition(paths):
    """Split an iterable of paths into (deletable, [(path, reason), ...])."""
    deletable, protected = [], []
    for path in paths:
        reason = protection_reason(path)
        if reason:
            protected.append((str(path), reason))
        else:
            deletable.append(str(path))
    return deletable, protected
