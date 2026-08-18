#
# Ported verbatim from doc-classifier/vision.py when that project was
# merged into File_Deduplification (2026-08-17). Unchanged so that fixes
# can still be diffed against the original.
#
#!/usr/bin/env python3
#
###################################################################
# Project: doc-classifier
# File: vision.py
# Purpose: Turn a photo into searchable text (caption + OCR + EXIF)
#
# Description of code and how it works:
# Captions an image with a local Ollama vision model, OCRs any text
# in it with Tesseract, and reads EXIF metadata, so images flow
# through the same text-based RAG pipeline as documents
#
# Author: Tim Canady
# Created: 2026-06-17
#
# Version: 1.1.0
# Last Modified: 2026-06-20 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-06-17): Initial version
# - 1.1.0 (2026-06-20): Default vision model -> llava (mllama unsupported)
###################################################################
#
"""
Image -> text helpers for the RAG indexer.

Everything here is offline:
  - caption  : local Ollama vision model (default llama3.2-vision)
  - OCR      : Tesseract (installed via brew)
  - EXIF     : Pillow
"""

from __future__ import annotations

import base64
from pathlib import Path

import requests

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
# llava is used instead of llama3.2-vision: the latter's 'mllama' architecture
# fails to load on the installed Ollama build ("unknown model architecture").
VISION_MODEL = "llava"

CAPTION_PROMPT = (
    "Describe this image in detail for search and retrieval. Mention the main "
    "subjects, objects, setting, colors, any visible text, and the type of "
    "image (photo, screenshot, diagram, document). Be concise but specific."
)

# Register HEIC/HEIF support if available (iPhone default format).
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass


def caption_image(path: str | Path, model: str = VISION_MODEL,
                  timeout: int = 180) -> str:
    """Return a natural-language description of the image via a local model."""
    data = Path(path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    payload = {
        "model": model,
        "prompt": CAPTION_PROMPT,
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        resp = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot reach Ollama at localhost:11434. Start it with: ollama serve"
        )
    return resp.json().get("response", "").strip()


def ocr_image(path: str | Path) -> str:
    """Extract any readable text from the image. Returns '' if none/unavailable."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:
        return ""


def exif_text(path: str | Path) -> str:
    """Return a few human-useful EXIF facts (date, camera, GPS) as text."""
    try:
        from PIL import ExifTags, Image
    except ImportError:
        return ""
    try:
        img = Image.open(path)
        exif = img.getexif()
    except Exception:
        return ""
    if not exif:
        return ""

    facts = []
    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    for key in ("DateTimeOriginal", "DateTime", "Make", "Model"):
        if tag_map.get(key):
            facts.append(f"{key}: {tag_map[key]}")

    # GPS lives in a sub-IFD; convert to decimal degrees if present.
    try:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if gps:
            g = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
            lat = _dms_to_deg(g.get("GPSLatitude"), g.get("GPSLatitudeRef"))
            lon = _dms_to_deg(g.get("GPSLongitude"), g.get("GPSLongitudeRef"))
            if lat is not None and lon is not None:
                facts.append(f"GPS: {lat:.5f}, {lon:.5f}")
    except Exception:
        pass

    return "\n".join(facts)


def _dms_to_deg(dms, ref) -> float | None:
    if not dms or not ref:
        return None
    try:
        d, m, s = (float(x) for x in dms)
        deg = d + m / 60 + s / 3600
        return -deg if ref in ("S", "W") else deg
    except Exception:
        return None


def describe_image(path: str | Path, model: str = VISION_MODEL) -> str:
    """Full text representation of an image: caption + OCR text + EXIF."""
    parts = []
    caption = caption_image(path, model=model)
    if caption:
        parts.append(f"[Image caption]\n{caption}")
    ocr = ocr_image(path)
    if ocr:
        parts.append(f"[Text in image (OCR)]\n{ocr}")
    meta = exif_text(path)
    if meta:
        parts.append(f"[Image metadata]\n{meta}")
    return "\n\n".join(parts)
