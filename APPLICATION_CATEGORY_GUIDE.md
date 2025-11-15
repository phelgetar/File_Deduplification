# Application Category Guide

## Overview

The **application** category automatically detects and preserves the complete directory structure of installed applications like PacketTracer, treating them similar to how .app packages and web projects are handled. All files under an application root directory maintain their exact folder hierarchy.

---

## 📦 Detected Application Directories

Files are classified as **application** if their path contains any of these directories (case-insensitive):

| Directory Pattern | Description | Example |
|-------------------|-------------|---------|
| `/PacketTracer/` | Cisco PacketTracer installations | `/Desktop/PacketTracer/` |
| `/Packet Tracer/` | Cisco PacketTracer (space variant) | `/Desktop/Packet Tracer/` |

---

## 📁 Directory Structure Preservation

### How It Works

Unlike other file categories that scatter files by type, the application category preserves the **complete directory structure** from the application root onwards, including all libraries, binaries, and configuration files.

### Example 1: PacketTracer Installation

**Source:**
```
/Users/canadytw/Desktop/PacketTracer/
├── bin/
│   ├── packettracer
│   └── helper
├── lib/
│   ├── libssl.so.1
│   ├── libcrypto.so.1
│   └── libQt5Core.so.5
├── extensions/
│   └── plugins/
└── help/
    └── default/
```

**Organized Output:**
```
/organized/
  Desktop/
    application/
      PacketTracer/
        ├── bin/
        │   ├── packettracer
        │   └── helper
        ├── lib/
        │   ├── libssl.so.1
        │   ├── libcrypto.so.1
        │   └── libQt5Core.so.5
        ├── extensions/
        │   └── plugins/
        └── help/
            └── default/
```

### Example 2: With Root Structure Preservation

**Source:**
```
/Users/canadytw/Documents/Documents - 2996KD/PacketTracer/
├── bin/packettracer
└── lib/libssl.so.1
```

**Organized Output:**
```
/organized/
  Documents - 2996KD/
    application/
      PacketTracer/
        ├── bin/packettracer
        └── lib/libssl.so.1
```

**Notice:**
- ✅ Root structure `Documents - 2996KD` is preserved
- ✅ Category is `application`
- ✅ Complete directory structure maintained
- ✅ No files scattered by type (binaries, libraries stay together)

---

## 🎯 Comparison to Other Categories

### Normal File Organization

**For non-application files:**
```
Source:      /Desktop/PacketTracer.app              → Atomic package (single unit)
Destination: /organized/Desktop/2024/installer/canadytw/PacketTracer.app

Source:      /Desktop/tools/lib/libssl.so           → Scattered by type
Destination: /organized/Desktop/2024/installer/canadytw/libssl.so
```

### Application File Organization

**For application files:**
```
Source:      /Desktop/PacketTracer/lib/libssl.so.1
Destination: /organized/Desktop/application/PacketTracer/lib/libssl.so.1

Source:      /Desktop/PacketTracer/bin/packettracer
Destination: /organized/Desktop/application/PacketTracer/bin/packettracer
```

Files preserve: **root_structure / application / complete_original_path**

---

## 🔧 File Type Support

### Shared Libraries

Application category preserves all shared library files in their correct paths:

| Extension Pattern | Description | Example |
|-------------------|-------------|---------|
| `.so` | Shared object (Linux) | `libssl.so` |
| `.so.1`, `.so.2` | Versioned shared libraries | `libssl.so.1.0.0` |
| `.dylib` | Dynamic library (macOS) | `libSystem.dylib` |
| `.dll` | Dynamic link library (Windows) | `msvcr120.dll` |

**Note:** These files would normally be classified as "installer" and scattered, but within an application directory they remain in place.

---

## 🔍 Detection Examples

### ✅ Detected as Application

```bash
# Any file under PacketTracer patterns:
/Users/canadytw/Desktop/PacketTracer/bin/app              → application
/Users/canadytw/Desktop/PacketTracer/lib/libssl.so.1      → application
/Users/canadytw/Desktop/Packet Tracer/extensions/plugin   → application
/Users/canadytw/Documents/PacketTracer/help/doc.html      → application
```

### ❌ Not Detected as Application

```bash
# Regular files outside application directories:
/Users/canadytw/Desktop/lib/libssl.so                     → installer
/Users/canadytw/Downloads/packettracer.tar.gz             → archive
/Users/canadytw/Documents/notes.txt                       → document
```

---

## 🚀 Usage Examples

### Example 1: Organize PacketTracer Installation

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan Desktop with PacketTracer
python main.py /Users/canadytw/Desktop \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --dry-run-log
```

**Output:**
```
🔍 Scanning files...
  [1/150] Processing: PacketTracer/bin/packettracer
  🏷️  Path tags: PacketTracer, bin
  [2/150] Processing: PacketTracer/lib/libssl.so.1
  🏷️  Path tags: PacketTracer, lib
  ...

🤖 Classifying files with AI...
  ✓ PacketTracer/bin/packettracer → application
  ✓ PacketTracer/lib/libssl.so.1 → application
  ...

📋 Organization plan:
  Source:      /Desktop/PacketTracer/bin/packettracer
  Destination: /organized/Desktop/application/PacketTracer/bin/packettracer

  Source:      /Desktop/PacketTracer/lib/libssl.so.1
  Destination: /organized/Desktop/application/PacketTracer/lib/libssl.so.1
```

### Example 2: Execute Organization

```bash
# After reviewing dry-run, execute:
python main.py /Users/canadytw/Desktop \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### Example 3: Query Application Files in Database

```bash
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT f.path, ROUND(f.size/1048576, 2) AS size_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'application'
ORDER BY f.path;
"
```

**Example Output:**
```
+---------------------------------------------------------------+----------+
| path                                                          | size_mb  |
+---------------------------------------------------------------+----------+
| /Users/canadytw/Desktop/PacketTracer/bin/packettracer        | 125.50   |
| /Users/canadytw/Desktop/PacketTracer/lib/libssl.so.1         | 2.30     |
| /Users/canadytw/Desktop/PacketTracer/lib/libcrypto.so.1      | 3.80     |
+---------------------------------------------------------------+----------+
```

---

## 📊 Atomic Packages vs Application Directories

### Atomic Packages (.app, .pkg, .mpkg, .dmg)

These are **single-unit files** treated as indivisible:

```bash
# Examples of atomic packages:
/Desktop/PacketTracer.app        → Scanned as ONE file (no internal scanning)
/Desktop/Installer.pkg           → Scanned as ONE file
/Desktop/Updater.mpkg            → Scanned as ONE file (NEW!)
/Desktop/Software.dmg            → Scanned as ONE file
```

**Atomic Package Behavior:**
- ✅ Treated as single file
- ✅ No internal files scanned
- ✅ Moved/copied as complete unit
- ✅ Category: `installer`

### Application Directories (PacketTracer, etc.)

These are **directory structures** with preserved hierarchy:

```bash
# Examples of application directories:
/Desktop/PacketTracer/           → Scanned recursively WITH structure preservation
/Desktop/Packet Tracer/          → Scanned recursively WITH structure preservation
```

**Application Directory Behavior:**
- ✅ Each file scanned individually
- ✅ Directory structure preserved
- ✅ Files moved maintaining paths
- ✅ Category: `application`

---

## 🆕 .mpkg Support

Added support for `.mpkg` (macOS meta-package installers) as atomic packages.

**What is .mpkg?**
- Meta-package format that contains multiple `.pkg` installers
- Common for complex macOS software installations
- Treated as single unit (not scanned internally)

**Example:**
```bash
# .mpkg file is treated like .app and .pkg:
/Desktop/Adobe_Creative_Suite.mpkg  → installer (atomic package)
```

---

## 🔧 Technical Details

### Implementation

The application category is implemented in:

1. **`core/scanner.py`** (v0.6.2):
   ```python
   # Added .mpkg to atomic packages
   atomic_extensions = {'.app', '.pkg', '.mpkg', '.dmg'}
   ```

2. **`core/classifier.py`** (v1.0.0):
   ```python
   # Application directories (preserve structure)
   elif any(app_dir in file_path_str.lower() for app_dir in [
       "/packettracer/", "/packet tracer/"
   ]):
       category = "application"
   ```

3. **`core/organizer.py`** (v0.3.0):
   ```python
   # Special handling for application directories
   if file_info.type == "application":
       destination = _plan_application_project(file_info, base_dir, preserve_root_structure)
   ```

### Structure Preservation Logic

```python
def _plan_application_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for application files, preserving directory structure.

    1. Extract root structure folder if preserving (e.g., "Desktop - 2996KD")
    2. Find the application root directory (PacketTracer, etc.)
    3. Extract the path from app root onwards
    4. Build destination: base_dir/root_folder/application/relative_path
    """
```

---

## 🎓 Similar Features

Application directories use the same structure preservation approach as:

| Feature | Category | Preservation |
|---------|----------|--------------|
| **.app packages** | installer | ✅ Complete (atomic) |
| **.pkg packages** | installer | ✅ Complete (atomic) |
| **.mpkg packages** | installer | ✅ Complete (atomic) |
| **Web directories** | web | ✅ Complete (recursive) |
| **Application directories** | application | ✅ Complete (recursive) |

---

## ✅ Best Practices

### 1. Organize Applications Separately

```bash
# Scan only application directories
python main.py /Users/canadytw/Desktop/PacketTracer \
  --base-dir /organized_apps \
  --use-db \
  --execute
```

### 2. Use Metadata for Search

```bash
# Find all PacketTracer library files
find /organized -name "*.meta.json" | \
  xargs grep -l "PacketTracer" | \
  grep -l "\.so\." | \
  sed 's/.meta.json$//'
```

### 3. Backup Before Organizing

```bash
# Create backup
tar -czf packettracer_backup_$(date +%Y%m%d).tar.gz ~/Desktop/PacketTracer

# Then organize
python main.py ~/Desktop --base-dir /organized --use-db --execute
```

---

## 🔍 Query Examples

### Count Application Files by Extension

```sql
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'application'
GROUP BY extension
ORDER BY count DESC
LIMIT 10;
```

**Example Output:**
```
+-----------+-------+----------+
| extension | count | total_mb |
+-----------+-------+----------+
| so        |    45 |   120.50 |
| 1         |    23 |    56.30 |
| xml       |    18 |     2.10 |
| png       |    12 |     5.20 |
+-----------+-------+----------+
```

### Find All Library Files

```sql
SELECT f.path, ROUND(f.size/1048576, 2) AS size_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'application'
  AND (f.path LIKE '%.so%' OR f.path LIKE '%.dylib%')
ORDER BY f.size DESC;
```

---

## 🆘 Troubleshooting

### Issue: Files Scattered Despite Being in PacketTracer Directory

**Cause:** Spelling or path mismatch

**Check:**
```bash
# Verify directory name exactly matches:
ls -la /path/to/directory
```

**Solution:** Ensure directory is named exactly `PacketTracer` or `Packet Tracer` (case-insensitive).

### Issue: .so Files Not Staying Together

**Cause:** Files are outside PacketTracer directory

**Example:**
```bash
# NOT detected (no PacketTracer in path):
/Desktop/lib/libssl.so  → installer (scattered)

# DETECTED (PacketTracer in path):
/Desktop/PacketTracer/lib/libssl.so  → application (preserved)
```

**Solution:** Move libraries into PacketTracer directory structure.

### Issue: .mpkg File Being Scanned Internally

**Cause:** Using old version before .mpkg support

**Solution:** Update to v1.0.0+ and rescan.

---

## 📈 Statistics

### Total Categories: 22

The system now supports **22 file categories**:

1. image
2. video
3. audio
4. document
5. spreadsheet
6. presentation
7. code
8. archive
9. data
10. font
11. installer
12. certificate
13. shortcut
14. scientific
15. education
16. financial
17. web
18. **application** ← NEW!
19. backup
20. temporary
21. system
22. other

---

## 💡 Tips

### Tip 1: Add Custom Applications

To add support for other applications, edit `core/classifier.py`:

```python
# Application directories (preserve structure)
elif any(app_dir in file_path_str.lower() for app_dir in [
    "/packettracer/", "/packet tracer/",
    "/your_app_name/",  # Add here
]):
    category = "application"
```

And update `core/organizer.py`:

```python
app_roots = ['/packettracer/', '/packet tracer/', '/your_app_name/']
```

### Tip 2: Verify Structure Before Moving

```bash
# Dry-run to see structure
python main.py /source --base-dir /output --dry-run-log

# Check the log
cat dry_run_preview_*.txt | grep "PacketTracer"
```

### Tip 3: Test on Copy First

```bash
# Copy instead of move first
cp -r /Desktop/PacketTracer /test/PacketTracer

# Organize the copy
python main.py /test --base-dir /organized --use-db --execute

# Verify it works, then organize original
```

---

## ✅ Summary

### Detection
- ✅ Automatically detects PacketTracer directories (case-insensitive)
- ✅ Works with any file type under application directories
- ✅ Preserves complete structure including libraries

### Organization
- ✅ Preserves complete directory structure
- ✅ Maintains root structure (Desktop - 2996KD, etc.)
- ✅ Groups under `/application/` category folder
- ✅ No file scattering by type

### Atomic Packages
- ✅ .app, .pkg, .mpkg, .dmg as single units
- ✅ No internal scanning
- ✅ Moved as complete files

### Similar To
- ✅ Web project handling (structure preservation)
- ✅ .app package handling (complete units)

---

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Modules:** `core/scanner.py`, `core/classifier.py`, `core/organizer.py`
