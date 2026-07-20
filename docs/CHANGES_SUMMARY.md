# Recent Changes Summary

## Date: 2025-11-14

---

## ✅ 1. Hidden Files - Now Automatically Skipped

**What Changed:**
- Scanner now automatically ignores all hidden files and directories (starting with `.`)
- Includes `.DS_Store`, `.git`, `.vscode`, `.cache`, etc.
- Also skips files inside hidden directories

**Files Modified:**
- `core/scanner.py` - Added `is_hidden()` function

**Output Example:**
```
🔍 Scanning files...
Skipped 247 hidden files (starting with '.')
Found 3 atomic packages (.app, .pkg, .dmg) treated as single units
🧮 Files matched: 150
```

---

## ✅ 2. Certificate Category - Already Exists!

**Good News:**
The certificate category already exists with ALL your requested extensions plus more!

**Supported Extensions:**
- ✅ `.cer` (your request)
- ✅ `.csr` (your request)
- ✅ `.pem` (your request)
- ✅ `.pfx` (your request)
- Plus: `.p7b`, `.p12`, `.crt`, `.der`, `.key`, `.p7c`, `.spc`, `.pub`

**No changes needed!**

---

## ✅ 3. Education Category - NEW!

**What Changed:**
- Added brand new "education" category
- Automatically detects files with course prefixes

**Detected Prefixes:**
- **CS** (Computer Science) - e.g., `CS101_assignment.pdf`
- **CEG** (Computer Engineering) - e.g., `CEG3120_lab5.zip`
- **STAT** (Statistics) - e.g., `STAT401_homework.docx`
- **MAT** (Mathematics) - e.g., `MAT251_notes.txt`
- Also: ECON, PHYS, CHEM, BIO, ENG, MATH

**Files Modified:**
- `core/classifier.py` - Added education category detection

**Total Categories:** Now 19 (was 18)

---

## ✅ 4. SQL Queries for "Other" Files

**What Created:**
- `queries/find_other_files.sql` - 11 comprehensive SQL queries
- `QUERY_GUIDE.md` - Complete usage guide

**Most Useful Queries:**
1. Group "other" files by extension (shows what's missing)
2. Summary statistics
3. Largest unclassified files
4. Find potential education files

**Quick Usage:**
```bash
# Connect to database
mysql -u jarheads_0231 -p -D File_Deduplification

# Run queries
source queries/find_other_files.sql

# Or run specific query
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT SUBSTRING_INDEX(f.path, '.', -1) AS extension, COUNT(*) AS count
FROM files f LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other' GROUP BY extension ORDER BY count DESC;"
```

---

## ✅ 5. Path Metadata Extraction - NEW!

**What Changed:**
Major new feature! Automatically extracts metadata from your directory structure.

### Your Example:
```
/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
```

### Extracted Metadata:
```json
{
  "root_folder": "Documents - 2996KD",
  "tags": ["Pictures", "Land-Pics", "8May16"],
  "date_tags": ["8May16"],
  "category_tags": ["Pictures", "Land-Pics"]
}
```

**Files Created:**
- `utils/path_metadata.py` - Metadata extraction logic
- `PATH_METADATA_GUIDE.md` - Complete documentation

**Files Modified:**
- `models/file_info.py` - Added `path_metadata` field
- `core/hasher.py` - Extracts metadata during hashing
- `core/executor.py` - Writes metadata to `.meta.json` files
- `core/organizer.py` - Preserves root structure

### How It Works:

**Root Structure Preserved:**
```
organized/
├── Desktop - 2996KD/          ← Preserved exactly as in source
│   ├── 2024/
│   │   └── image/
│   │       └── canadytw/
│   │           └── file.jpg
├── Desktop - Teufelshunde/    ← Preserved exactly as in source
│   ├── 2024/
│   │   └── document/
│   │       └── canadytw/
│   │           └── file.pdf
```

**Metadata File (`file.jpg.meta.json`):**
```json
{
  "original_path": "/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG",
  "hash": "a1b2c3d4...",
  "size": 2048576,
  "type": "image",
  "path_metadata": {
    "root_folder": "Documents - 2996KD",
    "relative_path": "Pictures/Land-Pics/8May16",
    "tags": ["Pictures", "Land-Pics", "8May16"],
    "date_tags": ["8May16"],
    "category_tags": ["Pictures", "Land-Pics"]
  }
}
```

---

## ✅ 6. Extension Additions

**What Changed:**
Added support for additional file extensions based on user needs.

### .wzd Extension (Encryption Wizard)
- **Extension:** `.wzd`
- **Category:** `certificate`
- **Description:** Encryption Wizard files (encrypted financial/sensitive data)

### .qel Extension (Quicken)
- **Extension:** `.qel`
- **Category:** `financial`
- **Description:** Quicken Electronic Library files

**Files Modified:**
- `core/classifier.py` v0.7.1, v0.7.2 - Added extension support

---

## ✅ 7. Financial Category - NEW!

**What Changed:**
Created dedicated "financial" category for all financial and tax-related files.

**Supported Extensions:**

### Quicken Files (10 extensions)
- `.qdf` - Quicken Data File (primary)
- `.qel` - Quicken Electronic Library
- `.qfx` - Quicken Financial Exchange
- `.qif` - Quicken Interchange Format
- `.qpb` - Quicken Backup File
- `.qsd` - Quicken Supplemental Data
- `.qph` - Quicken Home & Business
- `.qxf` - Quicken Transfer Format
- `.qmtf` - Quicken Money Transfer Format
- `.qnx` - Quicken Network Exchange
- Plus year-specific: `.q2023`, `.q2024`, etc.

### Tax Software Files (10+ extensions)
- **TurboTax:** `.tax`, `.txf`, `.tax2023`, `.tax2024`, etc.
- **TaxAct:** `.t23`, `.t24`, `.t25`, `.t26`
- **H&R Block:** `.h23`, `.h24`, `.h25`, `.h26`

### Keyword Detection
Files are also classified as financial if they contain:
- Tax keywords: `tax`, `1040`, `w2`, `w-2`, `1099`
- Financial keywords: `quicken`, `finance`, `invoice`, `banking`, `investment`, `401k`, `ira`

**Files Modified:**
- `core/classifier.py` v0.8.0 - Added financial category

**Files Created:**
- `FINANCIAL_CATEGORY_GUIDE.md` - Complete documentation

**Total Categories:** Now 20 (was 19)

**Example:**
```bash
# These files are now classified as "financial":
2023_Taxes.tax2023         → financial
Quicken_Data.qdf           → financial
W2_2024.pdf                → financial (contains "w2")
Investment_Summary.xlsx    → financial (contains "investment")
```

---

## ✅ 8. Reclassify Script Improvements

**What Changed:**
Enhanced `reclassify_files.py` with cloud storage handling and better error handling.

**New Features:**
- **`--skip-cloud` flag:** Skip files in cloud storage (Google Drive, Dropbox, OneDrive, iCloud, Box)
- **Timeout handling:** Gracefully handles file access timeouts
- **Error statistics:** Tracks skipped and error files separately

**Supported Cloud Paths:**
- Google Drive
- Dropbox
- OneDrive
- iCloud Drive
- Box Sync
- Library/CloudStorage

**Usage:**
```bash
# Skip cloud files to avoid timeouts
python scripts/reclassify_files.py --categories other --skip-cloud

# Verbose output with cloud files skipped
python scripts/reclassify_files.py --categories other --skip-cloud --verbose
```

**Files Modified:**
- `scripts/reclassify_files.py` v0.7.1 - Added cloud storage handling

---

## ✅ 9. Web Category - NEW!

**What Changed:**
Created "web" category with complete directory structure preservation (similar to .app packages).

**Detected Web Directories:**
Files are classified as `web` if their path contains any of:
- `/http/`, `/https/`
- `/www/`, `/website/`, `/websites/`
- `/web/`, `/html/`, `/public_html/`
- `/htdocs/`, `/web-projects/`, `/sites/`

**Structure Preservation:**
Unlike other categories, web files maintain their **complete directory structure**.

**Example:**
```
Source:      /Users/canadytw/Desktop/http/mysite/css/style.css
Destination: /organized/Desktop/web/http/mysite/css/style.css

Source:      /Users/canadytw/Desktop/www/portfolio/index.html
Destination: /organized/Desktop/web/www/portfolio/index.html
```

**Why This Matters:**
- ✅ Websites need their folder structure to work correctly
- ✅ CSS, JS, image paths remain intact
- ✅ Similar to how .app packages preserve internal structure
- ✅ No files scattered by type

**Files Modified:**
- `core/classifier.py` v0.9.0 - Added web directory detection
- `core/organizer.py` v0.2.0 - Added `_plan_web_project()` function

**Files Created:**
- `WEB_CATEGORY_GUIDE.md` - Complete documentation

**Total Categories:** Now 21 (was 20)

**Comparison:**

| Regular File | Web File |
|--------------|----------|
| `/Desktop/project/image.png` | `/Desktop/http/site/image.png` |
| → `/organized/Desktop/2024/image/canadytw/image.png` | → `/organized/Desktop/web/http/site/image.png` |
| Files scattered by type | Structure preserved |

---

## ✅ 10. Application Category & .mpkg Support - NEW!

**What Changed:**
Created "application" category for installed applications with directory structure preservation (similar to web projects). Added .mpkg installer support.

**Detected Application Directories:**
Files are classified as `application` if their path contains:
- `/PacketTracer/` or `/Packet Tracer/`

**Structure Preservation:**
Unlike normal files, application directories maintain their **complete directory structure** including `.so.*` library files.

**Example:**
```
Source:      /Users/canadytw/Desktop/PacketTracer/lib/libssl.so.1
Destination: /organized/Desktop/application/PacketTracer/lib/libssl.so.1

Source:      /Users/canadytw/Desktop/PacketTracer/bin/packettracer
Destination: /organized/Desktop/application/PacketTracer/bin/packettracer
```

**Why This Matters:**
- ✅ Application installations need their folder structure to work correctly
- ✅ Shared libraries (.so, .so.1, .so.2) remain in correct paths
- ✅ Similar to how .app packages and web projects preserve structure
- ✅ No files scattered by type

**Atomic Package Support:**
Added `.mpkg` (macOS meta-package installer) to atomic package detection:
- `.app` - Application bundles
- `.pkg` - Installer packages
- `.mpkg` - Meta-package installers (NEW!)
- `.dmg` - Disk images

**Files Modified:**
- `core/scanner.py` v0.6.2 - Added .mpkg to atomic packages
- `core/classifier.py` v1.0.0 - Added application category and .mpkg extension
- `core/organizer.py` v0.3.0 - Added `_plan_application_project()` function

**Total Categories:** Now 22 (was 21)

**Comparison:**

| Regular File | Application File |
|--------------|------------------|
| `/Desktop/lib/libssl.so` | `/Desktop/PacketTracer/lib/libssl.so.1` |
| → `/organized/Desktop/2024/installer/canadytw/libssl.so` | → `/organized/Desktop/application/PacketTracer/lib/libssl.so.1` |
| Files scattered by type | Structure preserved |

---

## 🚀 Quick Start Guide

### 1. Basic Scan (with all new features)
```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan with automatic metadata extraction
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db
```

**What happens:**
- ✅ Hidden files skipped automatically
- ✅ Certificates detected (`.cer`, `.pem`, etc.)
- ✅ Education files detected (`CS101`, `MAT251`, etc.)
- ✅ Financial files detected (Quicken, TurboTax, tax files)
- ✅ Web projects preserve structure (`/http/`, `/www/`)
- ✅ Application directories preserve structure (PacketTracer)
- ✅ Path metadata extracted ("Land-Pics", "8May16", etc.)
- ✅ Root structure preserved ("Documents - 2996KD")
- ✅ Atomic packages handled (`.app`, `.pkg`, `.mpkg`, `.dmg` as single units)

### 2. With Metadata Files
```bash
# Also create .meta.json sidecar files
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### 3. Check "Other" Files in Database
```bash
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT SUBSTRING_INDEX(f.path, '.', -1) AS extension, COUNT(*)
      FROM files f LEFT JOIN classifications c ON f.id = c.file_id
      WHERE c.category = 'other' GROUP BY extension ORDER BY COUNT(*) DESC"
```

---

## 📊 Summary of All Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Hidden Files** | ✅ Auto | Skips all `.files` and `.directories` |
| **Certificates** | ✅ Existing | `.cer`, `.csr`, `.pem`, `.pfx`, `.wzd` + 8 more |
| **Education** | ✅ New | Detects CS, CEG, STAT, MAT prefixed files |
| **Financial** | ✅ New | 20+ extensions (Quicken, TurboTax, etc.) + keywords |
| **Web Projects** | ✅ New | Preserves structure for http, www, website directories |
| **Application** | ✅ New | Preserves structure for PacketTracer and similar apps |
| **Path Metadata** | ✅ New | Extracts tags from directory structure |
| **Root Preservation** | ✅ New | Keeps "Desktop - 2996KD" structure |
| **SQL Queries** | ✅ New | 11 queries to find "other" files |
| **Reclassify --skip-cloud** | ✅ New | Skip cloud storage to avoid timeouts |
| **Atomic Packages** | ✅ Enhanced | `.app`, `.pkg`, `.mpkg`, `.dmg` as single units |
| **Duplicate Detection** | ✅ Existing | Hash-based deduplication |

---

## 📁 New Files Created

1. `utils/path_metadata.py` - Path metadata extraction logic
2. `queries/find_other_files.sql` - SQL queries for "other" files
3. `QUERY_GUIDE.md` - SQL query usage guide
4. `PATH_METADATA_GUIDE.md` - Complete path metadata documentation
5. `YOUR_EXAMPLE.md` - Your specific example walkthrough
6. `FINANCIAL_CATEGORY_GUIDE.md` - Financial category documentation
7. `WEB_CATEGORY_GUIDE.md` - Web category documentation
8. `APPLICATION_CATEGORY_GUIDE.md` - Application category documentation
9. `CHANGES_SUMMARY.md` - This file

---

## 🔄 Files Modified

1. `core/scanner.py` v0.6.2 - Added hidden file detection and .mpkg support
2. `core/classifier.py` v1.0.0 - Added education, financial, web, and application categories (v0.7.0 → v1.0.0)
   - v0.7.0: Education category
   - v0.7.1: .wzd extension
   - v0.7.2: .qel extension
   - v0.8.0: Financial category
   - v0.9.0: Web category
   - v1.0.0: Application category and .mpkg support (22 categories total)
3. `models/file_info.py` - Added `path_metadata` field
4. `core/hasher.py` v0.6.0 - Extracts path metadata
5. `core/organizer.py` v0.3.0 - Preserves root structure, web projects, and application structures
6. `core/executor.py` - Writes path metadata to files
7. `scripts/reclassify_files.py` v0.7.1 - Added --skip-cloud flag and error handling
8. `main.py` - Fixed outdated execution instructions

---

## 🧪 Testing

### Test Hidden File Detection
```bash
# Create a hidden file
touch /tmp/.test_hidden.txt

# Scan - should be skipped
python main.py /tmp --base-dir /output --use-db --max-files 10
# Look for: "Skipped X hidden files"
```

### Test Education Detection
```bash
# Create test files
touch /tmp/CS101_test.pdf
touch /tmp/MAT251_homework.docx

# Scan
python main.py /tmp --base-dir /output --use-db

# Check database
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT f.path, c.category FROM files f
      LEFT JOIN classifications c ON f.id = c.file_id
      WHERE f.path LIKE '%CS101%' OR f.path LIKE '%MAT251%'"
```

### Test Path Metadata
```bash
# Run the test script
python3 utils/path_metadata.py
```

---

## 📖 Documentation

All documentation is available in these files:
- `PATH_METADATA_GUIDE.md` - Path metadata and root structure
- `YOUR_EXAMPLE.md` - Your specific example walkthrough
- `FINANCIAL_CATEGORY_GUIDE.md` - Financial category guide (Quicken, tax files)
- `WEB_CATEGORY_GUIDE.md` - Web category guide (structure preservation)
- `APPLICATION_CATEGORY_GUIDE.md` - Application category guide (PacketTracer, .mpkg)
- `QUERY_GUIDE.md` - SQL queries for "other" files
- `ATOMIC_PACKAGES_GUIDE.md` - Atomic package handling
- `DUPLICATE_DETECTION_GUIDE.md` - Duplicate detection
- `README.md` - Updated with all new features

---

## ⚙️ Your Requested Structure

Your Apple backup structure is now **fully supported**:

```
canadytw/
├── Desktop/
│   ├── Desktop
│   ├── Desktop - 2996KD           ← Preserved exactly
│   ├── Desktop - 42739            ← Preserved exactly
│   ├── Desktop - Fratricide (2)   ← Preserved exactly
│   ├── Desktop - Teufelshunde     ← Preserved exactly
├── Documents/
    ├── Documents
    ├── Documents - 2996KD         ← Preserved exactly
```

When organized, these root names stay **exactly the same** in the output directory, and your custom structure is created within each one.

---

## 🎯 Next Steps

1. **Review the documentation:**
   - Read `PATH_METADATA_GUIDE.md` for full details
   - Check `QUERY_GUIDE.md` for SQL usage

2. **Test on a small directory first:**
   ```bash
   python main.py /small/test/dir --base-dir /test/output --use-db --dry-run-log
   ```

3. **Review the dry-run output:**
   ```bash
   cat dry_run_preview_*.txt
   ```

4. **Run on your full directory when satisfied:**
   ```bash
   python main.py /Users/canadytw/Documents \
     --base-dir /organized \
     --use-db \
     --write-metadata \
     --execute
   ```

---

**Version:** 1.0.0
**Date:** 2025-11-14
**Author:** Tim Canady

**Major Changes in v1.0.0:**
- Added application category with directory structure preservation (PacketTracer)
- Added .mpkg support for macOS meta-package installers
- Enhanced web category with directory structure preservation
- Enhanced financial category with 20+ extensions
- Improved reclassify script with --skip-cloud option
- Updated to 22 total file categories
