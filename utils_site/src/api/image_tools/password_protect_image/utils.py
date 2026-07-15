import os
import tempfile

from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from src.exceptions import ConversionError

from ...file_validation import sanitize_filename
from ...logging_utils import get_logger

logger = get_logger(__name__)


def protect_image(
    uploaded_files: list[UploadedFile],
    password: str,
    user_password: str | None = None,
    owner_password: str | None = None,
    quality: int = 85,
    suffix: str = "_convertica",
) -> tuple[str, str]:
    """Render image(s) into one PDF and encrypt it with a password (AES-256).

    Returns (input_pdf_path, output_pdf_path); both live in a fresh temp dir the
    caller must clean up (``shutil.rmtree(os.path.dirname(output_pdf_path))``).
    """
    context = {"function": "protect_image"}
    if not uploaded_files:
        raise ConversionError("At least one image file is required", context=context)
    if not password or not password.strip():
        raise ConversionError("Password cannot be empty", context=context)

    pwd = password.strip()
    user_pwd = user_password.strip() if user_password and user_password.strip() else pwd
    owner_pwd = (
        owner_password.strip() if owner_password and owner_password.strip() else pwd
    )
    quality = max(60, min(95, int(quality)))

    tmp_dir = tempfile.mkdtemp(prefix="protect_image_")
    rendered_pdf = os.path.join(tmp_dir, "rendered.pdf")

    c = canvas.Canvas(rendered_pdf, pagesize=A4)
    page_width, page_height = A4
    margin = 72
    avail_w = page_width - 2 * margin
    avail_h = page_height - 2 * margin

    for idx, uf in enumerate(uploaded_files):
        safe_name = sanitize_filename(os.path.basename(uf.name or f"image_{idx}"))
        img_path = os.path.join(tmp_dir, f"{idx}_{safe_name}")
        with open(img_path, "wb") as f:
            for chunk in uf.chunks():
                f.write(chunk)
        try:
            Image.open(img_path).verify()
        except (UnidentifiedImageError, OSError) as e:
            raise ConversionError(
                "File '%s' is not a valid image. Please upload image files "
                "(JPG, PNG, WebP, GIF) only." % (uf.name or safe_name),
                context=context,
            ) from e
        with Image.open(img_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            draw_path = os.path.join(tmp_dir, f"draw_{idx}.jpg")
            img.save(draw_path, "JPEG", quality=quality, optimize=True)
            w, h = img.size
        scale = min(avail_w / w, avail_h / h)
        sw, sh = w * scale, h * scale
        x = margin + (avail_w - sw) / 2
        y = margin + (avail_h - sh) / 2
        c.drawImage(ImageReader(draw_path), x, y, sw, sh)
        if idx < len(uploaded_files) - 1:
            c.showPage()
    c.save()

    base = sanitize_filename(
        os.path.splitext(os.path.basename(uploaded_files[0].name or "image"))[0]
    )
    output_path = os.path.join(tmp_dir, f"{base}_protected{suffix}.pdf")

    reader = PdfReader(rendered_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    # AES-256, matching protect_pdf. pypdf's default RC4-128 is broken; a tool
    # named "password protect" must mean real encryption.
    writer.encrypt(
        user_password=user_pwd, owner_password=owner_pwd, algorithm="AES-256"
    )
    with open(output_path, "wb") as f:
        writer.write(f)

    return rendered_pdf, output_path
