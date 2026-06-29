from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.session import SessionHeaders, get_session_headers, resolve_session_from_request
from app.cram.engine import CramSessionCreate
from app.database.store import get_store
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize, new_id


router = APIRouter(prefix="/api/cram", tags=["cram"])


class CramSessionCreateRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    course_title: str
    topics: list[str] = Field(default_factory=list)
    exam_types: list[str] = Field(default_factory=list)
    must_know: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    textbook: str | None = None
    materials: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)


class CramAdvanceRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


def _session_from_request(body: CramSessionCreateRequest | CramAdvanceRequest, headers: SessionHeaders):
    return resolve_session_from_request(
        explicit_student_id=body.student_id,
        explicit_course_id=body.course_id,
        explicit_conversation_id=body.conversation_id,
        headers=headers,
    )


def _cram_canvas_app(session, conversation_id: str | None) -> CanvasApp:
    return CanvasApp(
        app_id=new_id("app_cram"),
        app_type="exam.cram",
        title=f"{session.course_title} · 期末速成",
        icon="GraduationCap",
        position=CanvasPosition(x=1040, y=120),
        size=CanvasSize(width=430, height=380),
        z_index=18,
        payload={"session": session.model_dump(mode="json"), "session_id": session.session_id},
        source={"student_id": session.student_id, "course_id": session.course_id, "conversation_id": conversation_id},
        source_refs=session.source_refs,
        actions=[
            {"label": "继续", "action": "cram.advance", "payload": {"action": "teach_next_batch"}},
            {"label": "查看仪表盘", "action": "dashboard.refresh"},
        ],
    )


@router.get("/openstax-books")
async def openstax_books() -> dict[str, Any]:
    books = get_store().ensure_openstax_book_seeds()
    return {"books": books, "count": len(books)}


@router.get("/sessions")
async def list_cram_sessions(
    student_id: str | None = None,
    course_id: str | None = None,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session_from_request(
        explicit_student_id=student_id,
        explicit_course_id=course_id,
        explicit_conversation_id=None,
        headers=headers,
    )
    sessions = get_store().list_cram_sessions(session.student_id, course_id=session.course_id)
    return {"sessions": [item.model_dump(mode="json") for item in sessions]}


@router.post("/sessions")
async def create_cram_session(request: CramSessionCreateRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session_context = _session_from_request(request, headers)
    store = get_store()
    created = store.create_cram_session(
        CramSessionCreate(
            student_id=session_context.student_id,
            course_id=session_context.course_id,
            course_title=request.course_title,
            exam_types=request.exam_types,
            must_know=request.must_know or request.topics[:4],
            key_points=request.key_points or request.topics[4:],
            textbook=request.textbook,
            materials=request.materials,
            preferences=request.preferences,
        )
    )
    app = _cram_canvas_app(created, session_context.conversation_id)
    saved_app = store.save_app(app, student_id=session_context.student_id, course_id=session_context.course_id, agent="cram_engine", skill="cram-engine-skill")
    dashboard = store.dashboard(session_context.student_id, course_id=session_context.course_id, conversation_id=session_context.conversation_id)
    return {"session": created.model_dump(mode="json"), "app": saved_app.model_dump(), "dashboard": dashboard.model_dump()}


@router.get("/sessions/{session_id}")
async def get_cram_session(session_id: str, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session_context = resolve_session_from_request(
        explicit_student_id=None,
        explicit_course_id=None,
        explicit_conversation_id=None,
        headers=headers,
    )
    session = get_store().get_cram_session(session_id, student_id=session_context.student_id, course_id=session_context.course_id)
    if not session:
        raise HTTPException(status_code=404, detail="cram session not found")
    return {"session": session.model_dump(mode="json")}


@router.post("/sessions/{session_id}/advance")
async def advance_cram_session(session_id: str, request: CramAdvanceRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session_context = _session_from_request(request, headers)
    store = get_store()
    try:
        updated = store.advance_cram_session(
            session_id,
            action=request.action,
            payload=request.payload,
            student_id=session_context.student_id,
            course_id=session_context.course_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    dashboard = store.dashboard(session_context.student_id, course_id=session_context.course_id, conversation_id=session_context.conversation_id)
    return {"session": updated.model_dump(mode="json"), "dashboard": dashboard.model_dump()}
