"""
English Word Service — API proxy to english-word-fission backend (port 3011).

Provides:
- Fission graph data (word relationships)
- Word list lookup
- Quiz data
- User library management

Authentication mapping: student_id (LearnForge) ↔ user_id (english-word-fission).
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

# english-word-fission backend URL
EFW_BASE_URL = os.getenv("EFW_BASE_URL", "http://localhost:3011")
EFW_API_KEY = os.getenv("EFW_API_KEY", "")

# In-memory mapping: student_id -> efw_user_id
# In production this should be persisted in the database
_student_id_to_efw_user: dict[str, str] = {}


def _get_efw_user_id(student_id: str) -> str | None:
    """Get the english-word-fission user_id for a student."""
    return _student_id_to_efw_user.get(student_id)


def _set_efw_user_id(student_id: str, efw_user_id: str) -> None:
    """Store the mapping from student_id to efw_user_id."""
    _student_id_to_efw_user[student_id] = efw_user_id


async def _efw_request(
    method: str,
    path: str,
    student_id: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make a request to the english-word-fission backend."""
    efw_user_id = _get_efw_user_id(student_id)
    headers: dict[str, str] = {}
    if EFW_API_KEY:
        headers["Authorization"] = f"Bearer {EFW_API_KEY}"
    if efw_user_id:
        headers["X-User-Id"] = efw_user_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=f"{EFW_BASE_URL}{path}",
            headers=headers,
            json=json,
            params=params,
        )
        response.raise_for_status()
        return response.json()


# ── Fission Graph ───────────────────────────────────────────────────────────

async def get_fission_graph(student_id: str, word: str, depth: int = 2) -> dict[str, Any]:
    """Get the fission graph (word relationship network) for a given word."""
    return await _efw_request(
        "GET",
        "/api/fission",
        student_id,
        params={"word": word, "depth": depth},
    )


# ── Word List ───────────────────────────────────────────────────────────────

# The "考试考纲" entry returned by EFW is a directory of CSV files (初中/高中/
# CET4/CET6/考研/托福/SAT). EFW's /api/words only does free-text search and returns
# bare strings; it cannot list the contents of a directory-backed library. So when a
# caller asks for the exam library, we route through /api/library-words instead,
# which reads the actual CSV and — crucially — can return each word WITH its
# chineseData (collins stars, definition, phonetic) when includeDefinitions=true.
# That's what the word list needs to render Collins stars + meanings per row.
_EXAM_LIBRARY_CSV = "考试考纲/3-CET4-顺序.csv"  # 7508 words, the canonical exam set


async def get_word_list(
    student_id: str,
    library_id: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Get a list of words (with optional search and library filter).

    For the exam library we use /api/library-words so the response carries per-word
    chineseData (collins / definition / phonetic). Free-text search still uses the
    lightweight /api/words endpoint.
    """
    # Library browse (考试考纲) — return rich word objects via library-words.
    is_exam_library = library_id in {"考试考纲", "exam", "考试考纲/3-CET4-顺序.csv"}
    if is_exam_library and not search:
        params: dict[str, Any] = {
            "path": _EXAM_LIBRARY_CSV,
            "groupIndex": str(offset // max(limit, 1)),
            "groupSize": str(limit),
            "includeDefinitions": "true",
        }
        data = await _efw_request("GET", "/api/library-words", student_id, params=params)
        # Normalize: EFW returns a bare array of word objects; expose as {words, total}.
        words = data if isinstance(data, list) else data.get("words", [])
        return {"words": words, "total": len(words)}

    # Free-text search — EFW's /api/words, optionally enriched.
    params = {}
    if search:
        params["query"] = search
        params["includeDefinitions"] = "true"
    params["limit"] = str(limit)
    params["offset"] = str(offset)
    if library_id and not is_exam_library:
        params["libraryId"] = library_id
    return await _efw_request(
        "GET",
        "/api/words",
        student_id,
        params=params,
    )


async def get_word_detail(student_id: str, word: str) -> dict[str, Any]:
    """Get detailed information about a single word."""
    return await _efw_request(
        "GET",
        f"/api/words/{word}",
        student_id,
    )


# ── Quiz ────────────────────────────────────────────────────────────────────

async def get_quiz_data(
    student_id: str,
    word: str,
    quiz_type: str = "multiple_choice",
) -> dict[str, Any]:
    """Get quiz questions for a word."""
    normalized_word = word.strip().lower()
    if not normalized_word:
        return {"questions": []}

    data = await _efw_request(
        "POST",
        "/api/quiz/data",
        student_id,
        json={"words": [normalized_word]},
    )
    entries = data if isinstance(data, list) else data.get("words") or data.get("data") or []
    entry = next((item for item in entries if str(item.get("word", "")).lower() == normalized_word), entries[0] if entries else {})
    if not entry:
        detail = await get_word_detail(student_id, normalized_word)
        entry = {"word": detail.get("word", normalized_word), "chineseData": detail}
    return {"questions": _quiz_questions_from_entry(entry, quiz_type)}


def _plain_text(value: Any) -> str:
    text = str(value or "").replace("\\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _definition_from_chinese_data(data: dict[str, Any]) -> str:
    for key in ("concise_definition", "translation", "definition", "meaning"):
        text = _plain_text(data.get(key))
        if text:
            return text
    definitions = data.get("definitions")
    if isinstance(definitions, list):
        parts: list[str] = []
        for item in definitions[:3]:
            if isinstance(item, dict):
                parts.append(_plain_text(item.get("definition") or item.get("meaning") or item.get("translation")))
            else:
                parts.append(_plain_text(item))
        text = "；".join(part for part in parts if part)
        if text:
            return text
    return "暂无释义"


def _quiz_questions_from_entry(entry: dict[str, Any], quiz_type: str) -> list[dict[str, Any]]:
    word = str(entry.get("word") or "").strip().lower()
    chinese_data = entry.get("chineseData") if isinstance(entry.get("chineseData"), dict) else entry
    definition = _definition_from_chinese_data(chinese_data if isinstance(chinese_data, dict) else {})
    phonetic = _plain_text((chinese_data or {}).get("phonetic") or (chinese_data or {}).get("pronunciation")) if isinstance(chinese_data, dict) else ""
    quiz_type = quiz_type if quiz_type in {"multiple_choice", "spelling", "recall"} else "multiple_choice"
    if quiz_type == "spelling":
        return [{
            "word": word,
            "quizType": "spelling",
            "question": f"根据释义拼写单词：{definition}",
            "options": [],
            "correctAnswer": word,
            "hint": phonetic or (word[:1] + "..." if word else ""),
        }]
    if quiz_type == "recall":
        return [{
            "word": word,
            "quizType": "recall",
            "question": f"请写出 “{word}” 的核心释义或用法。",
            "options": [],
            "correctAnswer": definition,
            "hint": phonetic or "可写中文释义、常见搭配或例句线索。",
        }]
    distractors = [
        "突然的、临时的变化",
        "一种工具或设备",
        "缓慢移动或拖延",
        "与主题无关的描述",
    ]
    options = [definition, *[item for item in distractors if item != definition]][:4]
    return [{
        "word": word,
        "quizType": "multiple_choice",
        "question": f"“{word}” 最贴近下面哪个释义？",
        "options": options,
        "correctAnswer": definition,
        "hint": phonetic or None,
    }]


async def submit_quiz_result(
    student_id: str,
    word: str,
    quiz_type: str,
    score: float,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Submit a quiz result."""
    test_type = {"multiple_choice": 1, "spelling": 2, "recall": 3}.get(quiz_type, 1)
    try:
        return await _efw_request(
            "POST",
            "/api/quiz/record",
            student_id,
            json={"word": word, "testType": test_type, "score": score},
        )
    except Exception:
        return {"status": "recorded_locally", "word": word, "type": quiz_type, "score": score, "answers": answers}


# ── User Library ────────────────────────────────────────────────────────────

async def get_libraries(student_id: str, path: str | None = None) -> dict[str, Any]:
    """Get libraries (system + user). Supports path parameter for file system browsing."""
    params = {}
    if path is not None:
        params["path"] = path
    return await _efw_request(
        "GET",
        "/api/libraries",
        student_id,
        params=params,
    )

def _resolve_library_path(path: str) -> str:
    """Map a workspace library path to the concrete CSV EFW should read.

    The workspace only exposes 考试考纲 (a directory of CSVs). EFW's library-words /
    library-groups endpoints need an actual .csv file, so we point the directory at
    its canonical contents (CET4-顺序, the primary exam word set).
    """
    normalized = path.strip().rstrip("/")
    if normalized in {"", "考试考纲", "exam"}:
        return _EXAM_LIBRARY_CSV
    return path


async def get_library_words(student_id: str, path: str, group_index: int | None = None, group_size: int = 100, include_definitions: bool = False) -> dict[str, Any]:
    """Get words from a library file."""
    csv_path = _resolve_library_path(path)
    params: dict[str, Any] = {"path": csv_path, "groupSize": group_size}
    if group_index is not None:
        params["groupIndex"] = group_index
    if include_definitions:
        params["includeDefinitions"] = "true"
    return await _efw_request(
        "GET",
        "/api/library-words",
        student_id,
        params=params,
    )

async def get_library_groups(student_id: str, path: str, group_size: int = 100) -> dict[str, Any]:
    """Get groups for a library file."""
    csv_path = _resolve_library_path(path)
    params = {"path": csv_path, "groupSize": group_size}
    return await _efw_request(
        "GET",
        "/api/library-groups",
        student_id,
        params=params,
    )

async def get_user_libraries(student_id: str) -> dict[str, Any]:
    """Get the user's word libraries."""
    return await _efw_request(
        "GET",
        "/api/libraries",
        student_id,
    )


async def create_user_library(student_id: str, name: str) -> dict[str, Any]:
    """Create a new word library."""
    return await _efw_request(
        "POST",
        "/api/libraries",
        student_id,
        json={"name": name},
    )


# ── Study Plan ──────────────────────────────────────────────────────────────

async def get_study_plan(student_id: str) -> dict[str, Any]:
    """Get the user's study plan."""
    return await _efw_request(
        "GET",
        "/api/study-plan",
        student_id,
    )


async def update_study_plan(student_id: str, daily_goal: int) -> dict[str, Any]:
    """Update the user's study plan."""
    return await _efw_request(
        "PUT",
        "/api/study-plan",
        student_id,
        json={"dailyGoal": daily_goal},
    )


# ── Health Check ────────────────────────────────────────────────────────────

async def health_check() -> dict[str, Any]:
    """Check if the english-word-fission backend is reachable.

    EFW has no dedicated /api/health route, so we probe /api/libraries instead —
    a lightweight read-only endpoint that exists on every install. A 2xx response
    (even an empty list) means the backend is up and the DB is reachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{EFW_BASE_URL}/api/libraries",
                headers={"X-User-Id": "health-check"},
            )
            response.raise_for_status()
            return {"status": "ok", "reachable": True, "base_url": EFW_BASE_URL}
    except Exception as e:
        return {
            "status": "error",
            "reachable": False,
            "base_url": EFW_BASE_URL,
            "message": str(e) or repr(e),
        }
