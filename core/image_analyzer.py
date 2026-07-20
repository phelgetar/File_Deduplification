#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: image_analyzer.py
# Purpose: Extract comprehensive metadata from image files
#
# Description:
# Extracts all available metadata from images including:
# - EXIF data (camera settings, GPS, dates, lens info)
# - IPTC data (captions, keywords, copyright)
# - XMP data (Adobe metadata, ratings)
# - Image properties (dimensions, format, color mode, DPI)
# - File metadata (timestamps, size)
# - Optional: AI content analysis (faces, objects, scenes)
#
# Author: Tim Canady
# Created: 2025-11-14
#
# Version: 1.0.0
# Last Modified: 2025-11-14 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-14): Initial image metadata analyzer — Tim Canady
###################################################################

from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import hashlib

# Image processing libraries
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from PIL import IptcImagePlugin
    IPTC_AVAILABLE = True
except ImportError:
    IPTC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Complete metadata for an image file."""

    # Basic file info
    file_path: Path
    file_size: int
    file_hash: str

    # Image properties
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    mode: Optional[str] = None  # RGB, RGBA, L (grayscale), etc.
    color_space: Optional[str] = None
    dpi: Optional[tuple] = None
    bit_depth: Optional[int] = None
    has_transparency: bool = False

    # EXIF metadata
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_make: Optional[str] = None
    lens_model: Optional[str] = None

    # Camera settings
    date_taken: Optional[datetime] = None
    date_digitized: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    iso_speed: Optional[int] = None
    exposure_time: Optional[str] = None
    f_number: Optional[float] = None
    focal_length: Optional[float] = None
    flash: Optional[str] = None
    white_balance: Optional[str] = None
    metering_mode: Optional[str] = None
    exposure_program: Optional[str] = None
    exposure_bias: Optional[float] = None

    # GPS data
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None
    gps_timestamp: Optional[datetime] = None
    gps_location_name: Optional[str] = None

    # IPTC/Copyright
    copyright: Optional[str] = None
    creator: Optional[str] = None
    credit: Optional[str] = None
    caption: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    title: Optional[str] = None

    # Software/Processing
    software: Optional[str] = None
    orientation: Optional[int] = None

    # Quality indicators
    compression: Optional[str] = None
    quality: Optional[int] = None  # 0-100 for JPEG

    # XMP/Rating
    rating: Optional[int] = None  # 0-5 stars

    # File timestamps
    file_created: Optional[datetime] = None
    file_modified: Optional[datetime] = None

    # Raw EXIF (for debugging/analysis)
    raw_exif: Dict[str, Any] = field(default_factory=dict)

    # Errors during extraction
    errors: List[str] = field(default_factory=list)


class ImageAnalyzer:
    """
    Comprehensive image metadata analyzer.

    Extracts all available metadata from image files including EXIF,
    IPTC, XMP, and image properties.
    """

    def __init__(self):
        """Initialize the image analyzer."""
        if not PIL_AVAILABLE:
            logger.warning("PIL/Pillow not available - image analysis disabled")
            raise ImportError("PIL/Pillow required for image analysis")

        self.supported_formats = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            '.webp', '.heic', '.heif', '.raw', '.cr2', '.nef', '.dng'
        }

    def can_analyze(self, file_path: Path) -> bool:
        """
        Check if file can be analyzed.

        Args:
            file_path: Path to image file

        Returns:
            True if file can be analyzed
        """
        return file_path.suffix.lower() in self.supported_formats

    def analyze(self, file_path: Path) -> Optional[ImageMetadata]:
        """
        Extract all available metadata from an image.

        Args:
            file_path: Path to image file

        Returns:
            ImageMetadata object with all extracted data, or None if failed
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        if not self.can_analyze(file_path):
            logger.debug(f"Unsupported image format: {file_path.suffix}")
            return None

        # Initialize metadata object
        metadata = ImageMetadata(
            file_path=file_path,
            file_size=file_path.stat().st_size,
            file_hash=self._calculate_hash(file_path)
        )

        try:
            # Open image
            with Image.open(file_path) as img:
                # Extract basic image properties
                self._extract_image_properties(img, metadata)

                # Extract EXIF data
                if hasattr(img, '_getexif') and img._getexif():
                    self._extract_exif(img, metadata)
                elif hasattr(img, 'getexif'):
                    exif = img.getexif()
                    if exif:
                        self._extract_exif_pil(exif, metadata)

                # Extract IPTC data
                if IPTC_AVAILABLE:
                    self._extract_iptc(img, metadata)

        except Exception as e:
            error_msg = f"Error analyzing {file_path.name}: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

        # Extract file timestamps
        self._extract_file_timestamps(file_path, metadata)

        return metadata

    def _calculate_hash(self, file_path: Path, chunk_size: int = 65536) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def _extract_image_properties(self, img: Image.Image, metadata: ImageMetadata):
        """Extract basic image properties."""
        try:
            metadata.width = img.width
            metadata.height = img.height
            metadata.format = img.format
            metadata.mode = img.mode
            metadata.color_space = img.mode

            # DPI
            if 'dpi' in img.info:
                metadata.dpi = img.info['dpi']

            # Transparency
            metadata.has_transparency = (
                img.mode == 'RGBA' or
                img.mode == 'LA' or
                (img.mode == 'P' and 'transparency' in img.info)
            )

            # Bit depth
            if img.mode == 'L':
                metadata.bit_depth = 8
            elif img.mode == 'RGB':
                metadata.bit_depth = 24
            elif img.mode == 'RGBA':
                metadata.bit_depth = 32
            elif img.mode == '1':
                metadata.bit_depth = 1

        except Exception as e:
            error_msg = f"Error extracting image properties: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def _extract_exif_pil(self, exif, metadata: ImageMetadata):
        """Extract EXIF data using PIL's getexif() method."""
        try:
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)

                # Store in raw_exif
                metadata.raw_exif[tag_name] = value

                # Extract specific fields
                if tag_name == 'Make':
                    metadata.camera_make = str(value).strip()
                elif tag_name == 'Model':
                    metadata.camera_model = str(value).strip()
                elif tag_name == 'LensMake':
                    metadata.lens_make = str(value).strip()
                elif tag_name == 'LensModel':
                    metadata.lens_model = str(value).strip()
                elif tag_name == 'DateTime':
                    metadata.date_taken = self._parse_exif_date(value)
                elif tag_name == 'DateTimeOriginal':
                    metadata.date_taken = self._parse_exif_date(value)
                elif tag_name == 'DateTimeDigitized':
                    metadata.date_digitized = self._parse_exif_date(value)
                elif tag_name == 'ISOSpeedRatings' or tag_name == 'ISO':
                    metadata.iso_speed = int(value) if value else None
                elif tag_name == 'ExposureTime':
                    metadata.exposure_time = str(value)
                elif tag_name == 'FNumber':
                    metadata.f_number = float(value)
                elif tag_name == 'FocalLength':
                    metadata.focal_length = float(value)
                elif tag_name == 'Flash':
                    metadata.flash = str(value)
                elif tag_name == 'WhiteBalance':
                    metadata.white_balance = str(value)
                elif tag_name == 'MeteringMode':
                    metadata.metering_mode = str(value)
                elif tag_name == 'ExposureProgram':
                    metadata.exposure_program = str(value)
                elif tag_name == 'ExposureBiasValue':
                    metadata.exposure_bias = float(value)
                elif tag_name == 'Software':
                    metadata.software = str(value)
                elif tag_name == 'Orientation':
                    metadata.orientation = int(value)
                elif tag_name == 'Copyright':
                    metadata.copyright = str(value)
                elif tag_name == 'Artist':
                    metadata.creator = str(value)
                elif tag_name == 'Rating':
                    metadata.rating = int(value)

                # GPS data
                elif tag_name == 'GPSInfo':
                    self._extract_gps(value, metadata)

        except Exception as e:
            error_msg = f"Error extracting EXIF: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def _extract_exif(self, img: Image.Image, metadata: ImageMetadata):
        """Extract EXIF data (legacy method for older PIL versions)."""
        try:
            exif = img._getexif()
            if exif:
                self._extract_exif_pil(exif, metadata)
        except Exception as e:
            error_msg = f"Error extracting EXIF (legacy): {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def _extract_gps(self, gps_info, metadata: ImageMetadata):
        """Extract GPS coordinates from EXIF GPS data."""
        try:
            gps_data = {}
            for tag_id, value in gps_info.items():
                tag_name = GPSTAGS.get(tag_id, tag_id)
                gps_data[tag_name] = value

            # Extract latitude
            if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                lat = gps_data['GPSLatitude']
                lat_ref = gps_data['GPSLatitudeRef']
                metadata.gps_latitude = self._convert_to_degrees(lat, lat_ref)

            # Extract longitude
            if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                lon = gps_data['GPSLongitude']
                lon_ref = gps_data['GPSLongitudeRef']
                metadata.gps_longitude = self._convert_to_degrees(lon, lon_ref)

            # Extract altitude
            if 'GPSAltitude' in gps_data:
                altitude = gps_data['GPSAltitude']
                metadata.gps_altitude = float(altitude)

            # Extract GPS timestamp
            if 'GPSTimeStamp' in gps_data and 'GPSDateStamp' in gps_data:
                time_parts = gps_data['GPSTimeStamp']
                date_str = gps_data['GPSDateStamp']
                try:
                    timestamp_str = f"{date_str} {time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
                    metadata.gps_timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S")
                except:
                    pass

        except Exception as e:
            error_msg = f"Error extracting GPS: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def _convert_to_degrees(self, value, ref):
        """Convert GPS coordinates to degrees."""
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])

            degrees = d + (m / 60.0) + (s / 3600.0)

            if ref in ['S', 'W']:
                degrees = -degrees

            return degrees
        except:
            return None

    def _extract_iptc(self, img: Image.Image, metadata: ImageMetadata):
        """Extract IPTC metadata (captions, keywords, copyright)."""
        try:
            if hasattr(img, 'app') and 'APP13' in img.app:
                iptc = IptcImagePlugin.getiptcinfo(img)

                if iptc:
                    # Caption
                    if (2, 120) in iptc:
                        metadata.caption = iptc[(2, 120)].decode('utf-8', errors='ignore')

                    # Keywords
                    if (2, 25) in iptc:
                        keywords = iptc[(2, 25)]
                        if isinstance(keywords, bytes):
                            metadata.keywords = [keywords.decode('utf-8', errors='ignore')]
                        elif isinstance(keywords, list):
                            metadata.keywords = [k.decode('utf-8', errors='ignore') if isinstance(k, bytes) else k for k in keywords]

                    # Copyright
                    if (2, 116) in iptc:
                        metadata.copyright = iptc[(2, 116)].decode('utf-8', errors='ignore')

                    # Creator
                    if (2, 80) in iptc:
                        metadata.creator = iptc[(2, 80)].decode('utf-8', errors='ignore')

                    # Credit
                    if (2, 110) in iptc:
                        metadata.credit = iptc[(2, 110)].decode('utf-8', errors='ignore')

                    # Title
                    if (2, 5) in iptc:
                        metadata.title = iptc[(2, 5)].decode('utf-8', errors='ignore')

        except Exception as e:
            error_msg = f"Error extracting IPTC: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def _parse_exif_date(self, date_str) -> Optional[datetime]:
        """Parse EXIF date string to datetime object."""
        if not date_str:
            return None

        try:
            # EXIF date format: "YYYY:MM:DD HH:MM:SS"
            return datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
        except:
            try:
                # Try alternate format
                return datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
            except:
                return None

    def _extract_file_timestamps(self, file_path: Path, metadata: ImageMetadata):
        """Extract file system timestamps."""
        try:
            stat = file_path.stat()
            metadata.file_created = datetime.fromtimestamp(stat.st_ctime)
            metadata.file_modified = datetime.fromtimestamp(stat.st_mtime)
        except Exception as e:
            error_msg = f"Error extracting file timestamps: {e}"
            logger.error(error_msg)
            metadata.errors.append(error_msg)

    def get_metadata_summary(self, metadata: ImageMetadata) -> Dict[str, Any]:
        """
        Get a summary of the most important metadata fields.

        Args:
            metadata: ImageMetadata object

        Returns:
            Dictionary with summary of key fields
        """
        summary = {
            'basic': {
                'format': metadata.format,
                'dimensions': f"{metadata.width}x{metadata.height}" if metadata.width else None,
                'size_mb': round(metadata.file_size / (1024 * 1024), 2),
                'color_mode': metadata.mode,
            },
            'camera': {
                'make': metadata.camera_make,
                'model': metadata.camera_model,
                'lens': metadata.lens_model,
            },
            'settings': {
                'date_taken': metadata.date_taken.isoformat() if metadata.date_taken else None,
                'iso': metadata.iso_speed,
                'exposure': metadata.exposure_time,
                'f_stop': metadata.f_number,
                'focal_length': metadata.focal_length,
            },
            'location': {
                'latitude': metadata.gps_latitude,
                'longitude': metadata.gps_longitude,
                'altitude': metadata.gps_altitude,
            },
            'copyright': {
                'copyright': metadata.copyright,
                'creator': metadata.creator,
                'caption': metadata.caption,
                'keywords': metadata.keywords,
            }
        }

        return summary
