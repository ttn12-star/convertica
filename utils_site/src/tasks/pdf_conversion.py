"""
Celery tasks for PDF conversion operations.

These tasks handle heavy PDF conversion operations asynchronously
to prevent blocking the main request/response cycle and Cloudflare timeouts.

Tasks report progress via self.update_state() for real-time progress bars.
"""

import os
import shutil

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from src.api.logging_utils import get_logger

logger = get_logger(__name__)


def update_progress(task, progress: int, current_step: str = "", total_steps: int = 0):
    """Helper to update task progress."""
    task.update_state(
        state="PROGRESS",
        meta={
            "progress": progress,
            "current_step": current_step,
            "total_steps": total_steps,
        },
    )


@shared_task(
    bind=True,
    name="pdf_conversion.generic_conversion",
    queue="pdf_conversion",
    soft_time_limit=540,
    time_limit=600,
)
def generic_conversion_task(
    self,
    task_id: str,
    input_path: str,
    original_filename: str,
    conversion_type: str,
    **kwargs,
) -> dict:
    """
    Universal async conversion task with progress reporting.

    Supports all conversion types by dynamically importing the converter.

    Args:
        task_id: Unique task identifier
        input_path: Path to the uploaded file
        original_filename: Original filename for output naming
        conversion_type: Type of conversion (e.g., 'pdf_to_word', 'word_to_pdf')
        **kwargs: Additional conversion parameters

    Returns:
        dict: Result containing output_path and output_filename
    """
    task_dir = os.path.dirname(input_path)
    output_path = None

    try:
        # Step 1: Validate input file exists
        update_progress(self, 5, "Validating input file...", 5)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Step 2: Load the file
        update_progress(self, 15, "Loading file...", 5)

        with open(input_path, "rb") as f:
            file_content = f.read()

        uploaded_file = ContentFile(file_content)
        uploaded_file.name = original_filename

        # Step 3: Get the converter function based on conversion type
        update_progress(self, 25, "Preparing conversion...", 5)

        converter_map = {
            "pdf_to_word": (
                "src.api.pdf_convert.pdf_to_word.utils",
                "convert_pdf_to_docx",
            ),
            "word_to_pdf": (
                "src.api.pdf_convert.word_to_pdf.utils",
                "convert_word_to_pdf",
            ),
            "pdf_to_excel": (
                "src.api.pdf_convert.pdf_to_excel.utils",
                "convert_pdf_to_excel",
            ),
            "pdf_to_jpg": (
                "src.api.pdf_convert.pdf_to_jpg.utils",
                "convert_pdf_to_jpg",
            ),
            "jpg_to_pdf": (
                "src.api.pdf_convert.jpg_to_pdf.utils",
                "convert_images_to_pdf",
            ),
            "compress_pdf": ("src.api.pdf_organize.compress_pdf.utils", "compress_pdf"),
            "merge_pdf": ("src.api.pdf_organize.merge_pdf.utils", "merge_pdfs"),
            "split_pdf": ("src.api.pdf_organize.split_pdf.utils", "split_pdf"),
            "rotate_pdf": ("src.api.pdf_edit.rotate_pdf.utils", "rotate_pdf"),
            "add_watermark": ("src.api.pdf_edit.add_watermark.utils", "add_watermark"),
            "crop_pdf": ("src.api.pdf_edit.crop_pdf.utils", "crop_pdf"),
            "add_page_numbers": (
                "src.api.pdf_edit.add_page_numbers.utils",
                "add_page_numbers",
            ),
            "organize_pdf": ("src.api.pdf_organize.organize_pdf.utils", "organize_pdf"),
            "extract_pages": (
                "src.api.pdf_organize.extract_pages.utils",
                "extract_pages",
            ),
            "remove_pages": ("src.api.pdf_organize.remove_pages.utils", "remove_pages"),
        }

        if conversion_type not in converter_map:
            raise ValueError(f"Unknown conversion type: {conversion_type}")

        module_path, func_name = converter_map[conversion_type]

        # Dynamic import
        import importlib

        module = importlib.import_module(module_path)
        converter_func = getattr(module, func_name)

        # Step 4: Perform conversion
        update_progress(self, 40, "Converting...", 5)

        # Call converter with appropriate arguments
        if conversion_type in ("compress_pdf",):
            compression_level = kwargs.get("compression_level", "medium")
            _, output_path = converter_func(
                uploaded_file, compression_level=compression_level, suffix="_convertica"
            )
        elif conversion_type in ("add_watermark",):
            _, output_path = converter_func(
                uploaded_file,
                watermark_text=kwargs.get("watermark_text"),
                watermark_file=kwargs.get("watermark_file"),
                position=kwargs.get("position", "center"),
                opacity=kwargs.get("opacity", 30),
                color=kwargs.get("color", "#000000"),
                font_size=kwargs.get("font_size", 72),
                pages=kwargs.get("pages", "all"),
                x=kwargs.get("x"),
                y=kwargs.get("y"),
                rotation=kwargs.get("rotation", 0),
                scale=kwargs.get("scale", 1.0),
                suffix="_convertica",
            )
        elif conversion_type in ("crop_pdf",):
            _, output_path = converter_func(
                uploaded_file,
                x=kwargs.get("x", 0),
                y=kwargs.get("y", 0),
                width=kwargs.get("width", 0),
                height=kwargs.get("height", 0),
                pages=kwargs.get("pages", "all"),
                scale_to_page_size=kwargs.get("scale_to_page_size", False),
                suffix="_convertica",
            )
        elif conversion_type in ("rotate_pdf",):
            _, output_path = converter_func(
                uploaded_file,
                rotation=kwargs.get("rotation", 90),
                pages=kwargs.get("pages", "all"),
                suffix="_convertica",
            )
        elif conversion_type in ("add_page_numbers",):
            _, output_path = converter_func(
                uploaded_file,
                position=kwargs.get("position", "bottom-center"),
                start_number=kwargs.get("start_number", 1),
                format_string=kwargs.get("format_string", "{page}"),
                font_size=kwargs.get("font_size", 12),
                pages=kwargs.get("pages", "all"),
                suffix="_convertica",
            )
        elif conversion_type in ("split_pdf",) or conversion_type in (
            "extract_pages",
            "remove_pages",
        ):
            _, output_path = converter_func(
                uploaded_file,
                pages=kwargs.get("pages", ""),
                suffix="_convertica",
            )
        elif conversion_type in ("organize_pdf",):
            _, output_path = converter_func(
                uploaded_file,
                page_order=kwargs.get("page_order", []),
                suffix="_convertica",
            )
        else:
            # Default: simple conversion (pdf_to_word, word_to_pdf, etc.)
            _, output_path = converter_func(uploaded_file, suffix="_convertica")

        # Step 5: Move output to task directory for persistence
        update_progress(self, 85, "Finalizing...", 5)

        # Generate output filename
        base_name = os.path.splitext(original_filename)[0]
        output_ext = os.path.splitext(output_path)[1]

        # Map conversion types to output extensions
        ext_map = {
            "pdf_to_word": ".docx",
            "pdf_to_excel": ".xlsx",
            "pdf_to_jpg": ".zip",
            "word_to_pdf": ".pdf",
            "jpg_to_pdf": ".pdf",
        }
        if conversion_type in ext_map:
            output_ext = ext_map[conversion_type]

        output_filename = f"{base_name}_convertica{output_ext}"
        final_output_path = os.path.join(task_dir, output_filename)

        # Move or copy output to task dir
        if output_path != final_output_path:
            shutil.copy2(output_path, final_output_path)
            # Cleanup original temp file
            try:
                temp_dir = os.path.dirname(output_path)
                if temp_dir != task_dir and os.path.isdir(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

        update_progress(self, 100, "Complete!", 5)

        logger.info(f"Conversion {conversion_type} completed: {final_output_path}")

        return {
            "status": "success",
            "output_path": final_output_path,
            "output_filename": output_filename,
            "conversion_type": conversion_type,
        }

    except Exception as exc:
        logger.error(f"Conversion {conversion_type} failed: {str(exc)}", exc_info=True)

        # Don't retry for user errors (validation, etc.)
        error_message = str(exc)
        if any(
            msg in error_message.lower()
            for msg in ["invalid", "corrupt", "password", "encrypted", "not found"]
        ):
            return {
                "status": "error",
                "error": error_message,
                "conversion_type": conversion_type,
            }

        # Retry for transient errors
        raise self.retry(exc=exc, countdown=30, max_retries=2)


# Legacy tasks for backwards compatibility
@shared_task(
    bind=True, name="pdf_conversion.convert_pdf_to_word", queue="pdf_conversion"
)
def convert_pdf_to_word_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        task_id=self.request.id or "legacy",
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="pdf_to_word",
        **kwargs,
    )


@shared_task(
    bind=True, name="pdf_conversion.convert_word_to_pdf", queue="pdf_conversion"
)
def convert_word_to_pdf_task(
    self, file_path: str, output_filename: str, **kwargs
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        task_id=self.request.id or "legacy",
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="word_to_pdf",
        **kwargs,
    )


@shared_task(bind=True, name="pdf_conversion.compress_pdf", queue="pdf_processing")
def compress_pdf_task(
    self,
    file_path: str,
    output_filename: str,
    compression_level: str = "medium",
    **kwargs,
) -> dict:
    """Legacy task - redirects to generic_conversion_task."""
    return generic_conversion_task(
        task_id=self.request.id or "legacy",
        input_path=file_path,
        original_filename=output_filename,
        conversion_type="compress_pdf",
        compression_level=compression_level,
        **kwargs,
    )
