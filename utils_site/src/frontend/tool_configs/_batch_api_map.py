"""Batch API routing map for Convertica PDF tools."""

# Batch API routing: api_url_name -> batch endpoint + field name
BATCH_API_MAP = BATCH_API_MAP = {
    "excel_to_pdf_api": {
        "batch_url": "excel_to_pdf_batch_api",
        "field_name": "excel_files",
    },
    "ppt_to_pdf_api": {"batch_url": "ppt_to_pdf_batch_api", "field_name": "ppt_files"},
    "pdf_to_word_api": {
        "batch_url": "pdf_to_word_batch_api",
        "field_name": "pdf_files",
    },
    "word_to_pdf_api": {
        "batch_url": "word_to_pdf_batch_api",
        "field_name": "word_files",
    },
    "pdf_to_jpg_api": {"batch_url": "pdf_to_jpg_batch_api", "field_name": "pdf_files"},
    "jpg_to_pdf_api": {
        "batch_url": "jpg_to_pdf_batch_api",
        "field_name": "image_files",
    },
    "pdf_to_excel_api": {
        "batch_url": "pdf_to_excel_batch_api",
        "field_name": "pdf_files",
    },
    "pdf_to_ppt_api": {"batch_url": "pdf_to_ppt_batch_api", "field_name": "pdf_files"},
    "pdf_to_html_api": {
        "batch_url": "pdf_to_html_batch_api",
        "field_name": "pdf_files",
    },
    "crop_pdf_api": {"batch_url": "crop_pdf_batch_api", "field_name": "pdf_files"},
    "add_watermark_api": {
        "batch_url": "add_watermark_batch_api",
        "field_name": "pdf_files",
    },
    "add_page_numbers_api": {
        "batch_url": "add_page_numbers_batch_api",
        "field_name": "pdf_files",
    },
    "compress_pdf_api": {
        "batch_url": "compress_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "split_pdf_api": {"batch_url": "split_pdf_batch_api", "field_name": "pdf_files"},
    "extract_pages_api": {
        "batch_url": "extract_pages_batch_api",
        "field_name": "pdf_files",
    },
    "remove_pages_api": {
        "batch_url": "remove_pages_batch_api",
        "field_name": "pdf_files",
    },
    "organize_pdf_api": {
        "batch_url": "organize_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "protect_pdf_api": {
        "batch_url": "protect_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "unlock_pdf_api": {"batch_url": "unlock_pdf_batch_api", "field_name": "pdf_files"},
    "flatten_pdf_api": {
        "batch_url": "flatten_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "pdf_to_text_api": {
        "batch_url": "pdf_to_text_batch_api",
        "field_name": "pdf_files",
    },
    "sign_pdf_api": {
        "batch_url": "sign_pdf_batch_api",
        "field_name": "pdf_files",
    },
    "optimize_image_api": {
        "batch_url": "optimize_image_batch_api",
        "field_name": "image_files",
    },
    "convert_image_api": {
        "batch_url": "convert_image_batch_api",
        "field_name": "image_files",
    },
}
