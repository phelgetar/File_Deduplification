
# 📁 File_Deduplification

An AI-enhanced file deduplication and organization tool with **atomic package detection**, **intelligent size management**, **comprehensive file classification (250+ file types)**, database caching, Slack/email notifications, dry-run previews, and GUI preview support.

> 📘 **[Full User Guide (PDF)](docs/USER_GUIDE.pdf)** — every CLI switch with examples, project structure, version management, and the git workflow. Regenerate after CLI changes with `python scripts/generate_user_guide.py`.

## ⚠️ Before You Run

The tool never deletes anything, but know these before the first real run (full detail in the User Guide, section 2):

1. **Execution COPIES, it does not move.** `--execute` leaves every source file in place — originals are always safe, but the destination volume needs free space roughly equal to the organized data. Duplicates are marked, never deleted.
2. **Never put `--base-dir` inside the source tree** — the next scan would ingest the organized copies and double-count everything.
3. **Files above `--metadata-only-size` are not hashed** — identical large videos will *not* be detected as duplicates.
4. **Hidden files (dotfiles) and `.dedupignore` matches are always skipped** — review `.dedupignore` before assuming full coverage.
5. **Ctrl+C is only safe with `--use-db`** — with it, re-running the same command resumes from the cache; without it, all progress is lost.
6. **Always dry-run first** — read the proposed tree before re-running with `--execute`.

---

## 🚀 Features

### Core Capabilities
- 🔍 **Recursive file scanning** with support for regex and wildcard filters, plus a 10-second progress heartbeat on long walks
- 🦙 **Local LLM classification fallback** (`--llm-classify`) - files the rule-based classifier can't place are classified by a local Ollama model from filename, path, and content; nothing leaves your machine
- 🧵 **Parallel hashing** (`--workers`) - multithreaded SHA256 hashing overlaps network reads for a large speedup on NAS volumes
- ♻️ **Resumable runs** - every hash commits to the database immediately; Ctrl+C exits cleanly and re-running the same command skips unchanged files via the cache
- 💾 **Batch checkpoints** (`--batch-size`) - periodic progress summaries during hashing
- 📦 **Atomic package detection** - treats .app, .pkg, .dmg as single units (18-60x faster!)
- 🔑 **Hash-based duplicate detection** (SHA256) with MySQL caching support
- 🤖 **AI-powered classification** - 18 categories, 250+ file types
- 📏 **Intelligent large file handling** - metadata-only mode for files above configurable size threshold
- 🗂️ **Folder structure planning** based on intelligent grouping (year/type/owner)
- 🧪 **Dry-run preview** with optional GUI and summary logs
- 📦 **Execution of proposed file operations** with confirmation prompts
- 🔔 **Notifications** via Slack or email
- 💾 **Logging** in `.json` or `.txt` formats
- 🧰 **Versioned Git workflow** with release automation
- ♻️ **Patch and rollback support** for safe updates

### 🆕 New in July 2026

#### **🦙 Local LLM Classification Fallback**
- New `--llm-classify` flag sends files no rule can classify to a local Ollama model (default `llama3.1:8b`)
- Uses filename, path context, and a 1KB content snippet for text-like files; binary content is detected and skipped
- Structured output constrained to the known category list — the model cannot invent categories
- Results cached per content hash: duplicates cost a single LLM call
- Degrades gracefully when the Ollama server is not running
- Configure via `OLLAMA_HOST` / `LLM_MODEL` in `.env`

#### **🧵 Parallel Hashing with Resume**
- `--workers N` (default 4) hashes files on a thread pool — a large speedup on network volumes; try 8 for a fast NAS
- Every completed hash commits to MySQL immediately: **Ctrl+C loses at most the files in flight**
- Re-running the same command resumes from the cache — unchanged files are skipped without reading a byte (`(cached)` in the log)
- `--batch-size N` (default 500) adds periodic checkpoint summaries during hashing

#### **🔌 Database Circuit Breaker**
- If MySQL dies mid-run, a circuit breaker trips after 3 consecutive failures: one clear error, then the run continues without persistence (no per-file timeout stalls)
- `--execute` is refused after a trip, and an in-progress execution stops cleanly before its next file move — file operations are never performed unlogged
- Connection attempts are bounded to 5 seconds

#### **⏳ Scan Progress Heartbeat**
- Long directory walks (network shares) log progress every 10 seconds: files matched, directories visited, and the current directory
- A completion summary reports totals and elapsed time

#### **📘 PDF User Guide**
- [docs/USER_GUIDE.pdf](docs/USER_GUIDE.pdf) documents every switch with examples; regenerate with `python scripts/generate_user_guide.py`

### 🆕 New in v0.9.0

#### **🤖 AI Tagging for ALL Files**
- Semantic analysis generates intelligent tags for ALL file types (not just images)
- Tags generated from path context, directory structure, filename analysis
- Semantic context detection (Personal/Disability/VA, Work, Education)
- Database storage in `file_tags` table with tag source tracking
- Example: Work documents automatically tagged with "Work", "Project", "2024"

#### **📁 File Type Filtering System**
- New `--file-types` flag for selective scanning by file type groups
- 20+ predefined groups: images, videos, audio, docs, word_docs, presentations, code, etc.
- Hierarchical support: "media" includes images, videos, and audio
- Comma-separated multiple types: `--file-types images,videos`
- Use `--list-file-types` to see all available groups

#### **🎨 Enhanced Image Content Analysis**
- CLIP AI model analyzes image content (objects, scenes, people)
- Tags saved to unified `file_tags` table
- Combined with path-based semantic tags for comprehensive tagging
- Example: Wedding photo tagged with "Wedding", "People", "2020", "celebration"

#### **🐛 Critical Fixes**
- Fixed root_folder double-nesting bug (no more `/Documents - 42739/Documents - 42739/`)
- Fixed path metadata extraction to prefer backup-style folders ("Documents - 42739" over "Documents")
- Disabled conflicting semantic context patterns that caused wrong organization
- Files now correctly organized to Media/Images/, Docs/Word/, etc.

### 🆕 From v0.8.0

#### **⚡ Atomic Package Detection (Major Performance Boost!)**
- Automatically detects macOS packages (.app, .pkg, .dmg)
- Treats packages as single units instead of scanning thousands of internal files
- Hashes entire package directory for consistent duplicate detection
- **18-60x performance improvement** when scanning applications
- Example: HP Easy Start.app (2,500 files) scanned in 5 seconds instead of 5 minutes!

#### **Intelligent File Size Management**
- Configure size threshold (e.g., `--metadata-only-size 75MB`)
- Files above threshold: Fast metadata-only processing (no hashing)
- Files below threshold: Full hash-based deduplication
- Perfect for handling large video files, disk images, and archives

#### **Comprehensive File Classification**
- **18 categories** (up from 10): image, video, audio, document, spreadsheet, presentation, code, archive, data, font, installer, certificate, shortcut, scientific, backup, temporary, system, other
- **250+ file types** supported (up from ~50)
- **~90% reduction** in "other" classification
- Enhanced macOS/iOS file support

---

## 🧾 Example CLI Usage

### Basic Usage
```bash
# Note: --base-dir must be OUTSIDE the scanned tree (see warnings below)
python main.py /Volumes/home \
  --base-dir /Volumes/homes/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

### Recommended for NAS volumes (parallel + resumable + LLM)
```bash
# Interrupt with Ctrl+C any time — re-run the same command to resume
python main.py /Volumes/home \
  --base-dir /Volumes/homes/Organized \
  --use-db \
  --llm-classify \
  --metadata-only-size 100MB \
  --workers 8 \
  --dry-run-log
```

### With Intelligent Size Management (NEW!)
```bash
# Handle large files efficiently - metadata only for files > 75MB
python main.py /Users/yourname/Documents \
  --base-dir /organized \
  --use-db \
  --metadata-only-size 75MB \
  --dry-run-log

# Skip hashing for large video files (>1GB)
python main.py /Videos \
  --base-dir /organized_videos \
  --use-db \
  --metadata-only-size 1GB

# Process everything with full hashing (no size limit)
python main.py /Photos \
  --base-dir /organized_photos \
  --use-db
```

---

## ⚙️ CLI Options

| Option                    | Description                                                     |
|---------------------------|-----------------------------------------------------------------|
| `source`                  | Source directory to scan                                        |
| `--base-dir`              | Target directory for sorted files                               |
| `--filter`                | One or more directory name filters                              |
| `--max-files`             | Maximum number of files to process                              |
| `--file-types`            | **NEW**: Filter by file type groups (e.g., `images`, `docs`, `media`). Use comma for multiple: `images,videos` |
| `--list-file-types`       | **NEW**: List all available file type groups and exit           |
| `--analyze-images`        | Extract and store comprehensive metadata from image files       |
| `--ai-tagging`            | Use AI to identify image content (objects, scenes, people)      |
| `--metadata-only-size`    | Files larger than this size will only have metadata stored (no hashing). Format: `75MB`, `1GB`, `500KB` |
| `--dry-run-log`           | Save dry-run results to log file                                |
| `--log-format`            | `json` or `txt` format for logs                                 |
| `--notify`                | `slack` or `email` notifications                                |
| `--execute`               | Apply changes (without this = dry-run)                          |
| `--write-metadata`        | Write JSON metadata sidecar files                               |
| `--ignore-errors`         | Skip files with access errors                                   |
| `--use-db`                | Enable database logging and caching                             |
| `--gui`                   | Show a GUI interface for preview                                |

---

## 🎯 File Classification Categories

The system now supports **18 categories** with **250+ file types**:

| Category       | Examples                                  | Count  |
|----------------|-------------------------------------------|--------|
| **image**      | .jpg, .png, .heic, .raw, .psd            | 22     |
| **video**      | .mp4, .mov, .mkv, .vob, .ts              | 17     |
| **audio**      | .mp3, .flac, .opus, .aiff, .mid          | 13     |
| **document**   | .pdf, .docx, .tex, .epub, .pages         | 13     |
| **spreadsheet**| .xlsx, .csv, .ods, .numbers              | 7      |
| **presentation**| .pptx, .odp, .key                       | 4      |
| **code**       | .py, .js, .swift, .rs, .lisp, .ps1       | 60+    |
| **archive**    | .zip, .dmg, .iso, .ova, .mdzip           | 22     |
| **data**       | .json, .xml, .sqlite, .toml, .ini        | 18     |
| **font**       | .ttf, .otf, .woff, .woff2                | 7      |
| **installer**  | .exe, .pkg, .dmg, .apk, .msu             | 18     |
| **certificate**| .p7b, .cer, .pem, .key, .pfx             | 12     |
| **shortcut**   | .lnk, .webloc, .url, .rdp                | 6      |
| **scientific** | .mat, .hdf5, .fits, .npy, .rdata         | 11     |
| **backup**     | .bak, .old, .orig, .swp                  | 6      |
| **temporary**  | .tmp, .crdownload, .cache, .part         | 7      |
| **system**     | .plist, .strings, .nib, Makefile         | 15+    |
| **other**      | Unrecognized formats                      | varies |

See [docs/CLASSIFICATION_IMPROVEMENTS.md](docs/CLASSIFICATION_IMPROVEMENTS.md) for complete list of all 250+ file types.

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

# Optional: local LLM classification fallback (--llm-classify)
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.1:8b
```

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
├── CHANGELOG.md
├── config/                  # YAML config + folder mapping rules
│   ├── file_type_groups.yaml
│   ├── folder_mapping.py
│   ├── folder_mappings.yaml
│   ├── image_ai_categories.yaml
│   └── semantic_paths.yaml
├── core/                    # Application library code
│   ├── main.py              # CLI implementation
│   ├── scanner.py           # Recursive scan + atomic package detection
│   ├── hasher.py            # SHA256 hashing
│   ├── deduplicator.py      # Duplicate detection
│   ├── classifier.py        # 18-category file classification
│   ├── organizer.py         # Folder structure planning
│   ├── previewer.py         # Dry-run previews
│   ├── executor.py          # Executes planned file operations
│   ├── context_detector.py  # Semantic context detection
│   ├── ai_tagger.py         # AI tagging for all file types
│   ├── image_analyzer.py    # Image metadata extraction
│   ├── image_content_analyzer.py  # CLIP-based image content analysis
│   ├── image_db.py          # Image metadata persistence
│   ├── metadata_writer.py
│   └── db.py                # MySQL connection (SQLAlchemy)
├── database/
│   ├── schema/              # Table creation scripts
│   ├── migrations/          # Incremental schema changes
│   └── queries/             # Ad-hoc analysis queries
├── docs/                    # All guides and implementation notes
├── models/
│   └── file_info.py
├── scripts/                 # Dev/release automation + debug tools
├── tests/                   # Test suite (pytest)
└── utils/                   # Cache, GUI, notifications, path metadata
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
