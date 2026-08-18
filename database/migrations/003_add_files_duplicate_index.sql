-- ---------------------------------------------------------------------
-- 003_add_files_duplicate_index.sql
--
-- Purpose: make the whole-database duplicate totals cheap.
--
-- The Dup Trees banner aggregates over every row in `files`:
--
--     SELECT COUNT(*), SUM(is_duplicate = 1),
--            SUM(CASE WHEN is_duplicate = 1 THEN size ELSE 0 END)
--     FROM files;
--
-- `files` had indexes only on id (PK) and path (UNIQUE), so this had to
-- scan the clustered index — which carries the full 767-char path on
-- every row. At ~7.7M rows that took minutes.
--
-- (is_duplicate, size) is a covering index for the query: both columns
-- are in the index, so MySQL can satisfy the aggregate with an
-- index-only scan over a structure a fraction of the table's size.
--
-- MySQL 8 performs this as an online DDL operation, so it is safe to
-- apply while a scan is running. Expect it to take a few minutes on a
-- large table and to add roughly 100-200 MB.
-- ---------------------------------------------------------------------

ALTER TABLE files
    ADD INDEX idx_files_is_duplicate_size (is_duplicate, size);
