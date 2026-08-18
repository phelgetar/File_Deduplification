#!/usr/bin/env python3
#
###################################################################
# Project: doc-classifier
# File: metadata_store.py
# Purpose: User-editable, searchable metadata for indexed files
#
# Description of code and how it works:
# Stores hand-added metadata (people, tags, notes, category) in a
# sidecar JSON and maintains a small separate embedding index so that
# added text (e.g. names on a photo) is searchable without rebuilding
# the main content index
#
# Author: Tim Canady
# Created: 2026-06-20
#
# Version: 1.0.0
# Last Modified: 2026-06-20 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-06-20): Initial version
###################################################################
#
"""
Separation of concerns:
  - rag_index.*    : machine-extracted content (rebuilt by index.py)
  - user_metadata.json : human-added facts per file (this module)
  - meta_index.*   : embeddings of that human-added text, so it is searchable

Editing metadata is instant and never touches the main content index.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rag_store import embed

USER_META_PATH = Path("user_metadata.json")
META_VECTORS_PATH = Path("meta_index.npy")
META_META_PATH = Path("meta_index.json")

FIELDS = ("people", "tags", "notes", "category")


# ----------------------------- user metadata -----------------------------

def load_all() -> dict:
    if USER_META_PATH.exists():
        return json.loads(USER_META_PATH.read_text(encoding="utf-8"))
    return {}


def get_meta(path: str) -> dict:
    data = load_all().get(path, {})
    return {
        "people": data.get("people", []),
        "tags": data.get("tags", []),
        "notes": data.get("notes", ""),
        "category": data.get("category", ""),
    }


def set_meta(path: str, people=None, tags=None, notes=None, category=None) -> dict:
    """Update a file's metadata and refresh its searchable embedding."""
    data = load_all()
    entry = data.get(path, {})
    if people is not None:
        entry["people"] = [p.strip() for p in people if p.strip()]
    if tags is not None:
        entry["tags"] = [t.strip() for t in tags if t.strip()]
    if notes is not None:
        entry["notes"] = notes.strip()
    if category is not None:
        entry["category"] = category.strip()
    data[path] = entry
    USER_META_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _refresh_embedding(path, entry)
    return get_meta(path)


def _searchable_text(path: str, entry: dict) -> str:
    parts = [Path(path).name]
    if entry.get("people"):
        parts.append("People: " + ", ".join(entry["people"]))
    if entry.get("tags"):
        parts.append("Tags: " + ", ".join(entry["tags"]))
    if entry.get("category"):
        parts.append("Category: " + entry["category"])
    if entry.get("notes"):
        parts.append("Notes: " + entry["notes"])
    return "\n".join(parts)


# --------------------------- searchable embeddings -----------------------

def _load_meta_index() -> tuple[list, list[dict]]:
    if not META_VECTORS_PATH.exists() or not META_META_PATH.exists():
        return [], []
    mat = np.load(META_VECTORS_PATH)
    metas = json.loads(META_META_PATH.read_text(encoding="utf-8"))
    return [mat[i] for i in range(len(metas))], metas


def _save_meta_index(vectors: list, metas: list[dict]) -> None:
    if not vectors:
        # nothing to store; clear the index files
        for p in (META_VECTORS_PATH, META_META_PATH):
            if p.exists():
                p.unlink()
        return
    mat = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    np.save(META_VECTORS_PATH, mat / norms)
    META_META_PATH.write_text(json.dumps(metas, indent=2), encoding="utf-8")


def _refresh_embedding(path: str, entry: dict) -> None:
    vectors, metas = _load_meta_index()
    # drop any existing entry for this path
    kept = [(v, m) for v, m in zip(vectors, metas) if m["file"] != path]
    text = _searchable_text(path, entry)
    # only embed if there is real user content beyond the filename
    if any(entry.get(f) for f in FIELDS):
        kept.append((embed(text), {"file": path, "text": text}))
    _save_meta_index([v for v, _ in kept], [m for _, m in kept])


def search_meta(query: str, k: int = 5) -> list[dict]:
    """Top-k files whose user metadata matches the query."""
    vectors, metas = _load_meta_index()
    if not metas:
        return []
    mat = np.asarray(vectors, dtype=np.float32)
    q = np.asarray(embed(query), dtype=np.float32)
    q /= np.linalg.norm(q) or 1.0
    scores = mat @ q
    order = np.argsort(scores)[::-1][:k]
    return [{"file": metas[int(i)]["file"],
             "text": metas[int(i)]["text"],
             "score": float(scores[int(i)]),
             "source": "metadata"} for i in order]
