from django.urls import path

from .pdf_convert.pdf_to_word.views import PDFToWordAPIView
from .pdf_convert.word_to_pdf.views import WordToPDFAPIView
from .pdf_convert.pdf_to_jpg.views import PDFToJPGAPIView
from .pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView
from .pdf_convert.pdf_to_excel.views import PDFToExcelAPIView
from .pdf_edit.rotate_pdf.views import RotatePDFAPIView
from .pdf_edit.add_page_numbers.views import AddPageNumbersAPIView
from .pdf_edit.add_watermark.views import AddWatermarkAPIView
from .pdf_edit.crop_pdf.views import CropPDFAPIView
from .pdf_organize.merge_pdf.views import MergePDFAPIView
from .pdf_organize.split_pdf.views import SplitPDFAPIView
from .pdf_organize.remove_pages.views import RemovePagesAPIView
from .pdf_organize.extract_pages.views import ExtractPagesAPIView
from .pdf_organize.organize_pdf.views import OrganizePDFAPIView
from .pdf_organize.compress_pdf.views import CompressPDFAPIView
from .pdf_security.protect_pdf.views import ProtectPDFAPIView
from .pdf_security.unlock_pdf.views import UnlockPDFAPIView

urlpatterns = [
    path('pdf-to-word/', PDFToWordAPIView.as_view(), name='pdf_to_word_api'),
    path('word-to-pdf/', WordToPDFAPIView.as_view(), name='word_to_pdf_api'),
    path('pdf-to-jpg/', PDFToJPGAPIView.as_view(), name='pdf_to_jpg_api'),
    path('jpg-to-pdf/', JPGToPDFAPIView.as_view(), name='jpg_to_pdf_api'),
    path('pdf-to-excel/', PDFToExcelAPIView.as_view(), name='pdf_to_excel_api'),
    # PDF Edit endpoints
    path('pdf-edit/rotate/', RotatePDFAPIView.as_view(), name='rotate_pdf_api'),
    path('pdf-edit/add-page-numbers/', AddPageNumbersAPIView.as_view(), name='add_page_numbers_api'),
    path('pdf-edit/add-watermark/', AddWatermarkAPIView.as_view(), name='add_watermark_api'),
    path('pdf-edit/crop/', CropPDFAPIView.as_view(), name='crop_pdf_api'),
    # PDF Organize endpoints
    path('pdf-organize/merge/', MergePDFAPIView.as_view(), name='merge_pdf_api'),
    path('pdf-organize/split/', SplitPDFAPIView.as_view(), name='split_pdf_api'),
    path('pdf-organize/remove-pages/', RemovePagesAPIView.as_view(), name='remove_pages_api'),
    path('pdf-organize/extract-pages/', ExtractPagesAPIView.as_view(), name='extract_pages_api'),
    path('pdf-organize/organize/', OrganizePDFAPIView.as_view(), name='organize_pdf_api'),
    path('pdf-organize/compress/', CompressPDFAPIView.as_view(), name='compress_pdf_api'),
    # PDF Security endpoints
    path('pdf-security/protect/', ProtectPDFAPIView.as_view(), name='protect_pdf_api'),
    path('pdf-security/unlock/', UnlockPDFAPIView.as_view(), name='unlock_pdf_api'),
]
