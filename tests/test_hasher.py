#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: test_hasher.py
# Purpose: Unit tests for the hasher module.
#
# Author: Tim Canady
# Created: 2025-09-28
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial test logic for hasher — Tim Canady
###################################################################

import unittest
from pathlib import Path
from core.hasher import generate_hashes
from models.file_info import FileInfo


class TestHasher(unittest.TestCase):
    def test_generate_hashes(self):
        sample_file = Path("tests/test_data/sample1.txt")
        file_info = FileInfo(path=sample_file, size=sample_file.stat().st_size)
        hashed_files = generate_hashes([file_info])
        self.assertIsNotNone(hashed_files[0].hash)
        self.assertEqual(len(hashed_files), 1)


if __name__ == '__main__':
    unittest.main()