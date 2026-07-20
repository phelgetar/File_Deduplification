# SQL Query Tab Labeling Guide

## Overview

When running multiple SQL queries, each result opens in a separate tab. This guide shows different methods to label and identify those tabs.

---

## Method 1: Query Label Column (Recommended)

Add a label column as the **first column** in each SELECT statement:

### Before:
```sql
SELECT
    f.path,
    f.size,
    c.category
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other';
```

### After:
```sql
SELECT
    'Q1: Basic List' AS Query,  -- ✅ Add this label column
    f.path,
    f.size,
    c.category
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other';
```

### Result:
```
┌──────────────────┬─────────────────────────┬─────────┬──────────┐
│ Query            │ path                    │ size    │ category │
├──────────────────┼─────────────────────────┼─────────┼──────────┤
│ Q1: Basic List   │ /Documents/file1.xyz    │ 1024    │ other    │
│ Q1: Basic List   │ /Documents/file2.abc    │ 2048    │ other    │
└──────────────────┴─────────────────────────┴─────────┴──────────┘
```

**Benefits:**
- ✅ Works in all SQL clients
- ✅ Label visible in every row
- ✅ Easy to identify results when scrolling
- ✅ Labels included when exporting to CSV
- ✅ Can filter/sort by label column

---

## Method 2: Comment-Based Tab Names

Some SQL clients (like MySQL Workbench) use the first comment as the tab name:

```sql
-- Q2: Files By Extension
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS file_extension,
    COUNT(*) AS count
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY file_extension;
```

**Note:** This depends on your SQL client and may not work everywhere.

---

## Method 3: Run Queries Separately with Named Files

Create separate SQL files for each query:

```
queries/
├── q1_basic_list.sql
├── q2_by_extension.sql
├── q3_extension_details.sql
├── q4_by_directory.sql
└── ...
```

Run individually:
```bash
mysql -u jarheads_0231 -p -D File_Deduplification < queries/q1_basic_list.sql
```

---

## Method 4: Use MySQL Workbench Saved Queries

In MySQL Workbench:

1. **Save each query** with a descriptive name
2. **Run from saved queries** - tab name matches saved query name
3. **Create query collection** for related queries

---

## Method 5: Custom Result Identifier

Add a unique identifier that shows which query and result number:

```sql
SELECT
    'Q2-Extension' AS QueryID,
    ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS ResultNum,
    SUBSTRING_INDEX(f.path, '.', -1) AS file_extension,
    COUNT(*) AS count
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY file_extension;
```

Result:
```
┌──────────────┬───────────┬────────────────┬───────┐
│ QueryID      │ ResultNum │ file_extension │ count │
├──────────────┼───────────┼────────────────┼───────┤
│ Q2-Extension │ 1         │ xyz            │ 150   │
│ Q2-Extension │ 2         │ abc            │ 120   │
│ Q2-Extension │ 3         │ def            │ 95    │
└──────────────┴───────────┴────────────────┴───────┘
```

---

## Comparison of Methods

| Method | Pros | Cons | Works In |
|--------|------|------|----------|
| **Label Column** | ✅ Universal<br>✅ Always visible<br>✅ Exports to CSV | Takes up column space | All SQL clients |
| **Comments** | ✅ Clean results<br>✅ No extra columns | ❌ Client-dependent<br>❌ May not work | Some SQL clients |
| **Separate Files** | ✅ Organized<br>✅ Easy to manage | ❌ More files to maintain | Command line |
| **Saved Queries** | ✅ Workbench integration<br>✅ Easy to run | ❌ Workbench-specific | MySQL Workbench only |
| **Result ID** | ✅ Row numbering<br>✅ Detailed tracking | More complex queries | All SQL clients |

---

## Recommended Approach

**For your "find_other_files.sql"**, I recommend **Method 1 (Label Column)** because:

1. ✅ Works everywhere (command line, Workbench, DBeaver, etc.)
2. ✅ Labels are part of the data - visible when scrolling
3. ✅ Easy to export and share results
4. ✅ Can filter results: `WHERE Query = 'Q2: By Extension'`
5. ✅ No dependency on specific SQL client features

---

## Example Usage

### Original Query File
`queries/find_other_files.sql` - No labels

### Labeled Query File
`queries/find_other_files_labeled.sql` - **With Query column labels**

### Running Labeled Queries

```bash
# Run all queries with labels
mysql -u jarheads_0231 -p -D File_Deduplification < queries/find_other_files_labeled.sql

# Export specific query to CSV
mysql -u jarheads_0231 -p -D File_Deduplification \
  -e "SELECT 'Q2: By Extension' AS Query, ... FROM files ..." \
  > extensions.csv

# In MySQL Workbench:
# - Open: queries/find_other_files_labeled.sql
# - Execute: Ctrl+Shift+Enter (all queries)
# - Each result tab will show "Query" column with label
```

---

## Quick Reference: All Query Labels

```
Q1:  Basic List               - All "other" files with paths
Q2:  By Extension             - Grouped by file extension
Q3:  Extension Details        - Detailed extension analysis
Q4:  By Directory             - Files grouped by directory
Q5:  No Extension             - Files without extensions
Q6:  Summary Stats            - Overview statistics
Q7:  Top 50 by Size           - Largest unclassified files
Q8:  Potential Education      - Education-related files
Q9:  Pattern Search           - Custom pattern search
Q10: Category Comparison      - Compare to all categories
Q11: Export List              - Clean export format
```

---

## Tips for Working with Multiple Query Results

### 1. Keep Results Organized
```sql
-- Start every query with a label
SELECT 'Q1: Description' AS Query, ...
```

### 2. Use Consistent Naming
```
Q1, Q2, Q3...  ← Sequential numbering
Q-Extension    ← Category-based
Q-Dir-2024     ← Date-specific
```

### 3. Add Metadata to Results
```sql
SELECT
    'Q2: By Extension' AS Query,
    NOW() AS RunTime,
    'v1.0' AS Version,
    ...
```

### 4. Export with Labels
Labels make it easy to identify exported data:
```bash
# CSV will include Query column
mysql ... > results.csv
```

### 5. Filter Combined Results
```sql
-- Run all queries, then filter
SELECT * FROM (
  -- Query 1
  SELECT 'Q1' AS Query, ...
  UNION ALL
  -- Query 2
  SELECT 'Q2' AS Query, ...
) results
WHERE Query = 'Q2';
```

---

## Custom Label Examples

### Detailed Labels
```sql
SELECT
    'Q2: Files By Extension (Other Category Only)' AS Query,
    ...
```

### Date-Stamped Labels
```sql
SELECT
    CONCAT('Q1: Basic List - ', DATE_FORMAT(NOW(), '%Y-%m-%d')) AS Query,
    ...
```

### User-Stamped Labels
```sql
SELECT
    'Q1: Basic List - jarheads_0231' AS Query,
    ...
```

### Environment Labels
```sql
SELECT
    'Q1: Basic List [PRODUCTION]' AS Query,
    ...
```

---

## Summary

✅ **Use the labeled version:** `queries/find_other_files_labeled.sql`

✅ **First column shows:** `Q1: Basic List`, `Q2: By Extension`, etc.

✅ **Works everywhere:** Command line, MySQL Workbench, DBeaver, HeidiSQL

✅ **Easy to identify:** Just look at the "Query" column

✅ **Export-friendly:** Labels included in CSV exports

---

**Created:** 2025-11-14
**File:** `queries/SQL_TAB_LABELING_GUIDE.md`
