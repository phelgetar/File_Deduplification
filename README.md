
# 📁 File_Deduplification

One tool for finding duplicate files, working out what every file *is*, and
proposing where it should live — over a terminal or a local web UI, sharing one
pipeline. Built for large, messy, mostly-networked collections: this repository's
own database holds **7.4 million files**.

Atomic package detection, resumable hashing, 28 categories across 309
extensions, a rules → local LLM → cloud classification ladder, and a planner
that keeps projects and captured folders intact instead of scattering them by
file type.

> 📘 **[Full User Guide (PDF)](docs/USER_GUIDE.pdf)** — every CLI switch with examples, project structure, version management, and the git workflow. Regenerate after CLI changes with `python scripts/generate_user_guide.py`.

> **Looking for the web interface?** See **[WORKBENCH.md](WORKBENCH.md)** —
> File Workbench puts one UI over deduplication, classification, and search.
> This file remains the deduplicator's CLI and database reference.

## ⚠️ Before You Run

The tool never deletes anything, but know these before the first real run (full detail in the User Guide, section 2):

1. **Execution COPIES, it does not move.** `--execute` leaves every source file in place — originals are always safe, but the destination volume needs free space roughly equal to the organized data. Duplicates are marked, never deleted.
2. **Never put `--base-dir` inside the source tree** — the next scan would ingest the organized copies and double-count everything.
3. **Files above `--metadata-only-size` are not hashed** — identical large videos will *not* be detected as duplicates.
4. **Hidden files (dotfiles) and `.dedupignore` matches are always skipped** — review `.dedupignore` before assuming full coverage.
5. **Ctrl+C is only safe with `--use-db`** — with it, re-running the same command resumes from the cache; without it, all progress is lost.
6. **Always dry-run first** — read the proposed tree before re-running with `--execute`.

---

## 🧩 What this is

Three separate tools used to do overlapping work on the same files, each with
its own scan loop, its own store, and no shared UI:

| Was | Did | Stored in |
|---|---|---|
| **File_Deduplification** | scan → hash → dedupe → classify → plan → copy | MySQL |
| **doc-classifier** | text extraction → LLM classify → RAG index → hybrid search | `.npy` + `.json` |
| **File_Classifier** | Claude classification of a directory, with a cost pre-flight | CSV |

They are now one application. This repository is the hub; the other two are
packages inside it (`classify/`, `search/`), and every stage runs through one
pipeline (`core/pipeline.py`) reached two ways:

- **`python main.py …`** — the CLI documented below. Every previously documented
  command still works.
- **`python -m server.app`** — File Workbench, a local web UI over the same
  pipeline. See **[WORKBENCH.md](WORKBENCH.md)**.

Neither is a wrapper around the other. They share the planner, the classifier
and the rules, so a plan built from the CLI and a plan built from the browser
are byte-identical, and a run started at the terminal shows up in the browser's
Jobs tab.

### Why it is fast now

The bottleneck was never thread count — it was that most stages were serial.
Only hashing was parallel; rule classification, path tagging, EXIF extraction
and image tagging each ran in a plain loop over every file, leaving most of the
machine idle for most of the wall clock.

Each stage is bound by a different resource, so a single `--workers` number is
the wrong model. `core/parallel.py` owns one policy table and every stage asks
it for an executor:

| Stage | Bound by | Executor |
|---|---|---|
| scan | directory I/O | threads over subtrees |
| hash | disk read (hashlib releases the GIL) | threads |
| rule classify, path tagging | pure CPU | **process pool** |
| text extraction | pure CPU, the heaviest stage | **process pool** |
| EXIF / image metadata | I/O + CPU | process pool |
| Ollama classify and embed | the Ollama server, not us | bounded threads |
| CLIP content tagging | the GPU | single worker, batched |

A pool is not always worth it. Starting one costs about a quarter of a second,
which is longer than classifying eight thousand small files serially — so each
stage samples the first few dozen items, measures the real per-item cost, and
only spins up workers when the arithmetic says they will pay for themselves.
`python main.py --show-parallelism` prints what your machine will actually do.

---

## 🗂️ How a destination is decided

Rules are applied in this order, first match wins. All of them live in three
config files: `config/rules.yaml` (what a file *is*), `config/semantic_paths.yaml`
(where it *came from*), `config/image_ai_categories.yaml` (what a photo *depicts*).

**0. Project roots — outrank everything.** A project is not a category. A folder
under `PycharmProjects` holds source, a README, design PDFs, a Word spec and
screenshots, and each only means something in place. The whole subtree is copied
verbatim to `Projects/<name>/<original relative path>`. Roots come from
*containers* (a directory whose immediate children are each one project) and
*markers* (`.git`, `package.json`, `.xcodeproj`, `.MATLABDriveTag`, `.xise` and
30 others). Inspect with `--show-project-roots`.

**1. Semantic context, then category.** A file under a recognised context —
`Education/WSU`, `Work`, `Personal/Disability/VA`, `Desktop` — is filed as
`<context>/<category>/<rest of its path>`:

```
Education/WSU/Docs/PowerPoints/FALL18-EGR3350/Chapter 3 Aug 30.pptx
```

Context comes before category deliberately. The other way round split one course
across `Docs/PowerPoints/…`, `Docs/PDF/…` and `Media/Images/…`. Finding *every*
presentation is a database question, not a directory question. Set
`category_position: before_context` to swap it back.

**1a. Captured folders are not sorted.** A folder under a context spanning 3+
categories over 8+ files is a unit, and keeps its subtree. `fred_disk` on a
Desktop is somebody's Windows disk — `$RECYCLE.BIN`, event logs, 5,986 files
across 18 categories — and filing it by type produced six copies of a name that
means one thing. A camera folder of nothing but JPEGs is one category, so it
still sorts.

**1b. Record sets ignore category entirely.** Contexts marked
`group_by_category: false` keep everything together, so a DICOM series arrives
beside its cover letter rather than being split across `Media/Images` and `Docs`.

**2. Category.** Everything else is filed by what it is —
`Media/Images/…`, `Docs/PDF/…`, `Code/…` — with its directory structure below
that preserved.

---

## 🚀 Features

**Scanning and hashing**
- Recursive scan with name filters and a progress heartbeat on long walks
- SHA-256 duplicate detection, with the hash cached in MySQL
- **Atomic package detection** — `.app`, `.pkg`, `.framework` are treated as single units rather than descended into, which is 18–60× faster and keeps bundles intact when copied
- **Resumable** — every hash commits immediately, so Ctrl+C is safe and re-running skips unchanged files
- **Metadata-only mode** for large files, so a 4 GB video is recorded without being read end to end
- Zero-byte files excluded from duplicate grouping — they all share one hash and are not redundant copies of each other

**Classification**
- Rule-based across 28 categories and 309 extensions, from one table
- **Local LLM fallback** (`--llm-classify`) via Ollama — nothing leaves the machine
- **Cloud escalation** (`--cloud-classify`) to Claude for what neither could place, under a hard dollar ceiling
- **Image metadata** (`--analyze-images`) — EXIF, dimensions, camera, GPS
- **Image content tagging** (`--ai-tagging`) — objects, scenes, people, locations
- **Video to text** — `ffprobe` metadata plus a captioned, OCR'd midpoint frame, so a clip becomes searchable. Needs `brew install ffmpeg`; reached today by the cloud tier only (see [WORKBENCH.md](WORKBENCH.md))

**Planning and execution**
- Project roots, semantic contexts and captured folders, in the order described above
- Dry run by default; `--execute` **copies** and never moves or deletes
- Metadata sidecars recording each file's origin
- Every run recorded under `.workbench/jobs/`, browsable and executable later from the web UI

**Awareness**
- **Service status panel** in the web UI — every service `start-services.sh` manages, green for up and red for down, refreshed every 10s. The list is read *from* the script rather than copied, so it cannot drift; MySQL and Ollama are flagged as the two the workbench itself needs

**Safety**
- Mount preflight that checks `ismount()`, not merely that the path exists
- Database circuit breaker — execution stops rather than continuing unlogged
- Duplicate deletion goes to the per-volume Trash, not `unlink()`, with a one-click undo of the last batch
- `.js` and other sidecars belonging to a media file are protected from duplicate deletion

For what changed and when, see **[CHANGELOG.md](CHANGELOG.md)**.

---

## ⚙️ Command line reference

Every switch, grouped by what it decides. `python main.py --help` prints the same
list; this section adds the reasoning and the failure modes.

`source` and `--base-dir` are required for a real run. The four informational
switches (`--show-mounts`, `--show-parallelism`, `--show-project-roots`,
`--list-file-types`) print and exit, so they work on their own.

### What to scan

| Option | Default | What it does |
|---|---|---|
| `source` | *required* | Root directory to walk. May be a local path or a mounted volume. |
| `--base-dir PATH` | *required* | Where the organized copy is built. **Must be outside `source`** — otherwise the next scan ingests your own output and double-counts everything. |
| `--filter NAME [NAME …]` | all | Root-level directory names to include. Everything else at the top level is skipped. |
| `--max-files N` | no limit | Stop after N files. The fastest way to sanity-check a plan before committing to a full run. |
| `--file-types GROUPS` | all | Comma-separated groups, e.g. `images,videos` or `docs`. See `--list-file-types`; 37 groups are available and every category name works as one. |
| `--ignore-errors` | off | Keep going past permission errors and unreadable files instead of stopping. |

Hidden files and anything matching `.dedupignore` are always skipped. Read that
file before assuming a scan covered everything.

### What actually happens

| Option | Default | What it does |
|---|---|---|
| *(none)* | — | **Dry run.** The plan is computed and recorded; nothing is written. |
| `--execute` | off | **Copies** files to their planned destinations. Sources are never moved or deleted, so the destination needs free space roughly equal to the organized data. |
| `--write-metadata` | off | Writes a `<name>.meta.json` sidecar beside each copied file: original path, hash, size, category, tags. |
| `--use-db` | off | Log to MySQL and cache hashes. **Turn this on.** Without it a Ctrl+C loses all progress; with it, re-running the same command resumes. |
| `--gui` | off | Preview the plan in a PySimpleGUI window. Superseded by the web UI; kept for existing workflows. |

Execution refuses to start if the database circuit breaker has tripped — an
unlogged copy is an unauditable one.

### Speed and memory

| Option | Default | What it does |
|---|---|---|
| `--workers N` | sized for the machine | Parallel hashing threads. Other stages size themselves; see `--show-parallelism`. |
| `--batch-size N` | 500 | Files per progress checkpoint. Every file is saved to the DB as it completes; this only controls how often a summary is printed. |
| `--metadata-only-size SIZE` | no limit | Files above this size (`75MB`, `1GB`, `500KB`) are recorded without hashing. **They can no longer be detected as duplicates** — two identical 4 GB videos will both be kept. |
| `--show-parallelism` | — | Print how each stage will be parallelised on this machine, and exit. |

Per-stage overrides are environment variables, not switches:
`WORKBENCH_HASH_WORKERS=32`, `WORKBENCH_CLASSIFY_WORKERS=20`, and so on for
`SCAN`, `TAG`, `EXTRACT`, `IMAGE_META`, `LLM`. Setting one to `1` forces that
stage serial, which is the quickest way to isolate a misbehaving stage.

### Classification

Files are classified by rules first. These switches control what happens to the
ones the rules cannot place.

| Option | Default | What it does |
|---|---|---|
| `--llm-classify` | off | Ask a local Ollama model about files that land in `other`. Nothing leaves the machine. Needs a running server — see `OLLAMA_HOST` / `LLM_MODEL`. |
| `--cloud-classify` | off | Escalate what the rules *and* the local model both failed on to Claude. **Costs money.** Needs `ANTHROPIC_API_KEY`. |
| `--cloud-cost-limit USD` | `1.00` | Hard ceiling for `--cloud-classify`, enforced against actual token usage rather than the estimate. The run is skipped outright if the pre-flight estimate already exceeds it. |
| `--cloud-model NAME` | `claude-opus-5` | Model for `--cloud-classify`; also honours `CLOUD_MODEL`. |
| `--analyze-images` | off | Extract EXIF, dimensions, camera and GPS from image files. |
| `--ai-tagging` | off | Identify image *content* — objects, scenes, people, locations — with a local vision model. |

### Duplicates

| Option | Default | What it does |
|---|---|---|
| `--skip-duplicates` | off | Plan only one copy of each set of identical files. |
| `--duplicate-report PATH` | off | Write the duplicate groups to a file. |

Zero-byte files are excluded from duplicate grouping entirely. Every empty file
shares one hash, so without this they form a single enormous "duplicate group"
— 149,296 members in this database — that reclaims nothing and would take
`.gitkeep`, empty `__init__.py` and other marker files with it.

### Layout

| Option | Default | What it does |
|---|---|---|
| `--show-project-roots` | — | Print which trees are kept intact as projects, and exit. |
| `--no-project-roots` | off | Turn off project preservation for one run and file everything by category. `WORKBENCH_NO_PROJECT_ROOTS=1` does the same thing permanently. |

### Network volumes

| Option | Default | What it does |
|---|---|---|
| `--show-mounts` | — | Print whether the required volumes are mounted, and exit. |
| `--no-auto-mount` | off | Fail rather than mounting a missing volume. The check that it *is* mounted still runs. |

The preflight uses `os.path.ismount()`, not "does the path exist". An unmounted
`/Volumes/home` is usually still a real, empty directory — a scan of it looks
like a successful pass over a volume that has lost all its files, and with
`--execute` the destination resolves locally and files are copied onto the boot
disk instead of the NAS.

Override the server with `WORKBENCH_MOUNT_HOST`, the protocol with
`WORKBENCH_MOUNT_SCHEME`, or skip the preflight with `WORKBENCH_NO_AUTOMOUNT=1`.
Mounting goes through `osascript`, so it uses the credentials already in your
login Keychain; no password is read, stored, or logged by this project.

### Records and output

| Option | Default | What it does |
|---|---|---|
| `--no-record` | off | Do not record the run under `.workbench/jobs/`. By default every run is recorded, so it appears in the web UI's Jobs tab and its plan stays reviewable and executable later. |
| `--dry-run-log` | off | Also write a standalone preview file. Largely superseded by job records. |
| `--log-format {json,txt}` | `json` | Format for `--dry-run-log`. |
| `--notify {slack,email}` | off | Send a summary when the run finishes. Needs `SLACK_WEBHOOK_URL` or the `EMAIL_*` settings. |
| `--list-file-types` | — | Print the available `--file-types` groups, and exit. |

---

## 🧾 Worked examples

### Look before you leap

```bash
# Is the NAS actually mounted? (A scan of an unmounted path silently finds nothing.)
python main.py --show-mounts
```

```bash
# What will this machine do in parallel?
python main.py --show-parallelism
```

```bash
# Which trees will be kept whole rather than filed by type?
python main.py --show-project-roots
```

```bash
# What can --file-types select?
python main.py --list-file-types
```

### A first, small dry run

```bash
python main.py /Volumes/home --base-dir /Volumes/homes/Organized --use-db --max-files 500
```

Reads 500 files, prints the proposed tree, writes nothing. The run is recorded
under `.workbench/jobs/`, so you can browse the same plan in the web UI instead
of scrolling the terminal.

### The full run, resumable

```bash
python main.py /Volumes/home \
  --base-dir /Volumes/homes/Organized \
  --use-db \
  --llm-classify \
  --metadata-only-size 100MB \
  --workers 16
```

Ctrl+C at any point; re-run the same command to resume from the hash cache.
Still a dry run — add `--execute` only after you have read the plan.

### Committing to it

```bash
python main.py /Volumes/home \
  --base-dir /Volumes/homes/Organized \
  --use-db --execute --write-metadata
```

Copies files and leaves a `.meta.json` beside each one. Sources are untouched.

### Narrower jobs

```bash
# Photographs only, with EXIF and content tags
python main.py ~/Pictures --base-dir /Volumes/homes/Organized \
  --use-db --file-types photos --analyze-images --ai-tagging
```

```bash
# Just find the duplicates; plan nothing
python main.py /Volumes/home --base-dir /tmp/unused \
  --use-db --duplicate-report ~/duplicates.txt
```

```bash
# One tree, files by category, ignoring project preservation
python main.py ~/Documents/Archive --base-dir /Volumes/homes/Organized \
  --use-db --no-project-roots
```

### Escalating the hard cases to Claude

```bash
python main.py /Volumes/home --base-dir /Volumes/homes/Organized \
  --use-db --llm-classify --cloud-classify --cloud-cost-limit 5.00
```

Rules first, then the local model, then Claude for whatever is left — and it
stops at five dollars of real token usage.

---

## 🧰 Maintenance scripts

| Script | What it is for |
|---|---|
| `scripts/reclassify_files.py` | Re-derive categories for rows already in the database. **Classification is cached**: a file classified under an older ruleset keeps its stored category on re-runs, so a rules change only reaches existing rows through this. `--categories other data` to target, `--dry-run` first, `--skip-cloud` to leave Google Drive and Dropbox alone. A move into `other`/`unknown` is refused unless you pass `--allow-downgrade` — reclassifying a specific category into an unclassified one is a loss, not an improvement. |
| `scripts/import_cli_runs.py` | Convert historical `dry_run_preview_*.json` files into job records the web UI can read. `--dry-run`, `--max-size-mb` and `--only` are there because the largest preview here is 5.5 GB and 6,992,105 rows. Imported plans are flagged `ruleset: historical` when they predate the current rules — they are a record of what was decided, not a proposal to act on. |
| `scripts/debug_classification.py` | Ask why one specific file was classified the way it was. |
| `scripts/generate_user_guide.py` | Rebuild `docs/USER_GUIDE.pdf`. Run after changing any CLI switch. |
| `scripts/gen_changelog.py`, `scripts/bump_version.py` | Release plumbing; `make changelog`, `make bump`, `make release` wrap them. |

---

## 🎯 Categories and where they go

**28 categories, 309 extensions.** All of it is one table in `config/rules.yaml`, where each extension appears exactly once and the folder below is read from the same row. Keeping these apart is how `.py` came to be `code` to the `--file-types` filter and `document` to the classifier.

Categories with no extensions are reached by path or filename rules rather than by extension, so they cannot be used as `--file-types` filters.

| Category | Goes to | Extensions | Examples |
|---|---|---|---|
| **image** | `Media/Images` | 25 | `.ai`, `.arw`, `.bmp`, `.cdr`, `.cr2` |
| **video** | `Media/Videos` | 16 | `.3gp`, `.avi`, `.flv`, `.m2ts`, `.m4v` |
| **audio** | `Media/Music` | 13 | `.aac`, `.aiff`, `.alac`, `.ape`, `.flac` |
| **document_word** | `Docs/Word` | 7 | `.doc`, `.docm`, `.docx`, `.odt`, `.pages` |
| **document_pdf** | `Docs/PDF` | 6 | `.azw`, `.azw3`, `.epub`, `.mobi`, `.pdf` |
| **document_text** | `Docs/Text` | 7 | `.log`, `.md`, `.nfo`, `.readme`, `.rst` |
| **document** | `Docs` | — | *by path or name* |
| **spreadsheet** | `Docs/Spreadsheets` | 6 | `.csv`, `.ods`, `.tsv`, `.xls`, `.xlsm` |
| **presentation** | `Docs/PowerPoints` | 5 | `.key`, `.odp`, `.ppt`, `.pptm`, `.pptx` |
| **code** | `Code` | 70 | `.a`, `.asd`, `.asm`, `.bash`, `.c` |
| **web** | `Web` | 4 | `.css`, `.htm`, `.html`, `.js` |
| **data** | `Data` | 18 | `.accdb`, `.cfg`, `.conf`, `.config`, `.dat` |
| **archive** | `Archives` | 29 | `.7z`, `.ace`, `.arj`, `.bz2`, `.cab` |
| **installer** | `Installers` | 22 | `.apk`, `.app`, `.appx`, `.bat`, `.bin` |
| **application** | `Applications` | — | *by path or name* |
| **font** | `Fonts` | 7 | `.dfont`, `.eot`, `.fon`, `.otf`, `.ttf` |
| **certificate** | `Certs` | 12 | `.cer`, `.crt`, `.csr`, `.der`, `.p12` |
| **scientific** | `Scientific` | 16 | `.dcm`, `.dicom`, `.dta`, `.fig`, `.fits` |
| **financial** | `Financial` | 23 | `.h2`, `.h23`, `.h24`, `.h25`, `.h26` |
| **education** | `Education` | — | *by path or name* |
| **backup** | `Backups` | 6 | `.backup`, `.bak`, `.old`, `.orig`, `.save` |
| **temporary** | `Temp` | 4 | `.cache`, `.part`, `.temp`, `.tmp` |
| **system** | `System` | 7 | `.bundle`, `.car`, `.log2`, `.nib`, `.plist` |
| **shortcut** | `Shortcuts` | 6 | `.alias`, `.lnk`, `.rdp`, `.url`, `.vncloc` |
| **security_camera_video** | `Media/Videos/SecurityCameraVideos` | — | *by path or name* |
| **wolf_video** | `Media/Videos/WolfVids` | — | *by path or name* |
| **other** | `Other` | — | *by path or name* |
| **unknown** | `Unclassified` | — | *by path or name* |

Inspect or change any of it with `python main.py --list-file-types`, or by editing `config/rules.yaml` directly. Existing database rows keep their stored category — use `scripts/reclassify_files.py` to re-derive them.

---

## 🧰 Requirements

- Python 3.9+
- MySQL 8.x
- Slack webhook URL (optional, for notifications)

Install dependencies:
```bash
pip install -r requirements.txt
```

For AI image content analysis (CLIP model, ~2GB of ML dependencies), additionally:
```bash
pip install -r requirements-ai.txt
```
The app runs fine without these — image content tagging is skipped when they're absent.

For turning **video** into searchable text (`ffprobe` metadata plus a captioned
midpoint frame):
```bash
brew install ffmpeg
```
Also optional. Without it a video is still classified and filed by extension;
only its contents go undescribed.

---

## 🔐 .env Configuration

Create a `.env` file with the following:

```env
# MySQL connection (used by core/db.py)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=File_Deduplification
DB_USER=your-db-user
DB_PASSWORD=your-db-password

# Optional: Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: email notifications (--notify email)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=you@example.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=you@example.com

# Optional: local LLM classification fallback (--llm-classify)
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.1:8b
# How many requests Ollama will genuinely serve at once. The client reads the
# same number rather than guessing, so raising one without the other buys
# nothing.
OLLAMA_NUM_PARALLEL=8

# Optional: cloud escalation (--cloud-classify)
ANTHROPIC_API_KEY=sk-ant-...
CLOUD_MODEL=claude-opus-5
```

### Environment variables (not in `.env`)

Set these in the shell for one run, or export them permanently.

| Variable | Effect |
|---|---|
| `WORKBENCH_<STAGE>_WORKERS` | Override one stage's worker count: `SCAN`, `HASH`, `CLASSIFY`, `TAG`, `EXTRACT`, `IMAGE_META`, `LLM`. Setting one to `1` forces it serial. |
| `WORKBENCH_NO_PROJECT_ROOTS=1` | Turn off project preservation permanently (`--no-project-roots` does it for one run). |
| `WORKBENCH_NO_AUTOMOUNT=1` | Skip the mount preflight entirely. |
| `WORKBENCH_MOUNT_HOST` | Server to mount the required shares from (default `canome`). |
| `WORKBENCH_MOUNT_SCHEME` | `smb` (default), `afp` or `nfs`. |
| `WORKBENCH_FFPROBE`, `WORKBENCH_FFMPEG` | Paths to the ffmpeg binaries, when they are not on `PATH`. |

---

## 🛠 Dev Commands

```bash
make bump         # Bump patch version
make changelog    # Generate CHANGELOG from commits
make release      # Tag and push new version
make rollback     # Revert latest patch
```

---

## 📂 Project Structure

```
File_Deduplification/
├── main.py                  # CLI entry point (delegates to core/main.py)
├── setup.py                 # Packaging (console script: dedupe)
├── requirements.txt
├── Makefile
├── README.md
├── WORKBENCH.md             # File Workbench: the web UI + unified pipeline
├── CHANGELOG.md
├── config/                  # Three rule files, one question each
│   ├── rules.yaml           # WHAT a file is: extension → category → folder,
│   │                        #   the --file-types groups, and the project roots
│   │                        #   whose trees are kept whole
│   ├── semantic_paths.yaml  # WHERE it came from: Work, Education, Personal/VA
│   ├── image_ai_categories.yaml  # what a photograph DEPICTS, for the vision model
│   └── folder_mapping.py    # thin accessors over rules.yaml
├── core/                    # Application library code
│   ├── main.py              # CLI implementation
│   ├── scanner.py           # Recursive scan + atomic package detection
│   ├── hasher.py            # SHA256 hashing
│   ├── deduplicator.py      # Duplicate detection
│   ├── classifier.py        # Path, extension and MIME classification
│   ├── rules.py             # The only reader of config/rules.yaml
│   ├── services.py          # Is the rest of the local dev stack up?
│   ├── projects.py          # Project roots — trees kept whole
│   ├── organizer.py         # Folder structure planning
│   ├── previewer.py         # Dry-run previews
│   ├── executor.py          # Executes planned file operations
│   ├── context_detector.py  # Semantic context detection
│   ├── ai_tagger.py         # AI tagging for all file types
│   ├── image_analyzer.py    # Image metadata extraction
│   ├── image_content_analyzer.py  # CLIP-based image content analysis
│   ├── image_db.py          # Image metadata persistence
│   ├── metadata_writer.py
│   ├── parallel.py          # Per-stage execution policy (threads/processes/serial)
│   ├── pipeline.py          # The pipeline as a library (CLI + server both call this)
│   └── db.py                # MySQL connection (SQLAlchemy)
├── classify/                # Content extraction + classification ladder
│   ├── extract.py           # Any supported file -> plain text
│   ├── vision.py            # Image -> caption + OCR + EXIF
│   ├── video.py             # Video -> ffprobe metadata + captioned frame
│   ├── engine.py            # Rules -> local LLM -> cloud escalation
│   └── cloud.py             # Claude tier, with a hard spend cap
├── search/                  # RAG index + user metadata
│   ├── rag_store.py         # Embeddings, vector store, hybrid search
│   └── metadata_store.py    # User-added people/tags/notes
├── server/                  # FastAPI backend for the web UI
│   ├── app.py               # Routes
│   ├── jobs.py              # Jobs in child processes, progress, cancellation
│   └── security.py          # Path guards and file allowlist
├── web/                     # Single-page front end (no build step)
│   ├── index.html
│   └── js/app.js
├── database/
│   ├── schema/              # Table creation scripts
│   ├── migrations/          # Incremental schema changes
│   └── queries/             # Ad-hoc analysis queries
├── docs/                    # All guides and implementation notes
├── models/
│   └── file_info.py
├── scripts/                 # Maintenance, debug and release tooling
│   ├── reclassify_files.py  # Re-derive categories for existing DB rows
│   ├── import_cli_runs.py   # Historical CLI previews -> Jobs tab
│   └── debug_classification.py  # Why was THIS file classified that way?
├── tests/                   # Test suite (pytest)
├── utils/                   # Cache, notifications, path metadata
│   ├── mounts.py            # Mount preflight (ismount, not exists)
│   ├── trash.py             # Per-volume Trash, so deletion is reversible
│   └── protected.py         # Sidecars that must not be deleted as dupes
└── .workbench/jobs/         # One directory per run: manifest, plan, result
```

---

## 📦 Outputs

- `.scan_cache.json`: local file cache
- `logs/`: timestamped dry-run logs
- `CHANGELOG.md`: auto-generated history

---

## 🛡 Disclaimer

Always use `--dry-run` to preview changes before executing them. Use `--execute` only after validating operations.

---

## 🧑‍💻 Maintainer

[📎 phelgetar @ GitHub](https://github.com/phelgetar)

---

## Web front end

File Workbench is documented in **[WORKBENCH.md](WORKBENCH.md)** — running the
server, the four screens, how each stage is parallelised, and the
rules → local → cloud classification ladder.

```bash
./.venv/bin/python -m server.app
```
