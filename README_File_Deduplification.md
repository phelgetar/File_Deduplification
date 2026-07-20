# 📁 File_Deduplification

A powerful, AI-assisted file deduplication and organization tool that intelligently scans, hashes, classifies, and previews file operations — supporting dry runs, structured logs, database caching, and GUI previews.

---

## 🚀 Features

- 🔍 **Recursive File Scanning** with regex filters for directory roots
- 🧠 **AI Classification** using OpenAI to categorize files intelligently
- 🧮 **SHA256 Hashing** to detect duplicates and avoid reprocessing
- 🗂️ **Folder Organization** based on classification and metadata
- 🧪 **Dry Run Preview** with printable and visual tree structure
- 🧾 **Log Output** in `.txt` or `.json` formats
- 🗃️ **MySQL-based Caching** for incremental, resumable runs
- 💬 **Slack/Email Notification** after scan and planning complete
- 🖥️ **GUI Preview Stub** for future interactive visual confirmation
- ♻️ **Safe Execution Mode** with rollback and script patching
- 🧰 **Versioned Git Integration** with release automation

---

## 🏗️ Directory Structure

```bash
File_Deduplification/
├── core/                  # Main logic: scanner, hasher, classifier, executor
├── utils/                 # Notification, GUI, cache, versioning helpers
├── scripts/               # Patch management, release, version bumping
├── .env                   # DB credentials, OpenAI API key
├── main.py                # CLI entry point
├── executor.py            # Execution logic
├── requirements.txt
└── README.md              # You are here
```

---

## ⚙️ Command Line Usage

```bash
python main.py <source_directory> --base-dir <target_directory> [options]
```

### 🔧 Options:

| Flag | Description |
|------|-------------|
| `--base-dir`            | Target directory for organized output (required) |
| `--filter canadytw*`    | Regex/wildcard directory root filter (supports multiple) |
| `--dry-run-log`         | Enable logging of dry-run to file |
| `--log-format txt|json` | Choose log output format |
| `--notify slack|email`  | Send notification on completion |
| `--gui`                 | Launch GUI stub for preview |
| `--execute`             | Actually perform the file moves |
| `--write-metadata`      | Save classification metadata for files |
| `--cache-db`            | Use MySQL DB for hash/cache persistence |
| `--help`                | Show help message and exit |

---

## 🧪 Example Commands

### Dry Run with Preview + Slack Notification
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

### Full Execution
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw \
  --execute
```

---

## 🗃️ .env Configuration

Create a `.env` file in the root directory with the following:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx
DATABASE_URL=mysql+pymysql://jarheads_0231:your_password@localhost:3306/File_Deduplification
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

---

## 🧰 Development & Patch Workflow

### Apply a Patch from ZIP
```bash
./scripts/push_patch.sh
```

### Roll Back Last Patch
```bash
./scripts/rollback_patch.sh
```

---

## 📦 Versioning & Releases

- `make bump` – Increments patch version in `version.py`
- `make changelog` – Updates `CHANGELOG.md` with commit history
- `make release` – Commits, pushes, and publishes GitHub release

Ensure you're authenticated via `gh auth login` to use GitHub CLI integration.

---

## 🧩 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Main packages:
- `openai`
- `sqlalchemy`
- `pymysql`
- `slack_sdk`
- `python-dotenv`

---

## 📌 Roadmap

- [x] Caching with MySQL
- [x] CLI dry-run and logging
- [x] Basic GUI stub launcher
- [ ] Interactive GUI interface
- [ ] Restore/move conflict resolution
- [ ] Cross-platform daemon support

---

## 🚀 Features

- 🔍 **Recursive File Scanning** with regex filters for directory roots
- 🧠 **AI Classification** using OpenAI to categorize files intelligently
- 🧮 **SHA256 Hashing** to detect duplicates and avoid reprocessing
- 🗂️ **Folder Organization** based on classification and metadata
- 🧪 **Dry Run Preview** with printable and visual tree structure
- 🧾 **Log Output** in `.txt` or `.json` formats
- 🗃️ **MySQL-based Caching** for incremental, resumable runs
- 💬 **Slack/Email Notification** after scan and planning complete
- 🖥️ **GUI Preview Stub** for future interactive visual confirmation
- ♻️ **Safe Execution Mode** with rollback and script patching
- 🧰 **Versioned Git Integration** with release automation

---

## 🏗️ Directory Structure

```bash
File_Deduplification/
├── core/                  # Main logic: scanner, hasher, classifier, executor
├── utils/                 # Notification, GUI, cache, versioning helpers
├── scripts/               # Patch management, release, version bumping
├── .env                   # DB credentials, OpenAI API key
├── main.py                # CLI entry point
├── executor.py            # Execution logic
├── requirements.txt
└── README.md              # You are here
```

---

## ⚙️ Command Line Usage

```bash
python main.py <source_directory> --base-dir <target_directory> [options]
```

### 🔧 Options:

| Flag | Description |
|------|-------------|
| `--base-dir`            | Target directory for organized output (required) |
| `--filter canadytw*`    | Regex/wildcard directory root filter (supports multiple) |
| `--dry-run-log`         | Enable logging of dry-run to file |
| `--log-format txt|json` | Choose log output format |
| `--notify slack|email`  | Send notification on completion |
| `--gui`                 | Launch GUI stub for preview |
| `--execute`             | Actually perform the file moves |
| `--write-metadata`      | Save classification metadata for files |
| `--cache-db`            | Use MySQL DB for hash/cache persistence |
| `--help`                | Show help message and exit |

---

## 🧪 Example Commands

### Dry Run with Preview + Slack Notification
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

### Full Execution
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw \
  --execute
```

---

## 🗃️ .env Configuration
# 📁 File_Deduplification

A powerful, AI-assisted file deduplication and organization tool that intelligently scans, hashes, classifies, and previews file operations — supporting dry runs, structured logs, database caching, and GUI previews.

---

## 🚀 Features

- 🔍 **Recursive File Scanning** with regex filters for directory roots
- 🧠 **AI Classification** using OpenAI to categorize files intelligently
- 🧮 **SHA256 Hashing** to detect duplicates and avoid reprocessing
- 🗂️ **Folder Organization** based on classification and metadata
- 🧪 **Dry Run Preview** with printable and visual tree structure
- 🧾 **Log Output** in `.txt` or `.json` formats
- 🗃️ **MySQL-based Caching** for incremental, resumable runs
- 💬 **Slack/Email Notification** after scan and planning complete
- 🖥️ **GUI Preview Stub** for future interactive visual confirmation
- ♻️ **Safe Execution Mode** with rollback and script patching
- 🧰 **Versioned Git Integration** with release automation

---

## 🏗️ Directory Structure

```bash
File_Deduplification/
├── core/                  # Main logic: scanner, hasher, classifier, executor
├── utils/                 # Notification, GUI, cache, versioning helpers
├── scripts/               # Patch management, release, version bumping
├── .env                   # DB credentials, OpenAI API key
├── main.py                # CLI entry point
├── executor.py            # Execution logic
├── requirements.txt
└── README.md              # You are here
```

---

## ⚙️ Command Line Usage

```bash
python main.py <source_directory> --base-dir <target_directory> [options]
```

### 🔧 Options:

| Flag | Description |
|------|-------------|
| `--base-dir`            | Target directory for organized output (required) |
| `--filter canadytw*`    | Regex/wildcard directory root filter (supports multiple) |
| `--dry-run-log`         | Enable logging of dry-run to file |
| `--log-format txt|json` | Choose log output format |
| `--notify slack|email`  | Send notification on completion |
| `--gui`                 | Launch GUI stub for preview |
| `--execute`             | Actually perform the file moves |
| `--write-metadata`      | Save classification metadata for files |
| `--cache-db`            | Use MySQL DB for hash/cache persistence |
| `--help`                | Show help message and exit |

---

## 🧪 Example Commands

### Dry Run with Preview + Slack Notification
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

### Full Execution
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw \
  --execute
```

---

## 🗃️ .env Configuration

Create a `.env` file in the root directory with the following:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx
DATABASE_URL=mysql+pymysql://jarheads_0231:your_password@localhost:3306/File_Deduplification
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

---

## 🧰 Development & Patch Workflow

### Apply a Patch from ZIP
```bash
./scripts/push_patch.sh
```

### Roll Back Last Patch
```bash
./scripts/rollback_patch.sh
```

---

## 📦 Versioning & Releases

- `make bump` – Increments patch version in `version.py`
- `make changelog` – Updates `CHANGELOG.md` with commit history
- `make release` – Commits, pushes, and publishes GitHub release

Ensure you're authenticated via `gh auth login` to use GitHub CLI integration.

---

## 🧩 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Main packages:
- `openai`
- `sqlalchemy`
- `pymysql`
- `slack_sdk`
- `python-dotenv`

---

## 📌 Roadmap

- [x] Caching with MySQL
- [x] CLI dry-run and logging
- [x] Basic GUI stub launcher
- [ ] Interactive GUI interface
- [ ] Restore/move conflict resolution
- [ ] Cross-platform daemon support

---

## 🚀 Features

- 🔍 **Recursive File Scanning** with regex filters for directory roots
- 🧠 **AI Classification** using OpenAI to categorize files intelligently
- 🧮 **SHA256 Hashing** to detect duplicates and avoid reprocessing
- 🗂️ **Folder Organization** based on classification and metadata
- 🧪 **Dry Run Preview** with printable and visual tree structure
- 🧾 **Log Output** in `.txt` or `.json` formats
- 🗃️ **MySQL-based Caching** for incremental, resumable runs
- 💬 **Slack/Email Notification** after scan and planning complete
- 🖥️ **GUI Preview Stub** for future interactive visual confirmation
- ♻️ **Safe Execution Mode** with rollback and script patching
- 🧰 **Versioned Git Integration** with release automation

---

## 🏗️ Directory Structure

```bash
File_Deduplification/
├── core/                  # Main logic: scanner, hasher, classifier, executor
├── utils/                 # Notification, GUI, cache, versioning helpers
├── scripts/               # Patch management, release, version bumping
├── .env                   # DB credentials, OpenAI API key
├── main.py                # CLI entry point
├── executor.py            # Execution logic
├── requirements.txt
└── README.md              # You are here
```

---

## ⚙️ Command Line Usage

```bash
python main.py <source_directory> --base-dir <target_directory> [options]
```

### 🔧 Options:

| Flag | Description |
|------|-------------|
| `--base-dir`            | Target directory for organized output (required) |
| `--filter canadytw*`    | Regex/wildcard directory root filter (supports multiple) |
| `--dry-run-log`         | Enable logging of dry-run to file |
| `--log-format txt|json` | Choose log output format |
| `--notify slack|email`  | Send notification on completion |
| `--gui`                 | Launch GUI stub for preview |
| `--execute`             | Actually perform the file moves |
| `--write-metadata`      | Save classification metadata for files |
| `--cache-db`            | Use MySQL DB for hash/cache persistence |
| `--help`                | Show help message and exit |

---

## 🧪 Example Commands

### Dry Run with Preview + Slack Notification
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw canamac \
  --dry-run-log \
  --log-format txt \
  --notify slack \
  --gui
```

### Full Execution
```bash
python main.py /Volumes/home \
  --base-dir /Volumes/home/SortedPreview \
  --filter canadytw \
  --execute
```

---

## 🗃️ .env Configuration

Create a `.env` file in the root directory with the following:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx
DATABASE_URL=mysql+pymysql://jarheads_0231:your_password@localhost:3306/File_Deduplification
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

---

## 🧰 Development & Patch Workflow

### Apply a Patch from ZIP
```bash
./scripts/push_patch.sh
```

### Roll Back Last Patch
```bash
./scripts/rollback_patch.sh
```

---

## 📦 Versioning & Releases

-
Create a `.env` file in the root directory with the following:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx
DATABASE_URL=mysql+pymysql://jarheads_0231:your_password@localhost:3306/File_Deduplification
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

---

## 🧰 Development & Patch Workflow

### Apply a Patch from ZIP
```bash
./scripts/push_patch.sh
```

### Roll Back Last Patch
```bash
./scripts/rollback_patch.sh
```

---

## 📦 Versioning & Releases

- `make bump` – Increments patch version in `version.py`
- `make changelog` – Updates `CHANGELOG.md` with commit history
- `make release` – Commits, pushes, and publishes GitHub release

Ensure you're authenticated via `gh auth login` to use GitHub CLI integration.

---

## 🧩 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

Main packages:
- `openai`
- `sqlalchemy`
- `pymysql`
- `slack_sdk`
- `python-dotenv`

---

## 📌 Roadmap

- [x] Caching with MySQL
- [x] CLI dry-run and logging
- [x] Basic GUI stub launcher
- [ ] Interactive GUI interface
- [ ] Restore/move conflict resolution
- [ ] Cross-platform daemon support

---

## 🛡 Disclaimer

Always use `--dry-run` to preview changes before executing them. Use `--execute` only after validating operations.

---

## 🧑‍💻 Maintainer

[📎 phelgetar @ GitHub](https://github.com/phelgetar)
