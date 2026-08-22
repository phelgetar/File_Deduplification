#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: security.py
# Purpose: Keep the local server from reading or opening arbitrary paths
#
# Description:
# The server binds to localhost, but "local" is not "safe": any page in
# any browser can POST to 127.0.0.1. Two guards, both deny-by-default:
#
#   safe_scan_root()  — a scan source must be a real directory the user
#                       can read, and must not be a system path
#   allowed_file()    — preview/open is restricted to files that appear
#                       in a job's own plan, so the API cannot be talked
#                       into serving /etc/shadow
#
# Ported from the allowlist in doc-classifier/server.py, which
# restricted reads to files present in the RAG index.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Initial path guards — Tim Canady
###################################################################

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# Directories a scan must never be pointed at. Not a security boundary
# against a determined local attacker — it is a guard against a
# mistyped path turning into a multi-hour walk of the whole system.
FORBIDDEN_ROOTS = [
    Path("/System"), Path("/private/var/db"), Path("/dev"),
    Path("/Library/Caches"), Path("/usr"), Path("/bin"), Path("/sbin"),
]


class PathRejected(Exception):
    """Raised when a caller-supplied path fails validation."""


def safe_scan_root(raw: str) -> Path:
    """Validate a user-supplied scan source directory."""
    if not raw or not raw.strip():
        raise PathRejected("No source directory given.")

    path = Path(raw).expanduser()
    try:
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise PathRejected(f"Cannot resolve {raw!r}: {e}") from e

    if not path.is_dir():
        raise PathRejected(f"Not a directory: {path}")
    if not os.access(path, os.R_OK):
        raise PathRejected(f"Not readable: {path}")

    for forbidden in FORBIDDEN_ROOTS:
        if path == forbidden or forbidden in path.parents:
            raise PathRejected(f"Refusing to scan a system directory: {path}")
    if path == Path("/"):
        raise PathRejected("Refusing to scan the filesystem root. "
                           "Pick a specific directory.")
    return path


def safe_output_dir(raw: str) -> Path:
    """Validate the destination directory, creating it if it is safe to."""
    if not raw or not raw.strip():
        raise PathRejected("No destination directory given.")

    path = Path(raw).expanduser()
    if path.exists():
        resolved = path.resolve()
        if not resolved.is_dir():
            raise PathRejected(f"Destination exists and is not a directory: {resolved}")
        if not os.access(resolved, os.W_OK):
            raise PathRejected(f"Destination is not writable: {resolved}")
        return resolved

    parent = path.parent.expanduser()
    if not parent.exists():
        raise PathRejected(f"Parent directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise PathRejected(f"Parent directory is not writable: {parent}")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        hint = ""
        if str(path).startswith("/Volumes/"):
            hint = (" This server process may lack macOS permission for "
                    "network volumes — launch it from your own terminal "
                    "(which has your access) rather than an IDE or sandbox.")
        raise PathRejected(f"Cannot create destination {path}: {e}.{hint}") from e
    return path.resolve()


def list_subdirectories(raw: str) -> dict:
    """Directory listing for the folder picker — directories only.

    Browsing is read-only and shallow (one level per call), but still
    refuses the same system roots as scanning, hides dot-directories,
    and caps the listing so a huge directory cannot flood the UI.
    """
    path = Path(raw or "/").expanduser()
    try:
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise PathRejected(f"Cannot resolve {raw!r}: {e}") from e
    if not path.is_dir():
        raise PathRejected(f"Not a directory: {path}")
    if not os.access(path, os.R_OK):
        raise PathRejected(f"Not readable: {path}")
    for forbidden in FORBIDDEN_ROOTS:
        if path == forbidden or forbidden in path.parents:
            raise PathRejected(f"Refusing to browse a system directory: {path}")

    dirs, truncated = [], False
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    # Follow symlinks. Not following them hid every
                    # symlinked directory from the picker — including
                    # /Volumes/Macintosh HD, which is how the boot volume
                    # is presented, so browsing /Volumes on a machine with
                    # nothing else mounted showed an empty list.
                    #
                    # Safe to follow here: browsing is read-only, and the
                    # forbidden-root check below is applied to the resolved
                    # target rather than to the link.
                    if not entry.is_dir():
                        continue
                except OSError:
                    continue
                if entry.name.startswith("."):
                    continue
                try:
                    resolved = Path(entry.path).resolve()
                except (OSError, RuntimeError):
                    continue
                if any(resolved == f or f in resolved.parents
                       for f in FORBIDDEN_ROOTS):
                    continue
                dirs.append(entry.name)
                if len(dirs) >= 500:
                    truncated = True
                    break
    except OSError as e:
        raise PathRejected(f"Cannot list {path}: {e}") from e

    return {
        "path": str(path),
        "parent": str(path.parent) if path != Path("/") else None,
        "dirs": sorted(dirs, key=str.lower),
        "truncated": truncated,
        "note": _browsing_note(path, dirs),
    }


def _browsing_note(path: Path, dirs: list) -> Optional[str]:
    """Explain an empty or surprising listing, rather than showing nothing.

    "No subfolders" under /Volumes is almost never the truth — it means
    the shares dropped. Saying so beats leaving someone to wonder why the
    picker is broken.
    """
    if str(path) != "/Volumes":
        return None
    try:
        from utils import mounts
        missing = [m for m in mounts.required_mounts()
                   if not mounts.is_mounted(m)]
    except Exception:
        return None
    if not missing:
        return None
    names = ", ".join(Path(m).name for m in missing)
    return (f"Not mounted: {names}. Run the scan from the command line once "
            f"(it mounts them), or mount in Finder — a scan of an unmounted "
            f"path finds nothing and looks like an empty volume.")


def allowed_file(job_dir: Path, candidate: str) -> Optional[Path]:
    """Return the path only if it appears in this job's plan.

    An allowlist keyed to the job, so previewing a file requires that a
    scan actually found it — the endpoint cannot be repurposed into a
    general file reader.
    """
    plan = job_dir / "plan.jsonl"
    if not plan.exists():
        return None

    try:
        target = str(Path(candidate).expanduser().resolve())
    except (OSError, RuntimeError):
        return None

    with plan.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            for key in ("src", "dest"):
                value = row.get(key)
                if value and str(Path(value).resolve()) == target:
                    return Path(target)
    return None
