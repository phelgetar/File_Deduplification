#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_projects.py
# Purpose: Project roots keep whole trees together
#
# Description:
# The rule these cover is "a project is not a category": every file
# under a project root — source, PDFs, Word specs, screenshots —
# arrives at the same relative position it left, and no other rule
# gets to pull one of them out.
#
# Author: Tim Canady
# Created: 2026-08-20
#
# Version: 0.1.0
# Last Modified: 2026-08-20 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-20): Initial project-root tests — Tim Canady
###################################################################

from pathlib import Path

import pytest
import yaml

from models.file_info import FileInfo
from core.organizer import plan_organization


@pytest.fixture
def projects(tmp_path, monkeypatch):
    """A container of two projects, plus a marker project outside it."""
    import core.projects as mod

    container = tmp_path / "Workspaces"
    alpha = container / "alpha"
    (alpha / "src").mkdir(parents=True)
    (alpha / "docs").mkdir()
    (alpha / "src" / "app.py").write_text("x")
    (alpha / "docs" / "spec.pdf").write_bytes(b"%PDF-1.4")
    (alpha / "docs" / "notes.docx").write_bytes(b"PK")
    (alpha / "screenshot.png").write_bytes(b"\x89PNG")

    beta = container / "beta"
    (beta / "deep" / "nested" / "here").mkdir(parents=True)
    (beta / "deep" / "nested" / "here" / "thing.txt").write_text("x")

    # A repository nested inside a container project must NOT become its
    # own root — the container decides where the seams are.
    (alpha / "vendor" / "lib").mkdir(parents=True)
    (alpha / "vendor" / "lib" / ".git").mkdir()
    (alpha / "vendor" / "lib" / "vendored.py").write_text("x")

    # Outside the container: found by marker instead.
    loose = tmp_path / "elsewhere" / "gamma"
    loose.mkdir(parents=True)
    (loose / "package.json").write_text("{}")
    (loose / "index.js").write_text("x")

    # Not a project at all.
    plain = tmp_path / "elsewhere" / "papers"
    plain.mkdir(parents=True)
    (plain / "reading.pdf").write_bytes(b"%PDF-1.4")

    config = tmp_path / "project_roots.yaml"
    # A container matched by NAME, holding a project that carries the same
    # marker at its own top — the MATLAB-Drive shape.
    named = tmp_path / "copies" / "MATLAB-Drive"
    (named / "Coinage").mkdir(parents=True)
    (named / ".MATLABDriveTag").write_text("")
    (named / "Coinage" / ".MATLABDriveTag").write_text("")
    (named / "Coinage" / "catalog.pdf").write_bytes(b"%PDF-1.4")
    (named / "loose-note.pdf").write_bytes(b"%PDF-1.4")

    config.write_text(yaml.safe_dump({"project_roots": {
        "enabled": True,
        "containers": [{"path": str(container), "destination": "Projects"}],
        "container_names": [{"MATLAB-Drive": "Projects"}],
        "marker_destination": "Projects",
        "markers": [".git", "package.json", ".MATLABDriveTag"],
        "never_roots": [],
    }}))

    monkeypatch.setattr(mod, "CONFIG_PATH", config)
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()
    monkeypatch.delenv("WORKBENCH_NO_PROJECT_ROOTS", raising=False)
    yield tmp_path
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()


def _plan(paths, tmp_path, out=Path("/out")):
    infos = [FileInfo(path=p, size=10, type=t) for p, t in paths]
    return {fi.path: dest
            for fi, dest in plan_organization(infos, out, source_root=tmp_path)}


def test_mixed_types_stay_in_their_project(projects):
    """Code, PDF, Word and an image from one project stay side by side."""
    alpha = projects / "Workspaces" / "alpha"
    plan = _plan([
        (alpha / "src" / "app.py", "code"),
        (alpha / "docs" / "spec.pdf", "document_pdf"),
        (alpha / "docs" / "notes.docx", "document_word"),
        (alpha / "screenshot.png", "image"),
    ], projects)

    assert plan[alpha / "src" / "app.py"] == Path("/out/Projects/alpha/src/app.py")
    assert plan[alpha / "docs" / "spec.pdf"] == Path("/out/Projects/alpha/docs/spec.pdf")
    assert plan[alpha / "docs" / "notes.docx"] == Path("/out/Projects/alpha/docs/notes.docx")
    assert plan[alpha / "screenshot.png"] == Path("/out/Projects/alpha/screenshot.png")


def test_projects_do_not_merge(projects):
    """Two projects in one container get one folder each, not a shared one."""
    beta = projects / "Workspaces" / "beta" / "deep" / "nested" / "here" / "thing.txt"
    plan = _plan([(beta, "document_text")], projects)
    assert plan[beta] == Path("/out/Projects/beta/deep/nested/here/thing.txt")


def test_container_beats_nested_marker(projects):
    """A vendored repo inside a project does not carve out its own root."""
    vendored = projects / "Workspaces" / "alpha" / "vendor" / "lib" / "vendored.py"
    plan = _plan([(vendored, "code")], projects)
    assert plan[vendored] == Path("/out/Projects/alpha/vendor/lib/vendored.py")


def test_marker_project_outside_any_container(projects):
    """package.json makes a directory a root wherever it lives."""
    gamma = projects / "elsewhere" / "gamma" / "index.js"
    plan = _plan([(gamma, "code")], projects)
    assert plan[gamma] == Path("/out/Projects/gamma/index.js")


def test_loose_file_is_untouched_by_this_rule(projects):
    """A PDF that is not in a project still goes through normal filing."""
    paper = projects / "elsewhere" / "papers" / "reading.pdf"
    plan = _plan([(paper, "document_pdf")], projects)
    assert "Projects" not in plan[paper].parts


def test_kill_switch(projects, monkeypatch):
    """WORKBENCH_NO_PROJECT_ROOTS=1 restores the old behaviour."""
    monkeypatch.setenv("WORKBENCH_NO_PROJECT_ROOTS", "1")
    app = projects / "Workspaces" / "alpha" / "src" / "app.py"
    plan = _plan([(app, "code")], projects)
    assert "Projects" not in plan[app].parts


def test_home_directory_is_never_a_root(tmp_path, monkeypatch):
    """One stray Makefile at the top of a scan must not swallow everything."""
    import core.projects as mod

    config = tmp_path / "project_roots.yaml"
    config.write_text(yaml.safe_dump({"project_roots": {
        "enabled": True, "containers": [],
        "markers": ["Makefile"], "marker_destination": "Projects",
    }}))
    monkeypatch.setattr(mod, "CONFIG_PATH", config)
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()

    home = Path.home()
    monkeypatch.setattr(mod.Path, "home", staticmethod(lambda: home))
    assert mod._plausible_root(home) is False
    assert mod._plausible_root(Path("/Volumes/home")) is False
    assert mod._plausible_root(Path("/Users")) is False
    assert mod._plausible_root(Path("/Volumes/home/Projects/thing")) is True

    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()


def test_container_matched_by_name_anywhere(projects):
    """The same tree exists on two shares and in a backup; name matching
    catches every copy without listing three absolute paths."""
    doc = projects / "copies" / "MATLAB-Drive" / "Coinage" / "catalog.pdf"
    plan = _plan([(doc, "document_pdf")], projects)
    assert plan[doc] == Path("/out/Projects/Coinage/catalog.pdf")


def test_a_container_is_not_itself_a_project(projects):
    """MATLAB-Drive carries the marker at its own top as well as in each
    synced folder. Promoting the container would sweep up loose files that
    only happen to live there."""
    loose = projects / "copies" / "MATLAB-Drive" / "loose-note.pdf"
    plan = _plan([(loose, "document_pdf")], projects)
    assert "Projects" not in plan[loose].parts


def test_a_file_loose_in_a_container_is_not_a_project(projects):
    """Without the guard this planned to Projects/notes.docx/notes.docx."""
    loose = projects / "Workspaces" / "notes.docx"
    loose.write_bytes(b"PK")
    plan = _plan([(loose, "document_word")], projects)
    assert "Projects" not in plan[loose].parts
    assert plan[loose].name == "notes.docx"


def test_outermost_container_wins(projects, monkeypatch):
    """Under .../MATLAB-Drive/Foo/MATLAB-Drive/bar, Foo is the project —
    an inner directory of the same name is part of it, not a new seam."""
    import core.projects as mod
    nested = (projects / "copies" / "MATLAB-Drive" / "Foo"
              / "MATLAB-Drive" / "bar" / "deep.txt")
    nested.parent.mkdir(parents=True)
    nested.write_text("x")
    mod._is_project_dir.cache_clear()
    root = mod.project_root_for(nested)
    assert root is not None and root.name == "Foo"


def test_a_declared_root_is_one_project_whole(tmp_path, monkeypatch):
    """Neither a container nor a marker fits an Eclipse install: it holds
    two IDE builds, which is one thing, not two projects."""
    import core.projects as mod

    eclipse = tmp_path / "eclipse"
    (eclipse / "cpp-oxygen").mkdir(parents=True)
    (eclipse / "java-oxygen").mkdir()
    (eclipse / "cpp-oxygen" / "EclipseCpp.app").mkdir()
    (eclipse / "java-oxygen" / ".git").mkdir()      # must not carve a sub-root

    config = tmp_path / "rules.yaml"
    config.write_text(yaml.safe_dump({"project_roots": {
        "enabled": True,
        "roots": [{"path": str(eclipse), "destination": "Projects"}],
        "containers": [], "container_names": [],
        "markers": [".git"], "marker_destination": "Projects",
        "never_roots": [],
    }}))
    monkeypatch.setattr(mod, "CONFIG_PATH", config)
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()
    try:
        for leaf, expected in (
            ("cpp-oxygen/EclipseCpp.app/Contents/Info.plist", "eclipse"),
            ("java-oxygen/anything.txt", "eclipse"),
        ):
            root = mod.project_root_for(eclipse / leaf)
            assert root is not None and root.name == expected
            assert root.root == eclipse
    finally:
        monkeypatch.setattr(mod, "_config", None)
        mod._is_project_dir.cache_clear()


# ---------------------------------------------------------------------------
# Backup trees are copies, not projects
# ---------------------------------------------------------------------------

@pytest.fixture
def backupish(tmp_path, monkeypatch):
    import core.projects as mod
    config = tmp_path / "rules.yaml"
    config.write_text(yaml.safe_dump({"project_roots": {
        "enabled": True, "roots": [], "containers": [],
        "container_names": [{"PycharmProjects": "Projects"},
                            {"XCode-42739": "Projects"}],
        "markers": [".git"], "marker_destination": "Projects",
        "never_roots": [],
    }}))
    monkeypatch.setattr(mod, "CONFIG_PATH", config)
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()
    yield mod
    monkeypatch.setattr(mod, "_config", None)
    mod._is_project_dir.cache_clear()


@pytest.mark.parametrize("path,expected", [
    # Live, and the NAS mirror of it: both real projects.
    ("/Users/x/PycharmProjects/Foo/a.py", "Foo"),
    ("/Volumes/homes/x/PycharmProjects/Foo/a.py", "Foo"),
    # Dated snapshots and restores are copies. 85 of these planned into one
    # Projects/SENG593/, and the executor would have kept one and dropped 84.
    ("/V/Data/Restore/Backups/appdata/Host_20251028T061503Z/PycharmProjects/S/a.py", None),
    ("/V/Data/Restore/PycharmProjects/Foo/a.py", None),
    ("/V/iMac_Backup/x/PycharmProjects/Foo/a.pdf", None),
    # Only ancestors count: an Xcode project *named* Backup is still a project.
    ("/Users/x/Documents/XCode-42739/Backup/Backup.xcodeproj/p.pbxproj", "Backup"),
])
def test_backup_trees_are_not_projects(backupish, path, expected):
    root = backupish.project_root_for(path)
    assert (root.name if root else None) == expected


# ---------------------------------------------------------------------------
# Colliding project names
# ---------------------------------------------------------------------------

def test_colliding_names_are_qualified_by_parent(backupish, tmp_path):
    """Two Unit6 folders under different courses must not merge."""
    from core.organizer import plan_organization
    from models.file_info import FileInfo

    paths = [
        "/V/Edu/Park/2020-U1A-CS225/PycharmProjects/Unit6/main.cpp",
        "/V/Edu/Park/CS225/PycharmProjects/Unit6/main.cpp",
    ]
    infos = [FileInfo(path=Path(p), size=10, type="code") for p in paths]
    dests = [str(d) for _, d in
             plan_organization(infos, Path("/out"), source_root=Path("/V"))]
    assert len(set(dests)) == 2, f"still merged: {dests}"
    assert all("Unit6" in d for d in dests)
    assert any("2020-U1A-CS225" in d for d in dests)


def test_unique_names_stay_flat(backupish):
    """Only collisions are qualified; the common case keeps a short path."""
    from core.organizer import plan_organization
    from models.file_info import FileInfo

    infos = [FileInfo(path=Path("/V/x/PycharmProjects/Solo/main.py"),
                      size=10, type="code")]
    dest = str(plan_organization(infos, Path("/out"), source_root=Path("/V"))[0][1])
    assert dest == "/out/Projects/Solo/main.py"
