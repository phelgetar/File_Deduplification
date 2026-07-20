#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: image_db.py
# Purpose: Database persistence for image metadata
#
# Description:
# Handles saving and retrieving image metadata from the database.
# Includes ORM models for image_metadata, image_keywords, image_exif_raw,
# and image_analysis_errors tables. Provides functions to save complete
# ImageMetadata objects to the database.
#
# Author: Tim Canady
# Created: 2025-11-15
#
# Version: 1.0.0
# Last Modified: 2025-11-15 by Tim Canady
#
# Revision History:
# - 1.0.0 (2025-11-15): Initial image metadata database persistence — Tim Canady
###################################################################

from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text, Float, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from core.db import Base, Session, engine
from core.image_analyzer import ImageMetadata

logger = logging.getLogger(__name__)


# --- ORM Models ---

class ImageMetadataDB(Base):
    """Image metadata table - stores comprehensive metadata for image files."""
    __tablename__ = 'image_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(BigInteger, nullable=False)

    # Basic Image Properties
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String(20))
    mode = Column(String(20))
    color_space = Column(String(50))
    dpi_x = Column(Float)
    dpi_y = Column(Float)
    bit_depth = Column(Integer)
    has_transparency = Column(Boolean, default=False)

    # Camera Information
    camera_make = Column(String(255))
    camera_model = Column(String(255))
    lens_make = Column(String(255))
    lens_model = Column(String(255))

    # Camera Settings
    date_taken = Column(DateTime)
    date_digitized = Column(DateTime)
    date_modified = Column(DateTime)
    iso_speed = Column(Integer)
    exposure_time = Column(String(50))
    f_number = Column(Float)
    focal_length = Column(Float)
    flash = Column(String(100))
    white_balance = Column(String(100))
    metering_mode = Column(String(100))
    exposure_program = Column(String(100))
    exposure_bias = Column(Float)

    # GPS Location Data
    gps_latitude = Column(DECIMAL(10, 8))
    gps_longitude = Column(DECIMAL(11, 8))
    gps_altitude = Column(Float)
    gps_timestamp = Column(DateTime)
    gps_location_name = Column(String(255))

    # Copyright/Creator Information
    copyright = Column(String(500))
    creator = Column(String(255))
    credit = Column(String(255))
    caption = Column(Text)
    title = Column(String(500))

    # Software/Processing
    software = Column(String(255))
    orientation = Column(Integer)
    compression = Column(String(100))
    quality = Column(Integer)

    # Rating/Organization
    rating = Column(Integer)

    # File Timestamps
    file_created = Column(DateTime)
    file_modified = Column(DateTime)

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_version = Column(String(20), default='1.0.0')
    has_errors = Column(Boolean, default=False)

    # Relationships
    keywords = relationship("ImageKeyword", back_populates="image_metadata", cascade="all, delete-orphan")
    exif_raw = relationship("ImageExifRaw", back_populates="image_metadata", cascade="all, delete-orphan")


class ImageKeyword(Base):
    """Image keywords table - many-to-many relationship for tags."""
    __tablename__ = 'image_keywords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_metadata_id = Column(Integer, ForeignKey('image_metadata.id', ondelete='CASCADE'), nullable=False)
    keyword = Column(String(255), nullable=False)

    # Relationship
    image_metadata = relationship("ImageMetadataDB", back_populates="keywords")


class ImageExifRaw(Base):
    """Image EXIF raw data table - stores all EXIF tags as key-value pairs."""
    __tablename__ = 'image_exif_raw'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_metadata_id = Column(Integer, ForeignKey('image_metadata.id', ondelete='CASCADE'), nullable=False)
    exif_tag = Column(String(255), nullable=False)
    exif_value = Column(Text)

    # Relationship
    image_metadata = relationship("ImageMetadataDB", back_populates="exif_raw")


class ImageAnalysisError(Base):
    """Image analysis errors table - stores errors during analysis."""
    __tablename__ = 'image_analysis_errors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(BigInteger, nullable=False)
    error_message = Column(Text, nullable=False)
    error_timestamp = Column(DateTime, default=datetime.utcnow)


# --- Database Functions ---

def save_image_metadata(file_path: Path, metadata: ImageMetadata) -> bool:
    """
    Save image metadata to database.

    Args:
        file_path: Path to the image file
        metadata: ImageMetadata object with extracted data

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        with Session() as session:
            # Get file_id from files table
            from core.db import File
            file = session.query(File).filter_by(path=str(file_path)).first()
            if not file:
                logger.warning(f"File not found in database: {file_path}")
                return False

            # Check if metadata already exists
            existing = session.query(ImageMetadataDB).filter_by(file_id=file.id).first()
            if existing:
                # Delete existing to replace (cascade will handle keywords and exif_raw)
                session.delete(existing)
                session.commit()

            # Create new metadata record
            db_metadata = ImageMetadataDB(
                file_id=file.id,
                # Basic Image Properties
                width=metadata.width,
                height=metadata.height,
                format=metadata.format,
                mode=metadata.mode,
                color_space=metadata.color_space,
                dpi_x=metadata.dpi[0] if metadata.dpi else None,
                dpi_y=metadata.dpi[1] if metadata.dpi else None,
                bit_depth=metadata.bit_depth,
                has_transparency=metadata.has_transparency,
                # Camera Information
                camera_make=metadata.camera_make,
                camera_model=metadata.camera_model,
                lens_make=metadata.lens_make,
                lens_model=metadata.lens_model,
                # Camera Settings
                date_taken=metadata.date_taken,
                date_digitized=metadata.date_digitized,
                date_modified=metadata.date_modified,
                iso_speed=metadata.iso_speed,
                exposure_time=metadata.exposure_time,
                f_number=metadata.f_number,
                focal_length=metadata.focal_length,
                flash=metadata.flash,
                white_balance=metadata.white_balance,
                metering_mode=metadata.metering_mode,
                exposure_program=metadata.exposure_program,
                exposure_bias=metadata.exposure_bias,
                # GPS Location Data
                gps_latitude=metadata.gps_latitude,
                gps_longitude=metadata.gps_longitude,
                gps_altitude=metadata.gps_altitude,
                gps_timestamp=metadata.gps_timestamp,
                gps_location_name=metadata.gps_location_name,
                # Copyright/Creator Information
                copyright=metadata.copyright,
                creator=metadata.creator,
                credit=metadata.credit,
                caption=metadata.caption,
                title=metadata.title,
                # Software/Processing
                software=metadata.software,
                orientation=metadata.orientation,
                compression=metadata.compression,
                quality=metadata.quality,
                # Rating/Organization
                rating=metadata.rating,
                # File Timestamps
                file_created=metadata.file_created,
                file_modified=metadata.file_modified,
                # Metadata
                analyzed_at=datetime.utcnow(),
                analysis_version='1.0.0',
                has_errors=len(metadata.errors) > 0
            )

            session.add(db_metadata)
            session.flush()  # Get the ID without committing

            # Add keywords
            if metadata.keywords:
                for keyword in metadata.keywords:
                    if keyword:  # Skip empty keywords
                        kw = ImageKeyword(
                            image_metadata_id=db_metadata.id,
                            keyword=keyword[:255]  # Truncate to fit column
                        )
                        session.add(kw)

            # Add raw EXIF data
            if metadata.raw_exif:
                for tag, value in metadata.raw_exif.items():
                    if tag and value is not None:  # Skip empty tags
                        exif_raw = ImageExifRaw(
                            image_metadata_id=db_metadata.id,
                            exif_tag=str(tag)[:255],  # Truncate to fit column
                            exif_value=str(value)[:65535] if value else None  # Truncate for TEXT field
                        )
                        session.add(exif_raw)

            # Save any errors
            if metadata.errors:
                for error in metadata.errors:
                    error_record = ImageAnalysisError(
                        file_id=file.id,
                        error_message=error[:65535],  # Truncate for TEXT field
                        error_timestamp=datetime.utcnow()
                    )
                    session.add(error_record)

            session.commit()
            logger.info(f"✅ Saved image metadata for: {file_path.name}")
            return True

    except Exception as e:
        logger.error(f"❌ Error saving image metadata for {file_path}: {e}")
        return False


def get_image_metadata(file_path: Path) -> Optional[ImageMetadata]:
    """
    Retrieve image metadata from database.

    Args:
        file_path: Path to the image file

    Returns:
        ImageMetadata object if found, None otherwise
    """
    try:
        with Session() as session:
            # Get file_id
            from core.db import File
            file = session.query(File).filter_by(path=str(file_path)).first()
            if not file:
                return None

            # Get metadata
            db_metadata = session.query(ImageMetadataDB).filter_by(file_id=file.id).first()
            if not db_metadata:
                return None

            # Get keywords
            keywords = [kw.keyword for kw in db_metadata.keywords]

            # Get raw EXIF
            raw_exif = {exif.exif_tag: exif.exif_value for exif in db_metadata.exif_raw}

            # Get errors
            errors = [err.error_message for err in
                     session.query(ImageAnalysisError).filter_by(file_id=file.id).all()]

            # Reconstruct ImageMetadata object
            metadata = ImageMetadata(
                file_path=file_path,
                file_size=file.size,
                file_hash=file.hash or "",
                # Basic Image Properties
                width=db_metadata.width,
                height=db_metadata.height,
                format=db_metadata.format,
                mode=db_metadata.mode,
                color_space=db_metadata.color_space,
                dpi=(db_metadata.dpi_x, db_metadata.dpi_y) if db_metadata.dpi_x else None,
                bit_depth=db_metadata.bit_depth,
                has_transparency=db_metadata.has_transparency,
                # Camera Information
                camera_make=db_metadata.camera_make,
                camera_model=db_metadata.camera_model,
                lens_make=db_metadata.lens_make,
                lens_model=db_metadata.lens_model,
                # Camera Settings
                date_taken=db_metadata.date_taken,
                date_digitized=db_metadata.date_digitized,
                date_modified=db_metadata.date_modified,
                iso_speed=db_metadata.iso_speed,
                exposure_time=db_metadata.exposure_time,
                f_number=db_metadata.f_number,
                focal_length=db_metadata.focal_length,
                flash=db_metadata.flash,
                white_balance=db_metadata.white_balance,
                metering_mode=db_metadata.metering_mode,
                exposure_program=db_metadata.exposure_program,
                exposure_bias=db_metadata.exposure_bias,
                # GPS Location Data
                gps_latitude=float(db_metadata.gps_latitude) if db_metadata.gps_latitude else None,
                gps_longitude=float(db_metadata.gps_longitude) if db_metadata.gps_longitude else None,
                gps_altitude=db_metadata.gps_altitude,
                gps_timestamp=db_metadata.gps_timestamp,
                gps_location_name=db_metadata.gps_location_name,
                # Copyright/Creator Information
                copyright=db_metadata.copyright,
                creator=db_metadata.creator,
                credit=db_metadata.credit,
                caption=db_metadata.caption,
                title=db_metadata.title,
                keywords=keywords,
                # Software/Processing
                software=db_metadata.software,
                orientation=db_metadata.orientation,
                compression=db_metadata.compression,
                quality=db_metadata.quality,
                # Rating/Organization
                rating=db_metadata.rating,
                # File Timestamps
                file_created=db_metadata.file_created,
                file_modified=db_metadata.file_modified,
                # Raw EXIF
                raw_exif=raw_exif,
                # Errors
                errors=errors
            )

            return metadata

    except Exception as e:
        logger.error(f"❌ Error retrieving image metadata for {file_path}: {e}")
        return None


def has_image_metadata(file_path: Path) -> bool:
    """
    Check if image metadata exists in database.

    Args:
        file_path: Path to the image file

    Returns:
        True if metadata exists, False otherwise
    """
    try:
        with Session() as session:
            from core.db import File
            file = session.query(File).filter_by(path=str(file_path)).first()
            if not file:
                return False

            exists = session.query(ImageMetadataDB).filter_by(file_id=file.id).first() is not None
            return exists

    except Exception as e:
        logger.error(f"❌ Error checking image metadata for {file_path}: {e}")
        return False
