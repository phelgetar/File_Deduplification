# File Deduplication System

## 📦 Project Overview

An AI-enhanced Python utility for scanning, deduplicating, classifying, and organizing files across complex directory structures (e.g., NAS backups). It supports:

- 🔍 Top-level directory filtering with regex
- 🧠 AI classification (owner, category, year, etc.)
- 🧹 Exact duplicate detection via hashing
- 🗂️ Smart folder tree planning and preview
- 🧪 Dry-run preview with visual + file output
- 📝 Metadata embedding (optional)
- 💬 Slack/Email notifications (stubbed)
- 🖼️ GUI preview launcher (stubbed)

---

## 🚀 Features

### ✅ Smart Scanning
- Filter top-level subdirectories with `--filter` (supports multiple + regex)
- Parallelized scanning
- Caching for rapid re-runs

### ✅ Deduplication
- Multithreaded SHA256 hashing
- Tracks duplicates by file content, not just name

### ✅ AI Classification
- Categorize by file type, owner, date
- OpenAI-driven logic

### ✅ Organization
- Logical folder structure generation
- Preview before applying
- GUI and CLI options

### ✅ Metadata
- Optionally writes metadata tags (e.g., EXIF, PDF metadata)

### ✅ Preview/Execution
- Dry-run mode with summary tree
- Logs: `--log-format json|txt`
- `--dry-run-log` for outputting planned actions

### ✅ Execution Control
- `--execute` requires confirmation
- Automatically creates target folder

### ✅ Notifications
- `--notify email|slack` (stub)

---

## 🧪 Tests

```bash
python -m unittest discover tests
```

---

## 📦 Setup

### 🐍 Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 🔑 Environment Variables (`.env`)
```env
OPENAI_API_KEY=sk-...
```

Set your OpenAI key:
```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

---

## 🧪 Sample Run

```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw --filter canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

To apply changes:
```bash
python main.py /Volumes/home --execute
```

---
## 🗂 Project Structure
---

```
file_deduplicator/
├── core/               # Main logic modules
├── models/             # FileInfo dataclass
├── tests/              # Unit tests
├── scripts/            # Utility scripts (.env setup)
├── main.py             # Orchestration script
├── requirements.txt    # Dependencies
├── setup.py            # Packaging
├── README.md           # This file
```

```
File_Deduplication/
├── core/
│   ├── scanner.py
│   ├── hasher.py
│   ├── classifier.py
│   ├── organizer.py
│   ├── previewer.py
│   ├── executor.py
│   ├── metadata_writer.py
├── models/
│   ├── file_info.py
├── tests/
│   ├── test_scanner.py
│   ├── test_hasher.py
│   ├── test_classifier.py
│   ├── test_organizer.py
│   ├── test_executor.py
│   └── test_data/
├── main.py
├── requirements.txt
├── version.yaml
├── README.md
├── .env
└── .scan_cache.json
```

---

## 🔧 Git Commit Suggestions

```bash
git init
git add .
git commit -m "Initial commit: full deduplication system with scanning, classification, filtering, and execution pipeline"
```

To push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/File_Deduplication.git
git push -u origin main
```

---

## 📬 Future Ideas
- Real Slack webhook support
- SMTP notifications
- Full GUI file browser
- File-type-specific metadata analyzers
