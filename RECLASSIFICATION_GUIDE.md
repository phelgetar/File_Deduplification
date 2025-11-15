# File Reclassification Guide

## Overview

The `reclassify_files.py` script allows you to update file classifications in your database using the improved classifier **without re-scanning files**. This is perfect for applying the v0.7.0 classification improvements to your existing database.

---

## 🎯 Use Cases

### When to Use Reclassification

1. **After upgrading to v0.7.0** - Apply new classification to existing files
2. **Files marked as "other"** - Reclassify with expanded file type support
3. **Incorrect classifications** - Fix mis-categorized files
4. **After adding new file types** - Update classifications to use new categories

### When NOT to Use

- **Files have moved** - Script checks if files still exist at original paths
- **You want to re-scan** - Use main.py instead to re-scan and re-hash
- **Database is corrupt** - Fix database issues first

---

## 🚀 Quick Start

### Basic Usage

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Reclassify files marked as "other" (most common use case)
python scripts/reclassify_files.py --categories other

# Dry run first to see what would change
python scripts/reclassify_files.py --categories other --dry-run
```

---

## 📋 Command Options

### Reclassify Specific Categories

```bash
# Reclassify only "other" files
python scripts/reclassify_files.py --categories other

# Reclassify "other" and "unknown" files
python scripts/reclassify_files.py --categories other unknown

# Reclassify multiple categories
python scripts/reclassify_files.py --categories other unknown data system
```

### Reclassify All Files

```bash
# Update ALL files in database (useful after major classifier updates)
python scripts/reclassify_files.py --all
```

### Dry Run Mode

```bash
# See what would change without modifying database
python scripts/reclassify_files.py --categories other --dry-run

# Dry run with detailed output
python scripts/reclassify_files.py --categories other --dry-run --verbose
```

### Verbose Output

```bash
# Show progress for each file
python scripts/reclassify_files.py --categories other --verbose

# Show only summary (default)
python scripts/reclassify_files.py --categories other
```

---

## 📊 Example Output

### Dry Run Output

```
======================================================================
  RECLASSIFICATION DRY RUN STARTED
======================================================================
Files to process: 139
Mode: DRY RUN (no changes will be saved)
======================================================================

[1/139] 📝 other → installer: HP Easy Start.app
[15/139] 📝 other → font: Arial.ttf
[23/139] 📝 other → certificate: cert.p7b
[45/139] 📝 other → shortcut: bookmark.webloc
  Processing... 50/139
  Processing... 100/139

======================================================================
  RECLASSIFICATION DRY RUN COMPLETE
======================================================================

📊 SUMMARY:
  Total files in database: 139
  Files checked: 139
  Files updated: 127
  Files unchanged: 12
  Files missing: 0

📈 CATEGORY CHANGES:

  From 'other':
    → installer: 45 files
    → code: 28 files
    → font: 18 files
    → certificate: 15 files
    → shortcut: 12 files
    → system: 9 files

💡 This was a DRY RUN. Run without --dry-run to apply changes.

======================================================================
```

### Live Update Output

```
======================================================================
  RECLASSIFICATION STARTED
======================================================================
Files to process: 139
Mode: LIVE UPDATE
======================================================================

  Processing... 10/139
  Processing... 20/139
  ...
  Processing... 130/139

======================================================================
  RECLASSIFICATION COMPLETE
======================================================================

📊 SUMMARY:
  Total files in database: 139
  Files checked: 139
  Files updated: 127
  Files unchanged: 12
  Files missing: 0

📈 CATEGORY CHANGES:

  From 'other':
    → installer: 45 files
    → code: 28 files
    → font: 18 files
    → certificate: 15 files
    → shortcut: 12 files
    → system: 9 files

======================================================================
```

---

## 🔍 Before & After Comparison

### Query Categories Before Reclassification

```sql
SELECT category, COUNT(*) as count
FROM classifications
GROUP BY category
ORDER BY count DESC;
```

**Output:**
```
category        count
-----------------------
document        386
data            203
image           188
other           139  ← These will be reclassified
spreadsheet     31
archive         25
...
```

### After Reclassification

```
category        count
-----------------------
document        386
data            203
image           188
code            41     ← 28 from "other"
installer       45     ← NEW: from "other"
spreadsheet     31
archive         25
font            18     ← NEW: from "other"
certificate     15     ← NEW: from "other"
other           12     ← Reduced from 139!
shortcut        12     ← NEW: from "other"
system          9      ← NEW: from "other"
```

---

## 🛡️ Safety Features

### Dry Run Protection
```bash
# ALWAYS run dry run first
python scripts/reclassify_files.py --categories other --dry-run

# Then apply if results look good
python scripts/reclassify_files.py --categories other
```

### File Existence Checking
- Script verifies files still exist at original paths
- Missing files are skipped and counted
- No database corruption if files have been moved

### Database Transaction Safety
- Uses proper SQLAlchemy sessions
- Changes are committed transactionally
- Rollback on error

---

## 📈 Recommended Workflow

### Step 1: Backup Database

```bash
# Backup before reclassification
mysqldump -u jarheads_0231 -p File_Deduplification > backup_before_reclassify.sql
```

### Step 2: Check Current State

```bash
# See how many "other" files you have
mysql -u jarheads_0231 -p File_Deduplification -e "
SELECT category, COUNT(*) as count
FROM classifications
WHERE category IN ('other', 'unknown')
GROUP BY category;"
```

### Step 3: Dry Run

```bash
# See what would change
python scripts/reclassify_files.py --categories other --dry-run
```

### Step 4: Apply Changes

```bash
# Apply reclassification
python scripts/reclassify_files.py --categories other
```

### Step 5: Verify Results

```bash
# Check updated categories
mysql -u jarheads_0231 -p File_Deduplification -e "
SELECT category, COUNT(*) as count
FROM classifications
GROUP BY category
ORDER BY count DESC;"
```

---

## 🎓 Advanced Usage

### Reclassify Specific File Types

```sql
-- Find files with specific extensions marked as "other"
SELECT f.path, c.category
FROM files f
JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
AND f.path LIKE '%.exe';

-- Then reclassify
```

### Reclassify by Date Range

```sql
-- Find recently added files marked as "other"
SELECT COUNT(*)
FROM files f
JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
AND f.scanned_at > '2025-11-01';
```

### Selective Category Updates

```bash
# Reclassify only data and system categories
python scripts/reclassify_files.py --categories data system
```

---

## 🐛 Troubleshooting

### Issue: "No files found matching criteria"

**Cause**: No files in database with specified categories

**Solution**:
```bash
# Check what categories exist
mysql -u jarheads_0231 -p File_Deduplification -e "
SELECT DISTINCT category FROM classifications;"
```

### Issue: "Database connection failed"

**Cause**: .env file not configured or database not running

**Solution**:
```bash
# Check database connection
python test_db_connection.py

# Verify .env file exists
cat .env
```

### Issue: Many files marked as "missing"

**Cause**: Files have been moved or deleted since original scan

**Solution**:
- Re-scan the directory with main.py
- Or manually clean up database:
```sql
-- Find missing files
SELECT f.path
FROM files f
WHERE NOT EXISTS (
  SELECT 1 FROM classifications c
  WHERE c.file_id = f.id
);
```

### Issue: Reclassification is slow

**Cause**: Processing many files

**Solution**:
```bash
# Process in batches
python scripts/reclassify_files.py --categories other --verbose

# Or use SQL to limit
```

---

## 📊 Performance

### Speed Estimates

| Files | Dry Run | Live Update |
|-------|---------|-------------|
| 100   | ~2 sec  | ~5 sec      |
| 1,000 | ~15 sec | ~30 sec     |
| 10,000| ~2 min  | ~4 min      |
| 100,000| ~20 min | ~40 min     |

**Note**: Speed depends on:
- File system performance
- Database query speed
- Whether files still exist

### Optimization Tips

1. **Run during off-hours** for large datasets
2. **Use --dry-run first** to estimate time
3. **Close other database connections** to avoid locks
4. **Consider batching** for very large datasets

---

## 🔗 Integration with Main Workflow

### After Initial Scan

```bash
# 1. Initial scan
python main.py /source --base-dir /output --use-db

# 2. Upgrade to v0.7.0
git pull

# 3. Reclassify existing files
python scripts/reclassify_files.py --categories other

# 4. Continue with new scans
python main.py /new_source --base-dir /output --use-db
```

### Periodic Maintenance

```bash
# Weekly: Check for "other" files
mysql -u jarheads_0231 -p File_Deduplification -e "
SELECT COUNT(*) as other_count
FROM classifications
WHERE category = 'other';"

# If > 0, reclassify
python scripts/reclassify_files.py --categories other
```

---

## 🎯 Your Specific Case

Based on your database having **139 files** marked as "other":

### Recommended Commands

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# 1. Dry run to see what would change
python scripts/reclassify_files.py --categories other --dry-run

# 2. Review output, then apply
python scripts/reclassify_files.py --categories other

# 3. Verify results
mysql -u jarheads_0231 -p'jQ4sr8zP5;V=&iHInU' -D File_Deduplification -e "
SELECT category, COUNT(*) as count
FROM classifications
GROUP BY category
ORDER BY count DESC;"
```

### Expected Results

- **139 "other" files** will be re-examined
- **~127 files** will be reclassified (based on v0.7.0 improvements)
- **~12 files** may remain as "other" (truly unknown types)
- **New categories** will appear: installer, font, certificate, shortcut, etc.

---

## 📝 Script Details

### What It Does

1. Queries database for files matching criteria
2. Checks if files still exist on disk
3. Re-runs classifier on file paths
4. Compares old vs new category
5. Updates classifications table if changed
6. Provides detailed statistics

### What It Doesn't Do

- **Re-scan files** - Uses existing file paths
- **Re-hash files** - Uses existing hashes
- **Move files** - Only updates database classifications
- **Delete records** - Only updates categories

---

## 🆘 Getting Help

### View Built-in Help

```bash
python scripts/reclassify_files.py --help
```

### Check Version

```bash
head -n 20 scripts/reclassify_files.py | grep Version
```

### Report Issues

If you encounter problems:
1. Run with `--dry-run --verbose` to see details
2. Check database connection with `test_db_connection.py`
3. Verify files still exist at original paths

---

## ✅ Success Checklist

After reclassification:

- [ ] Dry run completed successfully
- [ ] Live update completed without errors
- [ ] "other" count reduced significantly
- [ ] New categories appear in database
- [ ] File counts match expectations
- [ ] No files marked as "missing"
- [ ] Database backup created (recommended)

---

**Version**: 0.7.1
**Last Updated**: 2025-11-13
**Script**: `scripts/reclassify_files.py`
