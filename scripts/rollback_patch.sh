#!/bin/bash
# scripts/rollback_patch.sh

PATCH_FILES=(
  "core/scanner.py"
  "core/previewer.py"
)

echo "♻️ Rolling back patch 0.4.3..."

cd ../File_Deduplification || {
  echo "❌ Cannot find project directory. Exiting."
  exit 1
}

# Revert changes to each file
for file in "${PATCH_FILES[@]}"; do
  echo "⏪ Reverting $file..."
  git restore "$file"
done

echo "📝 Committing rollback..."
git commit -am "⏪ Rollback Patch 0.4.3: Restore scanner and previewer"

echo "🚀 Pushing rollback to remote..."
git push origin main

echo "✅ Rollback completed."
