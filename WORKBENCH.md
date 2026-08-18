# File Workbench

One application over your files: find duplicates, work out what everything is,
review a proposed reorganization, and only then write anything to disk.

It replaces three separate tools that each walked the same files with their own
scanner, their own storage, and their own interface:

| Was | Did | Now |
|---|---|---|
| `File_Deduplification` | scan, hash, dedup, organize, execute | the core pipeline |
| `doc-classifier` | text extraction, local classification, RAG search | `classify/`, `search/` |
| `File_Classifier` | Claude-based classification with a cost estimate | the cloud tier of `classify/` |

---

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./.venv/bin/python -m server.app
```

It prints the URL — the first free port from 8000 — and binds to localhost only.

The CLI still works exactly as before, and drives the same pipeline:

```bash
./.venv/bin/python main.py ~/Documents --base-dir ~/Organized --use-db
```

**Python 3.12+ is recommended.** Everything here was built and measured on
3.14.7. The code imports cleanly on 3.9, but that is not the version it was
tested against.

---

## The four screens

| Screen | What it is for |
|---|---|
| **Run** | Choose a source and destination, pick options, and watch each stage report throughput and ETA as it goes. Cancel any time; completed work is kept. |
| **Duplicates** | Groups by content hash, largest reclaimable space first, with the copy that would be kept marked. |
| **Plan** | Every proposed move, paginated and filterable by path or category. This is the review step — nothing has been written yet. |
| **Jobs** | Every run this session. Reopen one to review its plan or execute it later. |

### Nothing is written until you say so

Execution **copies**; your source tree is left exactly as it was, so a run is
undone by deleting the destination. It still requires typing a confirmation
phrase, existing destination files are skipped rather than overwritten, and
with the database enabled every operation is logged. If the database drops
mid-run, execution refuses to start rather than move files it cannot record.

---

## What runs in parallel, and why it varies

Each stage is limited by something different — disk, the GIL, the Ollama
server, or the GPU — so a single worker count would be wrong for most of them.
`core/parallel.py` holds one policy table:

```bash
./.venv/bin/python main.py --show-parallelism
```

```
scan        8x thread    directory I/O bound
hash       16x thread    disk read bound, GIL released in hashlib
classify   20x process   pure CPU, GIL-bound in threads
tag        20x process   pure CPU, GIL-bound in threads
extract    20x process   heavy CPU parsing
image_meta 10x process   mixed I/O and CPU
llm         4x thread    bounded by Ollama server concurrency
vision_gpu     serial    single Apple GPU, batch instead of fan out
```

Two things are worth understanding before tuning anything:

**A process pool is not free, and not always a win.** Worker startup and the
pickle round-trip cost real time. On deliberately expensive work, pooling gives
about **8x**. On trivial per-file work it *loses* — forcing a pool over 8,000
tiny files turned a 0.12s stage into 0.27s. So the pool is not built blindly: a
short serial sample measures the actual per-item cost, and the pool is only
created when that cost justifies it. Cheap stages stay serial on purpose.

**The local-LLM stage is capped by Ollama, not by your cores.** Client
concurrency is read from `OLLAMA_NUM_PARALLEL`. If it is unset, Ollama serves
only a few requests at once and adding client threads changes nothing. Raise
that variable to actually use more of the machine:

```bash
export OLLAMA_NUM_PARALLEL=8
```

Override any stage with `WORKBENCH_<STAGE>_WORKERS`. Setting one to `1` forces
it serial, which is the quickest way to isolate a stage while debugging:

```bash
WORKBENCH_HASH_WORKERS=32 ./.venv/bin/python main.py ...
```

---

## How a file gets classified

Three tiers, cheapest first, each seeing only what the tier below could not
place:

1. **Rules** — `core/classifier.py`. Free, instant, handles the bulk.
2. **Local LLM** — `--llm-classify`. Free, needs a running Ollama
   (`ollama serve`). Configured by `OLLAMA_HOST` and `LLM_MODEL`.
3. **Cloud** — `--cloud-classify`. The only tier that costs money, so it runs
   last and only on the leftovers.

The cloud tier is bounded rather than open-ended. It prices the batch before
sending anything, refuses to start if the estimate exceeds the cap, and tracks
real token usage against that cap as it runs:

```bash
./.venv/bin/python main.py ~/Documents --base-dir ~/Organized \
    --llm-classify --cloud-classify --cloud-cost-limit 2.50
```

Needs `ANTHROPIC_API_KEY` (or `ant auth login`). Without a credential the tier
disables itself and the run continues on the free tiers. Default model is
`claude-opus-5`; override with `--cloud-model` or `CLOUD_MODEL`.

---

## Layout

```
core/parallel.py     per-stage execution policy (the table above)
core/pipeline.py     the pipeline as a library — the CLI and server both call this
core/main.py         CLI: argument parsing and terminal output only

classify/extract.py  any supported file -> plain text
classify/vision.py   image -> caption + OCR + EXIF
classify/engine.py   the rules -> local -> cloud ladder
classify/cloud.py    the Claude tier, with the spend cap

search/rag_store.py  embeddings, vector store, hybrid BM25 + vector search
search/metadata_store.py  user-added people/tags/notes

server/app.py        FastAPI routes
server/jobs.py       jobs in child processes, progress streaming, cancellation
server/security.py   path guards and the file allowlist

web/index.html       the four screens
web/js/app.js        front-end logic, reconnect-safe event stream
```

`core/main.py` is a thin wrapper over `core/pipeline.py`, and the server drives
the same function — so the terminal and the browser cannot drift apart.

---

## Where things are stored

| What | Where | Why |
|---|---|---|
| Files, classifications, operations, tags | MySQL | Already holds millions of rows; resume depends on it |
| RAG vectors and chunks | `rag_index.npy` / `.json` | In-memory numpy search beats BLOB comparison at this scale |
| User metadata | `user_metadata.json` | Kept separate so it survives a reindex |
| Per-job plans and results | `.workbench/jobs/<id>/` | Run output, not source — gitignored |

The database is optional (`--use-db`), but resume, tagging, and image metadata
all depend on it.

---

## Notes

- **Point `--base-dir` outside the tree you are scanning.** Organizing a folder
  into itself is the one reliable way to make a mess.
- **Interrupted runs resume** when the database is on — re-run the same command
  and completed hashes are skipped.
- **The database is a hard dependency for execution logging.** If it dies
  mid-run, the circuit breaker trips and execution is refused rather than
  performed unrecorded.

For the deduplicator's full CLI reference, category list, and database schema,
see [README.md](README.md) and the guides in [docs/](docs/).
