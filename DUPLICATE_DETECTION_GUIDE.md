# Duplicate Detection Guide

## Overview

The duplicate detection system identifies files with identical content by comparing SHA256 hashes. This helps you find and manage duplicate files across your file collection.

---

## 🔍 How It Works

### Detection Process

1. **Hash Generation**: Each file is hashed using SHA256
2. **Hash Comparison**: Files with identical hashes are duplicates
3. **Duplicate Marking**: First file is kept as "original", others marked as "duplicates"
4. **Database Tracking**: Duplicates are marked in the database with reference to original

### What Counts as a Duplicate?

- **Same content** (identical SHA256 hash)
- **Any filename** (duplicates can have different names)
- **Any location** (duplicates can be in different directories)

---

## 🚀 Quick Start

### Basic Duplicate Detection

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Detect duplicates (shows them but processes all files)
python main.py /source --base-dir /output --use-db

# The output will show:
# 📂 Unique files: 950, Duplicates: 50
```

### Skip Duplicate Files

```bash
# Only process unique files (skip duplicates)
python main.py /source --base-dir /output --use-db --skip-duplicates
```

### Generate Duplicate Report

```bash
# Create a detailed report of all duplicates
python main.py /source --base-dir /output --use-db --duplicate-report duplicates_report.txt
```

---

## 📋 Command Options

### `--skip-duplicates`
Only process unique files. Duplicate files are:
- Detected and marked
- Saved to database (with duplicate flag)
- **NOT** classified or organized
- **NOT** included in the output plan

**Use when:**
- You only want to organize unique files
- You want to save processing time
- You'll handle duplicates separately later

**Example:**
```bash
python main.py /Photos --base-dir /organized --use-db --skip-duplicates
```

### `--duplicate-report [filename]`
Generate a detailed report of all duplicate files.

**Report includes:**
- Hash of duplicate files
- File size and wasted space
- Path to original file
- Paths to all duplicates
- Summary statistics

**Use when:**
- You want to review duplicates before deleting
- You need to document duplicate files
- You want to analyze wasted disk space

**Example:**
```bash
python main.py /Documents --base-dir /temp --use-db --duplicate-report dupes.txt
```

---

## 📊 Example Output

### Console Output

```
🔍 Scanning files...
🧮 Files matched: 1000

🔑 Generating file hashes...
📂 Files hashed: 1000

🔍 Detecting duplicates...

🔍 Found 2 duplicate(s) of: history9.txt
   Hash: 3a4f2b8c1d9e5f...
   Original: /Users/you/Documents/history9.txt
   Duplicate: /Users/you/Backup/history9.txt
   Duplicate: /Users/you/Archive/important_history.txt

🔍 Found 1 duplicate(s) of: photo.jpg
   Hash: 7b3c9a1f4e2d8...
   Original: /Users/you/Photos/photo.jpg
   Duplicate: /Users/you/Photos/Backup/photo.jpg

📊 Duplicate Detection Results:
   Unique files: 997
   Duplicate files: 3
   Total files: 1000

📂 Unique files: 997, Duplicates: 3
```

### Duplicate Report

```
================================================================================
                        DUPLICATE FILES REPORT
================================================================================

Duplicate Group #1
  Hash: 3a4f2b8c1d9e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
  Size: 2,048,576 bytes (2.00 MB)
  Count: 3 files
  Wasted: 4,097,152 bytes (4.00 MB)

  Original: /Users/you/Documents/history9.txt
  Duplicate: /Users/you/Backup/history9.txt
  Duplicate: /Users/you/Archive/important_history.txt

--------------------------------------------------------------------------------

Duplicate Group #2
  Hash: 7b3c9a1f4e2d8c5b6a7f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9c0a1b
  Size: 5,242,880 bytes (5.00 MB)
  Count: 2 files
  Wasted: 5,242,880 bytes (5.00 MB)

  Original: /Users/you/Photos/photo.jpg
  Duplicate: /Users/you/Photos/Backup/photo.jpg

--------------------------------------------------------------------------------

================================================================================
SUMMARY
================================================================================
Total duplicate groups: 2
Total duplicate files: 3
Total wasted space: 9,340,032 bytes (0.01 GB)
================================================================================
```

---

## 🎯 Your Specific Case

You mentioned:
- `history9.txt` appears multiple times
- Another file with different name but same content
- All 3 have the same hash

### How to Find Them

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Run with duplicate detection and report
python main.py /path/with/duplicates \
  --base-dir /temp/output \
  --use-db \
  --duplicate-report my_duplicates.txt

# Check the report
cat my_duplicates.txt
```

### Expected Output

You should see something like:
```
🔍 Found 2 duplicate(s) of: history9.txt
   Hash: [same hash for all 3]
   Original: /path/to/first/history9.txt
   Duplicate: /path/to/second/history9.txt
   Duplicate: /path/to/third/different_name.txt
```

---

## 🗄️ Database Integration

### Duplicate Fields in Database

The `files` table tracks duplicates:
```sql
SELECT
    path,
    hash,
    is_duplicate,
    duplicate_of
FROM files
WHERE is_duplicate = TRUE;
```

### Query Examples

**Find all duplicates:**
```sql
SELECT
    f1.path AS duplicate_file,
    f1.duplicate_of AS original_file,
    f1.hash,
    f1.size
FROM files f1
WHERE f1.is_duplicate = TRUE
ORDER BY f1.hash;
```

**Find duplicates of a specific file:**
```sql
SELECT path, size
FROM files
WHERE hash = (
    SELECT hash FROM files WHERE path = '/path/to/your/file.txt'
)
AND is_duplicate = TRUE;
```

**Calculate wasted space:**
```sql
SELECT
    hash,
    COUNT(*) - 1 AS duplicate_count,
    size AS file_size,
    (COUNT(*) - 1) * size AS wasted_space
FROM files
WHERE hash IN (
    SELECT hash
    FROM files
    GROUP BY hash
    HAVING COUNT(*) > 1
)
GROUP BY hash, size
ORDER BY wasted_space DESC;
```

---

## 🛠️ Workflow Examples

### Workflow 1: Find and Review Duplicates

```bash
# Step 1: Scan and generate report
python main.py /Documents \
  --base-dir /temp \
  --use-db \
  --duplicate-report duplicates.txt

# Step 2: Review the report
cat duplicates.txt

# Step 3: Manually decide what to keep/delete
# (No files moved yet - just review)
```

### Workflow 2: Organize Only Unique Files

```bash
# Step 1: Organize unique files, skip duplicates
python main.py /Photos \
  --base-dir /organized_photos \
  --use-db \
  --skip-duplicates \
  --execute

# Step 2: Handle duplicates separately
# Query database for duplicates
# Delete or archive as needed
```

### Workflow 3: Full Analysis

```bash
# Step 1: Scan with all options
python main.py /Backup \
  --base-dir /organized \
  --use-db \
  --metadata-only-size 75MB \
  --duplicate-report backup_dupes.txt \
  --dry-run-log

# Step 2: Review both reports
cat backup_dupes.txt
cat dry_run_preview_*.txt

# Step 3: Execute if satisfied
python main.py /Backup \
  --base-dir /organized \
  --use-db \
  --metadata-only-size 75MB \
  --skip-duplicates \
  --execute
```

---

## 🎓 Understanding Duplicate Detection

### What Gets Detected

✅ **Detected as duplicates:**
- Exact copies with same name
- Exact copies with different names
- Files in different locations with same content
- Renamed files with same content

❌ **NOT detected as duplicates:**
- Similar files with slight differences
- Different versions of a file
- Files with same name but different content
- Metadata-only files (>threshold size, no hash)

### Limitations

1. **Metadata-only files**: Files larger than `--metadata-only-size` threshold are not hashed, so duplicates won't be detected

2. **Content-based only**: Detection is based purely on file content (hash), not filename

3. **First-come basis**: The first file encountered is marked as "original", others as duplicates (arbitrary choice)

---

## 💡 Best Practices

### 1. Always Use with Database

```bash
# GOOD: Duplicates are tracked in database
python main.py /source --base-dir /output --use-db

# BAD: Duplicate info is lost after scan
python main.py /source --base-dir /output
```

### 2. Generate Reports for Large Scans

```bash
# Save report for later review
python main.py /large/directory \
  --base-dir /output \
  --use-db \
  --duplicate-report report_$(date +%Y%m%d).txt
```

### 3. Test with Dry Run First

```bash
# See what would happen without making changes
python main.py /source \
  --base-dir /output \
  --use-db \
  --skip-duplicates \
  --dry-run-log
```

### 4. Use --skip-duplicates for Organization

```bash
# Only organize unique files
python main.py /messy/folder \
  --base-dir /organized \
  --use-db \
  --skip-duplicates \
  --execute
```

---

## 🔧 Troubleshooting

### Issue: No Duplicates Detected

**Possible causes:**
1. Files are actually unique (no duplicates)
2. Using `--metadata-only-size` that's too low (large files not hashed)
3. Files haven't been hashed yet (missing `--use-db` or first scan)

**Solution:**
```bash
# Make sure files are fully hashed
python main.py /source --base-dir /output --use-db

# Check database
mysql -u user -p -D File_Deduplification -e "
SELECT COUNT(*) FROM files GROUP BY hash HAVING COUNT(*) > 1;"
```

### Issue: Different Files Marked as Duplicates

**Cause:** Hash collision (extremely rare with SHA256)

**Solution:**
- Verify files are actually the same: `diff file1 file2`
- Report if you find a genuine SHA256 collision (extremely valuable!)

### Issue: Duplicate Report is Empty

**Cause:** No duplicates found, or files not hashed

**Solution:**
```bash
# Ensure files are hashed
python main.py /source --base-dir /output --use-db --duplicate-report report.txt

# Check if report file exists
ls -lh report.txt
cat report.txt
```

---

## 📈 Performance Considerations

### Speed

- **Duplicate detection**: Very fast (O(n) hash table lookup)
- **Hash generation**: Slower for large files
- **With `--skip-duplicates`**: Faster overall (fewer files to classify)

### Memory Usage

- Stores hash → file list mapping in memory
- For 1 million files: ~100-200 MB RAM
- Acceptable for most systems

### Disk Space Savings

Example from a 1TB drive:
```
Scanned: 50,000 files (800 GB)
Found: 5,000 duplicates (120 GB wasted)
Savings: 15% disk space recovered
```

---

## 🆘 Getting Help

### Check Duplicate Status

```sql
-- In database
SELECT
    is_duplicate,
    COUNT(*) as count,
    SUM(size) as total_size
FROM files
GROUP BY is_duplicate;
```

### Verify Detection Works

```bash
# Create test duplicates
cp test.txt test_copy.txt

# Run detection
python main.py . --base-dir /tmp/test --use-db --duplicate-report test.txt

# Should show 1 duplicate detected
cat test.txt
```

---

## ✅ Success Checklist

After running duplicate detection:

- [ ] Console shows "Detecting duplicates..." step
- [ ] Duplicate count is displayed
- [ ] Duplicates marked in database (if `--use-db`)
- [ ] Report generated (if `--duplicate-report`)
- [ ] Unique files count is correct
- [ ] No errors in duplicate detection

---

**Version**: 0.7.1
**Last Updated**: 2025-11-13
**Module**: `core/deduplicator.py`
