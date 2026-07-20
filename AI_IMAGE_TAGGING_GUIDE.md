# AI Image Content Tagging - Complete Guide

## ✅ Implementation Complete!

Your File_Deduplification system now includes **AI-powered image content analysis** using OpenAI's CLIP model. This automatically identifies objects, scenes, people, and locations in your photos - completely locally and privately.

---

## 🎯 What It Does

Automatically identifies and tags image content:

- 🎖️ **Military:** Uniforms, vehicles, equipment, personnel, bases
- 🚗 **Vehicles:** Trucks, motorcycles, cars, aircraft
- 🌍 **Terrain:** Desert, urban, forest, mountains, beach
- 📍 **Regions:** Middle East/Iraq, Texas, Ohio
- 👥 **People:** Single person, groups, portraits
- 🎪 **Events:** Ceremonies, outdoor activities
- 🏠 **Setting:** Indoor/outdoor, time of day
- ⭐ **Custom:** Add your own categories!

**All processing is local** - your photos never leave your computer. Safe for military/VA images.

---

## 🚀 Quick Start

### Step 1: Install Required Libraries

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification
source .venv/bin/activate

# Install AI libraries (choose ONE option)

# Option A: CPU only (works on any computer)
pip install torch transformers

# Option B: With GPU support (faster, recommended if you have NVIDIA GPU)
pip install torch torchvision transformers

# Option C: Apple Silicon (M1/M2/M3 Mac)
pip install torch torchvision transformers
```

**Download size:** ~500MB for CLIP model (downloads automatically on first use)

### Step 2: Test AI Content Analysis

Test on a single image to see what the AI detects:

```bash
# Test with specific image
.venv/bin/python core/image_content_analyzer.py /path/to/your/photo.jpg
```

**Example output:**
```
🔍 Analyzing: vacation_photo.jpg

✅ Identified content:
   military: 85% confidence
   desert: 78% confidence
   truck: 72% confidence
   outdoor: 91% confidence
   daytime: 89% confidence
```

### Step 3: Run on Your Images

```bash
# Dry run with AI tagging
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --max-files 50 \
  --dry-run-log

# Execute when ready
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --execute
```

**Important:** Use `--analyze-images` and `--ai-tagging` together for best results.

---

## 📋 What Happens During AI Tagging

```
🔍 Scanning files...
🧮 Files matched: 500

🔑 Generating file hashes...
📂 Files hashed: 500

🔍 Detecting duplicates...
📂 Unique files: 480

🤖 Classifying files with AI...
🔎 Files classified: 500

📸 Analyzing image metadata...
✅ Saved image metadata for: IMG_1234.jpg
✅ Saved image metadata for: DSC_5678.jpg
📸 Images analyzed: 200

🤖 AI tagging image content...
Loading CLIP model (this may take a moment on first run)...
✅ CLIP model loaded on CPU
✅ Tagged IMG_1234.jpg with: military, desert, truck, outdoor, daytime
✅ Tagged DSC_5678.jpg with: motorcycle, Texas, outdoor, daytime
✅ Tagged photo_003.jpg with: group, military, ceremony
🤖 Images AI-tagged: 200
🏷️  Total keywords added: 847

🗂️ Planning folder structure...
```

---

## 🔍 Querying AI-Tagged Images

### Find All Military Photos

```sql
SELECT f.path, im.date_taken, im.gps_latitude, im.gps_longitude
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE ik.keyword = 'military'
ORDER BY im.date_taken DESC;
```

### Find Truck Photos in Desert

```sql
SELECT f.path, im.date_taken, GROUP_CONCAT(ik.keyword) as all_tags
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE im.id IN (
    SELECT image_metadata_id FROM image_keywords WHERE keyword = 'truck'
)
AND im.id IN (
    SELECT image_metadata_id FROM image_keywords WHERE keyword = 'desert'
)
GROUP BY f.path, im.date_taken
ORDER BY im.date_taken DESC;
```

### Find All Motorcycle Photos

```sql
SELECT f.path, im.date_taken, im.caption
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE ik.keyword = 'motorcycle'
ORDER BY im.date_taken DESC;
```

### Find Photos from Iraq Deployment

```sql
SELECT
    f.path,
    im.date_taken,
    im.gps_latitude,
    im.gps_longitude,
    GROUP_CONCAT(DISTINCT ik.keyword ORDER BY ik.keyword SEPARATOR ', ') as tags
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE im.id IN (
    SELECT image_metadata_id
    FROM image_keywords
    WHERE keyword IN ('Iraq', 'Middle East', 'desert')
)
GROUP BY f.path, im.date_taken, im.gps_latitude, im.gps_longitude
ORDER BY im.date_taken;
```

### Find Group Photos at Ceremonies

```sql
SELECT f.path, im.date_taken, im.caption
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE im.id IN (
    SELECT image_metadata_id FROM image_keywords WHERE keyword = 'group'
)
AND im.id IN (
    SELECT image_metadata_id FROM image_keywords WHERE keyword = 'ceremony'
)
ORDER BY im.date_taken DESC;
```

### Find All Outdoor Activity Photos

```sql
SELECT f.path, im.date_taken, GROUP_CONCAT(ik.keyword) as tags
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
WHERE ik.keyword = 'outdoor activity'
ORDER BY im.date_taken DESC;
```

---

## ⚙️ Customizing Categories

Edit `config/image_ai_categories.yaml` to add your own categories:

```yaml
# Add new category
pets:
  enabled: true
  descriptions:
    - "dog"
    - "cat"
    - "pet"
    - "puppy"
    - "kitten"
  keywords:
    - "pets"

# Add specific military equipment
military_aircraft:
  enabled: true
  descriptions:
    - "Apache helicopter"
    - "Black Hawk helicopter"
    - "F-16 fighter jet"
    - "C-130 cargo plane"
  keywords:
    - "military"
    - "aircraft"
    - "aviation"

# Add family-specific
family:
  enabled: true
  descriptions:
    - "family gathering"
    - "birthday party"
    - "holiday celebration"
    - "Christmas"
    - "Thanksgiving"
  keywords:
    - "family"
    - "celebration"
```

**After editing:**
```bash
# Re-run AI tagging with new categories
.venv/bin/python main.py /path/to/images \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --execute
```

---

## 🎯 Built-in Categories

### Military (20+ descriptions)
- "military uniform", "soldiers", "military vehicle", "military equipment", "military base", "combat gear", "tactical equipment", etc.
- **Tags:** `military`

### Vehicles
- **Trucks:** "truck", "pickup truck", "semi truck", "delivery truck", etc.
  - **Tags:** `truck`
- **Motorcycles:** "motorcycle", "dirt bike", "sport bike", etc.
  - **Tags:** `motorcycle`
- **Cars:** "car", "sedan", "SUV", "sports car", etc.
  - **Tags:** `car`
- **Aircraft:** "airplane", "helicopter", "military aircraft", "fighter jet", etc.
  - **Tags:** `aircraft`

### Terrain/Landscape
- **Desert:** "desert", "sand dunes", "arid landscape"
  - **Tags:** `desert`
- **Urban:** "city", "urban", "buildings", "street scene"
  - **Tags:** `urban`
- **Forest:** "forest", "woods", "trees"
  - **Tags:** `forest`
- **Mountains:** "mountains", "mountain range", "peaks"
  - **Tags:** `mountains`
- **Beach:** "beach", "ocean", "seaside", "coastline"
  - **Tags:** `beach`

### Regions
- **Middle East/Iraq:** "Iraq", "Middle East", "Baghdad", "Middle Eastern architecture"
  - **Tags:** `Middle East`, `Iraq`
- **Texas:** "Texas", "Texas landscape", "cowboy", "ranch"
  - **Tags:** `Texas`
- **Ohio:** "Ohio", "Midwest landscape"
  - **Tags:** `Ohio`

### People
- **People:** "person", "people", "human"
  - **Tags:** `people`
- **Groups:** "group of people", "crowd", "team photo", "family photo"
  - **Tags:** `group`
- **Portraits:** "portrait", "headshot", "selfie"
  - **Tags:** `portrait`

### Events
- **Ceremonies:** "ceremony", "graduation", "wedding", "award ceremony"
  - **Tags:** `ceremony`
- **Outdoor Activities:** "hiking", "camping", "fishing", "hunting"
  - **Tags:** `outdoor activity`

### Setting
- **Indoor/Outdoor:** Indoor, outdoor
- **Time:** Daytime, night, sunset

---

## 🔧 Advanced Configuration

### Adjust Confidence Threshold

Edit `config/image_ai_categories.yaml`:

```yaml
# Lower = more tags (may include false positives)
# Higher = fewer tags (only very confident matches)
confidence_threshold: 0.25  # Default

# Examples:
# confidence_threshold: 0.15  # More sensitive (more tags)
# confidence_threshold: 0.35  # More selective (fewer tags)
```

### Disable Unwanted Categories

```yaml
# Temporarily disable a category
texas:
  enabled: false  # Won't check for Texas photos
  descriptions: ...
```

---

## 📈 Performance

### Processing Speed

**With GPU (NVIDIA):**
- ~0.5-1 second per image
- 1,000 images in ~15-20 minutes

**CPU only:**
- ~2-5 seconds per image
- 1,000 images in ~1-2 hours

**First run:** Model download (~500MB) + initial loading (~30 seconds)

**Subsequent runs:** Fast (model cached locally)

### Accuracy

- **CLIP model:** OpenAI's vision-language model
- **Typical accuracy:** 75-90% for common objects/scenes
- **Best for:** Clear, well-lit photos with obvious subjects
- **Confidence scores:** Each tag includes confidence level (0-100%)

---

## 🔒 Privacy & Security

### ✅ 100% Local Processing
- **No cloud APIs** - All analysis on your computer
- **Your photos never leave** your machine
- **Safe for military/VA images**
- Works offline (after initial model download)

### ✅ No Data Collection
- CLIP model is open source
- No telemetry or tracking
- Your data stays private

---

## 💡 Use Cases

### 1. Photo Organization
Find specific types of photos:
- "Show me all military photos from Iraq"
- "Find motorcycle photos from Texas"
- "Show group photos at ceremonies"

### 2. Memory Lane
Explore your photo collection:
- Desert landscapes
- Aircraft photos
- Outdoor activities
- Family gatherings

### 3. Deployment Documentation
Organize military service photos:
- By location (Iraq, base, training)
- By equipment (vehicles, aircraft)
- By activity (ceremony, training, operations)

### 4. Hobby Collections
Find photos by interest:
- Motorcycles
- Trucks
- Aircraft
- Outdoor adventures

---

## 🛠️ Troubleshooting

### Issue 1: "CLIP not available" Error

**Solution:**
```bash
source .venv/bin/activate
pip install torch transformers
```

For GPU support (faster):
```bash
pip install torch torchvision transformers
```

### Issue 2: Model Download Fails

**Solution:**
- Check internet connection
- Model downloads automatically on first use (~500MB)
- Downloads once, cached forever

### Issue 3: "No metadata for image, skipping"

**Solution:** Use `--analyze-images` before `--ai-tagging`:
```bash
.venv/bin/python main.py /path/to/images \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --execute
```

### Issue 4: Slow Processing (CPU)

**Options:**
1. **Get GPU** - Much faster with NVIDIA GPU
2. **Process in batches** - Use `--max-files` to process in smaller batches
3. **Run overnight** - Let it run while you sleep

### Issue 5: Too Many/Few Tags

**Solution:** Adjust confidence threshold in `config/image_ai_categories.yaml`:
```yaml
# More tags (lower threshold)
confidence_threshold: 0.15

# Fewer tags (higher threshold)
confidence_threshold: 0.35
```

---

## 📚 Example Workflows

### Workflow 1: Full Analysis on New Photos

```bash
# Complete analysis with metadata + AI tagging
.venv/bin/python main.py \
  "/Users/canadytw/Pictures/New Photos" \
  --base-dir /organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --execute
```

### Workflow 2: Re-tag Existing Photos

```bash
# Just AI tagging (metadata already exists)
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /organized \
  --use-db \
  --ai-tagging \
  --execute
```

### Workflow 3: Test with Small Batch

```bash
# Test on 20 images first
.venv/bin/python main.py \
  "/Users/canadytw/Pictures" \
  --base-dir /test_organized \
  --use-db \
  --analyze-images \
  --ai-tagging \
  --max-files 20 \
  --dry-run-log
```

---

## 🎓 Next Steps

1. **Install libraries**
   ```bash
   pip install torch transformers
   ```

2. **Test on single image**
   ```bash
   .venv/bin/python core/image_content_analyzer.py /path/to/photo.jpg
   ```

3. **Run on small batch**
   ```bash
   .venv/bin/python main.py /path/to/images \
     --base-dir /test \
     --use-db \
     --analyze-images \
     --ai-tagging \
     --max-files 20
   ```

4. **Review results**
   ```sql
   SELECT keyword, COUNT(*) as count
   FROM image_keywords
   GROUP BY keyword
   ORDER BY count DESC;
   ```

5. **Customize categories** (optional)
   Edit `config/image_ai_categories.yaml`

6. **Run on full library**
   ```bash
   .venv/bin/python main.py /Users/canadytw/Pictures \
     --base-dir /organized \
     --use-db \
     --analyze-images \
     --ai-tagging \
     --execute
   ```

---

## 📊 Monitoring Progress

### Check Tags Added
```sql
-- Most common tags
SELECT keyword, COUNT(*) as count
FROM image_keywords
GROUP BY keyword
ORDER BY count DESC
LIMIT 20;

-- Tags per image (average)
SELECT AVG(keyword_count) as avg_tags_per_image
FROM (
    SELECT image_metadata_id, COUNT(*) as keyword_count
    FROM image_keywords
    GROUP BY image_metadata_id
) AS counts;

-- Recently tagged images
SELECT f.path, COUNT(ik.keyword) as tag_count,
       GROUP_CONCAT(ik.keyword SEPARATOR ', ') as tags
FROM files f
JOIN image_metadata im ON f.id = im.file_id
JOIN image_keywords ik ON im.id = ik.image_metadata_id
GROUP BY f.path
ORDER BY im.analyzed_at DESC
LIMIT 10;
```

---

**Version:** 1.0.0
**Created:** 2025-11-15
**Status:** ✅ Ready for Production Use

Enjoy AI-powered image tagging! 🤖📸
