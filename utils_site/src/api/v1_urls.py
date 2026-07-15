"""URL router for /api/v1/* — the post-cutover API surface.

Permission note: every tool route passes
  permission_classes=[IsAuthenticatedOrWebToken]
via as_view() so the legacy /api/<slug>/ paths remain unaffected
(they default to AllowAny per settings.REST_FRAMEWORK until P3-3).
"""

from django.urls import path
from src.api.auth.permissions import IsAuthenticatedOrWebToken
from src.api.auth.views import web_token_view
from src.api.epub_convert.views import EPUBToPDFAPIView, PDFToEPUBAPIView
from src.api.html_convert.views import HTMLToPDFAPIView, URLToPDFAPIView
from src.api.image_tools.convert_heic.views import ConvertHEICAPIView
from src.api.image_tools.convert_image.views import ConvertImageAPIView
from src.api.image_tools.optimize_image.views import OptimizeImageAPIView
from src.api.image_tools.password_protect_image.views import PasswordProtectImageAPIView
from src.api.pdf_compare.views import ComparePDFAPIView
from src.api.pdf_convert.excel_to_pdf.views import ExcelToPDFAPIView
from src.api.pdf_convert.jpg_to_pdf.views import JPGToPDFAPIView
from src.api.pdf_convert.pdf_to_excel.views import PDFToExcelAPIView
from src.api.pdf_convert.pdf_to_html.views import PDFToHTMLAPIView
from src.api.pdf_convert.pdf_to_jpg.views import PDFToJPGAPIView
from src.api.pdf_convert.pdf_to_markdown.views import PDFToMarkdownAPIView
from src.api.pdf_convert.pdf_to_ppt.views import PDFToPowerPointAPIView
from src.api.pdf_convert.pdf_to_text.views import PDFToTextAPIView
from src.api.pdf_convert.pdf_to_word.views import PDFToWordAPIView
from src.api.pdf_convert.ppt_to_pdf.views import PowerPointToPDFAPIView
from src.api.pdf_convert.word_to_pdf.views import WordToPDFAPIView
from src.api.pdf_edit.add_page_numbers.views import AddPageNumbersAPIView
from src.api.pdf_edit.add_watermark.views import AddWatermarkAPIView
from src.api.pdf_edit.crop_pdf.views import CropPDFAPIView
from src.api.pdf_edit.flatten_pdf.views import FlattenPDFAPIView
from src.api.pdf_edit.rotate_pdf.views import RotatePDFAPIView
from src.api.pdf_edit.sign_pdf.views import SignPDFAPIView
from src.api.pdf_organize.compress_pdf.views import CompressPDFAPIView
from src.api.pdf_organize.extract_pages.views import ExtractPagesAPIView
from src.api.pdf_organize.merge_pdf.views import MergePDFAPIView
from src.api.pdf_organize.organize_pdf.views import OrganizePDFAPIView
from src.api.pdf_organize.remove_pages.views import RemovePagesAPIView
from src.api.pdf_organize.split_pdf.views import SplitPDFAPIView
from src.api.pdf_security.protect_pdf.views import ProtectPDFAPIView
from src.api.pdf_security.unlock_pdf.views import UnlockPDFAPIView
from src.feedback.views import FeedbackAPIView

# Shorthand to keep each route terse.
_perm = {"permission_classes": [IsAuthenticatedOrWebToken]}

urlpatterns = [
    path("auth/web-token", web_token_view, name="v1_web_token"),
    # Tool feedback (anonymous-friendly; signed feedback_token is the abuse gate)
    path("feedback/", FeedbackAPIView.as_view(), name="v1_feedback"),
    # PDF convert endpoints
    path("pdf-to-word/", PDFToWordAPIView.as_view(**_perm), name="v1_pdf_to_word"),
    path("word-to-pdf/", WordToPDFAPIView.as_view(**_perm), name="v1_word_to_pdf"),
    path("excel-to-pdf/", ExcelToPDFAPIView.as_view(**_perm), name="v1_excel_to_pdf"),
    path("ppt-to-pdf/", PowerPointToPDFAPIView.as_view(**_perm), name="v1_ppt_to_pdf"),
    path("html-to-pdf/", HTMLToPDFAPIView.as_view(**_perm), name="v1_html_to_pdf"),
    path("epub-to-pdf/", EPUBToPDFAPIView.as_view(**_perm), name="v1_epub_to_pdf"),
    path("pdf-to-epub/", PDFToEPUBAPIView.as_view(**_perm), name="v1_pdf_to_epub"),
    path("url-to-pdf/", URLToPDFAPIView.as_view(**_perm), name="v1_url_to_pdf"),
    path("jpg-to-pdf/", JPGToPDFAPIView.as_view(**_perm), name="v1_jpg_to_pdf"),
    path("pdf-to-jpg/", PDFToJPGAPIView.as_view(**_perm), name="v1_pdf_to_jpg"),
    path("pdf-to-excel/", PDFToExcelAPIView.as_view(**_perm), name="v1_pdf_to_excel"),
    path("pdf-to-ppt/", PDFToPowerPointAPIView.as_view(**_perm), name="v1_pdf_to_ppt"),
    path("pdf-to-html/", PDFToHTMLAPIView.as_view(**_perm), name="v1_pdf_to_html"),
    path(
        "pdf-to-markdown/",
        PDFToMarkdownAPIView.as_view(**_perm),
        name="v1_pdf_to_markdown",
    ),
    path("pdf-to-text/", PDFToTextAPIView.as_view(**_perm), name="v1_pdf_to_text"),
    path("compare-pdf/", ComparePDFAPIView.as_view(**_perm), name="v1_compare_pdf"),
    # PDF edit endpoints
    path("pdf-edit/rotate/", RotatePDFAPIView.as_view(**_perm), name="v1_rotate_pdf"),
    path(
        "pdf-edit/add-page-numbers/",
        AddPageNumbersAPIView.as_view(**_perm),
        name="v1_add_page_numbers",
    ),
    path(
        "pdf-edit/add-watermark/",
        AddWatermarkAPIView.as_view(**_perm),
        name="v1_add_watermark",
    ),
    path("pdf-edit/crop/", CropPDFAPIView.as_view(**_perm), name="v1_crop_pdf"),
    path("pdf-edit/sign/", SignPDFAPIView.as_view(**_perm), name="v1_sign_pdf"),
    path(
        "pdf-edit/flatten/", FlattenPDFAPIView.as_view(**_perm), name="v1_flatten_pdf"
    ),
    # PDF organize endpoints
    path("pdf-organize/merge/", MergePDFAPIView.as_view(**_perm), name="v1_merge_pdf"),
    path("pdf-organize/split/", SplitPDFAPIView.as_view(**_perm), name="v1_split_pdf"),
    path(
        "pdf-organize/remove-pages/",
        RemovePagesAPIView.as_view(**_perm),
        name="v1_remove_pages",
    ),
    path(
        "pdf-organize/extract-pages/",
        ExtractPagesAPIView.as_view(**_perm),
        name="v1_extract_pages",
    ),
    path(
        "pdf-organize/organize/",
        OrganizePDFAPIView.as_view(**_perm),
        name="v1_organize_pdf",
    ),
    path(
        "pdf-organize/compress/",
        CompressPDFAPIView.as_view(**_perm),
        name="v1_compress_pdf",
    ),
    # PDF security endpoints
    path(
        "pdf-security/protect/",
        ProtectPDFAPIView.as_view(**_perm),
        name="v1_protect_pdf",
    ),
    path(
        "pdf-security/unlock/",
        UnlockPDFAPIView.as_view(**_perm),
        name="v1_unlock_pdf",
    ),
    # Image tool endpoints
    path(
        "image/optimize/",
        OptimizeImageAPIView.as_view(**_perm),
        name="v1_optimize_image",
    ),
    path(
        "image/convert/",
        ConvertImageAPIView.as_view(**_perm),
        name="v1_convert_image",
    ),
    path(
        "image/heic-convert/",
        ConvertHEICAPIView.as_view(**_perm),
        name="v1_convert_heic",
    ),
    path(
        "image-tools/password-protect-image/",
        PasswordProtectImageAPIView.as_view(**_perm),
        name="v1_password_protect_image",
    ),
]
