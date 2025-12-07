import os
import tempfile
from typing import List, Tuple

from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from src.exceptions import ConversionError, InvalidPDFError, StorageError

from ...file_validation import check_disk_space, sanitize_filename, validate_output_file
from ...logging_utils import get_logger

logger = get_logger(__name__)


def convert_jpg_to_pdf(
    uploaded_file: UploadedFile, suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Convert JPG/JPEG image to PDF.

    Args:
        uploaded_file (UploadedFile): Uploaded image file (JPG/JPEG).
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_image, path_to_pdf) where pdf exists.

    Raises:
        InvalidPDFError: when image is invalid or unsupported format.
        StorageError: for filesystem I/O errors.
        ConversionError: for other conversion-related failures.
    """
    tmp_dir = None
    safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
    context = {
        "function": "convert_jpg_to_pdf",
        "input_filename": safe_name,
        "input_size": uploaded_file.size,
    }

    try:
        # Check disk space
        tmp_dir = tempfile.mkdtemp(prefix="jpg2pdf_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        logger.debug(
            "Created temporary directory",
            extra={**context, "event": "temp_dir_created"},
        )

        image_path = os.path.join(tmp_dir, safe_name)
        base = os.path.splitext(safe_name)[0]
        pdf_name = f"{base}{suffix}.pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)

        context.update(
            {
                "image_path": image_path,
                "pdf_path": pdf_path,
            }
        )

        # Write uploaded file to temp
        try:
            logger.debug(
                "Writing uploaded file to temporary location",
                extra={**context, "event": "file_write_start"},
            )
            with open(image_path, "wb") as f:
                bytes_written = 0
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
                    bytes_written += len(chunk)
            context["bytes_written"] = bytes_written
            logger.debug(
                "File written successfully",
                extra={**context, "event": "file_write_success"},
            )
        except (OSError, IOError) as io_err:
            logger.error(
                "Failed to write uploaded file",
                extra={**context, "event": "file_write_error", "error": str(io_err)},
                exc_info=True,
            )
            raise StorageError(
                f"Failed to write uploaded file: {io_err}",
                context={**context, "error_type": type(io_err).__name__},
            ) from io_err

        # Validate and open image
        try:
            logger.info(
                "Starting JPG to PDF conversion",
                extra={**context, "event": "conversion_start"},
            )

            # Open and validate image
            try:
                image = Image.open(image_path)
                # Verify it's a valid image
                image.verify()
            except Exception as img_err:
                logger.error(
                    "Invalid image file",
                    extra={
                        **context,
                        "error": str(img_err),
                        "event": "invalid_image_error",
                    },
                    exc_info=True,
                )
                raise InvalidPDFError(
                    f"Invalid or corrupted image file: {img_err}", context=context
                ) from img_err

            # Reopen image after verify (verify closes the file)
            image = Image.open(image_path)

            # Convert to RGB if necessary (PDF doesn't support RGBA directly)
            if image.mode in ("RGBA", "LA", "P"):
                logger.debug(
                    "Converting image to RGB",
                    extra={**context, "original_mode": image.mode},
                )
                # Create white background
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                rgb_image.paste(
                    image,
                    mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None,
                )
                image = rgb_image
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Get image dimensions
            img_width, img_height = image.size
            context.update(
                {
                    "image_width": img_width,
                    "image_height": img_height,
                }
            )

            logger.debug(
                "Image loaded successfully",
                extra={**context, "image_mode": image.mode, "event": "image_loaded"},
            )

        except InvalidPDFError:
            raise
        except Exception as img_err:
            logger.error(
                "Error processing image",
                extra={
                    **context,
                    "error": str(img_err),
                    "event": "image_processing_error",
                },
                exc_info=True,
            )
            raise ConversionError(
                f"Error processing image: {img_err}",
                context={**context, "error_type": type(img_err).__name__},
            ) from img_err

        # Create PDF from image
        try:
            # Calculate page size to fit image (maintain aspect ratio)
            # Use A4 as base, but scale to fit image
            page_width, page_height = A4

            # Calculate scaling to fit image on page
            scale_x = page_width / img_width
            scale_y = page_height / img_height
            scale = min(scale_x, scale_y)  # Use smaller scale to fit both dimensions

            # Calculate scaled dimensions
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            # Center image on page
            x_offset = (page_width - scaled_width) / 2
            y_offset = (page_height - scaled_height) / 2

            # Create PDF
            c = canvas.Canvas(pdf_path, pagesize=A4)

            # Draw image on PDF
            img_reader = ImageReader(image)
            c.drawImage(
                img_reader,
                x_offset,
                y_offset,
                width=scaled_width,
                height=scaled_height,
                preserveAspectRatio=True,
            )

            c.save()

            logger.debug(
                "PDF created successfully", extra={**context, "event": "pdf_created"}
            )

        except Exception as pdf_err:
            logger.error(
                "Error creating PDF",
                extra={**context, "error": str(pdf_err), "event": "pdf_creation_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Error creating PDF: {pdf_err}",
                context={**context, "error_type": type(pdf_err).__name__},
            ) from pdf_err

        # Validate output file
        is_valid, validation_error = validate_output_file(
            pdf_path, min_size=500, context=context
        )
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={
                    **context,
                    "validation_error": validation_error,
                    "event": "output_validation_failed",
                },
            )
            raise ConversionError(
                validation_error or "Conversion finished but output file is invalid",
                context=context,
            )

        output_size = os.path.getsize(pdf_path)
        logger.info(
            "JPG to PDF conversion successful",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return image_path, pdf_path

    except (StorageError, ConversionError, InvalidPDFError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during JPG to PDF conversion",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
    finally:
        # Note: We don't cleanup tmp_dir here - that's handled by the view
        pass


def convert_multiple_jpg_to_pdf(
    uploaded_files: List[UploadedFile], suffix: str = "_convertica"
) -> Tuple[str, str]:
    """Convert multiple JPG/JPEG images to a single PDF.

    Each image will be placed on a separate page in the PDF.

    Args:
        uploaded_files (List[UploadedFile]): List of uploaded image files (JPG/JPEG).
        suffix (str): Suffix to add to output file base name.

    Returns:
        Tuple[str, str]: (path_to_first_image, path_to_pdf) where pdf exists.

    Raises:
        InvalidPDFError: when image is invalid or unsupported format.
        StorageError: for filesystem I/O errors.
        ConversionError: for other conversion-related failures.
    """
    tmp_dir = None
    num_files = len(uploaded_files)
    context = {
        "function": "convert_multiple_jpg_to_pdf",
        "num_files": num_files,
        "total_size": sum(f.size for f in uploaded_files),
    }

    try:
        # Check disk space (estimate: 200MB per file)
        tmp_dir = tempfile.mkdtemp(prefix="jpg2pdf_multi_")
        context["tmp_dir"] = tmp_dir

        disk_check, disk_error = check_disk_space(tmp_dir, required_mb=200 * num_files)
        if not disk_check:
            raise StorageError(disk_error or "Insufficient disk space", context=context)

        logger.debug(
            "Created temporary directory",
            extra={**context, "event": "temp_dir_created"},
        )

        # Save all uploaded files to temp directory
        image_paths = []
        for idx, uploaded_file in enumerate(uploaded_files):
            safe_name = sanitize_filename(os.path.basename(uploaded_file.name))
            # Add index prefix to avoid name collisions
            safe_name = f"{idx:03d}_{safe_name}"
            image_path = os.path.join(tmp_dir, safe_name)

            try:
                logger.debug(
                    f"Writing file {idx + 1}/{num_files} to temporary location",
                    extra={
                        **context,
                        "event": "file_write_start",
                        "file_index": idx + 1,
                        "filename": safe_name,
                    },
                )
                with open(image_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                image_paths.append(image_path)
                logger.debug(
                    f"File {idx + 1}/{num_files} written successfully",
                    extra={
                        **context,
                        "event": "file_write_success",
                        "file_index": idx + 1,
                    },
                )
            except (OSError, IOError) as io_err:
                logger.error(
                    f"Failed to write uploaded file {idx + 1}",
                    extra={
                        **context,
                        "event": "file_write_error",
                        "error": str(io_err),
                        "file_index": idx + 1,
                    },
                    exc_info=True,
                )
                raise StorageError(
                    f"Failed to write uploaded file {idx + 1}: {io_err}",
                    context={
                        **context,
                        "error_type": type(io_err).__name__,
                        "file_index": idx + 1,
                    },
                ) from io_err

        # Generate PDF name from first file
        first_safe_name = sanitize_filename(os.path.basename(uploaded_files[0].name))
        base = os.path.splitext(first_safe_name)[0]
        if num_files > 1:
            pdf_name = f"{base}_and_{num_files - 1}_more{suffix}.pdf"
        else:
            pdf_name = f"{base}{suffix}.pdf"
        pdf_path = os.path.join(tmp_dir, pdf_name)

        context.update(
            {
                "pdf_path": pdf_path,
                "pdf_name": pdf_name,
            }
        )

        # Process all images and create PDF
        try:
            logger.info(
                f"Starting multiple JPG to PDF conversion ({num_files} files)",
                extra={**context, "event": "conversion_start"},
            )

            # Create PDF canvas
            c = canvas.Canvas(pdf_path, pagesize=A4)
            page_width, page_height = A4

            # Process each image
            for idx, image_path in enumerate(image_paths):
                try:
                    # Open and validate image
                    try:
                        image = Image.open(image_path)
                        image.verify()
                    except Exception as img_err:
                        logger.error(
                            f"Invalid image file {idx + 1}",
                            extra={
                                **context,
                                "error": str(img_err),
                                "event": "invalid_image_error",
                                "file_index": idx + 1,
                            },
                            exc_info=True,
                        )
                        raise InvalidPDFError(
                            f"Invalid or corrupted image file {idx + 1}: {img_err}",
                            context={**context, "file_index": idx + 1},
                        ) from img_err

                    # Reopen image after verify
                    image = Image.open(image_path)

                    # Convert to RGB if necessary
                    if image.mode in ("RGBA", "LA", "P"):
                        logger.debug(
                            f"Converting image {idx + 1} to RGB",
                            extra={
                                **context,
                                "original_mode": image.mode,
                                "file_index": idx + 1,
                            },
                        )
                        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                        if image.mode == "P":
                            image = image.convert("RGBA")
                        rgb_image.paste(
                            image,
                            mask=(
                                image.split()[-1]
                                if image.mode in ("RGBA", "LA")
                                else None
                            ),
                        )
                        image = rgb_image
                    elif image.mode != "RGB":
                        image = image.convert("RGB")

                    # Get image dimensions
                    img_width, img_height = image.size

                    # Calculate scaling to fit image on page
                    scale_x = page_width / img_width
                    scale_y = page_height / img_height
                    scale = min(scale_x, scale_y)

                    # Calculate scaled dimensions
                    scaled_width = img_width * scale
                    scaled_height = img_height * scale

                    # Center image on page
                    x_offset = (page_width - scaled_width) / 2
                    y_offset = (page_height - scaled_height) / 2

                    # Draw image on PDF
                    img_reader = ImageReader(image)
                    c.drawImage(
                        img_reader,
                        x_offset,
                        y_offset,
                        width=scaled_width,
                        height=scaled_height,
                        preserveAspectRatio=True,
                    )

                    # Add new page for next image (except for the last one)
                    if idx < len(image_paths) - 1:
                        c.showPage()

                    logger.debug(
                        f"Image {idx + 1}/{num_files} added to PDF",
                        extra={
                            **context,
                            "event": "image_added",
                            "file_index": idx + 1,
                        },
                    )

                except InvalidPDFError:
                    raise
                except Exception as img_err:
                    logger.error(
                        f"Error processing image {idx + 1}",
                        extra={
                            **context,
                            "error": str(img_err),
                            "event": "image_processing_error",
                            "file_index": idx + 1,
                        },
                        exc_info=True,
                    )
                    raise ConversionError(
                        f"Error processing image {idx + 1}: {img_err}",
                        context={
                            **context,
                            "error_type": type(img_err).__name__,
                            "file_index": idx + 1,
                        },
                    ) from img_err

            # Save PDF
            c.save()

            logger.debug(
                "PDF created successfully", extra={**context, "event": "pdf_created"}
            )

        except (InvalidPDFError, ConversionError):
            raise
        except Exception as pdf_err:
            logger.error(
                "Error creating PDF",
                extra={**context, "error": str(pdf_err), "event": "pdf_creation_error"},
                exc_info=True,
            )
            raise ConversionError(
                f"Error creating PDF: {pdf_err}",
                context={**context, "error_type": type(pdf_err).__name__},
            ) from pdf_err

        # Validate output file
        is_valid, validation_error = validate_output_file(
            pdf_path, min_size=500, context=context
        )
        if not is_valid:
            logger.error(
                "Output file validation failed",
                extra={
                    **context,
                    "validation_error": validation_error,
                    "event": "output_validation_failed",
                },
            )
            raise ConversionError(
                validation_error or "Conversion finished but output file is invalid",
                context=context,
            )

        output_size = os.path.getsize(pdf_path)
        logger.info(
            f"Multiple JPG to PDF conversion successful ({num_files} files)",
            extra={
                **context,
                "event": "conversion_success",
                "output_size": output_size,
                "output_size_mb": round(output_size / (1024 * 1024), 2),
            },
        )

        return image_paths[0] if image_paths else tmp_dir, pdf_path

    except (StorageError, ConversionError, InvalidPDFError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(
            "Unexpected error during multiple JPG to PDF conversion",
            extra={
                **context,
                "event": "unexpected_error",
                "error_type": type(e).__name__,
            },
        )
        raise ConversionError(
            f"Unexpected error during conversion: {e}",
            context={**context, "error_type": type(e).__name__},
        ) from e
    finally:
        # Note: We don't cleanup tmp_dir here - that's handled by the view
        pass
