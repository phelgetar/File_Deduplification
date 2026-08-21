#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_rules.py
# Purpose: The consolidated rule table, and the drift it prevents
#
# Description:
# config/rules.yaml exists because four files held slices of the same
# knowledge and disagreed on 27 extensions. The most valuable test
# here is the one that fails if they ever diverge again: every
# --file-types group must select extensions the classifier agrees
# with, and every category must have somewhere to go.
#
# Author: Tim Canady
# Created: 2026-08-20
#
# Version: 1.0.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-20): Initial consolidated-rules tests — Tim Canady
###################################################################

import collections
import logging
from pathlib import Path

import pytest

from core import rules
from core.classifier import classify_file
from config.folder_mapping import CATEGORY_FOLDER_MAP
from models.file_info import FileInfo
from utils.file_type_filter import FileTypeFilter


def _classify(extension):
    """Category for an extension on a path with no rules of its own."""
    logging.disable(logging.CRITICAL)
    try:
        return classify_file(
            FileInfo(path=Path(f"/neutral/holder/sample{extension}"), size=100)
        ).type
    finally:
        logging.disable(logging.NOTSET)


def test_every_extension_is_claimed_once():
    """A duplicate would make the winner depend on dict ordering."""
    seen = collections.Counter()
    for spec in rules.categories().values():
        seen.update(e.lower() for e in (spec.get("extensions") or []))
    assert [e for e, n in seen.items() if n > 1] == []


def test_every_category_has_a_folder():
    """A category with no folder would plan files into a path named after it."""
    missing = [c for c in rules.categories() if not rules.folder_for_category(c)]
    assert missing == []


def test_folder_map_and_rules_are_the_same_table():
    assert CATEGORY_FOLDER_MAP == rules.folder_map()


@pytest.mark.parametrize("extension,expected", [
    # The 2026-08-20 corrections. Each was a live disagreement between the
    # --file-types groups and the classifier.
    (".py", "code"), (".java", "code"), (".c", "code"), (".h", "code"),
    (".ipynb", "code"),
    (".html", "web"), (".css", "web"), (".js", "web"),
    (".rw2", "image"), (".arw", "image"), (".orf", "image"),
    (".docm", "document_word"), (".xlsm", "spreadsheet"),
    (".pptm", "presentation"), (".wpd", "document_word"),
    (".dmg", "installer"), (".tsv", "spreadsheet"),
    # And things that must not have moved.
    (".pdf", "document_pdf"), (".jpg", "image"), (".mp4", "video"),
    (".mp3", "audio"), (".xlsx", "spreadsheet"), (".zip", "archive"),
])
def test_classifier_agrees_with_the_table(extension, expected):
    assert rules.category_for_extension(extension) == expected
    assert _classify(extension) == expected


def test_classifier_never_contradicts_the_table():
    """The drift guard. Every extension in rules.yaml, end to end."""
    disagreements = {
        ext: (expected, _classify(ext))
        for ext, expected in sorted(rules._extension_index().items())
        if _classify(ext) != expected
    }
    assert disagreements == {}, f"{len(disagreements)} extensions disagree"


def test_filter_groups_select_what_they_name():
    """A group's extensions must all classify into the categories it names."""
    filt = FileTypeFilter()
    problems = []
    for group, spec in rules.filter_groups().items():
        wanted = set(spec.get("categories") or [])
        if not wanted:
            continue                      # subset groups list their own extensions
        for ext in filt.get_extensions([group]):
            got = rules.category_for_extension(ext)
            if got not in wanted:
                problems.append(f"{group}: {ext} is {got}")
    assert problems == []


def test_subset_groups_stay_inside_their_category():
    """'photos' must be image files — narrower than 'image', never wider."""
    for group, parent in (("photos", "image"), ("raw_images", "image"),
                          ("movies", "video"), ("music", "audio")):
        selected = rules.extensions_for_group(group)
        assert selected, f"{group} selects nothing"
        assert selected <= rules.extensions_for_category(parent), (
            f"{group} reaches outside {parent}: "
            f"{sorted(selected - rules.extensions_for_category(parent))}")


def test_a_category_name_works_as_a_filter_group():
    assert rules.extensions_for_group("document_pdf") == \
           rules.extensions_for_category("document_pdf")


@pytest.mark.parametrize("path,not_expected", [
    # Substring keyword matching used to make these financial files.
    ("/x/sample.rw2", "financial"),
    ("/photos/2019/bmw2-detail.xyzzy", "financial"),
    ("/archive/Miranda/notes.xyzzy", "financial"),
    # …and these education files.
    ("/photos/matthew-wedding.xyzzy", "education"),
    ("/notes/bio.xyzzy", "education"),
])
def test_keyword_rules_match_words_not_substrings(path, not_expected):
    logging.disable(logging.CRITICAL)
    try:
        got = classify_file(FileInfo(path=Path(path), size=10)).type
    finally:
        logging.disable(logging.NOTSET)
    assert got != not_expected


@pytest.mark.parametrize("path,expected", [
    ("/records/2023 tax return.xyzzy", "financial"),
    ("/records/W2-2024.xyzzy", "financial"),
    ("/school/CS4850-notes.xyzzy", "education"),
    ("/school/MATH 233 syllabus.xyzzy", "education"),
])
def test_keyword_rules_still_fire_on_real_matches(path, expected):
    logging.disable(logging.CRITICAL)
    try:
        got = classify_file(FileInfo(path=Path(path), size=10)).type
    finally:
        logging.disable(logging.NOTSET)
    assert got == expected


@pytest.mark.parametrize("extension", [".tax2024", ".q2023", ".t225", ".h226"])
def test_year_stamped_financial_extensions(extension):
    assert _classify(extension) == "financial"


def test_no_advertised_group_selects_nothing():
    """A group that matches no extension would scan an empty disk.

    Categories like `other`, `unknown` and the video collections are
    reached by path and filename rules, never by extension, so they must
    not be offered as scan filters — on the CLI or in the UI dropdown.
    """
    dead = [g for g in rules.group_names() if not rules.extensions_for_group(g)]
    assert dead == []


def test_extensionless_categories_are_rejected_not_silently_empty():
    for name in ("other", "unknown", "education"):
        assert name not in rules.group_names()
        assert rules.extensions_for_group(name) == set()
