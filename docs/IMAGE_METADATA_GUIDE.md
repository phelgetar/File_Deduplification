# Image Metadata Extraction Guide

## Overview

The image analyzer can extract **comprehensive metadata** from photos including camera settings, GPS location, copyright information, and much more. This guide shows you everything that's available.

---

## 📊 Available Metadata Categories

### 1. File Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `file_path` | Path | Full path to image file | `/Photos/vacation.jpg` |
| `file_size` | int | Size in bytes | 4523891 (4.5 MB) |
| `file_hash` | string | SHA256 hash (for deduplication) | `a3f2c9...` |
| `file_created` | datetime | File creation timestamp | `2024-11-14 10:30:00` |
| `file_modified` | datetime | File modification timestamp | `2024-11-14 15:45:00` |

### 2. Image Properties
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `width` | int | Image width in pixels | 4000 |
| `height` | int | Image height in pixels | 3000 |
| `format` | string | Image format | JPEG, PNG, HEIC |
| `mode` | string | Color mode | RGB, RGBA, L (grayscale) |
| `color_space` | string | Color space | sRGB, Adobe RGB |
| `dpi` | tuple | Dots per inch | (300, 300) |
| `bit_depth` | int | Bits per pixel | 24 (8 bits × 3 channels) |
| `has_transparency` | bool | Has alpha channel | true/false |

### 3. Camera Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `camera_make` | string | Camera manufacturer | Canon, Nikon, Apple |
| `camera_model` | string | Camera model | EOS 5D Mark IV, iPhone 13 Pro |
| `lens_make` | string | Lens manufacturer | Canon, Sigma |
| `lens_model` | string | Lens model | EF 24-70mm f/2.8L II USM |

### 4. Camera Settings (EXIF)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `date_taken` | datetime | When photo was taken | `2024-07-15 14:32:18` |
| `date_digitized` | datetime | When photo was digitized | `2024-07-15 14:32:18` |
| `iso_speed` | int | ISO sensitivity | 100, 400, 1600 |
| `exposure_time` | string | Shutter speed | 1/250, 1/60, 2.5 |
| `f_number` | float | Aperture (f-stop) | 2.8, 5.6, 11.0 |
| `focal_length` | float | Focal length in mm | 50.0, 85.0, 200.0 |
| `flash` | string | Flash mode | On, Off, Auto |
| `white_balance` | string | White balance | Auto, Daylight, Cloudy |
| `metering_mode` | string | Light metering | Spot, Center-weighted, Matrix |
| `exposure_program` | string | Exposure mode | Manual, Aperture Priority, Auto |
| `exposure_bias` | float | Exposure compensation | -1.0, +0.5, +2.0 |
| `orientation` | int | Image orientation | 1 (normal), 6 (rotated 90°) |

### 5. GPS Location Data
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `gps_latitude` | float | Latitude in decimal degrees | 37.7749 (San Francisco) |
| `gps_longitude` | float | Longitude in decimal degrees | -122.4194 |
| `gps_altitude` | float | Altitude in meters | 15.5 |
| `gps_timestamp` | datetime | GPS timestamp | `2024-07-15 14:32:18` |
| `gps_location_name` | string | Location name (if available) | San Francisco, CA |

**GPS Coordinates Enable:**
- 🗺️ Mapping photos on a map
- 📍 Grouping by location
- 🌍 Travel timeline creation
- 🏠 Organizing by place

### 6. Copyright & Creator (IPTC)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `copyright` | string | Copyright notice | © 2024 Tim Canady |
| `creator` | string | Creator/Photographer | Tim Canady |
| `credit` | string | Credit line | Photo by Tim Canady |
| `caption` | text | Image caption/description | Family vacation at beach |
| `title` | string | Image title | Sunset Over Ocean |
| `keywords` | list | Keywords/tags | [vacation, beach, sunset] |

### 7. Software & Processing
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `software` | string | Editing software used | Adobe Photoshop CC 2024 |
| `compression` | string | Compression type | JPEG, PNG |
| `quality` | int | JPEG quality (0-100) | 95 |
| `rating` | int | Star rating (0-5) | 5 ⭐⭐⭐⭐⭐ |

### 8. Raw EXIF Data
| Field | Type | Description |
|-------|------|-------------|
| `raw_exif` | dict | ALL EXIF tags as key-value pairs |

Includes hundreds of possible fields like:
- Color temperature
- Scene capture type
- Subject distance
- Digital zoom ratio
- And many more...

---

## 🗄️ Database Schema

### Main Table: `image_metadata`
Stores all primary metadata for each image.

**Key Features:**
- ✅ Linked to `files` table via `file_id` (foreign key)
- ✅ Automatically deleted when file is deleted (CASCADE)
- ✅ Indexed for fast queries (date, camera, GPS, creator, rating)
- ✅ Timestamps for tracking when analysis was performed

### Supporting Tables:

**`image_keywords`** - Many-to-many relationship for tags
- Allows multiple keywords per image
- Prevents duplicate keywords
- Fast keyword searching

**`image_exif_raw`** - Complete EXIF data storage
- Stores all EXIF tags as key-value pairs
- Useful for advanced analysis
- Future-proof for new EXIF tags

**`image_analysis_errors`** - Error tracking
- Records any errors during analysis
- Helps identify problematic images

### Useful Views (Pre-built Queries):

**`images_with_gps`** - All images with location data
```sql
SELECT * FROM images_with_gps;
```

**`images_by_camera`** - Statistics by camera model
```sql
SELECT * FROM images_by_camera;
```

**`images_by_date`** - Images grouped by date
```sql
SELECT * FROM images_by_date WHERE photo_date = '2024-07-15';
```

**`images_with_ratings`** - All rated images
```sql
SELECT * FROM images_with_ratings WHERE rating >= 4;
```

---

## 🚀 How to Use

### Step 1: Install Required Libraries

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification
source .venv/bin/activate
pip install Pillow  # For image processing
```

### Step 2: Apply Database Migration

```bash
mysql -u jarheads_0231 -p < database/migrations/add_image_metadata_tables.sql
```

**Verify:**
```bash
mysql -u jarheads_0231 -p -D File_Deduplification -e "SHOW TABLES LIKE 'image_%';"
```

Should show:
```
+-----------------------------------+
| Tables_in_File_Deduplification (image_%) |
+-----------------------------------+
| image_analysis_errors             |
| image_exif_raw                    |
| image_keywords                    |
| image_metadata                    |
+-----------------------------------+
```

### Step 3: Test Metadata Extraction

```bash
# Test with sample images
.venv/bin/python test_image_metadata.py

# Or test specific image
.venv/bin/python test_image_metadata.py /path/to/your/photo.jpg
```

**Example Output:**
```
================================================================================
IMAGE METADATA ANALYSIS: vacation.jpg
================================================================================

📁 FILE INFORMATION
--------------------------------------------------------------------------------
  Path: /Photos/vacation.jpg
  Size: 4,523,891 bytes (4.31 MB)
  Hash (SHA256): a3f2c91d8e7b...
  Created: 2024-07-15 10:30:00
  Modified: 2024-07-15 15:45:00

🖼️  IMAGE PROPERTIES
--------------------------------------------------------------------------------
  Dimensions: 4000 x 3000 pixels
  Megapixels: 12.0 MP
  Format: JPEG
  Color Mode: RGB
  Bit Depth: 24 bits
  Has Transparency: No

📷 CAMERA INFORMATION
--------------------------------------------------------------------------------
  Camera Make: Canon
  Camera Model: EOS 5D Mark IV
  Lens Model: EF 24-70mm f/2.8L II USM

⚙️  CAMERA SETTINGS
--------------------------------------------------------------------------------
  Date Taken: 2024-07-15 14:32:18
  ISO Speed: 400
  Exposure Time: 1/250 sec
  F-Number (Aperture): f/5.6
  Focal Length: 50.0 mm
  Flash: Off
  White Balance: Auto

📍 GPS LOCATION
--------------------------------------------------------------------------------
  Latitude: 37.774929°
  Longitude: -122.419418°
  Google Maps: https://www.google.com/maps?q=37.774929,-122.419418
  Altitude: 15.5 meters

©️  COPYRIGHT & CREATOR
--------------------------------------------------------------------------------
  Creator/Artist: Tim Canady
  Caption: Family vacation at Golden Gate Bridge
  Keywords: vacation, san francisco, family

⭐ SOFTWARE & QUALITY
--------------------------------------------------------------------------------
  Software: Adobe Lightroom Classic 13.0
  Quality: 95/100
  Rating: ⭐⭐⭐⭐⭐ (5/5)
```

### Step 4: Run on Your Images

```bash
# Dry run with image analysis
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --dry-run-log

# Execute (when ready)
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --execute
```

---

## 📈 Use Cases

### 1. Find All Photos from a Trip

```sql
-- Photos taken in July 2024
SELECT
    f.path,
    im.date_taken,
    im.gps_latitude,
    im.gps_longitude,
    im.caption
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.date_taken BETWEEN '2024-07-01' AND '2024-07-31'
ORDER BY im.date_taken;
```

### 2. Find All Photos at a Specific Location

```sql
-- Photos taken in San Francisco area
SELECT
    f.path,
    im.date_taken,
    im.camera_model
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.gps_latitude BETWEEN 37.7 AND 37.8
  AND im.gps_longitude BETWEEN -122.5 AND -122.4;
```

### 3. Find Your Best Photos

```sql
-- All 5-star rated photos
SELECT * FROM images_with_ratings WHERE rating = 5;
```

### 4. Camera Equipment Analysis

```sql
-- Which camera do you use most?
SELECT * FROM images_by_camera ORDER BY image_count DESC;
```

### 5. Find Photos by Keyword

```sql
-- All photos tagged with "vacation"
SELECT
    f.path,
    im.date_taken,
    GROUP_CONCAT(ik.keyword SEPARATOR ', ') as all_keywords
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE ik.keyword = 'vacation'
GROUP BY f.path;
```

### 6. Photos Without GPS Data

```sql
-- Find photos that don't have location data
SELECT
    f.path,
    im.date_taken,
    im.camera_model
FROM files f
JOIN image_metadata im ON f.id = im.file_id
WHERE im.gps_latitude IS NULL
ORDER BY im.date_taken DESC;
```

---

## 💡 What You Can Do With This Data

### Photo Organization
- 📅 Group by date/year/month
- 📍 Group by location (city, country)
- 📷 Group by camera/lens
- ⭐ Separate best photos (by rating)
- 🏷️ Organize by keywords

### Travel Timelines
- 🗺️ Create map of all photo locations
- 📊 See where you've been
- 🌍 Track travel history
- 🛫 Vacation albums auto-generated

### Photography Analysis
- 📸 Which camera settings you use most
- 🎯 Focal length usage patterns
- ⚡ Flash usage statistics
- 📊 ISO range analysis

### Smart Albums
- 🎨 Photos by software (edited vs. straight from camera)
- 📱 Photos by device (iPhone vs. DSLR)
- 🌅 Photos by time of day
- 🌤️ Photos by weather (if available)

---

## ⚙️ Configuration Options

You can choose which metadata to extract and store:

**Option 1: Extract Everything** (Recommended)
- Stores all available metadata
- Most flexible for future queries
- Slightly larger database

**Option 2: Selective Extraction**
- Only extract essential fields
- Smaller database
- Faster processing

**Option 3: Minimal Extraction**
- Only dates, camera, GPS
- Fastest processing
- Limited query capabilities

---

## 🔒 Privacy Considerations

**GPS Data:**
- ⚠️ Contains exact location where photos were taken
- Consider removing GPS before sharing photos publicly
- Useful for personal organization

**Copyright/Creator:**
- ℹ️ Helps track ownership
- Important for professional photographers
- Can be removed if desired

**Camera Info:**
- ℹ️ Useful for equipment tracking
- Generally safe to share
- No privacy concerns

---

## 📋 Next Steps

1. **Test the extraction:**
   ```bash
   .venv/bin/python test_image_metadata.py
   ```

2. **Review the output** and decide which metadata you want

3. **Apply database migration:**
   ```bash
   mysql -u jarheads_0231 -p < database/migrations/add_image_metadata_tables.sql
   ```

4. **Enable in main workflow** (I'll create the integration)

5. **Run on your photo library!**

---

## ❓ Questions to Consider

1. **Do you want GPS data extracted?**
   - ✅ Yes - Enables location-based organization
   - ❌ No - Privacy concerns

2. **Do you want to store raw EXIF data?**
   - ✅ Yes - Complete data for future analysis
   - ❌ No - Only store essential fields

3. **Should we extract from all images or only specific formats?**
   - All formats (.jpg, .png, .heic, .raw, etc.)
   - Only JPEG (.jpg, .jpeg)
   - Only photos with EXIF (skip screenshots)

4. **Do you want to use this for:**
   - Deduplication (finding identical photos)
   - Organization (grouping by date/location)
   - Analysis (camera usage statistics)
   - Smart albums (auto-grouping)
   - All of the above

---

**Version:** 1.0.0
**Created:** 2025-11-14
**Status:** ✅ Ready for Testing

Let me know which metadata fields you want to use!
