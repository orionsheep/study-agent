"""
English learning API routes — proxy to english-word-fission backend.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.session import SessionHeaders, get_session_headers, resolve_session_context
from app.english_word_service import (
    _efw_request,
    get_fission_graph,
    get_word_detail,
    get_word_list,
    get_quiz_data,
    submit_quiz_result,
    get_libraries,
    get_library_words,
    get_library_groups,
    create_user_library,
    get_study_plan,
    update_study_plan,
    health_check,
)

router = APIRouter(prefix="/api/english", tags=["english"])


def get_current_student(headers: SessionHeaders = Depends(get_session_headers)) -> str:
    """Extract student_id from session headers."""
    ctx = resolve_session_context(
        explicit_student_id=None,
        explicit_course_id=None,
        headers=headers,
    )
    return ctx.student_id


@router.get("/health")
async def english_health() -> dict[str, Any]:
    """Check english-word-fission backend health."""
    return await health_check()


@router.get("/fission")
async def fission_graph(
    word: str,
    depth: int = Query(default=2, ge=1, le=4),
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get fission graph (word relationship network)."""
    try:
        return await get_fission_graph(student_id, word, depth)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/words")
async def word_list(
    library_id: str | None = None,
    library_id_camel: str | None = Query(default=None, alias="libraryId"),
    search: str | None = Query(default=None),
    # The english-word-fission frontend historically sends `query` (not `search`),
    # and the ported WordList.tsx still does. Accept both so the search box actually
    # filters words instead of silently returning an empty list.
    query: str | None = Query(default=None, alias="query"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get word list."""
    try:
        effective_search = search or query
        effective_library_id = library_id or library_id_camel
        return await get_word_list(student_id, effective_library_id, effective_search, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/words/{word}")
async def word_detail(
    word: str,
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get word detail."""
    try:
        return await get_word_detail(student_id, word)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/quiz")
async def quiz_data(
    word: str,
    quiz_type: str = Query(default="multiple_choice"),
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get quiz data for a word."""
    try:
        return await get_quiz_data(student_id, word, quiz_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.post("/quiz/submit")
async def quiz_submit(
    data: dict[str, Any],
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Submit quiz result."""
    try:
        return await submit_quiz_result(
            student_id,
            data.get("word", ""),
            data.get("type", "multiple_choice"),
            data.get("score", 0.0),
            data.get("answers", []),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/libraries")
async def libraries(
    path: str | None = Query(default=None),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get libraries (system file system + user libraries).

    透传 EFW 文件系统条目（directory + csv file），让工作区能逐层浏览：
    根目录看到「考试考纲」目录，点进去看到 14 个考纲 csv（初中/高中/CET4/CET6/考研/托福/SAT，
    各顺序+乱序），再点某个 csv 进入单词列表。旧实现只返回 directory、过滤掉 csv，
    导致点进「考试考纲」后是空的。
    """
    try:
        data = await get_libraries(student_id, path)
        items = data if isinstance(data, list) else data.get("libraries", [])
        return items
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/library-words")
async def library_words(
    path: str = Query(...),
    group_index: int | None = Query(default=None, alias="groupIndex"),
    group_size: int = Query(default=100, ge=1, le=500, alias="groupSize"),
    include_definitions: bool = Query(default=False, alias="includeDefinitions"),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get words from a library file."""
    try:
        return await get_library_words(student_id, path, group_index, group_size, include_definitions)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/library-groups")
async def library_groups(
    path: str = Query(...),
    group_size: int = Query(default=100, ge=1, le=500, alias="groupSize"),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get groups for a library file."""
    try:
        return await get_library_groups(student_id, path, group_size)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/user/progress")
async def user_progress(
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get user learning progress."""
    try:
        # Proxy to english-word-fission /api/user/progress
        return await _efw_request("GET", "/api/user/progress", student_id)
    except Exception as e:
        # Fallback: return empty progress if backend not available
        return {}


@router.get("/notes")
async def notes(
    word: str = Query(...),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get notes for a word."""
    try:
        return await _efw_request("GET", "/api/notes", student_id, params={"word": word})
    except Exception as e:
        return []


@router.get("/user/libraries/{library_id}/words")
async def user_library_words(
    library_id: str,
    group_index: int | None = Query(default=None),
    group_size: int = Query(default=100, ge=1, le=500),
    include_definitions: bool = Query(default=False),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get words from a user library."""
    try:
        params: dict[str, Any] = {"groupSize": group_size}
        if group_index is not None:
            params["groupIndex"] = group_index
        if include_definitions:
            params["includeDefinitions"] = "true"
        return await _efw_request("GET", f"/api/user/libraries/{library_id}/words", student_id, params=params)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/user/libraries/{library_id}/groups")
async def user_library_groups(
    library_id: str,
    group_size: int = Query(default=100, ge=1, le=500),
    student_id: str = Depends(get_current_student),
) -> Any:
    """Get groups for a user library."""
    try:
        return await _efw_request("GET", f"/api/user/libraries/{library_id}/groups", student_id, params={"groupSize": group_size})
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.post("/libraries")
async def create_library(
    data: dict[str, str],
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Create a new library."""
    try:
        return await create_user_library(student_id, data.get("name", ""))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.get("/study-plan")
async def study_plan(
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get study plan."""
    try:
        return await get_study_plan(student_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")


@router.put("/study-plan")
async def update_plan(
    data: dict[str, int],
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Update study plan."""
    try:
        return await update_study_plan(student_id, data.get("dailyGoal", 10))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"EFW backend error: {e}")
