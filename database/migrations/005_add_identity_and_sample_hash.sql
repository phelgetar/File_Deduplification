-- ---------------------------------------------------------------------
-- 005_add_identity_and_sample_hash.sql
--
-- Purpose: stop counting the same bytes twice, and stop reading them
--          in full before we know we have to.
--
-- Three new facts per file, all cheap to collect and none of them
-- available today:
--
--   link_target   A symlink is not a file. The scanner used to hand
--                 them to the hasher, which followed them: 488 sandbox
--                 container links to one Pictures library were read as
--                 488 separate 44 GB "files", 21.47 TB of the 25.77 TB
--                 that scan read. Links are now recorded, never
--                 followed, and carry hash = 'SYMLINK'.
--
--   dev, inode    Two paths sharing a device and an inode are ONE file
--                 on disk, by hardlink or by APFS clone. They hash
--                 identically because they are the same bytes, and
--                 "reclaimable" counted space that deleting cannot
--                 return. Identity is now checked before content.
--
--   sample_hash   SHA-256 of the first 64 KB, the last 64 KB and the
--                 size. Two files that differ in either end cannot be
--                 identical, so the full read is only needed for files
--                 that collide here. Kept in its own column so the
--                 full-hash cache stays complete and resume keeps
--                 working.
--
-- All four are nullable with no default, so existing rows are untouched
-- and a re-scan fills them in. INSTANT is requested first because
-- adding a nullable column at the end of the row is a metadata-only
-- change in MySQL 8; INPLACE/LOCK=NONE is the documented fallback.
-- ---------------------------------------------------------------------

ALTER TABLE files
    ADD COLUMN link_target VARCHAR(767) NULL,
    ADD COLUMN dev BIGINT NULL,
    ADD COLUMN inode BIGINT NULL,
    ADD COLUMN sample_hash VARCHAR(128) NULL,
    ALGORITHM=INSTANT;

-- Identity lookups: "have I already hashed these exact bytes under a
-- different name?" is asked once per file, so it needs an index.
ALTER TABLE files
    ADD INDEX idx_files_identity (dev, inode),
    ALGORITHM=INPLACE, LOCK=NONE;

-- Sample-hash grouping is the first pass of two-tier hashing, so it is
-- the same access pattern as idx_files_hash and needs the same support.
ALTER TABLE files
    ADD INDEX idx_files_sample_hash (sample_hash),
    ALGORITHM=INPLACE, LOCK=NONE;
