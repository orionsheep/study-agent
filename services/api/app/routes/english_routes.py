"""
English learning API routes — proxy to english-word-fission backend.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_student
from app.english_word_service import (
    get_fission_graph,
    get_word_detail,
    get_word_list,
    get_quiz_data,
    submit_quiz_result,
    get_user_libraries,
    create_user_library,
    get_study_plan,
    update_study_plan,
    health_check,
)

router = APIRouter(prefix="/api/english", tags=["english"])


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
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get word list."""
    try:
        return await get_word_list(student_id, library_id, search, limit, offset)
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
    student_id: str = Depends(get_current_student),
) -> dict[str, Any]:
    """Get user libraries."""
    try:
        return await get_user_libraries(student_id)
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
