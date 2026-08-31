#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: video.py
# Purpose: Turn a video file into searchable text
#
# Description of code and how it works:
# Uses ffprobe for technical metadata (duration, resolution, codec,
# creation date, GPS) and ffmpeg to pull one frame from the middle of
# the video, which is then captioned and OCR'd by the existing image
# pipeline (vision.py). The result is a text blob that flows through
# the same chunk/embed/index path as every other file type.
#
# Author: Tim Canady
# Created: 2026-08-30
#
# Version: 1.1.0
# Last Modified: 2026-08-25 by Tim Canady
#
# Revision History:
# - 1.1.0 (2026-08-25): Ported into File_Deduplification. Binaries are now
#   discovered on PATH rather than hardcoded to Homebrew, and a missing
#   ffmpeg says so once instead of failing silently per file — Tim Canady
# - 1.0.0 (2026-08-30): Initial version in doc-classifier — Tim Canady
###################################################################
#
"""
Video -> text: ffprobe metadata + a llava caption of the midpoint frame.

Requires the ffmpeg suite (brew install ffmpeg). Degrades gracefully:
metadata without a caption if the vision model is unavailable, caption
without metadata if ffprobe chokes, and an ExtractionError only when
neither yields anything.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from classify.vision import VISION_MODEL, caption_image, ocr_image

# The canonical VIDEO_SUFFIXES set lives in extract.py, next to the other
# format registries, so there is one authority on what is extractable.

# Found on PATH first. The original hardcoded /opt/homebrew, which is
# right on this machine and wrong on any Intel Mac (/usr/local), any Linux
# box, and any cron job with a trimmed PATH. Override either with
# WORKBENCH_FFPROBE / WORKBENCH_FFMPEG.
def _binary(name: str) -> str:
    return (os.getenv(f"WORKBENCH_{name.upper()}")
            or shutil.which(name)
            or f"/opt/homebrew/bin/{name}")


FFPROBE = _binary("ffprobe")
FFMPEG = _binary("ffmpeg")


def available() -> bool:
    """Both binaries present? Checked once so a missing ffmpeg is reported
    as one clear line rather than as thousands of per-file failures."""
    return all(Path(b).exists() or shutil.which(b) for b in (FFPROBE, FFMPEG))


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def probe(path: Path) -> dict:
    """ffprobe the file; returns {} on any failure."""
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, timeout=30, check=True)
        return json.loads(out.stdout or b"{}")
    except Exception:
        return {}


def probe_text(path: Path) -> tuple[str, float]:
    """Human-readable metadata lines and the duration in seconds (0 if
    unknown). The text is what gets embedded, so keep it word-like."""
    data = probe(path)
    if not data:
        return "", 0.0
    lines = []
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0) or 0)
    if duration:
        lines.append(f"Duration: {_fmt_duration(duration)}")
    tags = fmt.get("tags", {}) or {}
    created = tags.get("creation_time", "")
    if created:
        lines.append(f"Recorded: {created[:10]}")
    loc = tags.get("location") or tags.get("com.apple.quicktime.location.ISO6709")
    if loc:
        lines.append(f"Location: {loc}")
    make = tags.get("com.apple.quicktime.make", "")
    model = tags.get("com.apple.quicktime.model", "")
    if make or model:
        lines.append(f"Camera: {make} {model}".strip())
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w, h = s.get("width"), s.get("height")
            if w and h:
                lines.append(f"Resolution: {w}x{h}")
            lines.append(f"Video codec: {s.get('codec_name', 'unknown')}")
            break
    return "\n".join(lines), duration


def midpoint_frame(path: Path, duration: float) -> Path | None:
    """Extract one JPEG frame from the middle of the video (1s in when the
    duration is unknown). Returns the temp file path, or None on failure.
    Caller removes the file."""
    seek = max(duration / 2, 1.0) if duration else 1.0
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        subprocess.run(
            [FFMPEG, "-v", "quiet", "-ss", f"{seek:.1f}", "-i", str(path),
             "-frames:v", "1", "-q:v", "3", "-y", str(tmp)],
            capture_output=True, timeout=60, check=True)
        if tmp.stat().st_size > 0:
            return tmp
    except Exception:
        pass
    tmp.unlink(missing_ok=True)
    return None


def describe_video(path: str | Path, model: str = VISION_MODEL) -> str:
    """Full text representation of a video: metadata + midpoint-frame
    caption and OCR. Raises ValueError only if nothing at all is usable."""
    path = Path(path)
    parts = []
    meta, duration = probe_text(path)
    if meta:
        parts.append(f"[Video metadata]\n{meta}")

    frame = midpoint_frame(path, duration)
    if frame is not None:
        try:
            caption = caption_image(frame, model=model)
            if caption:
                parts.append(f"[Video frame caption (midpoint)]\n{caption}")
            ocr = ocr_image(frame)
            if ocr:
                parts.append(f"[Text visible in video frame (OCR)]\n{ocr}")
        finally:
            frame.unlink(missing_ok=True)

    if not parts:
        raise ValueError(f"Could not read metadata or a frame from {path.name}")
    return "\n\n".join(parts)
