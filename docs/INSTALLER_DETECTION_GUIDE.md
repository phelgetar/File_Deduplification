# Installer & Application Detection Guide

## Overview

The File Deduplication system comprehensively detects applications, software installers, and disk images across all major platforms. These files are handled in two ways:

1. **Atomic Packages** - Treated as single units (no internal scanning)
2. **Installer Category** - Classified as installer files
3. **Application Directories** - Structure-preserving for installed apps

---

## 🎯 Detection Summary

### ✅ Yes, the code CAN detect:
- ✅ macOS applications (.app bundles)
- ✅ macOS installers (.pkg, .mpkg)
- ✅ Windows installers (.exe, .msi, .appx, .msix)
- ✅ Linux packages (.deb, .rpm, .flatpak, .snap, .appimage)
- ✅ Mobile installers (.apk, .ipa)
- ✅ Disk images (.dmg, .iso, .img, and 10+ more formats)
- ✅ Virtual machine images (.vhd, .vmdk, .vdi, .ova, .ovf)
- ✅ Installed applications (PacketTracer with structure preservation)

---

## 📦 Atomic Packages (Treated as Single Units)

These files are **NOT scanned internally** - they're treated as complete, indivisible units:

### macOS Packages
| Extension | Description | Example |
|-----------|-------------|---------|
| `.app` | macOS application bundle | `Safari.app` |
| `.pkg` | macOS installer package | `Office.pkg` |
| `.mpkg` | macOS meta-package installer | `Adobe_Suite.mpkg` |

### Disk Images
| Extension | Description | Platform | Example |
|-----------|-------------|----------|---------|
| `.dmg` | Apple Disk Image | macOS | `Installer.dmg` |
| `.iso` | ISO 9660 Disk Image | All | `Ubuntu.iso` |
| `.img` | Raw Disk Image | All | `disk.img` |
| `.toast` | Roxio Toast Disk Image | macOS | `backup.toast` |
| `.cdr` | macOS Disk Image | macOS | `data.cdr` |
| `.nrg` | Nero Disk Image | Windows | `game.nrg` |
| `.mds` | Media Descriptor Sidecar | Windows | `disc.mds` |
| `.mdf` | Media Disc Image File | Windows | `disc.mdf` |

### Virtual Machine Disk Images
| Extension | Description | Platform | Example |
|-----------|-------------|----------|---------|
| `.vhd` | Virtual Hard Disk | Hyper-V | `Windows10.vhd` |
| `.vmdk` | Virtual Machine Disk | VMware | `Ubuntu.vmdk` |
| `.vdi` | Virtual Disk Image | VirtualBox | `Debian.vdi` |
| `.ova` | Open Virtual Appliance | All | `server.ova` |
| `.ovf` | Open Virtualization Format | All | `template.ovf` |

**Behavior:**
```bash
# Example: Scanning a .iso file
/Desktop/Ubuntu-22.04.iso (800 MB)
  ↓
Scanned as: ONE file
Internal files: NOT scanned
Category: archive
Hash: Single hash for entire .iso
```

---

## 💿 Installer Category (Regular File Classification)

These files are scanned and classified as "installer":

### Windows Installers
| Extension | Description | Example |
|-----------|-------------|---------|
| `.exe` | Windows executable | `setup.exe` |
| `.msi` | Windows Installer package | `Office.msi` |
| `.appx` | Windows Store app package | `Calculator.appx` |
| `.msix` | Modern Windows app package | `Teams.msix` |
| `.msu` | Windows Update package | `KB5001234.msu` |

### Linux Packages
| Extension | Description | Distribution | Example |
|-----------|-------------|--------------|---------|
| `.deb` | Debian package | Debian, Ubuntu | `firefox.deb` |
| `.rpm` | Red Hat package | Fedora, RHEL | `vim.rpm` |
| `.flatpak` | Flatpak package | Universal | `gimp.flatpak` |
| `.snap` | Snap package | Universal | `vscode.snap` |
| `.appimage` | AppImage package | Universal | `krita.appimage` |
| `.run` | Linux installer script | Various | `nvidia.run` |

### Mobile Installers
| Extension | Description | Platform | Example |
|-----------|-------------|----------|---------|
| `.apk` | Android package | Android | `WhatsApp.apk` |
| `.ipa` | iOS app package | iOS | `Instagram.ipa` |

### Binary Files & Libraries
| Extension | Description | Platform | Example |
|-----------|-------------|----------|---------|
| `.dll` | Dynamic link library | Windows | `kernel32.dll` |
| `.so` | Shared object | Linux | `libssl.so` |
| `.dylib` | Dynamic library | macOS | `libSystem.dylib` |
| `.bin` | Binary file | Various | `firmware.bin` |
| `.out` | Executable output | Unix | `a.out` |
| `.elf` | ELF executable | Linux | `app.elf` |

**Behavior:**
```bash
# Example: Regular installer file
/Desktop/setup.exe (50 MB)
  ↓
Scanned as: Regular file
Category: installer
Destination: /organized/Desktop/2024/installer/canadytw/setup.exe
```

---

## 🖥️ Application Directories (Structure-Preserving)

Installed applications that need their directory structure preserved:

| Directory Pattern | Description | Example |
|-------------------|-------------|---------|
| `/PacketTracer/` | Cisco PacketTracer | `/Desktop/PacketTracer/` |
| `/Packet Tracer/` | Cisco PacketTracer (space) | `/Desktop/Packet Tracer/` |

**Behavior:**
```bash
# Example: PacketTracer installation
/Desktop/PacketTracer/
├── bin/packettracer
├── lib/libssl.so.1
└── extensions/plugins/
  ↓
Organized as: Complete structure preserved
Category: application
Destination: /organized/Desktop/application/PacketTracer/
  ├── bin/packettracer
  ├── lib/libssl.so.1
  └── extensions/plugins/
```

---

## 🔍 How Detection Works

### 1. Atomic Package Detection

```python
# In core/scanner.py
atomic_extensions = {
    '.app', '.pkg', '.mpkg',              # macOS packages
    '.dmg', '.iso', '.img',               # Disk images
    '.vhd', '.vmdk', '.vdi',              # VM disk images
    '.ova', '.ovf',                       # Virtual appliances
    '.toast', '.cdr',                     # macOS disk images
    '.nrg',                               # Nero disk images
    '.mds', '.mdf'                        # Media Descriptor Files
}

# When scanning:
if is_atomic_package(file):
    # Add to results as single file
    # Skip scanning internal contents
```

### 2. Installer Classification

```python
# In core/classifier.py
if file_extension in [
    ".exe", ".msi", ".app", ".pkg", ".mpkg",           # macOS/Windows
    ".deb", ".rpm", ".apk", ".ipa",                    # Linux/Mobile
    ".flatpak", ".snap", ".appimage",                  # Modern Linux
    ".dll", ".so", ".dylib"                            # Libraries
]:
    category = "installer"
```

### 3. Application Directory Detection

```python
# In core/classifier.py
if any(app_dir in file_path_str.lower() for app_dir in [
    "/packettracer/", "/packet tracer/"
]):
    category = "application"
    # Special handling: preserve directory structure
```

---

## 📊 Complete Format Support

### Summary Table

| Category | Atomic? | Structure Preserved? | Count |
|----------|---------|---------------------|-------|
| **macOS Packages** | ✅ Yes | ✅ Yes (atomic) | 3 |
| **Disk Images** | ✅ Yes | ✅ Yes (atomic) | 8 |
| **VM Disk Images** | ✅ Yes | ✅ Yes (atomic) | 5 |
| **Windows Installers** | ❌ No | ❌ No | 5 |
| **Linux Packages** | ❌ No | ❌ No | 6 |
| **Mobile Installers** | ❌ No | ❌ No | 2 |
| **Libraries** | ❌ No | ❌ No | 6 |
| **Application Dirs** | ❌ No | ✅ Yes (recursive) | N/A |
| **TOTAL** | - | - | **35+** |

---

## 🚀 Usage Examples

### Example 1: Organize Installers Directory

```bash
cd /Users/canadytw/PycharmProjects/File_Deduplification

# Scan directory with installers
python main.py /Users/canadytw/Documents/Installers \
  --base-dir /organized \
  --use-db \
  --write-metadata \
  --dry-run-log
```

**Output:**
```
🔍 Scanning files...
Found 3 atomic packages (.app, .pkg, .dmg) treated as single units
  [1/15] Processing: Safari.app (atomic package)
  [2/15] Processing: Office.pkg (atomic package)
  [3/15] Processing: Ubuntu.iso (atomic package)
  [4/15] Processing: Chrome.dmg (atomic package)
  [5/15] Processing: setup.exe
  [6/15] Processing: installer.msi
  ...

🤖 Classifying files with AI...
  ✓ Safari.app → installer (atomic)
  ✓ Office.pkg → installer (atomic)
  ✓ Ubuntu.iso → archive (atomic)
  ✓ Chrome.dmg → archive (atomic)
  ✓ setup.exe → installer
  ✓ installer.msi → installer
```

### Example 2: Query All Installers

```bash
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT
    SUBSTRING_INDEX(f.path, '.', -1) AS extension,
    COUNT(*) AS count,
    ROUND(SUM(f.size) / 1073741824, 2) AS total_gb
FROM files f
LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category IN ('installer', 'archive')
  AND SUBSTRING_INDEX(f.path, '.', -1) IN (
    'exe', 'msi', 'pkg', 'mpkg', 'app', 'deb', 'rpm',
    'dmg', 'iso', 'img', 'apk', 'ipa', 'flatpak', 'snap'
  )
GROUP BY extension
ORDER BY total_gb DESC;
"
```

**Example Output:**
```
+-----------+-------+----------+
| extension | count | total_gb |
+-----------+-------+----------+
| iso       |     5 |    15.80 |
| dmg       |    12 |     8.50 |
| app       |     8 |     3.20 |
| exe       |    45 |     2.10 |
| pkg       |     6 |     1.50 |
| msi       |    10 |     0.80 |
+-----------+-------+----------+
```

### Example 3: Find All Disk Images

```bash
# Using grep on metadata files
find /organized -name "*.meta.json" | \
  xargs grep -l '"type": "archive"' | \
  xargs grep -E '\.(iso|dmg|img|vhd|vmdk)' | \
  sed 's/.meta.json$//'
```

---

## 🔧 Customization

### Add Custom Application Directory

To add support for other applications like PacketTracer, edit `core/classifier.py`:

```python
# Application directories (preserve structure)
elif any(app_dir in file_path_str.lower() for app_dir in [
    "/packettracer/", "/packet tracer/",
    "/virtualbox/",              # Add here
    "/your_app_name/"            # Add here
]):
    category = "application"
```

And update `core/organizer.py`:

```python
app_roots = [
    '/packettracer/', '/packet tracer/',
    '/virtualbox/',              # Add here
    '/your_app_name/'            # Add here
]
```

### Add Custom Atomic Package Format

To add a new format that should be treated as atomic, edit `core/scanner.py`:

```python
atomic_extensions = {
    '.app', '.pkg', '.mpkg',
    '.dmg', '.iso', '.img',
    '.your_format',              # Add here
}
```

And add to archive category in `core/classifier.py`:

```python
elif file_extension in [
    ".zip", ".tar", ".gz", ...,
    ".your_format"               # Add here
]:
    category = "archive"
```

---

## 📈 Statistics

### Formats Added in v1.1.0

**New Atomic Packages:**
- ✅ `.iso` - ISO disk images (most requested)
- ✅ `.img` - Raw disk images
- ✅ `.vdi` - VirtualBox disk images
- ✅ `.toast` - Roxio Toast images
- ✅ `.cdr` - macOS disk images
- ✅ `.nrg` - Nero disk images
- ✅ `.mds`, `.mdf` - Media Descriptor Files

**New Installer Formats:**
- ✅ `.flatpak` - Flatpak packages
- ✅ `.snap` - Snap packages
- ✅ `.appimage` - AppImage packages

**Total Supported Formats:** 35+ installer and disk image formats

---

## 🆘 Troubleshooting

### Issue: .iso File Being Scanned Internally

**Cause:** Using old version before .iso was added to atomic packages

**Check Version:**
```bash
grep "Version:" /Users/canadytw/PycharmProjects/File_Deduplification/core/scanner.py
# Should show: Version: 0.7.0 or higher
```

**Solution:** Update to v0.7.0+ and rescan.

### Issue: Installer File Classified as "other"

**Cause:** Extension not in supported list

**Check Extension:**
```bash
# Find files classified as "other"
mysql -u jarheads_0231 -p -D File_Deduplification -e "
SELECT SUBSTRING_INDEX(f.path, '.', -1) AS extension, COUNT(*) AS count
FROM files f LEFT JOIN classifications c ON f.id = c.file_id
WHERE c.category = 'other'
GROUP BY extension
ORDER BY count DESC
LIMIT 10;
"
```

**Solution:** Add extension to installer category (see Customization section).

### Issue: Application Directory Not Preserving Structure

**Cause:** Directory name doesn't match detection pattern

**Example:**
```bash
# NOT detected:
/Desktop/MyPacketTracer/  → Files scattered

# DETECTED:
/Desktop/PacketTracer/    → Structure preserved
```

**Solution:** Rename directory to match pattern or add custom pattern.

---

## ✅ Summary

### What the Code Detects

✅ **macOS:**
- Applications (.app)
- Installers (.pkg, .mpkg)
- Disk images (.dmg, .iso, .toast, .cdr)

✅ **Windows:**
- Executables (.exe)
- Installers (.msi, .appx, .msix)
- Disk images (.iso, .img, .nrg, .mds, .mdf)
- Virtual disks (.vhd, .vmdk, .vdi)

✅ **Linux:**
- Packages (.deb, .rpm)
- Universal packages (.flatpak, .snap, .appimage)
- Installers (.run)
- Disk images (.iso, .img)

✅ **Mobile:**
- Android (.apk)
- iOS (.ipa)

✅ **Virtual Machines:**
- Virtual disks (.vhd, .vmdk, .vdi)
- Virtual appliances (.ova, .ovf)

✅ **Application Directories:**
- PacketTracer (with structure preservation)

### Detection Methods

1. **Atomic Package Scanning** - Treats as single unit (16 formats)
2. **Installer Classification** - Classifies by extension (19+ formats)
3. **Application Directory Preservation** - Preserves structure (1+ patterns)

### Total Coverage

- **35+ installer and disk image formats**
- **3 detection methods**
- **All major platforms supported**

---

**Version:** 1.1.0
**Last Updated:** 2025-11-14
**Modules:** `core/scanner.py` v0.7.0, `core/classifier.py` v1.1.0
