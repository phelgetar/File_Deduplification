#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: db.py
# Purpose: ORM and DB utility functions
#
# Description:
# Defines SQLAlchemy models and handles DB connections, caching,
# and inserts/updates from scanner, hasher, and executor modules.
#
# Author: Tim Canady
# Created: 2025-11-04
#
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial DB ORM and integration logic — Tim Canady
###################################################################

import os
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, BigInteger, String,
                        Boolean, DateTime, Text, Enum, Float, ForeignKey)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Load env and replace password placeholder
load_dotenv()
raw_url = os.getenv("DATABASE_URL")
db_password = os.getenv("DB_PASSWORD")
DATABASE_URL = raw_url.replace("${DB_PASSWORD}", db_password)

# Set up engine and session
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- ORM Models ---

class File(Base):
    __tablename__ = 'files'

    id = Column(BigInteger, primary_key=True)
    path = Column(Text, nullable=False, unique=True)
    size = Column(BigInteger)
    mtime = Column(DateTime)
    hash = Column(String(128))
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Text)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    classification = relationship("Classification", back_populates="file", uselist=False)


class Classification(Base):
    __tablename__ = 'classifications'

    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger, ForeignKey('files.id'))
    category = Column(String(255))
    owner = Column(String(255))
    year = Column(Integer)
    confidence = Column(Float)
    classified_at = Column(DateTime, default=datetime.utcnow)
    file = relationship("File", back_populates="classification")


class Operation(Base):
    __tablename__ = 'operations'

    id = Column(BigInteger, primary_key=True)
    file_id = Column(BigInteger, ForeignKey('files.id'))
    action = Column(Enum('MOVE', 'DELETE', 'METADATA', name='action_enum'))
    target_path = Column(Text)
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime)

# --- DB Logic ---

def init_db():
    Base.metadata.create_all(engine)

def cache_file_entry(path, size, mtime, hash_val):
    session = Session()
    file = session.query(File).filter_by(path=str(path)).first()
    if not file:
        file = File(path=str(path), size=size, mtime=mtime, hash=hash_val)
    else:
        file.hash = hash_val
        file.size = size
        file.mtime = mtime
        file.scanned_at = datetime.utcnow()
    session.add(file)
    session.commit()
    session.close()
    return file

def get_cached_hash(path, mtime):
    session = Session()
    file = session.query(File).filter_by(path=str(path)).first()
    if file and file.mtime == mtime:
        return file.hash
    session.close()
    return None

def mark_duplicate(file_path, duplicate_of):
    session = Session()
    file = session.query(File).filter_by(path=str(file_path)).first()
    if file:
        file.is_duplicate = True
        file.duplicate_of = duplicate_of
        session.commit()
    session.close()

def log_operation(file_path, action, target_path):
    session = Session()
    file = session.query(File).filter_by(path=str(file_path)).first()
    if file:
        op = Operation(file_id=file.id, action=action, target_path=str(target_path))
        session.add(op)
        session.commit()
    session.close()
