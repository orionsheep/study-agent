from __future__ import annotations

import asyncio
import json
import re
from logging import getLogger
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import hash_password, issue_session, verify_password
from app.agents.app_canvas_agent import AppCanvasAgent
from app.agents.base import TutorTurnContext
from app.agents.evaluator_agent import EvaluatorAgent, EvaluatorAgentInput
from app.agents.orchestrator_agent import UnifiedOrchestrator
from app.agents.profile_agent import ProfileAgent, ProfileAgentInput
from app.canvas.materializer import CanvasMaterializer
from app.core.config import get_settings
from app.core.session import SessionContext, SessionHeaders, get_session_headers, resolve_session_from_request
from app.database.schema import REQUIRED_TABLES
from app.database.store import get_store
from app.edumem0.client import EduMem0Client
from app.edumem0.preference_memory import preference_memory
from app.hermes_runtime.runtime import HermesRuntime
from app.hermes_runtime.task_executor import HermesTaskExecutor
from app.image_gateway.router import ImageGatewayRouter
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked
from app.model_gateway.router import ModelGatewayRouter
from app.notebooklm_service import OpenNotebookBridge
from app.onboarding import extract_dimensions_with_llm, fetch_url_source, infer_profile_from_sources, parse_profile_upload, write_profile_memories
from app.rag.knowledge_graph import KnowledgeGraphBuilder
from app.rag.chunker import TextChunker
from app.rag.parser import CourseParser
from app.rag.retriever import CourseRetriever
from app.schemas.app_protocol import AppEvent, CanvasApp, DashboardSnapshot, EduMemoryItem, LearningResource
from app.skills.base import SkillInput
from app.skills.image_generation_skill import ImageGenerationSkill
from app.skills.registry import SkillRegistry
from app.storage.artifacts import ObjectStorage, artifact_object_key


class ChatRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    model_provider: str | None = None
    message: str
    requested_skill: str | None = None
    context_payload: dict[str, Any] | None = None
    attachments: list[dict[str, Any]] | None = None
    image_data: list[str] | None = None


class CourseRequest(BaseModel):
    title: str
    description: str | None = None


class CourseDocumentRequest(BaseModel):
    title: str
    content: str
    file_url: str | None = None


class MemorySearchRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    knowledge_point_id: str | None = None
    query: str | None = None
    memory_types: list[str] = Field(default_factory=list)
    limit: int = 10


class QuizSubmitRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    answer: Any


class CanvasAppCreateRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    app_type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class ArtifactUploadUrlRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    kind: str = "upload"
    filename: str = "artifact.bin"
    content_type: str = "application/octet-stream"
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# Whitelist of fields a client may patch on a canvas app. Crucially it excludes
# student_id/course_id/owner fields — identity comes from the authenticated session,
# never from the request body.
class CanvasAppPatchRequest(BaseModel):
    position: dict[str, Any] | None = None
    size: dict[str, Any] | None = None
    state: str | None = None
    status: str | None = None
    payload: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    title: str | None = None
    z_index: int | None = None
    group_id: str | None = None

    def to_patch(self) -> dict[str, Any]:
        return {key: value for key, value in self.model_dump().items() if value is not None}


def _is_status_assistant_message(text: str) -> bool:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return True
    status_markers = [
        "✅ 正在",
        "正在深度分析",
        "后台继续",
        "报告已生成并推送到画布",
        "分析完成！报告已生成",
        "HTML报告已生成，正在推送到画布",
        "是否确认开始生成",
        "这是一个比较耗时的任务",
        "不会影响你继续提问",
        "请查看左侧 Canvas",
        "已推送到画布",
        "产物校验没有通过",
        "需要重新触发 Hermes",
        "这次不会创建画布产物",
        "没能生成达标的内容",
    ]
    if any(marker in value for marker in status_markers):
        return True
    return value.startswith("✅") and len(value) <= 80


CHAT_CONTEXT_FETCH_LIMIT = 60
SEMANTIC_CHAT_WINDOW_LIMIT = 24


def _assistant_message_is_operational(item: dict[str, Any]) -> bool:
    if str(item.get("role") or "") != "assistant":
        return False
    text = str(item.get("text") or "")
    if _is_status_assistant_message(text):
        return True
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    if metadata.get("consent_required") or metadata.get("verification_failed") or metadata.get("artifact_verifier"):
        return True
    if metadata.get("background_generated") and any(
        marker in text
        for marker in [
            "已生成并推送到画布",
            "请查看左侧 Canvas",
            "已推送到画布",
            "没能生成达标的内容",
        ]
    ):
        return True
    return False


def _semantic_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    semantic = [item for item in messages if not _assistant_message_is_operational(item)]
    if len(semantic) <= SEMANTIC_CHAT_WINDOW_LIMIT:
        return semantic
    return semantic[-SEMANTIC_CHAT_WINDOW_LIMIT:]


class CanvasAppEventRequest(BaseModel):
    conversation_id: str | None = None
    event_type: str = "app.event"
    payload: dict[str, Any] = Field(default_factory=dict)


class ResourceFeedbackRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    resource_id: str | None = None
    app_id: str | None = None
    preference: str
    sentiment: str = "positive"
    rating: int | None = None
    comment: str | None = None


class ImageGenerateRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    conversation_id: str | None = None
    app_id: str | None = None
    topic: str
    teaching_goal: str = "生成可解释教学图"
    provider_alias: str | None = None


class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    course_id: str = "ai-course"


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class OnboardingMessageRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    message: str


class OnboardingSourceRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    source_type: str = "document"
    title: str = "学习资料"
    text: str | None = None
    url: str | None = None
    school: str | None = None
    major: str | None = None
    grade: str | None = None


app = FastAPI(title="LearnForge V2 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register english learning routes
from app.routes.english_routes import router as english_router
app.include_router(english_router)

# Register NotebookLM/Open Notebook bridge routes. Open Notebook is a background
# source engine only; LearnForge Hermes remains the only visible answer channel.
from app.routes.notebooklm_routes import router as notebooklm_router
app.include_router(notebooklm_router)

# Register Cram Engine routes. Hermes remains the capability chooser; this router
# stores the exam-sprint state machine and projects it into dashboard/canvas data.
from app.routes.cram_routes import router as cram_router
app.include_router(cram_router)

LOGGER = getLogger("learnforge.api")

# Patterns scrubbed from exception text before it is surfaced to the client, since raw
# errors may contain filesystem paths, API key fragments, or connection strings.
_SENSITIVE_PATTERNS = [
    re.compile(r"/[^\s'\"<>]+\.py"),                      # local filesystem paths
    re.compile(r"(sk-[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+"),   # API key fragments (sk-…)
    re.compile(r"(?i)(password|token|api[_-]?key|secret)=?[^\s'\"]+"),
    re.compile(r"postgresql?://[^\s'\"]+"),                # DB connection URLs
]


def _sanitize_exception_for_client(exc: BaseException) -> str:
    """Return a short, scrubbed exception label safe to show in the chat / trace UI."""
    text = f"{type(exc).__name__}: {exc}"
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:200]


def resolve_session(
    explicit_student_id: str | None = None,
    explicit_course_id: str | None = None,
    explicit_conversation_id: str | None = None,
    *,
    headers: SessionHeaders,
) -> SessionContext:
    return resolve_session_from_request(
        explicit_student_id=explicit_student_id,
        explicit_course_id=explicit_course_id,
        explicit_conversation_id=explicit_conversation_id,
        headers=headers,
    )


def build_tutor_context(
    request: ChatRequest,
    headers: SessionHeaders,
) -> TutorTurnContext:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        explicit_conversation_id=request.conversation_id,
        headers=headers,
    )
    store = get_store()
    conversation_id = session.conversation_id or "demo-conversation"
    recent_messages = store.list_chat_messages(
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=conversation_id,
        limit=CHAT_CONTEXT_FETCH_LIMIT,
    )
    semantic_recent_messages = _semantic_chat_messages(recent_messages)
    last_assistant_answer = next(
        (
            item.get("text")
            for item in reversed(semantic_recent_messages)
            if item.get("role") == "assistant" and item.get("text")
        ),
        None,
    )
    recent_apps = [
        item.model_dump() if hasattr(item, "model_dump") else dict(item)
        for item in store.list_apps(session.student_id, course_id=session.course_id, conversation_id=conversation_id)[-8:]
    ]
    try:
        resource_items = store.list_resources(session.student_id, course_id=session.course_id)
    except TypeError:
        try:
            resource_items = store.list_resources(course_id=session.course_id)
        except TypeError:
            try:
                resource_items = store.list_resources(session.student_id)
            except TypeError:
                resource_items = store.list_resources()
    recent_resources = [
        item.model_dump() if hasattr(item, "model_dump") else dict(item)
        for item in resource_items[-8:]
    ]
    focus = store.get_learning_focus(session.student_id, session.course_id)
    try:
        profile = store.get_profile(session.student_id, course_id=session.course_id) or {}
    except Exception:
        profile = {}
    try:
        _raw_mem = store.search_memories(
            session.student_id,
            course_id=session.course_id,
            memory_types=["profile", "mastery", "misconception", "resource_preference"],
            limit=24,
        )
        student_memories = [
            {
                "type": m.memory_type,
                "content": m.content,
                "topic": m.knowledge_point_id,
                "confidence": m.confidence,
                "importance": m.importance,
            }
            for m in _raw_mem
        ]
    except Exception:
        student_memories = []
    return TutorTurnContext(
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=conversation_id,
        message=request.message,
        requested_skill=request.requested_skill,
        context_payload=request.context_payload or {},
        attachments=request.attachments or [],
        model_provider=request.model_provider,
        recent_messages=semantic_recent_messages,
        last_assistant_answer=last_assistant_answer,
        recent_apps=recent_apps,
        recent_resources=recent_resources,
        profile=profile,
        student_memories=student_memories,
        current_topic=focus.get("topic") or None,
        current_objective=focus.get("objective") or None,
        image_data=request.image_data,
    )


async def system_status() -> dict[str, Any]:
    store = get_store()
    model_gateway = ModelGatewayRouter()
    model_provider_statuses = await model_gateway.statuses()
    image_statuses = await ImageGatewayRouter().statuses()
    image2_status = image_statuses["image2"]
    gemini_image_status = image_statuses["gemini_image"]
    hermes_status = HermesRuntime().status()
    hermes_payload = hermes_status.model_dump()
    if get_settings().app_env.lower() == "production" and hermes_payload.get("execution_mode") == "cli_oneshot":
        hermes_payload["status"] = "blocked_cli_fallback_in_production"
        hermes_payload["reason"] = "Production requires Hermes SDK embedded mode; CLI one-shot fallback is blocked."
    object_storage_status = ObjectStorage().status()
    try:
        notebooklm_status = await OpenNotebookBridge().status()
    except Exception as exc:
        notebooklm_status = {"status": "blocked_bridge_error", "reason": _sanitize_exception_for_client(exc)}
    database_status = "ready" if store.schema_ready() else "blocked_schema_missing"
    text_model_ready = any(status.status == "ready" for status in model_provider_statuses.values())
    # Overall is gated on text model + at least one image provider + hermes.
    image_ready = image2_status.status == "ready" or gemini_image_status.status == "ready"
    external_ready = text_model_ready and image_ready and hermes_payload.get("status") == "ready" and object_storage_status.get("status") == "ready"
    overall = "ready" if database_status == "ready" and external_ready else "blocked_external"
    dumped_model_statuses = {name: status.model_dump() for name, status in model_provider_statuses.items()}
    return {
        "overall": overall,
        "backend": {"status": "ready", "reason": "FastAPI app initialized."},
        "database": {"status": database_status, "required_tables": REQUIRED_TABLES, "path": str(store.path)},
        "gemini": dumped_model_statuses.get("gemini", {"name": "gemini", "status": "blocked_provider_error"}),
        "model_providers": dumped_model_statuses,
        "hermes": hermes_payload,
        "object_storage": object_storage_status,
        "image2": image2_status.model_dump(),
        "gemini_image": gemini_image_status.model_dump(),
        "edumem0": {"status": "ready", "reason": "EduMem0 store and policies initialized."},
        "rag": {"status": "ready", "reason": "Seed course chunks and source_refs are available."},
        "notebooklm": notebooklm_status,
    }


def auth_payload_for_session(token: str, session: dict[str, Any]) -> dict[str, Any]:
    store = get_store()
    user = store.get_user(session["user_id"]) or {}
    onboarding = store.start_onboarding(session["student_id"], session["course_id"])
    return {
        "token": token,
        "user": {
            "user_id": session["user_id"],
            "email": user.get("email"),
            "display_name": user.get("display_name"),
        },
        "student": {
            "student_id": session["student_id"],
            "course_id": session["course_id"],
            "profile_status": store.profile_status(session["student_id"], session["course_id"]),
        },
        "onboarding": onboarding,
    }


def require_auth(headers: SessionHeaders) -> dict[str, Any]:
    token = headers.authorization
    if not token:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Bearer token is required."})
    session = get_store().get_auth_session(token)
    if not session:
        raise HTTPException(status_code=401, detail={"code": "INVALID_SESSION", "message": "authentication token is invalid"})
    return session


def onboarding_status_payload(student_id: str, course_id: str) -> dict[str, Any]:
    store = get_store()
    onboarding = store.start_onboarding(student_id, course_id)
    sources = store.list_profile_sources(student_id, course_id=course_id)
    profile = store.get_profile(student_id, course_id=course_id)
    required = [
        "school",
        "major",
        "grade",
        "schedule",
        "learning_goal",
        "knowledge_foundation",
        "weak_points",
        "preferred_resources",
        "learning_pace",
        "available_study_time",
        "interests",
        "mastery_map",
        "subject_confidence",
    ]
    filled = [key for key in required if profile.get(key) not in (None, "", [], {})]
    coverage = round(len(filled) / len(required), 3)
    return {
        "onboarding": onboarding,
        "profile_status": store.profile_status(student_id, course_id),
        "profile": profile,
        "coverage": coverage,
        "missing_fields": store.onboarding_missing_fields(student_id, course_id),
        "sources": [
            {
                "id": item["id"],
                "source_type": item["source_type"],
                "title": item["title"],
                "parser_status": item["parser_status"],
                "parser_reason": item.get("parser_reason"),
                "created_at": item["created_at"],
                "structured_payload": item.get("structured_payload", {}),
            }
            for item in sources
        ],
        "next_actions": [
            "上传课表或学习资料" if "课表" in store.onboarding_missing_fields(student_id, course_id) else "补充学习目标",
            "用几句话说明当前薄弱点和喜欢的学习方式",
            "信息足够后点击生成画像",
        ],
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    store = get_store()
    database_status = "ready" if store.schema_ready() else "blocked_schema_missing"
    return {
        "status": "ready" if database_status == "ready" else "blocked",
        "components": {
            "backend": {"status": "ready", "reason": "FastAPI app initialized."},
            "database": {"status": database_status, "required_tables": REQUIRED_TABLES, "path": str(store.path)},
        },
    }


@app.get("/api/system/status")
async def api_system_status() -> dict[str, Any]:
    return await system_status()


def _assert_artifact_visible(artifact: dict[str, Any], session: SessionContext) -> None:
    owner = artifact.get("student_id")
    course = artifact.get("course_id")
    if owner and owner != session.student_id:
        raise HTTPException(status_code=404, detail="artifact not found")
    if course and course != session.course_id:
        raise HTTPException(status_code=404, detail="artifact not found")


@app.post("/api/artifacts/upload-url")
async def create_artifact_upload_url(
    request_body: ArtifactUploadUrlRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request_body.student_id,
        explicit_course_id=request_body.course_id,
        explicit_conversation_id=request_body.conversation_id,
        headers=headers,
    )
    artifact_id = f"artifact_{uuid4().hex[:12]}"
    object_key = artifact_object_key(kind=request_body.kind, artifact_id=artifact_id, filename=request_body.filename)
    artifact = get_store().save_artifact(
        artifact_id=artifact_id,
        kind=request_body.kind,
        object_key=object_key,
        content_type=request_body.content_type,
        sha256="pending",
        size_bytes=0,
        title=request_body.title or request_body.filename,
        source_run_id=None,
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=session.conversation_id,
        metadata={**request_body.metadata, "upload_status": "pending", "filename": request_body.filename},
    )
    return {
        "artifact": artifact,
        "artifact_id": artifact_id,
        "method": "PUT",
        "upload_url": f"/api/artifacts/{artifact_id}/content",
        "content_url": f"/api/artifacts/{artifact_id}/content",
        "object_key": object_key,
    }


@app.get("/api/artifacts/{artifact_id}")
async def get_artifact_metadata(
    artifact_id: str,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session(headers=headers)
    artifact = get_store().get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    _assert_artifact_visible(artifact, session)
    return artifact


@app.put("/api/artifacts/{artifact_id}/content")
async def put_artifact_content(
    artifact_id: str,
    raw_request: Request,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session(headers=headers)
    artifact = get_store().get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    _assert_artifact_visible(artifact, session)
    body = await raw_request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty artifact upload")
    content_type = raw_request.headers.get("content-type") or artifact.get("content_type") or "application/octet-stream"
    stored = ObjectStorage().put_bytes(object_key=str(artifact["object_key"]), data=body, content_type=content_type)
    saved = get_store().save_artifact(
        artifact_id=artifact_id,
        kind=str(artifact["kind"]),
        object_key=stored.object_key,
        content_type=stored.content_type,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        title=artifact.get("title"),
        source_run_id=artifact.get("source_run_id"),
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=session.conversation_id,
        metadata={**(artifact.get("metadata") or {}), "upload_status": "ready"},
    )
    return saved


@app.get("/api/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: str,
    headers: SessionHeaders = Depends(get_session_headers),
) -> Response:
    session = resolve_session(headers=headers)
    artifact = get_store().get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    _assert_artifact_visible(artifact, session)
    data, detected_content_type = ObjectStorage().get_bytes(str(artifact["object_key"]))
    media_type = str(artifact.get("content_type") or detected_content_type or "application/octet-stream")
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=60",
            "X-Artifact-Id": artifact_id,
            "X-Artifact-Sha256": str(artifact.get("sha256") or ""),
        },
    )


@app.post("/api/auth/register")
async def auth_register(request: AuthRegisterRequest) -> dict[str, Any]:
    if "@" not in request.email or len(request.password) < 6:
        raise HTTPException(status_code=400, detail={"code": "INVALID_AUTH_INPUT", "message": "email and password are required"})
    try:
        user = get_store().create_user_account(
            email=request.email,
            password_hash=hash_password(request.password),
            display_name=request.display_name or request.email.split("@")[0],
            course_id=request.course_id,
        )
    except ValueError as exc:
        if str(exc) == "email_exists":
            raise HTTPException(status_code=409, detail={"code": "EMAIL_EXISTS", "message": "email already registered"}) from exc
        raise
    session = issue_session(user["id"], user["student_id"], user["course_id"])
    return auth_payload_for_session(session["token"], session)


@app.post("/api/auth/login")
async def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
    user = get_store().get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "email or password is incorrect"})
    context = get_store().user_student_context(user["id"])
    if not context:
        raise HTTPException(status_code=409, detail={"code": "ACCOUNT_INCOMPLETE", "message": "student account is missing"})
    session = issue_session(user["id"], context["student_id"], context["course_id"] or "ai-course")
    return auth_payload_for_session(session["token"], session)


@app.get("/api/auth/me")
async def auth_me(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = require_auth(headers)
    return auth_payload_for_session(headers.authorization or session["token"], session)


@app.post("/api/onboarding/start")
async def onboarding_start(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = require_auth(headers)
    return onboarding_status_payload(session["student_id"], session["course_id"])


@app.get("/api/onboarding/status")
async def onboarding_status(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = require_auth(headers)
    return onboarding_status_payload(session["student_id"], session["course_id"])


@app.post("/api/onboarding/sources")
async def onboarding_sources(request: Request, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    auth_session = require_auth(headers)
    store = get_store()
    session = resolve_session(headers=headers)
    onboarding = store.start_onboarding(session.student_id, session.course_id)
    content_type = request.headers.get("content-type", "")
    parsed_sources: list[dict[str, Any]] = []
    if "multipart/form-data" in content_type:
        form = await request.form()
        source_type = str(form.get("source_type") or "document")
        title = str(form.get("title") or "学习资料")
        text_value = form.get("text")
        url_value = form.get("url")
        file_item = form.get("file")
        if hasattr(file_item, "read"):
            data = await file_item.read()  # type: ignore[attr-defined]
            parsed = await parse_profile_upload(
                data=data,
                filename=getattr(file_item, "filename", None),
                mime_type=getattr(file_item, "content_type", None),
                source_type=source_type,
            )
            parsed_sources.append(parsed)
        if text_value:
            parsed_sources.append(
                {
                    "source_type": source_type,
                    "title": title,
                    "raw_text": str(text_value),
                    "extracted_text": str(text_value),
                    "structured_payload": {},
                    "parser_status": "parsed",
                    "parser_reason": None,
                }
            )
        if url_value:
            parsed_sources.append(await fetch_url_source(str(url_value)))
    else:
        body = OnboardingSourceRequest.model_validate(await request.json())
        if body.student_id and body.student_id != auth_session["student_id"]:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_STUDENT_CONTEXT", "message": "student_id context mismatch"})
        if body.course_id and body.course_id != auth_session["course_id"]:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_COURSE_CONTEXT", "message": "course_id context mismatch"})
        if body.url:
            parsed_sources.append(await fetch_url_source(body.url))
        if body.text:
            structured = {}
            if body.source_type == "school_info":
                structured = {"school": body.school, "major": body.major, "grade": body.grade}
            parsed_sources.append(
                {
                    "source_type": body.source_type,
                    "title": body.title,
                    "raw_text": body.text,
                    "extracted_text": body.text,
                    "structured_payload": structured,
                    "parser_status": "parsed",
                    "parser_reason": None,
                }
            )
        if body.school or body.major or body.grade:
            school_text = " ".join(item for item in [body.school, body.major, body.grade] if item)
            parsed_sources.append(
                {
                    "source_type": "school_info",
                    "title": "学校信息",
                    "raw_text": school_text,
                    "extracted_text": school_text,
                    "structured_payload": {"school": body.school, "major": body.major, "grade": body.grade},
                    "parser_status": "parsed",
                    "parser_reason": None,
                }
            )
    if not parsed_sources:
        raise HTTPException(status_code=400, detail={"code": "SOURCE_EMPTY", "message": "no onboarding source was provided"})
    saved_sources = [
        store.save_profile_source(
            student_id=session.student_id,
            course_id=session.course_id,
            onboarding_session_id=onboarding["id"],
            file_name=item.get("file_name"),
            mime_type=item.get("mime_type"),
            url=item.get("structured_payload", {}).get("url") if isinstance(item.get("structured_payload"), dict) else None,
            **item,
        )
        for item in parsed_sources
    ]
    inferred = infer_profile_from_sources(saved_sources, [])
    store.save_profile(session.student_id, inferred, course_id=session.course_id)
    memories = write_profile_memories(session.student_id, session.course_id, saved_sources, inferred)
    store.update_onboarding(session.student_id, session.course_id, status="ready_to_generate", current_step="review_sources")
    return {
        "sources": saved_sources,
        "profile_preview": store.get_profile(session.student_id, session.course_id),
        "memories": [item.model_dump() for item in memories],
        **onboarding_status_payload(session.student_id, session.course_id),
    }


@app.post("/api/onboarding/message")
async def onboarding_message(request: OnboardingMessageRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    auth_session = require_auth(headers)
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        headers=headers,
    )
    if session.student_id != auth_session["student_id"]:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_STUDENT_CONTEXT", "message": "student_id context mismatch"})
    store = get_store()
    onboarding = store.start_onboarding(session.student_id, session.course_id)
    source = store.save_profile_source(
        student_id=session.student_id,
        course_id=session.course_id,
        onboarding_session_id=onboarding["id"],
        source_type="chat_message",
        title="画像问答",
        raw_text=request.message,
        extracted_text=request.message,
        structured_payload={},
        parser_status="parsed",
    )
    memories = await asyncio.to_thread(EduMem0Client().extract_from_chat, session.student_id, request.message, session.course_id)
    dimensions: dict[str, Any] = {}
    for memory in memories:
        dimensions = {**dimensions, **memory.structured_payload.get("dimensions", {})}
    # LLM extraction (robust, any school/major/grade/time) takes priority over keyword rules
    llm_dimensions = await extract_dimensions_with_llm(request.message)
    dimensions = {**dimensions, **llm_dimensions}
    if dimensions:
        store.save_profile(session.student_id, dimensions, course_id=session.course_id)
    store.update_onboarding(session.student_id, session.course_id, status="ready_to_generate", current_step="profile_dialogue")
    return {
        "source": source,
        "memories": [item.model_dump() for item in memories],
        **onboarding_status_payload(session.student_id, session.course_id),
    }


@app.post("/api/onboarding/generate-profile")
async def onboarding_generate_profile(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = require_auth(headers)
    store = get_store()
    sources = store.list_profile_sources(session["student_id"], course_id=session["course_id"], limit=120)
    chat_messages = [item.get("extracted_text", "") for item in sources if item.get("source_type") == "chat_message"]
    profile = infer_profile_from_sources(sources, chat_messages)
    saved_profile = store.save_profile(session["student_id"], profile, course_id=session["course_id"])
    memories = write_profile_memories(session["student_id"], session["course_id"], sources, saved_profile)
    if hasattr(store, "ensure_default_apps"):
        store.ensure_default_apps(session["student_id"], session["course_id"], full=True)
    store.update_onboarding(
        session["student_id"],
        session["course_id"],
        status="completed",
        current_step="completed",
        summary="画像已生成，可进入 LearnForge 主学习空间。",
    )
    return {
        "profile": saved_profile,
        "memories": [item.model_dump() for item in memories],
        **onboarding_status_payload(session["student_id"], session["course_id"]),
    }


@app.get("/api/chat/messages")
async def list_chat_messages(
    headers: SessionHeaders = Depends(get_session_headers),
    student_id: str | None = None,
    course_id: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=student_id,
        explicit_course_id=course_id,
        explicit_conversation_id=conversation_id,
        headers=headers,
    )
    conv_id = session.conversation_id or "demo-conversation"
    messages = get_store().list_chat_messages(
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=conv_id,
        limit=40,
    )
    return {"messages": messages}


@app.post("/api/auth/logout")
async def auth_logout(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    token = headers.authorization
    if token:
        get_store().delete_auth_session(token)
    return {"status": "ok"}


@app.post("/api/chat/message")
async def chat_message(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    # Non-streaming fallback. We materialize only the assistant text + run/message ids
    # rather than the full SSE event list (which can be MB-sized for detailed_analysis /
    # custom.html turns). Canvas apps are fetched separately by the client as needed.
    context = build_tutor_context(request, headers)
    orchestrator = UnifiedOrchestrator()
    events = await orchestrator.run_turn(context)
    assistant_text = "".join(event.get("text", "") for event in events if event.get("type") == "assistant.delta")
    run_id = next((str(event.get("run_id") or "") for event in events if event.get("type") == "run.started"), "")
    message_id = next((str(event.get("message_id") or "") for event in events if event.get("type") == "assistant.delta"), "")
    if not assistant_text.strip():
        assistant_text = f"这次没有收到 Hermes 的有效输出，任务已结束但未生成可交付内容（运行 ID: {run_id or 'unknown'}）。"
    return {"assistant_text": assistant_text, "run_id": run_id, "message_id": message_id}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> StreamingResponse:
    context = build_tutor_context(request, headers)
    orchestrator = UnifiedOrchestrator()

    async def generate() -> AsyncIterator[str]:
        plan = orchestrator.plan_turn(context)
        run_id: str | None = None
        message_id = f"assistant-error-{context.conversation_id or 'stream'}"
        emitted_assistant_text = False
        try:
            async for event in orchestrator.execute_plan(plan, context):
                if event.get("type") == "run.started":
                    run_id = str(event.get("run_id") or "")
                if event.get("type") == "assistant.delta":
                    message_id = str(event.get("message_id") or message_id)
                    emitted_assistant_text = emitted_assistant_text or bool(str(event.get("text") or "").strip())
                if event.get("type") == "assistant.done" and not emitted_assistant_text:
                    yield orchestrator.sse_line({
                        "type": "assistant.delta",
                        "message_id": message_id,
                        "text": f"这次没有收到 Hermes 的有效输出，任务已结束但未生成可交付内容（运行 ID: {run_id or 'unknown'}）。",
                    })
                    emitted_assistant_text = True
                yield orchestrator.sse_line(event)
            if not emitted_assistant_text:
                yield orchestrator.sse_line({
                    "type": "assistant.delta",
                    "message_id": message_id,
                    "text": f"这次没有收到 Hermes 的有效输出，任务已结束但未生成可交付内容（运行 ID: {run_id or 'unknown'}）。",
                })
                yield orchestrator.sse_line({"type": "assistant.done", "message_id": message_id})
        except Exception as exc:
            # Log the full traceback server-side; never echo raw exception text to the
            # client (it may include filesystem paths, API key fragments, or SQL).
            LOGGER.exception("chat_stream execution failed (run_id=%s)", run_id)
            safe_detail = _sanitize_exception_for_client(exc)
            if run_id:
                yield orchestrator.sse_line({
                    "type": "run.step",
                    "run_id": run_id,
                    "step_name": "backend",
                    "status": "failed",
                    "detail": safe_detail,
                })
            yield orchestrator.sse_line({
                "type": "assistant.delta",
                "message_id": message_id,
                "text": f"后端执行出错，请稍后重试（运行 ID: {run_id or 'unknown'}）。",
            })
            if run_id:
                yield orchestrator.sse_line({"type": "run.done", "run_id": run_id, "status": "failed"})
            yield orchestrator.sse_line({"type": "assistant.done", "message_id": message_id})

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chat/runs/{run_id}/cancel")
async def cancel_chat_run(run_id: str) -> dict[str, Any]:
    active = HermesTaskExecutor.request_cancel(run_id)
    try:
        get_store().finish_run(
            run_id,
            {"status": "cancelled", "reason": "user_requested"},
            "cancelled",
        )
    except Exception:
        LOGGER.warning("failed to mark run cancelled (run_id=%s)", run_id, exc_info=True)
    return {"status": "cancelled", "run_id": run_id, "active_process_terminated": active}


@app.get("/api/learning-focus")
async def get_learning_focus(headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(headers=headers)
    focus = get_store().get_learning_focus(session.student_id, session.course_id)
    return {
        "topic": focus.get("topic", ""),
        "objective": focus.get("objective", ""),
        "course_label": focus.get("course_label", ""),
    }


@app.post("/api/courses")
async def create_course(request: CourseRequest) -> dict[str, Any]:
    return {"course_id": "ai-course", "title": request.title, "description": request.description, "status": "ready"}


@app.post("/api/courses/{course_id}/documents")
async def add_course_document(course_id: str, request: CourseDocumentRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(explicit_course_id=course_id, headers=headers)
    parsed = CourseParser().parse_markdown(request.content)
    text = str(parsed.get("text") or request.content).strip()
    if not text:
        raise HTTPException(status_code=400, detail="document content is empty")
    chunks = TextChunker().chunk(text, size=900) or [text]
    store = get_store()
    saved = store.save_course_document_from_chunks(
        course_id=session.course_id,
        title=request.title,
        chunks=chunks,
        file_url=request.file_url,
        parser="api_markdown" if "#" in request.content else "api_text",
    )
    source_refs = [chunk["source_ref"] for chunk in saved["chunks"][:8]]
    resource = LearningResource(
        resource_id=f"res-{saved['document_id']}",
        type="document",
        title=request.title,
        target_topic=request.title,
        difficulty="adaptive",
        content={
            "module_name": "用户导入资料",
            "summary": f"已导入 {saved['chunk_count']} 个 RAG chunk，可用于问答、引用和学习资源生成。",
            "sections": parsed.get("sections", []),
            "chunk_count": saved["chunk_count"],
            "document_id": saved["document_id"],
            "tags": ["#用户资料", "#RAG", "#引用"],
        },
        source_refs=source_refs,
        personalized_reason="这份资料已进入当前课程知识库，可作为 NotebookLM 式来源进行引用问答。",
        tags=["#用户资料", "#RAG", "#引用"],
    )
    store.save_resource(resource, student_id=session.student_id, course_id=session.course_id, created_by_skill="api_document_ingest")
    retrieved = CourseRetriever(store).retrieve(request.title or text[:40], limit=5, course_id=session.course_id)
    return {
        "course_id": session.course_id,
        "document_id": saved["document_id"],
        "title": request.title,
        "chunk_count": saved["chunk_count"],
        "chunks": saved["chunks"],
        "retrieved_chunks": retrieved,
        "source_refs": source_refs,
        "resource": resource.model_dump(),
    }


@app.post("/api/courses/{course_id}/ingest")
async def ingest_course(course_id: str) -> dict[str, Any]:
    output = SkillRegistry().get("course_ingestion_skill").run(SkillInput(course_id=course_id))
    return output.model_dump()


@app.get("/api/courses/{course_id}/knowledge-graph")
async def get_knowledge_graph(course_id: str) -> dict[str, Any]:
    return KnowledgeGraphBuilder().graph(course_id)


@app.post("/api/profile/extract")
async def extract_profile(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    context = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        headers=headers,
    )
    output = ProfileAgent().run(
        ProfileAgentInput(student_id=context.student_id, course_id=context.course_id, message=request.message)
    )
    return {"memories": output.payload["memories"], "profile": output.payload["profile"], "trace": output.trace}


@app.get("/api/profile/{student_id}")
async def get_profile(student_id: str, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=student_id,
        headers=headers,
    )
    return {
        "student_id": session.student_id,
        "profile": get_store().get_profile(session.student_id, course_id=session.course_id),
        "evidence": [
            item.model_dump()
            for item in get_store().list_memories(session.student_id, course_id=session.course_id, limit=12)
        ],
    }


@app.post("/api/learning-path/generate")
async def generate_learning_path(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    context = build_tutor_context(request, headers)
    orchestrator = UnifiedOrchestrator()
    events = await orchestrator.run_turn(
        TutorTurnContext(
            student_id=context.student_id,
            course_id=context.course_id,
            conversation_id=context.conversation_id,
            message=f"生成{request.message}学习路径",
            image_data=context.image_data,
            model_provider=context.model_provider,
            recent_messages=context.recent_messages,
            last_assistant_answer=context.last_assistant_answer,
            recent_apps=context.recent_apps,
            recent_resources=context.recent_resources,
        )
    )
    path_events = [event for event in events if event.get("type") == "path.update"]
    return {"path": path_events[-1]["path"] if path_events else get_store().get_path().model_dump(), "events": events}


@app.get("/api/learning-path/{path_id}")
async def get_learning_path(path_id: str) -> dict[str, Any]:
    path = get_store().get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="path not found")
    return path.model_dump()


@app.post("/api/resources/generate")
async def generate_resources(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    context = build_tutor_context(request, headers)
    output = SkillRegistry().get("resource_bundle_skill").run(
        SkillInput(student_id=context.student_id, course_id=context.course_id, topic=request.message or "梯度下降")
    )
    resources = output.payload["resources"]
    for resource in resources:
        get_store().save_resource(
            LearningResource.model_validate(resource),
            student_id=context.student_id,
            course_id=context.course_id,
            created_by_skill="resource_bundle_skill",
        )
    return {"resources": resources, "trace": output.trace}


@app.get("/api/resources")
async def list_resources(
    query: str | None = None,
    tag: str | None = None,
    resource_type: str | None = None,
    limit: int = 240,
    student_id: str | None = None,
    course_id: str | None = None,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=student_id,
        explicit_course_id=course_id,
        headers=headers,
    )
    safe_limit = max(1, min(500, limit))
    if resource_type == "video":
        resources = get_store().search_video_resources(query or "", limit=safe_limit)
    else:
        resources = get_store().list_resources(
            session.student_id,
            course_id=session.course_id,
            query=query or None,
            tag=tag or None,
            resource_type=resource_type or None,
            limit=safe_limit,
        )
    return {
        "resources": [resource.model_dump() for resource in resources],
        "count": len(resources),
        "course_id": session.course_id,
    }


@app.get("/api/resources/{resource_id}")
async def get_resource(resource_id: str) -> dict[str, Any]:
    resource = get_store().get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource.model_dump()


@app.post("/api/quiz/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, request: QuizSubmitRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        explicit_conversation_id=request.conversation_id,
        headers=headers,
    )
    output = EvaluatorAgent().run(
        EvaluatorAgentInput(
            student_id=session.student_id,
            course_id=session.course_id,
            question_id=quiz_id,
            answer=request.answer,
        )
    )
    dashboard = get_store().dashboard(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id)
    return {"evaluation": output.model_dump(), "dashboard": dashboard.model_dump()}


@app.get("/api/canvas/apps")
async def list_canvas_apps(student_id: str | None = None, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(explicit_student_id=student_id, headers=headers)
    store = get_store()
    if hasattr(store, "ensure_default_apps"):
        store.ensure_default_apps(session.student_id, session.course_id)
    return {"apps": [app_item.model_dump() for app_item in store.list_apps(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id)]}


@app.post("/api/canvas/apps")
async def create_canvas_app(request: CanvasAppCreateRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        explicit_conversation_id=request.conversation_id,
        headers=headers,
    )
    request_payload = CanvasAppCreateRequest(**request.model_dump())
    request_payload.student_id = session.student_id
    request_payload.course_id = session.course_id
    # Normalize client-supplied app_type onto the CanvasAppType Literal so an unknown
    # value (e.g. "infographic"/"presentation") yields a graceful 422-ish fallback
    # instead of a 500 from a downstream Pydantic ValidationError.
    request_payload.app_type = CanvasMaterializer.normalize_app_type(request_payload.app_type)
    output = AppCanvasAgent().run(
        student_id=session.student_id,
        app_type=request_payload.app_type,
        title=request_payload.title,
        course_id=session.course_id,
        conversation_id=session.conversation_id,
        payload=request_payload.payload,
        source_refs=request_payload.source_refs,
    )
    return output.model_dump()


@app.patch("/api/canvas/apps/{app_id}")
async def patch_canvas_app(
    app_id: str,
    patch: CanvasAppPatchRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    # Identity comes ONLY from the authenticated session / headers, never from the
    # request body. The old `dict[str, Any]` let a caller spoof student_id/course_id
    # and patch other students' apps. With a token present the session is auth-backed;
    # without one we still fall back to X-Student-Id / demo defaults for legacy/demo use.
    session = resolve_session_from_request(None, None, headers=headers)
    app_item = get_store().update_app(app_id, patch.to_patch(), student_id=session.student_id, course_id=session.course_id)
    if not app_item:
        raise HTTPException(status_code=404, detail="app not found")
    return app_item.model_dump()


@app.post("/api/canvas/apps/{app_id}/events")
async def canvas_app_event(
    app_id: str,
    request_body: CanvasAppEventRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session_from_request(None, None, explicit_conversation_id=request_body.conversation_id, headers=headers)
    app_item = get_store().get_app(app_id, student_id=session.student_id, course_id=session.course_id)
    if not app_item:
        raise HTTPException(status_code=404, detail="app not found for current session")
    event_type = request_body.event_type
    event_payload = request_body.payload
    updated_app = None
    action_status = "recorded"
    action_reason = None
    if event_type == "image.generate":
        topic = str(event_payload.get("topic") or app_item.payload.get("topic") or app_item.title)
        teaching_goal = str(event_payload.get("teaching_goal") or app_item.payload.get("teaching_goal") or f"生成 {topic} 教学图")
        router = ImageGatewayRouter()
        image_request = router.planner.plan(topic, teaching_goal)
        try:
            result = await router.client.generate(image_request)
            updated_app = get_store().update_app(
                app_id,
                {
                    "status": "ready",
                    "payload": {
                        "topic": topic,
                        "teaching_goal": teaching_goal,
                        "image_url": result.image_url,
                        "overlay_labels": result.overlay_labels,
                        "provider": result.provider,
                        "provider_alias": event_payload.get("provider_alias") or app_item.payload.get("provider_alias") or result.provider,
                        "image_metadata": result.metadata,
                        "image_error": None,
                    },
                },
                student_id=session.student_id,
                course_id=session.course_id,
            )
            action_status = "completed"
        except (ProviderBlocked, ModelGatewayError) as exc:
            action_reason = exc.reason if isinstance(exc, ProviderBlocked) else str(exc)
            updated_app = get_store().update_app(
                app_id,
                {"status": "error", "payload": {"image_error": action_reason, "image_request": image_request.model_dump()}},
                student_id=session.student_id,
                course_id=session.course_id,
            )
            action_status = "failed"
    elif event_type == "notes.save":
        event_payload = {
            **event_payload,
            "topic": event_payload.get("topic") or app_item.payload.get("topic") or app_item.title,
            "title": app_item.title,
            "resource_id": app_item.payload.get("resource_id"),
        }
        updated_app = get_store().update_app(
            app_id,
            {"payload": {"content": event_payload.get("content", app_item.payload.get("content", ""))}},
            student_id=session.student_id,
            course_id=session.course_id,
        )
        action_status = "completed"
    elif event_type == "resource.filter":
        query = str(event_payload.get("query") or "").strip()
        resources = app_item.payload.get("resources") if isinstance(app_item.payload.get("resources"), list) else []
        filtered = [
            item for item in resources
            if not query or query.lower() in json.dumps(item, ensure_ascii=False).lower()
        ]
        updated_app = get_store().update_app(
            app_id,
            {"payload": {"active_filter": query, "filtered_resources": filtered}},
            student_id=session.student_id,
            course_id=session.course_id,
        )
        action_status = "completed"
    elif event_type in {"mindmap.expand", "ppt.preview", "video_script.view", "custom.preview", "knowledge.prerequisites", "profile.refresh", "path.focus_current", "dashboard.refresh", "demo.play"}:
        updated_app = get_store().update_app(
            app_id,
            {"payload": {"last_action": event_type, "action_status": "ready"}},
            student_id=session.student_id,
            course_id=session.course_id,
        )
        action_status = "completed"
    event = AppEvent(
        app_id=app_id,
        student_id=session.student_id,
        course_id=session.course_id,
        conversation_id=session.conversation_id,
        event_type=event_type,
        payload={**event_payload, "action_status": action_status, "reason": action_reason},
    )
    get_store().record_app_event(event)
    memory = EduMem0Client().record_app_event(event)
    return {
        "event": event.model_dump(),
        "memory": memory.model_dump(),
        "app": updated_app.model_dump() if updated_app else None,
        "action_status": action_status,
        "reason": action_reason,
        "dashboard": get_store().dashboard(event.student_id, course_id=session.course_id, conversation_id=session.conversation_id).model_dump(),
    }


@app.post("/api/canvas/applink/{link_id}/open")
async def open_applink(
    link_id: str, headers: SessionHeaders = Depends(get_session_headers)
) -> dict[str, Any]:
    session = resolve_session_from_request(None, None, headers=headers)
    store = get_store()
    # Ownership check: the link's target app must belong to the current student.
    # Without this, knowing a link_id was enough to focus anyone's app (IDOR).
    link = store.get_chat_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="link not found")
    if not store.get_app(link.app_id, student_id=session.student_id, course_id=session.course_id):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN_APP_LINK", "message": "link does not belong to current student"})
    output = AppCanvasAgent().focus_link(link_id, student_id=session.student_id, course_id=session.course_id)
    return output.model_dump()


@app.get("/api/dashboard/{student_id}")
async def dashboard(student_id: str, headers: SessionHeaders = Depends(get_session_headers)) -> DashboardSnapshot:
    session = resolve_session(explicit_student_id=student_id, headers=headers)
    return get_store().dashboard(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id)


@app.get("/api/dashboard/{student_id}/memory-evidence")
async def dashboard_memory_evidence(student_id: str, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(explicit_student_id=student_id, headers=headers)
    return {
        "evidence": [
            item.model_dump()
            for item in get_store().list_memories(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id, limit=30)
        ]
    }


@app.get("/api/agent-runs/{run_id}")
async def agent_run(run_id: str) -> dict[str, Any]:
    run = get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/api/memory/{student_id}")
async def memory_for_student(student_id: str, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(explicit_student_id=student_id, headers=headers)
    return {
        "memories": [
            item.model_dump()
            for item in get_store().list_memories(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id, limit=50)
        ]
    }


@app.post("/api/memory/search")
async def memory_search(request: MemorySearchRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        headers=headers,
    )
    memories = EduMem0Client().search(
        session.student_id,
        query=request.query,
        memory_types=request.memory_types,
        course_id=session.course_id,
        knowledge_point_id=request.knowledge_point_id,
        limit=request.limit,
    )
    return {"memories": [item.model_dump() for item in memories]}


@app.post("/api/memory/extract-from-chat")
async def memory_extract_from_chat(request: ChatRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        headers=headers,
    )
    memories = await asyncio.to_thread(EduMem0Client().extract_from_chat, session.student_id, request.message, session.course_id)
    return {"memories": [item.model_dump() for item in memories]}


@app.post("/api/memory/app-event")
async def memory_app_event(payload: dict[str, Any], headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=payload.get("student_id"),
        explicit_course_id=payload.get("course_id"),
        explicit_conversation_id=payload.get("conversation_id"),
        headers=headers,
    )
    payload = dict(payload)
    payload["student_id"] = session.student_id
    payload["course_id"] = session.course_id
    payload.setdefault("conversation_id", session.conversation_id)
    event = AppEvent.model_validate(payload)
    memory = EduMem0Client().record_app_event(event)
    return {
        "memory": memory.model_dump(),
        "dashboard": get_store().dashboard(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id).model_dump(),
    }


@app.post("/api/memory/quiz-result")
async def memory_quiz_result(payload: dict[str, Any], headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=payload.get("student_id"),
        explicit_course_id=payload.get("course_id"),
        headers=headers,
    )
    question_id = payload.get("question_id", "quiz-q-gradient-lr")
    answer = payload.get("answer", "")
    output = EvaluatorAgent().run(
        EvaluatorAgentInput(
            student_id=session.student_id,
            course_id=session.course_id,
            question_id=question_id,
            answer=answer,
        )
    )
    return output.model_dump()


@app.post("/api/memory/layout-event")
async def memory_layout_event(payload: dict[str, Any], headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=payload.get("student_id"),
        explicit_course_id=payload.get("course_id"),
        explicit_conversation_id=payload.get("conversation_id"),
        headers=headers,
    )
    event = AppEvent(
        app_id=payload.get("app_id", "app-gradient"),
        student_id=session.student_id,
        course_id=session.course_id,
        event_type="layout.save",
        conversation_id=session.conversation_id,
        payload=payload,
    )
    memory = EduMem0Client().record_app_event(event)
    return {
        "memory": memory.model_dump(),
        "dashboard": get_store().dashboard(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id).model_dump(),
    }


@app.post("/api/memory/resource-feedback")
async def memory_resource_feedback(
    request: ResourceFeedbackRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        headers=headers,
    )
    payload = request.model_dump()
    payload["student_id"] = session.student_id
    payload["course_id"] = session.course_id
    feedback_id = get_store().save_feedback(session.student_id, payload)
    memory = preference_memory(session.student_id, request.preference, request.sentiment, course_id=session.course_id)
    memory.source_event_id = feedback_id
    memory.course_id = session.course_id
    memory.structured_payload = {
        **memory.structured_payload,
        "resource_id": request.resource_id,
        "app_id": request.app_id,
        "rating": request.rating,
        "comment": request.comment,
    }
    saved = EduMem0Client().add(memory)
    return {
        "feedback_id": feedback_id,
        "memory": saved.model_dump(),
        "dashboard": get_store().dashboard(session.student_id, course_id=session.course_id, conversation_id=session.conversation_id).model_dump(),
    }


@app.post("/api/images/generate")
async def generate_image(request: ImageGenerateRequest, headers: SessionHeaders = Depends(get_session_headers)) -> dict[str, Any]:
    session = resolve_session(
        explicit_student_id=request.student_id,
        explicit_course_id=request.course_id,
        explicit_conversation_id=request.conversation_id,
        headers=headers,
    )
    skill_output = ImageGenerationSkill().run(SkillInput(topic=request.topic, payload={"teaching_goal": request.teaching_goal}))
    planned = skill_output.resource
    router = ImageGatewayRouter()
    image_request = router.planner.plan(request.topic, request.teaching_goal)
    try:
        result = await router.client.generate(image_request)
        app_item = None
        if request.app_id:
            app_item = get_store().update_app(
                request.app_id,
                {
                    "status": "ready",
                    "payload": {
                        "topic": request.topic,
                        "teaching_goal": request.teaching_goal,
                        "image_url": result.image_url,
                        "overlay_labels": result.overlay_labels,
                        "provider": result.provider,
                        "provider_alias": request.provider_alias or result.provider,
                        "image_metadata": result.metadata,
                        "image_error": None,
                    },
                },
                student_id=session.student_id,
                course_id=session.course_id,
            )
        return {"status": "ready", "resource": planned.model_dump() if planned else None, "image": result.model_dump(), "app": app_item.model_dump() if app_item else None}
    except ProviderBlocked as exc:
        return {"status": exc.code, "reason": exc.reason, "resource": planned.model_dump() if planned else None, "image_request": image_request.model_dump(), "app": None}
    except ModelGatewayError as exc:
        return {"status": "blocked_provider_error", "reason": str(exc), "resource": planned.model_dump() if planned else None, "image_request": image_request.model_dump(), "app": None}


@app.get("/api/protocol/fixtures")
async def protocol_fixtures() -> dict[str, Any]:
    app_item = get_store().get_app("app-gradient")
    dashboard_item = get_store().dashboard("demo-student")
    return {
        "canvas_app": app_item.model_dump() if app_item else None,
        "dashboard": dashboard_item.model_dump(),
        "event_variants": [
            "assistant.delta",
            "assistant.done",
            "run.started",
            "run.step",
            "run.done",
            "app.create",
            "app.update",
            "app.focus",
            "app.link.create",
            "app.event.received",
            "resource.create",
            "resource.update",
            "memory.update",
            "path.update",
            "dashboard.update",
            "verifier.result",
            "error",
        ],
    }
