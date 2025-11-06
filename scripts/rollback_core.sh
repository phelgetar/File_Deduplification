#!/usr/bin/env bash

###################################################################
# Project: File Deduplication
# Script: rollback_core.sh
# Purpose: Restore the latest core/ backup
#
# Author: Tim Canady
# Created: 2025-11-04
#
# Usage:
#   chmod +x rollback_core.sh
#   ./rollback_core.sh
#
# Notes:
#   - Restores latest ../backup/core_<timestamp> to core/
###################################################################

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR/.."
CORE_DIR="$PROJECT_ROOT/core"
LATEST_BACKUP=$(ls -d "$PROJECT_ROOT"/../backup/core_* 2>/dev/null | sort -r | head -n 1)

if [[ -z "$LATEST_BACKUP" ]]; then
  echo "❌ No core backups found in ../backup/"
  exit 1
fi

echo "⏪ Restoring from: $LATEST_BACKUP"
echo "📁 Target core dir: $CORE_DIR"

read -p "Are you sure you want to restore this backup? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "❌ Rollback cancelled."
  exit 1
fi

cp -r "$LATEST_BACKUP"/* "$CORE_DIR"/

echo "✅ Rollback complete."
