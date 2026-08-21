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


# ---------------------------------------------------------------------------
# Cohesive units: a captured folder is not a pile to be sorted
# ---------------------------------------------------------------------------

def _plan_many(entries, out=Path("/out")):
    infos = [FileInfo(path=Path(p), size=10, type=t) for p, t in entries]
    return {str(fi.path): str(dest).replace("/out/", "")
            for fi, dest in plan_organization(infos, out, source_root=Path("/"))}


def _desktop(folder, entries):
    return [(f"/Volumes/home/canamac/Desktop/{folder}/{name}", cat)
            for name, cat in entries]


MIXED = [(f"f{i}.x", cat) for i, cat in enumerate(
    ["data", "code", "certificate", "backup", "archive", "application",
     "image", "document_pdf", "video", "spreadsheet"])]


def test_a_captured_folder_is_not_split_by_category():
    """fred_disk is somebody's Windows disk: 18 categories, one meaning."""
    plan = _plan_many(_desktop("fred_disk", MIXED))
    roots = {"/".join(d.split("/")[:2]) for d in plan.values()}
    assert roots == {"Desktop/fred_disk"}


def test_the_structure_inside_a_unit_is_preserved():
    plan = _plan_many(_desktop("fred_disk", MIXED)
                      + [("/Volumes/home/canamac/Desktop/fred_disk/FRED_3.0/"
                          "sub/deep.dat", "data")])
    assert plan["/Volumes/home/canamac/Desktop/fred_disk/FRED_3.0/sub/deep.dat"] \
        == "Desktop/fred_disk/FRED_3.0/sub/deep.dat"


def test_a_single_purpose_folder_is_still_categorised():
    """A camera folder of nothing but JPEGs is one category, so it sorts."""
    entries = [(f"PIC_{i:04d}.JPG", "image") for i in range(12)]
    plan = _plan_many(_desktop("100JVCSO", entries))
    assert set(plan.values()) == {
        f"Desktop/Media/Images/100JVCSO/PIC_{i:04d}.JPG" for i in range(12)}


def test_loose_files_are_still_categorised():
    plan = _plan_many([
        ("/Volumes/home/canamac/Desktop/report.pdf", "document_pdf"),
        ("/Volumes/home/canamac/Desktop/shot.png", "image"),
        ("/Volumes/home/canamac/Desktop/notes.doc", "document_word"),
    ])
    assert plan["/Volumes/home/canamac/Desktop/report.pdf"] == "Desktop/Docs/PDF/report.pdf"
    assert plan["/Volumes/home/canamac/Desktop/shot.png"] == "Desktop/Media/Images/shot.png"


def test_a_small_mixed_folder_is_not_a_unit():
    """Three files of three types is not a captured disk; below the floor."""
    entries = [("a.dat", "data"), ("b.py", "code"), ("c.pdf", "document_pdf")]
    plan = _plan_many(_desktop("scratch", entries))
    roots = {"/".join(d.split("/")[:2]) for d in plan.values()}
    assert roots != {"Desktop/scratch"}
    assert "Desktop/Data" in roots


def test_a_big_single_category_folder_is_not_a_unit():
    """Volume alone is not evidence — it takes spread across categories."""
    entries = [(f"n{i}.txt", "document_text") for i in range(40)]
    plan = _plan_many(_desktop("logs", entries))
    assert all(d.startswith("Desktop/Docs/Text/logs/") for d in plan.values())
