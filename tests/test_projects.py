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
    config.write_text(yaml.safe_dump({
        "enabled": True,
        "containers": [{"path": str(container), "destination": "Projects"}],
        "marker_destination": "Projects",
        "markers": [".git", "package.json"],
        "never_roots": [],
    }))

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
    config.write_text(yaml.safe_dump({
        "enabled": True, "containers": [],
        "markers": ["Makefile"], "marker_destination": "Projects",
    }))
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
