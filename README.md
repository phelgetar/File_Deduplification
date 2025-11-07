
# 📁 File_Deduplification

An AI-enhanced file deduplication and organization tool with database caching, Slack/email notifications, dry-run previews, and GUI preview support.

---

## 🚀 Features

- 🔍 Recursive file scanning with support for regex and wildcard filters
- 🔑 Hash-based duplicate detection (SHA256) with MySQL caching support
- 🤖 AI-powered classification using OpenAI
- 🗂️ Folder structure planning based on intelligent grouping
- 🧪 Dry-run preview with optional GUI and summary logs
- 📦 Execution of proposed file operations
- 🔔 Notifications via Slack or email
- 💾 Logging in `.json` or `.txt` formats
- 🧰 Versioned Git workflow with release automation
- ♻️ Patch and rollback support for safe updates

---

## 🧾 Example CLI Usage

```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

---

## ⚙️ CLI Options

| Option               | Description                                      |
|----------------------|--------------------------------------------------|
| `source`             | Source directory to scan                         |
| `--base-dir`         | Target directory for sorted files                |
| `--filter`           | One or more directory name filters               |
| `--dry-run-log`      | Save dry-run results to log file                 |
| `--log-format`       | `json` or `txt` format for logs                  |
| `--notify`           | `slack` or `email` notifications                 |
| `--execute`          | Apply changes (without this = dry-run)           |
| `--gui`              | Show a GUI interface for preview                 |

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
├── core/
│   ├── scanner.py
│   ├── hasher.py
│   ├── classifier.py
│   ├── executor.py
│   └── previewer.py
├── utils/
│   ├── gui.py
│   ├── cache.py
│   ├── notifications.py
│   ├── versioning.py
├── scripts/
│   ├── push_patch.sh
│   ├── rollback_patch.sh
│   ├── force_clean_push.sh
│   ├── validate_large_files.sh
│   └── gen_changelog.py
├── main.py
├── requirements.txt
├── .env
├── README.md
└── CHANGELOG.md
```

---

## 📦 Outputs

- `.scan_cache.json`: local file cache
- `logs/`: timestamped dry-run logs
- `CHANGELOG.md`: auto-generated history

---

## 📣 Credits

Created with ❤️ by [Your Name or Team]
