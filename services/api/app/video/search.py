"""Real-time Bilibili video search.

Replaces the local SQLite "video resource pool" lookup for the primary
recommendation path. Hermes acts as the director (decides the query, explains
the picks); this module is the stable retrieval tool that actually hits
Bilibili search and returns relevance-filtered candidates as LearningResource.

Design notes:
- We warm up a cookie via GET https://bilibili.com, then call the official web
  search API (x/web-interface/search/type). This is the same endpoint the
  website uses; no scraping of rendered HTML required.
- Results are hard-filtered for relevance (a significant query term must appear
  in title or tags) so we never return "Java" cards that link to "操作系统".
- Each candidate carries a real bvid/url so the chat card, the player embed and
  the recommendation text all reference the SAME video.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from app.schemas.app_protocol import LearningResource
from app.video.bilibili import bilibili_embed_url

SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
WARMUP_URL = "https://www.bilibili.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://search.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}

_EM_TAG = re.compile(r"</?em[^>]*>")
_HTML_ENTITY = re.compile(r"&[a-zA-Z]+;")
# Split mixed text into: ASCII word chunks, or CJK word fragments (2+ chars as bigrams
# so "英语四级" → ["英语","语四","四级"] — substrings of the compound CJK span).
_CJK_RUN = re.compile(r"[一-鿿]{2,}")
_ASCII_TOKEN = re.compile(r"[0-9A-Za-z]{2,}")
# Overly-generic bigrams that match almost anything; skipped when building
# the query's own terms but NOT used to gate _is_relevant.
_TERM_STOPWORDS = {
    "方法", "学习方法", "应试", "技巧", "备考", "考试",
    "学习", "入门", "基础", "零基础", "讲解",
    "推荐", "最新", "完整", "全套", "合集", "免费", "高清", "系列", "详解",
    "可交", "交互", "模型", "演示", "还原",
}
# When these terms appear in the query, videos that do NOT contain them are still
# considered irrelevant — they serve as a hard-must-match requirement.
_HARD_MATCH_TERMS = {
    "java", "python", "matlab", "c语", "c++", "cpp",
    "高数", "数学", "物理", "化学", "历史", "政治",
    "英语", "日语", "韩语", "法语", "德语",
    "四级", "六级", "考研", "高考", "雅思", "托福",
    "魔方", "rubik", "rubik's", "rubiks", "鲁比克",
    "内燃机", "四冲程", "奥托循环", "热机",
}

_EDU_NEGATIVE_TERMS = {
    "搞笑", "美女", "成人", "擦边", "福利视频", "福利视频", "资源网站",
    "不笑算我输", "极限过审", "福利视频合集", "午夜福利",
    "致敬", "魅力谁懂", "永不过时", "悲鸣", "声音带来", "情怀",
    "minecraft", "我的世界", "游戏", "建筑教程", "内燃机车",
}

_EDU_SIGNAL_TERMS = {
    "教学", "教程", "课程", "公开课", "讲解", "详解", "知识点", "考点",
    "初中", "高中", "大学", "物理", "九年级", "原理", "工作原理",
    "冲程", "热机", "奥托循环", "动画", "实验", "题", "做题",
}


def _clean_text(value: str) -> str:
    value = _EM_TAG.sub("", value or "")
    value = _HTML_ENTITY.sub("", value)
    return value.strip()


def _extract_cjk_bigrams(value: str) -> list[str]:
    """Pull overlapping 2-char slices from each CJK run so that "英语四级"
    yields bigrams ["英语","语四","四级"] — far more selective than single chars.
    Also normalizes digit+级 into equivalent 汉字+级 before slicing."""
    # Normalise "4级"/"6级" → "四级"/"六级" so the bigram extractor captures them
    value = re.sub(
        r"([0-9]+)\s*级",
        lambda m: {"4": "四", "6": "六", "8": "八", "2": "二", "3": "三", "1": "一", "5": "五", "7": "七", "9": "九"}.get(m.group(1), m.group(1)) + "级",
        value,
    )
    result: list[str] = []
    for run in _CJK_RUN.findall(value):
        for i in range(len(run) - 1):
            result.append(run[i : i + 2])
    return result


def _significant_terms(query: str) -> list[str]:
    """Tokenize the query into meaningful relevance signals (multi-char bigrams)."""
    text = (query or "").casefold().strip()
    terms: list[str] = (
        _ASCII_TOKEN.findall(text) + _extract_cjk_bigrams(text)
    )
    terms = [t for t in terms if t not in _TERM_STOPWORDS]
    seen: set[str] = set()
    ordered = [t for t in terms if not (t in seen or seen.add(t))]
    return ordered


def _hard_match_terms(query: str) -> set[str]:
    """Returns the subset of the query's own terms that are in the hard-match set.
    These MUST appear in candidate video titles/tags — they carry strong domain signal."""
    all_terms = set(_ASCII_TOKEN.findall(query.casefold()))
    all_terms.update(_CJK_RUN.findall(query.casefold()))
    all_terms.update(_extract_cjk_bigrams(query))
    return {t for t in _HARD_MATCH_TERMS if t in all_terms}


def _has_negative_signal(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in _EDU_NEGATIVE_TERMS)


def _requires_edu_signal(terms: list[str], hard_must: set[str]) -> bool:
    joined = "".join([*terms, *hard_must])
    return any(term in joined for term in {"内燃机", "四冲程", "奥托循环", "热机"})


def _has_edu_signal(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in _EDU_SIGNAL_TERMS)


def _is_relevant(item: dict[str, Any], terms: list[str], hard_must: set[str]) -> bool:
    if not terms and not hard_must:
        return True
    haystack = " ".join(
        [
            _clean_text(str(item.get("title", ""))),
            _clean_text(str(item.get("description", "")))[:120],
            str(item.get("tag", "")),
            str(item.get("author", "")),
        ]
    ).casefold()
    if _has_negative_signal(haystack):
        return False
    if _requires_edu_signal(terms, hard_must) and not _has_edu_signal(haystack):
        return False
    # Hard-match: terms that carry strong domain signal (e.g. "java", "四级")
    # must appear in the candidate. Missing any = irrelevant.
    for t in hard_must:
        if t not in haystack:
            return False
    # Soft-match: at least half the bigrams must appear
    if terms:
        matched = sum(1 for t in terms if t in haystack)
        if matched < max(1, min(3, len(terms) // 2 + 1)):
            return False
    return True


def _to_resource(item: dict[str, Any], topic: str, reason: str) -> LearningResource | None:
    bvid = str(item.get("bvid") or "").strip()
    if not bvid:
        return None
    title = _clean_text(str(item.get("title", ""))) or bvid
    author = str(item.get("author", "")).strip()
    description = _clean_text(str(item.get("description", "")))[:280]
    pic = str(item.get("pic", "")).strip()
    if pic.startswith("//"):
        pic = f"https:{pic}"
    tags = [t.strip() for t in str(item.get("tag", "")).split(",") if t.strip()][:8]
    url = f"https://www.bilibili.com/video/{bvid}"
    play = item.get("play")
    duration = str(item.get("duration", "")).strip()

    resource_id = f"res-bili-{bvid}"
    content = {
        "bvid": bvid,
        "author": author,
        "description": description,
        "url": url,
        "embed_url": bilibili_embed_url(bvid),
        "cover": pic,
        "play": play,
        "duration": duration,
        "tags": tags,
        "source": "bilibili_live_search",
    }
    source_refs = [
        {
            "document_id": "bilibili-live-search",
            "chunk_id": f"chunk-{bvid}",
            "course_id": "course-bilibili-recommendations",
            "resource_id": resource_id,
            "chapter": topic or "视频推荐",
            "section": "B站实时搜索",
            "url": url,
            "bvid": bvid,
        }
    ]
    return LearningResource(
        resource_id=resource_id,
        type="video",
        title=title,
        target_topic=topic or title,
        difficulty="adaptive",
        content=content,
        source_refs=source_refs,
        personalized_reason=reason or f"B站「{topic or title}」实时搜索精选",
        tags=tags,
    )


async def search_bilibili_videos(query: str, limit: int = 6, reason: str = "") -> list[LearningResource]:
    """Search Bilibili in real time and return relevance-filtered LearningResources.

    Returns an empty list on any failure so callers can fall back to the local pool.
    """
    topic = (query or "").strip()
    if not topic:
        return []
    terms = _significant_terms(topic)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=8.0), follow_redirects=True) as client:
            # warm up to obtain the `buvid` cookie the search API expects
            try:
                await client.get(WARMUP_URL, headers=_HEADERS)
            except httpx.HTTPError:
                pass
            response = await client.get(
                SEARCH_API,
                headers=_HEADERS,
                params={"search_type": "video", "keyword": topic, "page": 1},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:  # network / JSON errors
        raise BilibiliSearchError(str(exc)) from exc

    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise BilibiliSearchError(f"bilibili search returned code={payload.get('code') if isinstance(payload, dict) else 'n/a'}")

    raw_results = payload.get("data", {}).get("result", [])
    if not isinstance(raw_results, list):
        return []

    # rank: relevant first, then by play count
    hard_must = _hard_match_terms(topic)
    relevant = [item for item in raw_results if isinstance(item, dict) and _is_relevant(item, terms, hard_must)]
    pool = relevant
    pool.sort(key=lambda it: int(it.get("play") or 0), reverse=True)

    resources: list[LearningResource] = []
    seen_bvids: set[str] = set()
    for item in pool:
        resource = _to_resource(item, topic, reason)
        if not resource:
            continue
        bvid = resource.content.get("bvid")
        if bvid in seen_bvids:
            continue
        seen_bvids.add(str(bvid))
        resources.append(resource)
        if len(resources) >= limit:
            break
    return resources


class BilibiliSearchError(RuntimeError):
    """Raised when the live Bilibili search cannot be completed."""


def search_bilibili_videos_sync(query: str, limit: int = 6, reason: str = "") -> list[LearningResource]:
    """Blocking helper for sync contexts (falls back to empty list on error)."""
    try:
        return asyncio.run(search_bilibili_videos(query, limit=limit, reason=reason))
    except (BilibiliSearchError, RuntimeError):
        return []
