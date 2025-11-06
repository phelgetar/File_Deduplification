#!/usr/bin/env bash

###################################################################
# Project: File Deduplication
# Script: update_core.sh
# Purpose: Update the File_Deduplification/core/ directory from a ZIP
#
# Author: Tim Canady
# Created: 2025-11-04
#
# Usage:
#   chmod +x update_core.sh
#   ./scripts/update_core.sh [ZIP_FILE]
#
# Notes:
#   - Expects ZIPs in ../zips/
#   - Targets ../File_Deduplification/core/
#   - Syntax-checks each file after extract
###################################################################

set -e

# Get absolute paths
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR/.."
CORE_DIR="$PROJECT_ROOT/core"
ZIP_DIR="$PROJECT_ROOT/../zips"
BACKUP_DIR="$PROJECT_ROOT/../backup/core_$(date +%Y%m%d_%H%M%S)"

ZIP_FILE="${1:-$ZIP_DIR/File_Deduplication_DBUpdate_FIXED.zip}"

if [[ ! -f "$ZIP_FILE" ]]; then
  echo "❌ ZIP file not found: $ZIP_FILE"
  exit 1
fi

echo "📦 ZIP file: $ZIP_FILE"
echo "📁 App root: $PROJECT_ROOT"
echo "🔐 Backing up current core/ to: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"
cp -r "$CORE_DIR"/* "$BACKUP_DIR"/

echo "📂 Extracting to: $CORE_DIR"
unzip -o "$ZIP_FILE" -d "$CORE_DIR"

echo "🧪 Validating Python syntax..."
FAIL=0
for pyfile in "$CORE_DIR"/*.py; do
  echo "🔍 Checking: $(basename "$pyfile")"
  if ! python3 -m py_compile "$pyfile"; then
    echo "❌ Syntax error in: $pyfile"
    FAIL=1
  fi
done

if [[ "$FAIL" -eq 1 ]]; then
  echo "❌ Aborting due to syntax errors."
  exit 1
fi

echo "✅ All Python files passed syntax check."
echo "✅ Core updated successfully in: $CORE_DIR"
