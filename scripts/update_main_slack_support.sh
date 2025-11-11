#!/usr/bin/env bash

set -e

echo "📁 Staging updated main.py..."
git add main.py

echo "📝 Committing changes..."
git commit -m '🔔 Add Slack notification integration in main.py (v0.4.5)'

echo "🚀 Pushing to origin/main..."
git push origin main

echo "✅ Slack integration committed and pushed."
