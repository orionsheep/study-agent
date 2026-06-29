from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.cram.openstax_seed import OPENSTAX_CRAM_BOOKS, OpenStaxCramBook
from app.schemas.app_protocol import new_id, utc_now


CramPriority = Literal["must_know", "key_point"]
CramHook = Literal["acronym", "contrast", "absurd", "none"]
ExamMode = Literal["conceptual_cram", "practice_heavy"]
RootCause = Literal["concept_confusion", "logic_bias", "memory_gap", "transfer_failure"]


class CramStage(StrEnum):
    DECONSTRUCT = "deconstruct"
    TEACH = "teach"
    TEST = "test"
    REMEDIATE = "remediate"
    SUMMARY = "summary"


class CramKnowledgePoint(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cramkp"))
    title: str
    parent_topic: str
    priority: CramPriority
    hook: CramHook = "none"
    order: int
    status: Literal["pending", "taught", "tested", "corrected", "stubborn"] = "pending"
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class CramProgress(BaseModel):
    total_points: int = 0
    taught_points: int = 0
    generated_questions: int = 0
    wrong_points: int = 0
    stubborn_points: int = 0
    must_know_total: int = 0
    key_point_total: int = 0


class CramRemediationItem(BaseModel):
    knowledge_point_id: str
    title: str
    root_cause: RootCause
    strategy: str
    status: Literal["pending", "corrected", "stubborn"] = "pending"
    attempts: int = 1


class CramSessionCreate(BaseModel):
    student_id: str
    course_id: str
    course_title: str
    exam_types: list[str] = Field(default_factory=list)
    must_know: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    textbook: str | None = None
    materials: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)


class CramSession(BaseModel):
    session_id: str = Field(default_factory=lambda: new_id("cram"))
    student_id: str
    course_id: str
    course_title: str
    stage: CramStage = CramStage.DECONSTRUCT
    status: Literal["active", "completed", "paused"] = "active"
    exam_mode: ExamMode = "conceptual_cram"
    exam_types: list[str] = Field(default_factory=list)
    textbook: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    knowledge_points: list[CramKnowledgePoint] = Field(default_factory=list)
    progress: CramProgress = Field(default_factory=CramProgress)
    remediation_items: list[CramRemediationItem] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


CONCEPTUAL_EXAM_MARKERS = {"名词", "解释", "简答", "论述", "辨析", "案例", "情景", "选择", "判断", "填空", "应用"}
PRACTICE_EXAM_MARKERS = {"计算", "推导", "证明", "编程", "作图", "画图", "实验设计", "建模"}


def classify_exam_mode(exam_types: list[str]) -> ExamMode:
    joined = " ".join(exam_types or [])
    conceptual_hits = sum(1 for marker in CONCEPTUAL_EXAM_MARKERS if marker in joined)
    practice_hits = sum(1 for marker in PRACTICE_EXAM_MARKERS if marker in joined)
    if practice_hits and practice_hits >= conceptual_hits:
        return "practice_heavy"
    return "conceptual_cram"


def _hook_for(text: str, sibling_topics: list[str]) -> CramHook:
    value = text.lower()
    if any(marker in value for marker in ["公式", "步骤", "变量", "分类", "三", "四", "法则"]):
        return "acronym"
    if any(marker in value for marker in ["区别", "对比", "vs", "比较", "公平", "期望"]) or len(sibling_topics) > 1:
        return "contrast"
    if any(marker in value for marker in ["抽象", "局限", "原则", "伦理", "哲学"]):
        return "absurd"
    return "none"


def _source_refs_for_textbook(textbook: str | None) -> list[dict[str, Any]]:
    if not textbook:
        return []
    needle = textbook.lower()
    for book in OPENSTAX_CRAM_BOOKS:
        if needle in book.title.lower() or book.title.lower() in needle:
            return [
                {
                    "source_id": f"openstax:{book.slug}",
                    "title": book.title,
                    "provider": book.provider,
                    "url": book.web_url,
                    "details_url": book.details_url,
                    "license": book.license,
                }
            ]
    return [{"source_id": f"textbook:{textbook}", "title": textbook, "provider": "user_supplied"}]


def _deconstruct_topic(topic: str, priority: CramPriority, order_start: int, source_refs: list[dict[str, Any]], sibling_topics: list[str]) -> list[CramKnowledgePoint]:
    clean = topic.strip()
    if not clean:
        return []
    templates = [
        f"{clean}的核心概念",
        f"{clean}的关键变量与判断标准",
        f"{clean}的应用场景与常见误区",
    ]
    if priority == "must_know":
        templates.append(f"{clean}的答题框架与局限")
    points: list[CramKnowledgePoint] = []
    for index, title in enumerate(templates):
        points.append(
            CramKnowledgePoint(
                title=title,
                parent_topic=clean,
                priority=priority,
                hook=_hook_for(title, sibling_topics),
                order=order_start + index,
                source_refs=source_refs,
            )
        )
    return points


def create_cram_session(data: CramSessionCreate) -> CramSession:
    source_refs = _source_refs_for_textbook(data.textbook)
    all_topics = [*data.must_know, *data.key_points]
    points: list[CramKnowledgePoint] = []
    order = 1
    for topic in data.must_know:
        new_points = _deconstruct_topic(topic, "must_know", order, source_refs, all_topics)
        points.extend(new_points)
        order += len(new_points)
    for topic in data.key_points:
        new_points = _deconstruct_topic(topic, "key_point", order, source_refs, all_topics)
        points.extend(new_points)
        order += len(new_points)
    progress = CramProgress(
        total_points=len(points),
        must_know_total=sum(1 for point in points if point.priority == "must_know"),
        key_point_total=sum(1 for point in points if point.priority == "key_point"),
    )
    next_action = "确认知识点树后进入讲授阶段" if points else "补充课程重点后重新拆解"
    return CramSession(
        student_id=data.student_id,
        course_id=data.course_id,
        course_title=data.course_title,
        exam_types=data.exam_types,
        textbook=data.textbook,
        exam_mode=classify_exam_mode(data.exam_types),
        preferences=data.preferences,
        knowledge_points=points,
        progress=progress,
        source_refs=source_refs,
        next_actions=[next_action],
    )


def _question_count(session: CramSession) -> int:
    exam_type_count = max(1, len(session.exam_types))
    must = session.progress.must_know_total * exam_type_count
    key = max(1, session.progress.key_point_total)
    return must + key


def _root_cause_for(answer: str, point: CramKnowledgePoint) -> RootCause:
    text = f"{answer} {point.title}"
    if any(marker in text for marker in ["混", "区别", "公平", "期望", "相似"]):
        return "concept_confusion"
    if any(marker in text for marker in ["反", "不是", "越", "工资", "高"]):
        return "logic_bias"
    if any(marker in text for marker in ["忘", "术语", "关键词", "记不住"]):
        return "memory_gap"
    return "transfer_failure"


def _strategy_for(root_cause: RootCause) -> str:
    return {
        "concept_confusion": "对比表纠偏，并要求学生复述关键差异",
        "logic_bias": "用极端反例打破错误逻辑，再重测",
        "memory_gap": "更换记忆钩子，提取关键词和口诀",
        "transfer_failure": "换一个新场景做迁移练习",
    }[root_cause]


def advance_cram_session(session: CramSession, *, action: str, payload: dict[str, Any] | None = None) -> CramSession:
    payload = payload or {}
    updated = session.model_copy(deep=True)
    if updated.stage == CramStage.DECONSTRUCT and action == "confirm_deconstruction":
        updated.stage = CramStage.TEACH
        batch = updated.knowledge_points[:3]
        for point in batch:
            point.status = "taught"
        updated.progress.taught_points = len(batch)
        updated.next_actions = ["继续讲授下一批知识点" if updated.progress.taught_points < updated.progress.total_points else "进入检题阶段"]
    elif updated.stage == CramStage.TEACH and action == "teach_next_batch":
        pending = [point for point in updated.knowledge_points if point.status == "pending"]
        for point in pending[:3]:
            point.status = "taught"
        updated.progress.taught_points = sum(1 for point in updated.knowledge_points if point.status in {"taught", "tested", "corrected", "stubborn"})
        if updated.progress.taught_points >= updated.progress.total_points:
            updated.stage = CramStage.TEST
            updated.progress.generated_questions = _question_count(updated)
            updated.next_actions = ["提交检题结果，系统会自动进入补漏或总结"]
        else:
            updated.next_actions = ["继续讲授下一批知识点"]
    elif updated.stage == CramStage.TEST and action == "submit_test_results":
        wrongs = [item for item in payload.get("results", []) if not bool(item.get("is_correct"))]
        updated.progress.wrong_points = len(wrongs)
        if not wrongs:
            updated.stage = CramStage.SUMMARY
            updated.status = "completed"
            updated.next_actions = ["考前复盘 must_know 清单和易混点"]
        else:
            updated.stage = CramStage.REMEDIATE
            point_by_id = {point.id: point for point in updated.knowledge_points}
            updated.remediation_items = []
            for item in wrongs:
                point = point_by_id.get(str(item.get("knowledge_point_id")))
                if not point:
                    continue
                point.status = "tested"
                root = _root_cause_for(str(item.get("user_answer") or ""), point)
                updated.remediation_items.append(
                    CramRemediationItem(
                        knowledge_point_id=point.id,
                        title=point.title,
                        root_cause=root,
                        strategy=_strategy_for(root),
                    )
                )
            updated.next_actions = ["逐个处理错因：诊断、换讲法、重测"]
    elif updated.stage == CramStage.REMEDIATE and action == "submit_remediation_results":
        results = payload.get("results", [])
        result_by_point = {str(item.get("knowledge_point_id")): bool(item.get("is_correct")) for item in results}
        point_by_id = {point.id: point for point in updated.knowledge_points}
        for item in updated.remediation_items:
            passed = result_by_point.get(item.knowledge_point_id, False)
            item.status = "corrected" if passed else "stubborn"
            item.attempts += 1
            point = point_by_id.get(item.knowledge_point_id)
            if point:
                point.status = "corrected" if passed else "stubborn"
        updated.progress.stubborn_points = sum(1 for item in updated.remediation_items if item.status == "stubborn")
        updated.stage = CramStage.SUMMARY
        updated.status = "completed"
        if updated.progress.stubborn_points:
            updated.next_actions = ["明天优先复习顽固点，利用间隔效应再测"]
        else:
            updated.next_actions = ["考前复盘 must_know 清单和标准答题框架"]
    updated.updated_at = utc_now()
    return updated


def _book_payload(book: OpenStaxCramBook) -> dict[str, Any]:
    return {
        "slug": book.slug,
        "title": book.title,
        "subject": book.subject,
        "exam_mode": book.exam_mode,
        "details_url": book.details_url,
        "web_url": book.web_url,
    }


def build_cram_dashboard_summary(sessions: list[CramSession], books: list[OpenStaxCramBook] | None = None) -> dict[str, Any]:
    books = books or OPENSTAX_CRAM_BOOKS
    active = next((session for session in sessions if session.status == "active"), sessions[0] if sessions else None)
    active_payload = None
    if active:
        active_payload = {
            "session_id": active.session_id,
            "course_title": active.course_title,
            "stage": active.stage.value,
            "exam_mode": active.exam_mode,
            "progress": active.progress.model_dump(),
            "next_actions": active.next_actions,
        }
    all_remediations = [item for session in sessions for item in session.remediation_items]
    root_dist: dict[str, int] = {}
    for item in all_remediations:
        root_dist[item.root_cause] = root_dist.get(item.root_cause, 0) + 1
    stubborn = [
        {"knowledge_point_id": item.knowledge_point_id, "title": item.title, "root_cause": item.root_cause, "strategy": item.strategy}
        for item in all_remediations
        if item.status == "stubborn"
    ]
    must_total = sum(session.progress.must_know_total for session in sessions)
    taught_must = sum(
        1
        for session in sessions
        for point in session.knowledge_points
        if point.priority == "must_know" and point.status in {"taught", "tested", "corrected", "stubborn"}
    )
    recommended = [book for book in books if book.exam_mode == (active.exam_mode if active else "conceptual_cram")][:5]
    return {
        "active_session": active_payload,
        "kpis": {
            "openstax_books": len(books),
            "active_sessions": sum(1 for session in sessions if session.status == "active"),
            "must_know_coverage": round(taught_must / must_total, 3) if must_total else 0,
            "stubborn_points": len(stubborn),
        },
        "recommended_books": [_book_payload(book) for book in recommended],
        "stubborn_points": stubborn,
        "root_cause_distribution": root_dist,
    }
