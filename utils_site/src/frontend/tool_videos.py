"""Per-tool YouTube tutorial video metadata.

Loaded once from ``content/tool_videos.yaml`` at import. Maps a ``tool_key``
(or ``"homepage"``) to ``{video_id, upload_date, duration}``. A tool absent
from the file simply renders without a video, so videos are added
incrementally by editing the YAML — no code change. See the YAML header for
the schema.
"""

from __future__ import annotations

import logging

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)

_VIDEOS_PATH = settings.BASE_DIR / "content" / "tool_videos.yaml"


def _load() -> dict[str, dict[str, str]]:
    try:
        with open(_VIDEOS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning("tool_videos.yaml not found at %s; no tool videos", _VIDEOS_PATH)
        return {}
    except yaml.YAMLError:
        logger.exception("tool_videos.yaml is invalid; no tool videos")
        return {}
    # Drop malformed entries defensively: one bad edit must not 500 every page.
    videos: dict[str, dict[str, str]] = {}
    for key, meta in data.items():
        if isinstance(meta, dict) and meta.get("video_id"):
            videos[key] = meta
        else:
            logger.warning("tool_videos.yaml: skipping malformed entry %r", key)
    return videos


TOOL_VIDEOS = _load()
