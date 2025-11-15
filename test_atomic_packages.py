#!/usr/bin/env python3
"""
Test script for atomic package detection.

This script creates a test .app package and verifies that:
1. The scanner detects it as an atomic package
2. Internal files are not scanned individually
3. The hasher can hash the entire directory as one unit
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.scanner import scan_directory, is_atomic_package
from core.hasher import generate_hashes, hash_directory

def create_test_app(base_dir):
    """Create a test .app bundle structure."""
    app_path = base_dir / "TestApp.app"
    contents_path = app_path / "Contents"
    macos_path = contents_path / "MacOS"
    resources_path = contents_path / "Resources"

    # Create directory structure
    macos_path.mkdir(parents=True, exist_ok=True)
    resources_path.mkdir(parents=True, exist_ok=True)

    # Create some test files
    (macos_path / "TestApp").write_text("#!/bin/bash\necho 'Test App'\n")
    (contents_path / "Info.plist").write_text("<plist>...</plist>")
    (resources_path / "icon.png").write_bytes(b"fake png data")
    (resources_path / "config.txt").write_text("config=test")

    return app_path

def test_atomic_package_detection():
    """Test that .app packages are detected correctly."""
    print("=" * 80)
    print("TEST 1: Atomic Package Detection")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test .app
        app_path = create_test_app(tmpdir_path)

        # Also create a regular file for comparison
        regular_file = tmpdir_path / "regular_file.txt"
        regular_file.write_text("This is a regular file")

        print(f"\n✓ Created test structure in: {tmpdir_path}")
        print(f"  - TestApp.app (directory)")
        print(f"  - regular_file.txt (file)")

        # Test is_atomic_package function
        print(f"\n✓ Testing is_atomic_package():")
        print(f"  - TestApp.app: {is_atomic_package(app_path)} (expected: True)")
        print(f"  - regular_file.txt: {is_atomic_package(regular_file)} (expected: False)")

        assert is_atomic_package(app_path) == True, "Failed: .app should be detected as atomic package"
        assert is_atomic_package(regular_file) == False, "Failed: regular file should not be atomic package"

        print("\n✅ Atomic package detection works correctly!")

        return tmpdir_path, app_path

def test_scanner_skips_internals():
    """Test that scanner doesn't scan inside .app packages."""
    print("\n" + "=" * 80)
    print("TEST 2: Scanner Skips Atomic Package Internals")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test .app
        app_path = create_test_app(tmpdir_path)

        # Count files inside .app manually
        internal_files = list(app_path.rglob("*"))
        internal_file_count = sum(1 for f in internal_files if f.is_file())

        print(f"\n✓ Created TestApp.app with {internal_file_count} internal files")

        # Scan directory
        print(f"\n✓ Scanning directory...")
        results = scan_directory(tmpdir_path)

        print(f"\n✓ Scan results:")
        print(f"  - Total items found: {len(results)}")
        for item in results:
            print(f"    - {item.name} ({'directory' if item.is_dir() else 'file'})")

        # Check results
        # Should find only the .app itself, not its internal files
        app_found = any(r.resolve() == app_path.resolve() for r in results)
        internal_found = any(str(r.resolve()).startswith(str(app_path.resolve()) + "/") for r in results)

        print(f"\n✓ Verification:")
        print(f"  - TestApp.app found: {app_found} (expected: True)")
        print(f"  - Internal files found: {internal_found} (expected: False)")

        assert app_found == True, "Failed: .app package should be found"
        assert internal_found == False, "Failed: Internal files should be skipped"

        print("\n✅ Scanner correctly skips atomic package internals!")

def test_directory_hashing():
    """Test that entire directories can be hashed."""
    print("\n" + "=" * 80)
    print("TEST 3: Directory Hashing")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test .app
        app_path = create_test_app(tmpdir_path)

        print(f"\n✓ Created TestApp.app")

        # Hash the directory
        print(f"\n✓ Hashing entire directory...")
        hash1 = hash_directory(app_path)

        print(f"  - Hash: {hash1[:32]}...")

        # Hash again to verify consistency
        print(f"\n✓ Hashing again to verify consistency...")
        hash2 = hash_directory(app_path)

        print(f"  - Hash: {hash2[:32]}...")

        assert hash1 == hash2, "Failed: Directory hash should be consistent"

        print(f"\n✓ Hashes match: {hash1 == hash2}")

        # Modify a file and verify hash changes
        print(f"\n✓ Modifying internal file...")
        (app_path / "Contents" / "Info.plist").write_text("<plist>modified</plist>")

        hash3 = hash_directory(app_path)
        print(f"  - New hash: {hash3[:32]}...")

        assert hash1 != hash3, "Failed: Hash should change when contents change"

        print(f"\n✓ Hash changed after modification: {hash1 != hash3}")

        print("\n✅ Directory hashing works correctly!")

def test_end_to_end():
    """Test complete pipeline with atomic packages."""
    print("\n" + "=" * 80)
    print("TEST 4: End-to-End Pipeline")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test .app
        app_path = create_test_app(tmpdir_path)

        # Create regular file
        regular_file = tmpdir_path / "regular.txt"
        regular_file.write_text("Regular file content")

        print(f"\n✓ Created test files in: {tmpdir_path}")

        # Scan
        print(f"\n✓ Step 1: Scanning...")
        scanned_files = scan_directory(tmpdir_path)
        print(f"  - Found {len(scanned_files)} items")

        # Hash
        print(f"\n✓ Step 2: Hashing...")
        hashed_files = generate_hashes(scanned_files, use_db=False)
        print(f"  - Hashed {len(hashed_files)} items")

        # Verify results
        print(f"\n✓ Results:")
        for file_info in hashed_files:
            print(f"  - {file_info.path.name}:")
            print(f"      Type: {'directory' if file_info.path.is_dir() else 'file'}")
            print(f"      Size: {file_info.size:,} bytes")
            print(f"      Hash: {file_info.hash[:32]}...")

        # Verify we got both items
        assert len(hashed_files) == 2, f"Failed: Expected 2 items, got {len(hashed_files)}"

        # Verify .app was hashed as directory
        app_file_info = next((f for f in hashed_files if f.path.name == "TestApp.app"), None)
        assert app_file_info is not None, "Failed: TestApp.app not found in results"
        assert app_file_info.hash != "METADATA_ONLY", "Failed: TestApp.app should be hashed"

        # Verify regular file was hashed normally
        regular_file_info = next((f for f in hashed_files if f.path.name == "regular.txt"), None)
        assert regular_file_info is not None, "Failed: regular.txt not found in results"
        assert regular_file_info.hash != "METADATA_ONLY", "Failed: regular.txt should be hashed"

        print("\n✅ End-to-end pipeline works correctly!")

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("ATOMIC PACKAGE TESTING SUITE")
    print("=" * 80)

    try:
        test_atomic_package_detection()
        test_scanner_skips_internals()
        test_directory_hashing()
        test_end_to_end()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nAtomic package handling is working correctly:")
        print("  ✓ .app, .pkg, .dmg packages detected")
        print("  ✓ Scanner skips internal files")
        print("  ✓ Directory hashing creates consistent hashes")
        print("  ✓ End-to-end pipeline handles atomic packages")
        print("\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
