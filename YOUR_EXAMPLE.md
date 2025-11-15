# Your Specific Example - Step by Step

## Your Original Path

```
/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
```

---

## What Happens When You Scan

### Step 1: Scanner
```bash
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db \
  --write-metadata
```

**Scanner finds:**
- File: `IMG_0001.JPG`
- Size: 2,048,576 bytes
- Location: `Documents - 2996KD/Pictures/Land-Pics/8May16/`

**Scanner skips:**
- `.DS_Store` (hidden file)
- `.Spotlight-V100/` (hidden directory)
- Any other `.files`

---

### Step 2: Hasher

**Generates hash:**
```
SHA256: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
```

**Extracts path metadata:**
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

**Console output:**
```
  [1/150] Processing: IMG_0001.JPG
    Large file detected: 2MB
    🏷️  Path tags: Pictures, Land-Pics, 8May16
    ✅ Saved to DB
```

---

### Step 3: Classifier

**Detects:**
- File extension: `.JPG`
- MIME type: `image/jpeg`

**Classification:**
```
Category: image
```

---

### Step 4: Organizer

**Plans destination:**
```
Source:      /Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
Destination: /organized/Documents - 2996KD/2024/image/canadytw/IMG_0001.JPG
```

**Structure breakdown:**
```
/organized/                    ← Your base directory
  Documents - 2996KD/          ← Root structure (PRESERVED)
    2024/                      ← Year
      image/                   ← File type
        canadytw/              ← Owner
          IMG_0001.JPG         ← Filename
```

---

### Step 5: Executor (with --execute)

**Creates directory structure:**
```bash
mkdir -p /organized/Documents\ -\ 2996KD/2024/image/canadytw
```

**Copies file:**
```bash
cp /Users/canadytw/Documents/Documents\ -\ 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG \
   /organized/Documents\ -\ 2996KD/2024/image/canadytw/IMG_0001.JPG
```

**Creates metadata file:**
```bash
/organized/Documents - 2996KD/2024/image/canadytw/IMG_0001.JPG.meta.json
```

---

## Generated Metadata File

### `IMG_0001.JPG.meta.json`

```json
{
  "original_path": "/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG",
  "hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
  "size": 2048576,
  "type": "image",
  "owner": "canadytw",
  "year": "2024",
  "is_duplicate": false,
  "path_metadata": {
    "root_folder": "Documents - 2996KD",
    "relative_path": "Pictures/Land-Pics/8May16",
    "parent_folders": [
      "Pictures",
      "Land-Pics",
      "8May16"
    ],
    "tags": [
      "Pictures",
      "Land-Pics",
      "8May16"
    ],
    "date_tags": [
      "8May16"
    ],
    "category_tags": [
      "Pictures",
      "Land-Pics"
    ]
  }
}
```

---

## What You Can Search For

### By Tag
```bash
# Find all files from Land-Pics
grep -r "Land-Pics" /organized --include="*.meta.json"

# Or using jq
find /organized -name "*.meta.json" -exec jq 'select(.path_metadata.tags[] == "Land-Pics")' {} \;
```

### By Date
```bash
# Find all files from 8May16
grep -r "8May16" /organized --include="*.meta.json"
```

### By Root Structure
```bash
# Find all files from Documents - 2996KD
find /organized/"Documents - 2996KD" -name "*.meta.json"
```

---

## Complete File List Example

After processing your full directory, you might have:

```
/organized/
├── Documents - 2996KD/
│   ├── 2024/
│   │   ├── image/
│   │   │   └── canadytw/
│   │   │       ├── IMG_0001.JPG
│   │   │       ├── IMG_0001.JPG.meta.json
│   │   │       ├── IMG_0002.JPG
│   │   │       ├── IMG_0002.JPG.meta.json
│   │   │       └── ... (more images from Land-Pics/8May16/)
│   │   ├── document/
│   │   │   └── canadytw/
│   │   │       ├── report.pdf
│   │   │       └── report.pdf.meta.json
│   │   └── education/
│   │       └── canadytw/
│   │           ├── CS101_assignment.pdf
│   │           └── CS101_assignment.pdf.meta.json
│   └── 2023/
│       └── image/
│           └── canadytw/
│               └── old_photo.jpg
│
├── Desktop - Teufelshunde/
│   └── 2024/
│       ├── code/
│       │   └── canadytw/
│       │       ├── script.py
│       │       └── script.py.meta.json
│       └── document/
│           └── canadytw/
│               ├── notes.txt
│               └── notes.txt.meta.json
│
└── Desktop - 42739/
    └── 2024/
        └── spreadsheet/
            └── canadytw/
                ├── budget.xlsx
                └── budget.xlsx.meta.json
```

---

## Tracing a File Back

Let's say you find a file in the organized structure and want to know where it came from:

### File Location
```
/organized/Documents - 2996KD/2024/image/canadytw/IMG_0001.JPG
```

### Check Metadata
```bash
cat /organized/Documents\ -\ 2996KD/2024/image/canadytw/IMG_0001.JPG.meta.json | jq .path_metadata
```

### Result
```json
{
  "root_folder": "Documents - 2996KD",
  "relative_path": "Pictures/Land-Pics/8May16",
  "parent_folders": ["Pictures", "Land-Pics", "8May16"],
  "tags": ["Pictures", "Land-Pics", "8May16"]
}
```

### You now know:
- **Root structure:** Documents - 2996KD
- **Original path components:** Pictures → Land-Pics → 8May16
- **Context tags:** This was from Land-Pics collection, dated 8May16
- **Full original path:** Available in `original_path` field

---

## Database Records

### Files Table
```sql
SELECT * FROM files WHERE path LIKE '%IMG_0001.JPG%';
```

**Result:**
```
| id  | path                                                              | size    | hash          | scanned_at          |
|-----|-------------------------------------------------------------------|---------|---------------|---------------------|
| 123 | /Users/canadytw/Documents/Documents - 2996KD/.../IMG_0001.JPG     | 2048576 | a1b2c3d4e5... | 2024-11-14 10:30:00 |
```

### Classifications Table
```sql
SELECT c.* FROM classifications c
JOIN files f ON c.file_id = f.id
WHERE f.path LIKE '%IMG_0001.JPG%';
```

**Result:**
```
| id  | file_id | category | confidence | classified_at       |
|-----|---------|----------|------------|---------------------|
| 456 | 123     | image    | 0.8        | 2024-11-14 10:30:01 |
```

---

## Search Examples

### Find All Images from Land-Pics
```bash
# Using grep
grep -r '"Land-Pics"' /organized --include="*.meta.json" -l

# Using find + jq
find /organized -name "*.meta.json" | xargs jq 'select(.path_metadata.category_tags[] == "Land-Pics") | .original_path'
```

### Find All Files from May 8, 2016
```bash
# Using grep
grep -r '"8May16"' /organized --include="*.meta.json" -l

# Count them
grep -r '"8May16"' /organized --include="*.meta.json" -l | wc -l
```

### Find All Files from Documents - 2996KD
```bash
# Simple directory listing
ls -R /organized/"Documents - 2996KD"

# Count files
find /organized/"Documents - 2996KD" -type f ! -name "*.meta.json" | wc -l
```

---

## Restore Original Structure

If you ever need to restore files to their original locations, the metadata has everything you need:

```bash
#!/bin/bash
# restore_file.sh

META_FILE="$1"

# Extract original path
ORIGINAL_PATH=$(jq -r '.original_path' "$META_FILE")

# Get current file (remove .meta.json extension)
CURRENT_FILE="${META_FILE%.meta.json}"

# Create parent directory
mkdir -p "$(dirname "$ORIGINAL_PATH")"

# Copy back
cp "$CURRENT_FILE" "$ORIGINAL_PATH"

echo "Restored: $CURRENT_FILE -> $ORIGINAL_PATH"
```

**Usage:**
```bash
./restore_file.sh /organized/Documents\ -\ 2996KD/2024/image/canadytw/IMG_0001.JPG.meta.json
```

---

## Summary

### Your Example Path
```
/Users/canadytw/Documents/Documents - 2996KD/Pictures/Land-Pics/8May16/IMG_0001.JPG
```

### Results In

**Organized location:**
```
/organized/Documents - 2996KD/2024/image/canadytw/IMG_0001.JPG
```

**Metadata preserved:**
- ✅ Root structure: "Documents - 2996KD"
- ✅ Original path: Full path saved
- ✅ Tags: "Pictures", "Land-Pics", "8May16"
- ✅ Date tags: "8May16"
- ✅ Category: image
- ✅ Hash: SHA256 for deduplication
- ✅ Size: File size in bytes

**Searchable by:**
- Root structure name
- Any folder tag (Land-Pics, Pictures, 8May16)
- File type (image)
- Date (2024, 8May16)
- Hash (for finding duplicates)

---

**Ready to use!** Your specific requirements are fully implemented and documented.
