# Code & Scripts Directory Preservation

## Overview

The File Deduplication system now preserves the complete directory structure for **all code and scripts directories**. This ensures that:
- Python imports work correctly
- Shell script relative paths remain valid
- Build tools can find dependencies
- Module imports function properly

---

## 🎯 Detected Directories

Any files under these directory patterns will **maintain their complete structure**:

### Source Code Directories
| Directory Pattern | Typical Use | Example |
|-------------------|-------------|---------|
| `/scripts/` | Script collections | `/Documents/scripts/` |
| `/script/` | Script folder | `/Documents/script/` |
| `/code/` | Code repositories | `/Documents/code/` |
| `/src/` | Source code (most common) | `/project/src/` |
| `/source/` | Source files | `/project/source/` |

### Library & Module Directories
| Directory Pattern | Typical Use | Example |
|-------------------|-------------|---------|
| `/lib/` | Library files | `/project/lib/` |
| `/libs/` | Libraries folder | `/project/libs/` |
| `/libraries/` | Libraries collection | `/project/libraries/` |
| `/modules/` | Module files | `/project/modules/` |
| `/packages/` | Package files | `/project/packages/` |

### Build & Distribution Directories
| Directory Pattern | Typical Use | Example |
|-------------------|-------------|---------|
| `/bin/` | Binary/executable files | `/project/bin/` |
| `/dist/` | Distribution builds | `/project/dist/` |
| `/build/` | Build artifacts | `/project/build/` |
| `/out/` | Output files | `/project/out/` |
| `/target/` | Target builds (Maven/Rust) | `/project/target/` |

### Xcode Project Directories
| Directory Pattern | Typical Use | Example |
|-------------------|-------------|---------||
| `/xcode/` | Xcode project directory | `/project/xcode/` |
| `.xcodeproj` | Xcode project bundle | `/project/MyApp.xcodeproj` |
| `.xcworkspace` | Xcode workspace | `/project/MyApp.xcworkspace` |

---

## 📊 Your Specific Example

### Source Structure

```
/Users/canadytw/Documents/Documents - 42739/Google Drive/Work Related/scripts/
├── python/
│   ├── data_processing/
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── utils.py
│   ├── automation/
│   │   ├── backup.sh
│   │   ├── deploy.py
│   │   └── config.yaml
│   └── requirements.txt
├── swift-master/
│   ├── lib/
│   │   └── Foundation.swift
│   ├── test/
│   │   └── TestRunner.swift
│   └── Makefile
└── shared/
    ├── constants.py
    └── logger.py
```

### Organized Structure

```
/organized/
  Documents - 42739/
    code/
      scripts/
        ├── python/
        │   ├── data_processing/
        │   │   ├── __init__.py
        │   │   ├── parser.py
        │   │   └── utils.py
        │   ├── automation/
        │   │   ├── backup.sh
        │   │   ├── deploy.py
        │   │   └── config.yaml
        │   └── requirements.txt
        ├── swift-master/
        │   ├── lib/
        │   │   └── Foundation.swift
        │   ├── test/
        │   │   └── TestRunner.swift
        │   └── Makefile
        └── shared/
            ├── constants.py
            └── logger.py
```

### ✅ What Still Works

**Python Imports:**
```python
# In python/data_processing/parser.py:
from shared import logger  # ✅ WORKS - relative path preserved
from shared.constants import API_KEY  # ✅ WORKS
```

**Shell Script Paths:**
```bash
# In python/automation/backup.sh:
python ../data_processing/parser.py  # ✅ WORKS
source ../../shared/constants.py     # ✅ WORKS
```

**Build Tools:**
```makefile
# In swift-master/Makefile:
SOURCES = lib/Foundation.swift       # ✅ WORKS
TEST_DIR = test/                      # ✅ WORKS
```

**Configuration Files:**
```yaml
# In python/automation/config.yaml:
shared_config: ../../shared/constants.py  # ✅ WORKS
```

---

## 🎯 Why This Matters

### Without Structure Preservation

**Problem:**
```
/organized/
  Documents - 42739/
    2024/
      code/
        canadytw/
          ├── __init__.py          ❌ Scattered!
          ├── parser.py            ❌ Wrong location!
          ├── utils.py             ❌ Imports break!
          ├── backup.sh            ❌ Paths invalid!
          ├── constants.py         ❌ Can't find each other!
          └── logger.py            ❌ Everything broken!
```

**Result:** All imports fail, paths break, nothing works!

### With Structure Preservation

**Solution:**
```
/organized/
  Documents - 42739/
    code/
      scripts/
        ├── python/
        │   ├── data_processing/
        │   │   ├── __init__.py  ✅ Correct location!
        │   │   ├── parser.py    ✅ Imports work!
        │   │   └── utils.py     ✅ Paths valid!
        │   └── automation/
        │       └── backup.sh    ✅ Scripts work!
        └── shared/
            ├── constants.py     ✅ Found correctly!
            └── logger.py        ✅ Everything works!
```

**Result:** All imports work, paths valid, scripts functional!

---

## 🚀 Usage

### Scan Your Scripts Directory

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Dry run first
python main.py "/Users/canadytw/Documents/Documents - 42739/Google Drive/Work Related" \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --dry-run-log

# Review the output
cat dry_run_preview_*.txt | grep "scripts"

# Execute when ready
python main.py "/Users/canadytw/Documents/Documents - 42739/Google Drive/Work Related" \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### Expected Output

```
🔍 Scanning files...
  [1/50] Processing: scripts/python/data_processing/__init__.py
  🏷️  Path tags: scripts, python, data_processing
  [2/50] Processing: scripts/python/data_processing/parser.py
  🏷️  Path tags: scripts, python, data_processing
  ...

🤖 Classifying files with AI...
  ✓ scripts/python/data_processing/__init__.py → code
  ✓ scripts/python/data_processing/parser.py → code
  ✓ scripts/swift-master/lib/Foundation.swift → code
  ...

📋 Organization plan:
  Source:      /Documents - 42739/Google Drive/Work Related/scripts/python/data_processing/parser.py
  Destination: /organized/Documents - 42739/application/scripts/python/data_processing/parser.py

✅ Structure preserved!
```

---

## 🔍 Detection Examples

### ✅ Detected as Code (Structure Preserved)

```bash
# Scripts directories
/Documents/scripts/automation/deploy.py              → code
/Desktop/code/myproject/src/main.py                  → code
/Documents/python_scripts/data_processing.py         → code

# Xcode projects
/Documents/xcode/MyApp.xcodeproj/project.pbxproj    → code
/Projects/iOS/MyApp.xcworkspace/contents.xcworkspacedata → code
/Desktop/xcode/MyGame/Assets.xcassets/icon.png       → code

# Source code
/Projects/myapp/src/components/Button.js            → code
/Documents/source/utils/helper.py                   → code

# Libraries
/Projects/myapp/lib/custom_library.py               → code
/Documents/libs/shared/common.js                    → code

# Build outputs
/Projects/myapp/dist/bundle.js                      → code
/Documents/build/output/app.exe                     → code
/Projects/maven-app/target/app.jar                  → code
```

### ❌ Not Detected (Regular Classification)

```bash
# Random Python files (no scripts/code directory)
/Documents/report_generator.py                       → code
/Desktop/quick_script.sh                            → code
/Downloads/backup.py                                → code
```

---

## 🔧 Technical Details

### Implementation

**Classifier Detection** (`core/classifier.py` v1.3.0):
```python
# Application and installer directories (preserve structure)
elif any(app_dir in file_path_str.lower() for app_dir in [
    # Code/Scripts directories (path-dependent)
    "/scripts/", "/script/", "/code/", "/src/", "/source/",
    "/lib/", "/libs/", "/libraries/", "/modules/", "/packages/",
    "/bin/", "/dist/", "/build/", "/out/", "/target/"
]):
    category = "application"
```

**Structure Preservation** (`core/organizer.py` v0.5.0):
```python
# Special handling for application directories
if file_info.type == "application":
    destination = _plan_application_project(file_info, base_dir, preserve_root_structure)
    # Preserves complete directory structure from detected directory onwards
```

---

## 💡 Common Use Cases

### Python Projects

**Structure:**
```
/Documents/code/my_project/
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── utils/
│       └── helpers.py
├── tests/
│   └── test_main.py
└── requirements.txt
```

**Organized:** Complete structure preserved under `/organized/Documents/application/code/my_project/`

### Node.js Projects

**Structure:**
```
/Documents/code/my_app/
├── src/
│   ├── index.js
│   └── components/
│       └── App.js
├── dist/
│   └── bundle.js
└── package.json
```

**Organized:** Complete structure preserved under `/organized/Documents/application/code/my_app/`

### Shell Scripts Collection

**Structure:**
```
/Documents/scripts/
├── backup/
│   ├── daily_backup.sh
│   └── weekly_backup.sh
├── deploy/
│   └── deploy_prod.sh
└── utils/
    └── common.sh
```

**Organized:** Complete structure preserved under `/organized/Documents/code/scripts/`

### Xcode Projects

**Structure:**
```
/Documents/xcode/MyApp.xcodeproj/
├── project.pbxproj
├── xcshareddata/
│   └── xcschemes/
│       └── MyApp.xcscheme
└── xcuserdata/
    └── user.xcuserdatad/
```

**Organized:** Complete structure preserved under `/organized/Documents/code/xcode/MyApp.xcodeproj/`

### Build Outputs

**Structure:**
```
/Projects/maven-app/
├── src/
│   └── main/
│       └── java/
├── target/
│   ├── classes/
│   └── my-app-1.0.jar
└── pom.xml
```

**Organized:** Complete structure preserved under `/organized/Projects/application/maven-app/`

---

## 🆘 Troubleshooting

### Issue: Scripts Still Being Scattered

**Cause:** Directory name doesn't match detection pattern

**Example:**
```bash
# NOT detected:
/Documents/my_scripts/  → Files scattered

# DETECTED:
/Documents/scripts/     → Structure preserved
```

**Solution:** Rename directory to match pattern:
```bash
mv "/Documents/my_scripts" "/Documents/scripts"
```

### Issue: Only Some Files Preserved

**Cause:** Directory is partially inside/outside detected pattern

**Example:**
```bash
# NOT detected (files OUTSIDE scripts directory):
/Documents/automation.py  → code (scattered)

# DETECTED (files INSIDE scripts directory):
/Documents/scripts/automation.py  → code (preserved)
```

**Solution:** Move all related files into scripts directory:
```bash
mv /Documents/automation.py /Documents/scripts/
```

---

## ✅ Summary

### What's Preserved

✅ **18 Directory Patterns:**
- Scripts: `/scripts/`, `/script/`
- Source: `/code/`, `/src/`, `/source/`
- Libraries: `/lib/`, `/libs/`, `/libraries/`, `/modules/`, `/packages/`
- Build: `/bin/`, `/dist/`, `/build/`, `/out/`, `/target/`
- Xcode: `/xcode/`, `.xcodeproj`, `.xcworkspace`

✅ **What Still Works:**
- Python imports (`from module import func`)
- Shell script paths (`../../shared/script.sh`)
- Build tools (Makefile, Maven, npm)
- Configuration file paths
- Relative imports and includes

✅ **Categories Affected:**
- Category: `code`
- Behavior: Complete structure preservation
- Similar to: web projects, installer directories

---

**Version:** 1.6.0
**Last Updated:** 2025-11-14
**Modules:** `core/classifier.py` v1.6.0, `core/organizer.py` v0.7.0

**What's New in v1.6.0:**
- ✅ Added backup directory preservation (`/backup/`, `/backups/`) with complete structure maintenance
- ✅ Added Xcode project support (`.xcodeproj`, `.xcworkspace`, `/xcode/`) under "code" category
- ✅ Total of 18 directory patterns now detected and preserved
- ✅ Backup files get their own "backup" category with full structure preservation

**What's New in v1.5.0:**
- ✅ Code/scripts directories now use **"code"** category folder instead of "application"
- ✅ Structure: `/organized/code/scripts/...` (not `/organized/application/scripts/...`)
- ✅ Application category reserved for installers and software only
