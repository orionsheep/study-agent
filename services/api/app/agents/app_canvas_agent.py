from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.base import AgentOutput
from app.canvas.component_namer import fallback_component_title
from app.database.store import get_store
from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import AppEvent, CanvasApp, CanvasPosition, CanvasSize


ICON_BY_APP_TYPE = {
    "resource.center": "BookOpen",
    "video.script": "Film",
    "video.player": "Film",
    "notes.session": "NotebookPen",
}

SIZE_BY_APP_TYPE = {
    "custom.html": (1060, 820),
    "resource.center": (520, 380),
    "video.script": (420, 310),
    "video.player": (720, 520),
    "notes.session": (430, 320),
}

ACTIONS_BY_APP_TYPE = {
    "custom.html": [{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "resource.center": [{"label": "筛选资源", "action": "resource.filter"}, {"label": "让导师推荐", "action": "tutor.explain"}],
    "video.script": [{"label": "查看分镜", "action": "video_script.view"}, {"label": "让导师解说", "action": "tutor.explain"}],
    "video.player": [{"label": "切换视频", "action": "video.select"}, {"label": "让导师总结视频", "action": "tutor.explain"}],
    "notes.session": [{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
}


class CanvasAppCreateInput(BaseModel):
    app_type: str
    title: str
    payload: dict = Field(default_factory=dict)
    source_refs: list[dict] = Field(default_factory=list)
    student_id: str = "demo-student"
    course_id: str = "ai-course"
    conversation_id: str | None = None


class AppCanvasAgent:
    name = "app_canvas_agent"

    def run(
        self,
        data: CanvasAppCreateInput | None = None,
        *,
        student_id: str | None = None,
        course_id: str | None = None,
        conversation_id: str | None = None,
        app_type: str | None = None,
        title: str | None = None,
        payload: dict | None = None,
        source_refs: list[dict] | None = None,
    ) -> AgentOutput:
        if data:
            student_id = student_id or data.student_id
            course_id = course_id or data.course_id
            conversation_id = conversation_id or data.conversation_id
            app_type = app_type or data.app_type
            title = title or data.title
            payload = payload or data.payload
            source_refs = source_refs or data.source_refs
        if not student_id or not app_type or not title:
            raise ValueError("student_id, app_type and title are required to create a canvas app")

        course_id = course_id or "ai-course"
        payload = payload or {}
        source_refs = source_refs or []
        title = fallback_component_title(title, component_type=app_type, topic=str(payload.get("topic") or ""), payload=payload)
        width, height = SIZE_BY_APP_TYPE.get(app_type, (420, 300))
        app = CanvasApp(
            app_type=app_type,
            title=title,
            icon=ICON_BY_APP_TYPE.get(app_type, "Sparkles"),
            position=CanvasPosition(x=260, y=220),
            size=CanvasSize(width=width, height=height),
            payload=payload,
            source={"student_id": student_id, "course_id": course_id, "conversation_id": conversation_id},
            source_refs=source_refs,
            actions=ACTIONS_BY_APP_TYPE.get(app_type, [{"label": "让导师解释", "action": "tutor.explain"}]),
        )
        saved = get_store().save_app(app, student_id=student_id, course_id=course_id)
        return AgentOutput(summary=f"已创建 {title}。", payload={"app": saved.model_dump()}, trace=["created_canvas_app", "persisted_canvas_app"])

    def focus_link(self, link_id: str, student_id: str = "demo-student", course_id: str | None = None) -> AgentOutput:
        store = get_store()
        link = store.get_chat_link(link_id)
        if not link:
            return AgentOutput(summary="未找到 AppLink。", payload={"found": False}, trace=["link_missing"])
        state_by_action = {
            "fullscreen": "fullscreen",
            "split": "split_left",
            "open": "focused",
            "focus": "focused",
            "explain": "focused",
            "generate_related": "focused",
        }
        next_state = state_by_action.get(link.action, "focused")
        app = store.update_app(link.app_id, {"state": next_state}, student_id=student_id, course_id=course_id)
        event = AppEvent(
            app_id=link.app_id,
            student_id=student_id,
            course_id=course_id,
            event_type="applink.open",
            payload={"link_id": link_id, "action": link.action, "course_id": course_id},
        )
        store.record_app_event(event)
        EduMem0Client().record_app_event(event)
        return AgentOutput(summary="已打开并聚焦目标 App。", payload={"link": link.model_dump(), "app": app.model_dump() if app else None, "event": event.model_dump()}, trace=["opened_chat_app_link", f"applied_link_action:{link.action}", "persisted_focus_event"])
