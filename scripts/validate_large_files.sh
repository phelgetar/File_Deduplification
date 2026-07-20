#!/usr/bin/env bash
#
###################################################################
# Project: File_Deduplification
# File: validate_large_files.sh
# Purpose: Prevent committing files > 100MB to Git
#
# Author: Tim Canady
# Created: 2025-11-06
#
# Version: 0.1.0
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-06): Initial version — Tim Canady
###################################################################
#

MAX_SIZE=$((100 * 1024 * 1024))  # 100 MB

echo "🔎 Checking staged files for size violations (>100MB)..."

# Get list of staged files
files=$(git diff --cached --name-only --diff-filter=AM)

for file in $files; do
    if [[ -f "$file" ]]; then
        size=$(wc -c < "$file")
        if [[ $size -gt $MAX_SIZE ]]; then
            echo "❌ ERROR: '$file' is $(du -h "$file" | cut -f1) — exceeds 100MB limit."
            echo "🛑 Commit aborted. Use .gitignore or Git LFS for large files."
            exit 1
        fi
    fi
done

echo "✅ All staged files are under the 100MB limit."
