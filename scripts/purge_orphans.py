#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: purge_orphans.py
# Purpose: Remove child rows whose file row is gone
#
# Description:
# scripts/purge_symlink_rows.py deleted 5,639 rows from `files` that
# had been created by following symlinks. It did not delete their
# classifications, which are now orphaned: they describe a file row
# that no longer exists and nothing will ever read them again.
#
# Also removes rows left behind by scratch runs under /tmp and
# /folders, which are test artefacts rather than inventory.
#
# Deliberately batched by primary key. The anti-join over 10.4M
# classifications is one long query, and this is housekeeping worth a
# few megabytes: it must not contend with a scan that is running.
#
# Author: Tim Canady
# Created: 2026-10-04
#
# Version: 1.0.0
# Last Modified: 2026-10-04 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-10-04): Initial orphan cleanup — Tim Canady
###################################################################

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text                                   # noqa: E402

from core.db import engine                                    # noqa: E402

BATCH = 250_000          # primary-key window per query
PAUSE = 0.05             # breathe between windows, for a concurrent scan

# Child tables and the column pointing at files.id. file_tags,
# image_metadata and image_analysis_errors declare real foreign keys, so
# the database already removed their rows; classifications does not.
CHILDREN = (("classifications", "file_id"),
            ("file_tags", "file_id"),
            ("image_metadata", "file_id"),
            ("image_analysis_errors", "file_id"))

# Scratch roots from test runs, not inventory.
TEST_ROOTS = ("/tmp/%", "/private/tmp/%", "/folders/%")


def orphans(conn, table, column, apply_changes):
    """Walk the table by primary key, counting or deleting orphans."""
    top = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar()
    found = 0
    low = 0
    while low <= top:
        high = low + BATCH
        if apply_changes:
            found += conn.execute(text(f"""
                DELETE t FROM {table} t
                LEFT JOIN files f ON f.id = t.{column}
                WHERE t.id >= :lo AND t.id < :hi AND f.id IS NULL
            """), {"lo": low, "hi": high}).rowcount
        else:
            found += conn.execute(text(f"""
                SELECT COUNT(*) FROM {table} t
                LEFT JOIN files f ON f.id = t.{column}
                WHERE t.id >= :lo AND t.id < :hi AND f.id IS NULL
            """), {"lo": low, "hi": high}).scalar()
        low = high
        time.sleep(PAUSE)
    return found


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Remove child rows whose file row no longer exists.")
    ap.add_argument("--apply", action="store_true",
                    help="Actually delete. Without this it only reports.")
    args = ap.parse_args()

    total = 0
    with engine.begin() as conn:
        # Test roots FIRST. Removing them creates orphans of their own,
        # so sweeping children beforehand leaves exactly those behind:
        # the first run of this script deleted 5,639 orphans and then
        # made 6 more in the same transaction.
        for pattern in TEST_ROOTS:
            if args.apply:
                n = conn.execute(text("DELETE FROM files WHERE path LIKE :p"),
                                 {"p": pattern}).rowcount
            else:
                n = conn.execute(text("SELECT COUNT(*) FROM files WHERE path LIKE :p"),
                                 {"p": pattern}).scalar()
            if n:
                total += n
                print(f"  files under {pattern:<20}{n:>8,}")

        for table, column in CHILDREN:
            t = time.time()
            n = orphans(conn, table, column, args.apply)
            total += n
            verb = "deleted" if args.apply else "orphaned"
            print(f"  {table:<24}{n:>8,} {verb}   ({time.time()-t:.0f}s)")

    print(f"\n  total: {total:,} row(s)")
    if not args.apply:
        print("  Dry run. Re-run with --apply to delete.")


if __name__ == "__main__":
    main()
