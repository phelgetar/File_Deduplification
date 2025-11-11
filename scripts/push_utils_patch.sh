#!/bin/bash

echo "🔍 Staging utils/ and core/organizer.py..."
git add utils/*.py core/organizer.py

echo "📝 Committing changes..."
git commit -m "🔧 Add missing utils modules and restore core/organizer.py"

echo "🚀 Pushing to origin..."
git push origin main

echo "✅ Patch committed and pushed successfully."
