-- ============================================================================
-- SQL Queries for Finding Files Classified as "other"
-- ============================================================================
-- Database: File_Deduplification
-- Purpose: Identify files that couldn't be classified into known categories
-- ============================================================================

-- Query 1: Basic list of "other" files with paths
-- Shows all files classified as "other" with their full paths
-- ============================================================================
SELECT
    f.path,
    f.size,
    f.hash,
    c.category,
    f.scanned_at
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
ORDER BY f.size DESC;


-- Query 2: "other" files grouped by file extension
-- Shows how many files of each extension are classified as "other"
-- Helps identify patterns and missing classifications
-- ============================================================================
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS file_extension,
    COUNT(*) AS count,
    SUM(f.size) AS total_size,
    ROUND(SUM(f.size) / 1048576, 2) AS total_size_mb,
    MIN(f.path) AS example_file
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY file_extension
ORDER BY count DESC;


-- Query 3: "other" files with details (extension, size, examples)
-- More detailed view showing file extensions and representative examples
-- ============================================================================
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    COUNT(*) AS file_count,
    ROUND(AVG(f.size) / 1048576, 2) AS avg_size_mb,
    ROUND(MIN(f.size) / 1024, 2) AS min_size_kb,
    ROUND(MAX(f.size) / 1048576, 2) AS max_size_mb,
    GROUP_CONCAT(
        SUBSTRING_INDEX(f.path, '/', -1)
        SEPARATOR ', '
    ) AS example_files
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY extension
ORDER BY file_count DESC
LIMIT 50;


-- Query 4: "other" files by directory
-- Shows which directories contain the most unclassified files
-- ============================================================================
SELECT
    SUBSTRING_INDEX(f.path, '/', -2) AS parent_directory,
    COUNT(*) AS file_count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_size_mb,
    GROUP_CONCAT(
        DISTINCT SUBSTRING_INDEX(f.path, '.', -1)
        SEPARATOR ', '
    ) AS extensions_found
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY parent_directory
ORDER BY file_count DESC
LIMIT 25;


-- Query 5: Find files without extensions classified as "other"
-- These are the trickiest to classify
-- ============================================================================
SELECT
    f.path,
    f.size,
    ROUND(f.size / 1048576, 2) AS size_mb,
    f.scanned_at
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
  AND f.path NOT LIKE '%.%'
ORDER BY f.size DESC
LIMIT 50;


-- Query 6: Summary statistics for "other" files
-- High-level overview of unclassified files
-- ============================================================================
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
WHERE c.category = 'other'

UNION ALL

SELECT
    'Average file size (MB)',
    ROUND(AVG(f.size) / 1048576, 2)
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'

UNION ALL

SELECT
    'Unique extensions',
    COUNT(DISTINCT SUBSTRING_INDEX(f.path, '.', -1))
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other';


-- Query 7: Top 50 "other" files by size
-- Shows the largest unclassified files (potential for optimization)
-- ============================================================================
SELECT
    f.path,
    ROUND(f.size / 1048576, 2) AS size_mb,
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    SUBSTRING_INDEX(f.path, '/', -1) AS filename,
    f.scanned_at
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
ORDER BY f.size DESC
LIMIT 50;


-- Query 8: Find potential education files in "other"
-- Looks for files that might be education-related but weren't classified
-- ============================================================================
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
    OR LOWER(f.path) LIKE '%/econ%'
    OR LOWER(f.path) LIKE '%homework%'
    OR LOWER(f.path) LIKE '%assignment%'
    OR LOWER(f.path) LIKE '%lab%'
    OR LOWER(f.path) LIKE '%project%'
  )
ORDER BY f.path
LIMIT 100;


-- Query 9: Files classified as "other" with specific patterns
-- Customizable query - replace 'pattern' with your search term
-- ============================================================================
SELECT
    f.path,
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    ROUND(f.size / 1024, 2) AS size_kb,
    f.scanned_at
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
  AND LOWER(f.path) LIKE '%pattern%'  -- Replace 'pattern' with your search term
ORDER BY f.path
LIMIT 100;


-- Query 10: Compare "other" count to total files
-- Shows what percentage of files are unclassified
-- ============================================================================
SELECT
    'Total files' AS category,
    COUNT(*) AS count,
    100.0 AS percentage
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id

UNION ALL

SELECT
    c.category,
    COUNT(*),
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM files), 2)
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category IS NOT NULL
GROUP BY c.category
ORDER BY count DESC;


-- Query 11: Export "other" files for review
-- Simple list suitable for exporting to CSV
-- ============================================================================
SELECT
    f.path AS file_path,
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    f.size AS size_bytes,
    ROUND(f.size / 1048576, 2) AS size_mb,
    DATE_FORMAT(f.scanned_at, '%Y-%m-%d %H:%i:%s') AS scanned_date
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
ORDER BY f.path;


-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
--
-- To run these queries:
--
-- 1. Connect to MySQL:
--    mysql -u jarheads_0231 -p -D File_Deduplification
--
-- 2. Run a specific query:
--    source queries/find_other_files.sql
--
-- 3. Or copy/paste individual queries into MySQL workbench or command line
--
-- 4. Export results to CSV:
--    mysql -u jarheads_0231 -p -D File_Deduplification \
--      -e "SELECT ... your query ..." > output.csv
--
-- ============================================================================
