from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from app.schemas.app_protocol import LearningResource


BILIBILI_EMBED_OPTIONS: dict[str, bool | int] = {
    "autoplay": False,
    "danmaku": False,
    "poster": True,
    "page": 1,
}

BVID_PATTERN = re.compile(r"\b(BV[0-9A-Za-z]{4,})\b")


def _string_candidates(resource: LearningResource) -> list[str]:
    content = resource.content if isinstance(resource.content, dict) else {}
    values: list[str] = []
    for key in ("bvid", "url", "href", "embed_url", "description"):
        value = content.get(key)
        if isinstance(value, str):
            values.append(value)
    values.append(resource.title)
    for ref in resource.source_refs:
        if isinstance(ref, dict):
            for key in ("bvid", "url", "href", "resource_id", "chunk_id"):
                value = ref.get(key)
                if isinstance(value, str):
                    values.append(value)
    return values


def extract_bvid(resource: LearningResource | dict[str, Any]) -> str:
    if isinstance(resource, dict):
        try:
            resource = LearningResource.model_validate(resource)
        except Exception:
            content = resource.get("content") if isinstance(resource.get("content"), dict) else {}
            candidates = [
                str(content.get("bvid") or ""),
                str(content.get("url") or ""),
                str(resource.get("title") or ""),
            ]
            for candidate in candidates:
                match = BVID_PATTERN.search(candidate)
                if match:
                    return match.group(1)
            return ""
    for candidate in _string_candidates(resource):
        match = BVID_PATTERN.search(candidate)
        if match:
            return match.group(1)
    return ""


def bilibili_embed_url(bvid: str, options: dict[str, Any] | None = None) -> str:
    clean_bvid = (bvid or "").strip()
    if not clean_bvid:
        return ""
    merged = {**BILIBILI_EMBED_OPTIONS, **(options or {})}
    params = {
        "bvid": clean_bvid,
        "poster": 1 if bool(merged.get("poster", True)) else 0,
        "autoplay": 1 if bool(merged.get("autoplay", False)) else 0,
        "danmaku": 1 if bool(merged.get("danmaku", False)) else 0,
        "p": int(merged.get("page") or 1),
    }
    return f"https://player.bilibili.com/player.html?{urlencode(params)}"


def video_player_payload(topic: str, resources: list[LearningResource]) -> dict[str, Any]:
    videos = [resource.model_dump() for resource in resources]
    selected = next((resource for resource in resources if extract_bvid(resource)), resources[0] if resources else None)
    selected_bvid = extract_bvid(selected) if selected else ""
    return {
        "topic": topic or "B站视频推荐",
        "videos": videos,
        "selected_resource_id": selected.resource_id if selected else "",
        "selected_bvid": selected_bvid,
        "embed_url": bilibili_embed_url(selected_bvid),
        "embed_options": BILIBILI_EMBED_OPTIONS.copy(),
    }
