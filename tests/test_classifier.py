#!/usr/bin/env python3
#
###################################################################
# Project: File Deduplication
# File: test_classifier.py
# Purpose: Unit tests for the classifier module.
#
# Author: Tim Canady
# Created: 2025-09-28
# Version: 0.1.0
# Last Modified: 2025-11-04 by Tim Canady
#
# Revision History:
# - 0.1.0 (2025-11-04): Initial test logic for classifier — Tim Canady
###################################################################

import unittest
from pathlib import Path
from models.file_info import FileInfo
from core.classifier import classify_file


class TestClassifier(unittest.TestCase):
    def test_classifier_output_format(self):
        file = FileInfo(path=Path("tests/test_data/financial_2021_john.pdf"), size=1234)
        classified = classify_file(file)
        self.assertIsInstance(classified.type, str)
        self.assertTrue(classified.type)
        self.assertIsNotNone(classified.type)
        # self.assertTrue(classified.owner or classified.year)


if __name__ == '__main__':
    unittest.main()