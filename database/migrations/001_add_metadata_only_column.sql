-- Migration: Add metadata_only column to files table
-- Purpose: Support metadata-only storage for large files without hashing
-- Date: 2025-11-13
-- Version: 0.6.0

-- Add metadata_only column to files table
ALTER TABLE files ADD COLUMN metadata_only BOOLEAN DEFAULT FALSE AFTER hash;

-- Optional: Update existing NULL hash entries to be marked as metadata_only
-- UPDATE files SET metadata_only = TRUE WHERE hash IS NULL;

-- Verify the change
-- SELECT * FROM files LIMIT 1;
