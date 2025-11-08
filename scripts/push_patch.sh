#!/usr/bin/env bash

set -e

PATCH_DIR="../zips"
echo "🔍 Searching for latest zip patch in $PATCH_DIR..."

latest_zip=$(ls -t "$PATCH_DIR"/*.zip | head -n 1)
echo "📦 Extracting $(basename "$latest_zip")..."

unzip -o "$latest_zip" -d ./

if [[ -f patch_info.txt ]]; then
  echo "🧾 Staging files from patch_info.txt..."
  grep -v '^#' patch_info.txt | grep -v '^\s*$' | xargs git add
else
  echo "⚠️ No patch_info.txt found in zip. Defaulting to 'git add .'"
  git add .
  rm "$PATCH_INFO"
fi

echo "📝 Committing patch..."
git commit -m "🔧 Apply patch $(basename "$latest_zip")"

echo "🔎 Checking staged files for size violations (>100MB)..."
if git diff --cached --name-only | xargs -I{} find {} -type f -size +100M | grep -q .; then
  echo "❌ One or more staged files exceed 100MB. Commit aborted."
  exit 1
fi

echo "🚀 Pushing to origin..."
git push origin main
echo "✅ Patch applied and pushed."
