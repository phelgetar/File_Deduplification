# Changelog

## [0.3.0] – 2025-11-04

### Added
- `scripts/update_core.sh`: Now validates extracted Python file syntax after unzip.
- `scripts/rollback_core.sh`: Allows restoring the most recent core/ backup.
- JSON log support and dry-run change preview from CLI.
- Optional directory filtering via `--filter` using multiple values and regex.

### Changed
- `core/hasher.py`: Checks and stores hashes using MySQL caching layer.
- `core/scanner.py`: Skips rescanning files whose size & mtime match cache.
- `core/executor.py`: Logs file move/delete operations to MySQL.

### Fixed
- ZIP generation now correctly flattens core files for proper extraction.
- Updated `update_core.sh` to prevent `core/core/` nesting errors.

### Security
- `.env` now securely stores OpenAI API key and MySQL credentials.

### 🔁 Core System Update — Version 0.4.0 (2025-11-04)

- Integrated MySQL-based deduplication cache and operation logging.
- Enhanced ZIP packaging to flatten files correctly during deploy.
- Added syntax-checking to core update script for safe merges.
- Introduced directory-level filtering using regex in main.py.
- rollback_core.sh script added to enable easy restoration of last known good state.
- CHANGELOG.md created for versioned tracking of features and patches.

## [v0.4.2] – 2025-11-04

- Core enhancements and MySQL caching added
- Syntax check added to update scripts
