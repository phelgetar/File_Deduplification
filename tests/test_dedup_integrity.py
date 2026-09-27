#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_dedup_integrity.py
# Purpose: What counts as a duplicate, and what must never count
#
# Description:
# Duplicate detection compares SHA-256 of file contents. The
# comparison was never wrong; what reached it was. A symlink was
# followed and its target read once per link (488 sandbox container
# links to one Pictures library, 21.47 TB of a 25.77 TB scan), and a
# hardlink was reported as a second copy whose deletion would reclaim
# nothing.
#
# These cover the four guards added on 2026-09-26: skip symlinks,
# treat (device, inode) as identity, sample the ends before reading
# the middle, and re-read before trashing.
#
# Author: Tim Canady
# Created: 2026-09-26
#
# Version: 1.0.0
# Last Modified: 2026-09-26 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-09-26): Initial integrity tests — Tim Canady
###################################################################

import hashlib
import os
from pathlib import Path

import pytest

from core.deduplicator import detect_duplicates
from core.hasher import (SAMPLE_THRESHOLD, generate_hashes, hash_directory,
                         sample_hash, sample_prefilter)
from core.scanner import is_regular_file, link_record, scan_directory
from models.file_info import FileInfo


def _big(path, size=SAMPLE_THRESHOLD * 2, seed=b"\x01"):
    """A file large enough to be sampled, with distinctive ends."""
    body = bytearray(seed * size)
    body[:16] = b"HEAD" + bytes(seed) * 12
    body[-16:] = b"TAIL" + bytes(seed) * 12
    path.write_bytes(bytes(body))
    return path


# ---------------------------------------------------------------- symlinks

def test_a_symlink_is_recorded_not_followed(tmp_path):
    """The whole bug in one test. Every sandboxed app has
    Containers/<id>/Data/Pictures pointing at one library."""
    (tmp_path / "Pictures").mkdir()
    (tmp_path / "Pictures" / "photo.jpg").write_bytes(b"content")
    (tmp_path / "Containers").mkdir()
    link = tmp_path / "Containers" / "Pictures"
    link.symlink_to("../Pictures")

    links = []
    found = scan_directory(tmp_path, symlinks_out=links)

    assert [p.name for p in found] == ["photo.jpg"], \
        "the real file is scanned exactly once"
    assert [p.name for p, _ in links] == ["Pictures"]
    assert links[0][1] == "../Pictures", "the target is kept, not discarded"


def test_a_broken_symlink_does_not_reach_the_hasher(tmp_path):
    """os.walk calls an unresolvable link a FILE, which is how these
    got into the results with no check that they were one."""
    (tmp_path / "Data").mkdir()
    link = tmp_path / "Data" / "Pictures"
    link.symlink_to("/nowhere/at/all")
    assert not link.is_file() and not link.is_dir()

    links = []
    assert scan_directory(tmp_path, symlinks_out=links) == []
    assert [p.name for p, _ in links] == ["Pictures"]


def test_link_record_returns_none_for_a_real_file(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("x")
    assert link_record(real) is None
    assert is_regular_file(real) is True


def test_a_fifo_is_not_a_regular_file(tmp_path):
    """Opening one blocks forever. os.walk lists it among filenames."""
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    assert is_regular_file(fifo) is False
    assert scan_directory(tmp_path) == []


def test_hash_directory_does_not_walk_out_through_a_link(tmp_path):
    """rglob follows symlinks, so hashing a package could leave it."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "huge.bin").write_bytes(b"z" * 5000)

    pkg = tmp_path / "Thing.app"
    (pkg / "Contents").mkdir(parents=True)
    (pkg / "Contents" / "Info.plist").write_bytes(b"real")
    (pkg / "Contents" / "Escape").symlink_to(outside)

    lonely = tmp_path / "Lonely.app"
    (lonely / "Contents").mkdir(parents=True)
    (lonely / "Contents" / "Info.plist").write_bytes(b"real")

    assert hash_directory(pkg) == hash_directory(lonely), \
        "the symlinked escape hatch must contribute nothing"


def test_the_deduplicator_ignores_symlink_rows():
    files = [FileInfo(path=Path("/x/a"), size=0, hash="SYMLINK"),
             FileInfo(path=Path("/x/b"), size=0, hash="SYMLINK")]
    out = detect_duplicates(files)
    assert not any(f.is_duplicate for f in out)


# ---------------------------------------------------------------- identity

def test_a_hardlink_is_not_a_second_copy():
    """Same device and inode is one file under two names. Deleting the
    second name reclaims nothing, so it must not be offered."""
    digest = "a" * 64
    files = [
        FileInfo(path=Path("/x/original"), size=100, hash=digest, dev=1, inode=7),
        FileInfo(path=Path("/x/hardlink"), size=100, hash=digest, dev=1, inode=7),
        FileInfo(path=Path("/x/real_copy"), size=100, hash=digest, dev=1, inode=8),
    ]
    by_name = {f.path.name: f for f in detect_duplicates(files)}
    assert by_name["hardlink"].is_duplicate is False
    assert by_name["hardlink"].original_path == Path("/x/original"), \
        "the relationship is still recorded, just not as reclaimable"
    assert by_name["real_copy"].is_duplicate is True


def test_same_inode_on_different_devices_is_not_identity():
    """Inode numbers are only unique within a device."""
    digest = "b" * 64
    files = [
        FileInfo(path=Path("/vol1/f"), size=10, hash=digest, dev=1, inode=5),
        FileInfo(path=Path("/vol2/f"), size=10, hash=digest, dev=2, inode=5),
    ]
    assert sum(f.is_duplicate for f in detect_duplicates(files)) == 1


def test_identity_is_skipped_when_it_was_not_measured():
    """Rows scanned before this existed have no dev/inode, and must
    still dedupe on content rather than being silently dropped."""
    digest = "c" * 64
    files = [FileInfo(path=Path("/x/a"), size=10, hash=digest),
             FileInfo(path=Path("/x/b"), size=10, hash=digest)]
    assert sum(f.is_duplicate for f in detect_duplicates(files)) == 1


def test_the_hasher_records_device_and_inode(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("hello")
    info = generate_hashes([f], use_db=False, workers=1)[0]
    st = f.stat()
    assert (info.dev, info.inode) == (st.st_dev, st.st_ino)


# ------------------------------------------------------------ sample hash

def test_files_differing_only_in_the_middle_share_a_sample(tmp_path):
    """The trap. A sample match is a reason to read, never a verdict."""
    a = _big(tmp_path / "a.bin")
    b = _big(tmp_path / "b.bin")
    data = bytearray(b.read_bytes())
    data[len(data) // 2] ^= 0xFF
    b.write_bytes(bytes(data))

    size = a.stat().st_size
    assert sample_hash(a, size) == sample_hash(b, size)

    infos = generate_hashes([a, b], use_db=False, workers=1)
    assert len({i.hash for i in infos}) == 2, "both must be read in full"
    assert not any(f.is_duplicate for f in detect_duplicates(infos))


def test_a_small_file_is_never_sampled(tmp_path):
    small = tmp_path / "small.txt"
    small.write_text("tiny")
    assert sample_hash(small, small.stat().st_size) is None


def test_a_uniquely_shaped_large_file_skips_the_full_read(tmp_path):
    lonely = _big(tmp_path / "lonely.bin", seed=b"\x02")
    pair_a = _big(tmp_path / "pair_a.bin", seed=b"\x03")
    pair_b = tmp_path / "pair_b.bin"
    pair_b.write_bytes(pair_a.read_bytes())

    unique = sample_prefilter([lonely, pair_a, pair_b], workers=2, use_db=False)
    assert set(unique) == {lonely}

    infos = {i.path.name: i for i in
             generate_hashes([lonely, pair_a, pair_b], use_db=False, workers=2)}
    assert infos["lonely.bin"].hash == "SAMPLE_ONLY"
    assert infos["pair_a.bin"].hash == infos["pair_b.bin"].hash
    assert len(infos["pair_a.bin"].hash) == 64, "the pair got a real hash"


def test_sample_only_files_are_not_duplicate_candidates():
    files = [FileInfo(path=Path("/x/a"), size=99, hash="SAMPLE_ONLY"),
             FileInfo(path=Path("/x/b"), size=99, hash="SAMPLE_ONLY")]
    assert not any(f.is_duplicate for f in detect_duplicates(files))


# ------------------------------------------------- re-read before deleting

@pytest.fixture
def verify(monkeypatch):
    import server.dupes as dupes
    return dupes._verify_before_trash


def _recorded(paths_and_bytes):
    return {str(p): hashlib.sha256(b).hexdigest() for p, b in paths_and_bytes}


def test_a_file_changed_since_scanning_is_not_trashed(tmp_path, verify,
                                                      monkeypatch):
    """The hash cache is keyed on path plus mtime, so a file rewritten
    with its mtime preserved keeps a stale hash. This is the last point
    where being wrong is still recoverable."""
    good = tmp_path / "unchanged.bin"; good.write_bytes(b"original")
    bad = tmp_path / "changed.bin"; bad.write_bytes(b"original")
    recorded = _recorded([(good, b"original"), (bad, b"original")])
    bad.write_bytes(b"something else entirely")

    monkeypatch.setattr("core.db.get_recorded_hashes", lambda p: recorded)
    safe, rejected = verify([str(good), str(bad)])
    assert safe == [str(good)]
    assert len(rejected) == 1
    assert "changed" in rejected[0]["reason"]


def test_a_file_with_no_full_hash_is_never_trashed(tmp_path, verify,
                                                   monkeypatch):
    f = tmp_path / "big.bin"; f.write_bytes(b"x")
    for marker in ("METADATA_ONLY", "SAMPLE_ONLY", "SYMLINK"):
        monkeypatch.setattr("core.db.get_recorded_hashes",
                            lambda p, m=marker: {str(f): m})
        safe, rejected = verify([str(f)])
        assert safe == [] and rejected[0]["reason"] == "no full hash on record"


def test_a_vanished_file_is_reported_not_trashed(tmp_path, verify, monkeypatch):
    gone = tmp_path / "gone.bin"
    monkeypatch.setattr("core.db.get_recorded_hashes",
                        lambda p: {str(gone): "d" * 64})
    safe, rejected = verify([str(gone)])
    assert safe == [] and "could not re-read" in rejected[0]["reason"]
