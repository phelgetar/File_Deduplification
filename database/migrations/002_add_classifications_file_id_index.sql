-- Migration 002: index classifications.file_id
--
-- save_classification() looks up the classifications row by file_id for
-- every file processed. Without this index that lookup is a full table
-- scan, so classification cost grows with the number of rows already
-- written — O(n^2) over a run. Observed on a 7.5M-file run: throughput
-- decayed from ~417k files/day to ~128k/day by the time the table held
-- 2.4M rows. With the index the lookup examines a single row.
--
-- Safe to run while the application is running (MySQL 8 online DDL).

CREATE INDEX idx_classifications_file_id ON classifications (file_id);
