# utils_site/src/frontend/workbench.py
"""Workbench: the drop-board of converter widgets.

Catalog = everything a tile can point at, built from TOOL_CONFIGS so a new
tool shows up in the picker without extra code. Tier limits = the freemium
ladder from the spec. Views stay in views.py; this module has no HTML.
"""

from __future__ import annotations

from functools import lru_cache

from django.template.loader import get_template
from django.urls import NoReverseMatch, Resolver404, resolve, reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
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

#: Droppable tools whose serializer has a required non-file field with no
#: default, so a blind quick-add tile would 400 on the first drop. Derived by
#: reading the serializers of every droppable tool: only ConvertImageSerializer
#: qualifies (output_format is a required ChoiceField). generate_favicon and the
#: *_to_ico family only require the file itself; their `sizes` field defaults.
REQUIRES_CONFIG_KEYS: frozenset[str] = frozenset({"convert_image"})

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


def _try_reverse(name: str) -> str | None:
    """URL for `name`, or None when no such route is registered."""
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def _batch_async_url(batch_url: str | None) -> str | None:
    """Generic `^(?P<batch_route>.+/batch)/async/$` twin of a batch route.

    It is a re_path, so reversing it by name is fiddly; resolving the candidate
    URL both builds and verifies it in one step.
    """
    if not batch_url:
        return None
    candidate = batch_url + "async/"
    try:
        return candidate if resolve(candidate).url_name == "batch_async_api" else None
    except Resolver404:
        return None


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
        batch_url = reverse(batch["batch_url"]) if batch else None
        out[key] = {
            "group": _GROUP_OF.get(key, "convert"),
            "pageUrl": page_url,
            "apiUrl": api_url,
            "batchApiUrl": batch_url,
            "batchAsyncApiUrl": _batch_async_url(batch_url),
            # converter.js always posts heavy tools and every batch to /async/;
            # the sync twin races the 100s Cloudflare edge timeout.
            "asyncApiUrl": _try_reverse(f"{key}_async_api"),
            "batchFieldName": batch["field_name"] if batch else None,
            "fileAccept": args["file_accept"],
            "fileInputName": args["file_input_name"],
            "premiumOnly": key in PREMIUM_ONLY_KEYS,
            "droppable": _template_is_droppable(config["template"]),
            "requiresConfig": key in REQUIRES_CONFIG_KEYS,
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


#: First-run template boards. Tool keys that are not droppable (or need
#: configuration) are filtered out by build_templates(), so the spec's
#: "Compress PDF"/"Rotate" (edit_pdf_generic, not droppable yet) are absent.
BOARD_TEMPLATES = [
    {
        "key": "office",
        "name": _("Office"),
        "description": _("Word, Excel and PowerPoint to PDF and back."),
        "tools": ["word_to_pdf", "pdf_to_word", "excel_to_pdf", "ppt_to_pdf"],
    },
    {
        "key": "scans",
        "name": _("Scans"),
        "description": _("Get text out of scans and photos."),
        "tools": ["image_to_text", "pdf_to_text", "pdf_to_word"],
    },
    {
        "key": "images",
        "name": _("Images"),
        "description": _("HEIC to JPG, lighter images, PDF pages as pictures."),
        "tools": ["heic_to_jpg", "optimize_image", "pdf_to_jpg"],
    },
]


def build_templates(catalog: dict[str, dict]) -> list[dict]:
    out = []
    for template in BOARD_TEMPLATES:
        tools = [
            key
            for key in template["tools"]
            if key in catalog
            and catalog[key]["droppable"]
            and not catalog[key]["requiresConfig"]
        ]
        if len(tools) < 2:
            continue
        out.append(
            {
                "key": template["key"],
                "name": str(template["name"]),
                "description": str(template["description"]),
                "tools": tools,
            }
        )
    return out
