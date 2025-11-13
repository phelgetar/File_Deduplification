## [v0.7.0]
– 2025-11-13

### 🎯 Major Features Added

#### **Intelligent File Size Management**
- ✨ **NEW**: `--metadata-only-size` CLI parameter for handling large files efficiently
  - Accepts human-readable sizes: `75MB`, `1GB`, `500KB`, etc.
  - Files above threshold are tracked with metadata only (no hashing)
  - Files below threshold are fully hashed for deduplication
  - Configurable per-scan for maximum flexibility

#### **Database Schema Enhancement**
- ✨ **NEW**: Added `metadata_only` boolean column to `files` table
  - Tracks which files were processed metadata-only vs. fully hashed
  - Includes database migration script: `migrations/001_add_metadata_only_column.sql`
  - Backwards compatible with existing databases

#### **Massive File Classification Improvements**
- ✨ **NEW**: Expanded from **10 to 18 categories** (+80% increase)
- ✨ **NEW**: Support for **250+ file types** (+400% increase)
- ✨ **NEW**: 8 additional file categories:
  - `font`: Typography files (.ttf, .otf, .woff, .woff2, etc.)
  - `installer`: Executables and packages (.exe, .dmg, .pkg, .apk, .msu, etc.)
  - `certificate`: Security certificates (.p7b, .cer, .pem, .key, etc.)
  - `shortcut`: Links and shortcuts (.lnk, .webloc, .rdp, etc.)
  - `scientific`: Research data (.mat, .hdf5, .npy, .fits, etc.)
  - `backup`: Backup files (.bak, .old, .swp, etc.)
  - `temporary`: Temp/download files (.tmp, .crdownload, .cache, etc.)
  - `system`: Config and macOS files (.plist, .strings, Makefile, etc.)

### 📈 Enhanced Existing Categories

#### **Code Category** (+40 new languages)
- Added: Rust, Swift, Kotlin, Scala, PowerShell, TypeScript, Dart
- Added: Lisp family (.lisp, .cl, .scm, .el, .clj)
- Added: Functional languages (Haskell, OCaml, Erlang, Elixir)
- Added: Scientific languages (R, MATLAB, Julia, Fortran)
- Added: Shell scripts (.bash, .zsh, .bat, .cmd, .ps1)

#### **Archive Category** (+10 new formats)
- Added: Disk images (.iso, .dmg, .img)
- Added: Virtual machine formats (.vhd, .vmdk, .ova, .ovf, .qcow2)
- Added: Additional compression (.xz, .lzma, .sitx, .ace, .arj)

#### **Image Category** (+10 new formats)
- Added: RAW camera formats (.cr2, .nef, .dng, .raw)
- Added: Design files (.psd, .ai, .eps, .indd)
- Added: Modern formats (.heic, .heif, .webp)

#### **Video Category** (+7 new formats)
- Added: Broadcast formats (.ts, .mts, .m2ts, .vob)
- Added: Mobile and streaming (.3gp, .ogv, .m4v)

#### **Audio Category** (+5 new formats)
- Added: Lossless formats (.opus, .ape, .alac, .aiff)
- Added: MIDI music files (.mid, .midi)

#### **Document Category** (+5 new formats)
- Added: Academic papers (.tex for LaTeX)
- Added: E-books (.epub, .mobi, .azw, .djvu)
- Added: Apple Pages documents (.pages)

#### **Spreadsheet Category** (+2 new formats)
- Added: Apple Numbers (.numbers)
- Added: Tab-separated values (.tsv)

#### **Presentation Category** (+1 new format)
- Added: Apple Keynote (.key)

#### **Data Category** (+8 new formats)
- Added: Configuration files (.toml, .ini, .conf, .cfg)
- Added: Database files (.sqlite, .db, .mdb, .accdb)
- Added: SQLite temp files (.sqlite-wal, .sqlite-shm)
- Added: Generic data files (.dat, .data)

### 🐛 Bug Fixes

#### **macOS File Type Recognition**
- 🔧 Fixed: Unknown MIME type warnings for macOS `.strings` files
- 🔧 Fixed: Unrecognized `.plist`, `.nib`, `.xib`, `.storyboard` files
- 🔧 Fixed: macOS app bundle files (CodeResources, Info.plist, etc.)
- 🔧 Fixed: Files inside `/Contents/MacOS/`, `/Contents/PlugIns/`, `/Contents/Resources/`
- 🔧 Fixed: macOS alias files now properly classified as shortcuts

#### **GUI Error Handling**
- 🔧 Fixed: PySimpleGUI crash when `theme()` method unavailable
- 🔧 Added: Graceful fallback when PySimpleGUI not installed
- 🔧 Added: Comprehensive error handling with helpful installation instructions
- 🔧 Added: Compatibility with both old and new PySimpleGUI API versions

### 📝 Documentation

- 📄 **NEW**: `CLASSIFICATION_IMPROVEMENTS.md` - Comprehensive guide to all 250+ file types
- 📄 Updated: `README.md` with new features and CLI options
- 📄 Updated: `CHANGELOG.md` cleaned up and reorganized
- 📄 **NEW**: `migrations/001_add_metadata_only_column.sql` - Database migration script

### 🧪 Testing

- ✅ Tested: Metadata-only size filtering with 75MB threshold
- ✅ Tested: Files above/below threshold processed correctly
- ✅ Tested: Database migration on existing database
- ✅ Verified: Classification improvements reduce "other" category by ~90%

### 🔄 Changed Files

**Core Modules:**
- `main.py`: Added `--metadata-only-size` parameter and `parse_size()` function
- `core/hasher.py`: Added `metadata_only_size` parameter and size checking logic
- `core/db.py`: Added `metadata_only` column and updated `cache_file_entry()`
- `core/classifier.py`: Complete rewrite with 250+ file type support

**Utility Modules:**
- `utils/gui.py`: Enhanced error handling and updated statistics display

**Database:**
- `migrations/001_add_metadata_only_column.sql`: New migration script

**Documentation:**
- `CLASSIFICATION_IMPROVEMENTS.md`: New comprehensive classification guide
- `README.md`: Updated with new features
- `CHANGELOG.md`: Cleaned and updated

### 💡 Performance Improvements

- ⚡ Files larger than threshold skip expensive hashing operation
- ⚡ Significantly reduced processing time for large file collections
- ⚡ Reduced "unknown type" warnings by ~90%
- ⚡ More accurate file organization with expanded categories

### 🎓 Migration Notes

If you have an existing database, run the migration:

```bash
cd migrations
mysql -u your_user -p your_database < 001_add_metadata_only_column.sql
```

Or let SQLAlchemy auto-create the column on next run with `--use-db`.

### 📊 Impact

**Before v0.7.0:**
- 10 categories
- ~50 file types supported
- High "other" classification rate

**After v0.7.0:**
- 18 categories (+80%)
- 250+ file types supported (+400%)
- ~90% reduction in "other" classifications
- Intelligent large file handling

---