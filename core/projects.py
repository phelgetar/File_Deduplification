#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: projects.py
# Purpose: Trees that must stay intact, whatever they contain
#
# Description:
# A project is not a category. /Users/canadytw/PycharmProjects/Foo
# holds source, a README, design PDFs, a Word spec and screenshots —
# and every one of them is only meaningful in place. Filing them by
# type scatters one working thing across Code/, Docs/PDF/, Docs/Word/
# and Media/Images/, and nothing reassembles it.
#
# So a project root outranks every other rule: the whole subtree is
# copied verbatim under the project's own name. Roots are found two
# ways:
#
#   containers  a directory whose immediate children are each a
#               project (PycharmProjects, Sites, Developer)
#   markers     any directory holding .git, package.json,
#               pyproject.toml, index.html and similar
#
# Author: Tim Canady
# Created: 2026-08-20
#
# Version: 0.1.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-20): Initial project-root preservation — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "project_roots.yaml"


@dataclass(frozen=True)
class ProjectRoot:
    """A directory whose entire subtree travels together."""

    root: Path
    name: str
    destination: str      # top-level folder in the organized tree
    reason: str           # why this counts as a project, for the UI


_config: Optional[dict] = None


def _load() -> dict:
    global _config
    if _config is None:
        try:
            _config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Could not read %s: %s", CONFIG_PATH, e)
            _config = {}
    return _config


def enabled() -> bool:
    if os.getenv("WORKBENCH_NO_PROJECT_ROOTS"):
        return False
    return bool(_load().get("enabled", True))


def _containers() -> List[dict]:
    return _load().get("containers", []) or []


def _markers() -> set:
    return set(_load().get("markers", []) or [])


def _marker_destination() -> str:
    return _load().get("marker_destination", "Projects")



def _never_roots() -> set:
    """Directories that must never be treated as a project root.

    Without this, one stray Makefile or requirements.txt in a home
    directory or at the top of a share would make *every* file below it
    "one project", and the entire scan would be copied verbatim under a
    single folder. A root has to be a real, bounded piece of work.
    """
    configured = {str(Path(p).expanduser()).rstrip("/")
                  for p in (_load().get("never_roots") or [])}
    configured.add(str(Path.home()))
    return configured


def _plausible_root(directory: Path) -> bool:
    """Is this directory small enough in scope to be one project?

    Rejects /, /Users, /Users/<someone>, /Volumes and /Volumes/<share> —
    everything a whole-disk or whole-share scan starts from.
    """
    text = str(directory).rstrip("/")
    if text in _never_roots():
        return False
    parts = directory.parts
    if len(parts) < 3:                      # "/", "/Users", "/Volumes"
        return False
    if parts[1] in ("Users", "Volumes") and len(parts) < 4:
        return False                        # a home directory or a share root
    return True


@lru_cache(maxsize=50_000)
def _is_project_dir(directory: str) -> bool:
    """Does this directory hold a file that marks it as a project root?"""
    markers = _markers()
    if not markers:
        return False
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name in markers:
                    return True
                # .xcodeproj and friends are directories with a suffix
                if any(entry.name.endswith(m) for m in markers if m.startswith(".")):
                    return True
    except OSError:
        pass
    return False


def project_root_for(path) -> Optional[ProjectRoot]:
    """The project this file belongs to, if any.

    Containers are checked first and win: when a directory is declared a
    container, its immediate children are the projects, so a repository
    nested inside one does not carve out a smaller root than intended.
    """
    if not enabled():
        return None

    try:
        candidate = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return None

    # 1. Declared containers — each immediate child is one project.
    for entry in _containers():
        raw = entry.get("path")
        if not raw:
            continue
        container = Path(raw).expanduser()
        try:
            relative = candidate.relative_to(container)
        except ValueError:
            continue
        if not relative.parts:
            continue
        name = relative.parts[0]
        return ProjectRoot(
            root=container / name,
            name=name,
            destination=entry.get("destination", "Projects"),
            reason=f"inside {container.name}, which holds one project per folder",
        )

    # 2. Marker files — the nearest ancestor that looks like a project.
    for parent in candidate.parents:
        if _plausible_root(parent) and _is_project_dir(str(parent)):
            return ProjectRoot(
                root=parent,
                name=parent.name,
                destination=_marker_destination(),
                reason=f"{parent.name} contains a project marker",
            )
    return None


def describe() -> str:
    """Human-readable summary of the configured rules."""
    if not enabled():
        return "  project-root preservation is disabled"
    lines = ["  containers (each child is one project):"]
    for entry in _containers() or [{"path": "(none)"}]:
        lines.append(f"    {entry.get('path')} -> {entry.get('destination', 'Projects')}")
    markers = sorted(_markers())
    lines.append(f"  markers ({len(markers)}): {', '.join(markers[:12])}"
                 + (" …" if len(markers) > 12 else ""))
    return "\n".join(lines)
