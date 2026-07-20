# Custom Folder Structure Guide

## Overview

The File Deduplication system now supports **custom folder mapping** that allows you to organize files into your own preferred directory structure instead of the default category names.

Your files will be organized into this clean hierarchy:

```
organized/
├── Docs/
│   ├── PowerPoints/          ← Presentations (.pptx, .ppt, .odp, .key)
│   ├── Word/                 ← Documents (.pdf, .docx, .txt, .rtf)
│   └── Spreadsheets/         ← Spreadsheets (.xlsx, .xls, .csv, .numbers)
├── Media/
│   ├── Images/               ← Photos (.jpg, .png, .gif, .heic)
│   ├── Music/                ← Audio files (.mp3, .flac, .m4a)
│   └── Videos/               ← Video files (.mp4, .mov, .avi)
│       ├── SecurityCameraVideos/  ← SVR_Video_Recorder*.mp4
│       ├── WolfVids/              ← clip*.mov files
│       ├── Movies/                ← (future use)
│       └── TV/                    ← (future use)
├── Code/                     ← Code files with preserved structure
│   ├── eclipse/
│   ├── python/
│   ├── XCode/
│   └── Scripts/
├── Backups/                  ← Backup directories (structure preserved)
├── Web/                      ← Web projects (structure preserved)
├── Applications/             ← Application directories (structure preserved)
├── Archives/                 ← Compressed files (.zip, .tar.gz, .7z)
├── Installers/               ← Installation packages (.exe, .dmg, .pkg)
├── Certs/                    ← Certificates (.pem, .crt, .p12)
├── Education/                ← Educational course files
├── Financial/                ← Financial documents (Quicken, tax files)
└── Other/                    ← Unclassified files
```

---

## 🎯 New Features

### 1. Custom Folder Mapping

Files are now organized into **user-friendly folder names** instead of technical category names:

| Old Category Name | New Folder Name | Examples |
|-------------------|-----------------|----------|
| `document` | `Docs/Word` | .pdf, .docx, .txt |
| `presentation` | `Docs/PowerPoints` | .pptx, .ppt, .key |
| `spreadsheet` | `Docs/Spreadsheets` | .xlsx, .csv, .numbers |
| `image` | `Media/Images` | .jpg, .png, .heic |
| `audio` | `Media/Music` | .mp3, .flac, .m4a |
| `video` | `Media/Videos` | .mp4, .mov, .avi |
| `code` | `Code` | Programming files |
| `backup` | `Backups` | Backup directories |
| `archive` | `Archives` | .zip, .7z, .tar.gz |
| `installer` | `Installers` | .exe, .dmg, .pkg |

### 2. Special Video Subcategories

Videos are automatically organized into subcategories based on filename patterns:

```
Media/Videos/
├── SecurityCameraVideos/     ← Files matching: svr_video_recorder*, security_cam*, camera_recording*
├── WolfVids/                 ← Files matching: clip*, wolf*, wolfvid*
└── (regular videos)          ← All other video files
```

**Detection Examples:**
- ✅ `SVR_Video_Recorder_001.mp4` → `Media/Videos/SecurityCameraVideos/`
- ✅ `clip_2024_11_14.mov` → `Media/Videos/WolfVids/`
- ✅ `vacation_2024.mp4` → `Media/Videos/`

### 3. Code Structure Preservation

Code files maintain their complete directory structure under the `Code/` folder:

```
Code/
├── eclipse/
│   └── workspace/
│       └── MyProject/
├── python/
│   ├── data_processing/
│   │   ├── __init__.py
│   │   └── parser.py
│   └── automation/
├── XCode/
│   └── MyApp.xcodeproj/
└── Scripts/
    └── swift-master/
```

**Example:**
```
Source:      /Documents/scripts/swift-master/validation-test/compiler_crashers_fixed/00060-adjust-function-type.swift
Destination: /organized/Documents/Code/scripts/swift-master/validation-test/compiler_crashers_fixed/00060-adjust-function-type.swift
```

---

## 📊 Complete Category Mapping

### Documents
| Category | Folder | File Types |
|----------|--------|------------|
| document | `Docs/Word` | .pdf, .docx, .doc, .txt, .rtf, .odt, .md, .tex, .pages |
| presentation | `Docs/PowerPoints` | .pptx, .ppt, .odp, .key |
| spreadsheet | `Docs/Spreadsheets` | .xlsx, .xls, .csv, .ods, .numbers, .tsv |

### Media
| Category | Folder | File Types |
|----------|--------|------------|
| image | `Media/Images` | .jpg, .jpeg, .png, .gif, .bmp, .heic, .raw, .psd |
| audio | `Media/Music` | .mp3, .flac, .wav, .m4a, .aac, .ogg, .wma |
| video | `Media/Videos` | .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm |
| security_camera_video | `Media/Videos/SecurityCameraVideos` | Videos matching: svr_video_recorder*, security_cam* |
| wolf_video | `Media/Videos/WolfVids` | Videos matching: clip*, wolf*, wolfvid* |

### Code & Projects
| Category | Folder | Structure Preserved? |
|----------|--------|----------------------|
| code | `Code` | ✅ Yes - Full structure |
| web | `Web` | ✅ Yes - Full structure |
| backup | `Backups` | ✅ Yes - Full structure |
| application | `Applications` | ✅ Yes - Full structure |

### Other Categories
| Category | Folder | File Types |
|----------|--------|------------|
| archive | `Archives` | .zip, .tar, .gz, .7z, .rar, .iso, .dmg |
| installer | `Installers` | .exe, .msi, .pkg, .deb, .rpm, .apk, .ipa |
| certificate | `Certs` | .pem, .crt, .p12, .pfx, .key, .csr |
| data | `Data` | .json, .xml, .yaml, .sql, .db, .sqlite |
| font | `Fonts` | .ttf, .otf, .woff, .woff2 |
| scientific | `Scientific` | .mat, .hdf5, .nc, .fits, .npy |
| education | `Education` | Course files (CS*, CEG*, STAT*, MAT*) |
| financial | `Financial` | .qdf, .tax, Quicken files |
| temporary | `Temp` | .tmp, .cache, .crdownload |
| system | `System` | Config files, .plist, system files |
| shortcut | `Shortcuts` | .lnk, .url, .webloc, .desktop |
| other | `Other` | Unclassified files |
| unknown | `Unclassified` | Unknown file types |

---

## 🚀 Usage

### Test the Configuration

Before running the full organization, test the folder mapping:

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification
python3 test_folder_mapping.py
```

**Expected Output:**
```
======================================================================
FOLDER MAPPING TEST
======================================================================

📁 Category → Custom Folder Mappings:
----------------------------------------------------------------------
  document                  → Docs/Word
  presentation              → Docs/PowerPoints
  spreadsheet               → Docs/Spreadsheets
  image                     → Media/Images
  audio                     → Media/Music
  video                     → Media/Videos
  security_camera_video     → Media/Videos/SecurityCameraVideos  [PRESERVES STRUCTURE]
  wolf_video                → Media/Videos/WolfVids              [PRESERVES STRUCTURE]
  code                      → Code                               [PRESERVES STRUCTURE]
  ...

✅ Folder mapping test complete!
```

### Run Organization with Custom Folders

```bash
# Dry run first to preview the structure
python3 main.py "/Users/canadytw/Documents" \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --dry-run-log

# Review the output
cat dry_run_preview_*.txt

# Execute when ready
python3 main.py "/Users/canadytw/Documents" \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### Example Output Structure

After running organization on your Documents folder:

```
/organized/
└── Documents/
    ├── Docs/
    │   ├── PowerPoints/
    │   │   ├── Project_Presentation.pptx
    │   │   └── Team_Meeting_2024.pptx
    │   ├── Word/
    │   │   ├── Resume.pdf
    │   │   ├── Report_2024.docx
    │   │   └── Notes.txt
    │   └── Spreadsheets/
    │       ├── Budget_2024.xlsx
    │       └── Data_Analysis.csv
    ├── Media/
    │   ├── Images/
    │   │   ├── vacation_photo.jpg
    │   │   └── family_pic.heic
    │   ├── Music/
    │   │   ├── favorite_song.mp3
    │   │   └── album.flac
    │   └── Videos/
    │       ├── SecurityCameraVideos/
    │       │   ├── SVR_Video_Recorder_001.mp4
    │       │   └── SVR_Video_Recorder_002.mp4
    │       ├── WolfVids/
    │       │   ├── clip001.mov
    │       │   └── clip002.mov
    │       └── vacation_2024.mp4
    ├── Code/
    │   ├── python/
    │   │   ├── data_processing/
    │   │   │   ├── __init__.py
    │   │   │   └── parser.py
    │   │   └── automation/
    │   │       └── script.py
    │   ├── eclipse/
    │   │   └── workspace/
    │   └── XCode/
    │       └── MyApp.xcodeproj/
    ├── Backups/
    │   └── backup/
    │       └── 2024-11-14/
    ├── Archives/
    │   ├── project_backup.zip
    │   └── old_files.tar.gz
    └── Installers/
        ├── Chrome.dmg
        └── Office.pkg
```

---

## 🔧 Customization

### Modify Folder Mappings

Edit `/Users/canadytw/PycharmProjects/File_Deduplification/config/folder_mapping.py`:

```python
CATEGORY_FOLDER_MAP: Dict[str, str] = {
    # Change folder names here
    'document': 'Docs/Word',           # Change to 'Documents' if you prefer
    'presentation': 'Docs/PowerPoints', # Change to 'Presentations' if you prefer
    'image': 'Media/Images',           # Change to 'Photos' if you prefer
    # ... etc
}
```

### Add New Video Patterns

Add custom video filename patterns:

```python
VIDEO_PATTERNS = {
    'security_camera_video': [
        'svr_video_recorder',
        'security_cam',
        'camera_recording',
        'your_pattern_here'  # Add here
    ],
    'wolf_video': [
        'clip',
        'wolf',
        'wolfvid',
        'your_pattern_here'  # Add here
    ]
}
```

### Add New Categories

Add a new category to the mapping:

```python
CATEGORY_FOLDER_MAP: Dict[str, str] = {
    # ... existing mappings
    'my_new_category': 'MyCustomFolder',
}
```

Then update `core/classifier.py` to detect and assign the new category.

---

## 📈 Technical Details

### Version Information

**Modules Updated:**
- `core/classifier.py` v1.7.0 - Added video subcategory detection
- `core/organizer.py` v0.8.0 - Added custom folder mapping support
- `config/folder_mapping.py` v1.0.0 - New configuration module

**New Features:**
- ✅ Custom folder mapping for all categories
- ✅ Special video subcategories (SecurityCameraVideos, WolfVids)
- ✅ Filename pattern-based video detection
- ✅ Code structure preservation under `Code/` folder
- ✅ Configurable folder names

### Structure-Preserving Categories

These categories maintain their complete directory structure:

1. **code** - Programming files, scripts, source code
2. **backup** - Backup directories with dates and nested structure
3. **web** - Web projects with complete HTML/CSS/JS structure
4. **application** - Installed applications (PacketTracer, Adobe, etc.)
5. **security_camera_video** - Security camera videos with structure
6. **wolf_video** - Wolf videos with structure

All other categories place files directly in their designated folders without preserving subdirectories.

---

## ✅ Summary

### What Changed

**Before (Default):**
```
/organized/
├── document/              ← Generic category name
├── presentation/          ← Generic category name
├── image/                 ← Generic category name
├── video/                 ← All videos mixed together
└── code/                  ← All code files
```

**After (Custom Structure):**
```
/organized/
├── Docs/
│   ├── PowerPoints/       ← User-friendly name
│   ├── Word/              ← User-friendly name
│   └── Spreadsheets/      ← User-friendly name
├── Media/
│   ├── Images/            ← User-friendly name
│   ├── Music/             ← User-friendly name
│   └── Videos/            ← User-friendly name
│       ├── SecurityCameraVideos/  ← Separated by pattern
│       └── WolfVids/              ← Separated by pattern
└── Code/                  ← Preserves structure
    ├── python/
    ├── XCode/
    └── Scripts/
```

### Benefits

✅ **User-Friendly Names** - "Docs/Word" instead of "document"
✅ **Logical Grouping** - Documents under Docs/, Media under Media/
✅ **Video Organization** - Security camera and wolf videos separated
✅ **Structure Preservation** - Code, backups, web projects keep structure
✅ **Customizable** - Easy to modify folder names in config file
✅ **Backward Compatible** - Falls back to category names if mapping missing

---

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Modules:** `config/folder_mapping.py` v1.0.0, `core/classifier.py` v1.7.0, `core/organizer.py` v0.8.0
