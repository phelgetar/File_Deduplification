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
# Version: 0.7.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.7.0 (2026-08-17): Bulk helpers (get_file_ids, get_classified_categories, save_classifications_bulk, save_file_tags_bulk) — the per-file helpers issued one query per file (and per tag), which dominated the wall clock once the CPU stages were parallelised — Tim Canady
# - 0.6.0 (2026-07-20): Circuit breaker — after repeated consecutive DB failures mid-run, stop attempting DB writes (no per-file timeout stalls); bounded connect timeout — Tim Canady
# - 0.5.0 (2025-11-12): Fixed schema, removed FK constraints, added classification save — Tim Canady
# - 0.2.0 (2025-11-06): Added context manager support for sessions — Tim Canady
# - 0.1.0 (2025-11-04): Initial DB ORM and integration logic — Tim Canady
###################################################################

import functools
import os
import threading
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

# Set up engine and session. connect_timeout bounds how long a call can
# stall when the server is unreachable (default would be ~10s per attempt).
engine = create_engine(DATABASE_URL, echo=False,
                       connect_args={"connect_timeout": 5})
Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- Circuit breaker ---
#
# If the database dies mid-run, every helper call would otherwise stall for
# a full connection timeout — per file, across thousands of files. After
# DB_FAILURE_THRESHOLD consecutive failures the breaker trips: one loud
# error is logged and all further DB helpers become instant no-ops for the
# rest of the run. main.py/executor.py consult is_db_down() to fail fast
# before and during --execute, where losing the operation log matters.

DB_FAILURE_THRESHOLD = 3

_breaker = {"failures": 0, "down": False}
_breaker_lock = threading.Lock()


def is_db_down():
    """True once the circuit breaker has tripped for this run."""
    return _breaker["down"]


def _record_success():
    with _breaker_lock:
        _breaker["failures"] = 0


def _record_failure(func_name, error):
    with _breaker_lock:
        _breaker["failures"] += 1
        tripped = (not _breaker["down"]
                   and _breaker["failures"] >= DB_FAILURE_THRESHOLD)
        if tripped:
            _breaker["down"] = True
    if tripped:
        logger.error(
            f"🔌 Database circuit breaker tripped after {DB_FAILURE_THRESHOLD} "
            f"consecutive failures (last: {func_name}: {error}). Continuing "
            f"WITHOUT persistence — no hashes, classifications, or tags will "
            f"be saved from this point, and this run will not be resumable "
            f"past here. File execution (--execute) will be refused.")
    else:
        logger.warning(f"⚠️ DB operation {func_name} failed: {error}")


def _db_guard(default=None):
    """Wrap a DB helper: no-op instantly once the breaker is down, and
    swallow failures (counting them toward the breaker) otherwise."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _breaker["down"]:
                return default
            try:
                result = fn(*args, **kwargs)
                _record_success()
                return result
            except Exception as e:
                _record_failure(fn.__name__, e)
                return default
        return wrapper
    return decorator

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
    # index=True is load-bearing: save_classification() looks up by file_id
    # for EVERY file — without the index that is a full table scan per file,
    # which made classification O(n^2) over the run (observed: 417k/day
    # decaying to 128k/day at 2.4M rows before the index existed).
    file_id = Column(BigInteger, index=True)  # Removed ForeignKey constraint due to permission issues
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


class DuplicateResolution(Base):
    """A user's decision about one duplicate group, keyed by content hash.

    kept_paths is a JSON array — more than one copy may be kept. Files in
    the group but not in kept_paths are treated as duplicates without
    asking again; resolved groups are hidden from review screens.
    """
    __tablename__ = 'duplicate_resolutions'

    hash = Column(String(128), primary_key=True)
    kept_paths = Column(Text, nullable=False)
    resolved_at = Column(DateTime, default=datetime.utcnow)


class FileTag(Base):
    __tablename__ = 'file_tags'

    id = Column(Integer, primary_key=True)
    file_id = Column(BigInteger, nullable=False)
    tag = Column(String(255), nullable=False)
    tag_source = Column(String(50), default='ai_tagger')  # 'ai_tagger', 'image_content', 'semantic_context', 'manual'
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- DB Logic ---

def init_db():
    Base.metadata.create_all(engine)

@_db_guard(default=None)
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

@_db_guard(default={})
def get_duplicate_resolutions():
    """All resolved duplicate groups: {hash: [kept_path, ...]}."""
    import json as _json
    with Session() as session:
        out = {}
        for r in session.query(DuplicateResolution).all():
            try:
                out[r.hash] = _json.loads(r.kept_paths)
            except (TypeError, ValueError):
                continue
        return out


@_db_guard(default=False)
def save_duplicate_resolution(hash_val, kept_paths):
    """Record which copies of a duplicate group to keep."""
    import json as _json
    with Session() as session:
        row = session.query(DuplicateResolution).filter_by(hash=hash_val).first()
        if row is None:
            row = DuplicateResolution(hash=hash_val)
        row.kept_paths = _json.dumps(list(kept_paths))
        row.resolved_at = datetime.utcnow()
        session.add(row)
        session.commit()
        return True


@_db_guard(default=False)
def delete_duplicate_resolution(hash_val):
    """Forget a resolution so the group shows up for review again."""
    with Session() as session:
        row = session.query(DuplicateResolution).filter_by(hash=hash_val).first()
        if row:
            session.delete(row)
            session.commit()
            return True
        return False


@_db_guard(default=None)
def get_classification(path):
    """Return (category, confidence) for an already-classified file, or None.

    Used by classify_file() to resume interrupted runs: files that already
    have a classification row are not re-classified (and, crucially, not
    re-sent to the LLM). Use scripts/reclassify_files.py to force a redo
    after classifier rule changes.
    """
    with Session() as session:
        file = session.query(File).filter_by(path=str(path)).first()
        if not file:
            return None
        c = session.query(Classification).filter_by(file_id=file.id).first()
        if c and c.category:
            return (c.category, c.confidence)
        return None


@_db_guard(default=None)
def get_cached_hash(path, mtime):
    with Session() as session:
        file = session.query(File).filter_by(path=str(path)).first()
        if file and file.mtime == mtime:
            return file.hash
        return None

@_db_guard(default=None)
def mark_duplicate(file_path, duplicate_of):
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if file:
            file.is_duplicate = True
            file.duplicate_of = duplicate_of
            session.commit()

@_db_guard(default=None)
def log_operation(file_path, action, target_path):
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if file:
            op = Operation(file_id=file.id, action=action, target_path=str(target_path))
            session.add(op)
            session.commit()

@_db_guard(default=None)
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


@_db_guard(default=0)
def save_file_tags(file_path, tags, tag_source='ai_tagger', confidence=1.0):
    """
    Save tags for a file in the database.

    Args:
        file_path: Path to the file
        tags: List of tag strings
        tag_source: Source of tags ('ai_tagger', 'image_content', 'semantic_context', 'manual')
        confidence: Confidence score for tags (0.0 to 1.0)

    Returns:
        Number of tags saved
    """
    if not tags:
        return 0

    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if not file:
            logger.warning(f"File not found in database: {file_path}")
            return 0

        tags_saved = 0
        for tag in tags:
            try:
                # Check if tag already exists
                existing_tag = session.query(FileTag).filter_by(
                    file_id=file.id,
                    tag=tag,
                    tag_source=tag_source
                ).first()

                if not existing_tag:
                    # Create new tag
                    file_tag = FileTag(
                        file_id=file.id,
                        tag=tag,
                        tag_source=tag_source,
                        confidence=confidence
                    )
                    session.add(file_tag)
                    tags_saved += 1
                else:
                    # Update confidence if different
                    if existing_tag.confidence != confidence:
                        existing_tag.confidence = confidence
                        existing_tag.created_at = datetime.utcnow()
                        tags_saved += 1

            except Exception as e:
                logger.warning(f"Error saving tag '{tag}' for {file_path}: {e}")
                continue

        session.commit()
        return tags_saved


@_db_guard(default=[])
def get_file_tags(file_path, tag_source=None):
    """
    Retrieve tags for a file from the database.

    Args:
        file_path: Path to the file
        tag_source: Optional filter by tag source

    Returns:
        List of tag strings
    """
    with Session() as session:
        file = session.query(File).filter_by(path=str(file_path)).first()
        if not file:
            return []

        query = session.query(FileTag).filter_by(file_id=file.id)

        if tag_source:
            query = query.filter_by(tag_source=tag_source)

        tags = query.all()
        return [tag.tag for tag in tags]


# --- Bulk helpers ---
#
# The single-file helpers above issue one SELECT per file (and
# save_file_tags issues one more per tag). Across a large run that is
# millions of round trips, and it dominates the wall clock once the
# CPU stages are parallel. These batch equivalents do the same work a
# chunk at a time so a run costs a few thousand queries instead.
#
# All of them take and return plain paths/strings so they can be called
# from the parent process with results collected out of worker pools —
# worker processes deliberately never touch the database.

# Rows per statement. Large enough to amortise the round trip, small
# enough to stay well under MySQL's max_allowed_packet and to keep the
# IN() lists reasonable for the optimiser.
BULK_CHUNK = 1000


def _chunks(seq, size=BULK_CHUNK):
    seq = list(seq)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


@_db_guard(default=None)
def get_file_ids(paths):
    """Map {path string -> files.id} for the given paths.

    Returns only the paths that exist in the database. Callers should
    treat a None result (circuit breaker open) as "nothing known".
    """
    found = {}
    with Session() as session:
        for chunk in _chunks(str(p) for p in paths):
            rows = session.query(File.id, File.path).filter(File.path.in_(chunk)).all()
            for file_id, path in rows:
                found[path] = file_id
    return found


@_db_guard(default=None)
def get_classified_categories(paths):
    """Map {path -> category} for paths that already have a classification.

    Returns the category, not merely the fact one exists: the caller
    skips re-classifying these files, so it needs the stored answer to
    put back on the FileInfo. Returning a bare set of paths meant
    resumed files came through with type=None and were planned as
    unclassified — the resume path silently discarded every category.
    """
    found = {}
    with Session() as session:
        for chunk in _chunks(str(p) for p in paths):
            rows = (session.query(File.path, Classification.category)
                    .join(Classification, Classification.file_id == File.id)
                    .filter(File.path.in_(chunk))
                    .filter(Classification.category.isnot(None))
                    .all())
            for path, category in rows:
                found[path] = category
    return found


@_db_guard(default=0)
def save_classifications_bulk(rows):
    """Insert or update many classifications at once.

    `rows` is an iterable of (path, category, owner, year, confidence).
    Returns the number of rows written.
    """
    rows = [r for r in rows if r]
    if not rows:
        return 0

    written = 0
    with Session() as session:
        for chunk in _chunks(rows):
            by_path = {str(path): (category, owner, year, confidence)
                       for path, category, owner, year, confidence in chunk}

            id_rows = session.query(File.id, File.path).filter(
                File.path.in_(list(by_path))).all()
            path_to_id = {path: fid for fid, path in id_rows}
            if not path_to_id:
                continue

            # One query tells us which of these already have a row, so
            # the writes below split cleanly into inserts and updates.
            existing = {
                c.file_id: c for c in session.query(Classification).filter(
                    Classification.file_id.in_(list(path_to_id.values()))).all()
            }

            new_rows = []
            for path, (category, owner, year, confidence) in by_path.items():
                file_id = path_to_id.get(path)
                if file_id is None:
                    continue
                current = existing.get(file_id)
                if current is None:
                    new_rows.append({
                        "file_id": file_id, "category": category, "owner": owner,
                        "year": year, "confidence": confidence,
                        "classified_at": datetime.utcnow(),
                    })
                else:
                    current.category = category
                    current.owner = owner
                    current.year = year
                    current.confidence = confidence
                    current.classified_at = datetime.utcnow()
                written += 1

            if new_rows:
                session.bulk_insert_mappings(Classification, new_rows)
            session.commit()
    return written


@_db_guard(default=0)
def save_file_tags_bulk(rows, tag_source='ai_tagger', confidence=1.0):
    """Insert many (path, [tags]) pairs at once, skipping duplicates.

    Returns the number of tag rows inserted. Existing (file_id, tag,
    tag_source) rows are left alone rather than rewritten — re-running a
    tagging pass should be cheap and should not churn created_at.
    """
    rows = [(p, t) for p, t in rows if t]
    if not rows:
        return 0

    inserted = 0
    with Session() as session:
        for chunk in _chunks(rows):
            by_path = {}
            for path, tags in chunk:
                by_path.setdefault(str(path), set()).update(tags)

            id_rows = session.query(File.id, File.path).filter(
                File.path.in_(list(by_path))).all()
            path_to_id = {path: fid for fid, path in id_rows}
            if not path_to_id:
                continue

            file_ids = list(path_to_id.values())
            already = set(
                session.query(FileTag.file_id, FileTag.tag)
                .filter(FileTag.file_id.in_(file_ids))
                .filter(FileTag.tag_source == tag_source)
                .all()
            )

            new_rows = []
            for path, tags in by_path.items():
                file_id = path_to_id.get(path)
                if file_id is None:
                    continue
                for tag in tags:
                    if (file_id, tag) in already:
                        continue
                    already.add((file_id, tag))
                    new_rows.append({
                        "file_id": file_id, "tag": tag,
                        "tag_source": tag_source, "confidence": confidence,
                        "created_at": datetime.utcnow(),
                    })

            if new_rows:
                session.bulk_insert_mappings(FileTag, new_rows)
                inserted += len(new_rows)
            session.commit()
    return inserted


# --- Deletion log (Trash) and undo ---
#
# Trashing is recorded in `operations` with action='DELETE':
#   file_id      the file that was trashed (its path is in `files`)
#   target_path  where in the Trash it landed
#   executed_at  identical across one batch — this is the batch key
#   executed     1 while trashed, 0 once restored
#
# Grouping by executed_at avoids a schema change, and flipping `executed`
# on restore keeps the audit trail instead of deleting history.

@_db_guard(default=0)
def log_deletions_bulk(rows, batch_at=None):
    """Record a batch of trashed files. rows: (original_path, trash_path)."""
    rows = [r for r in rows if r]
    if not rows:
        return 0
    batch_at = batch_at or datetime.utcnow()

    written = 0
    with Session() as session:
        for chunk in _chunks(rows):
            by_path = {str(orig): trash for orig, trash in chunk}
            id_rows = session.query(File.id, File.path).filter(
                File.path.in_(list(by_path))).all()
            path_to_id = {path: fid for fid, path in id_rows}

            new_rows = [{
                "file_id": path_to_id[path],
                "action": "DELETE",
                "target_path": trash,
                "executed": True,
                "executed_at": batch_at,
            } for path, trash in by_path.items() if path in path_to_id]

            if new_rows:
                session.bulk_insert_mappings(Operation, new_rows)
                written += len(new_rows)
            session.commit()
    return written


@_db_guard(default=None)
def last_deletion_batch():
    """The most recent batch still in the Trash.

    Returns {"at": datetime, "items": [{"original","trash","file_id"}]} or
    None when there is nothing left to undo.
    """
    with Session() as session:
        latest = (session.query(Operation.executed_at)
                  .filter(Operation.action == "DELETE",
                          Operation.executed.is_(True))
                  .order_by(Operation.executed_at.desc())
                  .first())
        if not latest or latest[0] is None:
            return None
        at = latest[0]

        rows = (session.query(Operation.id, Operation.file_id,
                              Operation.target_path, File.path)
                .join(File, File.id == Operation.file_id)
                .filter(Operation.action == "DELETE",
                        Operation.executed.is_(True),
                        Operation.executed_at == at)
                .all())
        return {
            "at": at,
            "items": [{"operation_id": oid, "file_id": fid,
                       "trash": target, "original": original}
                      for oid, fid, target, original in rows],
        }


@_db_guard(default=0)
def mark_deletions_restored(operation_ids):
    """Flag operations as undone so the batch is no longer restorable."""
    operation_ids = list(operation_ids)
    if not operation_ids:
        return 0
    with Session() as session:
        n = (session.query(Operation)
             .filter(Operation.id.in_(operation_ids))
             .update({Operation.executed: False}, synchronize_session=False))
        session.commit()
        return n


@_db_guard(default=0)
def count_trashed():
    """How many files are currently sitting in the Trash from this tool."""
    with Session() as session:
        return (session.query(Operation)
                .filter(Operation.action == "DELETE",
                        Operation.executed.is_(True))
                .count())
