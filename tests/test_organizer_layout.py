#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_organizer_layout.py
# Purpose: Where the category folder sits inside a semantic context
#
# Description:
# Category-first scattered one course across Docs/PowerPoints,
# Docs/PDF and Media/Images — the same complaint that project roots
# exist to answer. Context-first keeps a subject together and
# subdivides it by type. These pin the ordering, both directions.
#
# Author: Tim Canady
# Created: 2026-08-21
#
# Version: 1.0.0
# Last Modified: 2026-08-21 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-21): Initial category-placement tests — Tim Canady
###################################################################

from pathlib import Path

import pytest

from core.organizer import plan_organization
from models.file_info import FileInfo


def _dest(path, category, out=Path("/out")):
    plan = plan_organization([FileInfo(path=Path(path), size=10, type=category)],
                             out, source_root=Path("/"))
    return str(plan[0][1]).replace("/out/", "")


@pytest.mark.parametrize("path,category,expected", [
    ("/Users/x/Documents/Education/WSU/FALL18-EGR3350/deck.pptx", "presentation",
     "Education/WSU/Docs/PowerPoints/FALL18-EGR3350/deck.pptx"),
    ("/Users/x/Documents/Education/AFIT/MECH532/rockets.pdf", "document_pdf",
     "Education/AFIT/Docs/PDF/MECH532/rockets.pdf"),
    ("/Volumes/home/canamac/Desktop/100JVCSO/PIC_0065.JPG", "image",
     "Desktop/Media/Images/100JVCSO/PIC_0065.JPG"),
    ("/Users/x/Documents/work/reports/q3.xlsx", "spreadsheet",
     "Work/Docs/Spreadsheets/reports/q3.xlsx"),
])
def test_context_comes_before_category(path, category, expected):
    assert _dest(path, category) == expected


def test_one_subject_stays_together_across_types():
    """The point of the ordering: a course is one subtree, not three."""
    base = "/Users/x/Documents/Education/WSU/FALL18-EGR3350/"
    dests = [_dest(base + name, cat) for name, cat in (
        ("deck.pptx", "presentation"), ("syllabus.pdf", "document_pdf"),
        ("lab.jpg", "image"), ("notes.docx", "document_word"))]
    assert all(d.startswith("Education/WSU/") for d in dests)


def test_record_set_contexts_still_ignore_category():
    """group_by_category: false keeps a DICOM series with its cover letter."""
    series = _dest("/Users/x/Documents/personal/Disability/VA_MRI/DICOM/S4/1.dcm",
                   "scientific")
    letter = _dest("/Users/x/Documents/personal/Disability/VA_MRI/cover.pdf",
                   "document_pdf")
    assert series == "Personal/Disability/VA/VA_MRI/DICOM/S4/1.dcm"
    assert letter == "Personal/Disability/VA/VA_MRI/cover.pdf"


def test_before_context_still_available(monkeypatch):
    """The old layout stays reachable for anyone who prefers it."""
    import core.organizer as org
    detector = org._get_context_detector()
    monkeypatch.setattr(detector, "category_position", "before_context")
    for ctx in detector.semantic_contexts:
        if isinstance(ctx, dict):
            ctx.pop("category_position", None)
    org._context_detector = None
    try:
        import core.context_detector as cd
        real = cd.ContextDetector

        class Before(real):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.category_position = "before_context"

        monkeypatch.setattr(cd, "ContextDetector", Before)
        monkeypatch.setattr(org, "ContextDetector", Before)
        org._context_detector = None
        assert _dest("/Users/x/Documents/Education/WSU/F18/deck.pptx",
                     "presentation") == \
            "Docs/PowerPoints/Education/WSU/F18/deck.pptx"
    finally:
        org._context_detector = None
