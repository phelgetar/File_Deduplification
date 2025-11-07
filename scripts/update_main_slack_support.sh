#!/usr/bin/env bash

set -e

echo "📁 Staging updated main.py..."
git add main.py

echo "📝 Committing changes..."
git commit -m '🔔 Update main.py to use send_slack_notification for Slack integration'

echo "🚀 Pushing to origin/main..."
git push origin main

echo "✅ Update pushed successfully."
