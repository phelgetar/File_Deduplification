
# 📁 File_Deduplification

An AI-enhanced file deduplication and organization tool with **atomic package detection**, **intelligent size management**, **comprehensive file classification (250+ file types)**, database caching, Slack/email notifications, dry-run previews, and GUI preview support.

---

## 🚀 Features

### Core Capabilities
- 🔍 **Recursive file scanning** with support for regex and wildcard filters
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
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
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

- Python 3.8+
- MySQL 8.x
- OpenAI API key
- Slack webhook URL (optional)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🔐 .env Configuration

Create a `.env` file with the following:

```env
OPENAI_API_KEY=your-api-key
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/File_Deduplification
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
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
