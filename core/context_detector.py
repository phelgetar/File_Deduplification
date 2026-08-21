#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: context_detector.py
# Purpose: Detect semantic context from file paths for intelligent organization
#
# Description:
# Analyzes file paths to detect semantic contexts (Personal/Disability,
# Work, Education, etc.) and project structures that must remain intact.
# Priority: Context detection > Project detection > File type classification
#
# Author: Tim Canady
# Created: 2025-11-14
#
# Version: 1.0.0
# Last Modified: 2025-11-14 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-14): Initial context detection implementation — Tim Canady
###################################################################

from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import yaml
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContextInfo:
    """Information about detected semantic context."""
    context_name: str
    destination: str
    preserve_structure: bool
    priority: int
    matched_pattern: str
    metadata: Dict[str, str]
    preserve_from_index: int  # Index in path where preservation should start
    # True  -> file in Media/Images/<context>/…, grouped by what it is
    # False -> file in <context>/…, keeping a record set together
    group_by_category: bool = True
    # Where the category folder sits relative to the context folder.
    #   "after_context"  Education/WSU/Docs/PowerPoints/FALL18/deck.pptx
    #   "before_context" Docs/PowerPoints/Education/WSU/FALL18/deck.pptx
    # After is the default: it keeps one subject together and subdivides
    # it by type, rather than scattering a single course across
    # Docs/PowerPoints, Docs/PDF and Media/Images. Finding "every
    # presentation" is a database question, not a directory question.
    category_position: str = "after_context"


@dataclass
class ProjectInfo:
    """Information about detected project structure."""
    project_type: str
    preserve_mode: str  # 'entire_structure', 'project_root', 'parent_tree'
    priority: int
    matched_patterns: List[str]
    root_path: Optional[Path]


class ContextDetector:
    """
    Detects semantic context from file paths.

    Detection Priority:
    1. Semantic path contexts (Personal/Disability, Work, Education) - HIGHEST
    2. Project/application indicators (DICOM, .git, .app) - HIGH
    3. Metadata extraction (dates, names, types from folder names) - MEDIUM
    4. File type classification (fallback) - LOWEST
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize context detector with configuration.

        Args:
            config_path: Path to semantic_paths.yaml configuration file
        """
        self.semantic_contexts = []
        self.project_indicators = []
        # File-wide default for where the category folder sits; a context
        # may override it.
        self.category_position = "after_context"

        if config_path and config_path.exists():
            self._load_config(config_path)
        else:
            # Use default configuration
            self._load_default_config()

    def _load_config(self, config_path: Path):
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.category_position = config.get('category_position',
                                                    'after_context')
                self.semantic_contexts = config.get('semantic_contexts', [])
                self.project_indicators = config.get('project_indicators', [])
                logger.info(f"Loaded context configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            self._load_default_config()

    def _load_default_config(self):
        """Load default configuration if no YAML file exists."""
        self.semantic_contexts = [
            {
                'name': 'Personal - Disability/VA',
                'patterns': ['/personal/', '/disability/', '/va_img', '/va/', '/medical/'],
                'destination': 'Personal/Disability/VA',
                'preserve_structure': True,
                'priority': 100
            },
            {
                'name': 'Work',
                'patterns': ['/work-info/', '/work/', '/afcam/', '/scc/', '/fbi/'],
                'destination': 'Work',
                'preserve_structure': True,
                'priority': 90
            },
            {
                'name': 'Education',
                'patterns': ['/education/', '/coursera/', '/mit-sloan/', '/wright-state/', '/afit/', '/park/', '/dau/'],
                'destination': 'Education',
                'preserve_structure': True,
                'priority': 90
            },
            {
                'name': 'Personal/Family',
                'patterns': ['/dad/', '/family/'],
                'destination': 'Personal/Family',
                'preserve_structure': True,
                'priority': 85
            },
            {
                'name': 'Personal',
                'patterns': ['/personal/'],
                'destination': 'Personal',
                'preserve_structure': True,
                'priority': 80
            }
        ]

        self.project_indicators = [
            {
                'name': 'DICOM Medical Images',
                'patterns': ['dicom/', 'series_'],
                'extensions': ['.dcm'],
                'preserve': 'parent_tree',
                'priority': 100
            },
            {
                'name': 'Code Projects',
                'patterns': ['.git/', 'package.json', 'requirements.txt', '.xcodeproj'],
                'preserve': 'project_root',
                'priority': 95
            }
        ]

    def detect_context(self, file_path: Path) -> Optional[ContextInfo]:
        """
        Detect semantic context from file path.

        Args:
            file_path: The file path to analyze

        Returns:
            ContextInfo if context detected, None otherwise
        """
        file_path_str = str(file_path).lower()

        # Sort contexts by priority (highest first)
        sorted_contexts = sorted(
            self.semantic_contexts,
            key=lambda x: x.get('priority', 0),
            reverse=True
        )

        for context in sorted_contexts:
            patterns = context.get('patterns', [])

            for pattern in patterns:
                if pattern.lower() in file_path_str:
                    # Find where the pattern appears
                    pattern_idx = file_path_str.find(pattern.lower())

                    # Extract metadata from path
                    metadata = self.extract_metadata_from_path(file_path)

                    context_info = ContextInfo(
                        context_name=context['name'],
                        destination=context['destination'],
                        preserve_structure=context.get('preserve_structure', True),
                        priority=context.get('priority', 0),
                        matched_pattern=pattern,
                        metadata=metadata,
                        preserve_from_index=pattern_idx,
                        group_by_category=context.get('group_by_category', True),
                        category_position=context.get(
                            'category_position',
                            self.category_position)
                    )

                    logger.debug(f"Context detected: {context['name']} for {file_path}")
                    return context_info

        return None

    def detect_project(self, file_path: Path) -> Optional[ProjectInfo]:
        """
        Detect if file is part of a project structure.

        Args:
            file_path: The file path to analyze

        Returns:
            ProjectInfo if project detected, None otherwise
        """
        file_path_str = str(file_path).lower()
        file_extension = file_path.suffix.lower()

        # Sort by priority (highest first)
        sorted_indicators = sorted(
            self.project_indicators,
            key=lambda x: x.get('priority', 0),
            reverse=True
        )

        for indicator in sorted_indicators:
            patterns = indicator.get('patterns', [])
            extensions = indicator.get('extensions', [])

            # Check if patterns match
            matched_patterns = []
            for pattern in patterns:
                if pattern.lower() in file_path_str:
                    matched_patterns.append(pattern)

            # Check if extension matches (if specified)
            extension_match = not extensions or file_extension in extensions

            if matched_patterns and extension_match:
                # Find project root
                root_path = self._find_project_root(file_path, matched_patterns)

                project_info = ProjectInfo(
                    project_type=indicator['name'],
                    preserve_mode=indicator.get('preserve', 'entire_structure'),
                    priority=indicator.get('priority', 0),
                    matched_patterns=matched_patterns,
                    root_path=root_path
                )

                logger.debug(f"Project detected: {indicator['name']} for {file_path}")
                return project_info

        return None

    def _find_project_root(self, file_path: Path, patterns: List[str]) -> Optional[Path]:
        """
        Find the root directory of a project.

        Args:
            file_path: The file path
            patterns: Matched patterns that indicate project

        Returns:
            Project root path
        """
        # Walk up the directory tree looking for project indicators
        current = file_path.parent

        while current and current != current.parent:
            for pattern in patterns:
                # Check if pattern exists at this level
                if pattern.startswith('.'):
                    # File pattern (.git, .xcodeproj)
                    if (current / pattern).exists():
                        return current
                else:
                    # Directory pattern
                    if pattern.rstrip('/').lower() in str(current).lower():
                        return current

            current = current.parent

        # Default to immediate parent if no root found
        return file_path.parent

    def extract_metadata_from_path(self, file_path: Path) -> Dict[str, str]:
        """
        Extract semantic metadata from folder names.

        Examples:
            VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020
            -> {type: 'MRI', body_part: 'CERVICAL_SPINE', date: '2020-09-15', owner: 'CANADY'}

        Args:
            file_path: The file path to analyze

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        path_parts = file_path.parts

        # Extract from all directory names in path
        for part in path_parts:
            part_lower = part.lower()

            # Date patterns
            date_patterns = [
                (r'(\d{2})(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\d{4})', '%d%b%Y'),
                (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
                (r'(\d{4})_(\d{2})_(\d{2})', '%Y_%m_%d'),
            ]

            for pattern, date_format in date_patterns:
                match = re.search(pattern, part_lower)
                if match:
                    try:
                        date_str = match.group(0)
                        if 'jan' in date_str or 'feb' in date_str:  # Month name format
                            parsed_date = datetime.strptime(date_str.upper(), '%d%b%Y')
                        else:
                            parsed_date = datetime.strptime(date_str, date_format.replace('_', '-'))
                        metadata['date'] = parsed_date.strftime('%Y-%m-%d')
                    except:
                        pass

            # Medical imaging types
            medical_terms = {
                'mri': 'MRI',
                'ct': 'CT',
                'xray': 'X-Ray',
                'x-ray': 'X-Ray',
                'ultrasound': 'Ultrasound',
                'dicom': 'DICOM'
            }
            for term, value in medical_terms.items():
                if term in part_lower:
                    metadata['imaging_type'] = value

            # Body parts
            body_parts = [
                'cervical', 'spine', 'lumbar', 'thoracic', 'brain', 'head',
                'chest', 'abdomen', 'pelvis', 'knee', 'shoulder', 'ankle'
            ]
            for body_part in body_parts:
                if body_part in part_lower:
                    if 'body_part' not in metadata:
                        metadata['body_part'] = body_part.upper()
                    else:
                        metadata['body_part'] += f"_{body_part.upper()}"

            # VA-specific
            if 'va_' in part_lower or '_va' in part_lower:
                metadata['organization'] = 'VA'

            # Owner/patient name (if pattern matches)
            if 'canady' in part_lower:
                metadata['owner'] = 'CANADY'

            # Course identifiers (CEG, CS, STAT, etc.)
            course_pattern = r'(ceg|cs|stat|mat|econ|phys|chem|bio|eng)\s*(\d{4})'
            match = re.search(course_pattern, part_lower)
            if match:
                metadata['course'] = f"{match.group(1).upper()}{match.group(2)}"

            # Work organizations
            orgs = ['afcam', 'scc', 'fbi', 'assurant']
            for org in orgs:
                if org in part_lower:
                    metadata['organization'] = org.upper()

        return metadata

    def should_preserve_structure(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Determine if file is part of a structure that must stay intact.

        Args:
            file_path: The file path to check

        Returns:
            Tuple of (should_preserve, reason)
        """
        # Check for context
        context = self.detect_context(file_path)
        if context and context.preserve_structure:
            return True, f"Part of {context.context_name} context"

        # Check for project
        project = self.detect_project(file_path)
        if project:
            return True, f"Part of {project.project_type} project"

        return False, None

    def get_preservation_root(self, file_path: Path, context: Optional[ContextInfo] = None) -> Optional[Path]:
        """
        Get the root directory from which structure should be preserved.

        Args:
            file_path: The file path
            context: Optional pre-detected context

        Returns:
            Path from which to preserve structure, or None
        """
        if not context:
            context = self.detect_context(file_path)

        if not context:
            return None

        # Find where the matched pattern appears in the path
        file_path_str = str(file_path).lower()
        pattern_idx = file_path_str.find(context.matched_pattern.lower())

        if pattern_idx < 0:
            return None

        # Get the path up to and including the pattern
        path_up_to_pattern = str(file_path)[:pattern_idx + len(context.matched_pattern)]

        # Walk back to find the directory that contains the pattern
        parts = Path(path_up_to_pattern).parts

        # Return the parent directory that contains the matched pattern
        for i, part in enumerate(parts):
            if context.matched_pattern.strip('/').lower() in part.lower():
                # Return path from this point
                return Path(*parts[:i+1])

        return file_path.parent
