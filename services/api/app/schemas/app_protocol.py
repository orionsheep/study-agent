from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field


CanvasAppState = Literal["icon", "card", "window", "fullscreen", "split_left", "split_right", "minimized", "focused"]
CanvasAppType = Literal[
    "profile.dashboard",
    "learning.path",
    "knowledge.graph",
    "mindmap.concept",
    "quiz.practice",
    "physics.work_energy_demo",
    "math.gradient_descent_demo",
    "code.lab",
    "notes.session",
    "dashboard.learning",
    "ppt.preview",
    "image.explanation",
    "video.script",
    "video.player",
    "resource.center",
    "resource.folder",
    "custom.html",
    "english.workspace",
    "humanities.notebook",
]
RenderMode = Literal["native_react", "sandbox_iframe", "svg", "react_flow", "pptx_preview"]
ResourceType = Literal[
    "document",
    "mindmap",
    "quiz",
    "ppt",
    "code_practice",
    "image",
    "video_script",
    "reading",
    "notes",
    "dashboard",
    "app_bundle",
    "video",
]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class CanvasViewport(BaseModel):
    x: float = 0
    y: float = 0
    scale: float = 1


class CanvasPosition(BaseModel):
    x: float
    y: float


class CanvasSize(BaseModel):
    width: float
    height: float


class CanvasFrame(BaseModel):
    frame_id: str
    title: str
    app_ids: list[str] = Field(default_factory=list)
    position: CanvasPosition
    size: CanvasSize


class CanvasConnector(BaseModel):
    connector_id: str
    source_app_id: str
    target_app_id: str
    label: str
    relation: str


class CanvasApp(BaseModel):
    app_id: str = Field(default_factory=lambda: new_id("app"))
    app_type: CanvasAppType
    title: str
    icon: str | None = None
    status: Literal["creating", "ready", "error", "blocked"] = "ready"
    render_mode: RenderMode = "native_react"
    state: CanvasAppState = "window"
    position: CanvasPosition
    size: CanvasSize
    z_index: int = 1
    group_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    personalized_reason: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ChatAppLink(BaseModel):
    link_id: str = Field(default_factory=lambda: new_id("link"))
    message_id: str
    app_id: str
    label: str
    action: Literal["focus", "open", "split", "fullscreen", "explain", "generate_related"] = "focus"
    anchor_text: str | None = None
    created_at: str = Field(default_factory=utc_now)
    source_run_id: str | None = None


class AppEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    app_id: str
    student_id: str
    course_id: str | None = None
    event_type: str
    conversation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class VerifierResult(BaseModel):
    passed: bool
    score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    source_coverage: float = Field(ge=0, le=1, default=0)
    profile_fit: float = Field(ge=0, le=1, default=0)
    safety: Literal["pass", "warn", "fail"] = "pass"


class LearningResource(BaseModel):
    resource_id: str = Field(default_factory=lambda: new_id("res"))
    type: ResourceType
    title: str
    target_topic: str
    difficulty: str = "adaptive"
    content: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    personalized_reason: str = ""
    estimated_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    quality_check: VerifierResult | None = None


class EduMemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem"))
    student_id: str
    course_id: str | None = None
    knowledge_point_id: str | None = None
    memory_type: str
    content: str
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1, default=0.5)
    importance: float = Field(ge=0, le=1, default=0.5)
    decay_rate: float = Field(ge=0, default=0.0)
    evidence_type: str
    effective_confidence: float | None = None
    decayed: bool = False
    source_event_id: str | None = None
    source_agent: str | None = None
    valid_from: str = Field(default_factory=utc_now)
    valid_until: str | None = None
    embedding: list[float] | None = None
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class StudentProfile(BaseModel):
    student_id: str
    display_name: str = "演示学习者"
    dimensions: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EduMemoryItem] = Field(default_factory=list)


class LearningPathStage(BaseModel):
    stage_id: str = Field(default_factory=lambda: new_id("stage"))
    title: str
    status: Literal["locked", "recommended", "in_progress", "completed", "needs_review"] = "recommended"
    mastery_required: float = 0.0
    current_mastery: float = 0.0
    recommended_resource_ids: list[str] = Field(default_factory=list)
    app_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class LearningPath(BaseModel):
    path_id: str = Field(default_factory=lambda: new_id("path"))
    title: str
    current_stage_id: str | None = None
    overall_progress: float = 0
    stages: list[LearningPathStage] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class AgentStep(BaseModel):
    step_id: str = Field(default_factory=lambda: new_id("step"))
    run_id: str
    step_order: int
    agent_or_skill: str
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    latency_ms: int = 0
    error_message: str | None = None
    created_at: str = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    student_id: str | None = None
    task_type: str
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    model_name: str | None = None
    latency_ms: int = 0
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    steps: list[AgentStep] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: new_id("q"))
    question_type: str = "single_choice"
    prompt: str
    options: list[str] = Field(default_factory=list)
    answer: Any
    explanation: str
    knowledge_point_id: str | None = None
    difficulty: str = "adaptive"
    misconception_tags: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class QuizSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: new_id("sub"))
    student_id: str
    question_id: str
    answer: Any
    is_correct: bool
    evaluation: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class DashboardSnapshot(BaseModel):
    student_id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    mastery: dict[str, float] = Field(default_factory=dict)
    weak_points: list[str] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    memory_evidence: list[EduMemoryItem] = Field(default_factory=list)
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    path_progress: float = 0
    canvas_activity: list[dict[str, Any]] = Field(default_factory=list)


class AssistantDelta(BaseModel):
    type: Literal["assistant.delta"] = "assistant.delta"
    message_id: str
    text: str


class AssistantDone(BaseModel):
    type: Literal["assistant.done"] = "assistant.done"
    message_id: str


class RunStarted(BaseModel):
    type: Literal["run.started"] = "run.started"
    run_id: str
    task_type: str


class RunStepEvent(BaseModel):
    type: Literal["run.step"] = "run.step"
    run_id: str
    step_name: str
    status: str
    detail: str | None = None


class RunDone(BaseModel):
    type: Literal["run.done"] = "run.done"
    run_id: str
    status: str


class AppCreateEvent(BaseModel):
    type: Literal["app.create"] = "app.create"
    app: CanvasApp
    link: ChatAppLink | None = None


class AppUpdateEvent(BaseModel):
    type: Literal["app.update"] = "app.update"
    app_id: str
    patch: dict[str, Any]


class AppFocusEvent(BaseModel):
    type: Literal["app.focus"] = "app.focus"
    app_id: str
    intent: str | None = None


class AppLinkCreateEvent(BaseModel):
    type: Literal["app.link.create"] = "app.link.create"
    link: ChatAppLink


class AppEventReceived(BaseModel):
    type: Literal["app.event.received"] = "app.event.received"
    event: AppEvent


class ResourceCreateEvent(BaseModel):
    type: Literal["resource.create"] = "resource.create"
    resource: LearningResource
    message_id: str | None = None


class ResourceUpdateEvent(BaseModel):
    type: Literal["resource.update"] = "resource.update"
    resource_id: str
    patch: dict[str, Any]


class MemoryUpdateEvent(BaseModel):
    type: Literal["memory.update"] = "memory.update"
    memory: EduMemoryItem
    summary: str


class PathUpdateEvent(BaseModel):
    type: Literal["path.update"] = "path.update"
    path: LearningPath


class DashboardUpdateEvent(BaseModel):
    type: Literal["dashboard.update"] = "dashboard.update"
    dashboard: DashboardSnapshot


class VerifierResultEvent(BaseModel):
    type: Literal["verifier.result"] = "verifier.result"
    resource_id: str
    result: VerifierResult


class ContextUpdateEvent(BaseModel):
    type: Literal["context.update"] = "context.update"
    topic: str
    capability: str
    course_label: str | None = None
    learning_objective: str | None = None


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str | None = None


AgentStreamEvent = Union[
    AssistantDelta,
    AssistantDone,
    RunStarted,
    RunStepEvent,
    RunDone,
    AppCreateEvent,
    AppUpdateEvent,
    AppFocusEvent,
    AppLinkCreateEvent,
    AppEventReceived,
    ResourceCreateEvent,
    ResourceUpdateEvent,
    MemoryUpdateEvent,
    PathUpdateEvent,
    DashboardUpdateEvent,
    ContextUpdateEvent,
    VerifierResultEvent,
    ErrorEvent,
]
