"""
Unit tests for file validation utilities.
"""

import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from src.api.file_validation import (
    check_disk_space,
    sanitize_filename,
    validate_output_file,
    validate_pdf_file,
    validate_word_file,
)


class FileValidationTestCase(TestCase):
    """Test cases for file validation functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.context = {"test": True}

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test special characters
        result = sanitize_filename("test@file#name$.pdf")
        self.assertEqual(result, "test_file_name_.pdf")

        # Test path components
        result = sanitize_filename("/path/to/file.pdf")
        self.assertEqual(result, "file.pdf")

        # Test empty filename
        result = sanitize_filename("")
        self.assertEqual(result, "file")

        # Test long filename
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        self.assertLessEqual(len(result), 200)
        self.assertTrue(result.endswith(".pdf"))

    def test_check_disk_space(self):
        """Test disk space checking."""
        has_space, error = check_disk_space(self.temp_dir, required_mb=1)
        # Should pass (1 MB is very small)
        self.assertTrue(has_space)
        self.assertIsNone(error)

        # Test with very large requirement (should fail on most systems)
        has_space, error = check_disk_space(self.temp_dir, required_mb=1000000)
        # May pass or fail depending on system
        self.assertIsInstance(has_space, bool)

    def test_validate_output_file(self):
        """Test output file validation."""
        # Test non-existent file
        fake_path = os.path.join(self.temp_dir, "nonexistent.pdf")
        is_valid, error = validate_output_file(fake_path, context={})
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)

        # Test empty file
        empty_file = os.path.join(self.temp_dir, "empty.pdf")
        with open(empty_file, "w") as f:
            pass  # Create empty file
        is_valid, error = validate_output_file(empty_file, context={})
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

        # Test valid file
        valid_file = os.path.join(self.temp_dir, "valid.pdf")
        with open(valid_file, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"x" * 1000)  # Valid PDF header + content
        is_valid, error = validate_output_file(valid_file, context={})
        self.assertTrue(is_valid)
        self.assertIsNone(error)
