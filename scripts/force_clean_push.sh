#!/usr/bin/env bash
#
###################################################################
# Project: File_Deduplification
# File: force_clean_push.sh
# Purpose: Force push cleaned repo history after filter-repo use
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

set -e

echo "🔍 Verifying .scan_cache.json is removed from Git history..."
if git log --all -- .scan_cache.json | grep -q .; then
  echo "❌ .scan_cache.json is still in history. Run git filter-repo first."
  exit 1
else
  echo "✅ Clean. Proceeding..."
fi

# Restore remote if needed
if ! git remote get-url origin &>/dev/null; then
  echo "🔗 Re-adding GitHub remote..."
  git remote add origin https://github.com/phelgetar/File_Deduplification.git
fi

echo "🚀 Force pushing cleaned main branch to GitHub..."
git push origin main --force --no-verify

echo "✅ Done. Your remote repository is now clean and up to date."
