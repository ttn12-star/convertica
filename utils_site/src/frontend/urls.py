from django.urls import path

from . import views
from .views import PricingPageView, SupportPageView, SupportSuccessPageView

app_name = "frontend"

urlpatterns = [
    path("", views.index_page, name="index_page_lang"),
    path("all-tools/", views.all_tools_page, name="all_tools_page"),
    path("premium-tools/", views.premium_tools_page, name="premium_tools_page"),
    # PDF Conversion pages
    path("pdf-to-word/", views.pdf_to_word_page, name="pdf_to_word_page"),
    path("word-to-pdf/", views.word_to_pdf_page, name="word_to_pdf_page"),
    path("pdf-to-jpg/", views.pdf_to_jpg_page, name="pdf_to_jpg_page"),
    path("jpg-to-pdf/", views.jpg_to_pdf_page, name="jpg_to_pdf_page"),
    path("pdf-to-excel/", views.pdf_to_excel_page, name="pdf_to_excel_page"),
    path("excel-to-pdf/", views.excel_to_pdf_page, name="excel_to_pdf_page"),
    path("ppt-to-pdf/", views.ppt_to_pdf_page, name="ppt_to_pdf_page"),
    path("html-to-pdf/", views.html_to_pdf_page, name="html_to_pdf_page"),
    path("pdf-to-ppt/", views.pdf_to_ppt_page, name="pdf_to_ppt_page"),
    path("pdf-to-html/", views.pdf_to_html_page, name="pdf_to_html_page"),
    path("epub-to-pdf/", views.epub_to_pdf_page, name="epub_to_pdf_page"),
    path("pdf-to-epub/", views.pdf_to_epub_page, name="pdf_to_epub_page"),
    path(
        "scanned-pdf-to-word/",
        views.ocr_pdf_to_word_page,
        name="ocr_pdf_to_word_page",
    ),
    path("batch-converter/", views.batch_converter_page, name="batch_converter_page"),
    path(
        "premium/workflows/",
        views.premium_workflows_page,
        name="premium_workflows_page",
    ),
    path(
        "premium/background-center/",
        views.background_center_page,
        name="background_center_page",
    ),
    # PDF Edit pages
    path("pdf-edit/rotate/", views.rotate_pdf_page, name="rotate_pdf_page"),
    path(
        "pdf-edit/add-page-numbers/",
        views.add_page_numbers_page,
        name="add_page_numbers_page",
    ),
    path(
        "pdf-edit/add-watermark/", views.add_watermark_page, name="add_watermark_page"
    ),
    path("pdf-edit/crop/", views.crop_pdf_page, name="crop_pdf_page"),
    # PDF Organize pages
    path("pdf-organize/merge/", views.merge_pdf_page, name="merge_pdf_page"),
    path("pdf-organize/split/", views.split_pdf_page, name="split_pdf_page"),
    path(
        "pdf-organize/remove-pages/", views.remove_pages_page, name="remove_pages_page"
    ),
    path(
        "pdf-organize/extract-pages/",
        views.extract_pages_page,
        name="extract_pages_page",
    ),
    path("pdf-organize/organize/", views.organize_pdf_page, name="organize_pdf_page"),
    path("pdf-organize/compress/", views.compress_pdf_page, name="compress_pdf_page"),
    # PDF Security pages
    path("pdf-security/protect/", views.protect_pdf_page, name="protect_pdf_page"),
    path("pdf-security/unlock/", views.unlock_pdf_page, name="unlock_pdf_page"),
    # Static pages
    path("pricing/", PricingPageView.as_view(), name="pricing"),
    path("contribute/", SupportPageView.as_view(), name="contribute"),
    path(
        "contribute/success/",
        SupportSuccessPageView.as_view(),
        name="contribute_success",
    ),
    path("about/", views.about_page, name="about_page"),
    path("privacy/", views.privacy_page, name="privacy_page"),
    path("terms/", views.terms_page, name="terms_page"),
    path("contact/", views.contact_page, name="contact_page"),
    path("faq/", views.faq_page, name="faq_page"),
]
