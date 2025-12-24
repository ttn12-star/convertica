"""
PDF to HTML conversion utilities.

Converts PDF documents to HTML format with text extraction and optional image embedding.
"""

import base64
import os
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, StorageError

logger = get_logger(__name__)


def convert_pdf_to_html(
    uploaded_file: UploadedFile,
    extract_images: bool = True,
    preserve_layout: bool = True,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Convert PDF to HTML.

    Args:
        uploaded_file: PDF file to convert
        extract_images: Whether to extract and embed images
        preserve_layout: Whether to preserve PDF layout
        suffix: Suffix for output filename

    Returns:
        Tuple of (input_path, output_path)

    Raises:
        ConversionError: If conversion fails
        StorageError: If disk space is insufficient
    """
    context = {
        "function": "convert_pdf_to_html",
        "input_filename": os.path.basename(uploaded_file.name),
        "input_size": uploaded_file.size,
        "extract_images": extract_images,
        "preserve_layout": preserve_layout,
    }

    logger.info("Starting PDF to HTML conversion", extra=context)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_to_html_")
    input_path = None
    output_path = None

    try:
        # Check disk space
        required_space = uploaded_file.size * 5
        check_disk_space(required_space, context)

        # Save uploaded file
        safe_filename = sanitize_filename(get_valid_filename(uploaded_file.name))
        input_path = os.path.join(tmp_dir, safe_filename)

        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        logger.debug("Saved PDF file", extra={**context, "input_path": input_path})

        # Read PDF
        reader = PdfReader(input_path)
        num_pages = len(reader.pages)

        logger.info(
            f"Processing {num_pages} pages",
            extra={**context, "num_pages": num_pages},
        )

        # Start HTML document
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF to HTML - Convertica</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .page {
            background-color: white;
            padding: 40px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            page-break-after: always;
        }
        .page-number {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
        img {
            max-width: 100%;
            height: auto;
        }
    </style>
</head>
<body>
"""

        # Process each page
        for page_num in range(num_pages):
            page = reader.pages[page_num]

            html_content += '<div class="page">\n'

            # Extract text
            try:
                text = page.extract_text()
                if text.strip():
                    # Convert text to HTML paragraphs
                    paragraphs = text.split("\n\n")
                    for para in paragraphs:
                        if para.strip():
                            html_content += f"<p>{para.strip()}</p>\n"
            except Exception as e:
                logger.warning(
                    f"Failed to extract text from page {page_num + 1}: {e}",
                    extra={**context, "page": page_num + 1},
                )

            # Add page number
            html_content += (
                f'<div class="page-number">Page {page_num + 1} of {num_pages}</div>\n'
            )
            html_content += "</div>\n\n"

        # If extract_images is enabled, convert pages to images as fallback
        if extract_images:
            logger.info("Converting pages to images", extra=context)
            try:
                images = convert_from_path(input_path, dpi=150)

                html_content += '<div class="page">\n'
                html_content += "<h2>PDF Pages as Images</h2>\n"

                for idx, image in enumerate(images):
                    # Save image temporarily
                    img_path = os.path.join(tmp_dir, f"page_{idx + 1}.png")
                    image.save(img_path, "PNG")

                    # Read and encode image as base64
                    with open(img_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode()

                    html_content += f'<img src="data:image/png;base64,{img_data}" alt="Page {idx + 1}" />\n'

                    # Clean up temp image
                    os.remove(img_path)

                html_content += "</div>\n"
            except Exception as e:
                logger.warning(
                    f"Failed to convert pages to images: {e}",
                    extra={**context, "error": str(e)},
                )

        # Close HTML document
        html_content += """
</body>
</html>
"""

        # Save HTML file
        base_name = Path(safe_filename).stem
        output_filename = f"{base_name}{suffix}.html"
        output_path = os.path.join(tmp_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        output_size = os.path.getsize(output_path)
        logger.info(
            "PDF to HTML conversion completed",
            extra={
                **context,
                "output_path": output_path,
                "output_size": output_size,
                "num_pages": num_pages,
            },
        )

        return input_path, output_path

    except Exception as e:
        logger.exception(
            "PDF to HTML conversion failed",
            extra={**context, "error": str(e)},
        )
        raise ConversionError(f"Failed to convert PDF to HTML: {str(e)}") from e
