-- ============================================================================
-- Reset All Classifications
-- ============================================================================
-- Purpose: Delete all classifications to force fresh re-classification
-- Created: 2025-11-19
--
-- Use this if you want to completely reset and re-classify all files
-- ============================================================================

-- Select the database
USE File_Deduplification;

-- Show statistics before cleanup
SELECT 'Before cleanup:' AS status;
SELECT
    category,
    COUNT(*) AS count
FROM classifications
GROUP BY category
ORDER BY count DESC;

-- Count total classifications
SELECT
    COUNT(*) AS total_classifications
FROM classifications;

-- OPTION 1: Delete ONLY archive classifications (safer)
-- DELETE FROM classifications WHERE category = 'archive';

-- OPTION 2: Delete ALL classifications (complete reset)
TRUNCATE TABLE classifications;

-- Show statistics after cleanup
SELECT 'After cleanup:' AS status;
SELECT
    COUNT(*) AS remaining_classifications
FROM classifications;

-- Note: On next run with --use-db, all files will be re-classified correctly
SELECT 'Next run will re-classify all files correctly based on file extensions and MIME types.' AS note;
