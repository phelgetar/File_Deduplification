#!/bin/bash
# scripts/push_patch.sh
# Automatically extract and commit the latest patch from ../zips/

set -e

cd "$(dirname "$0")/.." || exit 1

echo "🔍 Searching for latest zip patch in ../zips/..."
PATCH_ZIP=$(ls -t ../zips/*.zip 2>/dev/null | head -n 1)

if [ ! -f "$PATCH_ZIP" ]; then
  echo "❌ No zip file found in ../zips/"
  exit 1
fi

echo "📦 Extracting $(basename "$PATCH_ZIP")..."
unzip -o "$PATCH_ZIP" -d ./

PATCH_INFO="patch_info.txt"
if unzip -l "$PATCH_ZIP" | grep -q "$PATCH_INFO"; then
  unzip -p "$PATCH_ZIP" "$PATCH_INFO" > "$PATCH_INFO"
else
  echo "⚠️ No patch_info.txt found in zip. Defaulting to 'git add .'"
  git add .
fi

if [ -f "$PATCH_INFO" ]; then
  echo "🧾 Staging files from patch_info.txt..."
  while IFS= read -r line; do
    [ -n "$line" ] && git add "$line"
  done < "$PATCH_INFO"
  rm "$PATCH_INFO"
fi

echo "📝 Committing patch..."
git commit -m "🔧 Apply latest patch $(basename "$PATCH_ZIP")"

echo "🚀 Pushing to origin..."
git push origin main

echo "✅ Patch applied and pushed."
