#!/usr/bin/env python3
"""
Test script for image metadata extraction.

Shows all available metadata that can be extracted from images.
Helps user see what metadata is available and decide what to use.
"""

from pathlib import Path
from core.image_analyzer import ImageAnalyzer, ImageMetadata
import json
from datetime import datetime


def format_metadata_display(metadata: ImageMetadata) -> str:
    """Format metadata for display."""
    output = []

    output.append("=" * 80)
    output.append(f"IMAGE METADATA ANALYSIS: {metadata.file_path.name}")
    output.append("=" * 80)
    output.append("")

    # File Information
    output.append("📁 FILE INFORMATION")
    output.append("-" * 80)
    output.append(f"  Path: {metadata.file_path}")
    output.append(f"  Size: {metadata.file_size:,} bytes ({metadata.file_size / (1024*1024):.2f} MB)")
    output.append(f"  Hash (SHA256): {metadata.file_hash[:32]}...")
    if metadata.file_created:
        output.append(f"  Created: {metadata.file_created.strftime('%Y-%m-%d %H:%M:%S')}")
    if metadata.file_modified:
        output.append(f"  Modified: {metadata.file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("")

    # Image Properties
    output.append("🖼️  IMAGE PROPERTIES")
    output.append("-" * 80)
    if metadata.width and metadata.height:
        output.append(f"  Dimensions: {metadata.width} x {metadata.height} pixels")
        megapixels = (metadata.width * metadata.height) / 1_000_000
        output.append(f"  Megapixels: {megapixels:.1f} MP")
    if metadata.format:
        output.append(f"  Format: {metadata.format}")
    if metadata.mode:
        output.append(f"  Color Mode: {metadata.mode}")
    if metadata.color_space:
        output.append(f"  Color Space: {metadata.color_space}")
    if metadata.bit_depth:
        output.append(f"  Bit Depth: {metadata.bit_depth} bits")
    if metadata.dpi:
        output.append(f"  DPI: {metadata.dpi}")
    output.append(f"  Has Transparency: {'Yes' if metadata.has_transparency else 'No'}")
    output.append("")

    # Camera Information
    if any([metadata.camera_make, metadata.camera_model, metadata.lens_make, metadata.lens_model]):
        output.append("📷 CAMERA INFORMATION")
        output.append("-" * 80)
        if metadata.camera_make:
            output.append(f"  Camera Make: {metadata.camera_make}")
        if metadata.camera_model:
            output.append(f"  Camera Model: {metadata.camera_model}")
        if metadata.lens_make:
            output.append(f"  Lens Make: {metadata.lens_make}")
        if metadata.lens_model:
            output.append(f"  Lens Model: {metadata.lens_model}")
        output.append("")

    # Camera Settings
    settings_exist = any([
        metadata.date_taken, metadata.iso_speed, metadata.exposure_time,
        metadata.f_number, metadata.focal_length, metadata.flash,
        metadata.white_balance, metadata.metering_mode
    ])
    if settings_exist:
        output.append("⚙️  CAMERA SETTINGS")
        output.append("-" * 80)
        if metadata.date_taken:
            output.append(f"  Date Taken: {metadata.date_taken.strftime('%Y-%m-%d %H:%M:%S')}")
        if metadata.date_digitized:
            output.append(f"  Date Digitized: {metadata.date_digitized.strftime('%Y-%m-%d %H:%M:%S')}")
        if metadata.iso_speed:
            output.append(f"  ISO Speed: {metadata.iso_speed}")
        if metadata.exposure_time:
            output.append(f"  Exposure Time: {metadata.exposure_time} sec")
        if metadata.f_number:
            output.append(f"  F-Number (Aperture): f/{metadata.f_number}")
        if metadata.focal_length:
            output.append(f"  Focal Length: {metadata.focal_length} mm")
        if metadata.flash:
            output.append(f"  Flash: {metadata.flash}")
        if metadata.white_balance:
            output.append(f"  White Balance: {metadata.white_balance}")
        if metadata.metering_mode:
            output.append(f"  Metering Mode: {metadata.metering_mode}")
        if metadata.exposure_program:
            output.append(f"  Exposure Program: {metadata.exposure_program}")
        if metadata.exposure_bias:
            output.append(f"  Exposure Bias: {metadata.exposure_bias}")
        if metadata.orientation:
            output.append(f"  Orientation: {metadata.orientation}")
        output.append("")

    # GPS Location
    if any([metadata.gps_latitude, metadata.gps_longitude, metadata.gps_altitude]):
        output.append("📍 GPS LOCATION")
        output.append("-" * 80)
        if metadata.gps_latitude:
            output.append(f"  Latitude: {metadata.gps_latitude:.6f}°")
        if metadata.gps_longitude:
            output.append(f"  Longitude: {metadata.gps_longitude:.6f}°")
        if metadata.gps_latitude and metadata.gps_longitude:
            # Google Maps link
            gmaps_link = f"https://www.google.com/maps?q={metadata.gps_latitude},{metadata.gps_longitude}"
            output.append(f"  Google Maps: {gmaps_link}")
        if metadata.gps_altitude:
            output.append(f"  Altitude: {metadata.gps_altitude:.1f} meters")
        if metadata.gps_timestamp:
            output.append(f"  GPS Timestamp: {metadata.gps_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if metadata.gps_location_name:
            output.append(f"  Location Name: {metadata.gps_location_name}")
        output.append("")

    # Copyright & Creator
    copyright_exists = any([
        metadata.copyright, metadata.creator, metadata.credit,
        metadata.caption, metadata.title, metadata.keywords
    ])
    if copyright_exists:
        output.append("©️  COPYRIGHT & CREATOR")
        output.append("-" * 80)
        if metadata.copyright:
            output.append(f"  Copyright: {metadata.copyright}")
        if metadata.creator:
            output.append(f"  Creator/Artist: {metadata.creator}")
        if metadata.credit:
            output.append(f"  Credit: {metadata.credit}")
        if metadata.title:
            output.append(f"  Title: {metadata.title}")
        if metadata.caption:
            output.append(f"  Caption: {metadata.caption}")
        if metadata.keywords:
            output.append(f"  Keywords: {', '.join(metadata.keywords)}")
        output.append("")

    # Software & Quality
    quality_exists = any([
        metadata.software, metadata.compression, metadata.quality, metadata.rating
    ])
    if quality_exists:
        output.append("🔧 SOFTWARE & QUALITY")
        output.append("-" * 80)
        if metadata.software:
            output.append(f"  Software: {metadata.software}")
        if metadata.compression:
            output.append(f"  Compression: {metadata.compression}")
        if metadata.quality:
            output.append(f"  Quality: {metadata.quality}/100")
        if metadata.rating:
            stars = "⭐" * metadata.rating
            output.append(f"  Rating: {stars} ({metadata.rating}/5)")
        output.append("")

    # Raw EXIF Data
    if metadata.raw_exif:
        output.append("🔍 RAW EXIF DATA (All Available Tags)")
        output.append("-" * 80)
        for key, value in sorted(metadata.raw_exif.items()):
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            output.append(f"  {key}: {value_str}")
        output.append("")

    # Errors
    if metadata.errors:
        output.append("⚠️  ERRORS DURING ANALYSIS")
        output.append("-" * 80)
        for error in metadata.errors:
            output.append(f"  ❌ {error}")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


def test_image_files():
    """Test image metadata extraction on sample files."""
    analyzer = ImageAnalyzer()

    print("=" * 80)
    print("IMAGE METADATA EXTRACTION TEST")
    print("=" * 80)
    print()

    # Find sample images to test
    search_paths = [
        Path.home() / "Pictures",
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
    ]

    sample_images = []
    for search_path in search_paths:
        if search_path.exists():
            for ext in ['.jpg', '.jpeg', '.png', '.heic']:
                sample_images.extend(list(search_path.glob(f"**/*{ext}"))[:5])
            if sample_images:
                break

    if not sample_images:
        print("⚠️  No sample images found in standard locations.")
        print("   Please provide a path to an image file:")
        print()
        print("   Usage: .venv/bin/python test_image_metadata.py /path/to/image.jpg")
        return

    print(f"Found {len(sample_images)} sample images to analyze")
    print()

    # Analyze each image
    for i, image_path in enumerate(sample_images[:3], 1):  # Limit to 3 samples
        print(f"\n{'='*80}")
        print(f"SAMPLE {i}/{min(3, len(sample_images))}")
        print(f"{'='*80}\n")

        try:
            metadata = analyzer.analyze(image_path)
            if metadata:
                print(format_metadata_display(metadata))

                # Show summary
                summary = analyzer.get_metadata_summary(metadata)
                print("\n📊 METADATA SUMMARY (JSON Format):")
                print("-" * 80)
                print(json.dumps(summary, indent=2, default=str))
                print()
            else:
                print(f"❌ Could not analyze {image_path.name}")

        except Exception as e:
            print(f"❌ Error analyzing {image_path.name}: {e}")

    print("\n" + "=" * 80)
    print("✅ Image metadata test complete!")
    print("=" * 80)
    print()
    print("💡 What metadata is available:")
    print("-" * 80)
    print("  ✅ File info: size, hash, timestamps")
    print("  ✅ Image properties: dimensions, format, color mode, DPI")
    print("  ✅ Camera info: make, model, lens")
    print("  ✅ Camera settings: ISO, aperture, shutter speed, focal length")
    print("  ✅ GPS location: latitude, longitude, altitude")
    print("  ✅ Copyright: creator, caption, keywords, title")
    print("  ✅ Software: editing software, rating, quality")
    print("  ✅ Raw EXIF: ALL available EXIF tags")
    print()
    print("📋 Next steps:")
    print("-" * 80)
    print("  1. Apply database migration:")
    print("     mysql -u jarheads_0231 -p < database/migrations/add_image_metadata_tables.sql")
    print()
    print("  2. Enable image analysis in main.py (add --analyze-images flag)")
    print()
    print("  3. Run organization with image analysis:")
    print("     .venv/bin/python main.py /path/to/images --base-dir /organized --analyze-images")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test specific image
        image_path = Path(sys.argv[1])
        if image_path.exists():
            analyzer = ImageAnalyzer()
            metadata = analyzer.analyze(image_path)
            if metadata:
                print(format_metadata_display(metadata))
                summary = analyzer.get_metadata_summary(metadata)
                print("\n📊 METADATA SUMMARY (JSON):")
                print("-" * 80)
                print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"❌ File not found: {image_path}")
    else:
        # Test sample images
        test_image_files()
