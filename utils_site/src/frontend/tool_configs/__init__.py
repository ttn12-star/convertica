"""
Tool configuration package for Convertica PDF tools.

Re-exports TOOL_CONFIGS and BATCH_API_MAP so existing imports
(``from .tool_configs import TOOL_CONFIGS, BATCH_API_MAP``) keep working.

Module layout
─────────────
_batch_api_map.py  – BATCH_API_MAP (API routing table)
pdf_convert.py     – PDF ↔ Word / Image / Office converters
pdf_edit.py        – Rotate, watermark, crop, sign, …
pdf_organize.py    – Merge, split, compress, …
pdf_security.py    – Protect / unlock
epub_and_other.py  – EPUB, Markdown, …
image_tools.py     – Optimize / convert images
"""

from ._batch_api_map import BATCH_API_MAP
from .epub_and_other import EPUB_AND_OTHER_CONFIGS
from .image_tools import IMAGE_TOOLS_CONFIGS
from .pdf_convert import PDF_CONVERT_CONFIGS
from .pdf_edit import PDF_EDIT_CONFIGS
from .pdf_organize import PDF_ORGANIZE_CONFIGS
from .pdf_security import PDF_SECURITY_CONFIGS

TOOL_CONFIGS = {
    **PDF_CONVERT_CONFIGS,
    **PDF_EDIT_CONFIGS,
    **PDF_ORGANIZE_CONFIGS,
    **PDF_SECURITY_CONFIGS,
    **EPUB_AND_OTHER_CONFIGS,
    **IMAGE_TOOLS_CONFIGS,
}

__all__ = ["BATCH_API_MAP", "TOOL_CONFIGS"]
