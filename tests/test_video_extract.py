#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_video_extract.py
# Purpose: Video -> searchable text
#
# Description:
# The workbench could file a .mp4 correctly and knew nothing about
# what was in it, because the merge from doc-classifier froze at
# v1.0.0 while the original gained video support at v1.1.0. These
# cover the port: the format registry, the dispatch, binary
# discovery, and the graceful-degradation contract that keeps a
# missing ffmpeg from turning into thousands of hard failures.
#
# Author: Tim Canady
# Created: 2026-08-25
#
# Version: 1.0.0
# Last Modified: 2026-08-25 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-25): Initial video extraction tests — Tim Canady
###################################################################

import shutil
import subprocess
from pathlib import Path

import pytest

from classify import video
from classify.extract import VIDEO_SUFFIXES, ExtractionError, extract_text

FFMPEG = shutil.which("ffmpeg")


@pytest.mark.parametrize("suffix", [".mov", ".mp4", ".m4v", ".avi",
                                    ".mkv", ".webm", ".mpg", ".mpeg", ".wmv"])
def test_video_suffixes_are_registered(suffix):
    assert suffix in VIDEO_SUFFIXES


def test_binaries_are_discovered_not_assumed(monkeypatch):
    """The original hardcoded /opt/homebrew, which is wrong on an Intel
    Mac, on Linux, and in any cron job with a trimmed PATH."""
    monkeypatch.setenv("WORKBENCH_FFPROBE", "/custom/ffprobe")
    assert video._binary("ffprobe") == "/custom/ffprobe"
    monkeypatch.delenv("WORKBENCH_FFPROBE")
    found = video._binary("ffprobe")
    assert found == shutil.which("ffprobe") or found.endswith("ffprobe")


def test_probe_returns_empty_rather_than_raising(tmp_path):
    """ffprobe on a non-video must not take the run down with it."""
    junk = tmp_path / "not-a-video.mp4"
    junk.write_bytes(b"this is not a video")
    assert video.probe(junk) == {}
    text, duration = video.probe_text(junk)
    assert text == "" and duration == 0.0


def test_midpoint_frame_cleans_up_on_failure(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"nope")
    before = set(Path(tmp_path).glob("*"))
    assert video.midpoint_frame(junk, 0.0) is None
    assert set(Path(tmp_path).glob("*")) == before


def test_unusable_video_raises_rather_than_returning_nothing(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"nope")
    with pytest.raises(ValueError):
        video.describe_video(junk)
    # …and extract_text turns that into the type its callers expect.
    with pytest.raises(ExtractionError):
        extract_text(junk)


@pytest.fixture
def real_video(tmp_path):
    """Two seconds of generated colour bars, so the test needs no fixture
    file and no network."""
    if not FFMPEG:
        pytest.skip("ffmpeg not installed")
    out = tmp_path / "bars.mp4"
    subprocess.run(
        [FFMPEG, "-v", "quiet", "-f", "lavfi", "-i",
         "testsrc=duration=2:size=320x240:rate=10", "-y", str(out)],
        check=True, timeout=60)
    return out


def test_metadata_is_extracted_without_the_vision_model(real_video):
    """Degrades to metadata alone when the vision model is unavailable —
    the property that keeps a video from being a hard failure."""
    text, duration = video.probe_text(real_video)
    assert "Resolution: 320x240" in text
    assert "Video codec:" in text
    assert 1.5 < duration < 2.5


def test_a_frame_is_pulled_from_the_middle(real_video):
    frame = video.midpoint_frame(real_video, 2.0)
    assert frame is not None
    try:
        assert frame.stat().st_size > 0
    finally:
        frame.unlink(missing_ok=True)
