#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: test_executor.py
# Purpose: Unit tests for the executor module.
#
# Author: Tim Canady
# Created: 2025-09-28
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial test logic for executor — Tim Canady
###################################################################

import unittest
import shutil
from pathlib import Path
from core.executor import execute_plan
from models.file_info import FileInfo

class TestExecutor(unittest.TestCase):
    def setUp(self):
        self.target_dir = Path("tests/test_output")
        self.source_file = Path("tests/test_data/execute_sample.txt")
        self.source_file.write_text("test")
        self.file_info = FileInfo(path=self.source_file, size=self.source_file.stat().st_size)

    def tearDown(self):
        if self.target_dir.exists():
            shutil.rmtree(self.target_dir)
        if self.source_file.exists():
            self.source_file.unlink()

    def test_execute_moves_file(self):
        plan = {self.target_dir: [self.file_info]}
        execute_plan(plan, delete_duplicates=False)
        expected_target = self.target_dir / self.source_file.name
        self.assertTrue(expected_target.exists())

if __name__ == '__main__':
    unittest.main()