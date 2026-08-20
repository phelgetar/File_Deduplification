-- ---------------------------------------------------------------------
-- 004_add_files_hash_index.sql
--
-- Purpose: make duplicate lookups possible at all.
--
-- `files` was indexed only on id (PK) and path (UNIQUE), so every query
-- of the form
--
--     SELECT path, size FROM files WHERE hash = ?
--
-- scanned the clustered index — ~7.7M rows carrying a 767-char path
-- each. EXPLAIN reported key = NULL. The duplicate review screen does
-- one such lookup per resolved group, so at 148 resolved groups the
-- confirmation endpoint did 148 full table scans and never returned.
--
-- Batching the query to a single IN (...) helped, but grouping and
-- filtering by hash is the core access pattern of the whole duplicate
-- feature — including detect_duplicates() on every --use-db run — so
-- the column needs an index regardless.
--
-- MySQL 8 performs this as an online DDL operation, so it is safe to
-- apply while a run is in progress. On a table this size expect a few
-- minutes and roughly 500 MB, since the hash is a 64-character digest.
-- ---------------------------------------------------------------------

-- ALGORITHM=INPLACE, LOCK=NONE are explicit on purpose: they make MySQL
-- refuse the statement if it cannot build the index without blocking
-- writes, rather than quietly locking the table for the duration.
ALTER TABLE files
    ADD INDEX idx_files_hash (hash),
    ALGORITHM=INPLACE, LOCK=NONE;
