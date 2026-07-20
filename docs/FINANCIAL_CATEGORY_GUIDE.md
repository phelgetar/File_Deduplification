# Financial Category Guide

## Overview

The **financial** category automatically detects and classifies all financial and tax-related files, including Quicken, TurboTax, TaxAct, and H&R Block files.

---

## 🏦 Supported File Types

### Quicken Files

| Extension | Description |
|-----------|-------------|
| `.qdf` | Quicken Data File (primary data file) |
| `.qel` | Quicken Electronic Library |
| `.qfx` | Quicken Financial Exchange (download format) |
| `.qif` | Quicken Interchange Format (import/export) |
| `.qpb` | Quicken Backup File |
| `.qsd` | Quicken Supplemental Data |
| `.qph` | Quicken Home & Business |
| `.qxf` | Quicken Transfer Format |
| `.qmtf` | Quicken Money Transfer Format |
| `.qnx` | Quicken Network Exchange |
| `.q2023`, `.q2024`, etc. | Year-specific Quicken files |

### Tax Software Files

#### TurboTax
| Extension | Description |
|-----------|-------------|
| `.tax` | TurboTax Data File |
| `.tax2023`, `.tax2024`, etc. | Year-specific TurboTax files |
| `.txf` | Tax Exchange Format |

#### TaxAct
| Extension | Description |
|-----------|-------------|
| `.t23` | TaxAct 2023 |
| `.t24` | TaxAct 2024 |
| `.t25` | TaxAct 2025 |
| `.t26` | TaxAct 2026 |

#### H&R Block
| Extension | Description |
|-----------|-------------|
| `.h23` | H&R Block 2023 |
| `.h24` | H&R Block 2024 |
| `.h25` | H&R Block 2025 |
| `.h26` | H&R Block 2026 |

### Other Financial Files
| Extension | Description |
|-----------|-------------|
| `.wzd` | Encryption Wizard (for encrypted financial data) |

---

## 🔍 Filename Detection

Files are also classified as **financial** if they contain these keywords:

### Tax Keywords
- `tax`, `taxes`
- `1040`, `w2`, `w-2`, `1099`
- Forms: `schedule-a`, `schedule-c`, etc.

### Financial Keywords
- `quicken`, `finance`, `financial`
- `invoice`, `receipt`
- `banking`, `investment`
- `retirement`, `401k`, `ira`

### Examples
```
✅ 2023_Tax_Return.pdf           → financial
✅ W2_2024_Company.pdf            → financial
✅ Quicken_Backup_Jan2024.zip    → financial
✅ 1099-INT_Interest.pdf          → financial
✅ Investment_Portfolio.xlsx      → financial
✅ 401k_Statement_Q1.pdf          → financial
✅ Invoice_12345.pdf              → financial
```

---

## 📁 Organization Structure

Financial files are organized in their own category:

```
/organized/
  Documents - 2996KD/
    2024/
      financial/
        canadytw/
          ├── 2023_Taxes.tax2023
          ├── Quicken_Data.qdf
          ├── W2_2024.pdf
          ├── 1099_Interest.pdf
          └── Investment_Summary.xlsx
```

---

## 🚀 Usage Examples

### Example 1: Scan Financial Documents

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan your documents folder
python main.py /Users/canadytw/Documents \
  --base-dir /organized \
  --use-db \
  --dry-run-log
```

**Output:**
```
🔍 Scanning files...
  [1/100] Processing: 2023_Taxes.tax2023
  [2/100] Processing: Quicken_Data.qdf
  [3/100] Processing: W2_2024.pdf
  ...
🤖 Classifying files with AI...
  ✓ 2023_Taxes.tax2023 → financial
  ✓ Quicken_Data.qdf → financial
  ✓ W2_2024.pdf → financial (contains: 'w2')
```

### Example 2: Find All Financial Files

```bash
# After scanning with --use-db
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT f.path, f.size
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'financial'
ORDER BY f.path;"
```

### Example 3: Count Financial Files by Type

```bash
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'financial'
GROUP BY extension
ORDER BY count DESC;"
```

**Example Output:**
```
+-----------+-------+----------+
| extension | count | total_mb |
+-----------+-------+----------+
| tax2023   |    15 |    45.23 |
| qdf       |     8 |   120.50 |
| pdf       |    42 |    89.12 |
| xlsx      |    12 |    15.34 |
+-----------+-------+----------+
```

---

## 🔐 Security Considerations

### Encrypted Files

Financial files often contain sensitive data. The system supports:
- **Encryption Wizard** (`.wzd`) files are classified as **financial**
- Consider using `--write-metadata` to track encrypted file locations
- Keep backups of financial data in secure locations

### Best Practices

1. **Backup Before Organization**
   ```bash
   # Create backup
   cp -r /Users/canadytw/Documents/Financial ~/Backup_Financial_$(date +%Y%m%d)

   # Then organize
   python main.py ~/Documents/Financial --base-dir /organized --use-db --execute
   ```

2. **Use Database Tracking**
   ```bash
   # Always use --use-db for financial files
   python main.py /source --base-dir /output --use-db
   ```

3. **Write Metadata Files**
   ```bash
   # Create .meta.json for audit trail
   python main.py /source --base-dir /output --use-db --write-metadata --execute
   ```

---

## 📊 Query Examples

### Find Tax Returns by Year

```sql
SELECT f.path, f.size
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'financial'
  AND (
    f.path LIKE '%2023%'
    OR f.path LIKE '%.tax2023%'
    OR f.path LIKE '%.t23%'
    OR f.path LIKE '%.h23%'
  )
ORDER BY f.path;
```

### Find Quicken Backup Files

```sql
SELECT f.path, f.size, f.scanned_at
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'financial'
  AND f.path LIKE '%.qpb%'
ORDER BY f.scanned_at DESC;
```

### Calculate Total Size of Financial Files

```sql
SELECT
    COUNT(*) AS total_files,
    ROUND(SUM(f.size) / 1048576, 2) AS total_mb,
    ROUND(SUM(f.size) / 1073741824, 2) AS total_gb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'financial';
```

---

## 🧪 Testing

### Create Test Files

```bash
# Create test directory
mkdir -p /tmp/financial_test

# Create test files
touch /tmp/financial_test/2023_Taxes.tax2023
touch /tmp/financial_test/Quicken_Data.qdf
touch /tmp/financial_test/W2_2024.pdf
touch /tmp/financial_test/1099_INT.pdf
touch /tmp/financial_test/Investment_Report.xlsx

# Scan them
python main.py /tmp/financial_test \
  --base-dir /tmp/organized \
  --use-db \
  --max-files 10
```

### Verify Classification

```bash
# Check in database
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT f.path, c.category
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE f.path LIKE '%financial_test%';"
```

**Expected Result:**
```
+---------------------------------------------+------------+
| path                                        | category   |
+---------------------------------------------+------------+
| /tmp/financial_test/2023_Taxes.tax2023     | financial  |
| /tmp/financial_test/Quicken_Data.qdf       | financial  |
| /tmp/financial_test/W2_2024.pdf            | financial  |
| /tmp/financial_test/1099_INT.pdf           | financial  |
| /tmp/financial_test/Investment_Report.xlsx | financial  |
+---------------------------------------------+------------+
```

---

## 🔧 Customization

### Add Custom Financial Keywords

Edit `core/classifier.py` to add your own keywords:

```python
# Financial files by name/path
elif any(keyword in file_name or keyword in file_path_str.lower() for keyword in [
    "tax", "taxes", "1040", "w2", "w-2", "1099", "quicken", "finance", "financial",
    "invoice", "receipt", "banking", "investment", "retirement", "401k", "ira",
    "your_custom_keyword",  # Add here
    "another_keyword"
]):
    category = "financial"
```

### Add Custom Extensions

```python
# Financial and Tax files
elif file_extension in [
    # Quicken files
    ".qdf", ".qel", ".qfx", ".qif", ".qpb", ".qsd", ".qph", ".qxf", ".qmtf", ".qnx",
    # Tax software files
    ".tax", ".txf",
    ".t23", ".t24", ".t25", ".t26",
    ".h23", ".h24", ".h25", ".h26",
    ".your_custom_ext",  # Add here
]:
    category = "financial"
```

---

## 📈 Statistics

### Total Categories Now: 20

The system now supports **20 file categories** (up from 19):

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
16. **financial** ← NEW!
17. backup
18. temporary
19. system
20. other

---

## 💡 Tips

### 1. Organize Financial Files Separately

```bash
# Scan only financial folders
python main.py /Users/canadytw/Documents/Taxes \
  --base-dir /organized_finances \
  --use-db \
  --execute
```

### 2. Use Filters for Specific Years

```bash
# Process only 2023 tax files
python main.py /Documents \
  --base-dir /organized \
  --use-db \
  --filter "Taxes/2023"
```

### 3. Generate Financial File Report

```bash
# Create a report of all financial files
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT f.path, ROUND(f.size/1048576,2) AS size_mb, f.scanned_at
      FROM files f LEFT JOIN classifications c ON f.id = c.file_id
      WHERE c.category = 'financial'
      ORDER BY f.scanned_at DESC" \
  > financial_files_report.txt
```

---

## 🆘 Troubleshooting

### Issue: Financial File Not Detected

**Check the extension:**
```bash
# See what extension the file has
ls -la your_file.*
```

**Check if it's in the list:**
- Review the supported extensions above
- If missing, add it to `core/classifier.py`

### Issue: PDF Not Classified as Financial

**Cause:** PDF doesn't have financial keywords in filename

**Solution:** Rename to include keywords:
```bash
# Before: document.pdf → other
# After: 2023_Tax_Return.pdf → financial
```

Or add custom keywords to the classifier.

### Issue: Quicken File Shows as "data"

**Cause:** Old version before financial category added

**Solution:** Reclassify files:
```bash
python scripts/reclassify_files.py --categories data --verbose
```

---

## ✅ Summary

### Detected by Extension
- ✅ All Quicken formats (`.qdf`, `.qel`, `.qfx`, `.qif`, etc.)
- ✅ TurboTax (`.tax`, `.tax2023`, `.txf`)
- ✅ TaxAct (`.t23`, `.t24`, `.t25`, `.t26`)
- ✅ H&R Block (`.h23`, `.h24`, `.h25`, `.h26`)

### Detected by Filename
- ✅ Tax keywords: `tax`, `1040`, `w2`, `1099`
- ✅ Financial keywords: `quicken`, `finance`, `invoice`, `banking`, `investment`, `401k`

### Organization
- ✅ Separate `/financial/` category
- ✅ Organized by year/owner
- ✅ Root structure preserved

---

**Version:** 0.8.0
**Last Updated:** 2025-11-14
**Module:** `core/classifier.py`
