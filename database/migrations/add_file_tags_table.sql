-- ============================================================================
-- File Tags Table Migration
-- ============================================================================
-- Purpose: Add table for storing AI-generated tags for all file types
-- Created: 2025-11-19
-- ============================================================================

-- Select the database
USE File_Deduplification;

-- Create file_tags table
CREATE TABLE IF NOT EXISTS file_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id BIGINT NOT NULL,
    tag VARCHAR(255) NOT NULL,
    tag_source VARCHAR(50) DEFAULT 'ai_tagger',  -- 'ai_tagger', 'image_content', 'semantic_context', 'manual'
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_file_id (file_id),
    INDEX idx_tag (tag),
    INDEX idx_tag_source (tag_source),

    -- Foreign key to files table
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,

    -- Unique constraint to prevent duplicate tags for same file
    UNIQUE KEY unique_file_tag (file_id, tag, tag_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- View: files_with_tags - Join files with their tags
-- ============================================================================
CREATE OR REPLACE VIEW files_with_tags AS
SELECT
    f.path,
    f.size,
    f.mtime,
    f.hash,
    GROUP_CONCAT(DISTINCT ft.tag ORDER BY ft.tag SEPARATOR ', ') AS tags,
    COUNT(DISTINCT ft.tag) AS tag_count
FROM files f
LEFT JOIN file_tags ft ON f.id = ft.file_id
GROUP BY f.id, f.path, f.size, f.mtime, f.hash;

-- ============================================================================
-- View: tag_statistics - Show tag usage statistics
-- ============================================================================
CREATE OR REPLACE VIEW tag_statistics AS
SELECT
    tag,
    tag_source,
    COUNT(*) AS usage_count,
    AVG(confidence) AS avg_confidence
FROM file_tags
GROUP BY tag, tag_source
ORDER BY usage_count DESC;
