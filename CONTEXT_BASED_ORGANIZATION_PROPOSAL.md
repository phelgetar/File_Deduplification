# Context-Based Organization Architecture Proposal

## Executive Summary

**Problem:** The current file type classification system breaks apart meaningful structures (medical records, projects, applications) just to group by file extension.

**Solution:** Organize files based on **semantic context** detected from folder paths, not just file types.

---

## 🎯 Core Principle

> **"Context matters more than file type."**

A `.dcm` file in a `VA_IMG_CANADY_MRI` folder is a **medical record**, not just "other".
A `.py` file in a `Work-Info/scripts` folder is a **work tool**, not just "code".
A `.jpg` file in a `personal/Disability/VA` folder is a **VA document**, not just "image".

---

## 📋 Detection Priority (Top to Bottom)

### Priority 1: Semantic Path Contexts (HIGHEST)
Detect meaningful folder paths that indicate complete structures:

```python
SEMANTIC_CONTEXTS = {
    'Personal/Disability': {
        'patterns': ['/personal/', '/disability/', '/va_', '/va/', '/medical/'],
        'destination': 'Personal/Disability/VA',
        'preserve_structure': True,
        'reason': 'Medical/VA records must stay intact'
    },
    'Work': {
        'patterns': ['/work-info/', '/work/', '/afcam/', '/scc/', '/fbi/'],
        'destination': 'Work',
        'preserve_structure': True,
        'reason': 'Work-related files grouped together'
    },
    'Education': {
        'patterns': ['/education/', '/coursera/', '/mit-sloan/', '/wright-state/', '/afit/'],
        'destination': 'Education',
        'preserve_structure': True,
        'reason': 'Educational materials grouped by institution'
    },
    'Personal/Family': {
        'patterns': ['/dad/', '/family/', '/personal/'],
        'destination': 'Personal/Family',
        'preserve_structure': True,
        'reason': 'Family-related files'
    }
}
```

### Priority 2: Project/Application Detection
Recognize complete structures that must stay intact:

```python
PROJECT_INDICATORS = {
    'Medical/DICOM': {
        'indicators': ['dicom/', 'series_', '.dcm'],
        'preserve': 'entire_parent_tree',
        'reason': 'Medical imaging series must remain together'
    },
    'Code Projects': {
        'indicators': ['.git/', 'package.json', 'requirements.txt', '.xcodeproj'],
        'preserve': 'project_root',
        'reason': 'Code projects need dependencies'
    },
    'Applications': {
        'indicators': ['.app/', 'packettracer/', 'fusion 360/'],
        'preserve': 'entire_structure',
        'reason': 'Applications need complete structure'
    },
    'Web Projects': {
        'indicators': ['/http/', '/www/', 'index.html', 'wp-content/'],
        'preserve': 'entire_structure',
        'reason': 'Web projects need complete structure'
    }
}
```

### Priority 3: Metadata Extraction from Paths
Extract semantic tags from folder names:

```python
# Example: /personal/Disability/VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020/DICOM/

EXTRACTED_METADATA = {
    'context': 'Disability',
    'subcategory': 'VA',
    'type': 'MRI',
    'body_part': 'CERVICAL_SPINE',
    'contrast': 'W_O_CONTRAST',
    'date': '15SEP2020',
    'format': 'DICOM',
    'owner': 'CANADY'
}
```

### Priority 4: File Type Classification (LOWEST)
Only for loose files that don't belong to a context.

---

## 🔧 Implementation Changes

### 1. New Module: `core/context_detector.py`

```python
class ContextDetector:
    """
    Detects semantic context from file paths.
    """

    def detect_context(self, file_path: Path) -> ContextInfo:
        """
        Analyze path for semantic context.

        Priority:
        1. Semantic path contexts (Personal/Disability, Work, Education)
        2. Project/application indicators (DICOM, .git, .app)
        3. Metadata extraction (dates, names, types from folder names)
        4. File type classification (fallback)
        """

    def should_preserve_structure(self, file_path: Path) -> bool:
        """
        Determine if file is part of a structure that must stay intact.
        """

    def extract_metadata_from_path(self, file_path: Path) -> dict:
        """
        Extract semantic information from folder names.
        Example: VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020
        Returns: {type: 'MRI', body_part: 'CERVICAL_SPINE', date: '2020-09-15', ...}
        """
```

### 2. Modified: `core/organizer.py`

```python
def plan_organization_v2(files, base_dir):
    """
    NEW: Context-based organization.

    For each file:
    1. Detect semantic context from path
    2. If context found → preserve structure under context folder
    3. If project/app detected → preserve entire structure
    4. Extract metadata → add to file tags
    5. Otherwise → classify by file type (old behavior)
    """
```

### 3. New Configuration: `config/semantic_paths.yaml`

```yaml
# Define semantic path patterns and their destinations
semantic_contexts:
  - name: "Personal - Disability/VA"
    patterns:
      - "/personal/"
      - "/disability/"
      - "/va_"
      - "/medical/"
    destination: "Personal/Disability/VA"
    preserve_structure: true
    priority: 100

  - name: "Work - General"
    patterns:
      - "/work-info/"
      - "/work/"
    destination: "Work"
    preserve_structure: true
    priority: 90

  - name: "Education"
    patterns:
      - "/education/"
      - "/coursera/"
      - "/mit-sloan/"
    destination: "Education"
    preserve_structure: true
    priority: 90
```

---

## 📊 Example Scenarios

### Scenario 1: Medical Records (Your MRI Example)

**Source Path:**
```
/Documents - 42739/Google Drive/personal/Disability/
  VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020/
    DICOM/
      SERIES_4/
        95934524.dcm
        95934525.dcm
        95934526.dcm
```

**Detection:**
1. ✅ Detect `/personal/` → Personal context
2. ✅ Detect `/Disability/` → Disability subcategory
3. ✅ Detect `/VA_IMG_` → VA medical imaging
4. ✅ Detect `DICOM/` folder → Medical imaging project
5. ✅ Extract metadata: `{type: 'MRI', body_part: 'CERVICAL_SPINE', date: '2020-09-15'}`
6. ✅ Decision: Preserve entire structure under Personal/Disability/VA/

**Organized Path:**
```
/organized/Personal/Disability/VA/
  VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020/
    DICOM/
      SERIES_4/
        95934524.dcm
        95934525.dcm
        95934526.dcm
```

**Metadata Tags:** `personal`, `disability`, `va`, `mri`, `cervical_spine`, `2020-09-15`

---

### Scenario 2: Work Scripts

**Source Path:**
```
/Documents/Work-Info/scripts/
  backup_database.py
  deploy_app.sh
  monitor_logs.py
```

**Detection:**
1. ✅ Detect `/Work-Info/` → Work context
2. ✅ Detect `/scripts/` → Code directory
3. ✅ Decision: Preserve structure under Work/scripts/

**Organized Path:**
```
/organized/Work/scripts/
  backup_database.py
  deploy_app.sh
  monitor_logs.py
```

---

### Scenario 3: Education Files

**Source Path:**
```
/Documents/Education/CEG3310/Labs/Lab1/report.pdf
/Documents/Education/CEG3310/Labs/Lab2/code.cpp
```

**Detection:**
1. ✅ Detect `/Education/` → Education context
2. ✅ Detect `CEG3310` → Course identifier
3. ✅ Extract metadata: `{course: 'CEG3310', type: 'Labs'}`
4. ✅ Decision: Preserve structure under Education/

**Organized Path:**
```
/organized/Education/CEG3310/Labs/Lab1/report.pdf
/organized/Education/CEG3310/Labs/Lab2/code.cpp
```

---

### Scenario 4: Loose Files (No Context)

**Source Path:**
```
/Documents/random_report.pdf
/Desktop/vacation_photo.jpg
```

**Detection:**
1. ❌ No semantic context found
2. ❌ No project indicators
3. ✅ Fallback: Use file type classification

**Organized Path:**
```
/organized/Docs/Word/random_report.pdf
/organized/Media/Images/vacation_photo.jpg
```

---

## 🤖 Future Enhancement: AI-Based Image Clustering

### Phase 1: EXIF Metadata Clustering
```python
def cluster_images_by_metadata(images):
    """
    Group images by:
    - Date taken (time period detection)
    - Location (GPS coordinates)
    - Camera/device
    - Image dimensions/quality
    """
```

### Phase 2: Content-Based Clustering (Optional)
```python
def cluster_images_by_content(images):
    """
    Using AI models to detect:
    - People (face recognition)
    - Scenes (indoor/outdoor, beach/mountain, etc.)
    - Events (birthday, vacation, sports, etc.)
    - Objects (cars, animals, buildings, etc.)

    Libraries: face_recognition, CLIP, ResNet, YOLO
    """
```

**Example Output:**
```
/organized/Media/Images/
├── 2020_Family_Vacation/          ← Grouped by date + location
│   └── Beach_Photos/               ← Grouped by scene detection
├── 2021_Christmas/                 ← Grouped by date + event
└── Wolf_Videos/                    ← Grouped by subject (already done!)
```

---

## 📈 Benefits of New Architecture

### ✅ Structure Preservation
- Medical records stay intact (DICOM series)
- Work projects maintain organization
- Education files grouped by course
- Applications preserve dependencies

### ✅ Semantic Organization
- Files organized by PURPOSE, not just file type
- Easy to find: "Where are my VA records?" → `Personal/Disability/VA/`
- Context from folder names preserved as metadata

### ✅ Flexible
- Add new contexts in configuration file
- No code changes needed for new patterns
- Priority system handles overlapping patterns

### ✅ Backwards Compatible
- Loose files still use file type classification
- Existing custom folder mapping still works
- Can migrate gradually

---

## 🚀 Implementation Plan

### Phase 1: Core Context Detection (Week 1)
- [ ] Create `core/context_detector.py`
- [ ] Implement semantic path pattern matching
- [ ] Create `config/semantic_paths.yaml`
- [ ] Add metadata extraction from folder names

### Phase 2: Integration (Week 1-2)
- [ ] Modify `core/organizer.py` to use context detection first
- [ ] Update priority order: Context → Project → File Type
- [ ] Add context preservation logic
- [ ] Test with DICOM files, work files, education files

### Phase 3: Testing & Refinement (Week 2)
- [ ] Dry run on your Documents folder
- [ ] Review results and adjust patterns
- [ ] Add missing contexts
- [ ] Fine-tune preservation rules

### Phase 4: Image Clustering (Future)
- [ ] EXIF metadata extraction
- [ ] Date/location clustering
- [ ] Optional: AI content detection

---

## 🎯 Key Configuration Example

```yaml
# config/semantic_paths.yaml

semantic_contexts:
  # Personal - Disability/VA (HIGHEST PRIORITY)
  - name: "Personal - Disability/VA"
    patterns:
      - "/personal/"
      - "/disability/"
      - "/va_img"
      - "/va/"
      - "/medical/"
    destination: "Personal/Disability/VA"
    preserve_structure: true
    preserve_from_pattern: true  # Start preserving from pattern match
    priority: 100
    examples:
      - "/personal/Disability/VA_IMG_CANADY_MRI.../DICOM/"
      - "/Documents/Disability/medical_records/"

  # Work Files
  - name: "Work"
    patterns:
      - "/work-info/"
      - "/work/"
      - "/afcam/"
      - "/scc/"
      - "/fbi/"
    destination: "Work"
    preserve_structure: true
    priority: 90

  # Education
  - name: "Education"
    patterns:
      - "/education/"
      - "/coursera/"
      - "/mit-sloan/"
      - "/wright-state/"
      - "/afit/"
    destination: "Education"
    preserve_structure: true
    priority: 90

  # Family
  - name: "Personal/Family"
    patterns:
      - "/dad/"
      - "/family/"
    destination: "Personal/Family"
    preserve_structure: true
    priority: 85

project_indicators:
  # Medical Imaging
  - name: "DICOM Medical Images"
    patterns:
      - "dicom/"
      - "series_"
    extensions:
      - ".dcm"
    preserve: "parent_tree"  # Preserve entire parent directory
    priority: 100

  # Code Projects
  - name: "Code Projects"
    patterns:
      - ".git/"
      - "package.json"
      - "requirements.txt"
      - ".xcodeproj"
    preserve: "project_root"
    priority: 95
```

---

## 💬 Questions for You

1. **Are there other semantic contexts** you want to preserve?
   - Examples: Hobbies, Finances, Taxes, Legal, etc.

2. **Should we implement Phase 1 (context detection) immediately?**
   - This would fix your DICOM/VA files issue

3. **Do you want image clustering (Phase 4)?**
   - Would require additional libraries (face_recognition, EXIF tools)
   - Could group vacation photos, family events, etc.

4. **Any other folder patterns** that should stay intact?
   - Gaming saves, music libraries, photo albums, etc.

---

## 🎯 Next Steps

If you approve this approach, I can:

1. **Immediately implement** `core/context_detector.py` with semantic path detection
2. **Create** `config/semantic_paths.yaml` with your Personal/Disability/VA pattern
3. **Modify** organizer to check context BEFORE file type
4. **Test** with your MRI DICOM files to verify structure preservation

This will be a **game-changer** for real-world file organization!

---

**Version:** 1.0.0 (Proposal)
**Created:** 2025-11-14
**Status:** Awaiting Approval
