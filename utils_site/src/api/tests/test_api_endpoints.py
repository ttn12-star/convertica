"""
Integration tests for API endpoints.
"""
import os
import tempfile
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status


class APIEndpointsTestCase(TestCase):
    """Integration tests for conversion API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_pdf(self) -> SimpleUploadedFile:
        """Create a minimal valid PDF file for testing."""
        # Minimal valid PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF"""
        return SimpleUploadedFile(
            "test.pdf",
            pdf_content,
            content_type="application/pdf"
        )
    
    def _create_test_image(self) -> SimpleUploadedFile:
        """Create a minimal valid JPG file for testing."""
        # Minimal valid JPEG (just header, not a real image)
        # In real tests, you'd use a proper image file
        jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'
        return SimpleUploadedFile(
            "test.jpg",
            jpg_content,
            content_type="image/jpeg"
        )
    
    def test_pdf_to_word_endpoint_exists(self):
        """Test that PDF to Word endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-to-word/',
            {'pdf_file': pdf_file},
            format='multipart'
        )
        # Should either succeed or return a proper error (not 404)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_word_to_pdf_endpoint_exists(self):
        """Test that Word to PDF endpoint exists and responds."""
        # Create a minimal DOCX file (ZIP structure)
        import zipfile
        import io
        
        docx_content = io.BytesIO()
        with zipfile.ZipFile(docx_content, 'w') as zf:
            zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types></Types>')
            zf.writestr('word/document.xml', '<?xml version="1.0"?><document></document>')
        
        docx_file = SimpleUploadedFile(
            "test.docx",
            docx_content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        response = self.client.post(
            '/api/word-to-pdf/',
            {'word_file': docx_file},
            format='multipart'
        )
        # Should either succeed or return a proper error (not 404)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_pdf_to_jpg_endpoint_exists(self):
        """Test that PDF to JPG endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-to-jpg/',
            {'pdf_file': pdf_file, 'page': 1, 'dpi': 300},
            format='multipart'
        )
        # Should either succeed or return a proper error (not 404)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_jpg_to_pdf_endpoint_exists(self):
        """Test that JPG to PDF endpoint exists and responds."""
        jpg_file = self._create_test_image()
        response = self.client.post(
            '/api/jpg-to-pdf/',
            {'image_file': jpg_file},
            format='multipart'
        )
        # Should either succeed or return a proper error (not 404)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_pdf_to_word_validation_empty_file(self):
        """Test validation of empty file."""
        empty_file = SimpleUploadedFile(
            "empty.pdf",
            b"",
            content_type="application/pdf"
        )
        response = self.client.post(
            '/api/pdf-to-word/',
            {'pdf_file': empty_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_pdf_to_jpg_validation_dpi_range(self):
        """Test DPI validation for PDF to JPG."""
        pdf_file = self._create_test_pdf()
        
        # Test DPI too low
        response = self.client.post(
            '/api/pdf-to-jpg/',
            {'pdf_file': pdf_file, 'dpi': 50},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test DPI too high
        response = self.client.post(
            '/api/pdf-to-jpg/',
            {'pdf_file': pdf_file, 'dpi': 1000},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_rotate_pdf_endpoint_exists(self):
        """Test that Rotate PDF endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-edit/rotate/',
            {'pdf_file': pdf_file, 'angle': 90, 'pages': 'all'},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_merge_pdf_endpoint_exists(self):
        """Test that Merge PDF endpoint exists and responds."""
        pdf_file1 = self._create_test_pdf()
        pdf_file2 = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-organize/merge/',
            {'pdf_files': [pdf_file1, pdf_file2], 'order': 'upload'},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_split_pdf_endpoint_exists(self):
        """Test that Split PDF endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-organize/split/',
            {'pdf_file': pdf_file, 'split_type': 'page', 'pages': '1'},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_remove_pages_endpoint_exists(self):
        """Test that Remove Pages endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-organize/remove-pages/',
            {'pdf_file': pdf_file, 'pages': '1'},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_extract_pages_endpoint_exists(self):
        """Test that Extract Pages endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-organize/extract-pages/',
            {'pdf_file': pdf_file, 'pages': '1'},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_add_watermark_endpoint_exists(self):
        """Test that Add Watermark endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-edit/add-watermark/',
            {'pdf_file': pdf_file, 'watermark_text': 'TEST', 'opacity': 0.5},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_add_page_numbers_endpoint_exists(self):
        """Test that Add Page Numbers endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-edit/add-page-numbers/',
            {'pdf_file': pdf_file, 'position': 'bottom-center', 'font_size': 12},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_crop_pdf_endpoint_exists(self):
        """Test that Crop PDF endpoint exists and responds."""
        pdf_file = self._create_test_pdf()
        response = self.client.post(
            '/api/pdf-edit/crop/',
            {'pdf_file': pdf_file, 'x': 0, 'y': 0, 'width': 100, 'height': 100},
            format='multipart'
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

