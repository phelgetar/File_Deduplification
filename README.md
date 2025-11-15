
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

### 🆕 New in v0.8.0

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
| `--metadata-only-size`    | **NEW**: Files larger than this size will only have metadata stored (no hashing). Format: `75MB`, `1GB`, `500KB` |
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

See `CLASSIFICATION_IMPROVEMENTS.md` for complete list of all 250+ file types.

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
├── CHANGELOG.md
├── CHANGELOG_LAST.md
├── File_Dedup_Table_Creation.sql
├── Makefile
├── README.md
├── README_File_Deduplification.md
├── __pycache__
├── backup
├── core
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── classifier.cpython-313.pyc
│   │   ├── db.cpython-313.pyc
│   │   ├── executor.cpython-313.pyc
│   │   ├── hasher.cpython-313.pyc
│   │   ├── metadata_writer.cpython-313.pyc
│   │   ├── organizer.cpython-313.pyc
│   │   ├── previewer.cpython-313.pyc
│   │   └── scanner.cpython-313.pyc
│   ├── classifier.py
│   ├── db.py
│   ├── executor.py
│   ├── hasher.py
│   ├── metadata_writer.py
│   ├── organizer.py
│   ├── previewer.py
│   └── scanner.py
├── dry_run_preview_20251111_132112.txt
├── file_sorting_package.py
├── main.py
├── models
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   └── file_info.cpython-313.pyc
│   └── file_info.py
├── patch_info.txt
├── preview_2025_11_04.txt
├── requirements.txt
├── scripts
│   ├── bump_version.py
│   ├── force_clean_push.sh
│   ├── gen_changelog.py
│   ├── push_patch.sh
│   ├── push_utils_patch.sh
│   ├── read_version.py
│   ├── release_v045.sh
│   ├── rollback_core.sh
│   ├── rollback_patch.sh
│   ├── setup_env.py
│   ├── setup_env.sh
│   ├── update_core.sh
│   ├── update_main_slack_support.sh
│   └── validate_large_files.sh
├── setup.py
├── tests
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── test_classifier.cpython-313.pyc
│   │   ├── test_executor.cpython-313.pyc
│   │   ├── test_hasher.cpython-313.pyc
│   │   ├── test_organizer.cpython-313.pyc
│   │   └── test_scanner.cpython-313.pyc
│   ├── test_classifier.py
│   ├── test_data
│   │   ├── financial_2021_john.pdf
│   │   └── sample1.txt
│   ├── test_executor.py
│   ├── test_hasher.py
│   ├── test_organizer.py
│   └── test_scanner.py
├── utils
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── cache.cpython-313.pyc
│   │   ├── gui.cpython-313.pyc
│   │   ├── notifications.cpython-313.pyc
│   │   └── versioning.cpython-313.pyc
│   ├── cache.py
│   ├── gui.py
│   ├── notifications.py
│   └── versioning.py
└── version.yaml

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
