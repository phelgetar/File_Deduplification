#!/usr/bin/env python3
"""
Test script for semantic context detection.

Tests the new context-based organization system to ensure files are
organized by semantic context rather than just file type.
"""

from pathlib import Path
from core.context_detector import ContextDetector
from models.file_info import FileInfo

def test_context_detection():
    """Test context detection with real-world examples."""
    print("=" * 80)
    print("CONTEXT DETECTION TEST")
    print("=" * 80)
    print()

    # Initialize detector
    config_path = Path("config/semantic_paths.yaml")
    detector = ContextDetector(config_path)

    # Test cases: (file_path, expected_context, description)
    test_cases = [
        # Personal - Disability/VA (Your MRI example)
        (
            "/Users/canadytw/Documents/Documents - 42739/Google Drive/personal/Disability/"
            "VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020/DICOM/SERIES_4/95934524.dcm",
            "Personal - Disability/VA",
            "MRI DICOM file (YOUR EXAMPLE)"
        ),
        (
            "/Documents/personal/Disability/medical_records/2020/claim_form.pdf",
            "Personal - Disability/VA",
            "VA disability claim form"
        ),
        (
            "/Documents/medical/VA/appointments/2024/records.pdf",
            "Personal - Disability/VA",
            "VA medical appointment records"
        ),

        # Work files
        (
            "/Documents/Work-Info/scripts/backup_database.py",
            "Work",
            "Work automation script"
        ),
        (
            "/Documents/AFCAM/reports/2024/quarterly_report.pdf",
            "Work",
            "AFCAM work report"
        ),
        (
            "/Documents/Work-Info/SCC/documentation/guide.docx",
            "Work",
            "SCC documentation"
        ),

        # Education files
        (
            "/Documents/Education/CEG3310/Labs/Lab1/report.pdf",
            "Education",
            "CEG3310 lab report"
        ),
        (
            "/Documents/MIT-Sloan/AI_Course/week1/assignment.pdf",
            "Education",
            "MIT-Sloan course assignment"
        ),
        (
            "/Documents/Wright-State-University/CS_Courses/project.zip",
            "Education",
            "Wright State University project"
        ),

        # Family files
        (
            "/Documents/Dad/photos/vacation/2020/beach_photo.jpg",
            "Personal/Family",
            "Dad's vacation photo"
        ),
        (
            "/Documents/family/documents/birth_certificate.pdf",
            "Personal/Family",
            "Family document"
        ),

        # Hobbies
        (
            "/Documents/HAM-Radio-Survival/antennas/design.pdf",
            "Hobbies",
            "HAM radio antenna design"
        ),
        (
            "/Documents/Arduino/projects/LED_controller/code.ino",
            "Hobbies",
            "Arduino project"
        ),

        # Archived documents
        (
            "/Documents/Documents - 42739/Google Drive/work/file.pdf",
            "Archives",
            "Archived from Documents - 42739"
        ),
        (
            "/Documents/Documents - 2996KD/old_projects/project.zip",
            "Archives",
            "Archived from Documents - 2996KD"
        ),

        # Files that should NOT match any context (fallback to file type)
        (
            "/Documents/random_report.pdf",
            None,
            "Random PDF (no context - should use file type classification)"
        ),
        (
            "/Desktop/vacation_photo.jpg",
            None,
            "Random photo (no context - should use file type classification)"
        ),
    ]

    # Run tests
    print("🔍 Testing Context Detection:")
    print("-" * 80)

    passed = 0
    failed = 0

    for file_path, expected_context, description in test_cases:
        path = Path(file_path)
        context = detector.detect_context(path)

        if expected_context is None:
            # Should NOT detect context
            if context is None:
                status = "✅ PASS"
                passed += 1
            else:
                status = f"❌ FAIL (detected: {context.context_name})"
                failed += 1
        else:
            # Should detect context
            if context and context.context_name == expected_context:
                status = "✅ PASS"
                passed += 1
            else:
                detected = context.context_name if context else "None"
                status = f"❌ FAIL (detected: {detected}, expected: {expected_context})"
                failed += 1

        print(f"\n{status}")
        print(f"  Description: {description}")
        print(f"  File: {path.name}")
        print(f"  Path: ...{str(path)[-60:]}")
        if context:
            print(f"  → Context: {context.context_name}")
            print(f"  → Destination: {context.destination}")
            print(f"  → Pattern: {context.matched_pattern}")
            print(f"  → Priority: {context.priority}")
            if context.metadata:
                print(f"  → Metadata: {context.metadata}")

    print()
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    print("=" * 80)
    print()

    # Test metadata extraction
    print("=" * 80)
    print("METADATA EXTRACTION TEST")
    print("=" * 80)
    print()

    mri_path = Path(
        "/personal/Disability/VA_IMG_CANADY_MRI_CERVICAL_SPINE_W_O_CONTRAST_15SEP2020/"
        "DICOM/SERIES_4/95934524.dcm"
    )

    print(f"File: {mri_path}")
    print()

    metadata = detector.extract_metadata_from_path(mri_path)
    print("📊 Extracted Metadata:")
    print("-" * 80)
    for key, value in metadata.items():
        print(f"  {key:20s} → {value}")

    if not metadata:
        print("  (no metadata extracted)")

    print()
    print("=" * 80)
    print()

    # Test project detection
    print("=" * 80)
    print("PROJECT DETECTION TEST")
    print("=" * 80)
    print()

    project_test_cases = [
        (
            "/Documents/personal/Disability/VA_IMG/DICOM/SERIES_4/file.dcm",
            "DICOM Medical Images",
            "DICOM medical imaging"
        ),
        (
            "/Documents/code/myproject/.git/config",
            "Code Projects",
            "Git repository"
        ),
        (
            "/Documents/code/myproject/package.json",
            "Code Projects",
            "Node.js project"
        ),
        (
            "/Documents/code/myapp/requirements.txt",
            "Code Projects",
            "Python project"
        ),
    ]

    print("🔍 Testing Project Detection:")
    print("-" * 80)

    for file_path, expected_project, description in project_test_cases:
        path = Path(file_path)
        project = detector.detect_project(path)

        if project:
            status = "✅" if project.project_type == expected_project else "❌"
            print(f"\n{status} {description}")
            print(f"  File: {path.name}")
            print(f"  Path: ...{str(path)[-60:]}")
            print(f"  → Project: {project.project_type}")
            print(f"  → Preserve: {project.preserve_mode}")
            print(f"  → Priority: {project.priority}")
            print(f"  → Patterns: {project.matched_patterns}")
        else:
            print(f"\n❌ {description}")
            print(f"  File: {path.name}")
            print(f"  Path: ...{str(path)[-60:]}")
            print(f"  → No project detected!")

    print()
    print("=" * 80)
    print("✅ Context detection test complete!")
    print("=" * 80)
    print()

    return passed == len(test_cases)


if __name__ == "__main__":
    success = test_context_detection()
    exit(0 if success else 1)
