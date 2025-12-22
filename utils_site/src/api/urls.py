from django.urls import path

from .async_views import TaskResultAPIView, TaskStatusAPIView
from .cancel_task_view import cancel_task, mark_operation_abandoned
from .html_convert.batch_views import HTMLToPDFBatchAPIView
from .html_convert.views import HTMLToPDFAPIView, URLToPDFAPIView
from .pdf_convert.async_views import (
    PDFToExcelAsyncAPIView,
    PDFToJPGAsyncAPIView,
    PDFToWordAsyncAPIView,
    WordToPDFAsyncAPIView,
)
from .pdf_convert.excel_to_pdf.batch_views import ExcelToPDFBatchAPIView
from .pdf_convert.excel_to_pdf.views import ExcelToPDFAPIView
from .pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView
from .pdf_convert.pdf_to_excel.views import PDFToExcelAPIView
from .pdf_convert.pdf_to_jpg.views import PDFToJPGAPIView
from .pdf_convert.pdf_to_word.views import PDFToWordAPIView
from .pdf_convert.ppt_to_pdf.batch_views import PowerPointToPDFBatchAPIView
from .pdf_convert.ppt_to_pdf.views import PowerPointToPDFAPIView
from .pdf_convert.word_to_pdf.views import WordToPDFAPIView
from .pdf_edit.add_page_numbers.views import AddPageNumbersAPIView
from .pdf_edit.add_watermark.views import AddWatermarkAPIView
from .pdf_edit.crop_pdf.views import CropPDFAPIView
from .pdf_edit.rotate_pdf.views import RotatePDFAPIView
from .pdf_organize.async_views import CompressPDFAsyncAPIView
from .pdf_organize.compress_pdf.views import CompressPDFAPIView
from .pdf_organize.extract_pages.views import ExtractPagesAPIView
from .pdf_organize.merge_pdf.views import MergePDFAPIView
from .pdf_organize.organize_pdf.views import OrganizePDFAPIView
from .pdf_organize.remove_pages.views import RemovePagesAPIView
from .pdf_organize.split_pdf.views import SplitPDFAPIView
from .pdf_security.protect_pdf.views import ProtectPDFAPIView
from .pdf_security.unlock_pdf.views import UnlockPDFAPIView

urlpatterns = [
    # Async task endpoints (for progress polling and result download)
    path(
        "tasks/<str:task_id>/status/", TaskStatusAPIView.as_view(), name="task_status"
    ),
    path(
        "tasks/<str:task_id>/result/", TaskResultAPIView.as_view(), name="task_result"
    ),
    # Cancel running task
    path("cancel-task/", cancel_task, name="cancel_task"),
    path("operation-abandon/", mark_operation_abandoned, name="operation_abandon"),
    # Sync endpoints (for small files / fast operations)
    path("pdf-to-word/", PDFToWordAPIView.as_view(), name="pdf_to_word_api"),
    path("word-to-pdf/", WordToPDFAPIView.as_view(), name="word_to_pdf_api"),
    path("excel-to-pdf/", ExcelToPDFAPIView.as_view(), name="excel_to_pdf_api"),
    path("ppt-to-pdf/", PowerPointToPDFAPIView.as_view(), name="ppt_to_pdf_api"),
    path("html-to-pdf/", HTMLToPDFAPIView.as_view(), name="html_to_pdf_api"),
    path("url-to-pdf/", URLToPDFAPIView.as_view(), name="url_to_pdf_api"),
    # Batch endpoints for premium users
    path(
        "excel-to-pdf/batch/",
        ExcelToPDFBatchAPIView.as_view(),
        name="excel_to_pdf_batch_api",
    ),
    path(
        "ppt-to-pdf/batch/",
        PowerPointToPDFBatchAPIView.as_view(),
        name="ppt_to_pdf_batch_api",
    ),
    path(
        "html-to-pdf/batch/",
        HTMLToPDFBatchAPIView.as_view(),
        name="html_to_pdf_batch_api",
    ),
    path("pdf-to-jpg/", PDFToJPGAPIView.as_view(), name="pdf_to_jpg_api"),
    path("jpg-to-pdf/", JPGToPDFAPIView.as_view(), name="jpg_to_pdf_api"),
    path("pdf-to-excel/", PDFToExcelAPIView.as_view(), name="pdf_to_excel_api"),
    # Async endpoints (for large files / heavy operations - avoids Cloudflare timeout)
    path(
        "pdf-to-word/async/",
        PDFToWordAsyncAPIView.as_view(),
        name="pdf_to_word_async_api",
    ),
    path(
        "word-to-pdf/async/",
        WordToPDFAsyncAPIView.as_view(),
        name="word_to_pdf_async_api",
    ),
    path(
        "pdf-to-excel/async/",
        PDFToExcelAsyncAPIView.as_view(),
        name="pdf_to_excel_async_api",
    ),
    path(
        "pdf-to-jpg/async/",
        PDFToJPGAsyncAPIView.as_view(),
        name="pdf_to_jpg_async_api",
    ),
    # PDF Edit endpoints
    path("pdf-edit/rotate/", RotatePDFAPIView.as_view(), name="rotate_pdf_api"),
    path(
        "pdf-edit/add-page-numbers/",
        AddPageNumbersAPIView.as_view(),
        name="add_page_numbers_api",
    ),
    path(
        "pdf-edit/add-watermark/",
        AddWatermarkAPIView.as_view(),
        name="add_watermark_api",
    ),
    path("pdf-edit/crop/", CropPDFAPIView.as_view(), name="crop_pdf_api"),
    # PDF Organize endpoints
    path("pdf-organize/merge/", MergePDFAPIView.as_view(), name="merge_pdf_api"),
    path("pdf-organize/split/", SplitPDFAPIView.as_view(), name="split_pdf_api"),
    path(
        "pdf-organize/remove-pages/",
        RemovePagesAPIView.as_view(),
        name="remove_pages_api",
    ),
    path(
        "pdf-organize/extract-pages/",
        ExtractPagesAPIView.as_view(),
        name="extract_pages_api",
    ),
    path(
        "pdf-organize/organize/", OrganizePDFAPIView.as_view(), name="organize_pdf_api"
    ),
    path(
        "pdf-organize/compress/", CompressPDFAPIView.as_view(), name="compress_pdf_api"
    ),
    path(
        "pdf-organize/compress/async/",
        CompressPDFAsyncAPIView.as_view(),
        name="compress_pdf_async_api",
    ),
    # PDF Security endpoints
    path("pdf-security/protect/", ProtectPDFAPIView.as_view(), name="protect_pdf_api"),
    path("pdf-security/unlock/", UnlockPDFAPIView.as_view(), name="unlock_pdf_api"),
]
