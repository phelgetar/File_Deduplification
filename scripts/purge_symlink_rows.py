#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: purge_symlink_rows.py
# Purpose: Remove inventory rows created by following symlinks
#
# Description:
# Until the scanner learned to record symlinks instead of following
# them, a link that os.walk could not classify was handed to the
# hasher, which resolved it and read whatever it pointed at. Every
# sandboxed app has ~/Library/Containers/<id>/Data/Pictures pointing
# at one real library, so that library was recorded 488 times as a
# 44 GB "file": 21.47 TB of the 25.77 TB that scan read.
#
# Those rows are wrong in three ways. They claim a size the path does
# not have, they carry a content hash for something that is not
# content, and they are marked duplicates of each other, which puts
# 487 deletable paths in front of the review screen. Deleting them
# would remove the links every sandboxed app needs to reach Pictures.
#
# This removes them, along with any duplicate resolution keyed on a
# hash that only those rows produced. The next scan re-records the
# same paths properly, as links with a target and no hash.
#
# Author: Tim Canady
# Created: 2026-09-26
#
# Version: 1.0.0
# Last Modified: 2026-09-26 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-09-26): Initial purge — Tim Canady
###################################################################

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import bindparam, text                        # noqa: E402

from core.db import engine                                    # noqa: E402

# The exact names macOS symlinks into every sandbox container's Data
# directory. Named explicitly rather than matched by shape: a first
# attempt used "anything directly under Data/" and swept up 148 real
# files that legitimately live there (.tdb index tables, .plist
# preferences, .db caches). A purge has to be narrower than the problem,
# not wider.
#
# Library is deliberately absent. It is a real directory in a container,
# not a link.
#
# The match is anchored on the last two path segments being
# "Data/<leaf>", not on a LIKE over the whole path. An earlier attempt
# used NOT LIKE '%/Data/%/%' to mean "nothing below Data", which also
# rejected every path with a directory called Data higher up, hiding
# 759 of these rows under /Volumes/home/Data/Restore/Library/.
LINK_LEAVES = ("Desktop", "Documents", "Downloads", "Movies", "Music",
               "Pictures", "Public")

CONTAINER_ROWS = """
    (path LIKE '%/Containers/%' OR path LIKE '%/Daemon Containers/%')
    AND SUBSTRING_INDEX(SUBSTRING_INDEX(path, '/', -2), '/', 1) = 'Data'
    AND SUBSTRING_INDEX(path, '/', -1) IN (
        'Desktop','Documents','Downloads','Movies','Music','Pictures','Public')
    AND hash <> 'SYMLINK'
"""


def find(conn):
    rows = conn.execute(text(f"""
        SELECT id, path, size, hash FROM files WHERE {CONTAINER_ROWS}
    """)).fetchall()
    hashes = {r[3] for r in rows if r[3] and r[3] != 'METADATA_ONLY'}
    return rows, hashes


def hashes_only_used_here(conn, hashes):
    """Hashes that no row OUTSIDE the container set carries.

    A resolution is only safe to drop if every file that produced it was
    one of these bogus rows. If the same hash also belongs to a real
    file somewhere, the user's decision about that group still means
    something and is left alone.
    """
    safe = set()
    for digest in hashes:
        other = conn.execute(text(f"""
            SELECT 1 FROM files
            WHERE hash = :h AND NOT ({CONTAINER_ROWS})
            LIMIT 1"""), {"h": digest}).first()
        if other is None:
            safe.add(digest)
    return safe


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Purge inventory rows created by following symlinks.")
    ap.add_argument("--apply", action="store_true",
                    help="Actually delete. Without this it only reports.")
    args = ap.parse_args()

    with engine.begin() as conn:
        rows, hashes = find(conn)
        if not rows:
            print("  Nothing to purge.")
            return

        total_bytes = sum(int(r[2] or 0) for r in rows)
        print(f"  rows matching a container Data/<link>: {len(rows):,}")
        print(f"  size they claim between them:          {total_bytes/1e12:.2f} TB")
        print(f"  distinct content hashes:               {len(hashes)}")
        by_leaf = {}
        for _, path, size, _ in rows:
            leaf = path.rsplit("/", 1)[-1]
            n, b = by_leaf.get(leaf, (0, 0))
            by_leaf[leaf] = (n + 1, b + int(size or 0))
        print("\n    leaf            count        claimed bytes")
        for leaf, (n, b) in sorted(by_leaf.items(), key=lambda kv: -kv[1][1]):
            print(f"    {leaf:<14}{n:>7}{b/1e12:>17.2f} TB")

        droppable = hashes_only_used_here(conn, hashes)
        res = conn.execute(text("""
            SELECT hash FROM duplicate_resolutions""")).fetchall()
        res_hashes = {r[0] for r in res}
        to_drop = sorted(droppable & res_hashes)
        kept = sorted((hashes & res_hashes) - droppable)
        print(f"\n  duplicate resolutions keyed on those hashes: {len(to_drop)}")
        for h in to_drop:
            print(f"      drop   {h}")
        for h in kept:
            print(f"      KEEP   {h}  (a real file also has this hash)")

        if not args.apply:
            print("\n  Dry run. Re-run with --apply to delete.")
            return

        ids = [r[0] for r in rows]
        deleted = 0
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            deleted += conn.execute(
                text("DELETE FROM files WHERE id IN :ids").bindparams(
                    bindparam("ids", expanding=True)),
                {"ids": chunk}).rowcount

        # Any other row still pointing at a purged path as its original
        # is now dangling; clear the pointer rather than leave a lie.
        #
        # Targeted at the paths just deleted. A general "duplicate_of no
        # longer exists" sweep is a correlated subquery over 12.8M rows
        # and does not finish.
        purged_paths = [r[1] for r in rows]
        cleared = 0
        for i in range(0, len(purged_paths), 500):
            chunk = purged_paths[i:i + 500]
            cleared += conn.execute(
                text("UPDATE files SET is_duplicate = 0, duplicate_of = NULL "
                     "WHERE duplicate_of IN :ps").bindparams(
                         bindparam("ps", expanding=True)),
                {"ps": chunk}).rowcount

        dropped = 0
        if to_drop:
            dropped = conn.execute(
                text("DELETE FROM duplicate_resolutions WHERE hash IN :hs")
                .bindparams(bindparam("hs", expanding=True)),
                {"hs": to_drop}).rowcount

        print(f"\n  deleted {deleted:,} file rows")
        print(f"  cleared {cleared:,} dangling duplicate_of pointers")
        print(f"  dropped {dropped} duplicate resolution(s)")
        print("\n  The next scan re-records these paths as links, with a "
              "target and no hash.")


if __name__ == "__main__":
    main()
