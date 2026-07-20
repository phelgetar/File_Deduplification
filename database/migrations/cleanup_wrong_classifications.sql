-- ============================================================================
-- Cleanup Wrong Classifications
-- ============================================================================
-- Purpose: Remove incorrect "archive" classifications for image files
-- Created: 2025-11-19
-- ============================================================================

-- Select the database
USE file_deduplification;

-- Show current wrong classifications (for verification)
SELECT
    f.path,
    c.category AS current_category
FROM files f
JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'archive'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  )
ORDER BY f.path
LIMIT 20;

-- Count how many will be affected
SELECT
    COUNT(*) AS wrong_classifications_count
FROM files f
JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'archive'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  );

-- Delete wrong classifications for image files
DELETE c FROM classifications c
INNER JOIN files f ON c.file_id = f.id
WHERE c.category = 'archive'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  );

-- Also remove "archive" tags from file_tags if that table exists
DELETE ft FROM file_tags ft
INNER JOIN files f ON ft.file_id = f.id
WHERE ft.tag = 'archive'
  AND ft.tag_source = 'ai_tagger'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  );

-- Also remove "Archives" tag (capitalized)
DELETE ft FROM file_tags ft
INNER JOIN files f ON ft.file_id = f.id
WHERE ft.tag = 'Archives'
  AND ft.tag_source = 'ai_tagger'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  );

-- Verify cleanup
SELECT 'Remaining wrong classifications:' AS status;
SELECT
    COUNT(*) AS remaining_wrong_classifications
FROM files f
JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'archive'
  AND (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  );

-- Show example of what's left
SELECT
    f.path,
    c.category
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE (
    f.path LIKE '%.jpg' OR
    f.path LIKE '%.jpeg' OR
    f.path LIKE '%.png' OR
    f.path LIKE '%.gif' OR
    f.path LIKE '%.bmp' OR
    f.path LIKE '%.heic' OR
    f.path LIKE '%.heif' OR
    f.path LIKE '%.tiff' OR
    f.path LIKE '%.tif' OR
    f.path LIKE '%.webp'
  )
ORDER BY f.path
LIMIT 10;
