from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger
from typing import Any

from fastapi import Header, HTTPException


LOGGER = getLogger(__name__)


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


@dataclass(frozen=True)
class SessionHeaders:
    authorization: str | None = None
    x_student_id: str | None = None
    x_course_id: str | None = None
    x_conversation_id: str | None = None


@dataclass(frozen=True)
class SessionContext:
    student_id: str
    course_id: str
    conversation_id: str | None = None
    user_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "course_id": self.course_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
        }


def get_session_headers(
    authorization: str | None = Header(default=None),
    x_student_id: str | None = Header(default=None, alias="X-Student-Id"),
    x_course_id: str | None = Header(default=None, alias="X-Course-Id"),
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-Id"),
) -> SessionHeaders:
    return SessionHeaders(
        authorization=_parse_bearer_token(authorization),
        x_student_id=x_student_id,
        x_course_id=x_course_id,
        x_conversation_id=x_conversation_id,
    )


def resolve_session_context(
    *,
    explicit_student_id: str | None,
    explicit_course_id: str | None,
    explicit_conversation_id: str | None = None,
    headers: SessionHeaders | None = None,
    defaults: tuple[str, str] = ("demo-student", "ai-course"),
) -> SessionContext:
    headers = headers or SessionHeaders()
    auth_session: dict[str, Any] | None = None
    if headers.authorization:
        from app.database.store import get_store

        auth_session = get_store().get_auth_session(headers.authorization)
        if not auth_session:
            raise HTTPException(status_code=401, detail={"code": "INVALID_SESSION", "message": "authentication token is invalid"})

    header_student = str(auth_session["student_id"]) if auth_session else headers.x_student_id
    header_course = str(auth_session["course_id"]) if auth_session else headers.x_course_id

    if header_student and explicit_student_id and explicit_student_id != header_student:
        LOGGER.warning(
            "forbidden: header student mismatch (header=%s, explicit=%s)",
            header_student,
            explicit_student_id,
        )
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_STUDENT_CONTEXT", "message": "student_id context mismatch"})

    if header_course and explicit_course_id and explicit_course_id != header_course:
        LOGGER.warning(
            "forbidden: header course mismatch (header=%s, explicit=%s)",
            header_course,
            explicit_course_id,
        )
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_COURSE_CONTEXT", "message": "course_id context mismatch"})

    if explicit_student_id and not explicit_student_id.strip():
        explicit_student_id = None
    if explicit_course_id and not explicit_course_id.strip():
        explicit_course_id = None

    student_id = explicit_student_id or header_student or defaults[0]
    course_id = explicit_course_id or header_course or defaults[1]
    conversation_id = explicit_conversation_id or headers.x_conversation_id

    if not header_student and explicit_student_id is None:
        LOGGER.warning("legacy fallback used for session student_id (no identity headers)")
    if not header_course and explicit_course_id is None:
        LOGGER.warning("legacy fallback used for session course_id (no X-Course-Id)")

    return SessionContext(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        user_id=str(auth_session["user_id"]) if auth_session else None,
    )


def resolve_session_from_request(
    explicit_student_id: str | None,
    explicit_course_id: str | None,
    explicit_conversation_id: str | None = None,
    *,
    headers: SessionHeaders | None = None,
) -> SessionContext:
    """Backward-compatible alias used by API routers.

    The project currently has mixed-style endpoints (some path-based IDs, some body-based
    IDs, and some header-driven). Keep one canonical call point so access checks stay
    consistent while retaining compatibility.
    """

    return resolve_session_context(
        explicit_student_id=explicit_student_id,
        explicit_course_id=explicit_course_id,
        explicit_conversation_id=explicit_conversation_id,
        headers=headers,
    )
