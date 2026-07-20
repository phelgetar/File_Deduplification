#!/usr/bin/env python3
"""
Debug script to test file classification
"""

from pathlib import Path
from models.file_info import FileInfo
from core.classifier import classify_file
from utils.path_metadata import extract_path_metadata
from config.folder_mapping import get_custom_folder

# Test the problematic file
test_path = Path('/Users/canadytw/Documents/Documents - 42739/Google Drive/Google Photos/IMG_0969.JPG')

print("="*80)
print("CLASSIFICATION DEBUG")
print("="*80)
print(f"\nTest file: {test_path.name}")
print(f"Full path: {test_path}")
print(f"Extension: {test_path.suffix}")
print(f"Exists: {test_path.exists()}")

# Extract path metadata
print("\n" + "="*80)
print("PATH METADATA")
print("="*80)
path_metadata = extract_path_metadata(test_path)
for key, value in path_metadata.items():
    print(f"  {key}: {value}")

# Create FileInfo
file_info = FileInfo(
    path=test_path,
    size=100000,
    hash=None,
    type=None,
    owner=None,
    year=None,
    path_metadata=path_metadata
)

# Classify it
print("\n" + "="*80)
print("CLASSIFICATION")
print("="*80)
print("Before classification:")
print(f"  file_info.type: {file_info.type}")

classified = classify_file(file_info, use_db=False)

print("\nAfter classification:")
print(f"  file_info.type: {classified.type}")

# Check folder mapping
print("\n" + "="*80)
print("FOLDER MAPPING")
print("="*80)
custom_folder = get_custom_folder(classified.type)
print(f"  Category: {classified.type}")
print(f"  Custom folder: {custom_folder}")

# Check if it's being treated as structure-preserving
print("\n" + "="*80)
print("STRUCTURE PRESERVATION CHECK")
print("="*80)
from config.folder_mapping import is_structure_preserving_category
is_preserving = is_structure_preserving_category(classified.type)
print(f"  Is structure-preserving: {is_preserving}")

# Simulate organization path
print("\n" + "="*80)
print("EXPECTED ORGANIZATION PATH")
print("="*80)
base_dir = Path("/Users/canadytw/organized/Documents/Documents - 42739")
root_folder = path_metadata.get('root_folder')

print(f"  Base dir: {base_dir}")
print(f"  Root folder: {root_folder}")

# Check if root folder should be added
base_dir_str = str(base_dir)
should_add_root = root_folder and not base_dir_str.endswith(root_folder)
print(f"  Should add root folder: {should_add_root}")

# Build expected path
subfolders = []
if should_add_root:
    subfolders.append(root_folder)
if custom_folder:
    subfolders.append(str(custom_folder))
else:
    subfolders.append(classified.type)

expected_path = base_dir.joinpath(*subfolders, test_path.name)
print(f"\n  Expected destination: {expected_path}")

print("\n" + "="*80)
