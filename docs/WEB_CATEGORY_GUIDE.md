# Web Category Guide

## Overview

The **web** category automatically detects and preserves the complete directory structure of web projects, treating them similar to how .app packages are handled. All files under a web root directory (like `http/`, `www/`, `website/`) maintain their exact folder hierarchy.

---

## 🌐 Detected Web Directories

Files are classified as **web** if their path contains any of these directories:

| Directory Pattern | Description | Example |
|-------------------|-------------|---------|
| `/http/` | HTTP protocol directories | `/Desktop/http/mysite/` |
| `/https/` | HTTPS protocol directories | `/Desktop/https/secure-app/` |
| `/www/` | World Wide Web directories | `/Desktop/www/portfolio/` |
| `/website/` | Explicit website folders | `/Documents/website/blog/` |
| `/websites/` | Multiple website folders | `/Projects/websites/client1/` |
| `/web/` | Generic web folders | `/Desktop/web/app/` |
| `/html/` | HTML project folders | `/Desktop/html/landing-page/` |
| `/public_html/` | Public HTML (server-style) | `/Desktop/public_html/site/` |
| `/htdocs/` | Apache htdocs folders | `/Desktop/htdocs/webapp/` |
| `/web-projects/` | Web project collections | `/Desktop/web-projects/react-app/` |
| `/sites/` | Multiple sites folders | `/Desktop/sites/wordpress/` |

---

## 📁 Directory Structure Preservation

### How It Works

Unlike other file categories that scatter files by type, the web category preserves the **complete directory structure** from the web root onwards.

### Example 1: Basic Web Project

**Source:**
```
/Users/canadytw/Desktop/http/mysite/
├── index.html
├── about.html
├── css/
│   ├── style.css
│   └── responsive.css
├── js/
│   ├── main.js
│   └── utils.js
└── images/
    ├── logo.png
    └── banner.jpg
```

**Organized Output:**
```
/organized/
  Desktop/
    web/
      http/
        mysite/
          ├── index.html
          ├── about.html
          ├── css/
          │   ├── style.css
          │   └── responsive.css
          ├── js/
          │   ├── main.js
          │   └── utils.js
          └── images/
              ├── logo.png
              └── banner.jpg
```

### Example 2: Multiple Web Projects

**Source:**
```
/Users/canadytw/Desktop/websites/
├── portfolio/
│   ├── index.html
│   └── assets/
│       └── style.css
└── blog/
    ├── index.html
    └── posts/
        └── article1.html
```

**Organized Output:**
```
/organized/
  Desktop/
    web/
      websites/
        ├── portfolio/
        │   ├── index.html
        │   └── assets/
        │       └── style.css
        └── blog/
            ├── index.html
            └── posts/
                └── article1.html
```

### Example 3: With Root Structure Preservation

**Source:**
```
/Users/canadytw/Documents/Documents - 2996KD/www/company-site/
├── index.html
├── contact.html
└── assets/
    ├── logo.svg
    └── favicon.ico
```

**Organized Output:**
```
/organized/
  Documents - 2996KD/
    web/
      www/
        company-site/
          ├── index.html
          ├── contact.html
          └── assets/
              ├── logo.svg
              └── favicon.ico
```

**Notice:**
- ✅ Root structure `Documents - 2996KD` is preserved
- ✅ Category is `web` instead of year/type/owner
- ✅ Complete directory structure maintained
- ✅ No files scattered by file type

---

## 🎯 Comparison to Other Categories

### Normal File Organization

**For non-web files:**
```
Source:      /Desktop/project/images/logo.png
Destination: /organized/Desktop/2024/image/canadytw/logo.png
```

Files are organized by: **root_structure / year / type / owner / filename**

### Web File Organization

**For web files:**
```
Source:      /Desktop/http/project/images/logo.png
Destination: /organized/Desktop/web/http/project/images/logo.png
```

Files preserve: **root_structure / web / complete_original_path**

---

## 🔍 Detection Examples

### ✅ Detected as Web

```bash
# Any file under these patterns is automatically web:
/Users/canadytw/Desktop/http/site1/index.html        → web
/Users/canadytw/Documents/www/portfolio/style.css    → web
/Users/canadytw/Desktop/websites/blog/post.html      → web
/Users/canadytw/Desktop/web-projects/app/main.js     → web
/Users/canadytw/Desktop/html/landing/index.html      → web
/Users/canadytw/Desktop/public_html/site/page.php    → web
```

### ❌ Not Detected as Web

```bash
# Regular HTML files outside web directories:
/Users/canadytw/Desktop/notes.html                   → document
/Users/canadytw/Documents/report.html                → document
/Users/canadytw/Downloads/webpage.html               → document
```

---

## 🚀 Usage Examples

### Example 1: Organize Web Projects

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan Desktop with web projects
python main.py /Users/canadytw/Desktop \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --dry-run-log
```

**Output:**
```
🔍 Scanning files...
  [1/50] Processing: http/mysite/index.html
  🏷️  Path tags: http, mysite
  [2/50] Processing: http/mysite/css/style.css
  🏷️  Path tags: http, mysite, css
  ...

🤖 Classifying files with AI...
  ✓ http/mysite/index.html → web
  ✓ http/mysite/css/style.css → web
  ...

📋 Organization plan:
  Source:      /Desktop/http/mysite/index.html
  Destination: /organized/Desktop/web/http/mysite/index.html

  Source:      /Desktop/http/mysite/css/style.css
  Destination: /organized/Desktop/web/http/mysite/css/style.css
```

### Example 2: Execute Organization

```bash
# After reviewing dry-run, execute:
python main.py /Users/canadytw/Desktop \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --execute
```

### Example 3: Query Web Files in Database

```bash
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT f.path, ROUND(f.size/1048576, 2) AS size_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'web'
ORDER BY f.path;
"
```

**Example Output:**
```
+-----------------------------------------------------------+----------+
| path                                                      | size_mb  |
+-----------------------------------------------------------+----------+
| /Users/canadytw/Desktop/http/mysite/index.html           | 0.05     |
| /Users/canadytw/Desktop/http/mysite/css/style.css        | 0.02     |
| /Users/canadytw/Desktop/http/mysite/js/main.js           | 0.15     |
| /Users/canadytw/Desktop/websites/portfolio/index.html    | 0.08     |
+-----------------------------------------------------------+----------+
```

---

## 📊 Path Metadata

Web files still extract path metadata for searchability:

### Metadata Example

**File:** `/Users/canadytw/Desktop/http/mysite/blog/2024/post.html`

**Generated metadata:**
```json
{
  "original_path": "/Users/canadytw/Desktop/http/mysite/blog/2024/post.html",
  "hash": "a1b2c3d4...",
  "size": 8192,
  "type": "web",
  "owner": "canadytw",
  "year": "2024",
  "is_duplicate": false,
  "path_metadata": {
    "root_folder": "Desktop",
    "relative_path": "http/mysite/blog/2024",
    "parent_folders": ["http", "mysite", "blog", "2024"],
    "tags": ["http", "mysite", "blog", "2024"],
    "date_tags": ["2024"],
    "category_tags": ["http", "mysite", "blog"]
  }
}
```

### Searchable By

- ✅ Web root (http, www, etc.)
- ✅ Project name (mysite, portfolio, etc.)
- ✅ Subdirectories (blog, assets, etc.)
- ✅ Year tags
- ✅ Hash (for deduplication)

---

## 🔧 Technical Details

### Implementation

The web category is implemented in:

1. **`core/classifier.py`** (v0.9.0):
   ```python
   # Web project directories (preserve structure)
   elif any(web_dir in file_path_str for web_dir in [
       "/http/", "/https/", "/www/", "/website/", "/websites/", "/web/",
       "/html/", "/public_html/", "/htdocs/", "/web-projects/", "/sites/"
   ]):
       category = "web"
   ```

2. **`core/organizer.py`** (v0.2.0):
   ```python
   # Special handling for web projects - preserve directory structure
   if file_info.type == "web":
       destination = _plan_web_project(file_info, base_dir, preserve_root_structure)
       plan.append((file_info, destination))
       continue
   ```

### Structure Preservation Logic

```python
def _plan_web_project(file_info: FileInfo, base_dir: Path, preserve_root_structure: bool) -> Path:
    """
    Plan organization for web project files, preserving directory structure.

    1. Extract root structure folder if preserving (e.g., "Desktop - 2996KD")
    2. Find the web root directory (http, www, website, etc.)
    3. Extract the path from web root onwards
    4. Build destination: base_dir/root_folder/web/relative_path
    """
```

---

## 🎓 Similar to .app Package Handling

Web directories are treated like **atomic packages**, similar to how `.app`, `.pkg`, and `.dmg` files are handled:

| Feature | .app Packages | Web Directories |
|---------|---------------|-----------------|
| **Structure Preservation** | ✅ Complete | ✅ Complete |
| **Single Unit** | ✅ Yes | ✅ Yes (per web root) |
| **Metadata Extraction** | ✅ Yes | ✅ Yes |
| **File Scattering** | ❌ No | ❌ No |
| **Category** | installer | web |

---

## ✅ Best Practices

### 1. Organize Web Projects Separately

```bash
# Scan only Desktop with web projects
python main.py /Users/canadytw/Desktop \
  --base-dir /organized_web \
  --use-db \
  --execute
```

### 2. Use Metadata for Search

```bash
# Find all React projects
find /organized -name "*.meta.json" | \
  xargs grep -l "react" | \
  sed 's/.meta.json$//'
```

### 3. Backup Before Organizing

```bash
# Create backup
tar -czf web_projects_backup_$(date +%Y%m%d).tar.gz ~/Desktop/http ~/Desktop/www

# Then organize
python main.py ~/Desktop --base-dir /organized --use-db --execute
```

---

## 🔍 Query Examples

### Count Web Files by Web Root

```sql
SELECT
    CASE
        WHEN f.path LIKE '%/http/%' THEN 'http'
        WHEN f.path LIKE '%/https/%' THEN 'https'
        WHEN f.path LIKE '%/www/%' THEN 'www'
        WHEN f.path LIKE '%/website/%' THEN 'website'
        WHEN f.path LIKE '%/websites/%' THEN 'websites'
        ELSE 'other_web'
    END AS web_root,
    COUNT(*) AS file_count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'web'
GROUP BY web_root
ORDER BY file_count DESC;
```

### Find Web Files by Extension

```sql
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1048576, 2) AS total_mb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'web'
GROUP BY extension
ORDER BY count DESC
LIMIT 10;
```

**Example Output:**
```
+-----------+-------+----------+
| extension | count | total_mb |
+-----------+-------+----------+
| html      |   245 |    12.50 |
| css       |    89 |     3.20 |
| js        |   156 |    18.75 |
| png       |    67 |    25.30 |
| jpg       |    45 |    15.80 |
+-----------+-------+----------+
```

---

## 🆘 Troubleshooting

### Issue: HTML File Not Detected as Web

**Cause:** HTML file is not under a web directory pattern

**Example:**
```bash
# This is NOT detected as web:
/Users/canadytw/Desktop/notes.html

# This IS detected as web:
/Users/canadytw/Desktop/http/notes.html
```

**Solution:** Move web projects into a recognized web directory:
```bash
mkdir ~/Desktop/websites
mv ~/Desktop/mysite ~/Desktop/websites/
```

### Issue: Web Files Scattered by Type

**Cause:** Using old version before web category was added

**Solution:** Reclassify files:
```bash
python scripts/reclassify_files.py --categories other --verbose
```

### Issue: Root Structure Not Preserved

**Cause:** `--no-preserve-root` flag was used

**Solution:** Run without the flag (preservation is default):
```bash
python main.py /source --base-dir /output --use-db --execute
```

---

## 📈 Statistics

### Total Categories: 21

The system now supports **21 file categories**:

1. image
2. video
3. audio
4. document
5. spreadsheet
6. presentation
7. code
8. archive
9. data
10. font
11. installer
12. certificate
13. shortcut
14. scientific
15. education
16. financial
17. **web** ← NEW!
18. backup
19. temporary
20. system
21. other

---

## 💡 Tips

### Tip 1: Name Web Projects Clearly

```bash
# Good structure:
/Desktop/http/client-portfolio/
/Desktop/http/personal-blog/
/Desktop/websites/react-app/

# Avoid generic names:
/Desktop/http/project1/
/Desktop/http/test/
```

### Tip 2: Use Consistent Web Root

Pick one web root pattern and stick with it:
```bash
# Consistent:
/Desktop/http/site1/
/Desktop/http/site2/
/Desktop/http/site3/

# Less organized:
/Desktop/http/site1/
/Desktop/www/site2/
/Desktop/websites/site3/
```

### Tip 3: Backup Web Projects Regularly

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf ~/Backups/web_backup_$DATE.tar.gz \
  ~/Desktop/http \
  ~/Desktop/www \
  ~/Desktop/websites
```

---

## ✅ Summary

### Detection
- ✅ Automatically detects 11 web directory patterns
- ✅ Works with any file type under web directories
- ✅ Case-sensitive path matching

### Organization
- ✅ Preserves complete directory structure
- ✅ Maintains root structure (Desktop - 2996KD, etc.)
- ✅ Groups under `/web/` category folder
- ✅ No file scattering by type

### Metadata
- ✅ Extracts path tags for searchability
- ✅ Identifies web root and project names
- ✅ Detects date tags in folder names
- ✅ Writes .meta.json sidecar files

### Similar To
- ✅ .app package handling
- ✅ .pkg installer handling
- ✅ .dmg disk image handling

---

**Version:** 0.9.0
**Last Updated:** 2025-11-14
**Modules:** `core/classifier.py`, `core/organizer.py`
