#!/usr/bin/env python3
"""
Test script to verify custom folder mapping configuration.
"""

from pathlib import Path
from config.folder_mapping import (
    get_custom_folder,
    is_structure_preserving_category,
    detect_video_subcategory,
    CATEGORY_FOLDER_MAP
)

def test_folder_mapping():
    """Test the folder mapping configuration."""
    print("=" * 70)
    print("FOLDER MAPPING TEST")
    print("=" * 70)
    print()

    # Test all category mappings
    print("📁 Category → Custom Folder Mappings:")
    print("-" * 70)
    for category, folder in CATEGORY_FOLDER_MAP.items():
        custom = get_custom_folder(category)
        preserves_structure = is_structure_preserving_category(category)
        structure_flag = " [PRESERVES STRUCTURE]" if preserves_structure else ""
        print(f"  {category:25s} → {folder:40s}{structure_flag}")
    print()

    # Test video subcategory detection
    print("🎥 Video Filename Pattern Detection:")
    print("-" * 70)
    test_filenames = [
        "SVR_Video_Recorder_001.mp4",
        "SVR_VIDEO_RECORDER_2024.mp4",
        "security_cam_front_door.mov",
        "clip001.mov",
        "clip_2024_11_14.mp4",
        "wolf_pack_hunting.mp4",
        "wolfvid_sunset.mov",
        "random_video.mp4",
        "vacation_2024.mp4"
    ]

    for filename in test_filenames:
        subcategory = detect_video_subcategory(filename)
        if subcategory:
            custom_folder = get_custom_folder(subcategory)
            print(f"  ✓ {filename:40s} → {subcategory:25s} → {custom_folder}")
        else:
            print(f"  ✗ {filename:40s} → video (default)")
    print()

    # Test structure preservation flags
    print("🔧 Structure Preservation Categories:")
    print("-" * 70)
    for category in ['code', 'backup', 'web', 'application', 'security_camera_video', 'wolf_video', 'document', 'image']:
        preserves = is_structure_preserving_category(category)
        flag = "✓ YES" if preserves else "✗ NO"
        print(f"  {category:25s} → {flag}")
    print()

    # Test example file paths
    print("📂 Example Destination Paths:")
    print("-" * 70)
    base_dir = Path("/organized")
    root_folder = "Documents"

    examples = [
        ("document", "report.docx", f"{base_dir}/{root_folder}/Docs/Word/report.docx"),
        ("presentation", "slides.pptx", f"{base_dir}/{root_folder}/Docs/PowerPoints/slides.pptx"),
        ("spreadsheet", "budget.xlsx", f"{base_dir}/{root_folder}/Docs/Spreadsheets/budget.xlsx"),
        ("image", "photo.jpg", f"{base_dir}/{root_folder}/Media/Images/photo.jpg"),
        ("audio", "song.mp3", f"{base_dir}/{root_folder}/Media/Music/song.mp3"),
        ("video", "movie.mp4", f"{base_dir}/{root_folder}/Media/Videos/movie.mp4"),
        ("security_camera_video", "SVR_Video_Recorder_001.mp4",
         f"{base_dir}/{root_folder}/Media/Videos/SecurityCameraVideos/SVR_Video_Recorder_001.mp4"),
        ("wolf_video", "clip001.mov", f"{base_dir}/{root_folder}/Media/Videos/WolfVids/clip001.mov"),
    ]

    for category, filename, expected_path in examples:
        custom_folder = get_custom_folder(category)
        if custom_folder:
            actual_path = base_dir / root_folder / str(custom_folder) / filename
        else:
            actual_path = base_dir / root_folder / category / filename

        match = "✓" if str(actual_path) == expected_path else "✗"
        print(f"  {match} {category:25s} {filename:30s}")
        print(f"     → {actual_path}")
        if str(actual_path) != expected_path:
            print(f"     ✗ Expected: {expected_path}")
    print()

    print("=" * 70)
    print("✅ Folder mapping test complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_folder_mapping()
