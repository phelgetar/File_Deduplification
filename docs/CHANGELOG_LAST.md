## [v0.10.0] – 2026-07-20

### 🚀 Major Features

#### **Local LLM Classification Fallback**
- ✨ **NEW**: `--llm-classify` flag — files that fall through every rule-based tier are classified by a local Ollama model (default `llama3.1:8b`)
  - Uses filename, path context, and a 1KB content snippet for text-like files; binary content detected and skipped
  - Structured output constrained to the known category enum — the model cannot invent categories
  - Per-run cache keyed by content hash: duplicates cost one LLM call
  - LLM confidence persisted to the database instead of the fixed 0.8
  - Degrades gracefully when the Ollama server is unreachable
  - Configure via `OLLAMA_HOST` / `LLM_MODEL` in `.env`

#### **Parallel, Resumable Hashing**
- ✨ **NEW**: `--workers N` (default 4) — SHA256 hashing runs on a thread pool; large speedup on network volumes
- ✨ **NEW**: `--batch-size N` (default 500) — periodic checkpoint summaries during hashing
- ✨ **NEW**: Resume from the database cache — unchanged files (path + mtime match) are skipped without reading a byte, logged as `(cached)`
- 🐛 **FIX**: `get_cached_hash()` existed but was never called — restarts re-hashed everything
- 🐛 **FIX**: mtimes are normalized to whole seconds; MySQL DATETIME truncation silently defeated the cache equality check
- ✨ **NEW**: Graceful Ctrl+C — interrupted runs exit cleanly, report persisted progress, and resume on re-run

#### **Scan Progress Heartbeat**
- ✨ **NEW**: Long directory walks log progress every 10 seconds (files matched, directories visited, current directory)
- ✨ **NEW**: Completion summary with totals and elapsed time

#### **Documentation & Repository**
- ✨ **NEW**: `docs/USER_GUIDE.pdf` — full user guide (every switch with examples, project structure, versioning, git workflow); regenerate with `python scripts/generate_user_guide.py`
- 🔧 Repository restructure: docs into `docs/`, SQL into `database/{schema,migrations,queries}`, tests into `tests/`, requirements split (`requirements-ai.txt` for the CLIP stack)
- 🔧 Activated the 100MB pre-commit size guard (hook was never executable)
- 🔧 Version streams unified: `version.yaml`/`setup.py` (0.4.11) and CHANGELOG/`main.py` (0.9.0) now both track v0.10.0
