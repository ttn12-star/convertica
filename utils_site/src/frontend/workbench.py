# utils_site/src/frontend/workbench.py
"""Workbench: the drop-board of converter widgets.

Catalog = everything a tile can point at, built from TOOL_CONFIGS so a new
tool shows up in the picker without extra code. Tier limits = the freemium
ladder from the spec. Views stay in views.py; this module has no HTML.
"""

from __future__ import annotations

from functools import lru_cache

from django.template.loader import get_template
from django.urls import NoReverseMatch, reverse
from django.utils import translation
from src.api.premium_utils import is_premium_active
from src.frontend.tool_configs import BATCH_API_MAP, TOOL_CONFIGS
from src.frontend.tool_configs.archive_tools import ARCHIVE_TOOLS_CONFIGS
from src.frontend.tool_configs.epub_and_other import EPUB_AND_OTHER_CONFIGS
from src.frontend.tool_configs.image_tools import IMAGE_TOOLS_CONFIGS
from src.frontend.tool_configs.pdf_convert import PDF_CONVERT_CONFIGS
from src.frontend.tool_configs.pdf_edit import PDF_EDIT_CONFIGS
from src.frontend.tool_configs.pdf_organize import PDF_ORGANIZE_CONFIGS
from src.frontend.tool_configs.pdf_security import PDF_SECURITY_CONFIGS

#: tool_keys whose URL pattern name doesn't follow the "<tool_key>_page" rule
TOOL_URL_NAME_OVERRIDES = {"generate_favicon": "favicon_generator_page"}

#: Tools whose API refuses non-premium callers outright (OCR is a param, not a tool).
PREMIUM_ONLY_KEYS = frozenset({"pdf_to_pdfa"})

#: A tile can only drop on tools whose page is the plain file-in/file-out form.
# ponytail: edit_pdf_generic tools (rotate, compress, …) also post plain params;
# audit them one by one in phase 2 and add an allowlist here.
_DROPPABLE_BASE = 'extends "frontend/converter_generic.html"'

TIER_LIMITS = {
    "anonymous": {"boards": 1, "tiles": 3, "sync": False, "system": False},
    "registered": {"boards": 1, "tiles": 6, "sync": False, "system": False},
    "premium": {"boards": 5, "tiles": 20, "sync": True, "system": True},
}

_GROUP_OF = {
    key: group
    for configs, group in (
        (PDF_CONVERT_CONFIGS, "convert"),
        (PDF_EDIT_CONFIGS, "edit"),
        (PDF_ORGANIZE_CONFIGS, "organize"),
        (PDF_SECURITY_CONFIGS, "security"),
        (EPUB_AND_OTHER_CONFIGS, "epub"),
        (IMAGE_TOOLS_CONFIGS, "image"),
        (ARCHIVE_TOOLS_CONFIGS, "archive"),
    )
    for key in configs
}


@lru_cache(maxsize=16)
def _template_is_droppable(template_name: str) -> bool:
    return _DROPPABLE_BASE in get_template(template_name).template.source


@lru_cache(maxsize=16)
def _structure(language: str) -> dict[str, dict]:
    """Everything in the catalog except the translated label; cached per language
    because page URLs carry the locale prefix."""
    out: dict[str, dict] = {}
    for key, config in TOOL_CONFIGS.items():
        args = config["converter_args"]
        url_name = TOOL_URL_NAME_OVERRIDES.get(key, f"{key}_page")
        try:
            page_url = reverse(f"frontend:{url_name}")
            api_url = reverse(args["api_url_name"])
        except NoReverseMatch:
            continue
        batch = BATCH_API_MAP.get(args["api_url_name"])
        out[key] = {
            "group": _GROUP_OF.get(key, "convert"),
            "pageUrl": page_url,
            "apiUrl": api_url,
            "batchApiUrl": reverse(batch["batch_url"]) if batch else None,
            "batchFieldName": batch["field_name"] if batch else None,
            "fileAccept": args["file_accept"],
            "fileInputName": args["file_input_name"],
            "premiumOnly": key in PREMIUM_ONLY_KEYS,
            "droppable": _template_is_droppable(config["template"]),
        }
    return out


def build_catalog() -> dict[str, dict]:
    """Catalog for the current request language (labels are gettext_lazy)."""
    language = translation.get_language() or "en"
    return {
        key: {"label": str(TOOL_CONFIGS[key]["converter_args"]["header_text"]), **entry}
        for key, entry in _structure(language).items()
    }


def tier_for(request) -> str:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return "anonymous"
    return "premium" if is_premium_active(user) else "registered"


def limits_for(request) -> dict:
    tier = tier_for(request)
    return {"tier": tier, **TIER_LIMITS[tier]}
