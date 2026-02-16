from django.urls import path
from src.payments.views import stripe_webhook

from .async_views import TaskResultAPIView, TaskStatusAPIView
from .cancel_task_view import (
    cancel_task,
    mark_operation_abandoned,
    mark_task_background,
)
from .epub_convert.async_views import EPUBToPDFAsyncAPIView, PDFToEPUBAsyncAPIView
from .epub_convert.views import EPUBToPDFAPIView, PDFToEPUBAPIView
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
from .pdf_convert.jpg_to_pdf.batch_views import JPGToPDFBatchAPIView
from .pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView
from .pdf_convert.pdf_to_excel.batch_views import PDFToExcelBatchAPIView
from .pdf_convert.pdf_to_excel.views import PDFToExcelAPIView
from .pdf_convert.pdf_to_html.batch_views import PDFToHTMLBatchAPIView
from .pdf_convert.pdf_to_html.views import PDFToHTMLAPIView
from .pdf_convert.pdf_to_jpg.batch_views import PDFToJPGBatchAPIView
from .pdf_convert.pdf_to_jpg.views import PDFToJPGAPIView
from .pdf_convert.pdf_to_ppt.batch_views import PDFToPowerPointBatchAPIView
from .pdf_convert.pdf_to_ppt.views import PDFToPowerPointAPIView
from .pdf_convert.pdf_to_word.batch_views import PDFToWordBatchAPIView
from .pdf_convert.pdf_to_word.views import PDFToWordAPIView
from .pdf_convert.ppt_to_pdf.batch_views import PowerPointToPDFBatchAPIView
from .pdf_convert.ppt_to_pdf.views import PowerPointToPDFAPIView
from .pdf_convert.word_to_pdf.batch_views import WordToPDFBatchAPIView
from .pdf_convert.word_to_pdf.views import WordToPDFAPIView
from .pdf_edit.add_page_numbers.batch_views import AddPageNumbersBatchAPIView
from .pdf_edit.add_page_numbers.views import AddPageNumbersAPIView
from .pdf_edit.add_watermark.batch_views import AddWatermarkBatchAPIView
from .pdf_edit.add_watermark.views import AddWatermarkAPIView
from .pdf_edit.crop_pdf.batch_views import CropPDFBatchAPIView
from .pdf_edit.crop_pdf.views import CropPDFAPIView
from .pdf_edit.rotate_pdf.views import RotatePDFAPIView
from .pdf_organize.async_views import CompressPDFAsyncAPIView
from .pdf_organize.compress_pdf.batch_views import CompressPDFBatchAPIView
from .pdf_organize.compress_pdf.views import CompressPDFAPIView
from .pdf_organize.extract_pages.batch_views import ExtractPagesBatchAPIView
from .pdf_organize.extract_pages.views import ExtractPagesAPIView
from .pdf_organize.merge_pdf.views import MergePDFAPIView
from .pdf_organize.organize_pdf.batch_views import OrganizePDFBatchAPIView
from .pdf_organize.organize_pdf.views import OrganizePDFAPIView
from .pdf_organize.remove_pages.batch_views import RemovePagesBatchAPIView
from .pdf_organize.remove_pages.views import RemovePagesAPIView
from .pdf_organize.split_pdf.batch_views import SplitPDFBatchAPIView
from .pdf_organize.split_pdf.views import SplitPDFAPIView
from .pdf_security.protect_pdf.batch_views import ProtectPDFBatchAPIView
from .pdf_security.protect_pdf.views import ProtectPDFAPIView
from .pdf_security.unlock_pdf.batch_views import UnlockPDFBatchAPIView
from .pdf_security.unlock_pdf.views import UnlockPDFAPIView
from .user_info_view import UserInfoAPIView

urlpatterns = [
    # User info endpoint
    path("user-info/", UserInfoAPIView.as_view(), name="user_info_api"),
    # Stripe webhook endpoint (for Stripe CLI local testing)
    path("payments/webhook/", stripe_webhook, name="api_stripe_webhook"),
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
    path("task-background/", mark_task_background, name="task_background"),
    # Sync endpoints (for small files / fast operations)
    path("pdf-to-word/", PDFToWordAPIView.as_view(), name="pdf_to_word_api"),
    path("word-to-pdf/", WordToPDFAPIView.as_view(), name="word_to_pdf_api"),
    path("excel-to-pdf/", ExcelToPDFAPIView.as_view(), name="excel_to_pdf_api"),
    path("ppt-to-pdf/", PowerPointToPDFAPIView.as_view(), name="ppt_to_pdf_api"),
    path("html-to-pdf/", HTMLToPDFAPIView.as_view(), name="html_to_pdf_api"),
    path("epub-to-pdf/", EPUBToPDFAPIView.as_view(), name="epub_to_pdf_api"),
    path("pdf-to-epub/", PDFToEPUBAPIView.as_view(), name="pdf_to_epub_api"),
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
    # PDF Edit batch endpoints
    path(
        "pdf-edit/crop/batch/",
        CropPDFBatchAPIView.as_view(),
        name="crop_pdf_batch_api",
    ),
    path(
        "pdf-edit/add-watermark/batch/",
        AddWatermarkBatchAPIView.as_view(),
        name="add_watermark_batch_api",
    ),
    path(
        "pdf-edit/add-page-numbers/batch/",
        AddPageNumbersBatchAPIView.as_view(),
        name="add_page_numbers_batch_api",
    ),
    # Converter batch endpoints
    path(
        "pdf-to-word/batch/",
        PDFToWordBatchAPIView.as_view(),
        name="pdf_to_word_batch_api",
    ),
    path(
        "word-to-pdf/batch/",
        WordToPDFBatchAPIView.as_view(),
        name="word_to_pdf_batch_api",
    ),
    path(
        "pdf-to-jpg/batch/",
        PDFToJPGBatchAPIView.as_view(),
        name="pdf_to_jpg_batch_api",
    ),
    path(
        "jpg-to-pdf/batch/",
        JPGToPDFBatchAPIView.as_view(),
        name="jpg_to_pdf_batch_api",
    ),
    path(
        "pdf-to-excel/batch/",
        PDFToExcelBatchAPIView.as_view(),
        name="pdf_to_excel_batch_api",
    ),
    path(
        "pdf-to-ppt/batch/",
        PDFToPowerPointBatchAPIView.as_view(),
        name="pdf_to_ppt_batch_api",
    ),
    path(
        "pdf-to-html/batch/",
        PDFToHTMLBatchAPIView.as_view(),
        name="pdf_to_html_batch_api",
    ),
    # PDF Organize batch endpoints
    path(
        "pdf-organize/compress/batch/",
        CompressPDFBatchAPIView.as_view(),
        name="compress_pdf_batch_api",
    ),
    path(
        "pdf-organize/split/batch/",
        SplitPDFBatchAPIView.as_view(),
        name="split_pdf_batch_api",
    ),
    path(
        "pdf-organize/extract-pages/batch/",
        ExtractPagesBatchAPIView.as_view(),
        name="extract_pages_batch_api",
    ),
    path(
        "pdf-organize/remove-pages/batch/",
        RemovePagesBatchAPIView.as_view(),
        name="remove_pages_batch_api",
    ),
    path(
        "pdf-organize/organize/batch/",
        OrganizePDFBatchAPIView.as_view(),
        name="organize_pdf_batch_api",
    ),
    # PDF Security batch endpoints
    path(
        "pdf-security/protect/batch/",
        ProtectPDFBatchAPIView.as_view(),
        name="protect_pdf_batch_api",
    ),
    path(
        "pdf-security/unlock/batch/",
        UnlockPDFBatchAPIView.as_view(),
        name="unlock_pdf_batch_api",
    ),
    path("pdf-to-jpg/", PDFToJPGAPIView.as_view(), name="pdf_to_jpg_api"),
    path("jpg-to-pdf/", JPGToPDFAPIView.as_view(), name="jpg_to_pdf_api"),
    path("pdf-to-excel/", PDFToExcelAPIView.as_view(), name="pdf_to_excel_api"),
    path("pdf-to-ppt/", PDFToPowerPointAPIView.as_view(), name="pdf_to_ppt_api"),
    path("pdf-to-html/", PDFToHTMLAPIView.as_view(), name="pdf_to_html_api"),
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
    path(
        "epub-to-pdf/async/",
        EPUBToPDFAsyncAPIView.as_view(),
        name="epub_to_pdf_async_api",
    ),
    path(
        "pdf-to-epub/async/",
        PDFToEPUBAsyncAPIView.as_view(),
        name="pdf_to_epub_async_api",
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
