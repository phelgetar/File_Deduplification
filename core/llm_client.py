#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: llm_client.py
# Purpose: Local LLM classification fallback via Ollama
#
# Description:
# Talks to a locally running Ollama server (default localhost:11434)
# to classify files the extension/MIME-based classifier could not
# place (category "other"). Sends filename, path context, and a short
# text snippet for text-like files; the model must answer with one of
# the known categories, enforced via Ollama structured outputs.
#
# Follows the same graceful-degradation pattern as
# image_content_analyzer.py: if the server is unreachable, the
# pipeline continues without LLM classification.
#
# Configuration (.env):
#   OLLAMA_HOST  - server URL   (default: http://localhost:11434)
#   LLM_MODEL    - model to use (default: llama3.1:8b)
#
# Author: Tim Canady
# Created: 2026-07-20
#
# Version: 1.0.0
# Last Modified: 2026-07-20 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-07-20): Initial Ollama classification client — Tim Canady
###################################################################

import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Categories the LLM may choose from. Mirrors core/classifier.py minus the
# purely path-based structure-preserving categories (web, application),
# which the LLM cannot judge from a single file.
LLM_CATEGORIES = [
    "image", "video", "audio",
    "document", "spreadsheet", "presentation",
    "code", "archive", "data", "font",
    "installer", "certificate", "shortcut",
    "scientific", "education", "financial",
    "backup", "temporary", "system",
    "other",
]

# Bytes of file content offered to the model for text-like files
SNIPPET_BYTES = 1024

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": LLM_CATEGORIES},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["category", "confidence"],
}

_SYSTEM_PROMPT = (
    "You are a file classification assistant for a personal file "
    "organization tool. Given a filename, its directory path, and "
    "optionally the beginning of its content, choose the single best "
    "category. Answer honestly: if there is not enough information to "
    "decide, use category \"other\" with low confidence. Definitions: "
    "document=prose/letters/reports/manuals, data=structured or "
    "machine-generated data, code=source code or scripts, "
    "financial=banking/tax/invoices/receipts, "
    "education=coursework/study material, system=OS or app-internal "
    "files, temporary=caches and partial downloads."
)


def _read_snippet(path: Path, max_bytes: int = SNIPPET_BYTES) -> Optional[str]:
    """Return the start of the file as text, or None if it looks binary."""
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes)
    except OSError:
        return None
    if not raw:
        return None
    if b"\x00" in raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    # Too many replacement characters -> treat as binary
    if text.count("�") > len(text) * 0.10:
        return None
    return text


class LLMClassifier:
    """Classify hard-to-place files using a local Ollama model."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None,
                 timeout: int = 60):
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "llama3.1:8b")
        self.timeout = timeout
        self._available: Optional[bool] = None
        # hash (or path) -> (category, confidence); duplicates share a hash,
        # so each unique file costs at most one LLM call per run
        self._cache: dict = {}

    def is_available(self) -> bool:
        """Check once whether the Ollama server is reachable."""
        if self._available is None:
            try:
                resp = requests.get(f"{self.host}/api/version", timeout=2)
                self._available = resp.ok
            except requests.RequestException:
                self._available = False
            if not self._available:
                logger.warning(f"Ollama server not reachable at {self.host}")
        return self._available

    def classify(self, file_info) -> Optional[Tuple[str, float]]:
        """
        Classify a FileInfo. Returns (category, confidence) or None if the
        server is unavailable, the call fails, or the model declines to
        improve on "other".
        """
        if not self.is_available():
            return None

        cache_key = file_info.hash or str(file_info.path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_parts = [
            f"Filename: {file_info.path.name}",
            f"Directory: {file_info.path.parent}",
            f"Size: {file_info.size} bytes",
        ]
        snippet = _read_snippet(file_info.path)
        if snippet:
            prompt_parts.append(f"Content (start of file):\n{snippet}")

        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": "\n".join(prompt_parts)},
                    ],
                    "stream": False,
                    "format": _RESPONSE_SCHEMA,
                    "options": {"temperature": 0},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            answer = json.loads(resp.json()["message"]["content"])
            category = answer["category"]
            confidence = float(answer["confidence"])
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            logger.warning(f"LLM classification failed for {file_info.path.name}: {e}")
            return None

        if category not in LLM_CATEGORIES:
            logger.warning(f"LLM returned unknown category '{category}' for {file_info.path.name}")
            return None

        result = (category, confidence)
        self._cache[cache_key] = result
        return result
