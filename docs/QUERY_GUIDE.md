# SQL Query Guide - Finding "Other" Files

## Quick Start

### Connect to Database
```bash
mysql -u jarheads_0231 -p -D File_Deduplification
```

### Run All Queries
```bash
mysql -u jarheads_0231 -p -D File_Deduplification < queries/find_other_files.sql
```

---

## Most Useful Queries

### 1. Count Files by Extension
Shows how many files of each type are classified as "other":
```sql
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS file_extension,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_size_mb,
    MIN(f.path) AS example_file
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY file_extension
ORDER BY count DESC;
```

**Example Output:**
```
+----------------+-------+---------------+--------------------------------+
| file_extension | count | total_size_mb | example_file                   |
+----------------+-------+---------------+--------------------------------+
| bak            |   245 |        125.50 | /docs/report.bak               |
| dat            |   189 |         89.23 | /data/cache.dat                |
| xyz            |    42 |         12.10 | /projects/model.xyz            |
+----------------+-------+---------------+--------------------------------+
```

### 2. Summary Statistics
Quick overview of "other" files:
```sql
SELECT
    'Total "other" files' AS metric,
    COUNT(*) AS value
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'

UNION ALL

SELECT
    'Total size (GB)',
    ROUND(SUM(f.size) / 1073741824, 2)
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other';
```

### 3. Largest "Other" Files
Find the biggest unclassified files:
```sql
SELECT
    f.path,
    ROUND(f.size / 1048576, 2) AS size_mb,
    SUBSTRING_INDEX(f.path, '.', -1) AS extension
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
ORDER BY f.size DESC
LIMIT 20;
```

### 4. Find Potential Education Files
Files that might be education-related:
```sql
SELECT
    f.path,
    SUBSTRING_INDEX(f.path, '/', -1) AS filename,
    ROUND(f.size / 1048576, 2) AS size_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
  AND (
    LOWER(f.path) LIKE '%/cs%'
    OR LOWER(f.path) LIKE '%/ceg%'
    OR LOWER(f.path) LIKE '%/stat%'
    OR LOWER(f.path) LIKE '%/mat%'
  )
LIMIT 50;
```

---

## Export to CSV

### Export All "Other" Files
```bash
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT f.path, SUBSTRING_INDEX(f.path, '.', -1) AS extension,
      f.size, c.category FROM files f
      LEFT JOIN classifications c ON f.id = c.file_id
      WHERE c.category = 'other'" \
  > other_files.csv
```

### Export Extension Summary
```bash
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT SUBSTRING_INDEX(f.path, '.', -1) AS extension, COUNT(*) AS count
      FROM files f LEFT JOIN classifications c ON f.id = c.file_id
      WHERE c.category = 'other' GROUP BY extension ORDER BY count DESC" \
  > other_extensions.csv
```

---

## Categories Now Supported

After the recent updates, the system supports **19 categories**:

| Category      | Examples                                    |
|---------------|---------------------------------------------|
| image         | .jpg, .png, .heic, .raw, .psd              |
| video         | .mp4, .mov, .mkv, .vob, .ts                |
| audio         | .mp3, .flac, .opus, .aiff, .mid            |
| document      | .pdf, .docx, .tex, .epub, .pages           |
| spreadsheet   | .xlsx, .csv, .ods, .numbers                |
| presentation  | .pptx, .odp, .key                          |
| code          | .py, .js, .swift, .rs, .lisp, .ps1         |
| archive       | .zip, .dmg, .iso, .ova, .mdzip             |
| data          | .json, .xml, .sqlite, .toml, .ini          |
| font          | .ttf, .otf, .woff, .woff2                  |
| installer     | .exe, .pkg, .dmg, .apk, .msu               |
| **certificate** | **.cer, .csr, .pem, .pfx, .p7b, .key**   |
| shortcut      | .lnk, .webloc, .url, .rdp                  |
| scientific    | .mat, .hdf5, .fits, .npy, .rdata           |
| **education** | **Files starting with CS, CEG, STAT, MAT** |
| backup        | .bak, .old, .orig, .swp                    |
| temporary     | .tmp, .crdownload, .cache, .part           |
| system        | .plist, .strings, .nib, Makefile           |
| other         | Unrecognized formats                       |

---

## New Features Added

### ✅ Certificate Category
Already exists! Includes:
- .cer, .csr, .pem, .pfx (your requested extensions)
- Plus: .p7b, .p12, .crt, .der, .key, .p7c, .spc, .pub

### ✅ Education Category (NEW!)
Detects files with these prefixes:
- **CS** (Computer Science)
- **CEG** (Computer Engineering)
- **STAT** (Statistics)
- **MAT** (Mathematics)
- Plus: ECON, PHYS, CHEM, BIO, ENG, MATH

**Examples:**
- `CS101_assignment.pdf` → education
- `CEG3120_lab5.zip` → education
- `STAT401_homework.docx` → education
- `MAT251_notes.txt` → education

---

## Testing the Changes

### Test Education Classification
```bash
# Create a test file
touch /tmp/CS101_test.txt

# Run scan
python main.py /tmp --base-dir /output --use-db

# Check classification in database
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT f.path, c.category FROM files f
      LEFT JOIN classifications c ON f.id = c.file_id
      WHERE f.path LIKE '%CS101%'"
```

### Verify Certificate Classification
```sql
SELECT
    f.path,
    c.category
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE f.path LIKE '%.cer'
   OR f.path LIKE '%.csr'
   OR f.path LIKE '%.pem'
   OR f.path LIKE '%.pfx'
LIMIT 20;
```

---

## Common Tasks

### Find All Unclassified Files
```sql
SELECT path, size
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
ORDER BY size DESC;
```

### Count Files by Category
```sql
SELECT
    c.category,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1073741824, 2) AS total_gb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
GROUP BY c.category
ORDER BY count DESC;
```

### Find Files Without Classification
```sql
SELECT f.path, f.size
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category IS NULL
LIMIT 50;
```

---

## Reclassify Existing Files

If you have existing files that should now be classified as "education":

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Reclassify all "other" files
python scripts/reclassify_files.py --categories other --verbose

# Or reclassify everything
python scripts/reclassify_files.py --all
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Connect to DB | `mysql -u jarheads_0231 -p -D File_Deduplification` |
| Run queries | `source queries/find_other_files.sql` |
| Count "other" files | `SELECT COUNT(*) FROM files f LEFT JOIN classifications c ON f.id = c.file_id WHERE c.category = 'other';` |
| List extensions | Query #2 in find_other_files.sql |
| Export to CSV | `mysql ... -e "SELECT ..." > output.csv` |
| Reclassify | `python scripts/reclassify_files.py --categories other` |

---

**Last Updated:** 2025-11-14
**Version:** 0.7.0
