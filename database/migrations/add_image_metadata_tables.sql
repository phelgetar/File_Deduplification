-- ============================================================================
-- Image Metadata Tables Migration
-- ============================================================================
-- Database: File_Deduplification
-- Purpose: Add comprehensive image metadata storage
-- Version: 1.0.0
-- Created: 2025-11-14
-- ============================================================================

USE File_Deduplification;

-- ============================================================================
-- Table: image_metadata
-- Stores comprehensive metadata for image files
-- ============================================================================
CREATE TABLE IF NOT EXISTS image_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id BIGINT NOT NULL,

    -- Basic Image Properties
    width INT,
    height INT,
    format VARCHAR(20),
    mode VARCHAR(20),  -- RGB, RGBA, L, etc.
    color_space VARCHAR(50),
    dpi_x FLOAT,
    dpi_y FLOAT,
    bit_depth INT,
    has_transparency BOOLEAN DEFAULT FALSE,

    -- Camera Information
    camera_make VARCHAR(255),
    camera_model VARCHAR(255),
    lens_make VARCHAR(255),
    lens_model VARCHAR(255),

    -- Camera Settings
    date_taken DATETIME,
    date_digitized DATETIME,
    date_modified DATETIME,
    iso_speed INT,
    exposure_time VARCHAR(50),
    f_number FLOAT,
    focal_length FLOAT,
    flash VARCHAR(100),
    white_balance VARCHAR(100),
    metering_mode VARCHAR(100),
    exposure_program VARCHAR(100),
    exposure_bias FLOAT,

    -- GPS Location Data
    gps_latitude DECIMAL(10, 8),  -- -90 to 90
    gps_longitude DECIMAL(11, 8), -- -180 to 180
    gps_altitude FLOAT,
    gps_timestamp DATETIME,
    gps_location_name VARCHAR(255),

    -- Copyright/Creator Information
    copyright VARCHAR(500),
    creator VARCHAR(255),
    credit VARCHAR(255),
    caption TEXT,
    title VARCHAR(500),

    -- Software/Processing
    software VARCHAR(255),
    orientation INT,
    compression VARCHAR(100),
    quality INT,  -- 0-100 for JPEG

    -- Rating/Organization
    rating INT,  -- 0-5 stars

    -- File Timestamps
    file_created DATETIME,
    file_modified DATETIME,

    -- Metadata
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    analysis_version VARCHAR(20) DEFAULT '1.0.0',
    has_errors BOOLEAN DEFAULT FALSE,

    -- Indexes
    INDEX idx_file_id (file_id),
    INDEX idx_date_taken (date_taken),
    INDEX idx_camera_model (camera_model),
    INDEX idx_gps_location (gps_latitude, gps_longitude),
    INDEX idx_creator (creator),
    INDEX idx_rating (rating),

    -- Foreign key
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Table: image_keywords
-- Stores keywords/tags for images (many-to-many relationship)
-- ============================================================================
CREATE TABLE IF NOT EXISTS image_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_metadata_id INT NOT NULL,
    keyword VARCHAR(255) NOT NULL,

    -- Indexes
    INDEX idx_image_metadata_id (image_metadata_id),
    INDEX idx_keyword (keyword),

    -- Foreign key
    FOREIGN KEY (image_metadata_id) REFERENCES image_metadata(id) ON DELETE CASCADE,

    -- Unique constraint to prevent duplicate keywords
    UNIQUE KEY unique_image_keyword (image_metadata_id, keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Table: image_exif_raw
-- Stores raw EXIF data as JSON for advanced analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS image_exif_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_metadata_id INT NOT NULL,
    exif_tag VARCHAR(255) NOT NULL,
    exif_value TEXT,

    -- Indexes
    INDEX idx_image_metadata_id (image_metadata_id),
    INDEX idx_exif_tag (exif_tag),

    -- Foreign key
    FOREIGN KEY (image_metadata_id) REFERENCES image_metadata(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Table: image_analysis_errors
-- Stores errors that occurred during image analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS image_analysis_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id BIGINT NOT NULL,
    error_message TEXT NOT NULL,
    error_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_file_id (file_id),
    INDEX idx_timestamp (error_timestamp),

    -- Foreign key
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Views: Useful queries for image metadata
-- ============================================================================

-- View: images_with_gps
-- All images that have GPS location data
CREATE OR REPLACE VIEW images_with_gps AS
SELECT
    f.path,
    im.camera_make,
    im.camera_model,
    im.date_taken,
    im.gps_latitude,
    im.gps_longitude,
    im.gps_altitude,
    im.gps_location_name
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.gps_latitude IS NOT NULL
  AND im.gps_longitude IS NOT NULL;


-- View: images_by_camera
-- Summary of images by camera model
CREATE OR REPLACE VIEW images_by_camera AS
SELECT
    im.camera_make,
    im.camera_model,
    COUNT(*) as image_count,
    MIN(im.date_taken) as first_photo,
    MAX(im.date_taken) as last_photo
FROM image_metadata im
WHERE im.camera_make IS NOT NULL
GROUP BY im.camera_make, im.camera_model
ORDER BY image_count DESC;


-- View: images_by_date
-- Images grouped by date taken
CREATE OR REPLACE VIEW images_by_date AS
SELECT
    DATE(im.date_taken) as photo_date,
    COUNT(*) as image_count,
    MIN(f.path) as example_path
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.date_taken IS NOT NULL
GROUP BY DATE(im.date_taken)
ORDER BY photo_date DESC;


-- View: images_with_ratings
-- All rated images
CREATE OR REPLACE VIEW images_with_ratings AS
SELECT
    f.path,
    im.rating,
    im.date_taken,
    im.camera_model,
    im.caption
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.rating IS NOT NULL AND im.rating > 0
ORDER BY im.rating DESC, im.date_taken DESC;


-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Find all photos taken in a specific year
-- SELECT * FROM images_by_date WHERE photo_date BETWEEN '2020-01-01' AND '2020-12-31';

-- Find all photos from a specific camera
-- SELECT f.path, im.date_taken FROM files f
-- JOIN image_metadata im ON f.id = im.file_id
-- WHERE im.camera_model LIKE '%Canon%';

-- Find all photos with GPS data in a specific area (San Francisco example)
-- SELECT f.path, im.gps_latitude, im.gps_longitude FROM files f
-- JOIN image_metadata im ON f.id = im.file_id
-- WHERE im.gps_latitude BETWEEN 37.7 AND 37.8
--   AND im.gps_longitude BETWEEN -122.5 AND -122.4;

-- Find all photos by a specific creator/photographer
-- SELECT f.path, im.date_taken, im.caption FROM files f
-- JOIN image_metadata im ON f.id = im.file_id
-- WHERE im.creator = 'Your Name';

-- Find all 5-star rated photos
-- SELECT * FROM images_with_ratings WHERE rating = 5;

-- Find all images with keywords
-- SELECT f.path, GROUP_CONCAT(ik.keyword SEPARATOR ', ') as keywords
-- FROM files f
-- JOIN image_metadata im ON f.id = im.file_id
-- JOIN image_keywords ik ON im.id = ik.image_metadata_id
-- GROUP BY f.path;


-- ============================================================================
-- Usage Instructions
-- ============================================================================
--
-- To apply this migration:
--
-- 1. Connect to MySQL:
--    mysql -u jarheads_0231 -p
--
-- 2. Run this script:
--    source database/migrations/add_image_metadata_tables.sql
--
-- 3. Verify tables were created:
--    USE File_Deduplification;
--    SHOW TABLES LIKE 'image_%';
--
-- 4. Check table structure:
--    DESCRIBE image_metadata;
--
-- ============================================================================
