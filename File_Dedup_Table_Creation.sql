-- Pseudo schema (SQLAlchemy model behind the scenes)
SET @SCHEMA := 'File_Deduplification';
USE `File_Deduplification`;
CREATE TABLE file_hashes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_path TEXT,
    file_hash CHAR(64),
    file_size BIGINT,
    last_modified DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
