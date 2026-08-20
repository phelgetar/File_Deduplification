#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: trash.py
# Purpose: Recoverable deletion, and putting it back
#
# Description:
# Duplicates are moved to the Trash, never unlinked. Two details make
# this safe at this project's scale:
#
#  - The Trash used is the one on the file's OWN volume
#    (/Volumes/<vol>/.Trashes/<uid>/), not ~/.Trash. Moving a 40 GB
#    video from the NAS to the boot disk's Trash would be a full copy
#    across the network and would fill the local disk; within a volume
#    it is a rename — instant, and atomic.
#
#  - Every move records both paths, so restore is exact rather than a
#    guess. Finder's own "Put Back" metadata is not relied upon.
#
# Author: Tim Canady
# Created: 2026-08-19
#
# Version: 0.1.0
# Last Modified: 2026-08-19 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-19): Initial trash/restore — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrashResult:
    path: str                     # where it was
    trashed_to: Optional[str]     # where it went, or None on failure
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.trashed_to is not None


def _volume_root(path: Path) -> Optional[Path]:
    """The /Volumes/<name> this path lives on, or None for the boot disk."""
    parts = path.parts
    if len(parts) >= 3 and parts[1] == "Volumes":
        return Path(parts[0], parts[1], parts[2])
    return None


def trash_dir_for(path) -> Path:
    """The Trash directory that keeps a move on the same filesystem.

    macOS puts per-volume trash in <volume>/.Trashes/<uid>. Using it
    means trashing is a rename rather than a cross-device copy.
    """
    path = Path(path)
    volume = _volume_root(path)
    if volume is not None and os.path.ismount(str(volume)):
        return volume / ".Trashes" / str(os.getuid())
    return Path.home() / ".Trash"


def _unique_target(directory: Path, name: str) -> Path:
    """A free path in `directory`, suffixing on collision like Finder does."""
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    for n in range(2, 10_000):
        candidate = directory / f"{stem} {n}{suffix}"
        if not candidate.exists():
            return candidate
    raise OSError(f"could not find a free name for {name} in {directory}")


def move_to_trash(path) -> TrashResult:
    """Move one file to its volume's Trash. Never unlinks anything."""
    source = Path(path)
    if not source.exists():
        return TrashResult(str(source), None, "file no longer exists")

    try:
        destination_dir = trash_dir_for(source)
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = _unique_target(destination_dir, source.name)
        # shutil.move falls back to copy+delete across filesystems; on the
        # same volume — the normal case here — it is a rename.
        shutil.move(str(source), str(target))
        return TrashResult(str(source), str(target))
    except (OSError, shutil.Error) as e:
        return TrashResult(str(source), None, str(e))


def restore(trashed_to: str, original: str) -> Optional[str]:
    """Move a trashed file back. Returns None on success, else a reason."""
    source, destination = Path(trashed_to), Path(original)
    if not source.exists():
        return f"not in the Trash any more: {trashed_to}"
    if destination.exists():
        return f"something is already at {original}"
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return None
    except (OSError, shutil.Error) as e:
        return str(e)


def trash_many(paths: List[str], progress=None) -> List[TrashResult]:
    """Trash each path, reporting progress. Failures do not stop the batch."""
    results = []
    total = len(paths)
    for i, path in enumerate(paths, 1):
        result = move_to_trash(path)
        results.append(result)
        if not result.ok:
            logger.warning("Could not trash %s: %s", path, result.error)
        if progress is not None:
            progress(i, total)
    return results
