#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: ai_tagger.py
# Purpose: AI-powered file tagging for all file types
#
# Description:
# Uses AI and semantic analysis to generate intelligent tags
# for all files based on path context, directory structure,
# semantic meaning, and content analysis.
#
# Author: Tim Canady
# Created: 2025-11-19
#
# Version: 1.0.0
# Last Modified: 2025-11-19 by Tim Canady
###################################################################

from pathlib import Path
from typing import List, Set, Optional
import logging
import re

from core.context_detector import ContextDetector
from utils.path_metadata import extract_path_metadata, is_date_like
from models.file_info import FileInfo

logger = logging.getLogger(__name__)


class AITagger:
    """
    AI-powered tagger for generating intelligent file tags.

    Uses multiple sources:
    - Semantic context detection (Personal/Disability/VA, Work, Education, etc.)
    - Path structure analysis (directory names, file names)
    - File metadata (dates, categories, owners)
    - Content hints (file type, extension)
    """

    def __init__(self, semantic_config_path: Optional[Path] = None):
        """
        Initialize AI tagger.

        Args:
            semantic_config_path: Path to semantic_paths.yaml config
        """
        if semantic_config_path is None:
            semantic_config_path = Path(__file__).parent.parent / "config" / "semantic_paths.yaml"

        self.context_detector = ContextDetector(semantic_config_path)

    def generate_tags(self, file_info: FileInfo) -> List[str]:
        """
        Generate intelligent tags for a file using AI analysis.

        Args:
            file_info: File information object

        Returns:
            List of generated tags
        """
        tags = set()

        # 1. Semantic context tags
        context_tags = self._extract_context_tags(file_info)
        tags.update(context_tags)

        # 2. Path-based tags
        path_tags = self._extract_path_tags(file_info)
        tags.update(path_tags)

        # 3. Category/type tags
        type_tags = self._extract_type_tags(file_info)
        tags.update(type_tags)

        # 4. Temporal tags
        temporal_tags = self._extract_temporal_tags(file_info)
        tags.update(temporal_tags)

        # 5. Owner/device tags
        owner_tags = self._extract_owner_tags(file_info)
        tags.update(owner_tags)

        # Remove generic/noisy tags
        tags = self._filter_tags(tags)

        return sorted(list(tags))

    def _extract_context_tags(self, file_info: FileInfo) -> Set[str]:
        """Extract tags from semantic context detection."""
        tags = set()

        context = self.context_detector.detect_context(file_info.path)
        if context:
            # Add context name as tag (e.g., "Personal/Disability/VA" -> "Disability", "VA")
            for part in context.context_name.split('/'):
                if part and part not in ['Personal', 'Other']:  # Skip generic parts
                    tags.add(part)

            # Add custom tags from context
            if hasattr(context, 'tags'):
                tags.update(context.tags)

        return tags

    def _extract_path_tags(self, file_info: FileInfo) -> Set[str]:
        """Extract meaningful tags from file path."""
        tags = set()

        # Use path metadata if available
        if file_info.path_metadata:
            # Category tags from parent folders
            category_tags = file_info.path_metadata.get('category_tags', [])
            tags.update(category_tags)

            # Tags from metadata
            metadata_tags = file_info.path_metadata.get('tags', [])
            tags.update(metadata_tags)
        else:
            # Fallback: extract from path parts
            path_parts = file_info.path.parts

            # Skip common root parts
            skip_parts = {'Users', 'home', 'Documents', 'Desktop', 'Downloads', 'Pictures'}

            for part in path_parts[:-1]:  # Exclude filename
                if part in skip_parts:
                    continue

                # Skip Apple backup patterns (e.g., "Documents - 42739")
                if ' - ' in part and any(apple in part for apple in ['Documents', 'Desktop', 'Downloads']):
                    continue

                # Skip date-like folders
                if is_date_like(part):
                    continue

                # Add meaningful directory names
                if len(part) > 2:  # Skip very short names
                    tags.add(part)

        # Extract tags from filename (without extension)
        filename_tags = self._extract_filename_tags(file_info.path.stem)
        tags.update(filename_tags)

        return tags

    def _extract_filename_tags(self, filename: str) -> Set[str]:
        """Extract meaningful tags from filename."""
        tags = set()

        # Split filename by common separators
        parts = re.split(r'[-_\s.]+', filename)

        for part in parts:
            part = part.strip()

            # Skip short parts, numbers, dates
            if len(part) < 3:
                continue
            if part.isdigit():
                continue
            if is_date_like(part):
                continue

            # Skip generic words
            generic_words = {
                'file', 'document', 'image', 'photo', 'pic', 'picture',
                'video', 'movie', 'clip', 'audio', 'song', 'music',
                'copy', 'final', 'draft', 'version', 'new', 'old',
                'img', 'dsc', 'scan', 'page', 'doc', 'untitled'
            }
            if part.lower() in generic_words:
                continue

            tags.add(part)

        return tags

    def _extract_type_tags(self, file_info: FileInfo) -> Set[str]:
        """Extract tags based on file type/category."""
        tags = set()

        if file_info.type:
            category = file_info.type

            # Add category as tag
            if category not in ['other', 'unknown']:
                tags.add(category)

            # Add specific type hints
            type_hints = {
                'image': ['photo', 'picture', 'graphic'],
                'video': ['movie', 'clip', 'recording'],
                'audio': ['music', 'sound'],
                'document': ['text'],
                'code': ['programming', 'source', 'script'],
                'financial': ['money', 'tax', 'finance'],
                'education': ['course', 'school', 'class'],
                'web': ['website', 'html'],
            }

            hints = type_hints.get(category, [])
            # Only add hints if they're not already covered by path
            # (avoid redundancy)

        # Add extension as tag for specific types
        extension = file_info.path.suffix.lower()
        if extension in ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']:
            tags.add(extension[1:])  # Remove the dot

        return tags

    def _extract_temporal_tags(self, file_info: FileInfo) -> Set[str]:
        """Extract temporal/date tags."""
        tags = set()

        # Extract year if available
        if file_info.year:
            year_str = str(file_info.year)
            if year_str != 'Unknown_Year':
                tags.add(year_str)

                # Add decade tag
                if len(year_str) == 4:
                    decade = year_str[:3] + "0s"  # e.g., "2020s"
                    tags.add(decade)

        # Check path metadata for date tags
        if file_info.path_metadata:
            date_tags = file_info.path_metadata.get('date_tags', [])
            tags.update(date_tags)

        return tags

    def _extract_owner_tags(self, file_info: FileInfo) -> Set[str]:
        """Extract owner/device tags."""
        tags = set()

        if file_info.owner and file_info.owner != 'Unknown_Owner':
            tags.add(file_info.owner)

        return tags

    def _filter_tags(self, tags: Set[str]) -> Set[str]:
        """Remove generic, noisy, or duplicate tags."""
        filtered = set()

        # Generic words to remove
        generic = {
            'file', 'files', 'folder', 'folders', 'data', 'stuff', 'misc',
            'other', 'unknown', 'temp', 'tmp', 'new', 'old', 'copy',
            'untitled', 'document', 'image', 'photo', 'video', 'audio'
        }

        for tag in tags:
            tag = tag.strip()

            # Skip empty or very short
            if len(tag) < 2:
                continue

            # Skip generic words
            if tag.lower() in generic:
                continue

            # Skip if all digits
            if tag.isdigit():
                continue

            # Normalize: capitalize first letter
            tag = tag[0].upper() + tag[1:] if len(tag) > 1 else tag.upper()

            filtered.add(tag)

        return filtered


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ai_tagger.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    # Create a FileInfo object
    from utils.path_metadata import extract_path_metadata
    file_info = FileInfo(
        path=file_path,
        file_hash=None,
        type=None,
        owner=None,
        year=None,
        path_metadata=extract_path_metadata(file_path)
    )

    # Generate tags
    tagger = AITagger()
    tags = tagger.generate_tags(file_info)

    print(f"\nFile: {file_path.name}")
    print(f"Tags: {', '.join(tags)}")
    print(f"\nTotal tags: {len(tags)}")
