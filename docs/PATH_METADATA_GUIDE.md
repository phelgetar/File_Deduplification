# Path Metadata Extraction Guide

## Overview

The system now automatically extracts metadata from your directory structure and embeds it in the file metadata. This is perfect for Apple backup structures where folder names contain meaningful information.

---

## 🎯 How It Works

### Example Path
```
/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
```

### Extracted Metadata
```json
{
  "root_folder": "Documents - 2996KD",
  "relative_path": "Pictures/Land-Pics/8May16",
  "parent_folders": ["Pictures", "Land-Pics", "8May16"],
  "tags": ["Pictures", "Land-Pics", "8May16"],
  "date_tags": ["8May16"],
  "category_tags": ["Pictures", "Land-Pics"]
}
```

---

## 📁 Root Structure Preservation

The system **preserves your Apple backup folder structure**:

### Your Structure
```
canadytw/
├── Desktop/
│   ├── Desktop
│   ├── Desktop - 2996KD
│   ├── Desktop - 42739
│   ├── Desktop - Fratricide (2)
│   ├── Desktop - Teufelshunde
├── Documents/
│   ├── Documents
│   ├── Documents - 2996KD
│   ├── Documents - 42739
```

### Organized Output
```
organized/
├── Desktop - 2996KD/
│   ├── 2024/
│   │   ├── image/
│   │   │   └── owner/
│   │   │       └── file.jpg
│   │   └── document/
│   │       └── owner/
│   │           └── file.pdf
├── Desktop - Teufelshunde/
│   ├── 2024/
│   │   └── code/
│   │       └── owner/
│   │           └── script.py
```

The root structure names (**"Desktop - 2996KD"**, **"Desktop - Teufelshunde"**, etc.) are **preserved exactly** as they appear in your source.

---

## 🏷️ Metadata Tags

### What Gets Extracted

| Element | Description | Example |
|---------|-------------|---------|
| **Root Folder** | Apple backup structure name | "Documents - 2996KD" |
| **Parent Folders** | All directories between root and file | ["Pictures", "Land-Pics", "8May16"] |
| **Category Tags** | Non-date folder names | ["Pictures", "Land-Pics"] |
| **Date Tags** | Folder names that look like dates | ["8May16"] |

### Date Detection

The system automatically detects folder names that look like dates:

| Pattern | Example | Detected |
|---------|---------|----------|
| `DMmmYY` | 8May16, 15Dec24 | ✅ Yes |
| `YYYY-MM-DD` | 2024-01-15 | ✅ Yes |
| `MM-DD-YYYY` | 01-15-2024 | ✅ Yes |
| `YYYYMMDD` | 20240115 | ✅ Yes |
| `MonthYYYY` | Jan2024, December2023 | ✅ Yes |

---

## 📄 Metadata File Format

When you use `--write-metadata`, each file gets a `.meta.json` sidecar file:

### Example: `IMG_0001.JPG.meta.json`
```json
{
  "original_path": "/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG",
  "hash": "a1b2c3d4e5f6...",
  "size": 2048576,
  "type": "image",
  "owner": "canadytw",
  "year": "2024",
  "is_duplicate": false,
  "path_metadata": {
    "root_folder": "Documents - 2996KD",
    "relative_path": "Pictures/Land-Pics/8May16",
    "parent_folders": ["Pictures", "Land-Pics", "8May16"],
    "tags": ["Pictures", "Land-Pics", "8May16"],
    "date_tags": ["8May16"],
    "category_tags": ["Pictures", "Land-Pics"]
  }
}
```

---

## 🚀 Usage

### Basic Scan with Path Metadata
```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan with metadata extraction (automatic)
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db
```

### With Metadata File Creation
```bash
# Extract metadata AND write .meta.json files
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### Preview What Will Happen
```bash
# Dry run to see the organization structure
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db \
  --dry-run-log
```

---

## 📊 Example Scenarios

### Scenario 1: School Documents

**Source Path:**
```
/Users/canadytw/Documents/Documents - 2996KD/School/CS101/Assignment1/main.py
```

**Extracted Metadata:**
- Root: "Documents - 2996KD"
- Tags: ["School", "CS101", "Assignment1"]
- Category: education (because filename starts with "CS")

**Output Path:**
```
/organized/Documents - 2996KD/2024/education/canadytw/main.py
```

**Metadata File (`main.py.meta.json`):**
```json
{
  "path_metadata": {
    "root_folder": "Documents - 2996KD",
    "tags": ["School", "CS101", "Assignment1"],
    "category_tags": ["School", "CS101", "Assignment1"]
  }
}
```

### Scenario 2: Photos with Date

**Source Path:**
```
/Users/canadytw/Desktop/Desktop - Teufelshunde/Photos/Vacation/15Dec2024/beach.jpg
```

**Extracted Metadata:**
- Root: "Desktop - Teufelshunde"
- Tags: ["Photos", "Vacation", "15Dec2024"]
- Date Tags: ["15Dec2024"]
- Category Tags: ["Photos", "Vacation"]

**Output Path:**
```
/organized/Desktop - Teufelshunde/2024/image/canadytw/beach.jpg
```

### Scenario 3: Work Documents

**Source Path:**
```
/Users/canadytw/Documents/Documents - 42739/Work/Reports/Q1-2024/sales.xlsx
```

**Extracted Metadata:**
- Root: "Documents - 42739"
- Tags: ["Work", "Reports", "Q1-2024"]
- Date Tags: [] (Q1-2024 doesn't match date pattern)
- Category Tags: ["Work", "Reports", "Q1-2024"]

**Output Path:**
```
/organized/Documents - 42739/2024/spreadsheet/canadytw/sales.xlsx
```

---

## 🛠️ Configuration

### Enable/Disable Root Structure Preservation

By default, root structure is **preserved**. To change this behavior, modify `core/organizer.py`:

```python
# In main.py, when calling plan_organization:
plan = plan_organization(
    classified,
    base_dir_path,
    preserve_root_structure=True  # Set to False to disable
)
```

### Custom Folder Structure

You can customize the organization structure by modifying `plan_organization()` in `core/organizer.py`:

```python
# Current structure: root/year/type/owner/filename
# Example custom: root/type/year/filename

subfolders = []
if root_folder:
    subfolders.append(root_folder)
if file_info.type:  # Changed order
    subfolders.append(file_info.type)
if file_info.year:  # Changed order
    subfolders.append(str(file_info.year))
# Remove owner from structure
```

---

## 🔍 Querying Metadata

### Find Files by Tag

If you're writing metadata to database (future feature), you could query:

```sql
-- Files with specific path tag
SELECT path, path_metadata
FROM files
WHERE path_metadata LIKE '%Land-Pics%';

-- Files from specific root structure
SELECT path, path_metadata
FROM files
WHERE path_metadata LIKE '%"root_folder": "Documents - 2996KD"%';
```

### Search Metadata Files

```bash
# Find all .meta.json files with specific tag
find /organized -name "*.meta.json" -exec grep -l "Land-Pics" {} \;

# View metadata for specific file
cat /organized/Documents\ -\ 2996KD/2024/image/canadytw/IMG_0001.JPG.meta.json | jq .path_metadata
```

---

## 💡 Best Practices

### 1. Use Meaningful Folder Names

✅ **Good folder names:**
- `Land-Pics` (descriptive category)
- `8May16` (date format)
- `CS101` (course identifier)
- `Work-Projects` (clear purpose)

❌ **Poor folder names:**
- `Folder1`, `Stuff`, `Misc` (too generic, will be ignored)
- `temp`, `data` (common names, filtered out)

### 2. Consistent Date Formats

Use consistent date formats in folder names:
- `DMmmYY`: 8May16, 15Dec24
- `YYYY-MM-DD`: 2024-01-15
- `MonthYYYY`: Jan2024

### 3. Always Use --write-metadata for Backups

```bash
# Create metadata files for all your important files
python main.py /source \
  --base-dir /backup \
  --use-db \
  --write-metadata \
  --execute
```

This ensures you can always trace files back to their original location and context.

### 4. Test Before Executing

```bash
# Always dry-run first
python main.py /source --base-dir /output --use-db --dry-run-log

# Review the preview
cat dry_run_preview_*.txt

# Execute only if satisfied
python main.py /source --base-dir /output --use-db --execute
```

---

## 🧪 Testing

### Test Path Metadata Extraction

```bash
# Run the test utility
cd /Users/canadytw/PycharmProjects/File_Deduplification
python3 utils/path_metadata.py
```

**Expected Output:**
```
Path: /Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
Metadata: {'root_folder': 'Documents - 2996KD', 'relative_path': 'Pictures/Land-Pics/8May16', ...}
Formatted: Root: Documents - 2996KD | Categories: Pictures, Land-Pics | Dates: 8May16
Owner: 2996KD
```

### Verify Metadata Extraction During Scan

```bash
# Run with debug logging
python main.py /source --base-dir /output --use-db 2>&1 | grep "Path tags"
```

Look for lines like:
```
    🏷️  Path tags: Land-Pics, 8May16
    🏷️  Path tags: CS101, Assignment1
```

---

## 🔧 Troubleshooting

### Issue: Root Folder Not Detected

**Symptom:** Files organized without root structure preservation

**Cause:** Root folder pattern not recognized

**Solution:**
1. Check that your root folders match Apple backup pattern:
   - Standard: "Desktop", "Documents", "Pictures"
   - Extended: "Desktop - 2996KD", "Documents - Teufelshunde"

2. If using custom pattern, modify `extract_path_metadata()` in `utils/path_metadata.py`:
   ```python
   apple_folders = {'Desktop', 'Documents', 'YourCustomFolder'}
   ```

### Issue: Tags Not Extracted

**Symptom:** No tags in metadata

**Cause:** Folder names filtered as generic

**Solution:**
Check the `extract_path_metadata()` function. It filters out generic names:
```python
# Folders that are skipped
skip_names = {'files', 'data', 'stuff', 'misc', 'other', 'folder'}
```

Rename your folders to be more specific.

### Issue: Date Not Recognized

**Symptom:** Date folder treated as category tag

**Solution:**
The date pattern may not be recognized. Add your pattern to `is_date_like()` in `utils/path_metadata.py`:
```python
patterns = [
    r'\d{1,2}[A-Za-z]{3}\d{2,4}',  # 8May16
    r'your-custom-pattern',         # Add here
]
```

---

## 📈 Benefits

### 1. Searchability
- Search files by original context
- Find related files from same event/project
- Trace file lineage

### 2. Organization
- Preserve meaningful structure
- Maintain Apple backup hierarchy
- Logical file grouping

### 3. Backup Safety
- Full path history in metadata
- Original location preserved
- Easy restoration

### 4. Documentation
- Self-documenting file collections
- Context preserved with files
- Audit trail for file movements

---

**Version:** 0.1.0
**Last Updated:** 2025-11-14
**Related Modules:** `utils/path_metadata.py`, `core/hasher.py`, `core/organizer.py`, `core/executor.py`
