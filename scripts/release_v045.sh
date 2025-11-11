#!/usr/bin/env bash
from pip._internal.vcs import git

#####################################################################
# Script: release_v045.sh
# Purpose: Automate tagging, changelog bump, and GitHub release
#
# Author: Tim Canady
# Created: 2025-11-06
#
# Version: 0.4.5
# Last Modified: 2025-11-06 by Tim Canady
#
# Revision History:
# - 0.4.5 (2025-11-06): Initial release script for v0.4.5
#####################################################################

set -e

VERSION="v0.4.5"
TAG_MSG="📦 Release version $VERSION - Utilities and Organizer restoration"

echo "📘 Tagging release $VERSION..."
git add .
git commit -m "$TAG_MSG"
git tag -a "$VERSION" -m "$TAG_MSG"
git push origin main
git push origin "$VERSION"

echo "📜 Generating GitHub release..."
gh release create "$VERSION" --title "$VERSION - Utilities + Organizer Restoration" --notes-file CHANGELOG.md

echo "✅ Release $VERSION published successfully!"
