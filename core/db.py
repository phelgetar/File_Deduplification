#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: db.py
# Purpose: ORM and DB utility functions with SQLAlchemy
#
# Description:
# Defines SQLAlchemy models and handles DB connections, caching,
# and inserts/updates from scanner, hasher, and executor modules.
# Supports MySQL with proper password encoding and session management.
#
# Author: Tim Canady
# Created: 2025-11-04
#
# Version: 0.5.0
# Last Modified: 2025-11-12 by Tim Canady
#
# Revision History:
# - 0.5.0 (2025-11-12): Fixed schema, removed FK constraints, added classification save — Tim Canady
# - 0.2.0 (2025-11-06): Added context manager support for sessions — Tim Canady
# - 0.1.0 (2025-11-04): Initial DB ORM and integration logic — Tim Canady
###################################################################

import os
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import (create_engine, Column, Integer, BigInteger, String,
                        Boolean, DateTime, Text, Enum, Float, ForeignKey)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Load environment variables and build connection URL
load_dotenv()

# Get database connection components
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Debug logging
import logging
logger = logging.getLogger(__name__)

# Validate required variables
if not all([db_name, db_user, db_password]):
    missing = []
    if not db_name: missing.append("DB_NAME")
    if not db_user: missing.append("DB_USER")
    if not db_password: missing.append("DB_PASSWORD")
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# URL-encode the password to handle special characters
encoded_password = quote_plus(db_password)

# Build the database URL
DATABASE_URL = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

# Log masked URL for debugging
safe_url = DATABASE_URL.replace(encoded_password, "***MASKED***")
logger.debug(f"Database URL: {safe_url}")

# Set up engine and session
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- ORM Models ---

class File(Base):
    __tablename__ = 'files'

    id = Column(BigInteger, primary_key=True)
    path = Column(String(767), nullable=False, unique=True)  # 767 chars * 4 bytes = 3068 bytes (under 3072 limit)
    size = Column(BigInteger)
    mtime = Column(DateTime)
    hash = Column(String(128))
    metadata_only = Column(Boolean, default=False)  # True if file is too large to hash
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String(767))  # Match path length
    scanned_at = Column(DateTime, default=datetime.utcnow)
    # Removed relationship - not needed since we query directly by file_id


class Classification(Base):
    __tablename__ = 'classifications'

    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger)  # Removed ForeignKey constraint due to permission issues
    category = Column(String(255))
    owner = Column(String(255))
    year = Column(Integer)
    confidence = Column(Float)
    classified_at = Column(DateTime, default=datetime.utcnow)
    # Removed relationship - not needed since we query directly by file_id


class Operation(Base):
    __tablename__ = 'operations'

    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger)  # Removed ForeignKey constraint due to permission issues
    action = Column(Enum('MOVE', 'DELETE', 'METADATA', name='action_enum'))
    target_path = Column(String(767))  # Match path length
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime)

# --- DB Logic ---

def init_db():
    Base.metadata.create_all(engine)

def cache_file_entry(path, size, mtime, hash_val, metadata_only=False):
    with Session() as session:
        file = session.query(File).filter_by(path=str(path)).first()
        if not file:
            file = File(path=str(path), size=size, mtime=mtime, hash=hash_val, metadata_only=metadata_only)
        else:
            file.hash = hash_val
            file.size = size
            file.mtime = mtime
            file.metadata_only = metadata_only
            file.scanned_at = datetime.utcnow()
        session.add(file)
        session.commit()
        return file

def get_cached_hash(path, mtime):
    with Session() as session:
        file = session.query(File).filter_by(path=str(path)).first()
        if file and file.mtime == mtime:
            return file.hash
        return None

def mark_duplicate(file_path, duplicate_of):
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if file:
            file.is_duplicate = True
            file.duplicate_of = duplicate_of
            session.commit()

def log_operation(file_path, action, target_path):
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if file:
            op = Operation(file_id=file.id, action=action, target_path=str(target_path))
            session.add(op)
            session.commit()

def save_classification(file_path, category, owner=None, year=None, confidence=None):
    """Save or update file classification in database."""
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if file:
            # Check if classification already exists
            classification = session.query(Classification).filter_by(file_id=file.id).first()
            if not classification:
                classification = Classification(
                    file_id=file.id,
                    category=category,
                    owner=owner,
                    year=year,
                    confidence=confidence
                )
                session.add(classification)
            else:
                # Update existing classification
                classification.category = category
                classification.owner = owner
                classification.year = year
                classification.confidence = confidence
                classification.classified_at = datetime.utcnow()
            session.commit()
