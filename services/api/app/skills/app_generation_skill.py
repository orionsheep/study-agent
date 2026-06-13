from __future__ import annotations

from app.canvas.component_namer import fallback_component_title
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize
from app.skills.base import SkillInput, SkillOutput


DEFAULT_ACTIONS_BY_APP_TYPE = {
    "custom.html": [{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "mindmap.concept": [{"label": "展开节点", "action": "mindmap.expand"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "quiz.practice": [{"label": "提交答案", "action": "quiz.submit"}, {"label": "让导师讲题", "action": "tutor.explain"}],
    "code.lab": [{"label": "解释代码", "action": "tutor.explain"}],
    "ppt.preview": [{"label": "预览 PPT", "action": "ppt.preview"}, {"label": "让导师串讲", "action": "tutor.explain"}],
    "video.script": [{"label": "查看分镜", "action": "video_script.view"}, {"label": "让导师解说", "action": "tutor.explain"}],
    "video.player": [{"label": "切换视频", "action": "video.select"}, {"label": "让导师总结视频", "action": "tutor.explain"}],
    "image.explanation": [{"label": "生成图解", "action": "image.generate"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "notes.session": [{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
    "resource.center": [{"label": "筛选资源", "action": "resource.filter"}, {"label": "让导师推荐", "action": "tutor.explain"}],
}

DEFAULT_SIZE_BY_APP_TYPE = {
    "custom.html": (1060, 820),
}


class AppGenerationSkill:
    skill_name = "app_generation_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        app_type = data.payload.get("app_type", "notes.session")
        payload = data.payload.get("payload", {})
        title = fallback_component_title(
            data.payload.get("title", f"{data.topic} App"),
            component_type=app_type,
            topic=data.topic,
            payload=payload if isinstance(payload, dict) else {},
        )
        default_width, default_height = DEFAULT_SIZE_BY_APP_TYPE.get(app_type, (380, 280))
        app = CanvasApp(
            app_type=app_type,
            title=title,
            icon=data.payload.get("icon", "Sparkles"),
            position=CanvasPosition(x=float(data.payload.get("x", 240)), y=float(data.payload.get("y", 180))),
            size=CanvasSize(width=float(data.payload.get("width", default_width)), height=float(data.payload.get("height", default_height))),
            payload=payload if isinstance(payload, dict) else {},
            source_refs=data.payload.get("source_refs", []),
            personalized_reason=data.payload.get("personalized_reason", "由资源生成流程转为可操作 App。"),
            actions=data.payload.get("actions") or DEFAULT_ACTIONS_BY_APP_TYPE.get(app_type, [{"label": "让导师解释", "action": "tutor.explain"}]),
        )
        return SkillOutput(skill_name=self.skill_name, payload={"app": app.model_dump()}, trace=["selected_native_template", "built_canvas_app"])
