-- ============================================================================
-- Reset All Classifications
-- ============================================================================
-- Purpose: Delete all classifications to force fresh re-classification
-- Created: 2025-11-19
-- Safety:  2026-10-03 - back up the table before the destructive step
--
-- Use this if you want to completely reset and re-classify all files.
--
-- Run as an admin/owner account (e.g. jarheads_0231), NOT the app user
-- fdedup_app, which has no DDL/TRUNCATE privilege by design.
--
-- WHY A BACKUP INSTEAD OF A TRANSACTION:
-- TRUNCATE performs an implicit COMMIT and cannot be rolled back, so a
-- START TRANSACTION wrapper would NOT protect you here. A plain DELETE of
-- ~10M rows would be transactional but extremely slow and heavy. The safe,
-- fast approach is to snapshot the table first; if the reset turns out to be
-- a mistake, restore from the snapshot (see "TO RESTORE" at the bottom).
-- ============================================================================

USE File_Deduplification;

-- --- Statistics before cleanup ---
SELECT 'Before cleanup:' AS status;
SELECT category, COUNT(*) AS count
FROM classifications
GROUP BY category
ORDER BY count DESC;

SELECT COUNT(*) AS total_classifications FROM classifications;

-- --- STEP 1: Back up the table (fast, recoverable) ---
-- Edit the date suffix if you run this more than once in a day.
DROP TABLE IF EXISTS classifications_backup_20261003;
CREATE TABLE classifications_backup_20261003 AS SELECT * FROM classifications;

-- Confirm the backup row count matches the table before wiping.
SELECT COUNT(*) AS backup_rows FROM classifications_backup_20261003;

-- --- STEP 2: Destructive reset ---
-- OPTION 1 (safer, targeted): delete only archive classifications.
--   This IS transactional; uncomment to use instead of the full reset:
--   START TRANSACTION;
--   DELETE FROM classifications WHERE category = 'archive';
--   -- review the count, then COMMIT; or ROLLBACK;
--
-- OPTION 2 (complete reset): wipe everything. Irreversible except via the
-- backup table created in STEP 1.
TRUNCATE TABLE classifications;

-- --- Statistics after cleanup ---
SELECT 'After cleanup:' AS status;
SELECT COUNT(*) AS remaining_classifications FROM classifications;

SELECT 'Next run will re-classify all files correctly based on file extensions and MIME types.' AS note;

-- ============================================================================
-- TO RESTORE (if this reset was a mistake):
--   INSERT INTO classifications SELECT * FROM classifications_backup_20261003;
--
-- ONCE YOU ARE SURE the reset was correct, drop the backup to reclaim space:
--   DROP TABLE classifications_backup_20261003;
-- ============================================================================
