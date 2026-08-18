#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: cloud.py
# Purpose: Cloud (Claude) classification — the top rung of the ladder
#
# Description:
# The last resort in classify/engine.py's escalation: files that the
# rules could not place and the local model could not confidently
# place. Everything here costs money, so the module is built around a
# hard spend cap rather than around throughput:
#
#   - estimate_cost() prices a batch BEFORE any request is sent, so the
#     UI can show a number and the user can decline;
#   - CostCap tracks actual spend from each response's usage and stops
#     the run the moment the ceiling is reached.
#
# Adapted from File_Classifier/classifier.py (the Claude path), which
# wrote CSV rows; this version returns structured results for the
# pipeline and enforces the cap the original only estimated.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Adapted from File_Classifier; added a hard spend cap and structured JSON output — Tim Canady
###################################################################

from __future__ import annotations

import base64
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Categories the rest of the pipeline understands. The cloud model must
# answer with one of these, so its output drops straight into the same
# `classifications.category` column the rule classifier writes.
CATEGORIES = [
    "image", "video", "audio", "document", "spreadsheet", "presentation",
    "code", "archive", "data", "font", "installer", "certificate",
    "shortcut", "scientific", "education", "financial", "web",
    "application", "backup", "temporary", "system", "other",
]

# Default model. Deliberately the current flagship rather than the
# cheapest option: this tier only ever sees the handful of files two
# earlier passes could not place, so per-file quality matters more than
# per-token price, and the spend cap — not the model choice — is what
# bounds cost. Override with CLOUD_MODEL if you would rather trade
# accuracy for price on your own data.
#
#   claude-opus-5     $5 / $25  per MTok   (default)
#   claude-sonnet-5   $3 / $15  per MTok
#   claude-haiku-4-5  $1 / $5   per MTok
DEFAULT_MODEL = "claude-opus-5"

# USD per token, keyed by model. Used both for the pre-flight estimate
# and for running-total enforcement.
PRICING = {
    "claude-opus-5":    {"input": 5.00 / 1_000_000, "output": 25.00 / 1_000_000},
    "claude-sonnet-5":  {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-haiku-4-5": {"input": 1.00 / 1_000_000, "output":  5.00 / 1_000_000},
}

# Rough per-file token shapes for the pre-flight estimate. Deliberate
# over-estimates: quoting high and coming in under is the right error
# for a spend prompt.
AVG_TEXT_INPUT_TOKENS = 1500
AVG_IMAGE_INPUT_TOKENS = 1600
AVG_OUTPUT_TOKENS = 120

MAX_CHARS = 6000

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MEDIA_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp",
}

# The model must answer in this shape. Enforced by the API rather than
# by parsing prose, so there is no markdown-fence stripping to do.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "confidence": {"type": "number"},
        "summary": {"type": "string"},
    },
    "required": ["category", "confidence", "summary"],
    "additionalProperties": False,
}


@dataclass
class CloudResult:
    path: str
    category: Optional[str] = None
    confidence: float = 0.0
    summary: str = ""
    error: Optional[str] = None
    cost_usd: float = 0.0


def is_available() -> bool:
    """True when both the SDK and a credential are present."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def estimate_cost(paths, model: str = None) -> dict:
    """Price a batch before sending anything.

    Returns counts and a USD estimate so the caller can show the number
    and let the user decline. Intentionally errs high.
    """
    model = model or os.getenv("CLOUD_MODEL", DEFAULT_MODEL)
    rate = PRICING.get(model, PRICING[DEFAULT_MODEL])

    paths = list(paths)
    n_images = sum(1 for p in paths if Path(p).suffix.lower() in IMAGE_SUFFIXES)
    n_text = len(paths) - n_images

    input_tokens = n_text * AVG_TEXT_INPUT_TOKENS + n_images * AVG_IMAGE_INPUT_TOKENS
    output_tokens = len(paths) * AVG_OUTPUT_TOKENS
    cost = input_tokens * rate["input"] + output_tokens * rate["output"]

    return {
        "model": model,
        "files": len(paths),
        "text_files": n_text,
        "image_files": n_images,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_usd": round(cost, 4),
    }


class CostCap:
    """A running spend total with a hard ceiling.

    Checked before each request and updated from each response's actual
    usage, so the cap holds even when the pre-flight estimate was wrong.
    Thread-safe: the LLM stage runs several requests concurrently.
    """

    def __init__(self, limit_usd: float):
        self.limit = float(limit_usd)
        self.spent = 0.0
        self._lock = threading.Lock()

    def exceeded(self) -> bool:
        with self._lock:
            return self.spent >= self.limit

    def add(self, amount: float) -> None:
        with self._lock:
            self.spent += amount

    def remaining(self) -> float:
        with self._lock:
            return max(0.0, self.limit - self.spent)


class CloudClassifier:
    """Classify individual files with Claude, under a spend cap."""

    def __init__(self, model: str = None, cost_limit_usd: float = 1.0):
        self.model = model or os.getenv("CLOUD_MODEL", DEFAULT_MODEL)
        self.cap = CostCap(cost_limit_usd)
        self._client = None
        self._rate = PRICING.get(self.model, PRICING[DEFAULT_MODEL])

    @property
    def client(self):
        if self._client is None:
            import anthropic
            # Zero-arg construction resolves ANTHROPIC_API_KEY, then
            # ANTHROPIC_AUTH_TOKEN, then an `ant auth login` profile.
            self._client = anthropic.Anthropic()
        return self._client

    def _content_for(self, path: Path) -> Optional[list]:
        """Build the message content for one file, or None if unreadable."""
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            try:
                data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
            except OSError as e:
                logger.debug("Cannot read image %s: %s", path, e)
                return None
            return [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": _MEDIA_TYPES.get(suffix, "image/jpeg"),
                    "data": data,
                }},
                {"type": "text", "text": f"Classify this image. Filename: {path.name}"},
            ]

        # Text and everything else: fall back to the shared extractor so
        # pdf/docx/xlsx go in as text rather than as bytes.
        try:
            from classify.extract import extract_text
            text = (extract_text(path) or "")[:MAX_CHARS]
        except Exception:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_CHARS]
            except OSError as e:
                logger.debug("Cannot read %s: %s", path, e)
                return None

        return [{"type": "text", "text":
                 f"Filename: {path.name}\nDirectory: {path.parent}\n\n"
                 f"Content (start of file):\n{text}"}]

    def classify(self, path) -> CloudResult:
        """Classify one file. Returns an errored result rather than raising."""
        path = Path(path)
        result = CloudResult(path=str(path))

        if self.cap.exceeded():
            result.error = "cost cap reached"
            return result

        content = self._content_for(path)
        if content is None:
            result.error = "unreadable"
            return result

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,  # headroom: thinking is on by default
                system=(
                    "You classify files into exactly one category for a file "
                    "organization system. Judge by what the file IS, not by what "
                    "it mentions. Use 'other' only when nothing else fits."
                ),
                output_config={
                    "effort": "low",  # a one-label decision; low is plenty
                    "format": {"type": "json_schema", "schema": _RESPONSE_SCHEMA},
                },
                messages=[{"role": "user", "content": content}],
            )
        except Exception as e:
            result.error = str(e)
            logger.warning("Cloud classification failed for %s: %s", path.name, e)
            return result

        usage = response.usage
        cost = (usage.input_tokens * self._rate["input"]
                + usage.output_tokens * self._rate["output"])
        self.cap.add(cost)
        result.cost_usd = cost

        # A safety decline returns HTTP 200 with an empty/partial content
        # list — indexing content[0] without this check would raise.
        if response.stop_reason == "refusal":
            result.error = "refused by safety classifier"
            return result

        try:
            import json
            text = next(b.text for b in response.content if b.type == "text")
            data = json.loads(text)
            result.category = data["category"]
            result.confidence = float(data["confidence"])
            result.summary = data.get("summary", "")
        except (StopIteration, ValueError, KeyError, TypeError) as e:
            result.error = f"unparseable response: {e}"

        return result
