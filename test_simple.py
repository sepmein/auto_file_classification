#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, ".")

try:
    from ods.review.review_manager import ReviewManager

    print("✅ ReviewManager import successful")
except ImportError as e:
    print(f"❌ ReviewManager import failed: {e}")

try:
    from tests.test_review.test_review_manager import TestReviewManager

    print("✅ TestReviewManager import successful")
except ImportError as e:
    print(f"❌ TestReviewManager import failed: {e}")

try:
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestReviewManager)
    print(f"✅ Test suite loaded with {suite.countTestCases()} tests")
except Exception as e:
    print(f"❌ Test loading failed: {e}")
