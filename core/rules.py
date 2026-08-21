#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: rules.py
# Purpose: The one place that knows what a file is and where it goes
#
# Description:
# Four files used to hold slices of the same knowledge — the
# classifier's hardcoded extension lists, CATEGORY_FOLDER_MAP, the
# --file-types groups, and project_roots.yaml — and nothing made them
# agree. They drifted on 27 extensions: .py was "code" to the filter
# and "document" to the classifier, .rw2 was a photograph to one and a
# Quicken file to the other, and .docm/.xlsm/.pptm were unrecognised
# by both.
#
# config/rules.yaml now owns the table, each extension appearing
# exactly once, and this module is the only reader. Everything else
# asks it: the classifier for a category, the organizer for a folder,
# the file-type filter for a group's extensions.
#
# Author: Tim Canady
# Created: 2026-08-20
#
# Version: 1.0.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-20): Initial consolidated rule loader — Tim Canady
###################################################################

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rules.yaml"


@lru_cache(maxsize=1)
def _rules() -> dict:
    try:
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except (OSError, yaml.YAMLError) as e:
        # Loud, because everything downstream silently degrades to
        # "unknown" without this file.
        logger.error("Could not read %s: %s — classification will fall back "
                     "to MIME types only", CONFIG_PATH, e)
        return {}


def categories() -> Dict[str, dict]:
    return _rules().get("categories", {}) or {}


@lru_cache(maxsize=1)
def _extension_index() -> Dict[str, str]:
    """{".pdf": "document_pdf", …} — built once, read everywhere.

    A duplicate extension is a configuration error, not something to
    resolve silently: whichever category won would depend on dict order.
    """
    index: Dict[str, str] = {}
    for category, spec in categories().items():
        for ext in (spec.get("extensions") or []):
            key = str(ext).lower()
            if key in index and index[key] != category:
                logger.warning("config/rules.yaml: %s is listed under both "
                               "%s and %s; using %s",
                               key, index[key], category, index[key])
                continue
            index[key] = category
    return index


def category_for_extension(extension: str) -> Optional[str]:
    """The category an extension means, regardless of where the file sits."""
    if not extension:
        return None
    return _extension_index().get(extension.lower())


def known_extensions() -> Set[str]:
    return set(_extension_index())


@lru_cache(maxsize=1)
def folder_map() -> Dict[str, str]:
    """{category: folder} — the destination layout under --base-dir."""
    return {name: spec.get("folder", name.title())
            for name, spec in categories().items()}


def folder_for_category(category: str) -> Optional[str]:
    return folder_map().get(category)


def extensions_for_category(category: str) -> Set[str]:
    spec = categories().get(category) or {}
    return {str(e).lower() for e in (spec.get("extensions") or [])}


def filter_groups() -> Dict[str, dict]:
    return _rules().get("filter_groups", {}) or {}


def extensions_for_group(group: str) -> Set[str]:
    """Extensions selected by a --file-types group name.

    A group is either a union of categories — which therefore can never
    fall out of step with them — or, where it is narrower than any one
    category ("photos" excludes icons and vector art), its own list.
    """
    spec = filter_groups().get(group)
    if spec is None:
        # A category name is also a valid group; no reason to make people
        # learn two vocabularies.
        return extensions_for_category(group)
    found: Set[str] = {str(e).lower() for e in (spec.get("extensions") or [])}
    for category in (spec.get("categories") or []):
        found |= extensions_for_category(category)
    return found


def group_names() -> List[str]:
    """Every name --file-types accepts and that actually selects something.

    Categories with no extensions of their own — `other`, `unknown`,
    `application`, `education`, the video collections — are reached by
    path and filename rules during classification, never by extension.
    Offering them as scan filters would be a trap: the scan would match
    nothing and look like an empty disk.
    """
    usable = {c for c in categories() if extensions_for_category(c)}
    return sorted(set(filter_groups()) | usable)


def describe_group(group: str) -> str:
    spec = filter_groups().get(group) or categories().get(group) or {}
    if spec.get("description"):
        return spec["description"]
    cats = spec.get("categories")
    if cats:
        return "All " + ", ".join(cats)
    return ""


def reload() -> None:
    """Drop caches so an edited rules.yaml takes effect (used by tests)."""
    _rules.cache_clear()
    _extension_index.cache_clear()
    folder_map.cache_clear()
