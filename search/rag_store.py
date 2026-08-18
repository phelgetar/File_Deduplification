#!/usr/bin/env python3
#
###################################################################
# Project: doc-classifier
# File: rag_store.py
# Purpose: Local embedding + vector-store helpers for RAG
#
# Description of code and how it works:
# Calls a local Ollama embedding model and provides a tiny on-disk
# vector store (JSON metadata + .npy matrix) with cosine search
#
# Author: Tim Canady
# Created: 2026-06-17
#
# Version: 1.2.0
# Last Modified: 2026-06-24 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-06-17): Initial version
# - 1.1.0 (2026-06-20): Hybrid search (BM25 keyword + vector) via RRF fusion
# - 1.2.0 (2026-06-24): Atomic save_index (temp file + os.replace) so an
#   interrupted/partial write can never corrupt the on-disk index. This makes
#   the indexer safe to checkpoint frequently mid-run.
###################################################################
#
"""
RAG storage + embedding helpers.

Dependency-light by design: vectors live in a single .npy matrix and the
chunk text/metadata in a parallel JSON file. No external vector database,
so nothing to break on new Python versions.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from pathlib import Path

import numpy as np
import requests

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

VECTORS_PATH = Path("rag_index.npy")
META_PATH = Path("rag_index.json")


def embed(text: str, model: str = EMBED_MODEL, timeout: int = 120) -> list[float]:
    """Return the embedding vector for a single piece of text."""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": model, "prompt": text},
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot reach Ollama at localhost:11434. Start it with: ollama serve"
        )
    return resp.json()["embedding"]


def _atomic_replace(target: Path, write_tmp) -> None:
    """Write to a temp file in the target's directory, then os.replace() it
    into place. os.replace is atomic on the same filesystem, so a reader never
    sees a half-written file and an interrupt mid-write can't corrupt the
    existing one. write_tmp(tmp_path) does the actual writing."""
    target = Path(target)
    directory = target.parent if str(target.parent) else Path(".")
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=target.suffix)
    os.close(fd)
    tmp = Path(tmp)
    try:
        write_tmp(tmp)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()            # only runs if os.replace failed


def save_index(vectors: list[list[float]], metadata: list[dict]) -> None:
    """Persist the vector matrix and parallel chunk metadata to disk, atomically.

    Both files are written to temporaries first and then swapped into place, so
    a crash or interrupt during the write leaves the previous good index intact.
    This is what makes frequent mid-run checkpoints safe."""
    mat = np.asarray(vectors, dtype=np.float32)
    # L2-normalize so cosine similarity is a plain dot product later.
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms
    # np.save would append ".npy" unless the path already ends in it; the temp
    # name does (suffix matches VECTORS_PATH), so the name stays as given.
    _atomic_replace(VECTORS_PATH, lambda p: np.save(p, mat))
    _atomic_replace(
        META_PATH,
        lambda p: p.write_text(json.dumps(metadata, indent=2), encoding="utf-8"),
    )


def load_index() -> tuple[np.ndarray, list[dict]]:
    if not VECTORS_PATH.exists() or not META_PATH.exists():
        raise RuntimeError(
            "No index found. Build it first:  python index.py ~/Documents/Logs"
        )
    mat = np.load(VECTORS_PATH)
    metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
    return mat, metadata


def search(query: str, k: int = 5, model: str = EMBED_MODEL) -> list[dict]:
    """Return the top-k chunks most similar to the query (pure vector cosine)."""
    mat, metadata = load_index()
    q = np.asarray(embed(query, model=model), dtype=np.float32)
    q /= np.linalg.norm(q) or 1.0
    scores = mat @ q                       # cosine sim (matrix is normalized)
    top = np.argsort(scores)[::-1][:k]
    results = []
    for i in top:
        item = dict(metadata[int(i)])
        item["score"] = float(scores[int(i)])
        results.append(item)
    return results


# --------------------------- hybrid search -------------------------------
# Pure vector search matches meaning, but can rank exact tokens poorly
# (a course code like "SENG660", a filename, an ID). BM25 keyword scoring
# nails those literal matches. We run both and fuse the rankings with
# Reciprocal Rank Fusion (RRF), which needs no score-scale calibration.

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word/number tokens. Keeps 'SENG660' intact as one token."""
    return _TOKEN_RE.findall(text.lower())


# Building the BM25 inverted index is O(corpus); cache it, keyed by the index
# file's mtime + size so it rebuilds automatically after a re-index.
_BM25_CACHE: dict = {"key": None, "data": None}


def _doc_tokens(m: dict) -> list[str]:
    """Keyword tokens for one chunk: its text PLUS its file path. Folding the
    path in means identifiers that live only in the folder/filename (a course
    code like 'SENG660', a project name) are still findable by keyword. Common
    path parts ('users', 'documents') get low IDF automatically, so they don't
    distort ranking; rare ones like 'seng660' carry real weight."""
    return _tokenize(m.get("file", "")) + _tokenize(m.get("text", ""))


def _build_bm25(metadata: list[dict]) -> dict:
    n = len(metadata)
    postings: dict[str, list[tuple[int, int]]] = {}   # term -> [(doc, tf)]
    doc_len = np.zeros(n, dtype=np.float32)
    for i, m in enumerate(metadata):
        toks = _doc_tokens(m)
        doc_len[i] = len(toks)
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        for t, c in tf.items():
            postings.setdefault(t, []).append((i, c))
    avgdl = float(doc_len.mean()) if n else 0.0
    idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5))
           for t, p in postings.items()}
    return {"n": n, "postings": postings, "doc_len": doc_len,
            "avgdl": avgdl, "idf": idf}


def _get_bm25(metadata: list[dict]) -> dict:
    key = None
    if META_PATH.exists():
        st = META_PATH.stat()
        key = (st.st_mtime, st.st_size)
    if _BM25_CACHE["key"] != key or _BM25_CACHE["data"] is None:
        _BM25_CACHE["key"] = key
        _BM25_CACHE["data"] = _build_bm25(metadata)
    return _BM25_CACHE["data"]


def _bm25_scores(query: str, metadata: list[dict],
                 k1: float = 1.5, b: float = 0.75) -> dict[int, float]:
    """Okapi BM25 score per document for the query terms (0 if no terms hit)."""
    idx = _get_bm25(metadata)
    avgdl = idx["avgdl"] or 1.0
    scores: dict[int, float] = {}
    for t in set(_tokenize(query)):
        plist = idx["postings"].get(t)
        if not plist:
            continue
        idf = idx["idf"][t]
        for doc, tf in plist:
            dl = float(idx["doc_len"][doc])
            denom = tf + k1 * (1 - b + b * dl / avgdl)
            scores[doc] = scores.get(doc, 0.0) + idf * (tf * (k1 + 1)) / denom
    return scores


def search_hybrid(query: str, k: int = 5, model: str = EMBED_MODEL,
                  rrf_k: int = 60) -> list[dict]:
    """Fuse vector and BM25 rankings with Reciprocal Rank Fusion.

    Each document's fused score is the sum of 1/(rrf_k + rank) over the two
    rankings it appears in. A doc strong in either method surfaces; a doc
    strong in both wins. Falls back to pure vector order when no keyword hits.
    """
    mat, metadata = load_index()

    # Ranking 1: vector cosine over the whole corpus.
    q = np.asarray(embed(query, model=model), dtype=np.float32)
    q /= np.linalg.norm(q) or 1.0
    vscores = mat @ q
    vorder = np.argsort(vscores)[::-1]
    vrank = {int(d): r for r, d in enumerate(vorder)}

    # Ranking 2: BM25 keyword, only over docs that contain a query term.
    bscores = _bm25_scores(query, metadata)
    border = sorted(bscores, key=lambda d: bscores[d], reverse=True)
    brank = {d: r for r, d in enumerate(border)}

    fused: dict[int, float] = {}
    for d in vrank:                        # vrank covers every document
        s = 1.0 / (rrf_k + vrank[d])
        if d in brank:
            s += 1.0 / (rrf_k + brank[d])
        fused[d] = s

    top = sorted(fused, key=lambda d: fused[d], reverse=True)[:k]
    results = []
    for d in top:
        item = dict(metadata[d])
        item["score"] = round(float(fused[d]), 6)
        item["vec_score"] = round(float(vscores[d]), 4)
        item["kw_score"] = round(float(bscores.get(d, 0.0)), 4)
        results.append(item)
    return results
