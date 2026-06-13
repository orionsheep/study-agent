from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.canvas.component_namer import ComponentTitleNamer
from app.database.store import LearningStore
from app.image_gateway.router import ImageGatewayRouter
from app.model_gateway.errors import ModelGatewayError
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize, LearningResource, new_id
from app.skills.base import SkillInput
from app.skills.custom_html_app_skill import CustomHtmlAppSkill
from app.video.bilibili import video_player_payload

if TYPE_CHECKING:
    from app.hermes_runtime.task_executor import HermesTaskResult


APP_TYPE_BY_RESOURCE = {
    "document": "notes.session",
    "notes": "notes.session",
    "mindmap": "mindmap.concept",
    "quiz": "quiz.practice",
    "reading": "resource.center",
    "code_practice": "code.lab",
    "ppt": "ppt.preview",
    "video_script": "video.script",
    "video": "video.player",
    "image": "image.explanation",
}

ICON_BY_APP_TYPE = {
    "custom.html": "Image",
    "mindmap.concept": "Brain",
    "quiz.practice": "CircleHelp",
    "code.lab": "Code2",
    "ppt.preview": "Presentation",
    "video.script": "Film",
    "video.player": "Film",
    "image.explanation": "FileImage",
    "physics.work_energy_demo": "Activity",
    "math.gradient_descent_demo": "Gauge",
    "notes.session": "NotebookPen",
    "resource.center": "BookOpen",
}

SIZE_BY_APP_TYPE = {
    "custom.html": (1060, 820),
    "mindmap.concept": (440, 330),
    "quiz.practice": (420, 330),
    "code.lab": (480, 340),
    "ppt.preview": (420, 320),
    "video.script": (420, 310),
    "video.player": (720, 520),
    "image.explanation": (470, 340),
    "physics.work_energy_demo": (470, 350),
    "math.gradient_descent_demo": (470, 350),
    "notes.session": (430, 320),
    "resource.center": (430, 330),
}

POSITION_BY_APP_TYPE = {
    "profile.dashboard": (40, 40),
    "learning.path": (40, 380),
    "knowledge.graph": (1440, 430),
    "mindmap.concept": (40, 770),
    "quiz.practice": (970, 40),
    "physics.work_energy_demo": (500, 40),
    "math.gradient_descent_demo": (500, 380),
    "code.lab": (840, 770),
    "notes.session": (970, 370),
    "dashboard.learning": (1440, 40),
    "ppt.preview": (450, 770),
    "image.explanation": (1260, 770),
    "video.script": (1655, 770),
    "video.player": (1655, 770),
    "resource.center": (1880, 40),
    "custom.html": (2045, 770),
}

ACTIONS_BY_APP_TYPE = {
    "custom.html": [{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "mindmap.concept": [{"label": "展开节点", "action": "mindmap.expand"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "quiz.practice": [{"label": "提交答案", "action": "quiz.submit"}, {"label": "让导师讲题", "action": "tutor.explain"}],
    "code.lab": [{"label": "解释代码", "action": "tutor.explain"}],
    "ppt.preview": [{"label": "预览 PPT", "action": "ppt.preview"}, {"label": "让导师串讲", "action": "tutor.explain"}],
    "video.script": [{"label": "查看分镜", "action": "video_script.view"}, {"label": "让导师解说", "action": "tutor.explain"}],
    "video.player": [{"label": "切换视频", "action": "video.select"}, {"label": "让导师总结视频", "action": "tutor.explain"}],
    "image.explanation": [{"label": "生成图解", "action": "image.generate"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "physics.work_energy_demo": [{"label": "播放演示", "action": "demo.play"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "math.gradient_descent_demo": [{"label": "播放演示", "action": "demo.play"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "notes.session": [{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
    "resource.center": [{"label": "筛选资源", "action": "resource.filter"}, {"label": "让导师推荐", "action": "tutor.explain"}],
}


class MaterializedBundle(BaseModel):
    resources: list[LearningResource] = Field(default_factory=list)
    apps: list[CanvasApp] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class CanvasMaterializer:
    def __init__(self, store: LearningStore) -> None:
        self.store = store

    def normalize_resource(self, item: dict[str, Any], fallback_refs: list[dict[str, Any]]) -> LearningResource:
        raw_refs = item.get("source_refs")
        valid_refs = [ref for ref in raw_refs if isinstance(ref, dict)] if isinstance(raw_refs, list) else []
        data = {
            "type": item.get("type") or "document",
            "title": item.get("title") or "学习资源",
            "target_topic": item.get("target_topic") or item.get("topic") or "学习主题",
            "difficulty": item.get("difficulty") or "adaptive",
            "content": item.get("content") if isinstance(item.get("content"), dict) else {},
            "source_refs": valid_refs if valid_refs else fallback_refs,
            "personalized_reason": item.get("personalized_reason") or "由 Hermes 根据当前学习请求生成。",
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        }
        if item.get("resource_id"):
            data["resource_id"] = item["resource_id"]
        resource_type = data["type"]
        if resource_type == "code":
            data["type"] = "code_practice"
        return LearningResource.model_validate(data)

    def app_position(self, index: int) -> tuple[float, float]:
        col = index % 3
        row = index // 3
        return 80 + col * 470, 80 + row * 370

    def semantic_app_position(self, app_type: str, index: int, type_index: int) -> tuple[float, float]:
        base = POSITION_BY_APP_TYPE.get(app_type)
        if not base:
            return self.app_position(index)
        x, y = base
        return x + type_index * 34, y + type_index * 34

    async def enrich_image_payload(self, app_type: str, payload: dict[str, Any], topic: str) -> dict[str, Any]:
        if app_type != "image.explanation" or payload.get("image_url"):
            return payload
        provider_alias = str(payload.get("provider_alias") or payload.get("image_provider_alias") or payload.get("provider") or "").lower()
        try:
            request = ImageGatewayRouter().planner.plan(topic, str(payload.get("visual_brief") or payload.get("teaching_goal") or f"解释 {topic}"))
            result = await ImageGatewayRouter().client.generate(request)
            display_provider = "nanobanana" if provider_alias in {"nanobanana", "nano banana", "banana"} else result.provider
            return {
                **payload,
                "image_url": result.image_url,
                "overlay_labels": result.overlay_labels,
                "provider": display_provider,
                "provider_alias": display_provider,
                "image_metadata": {**result.metadata, "actual_provider": result.provider, "display_provider": display_provider},
            }
        except Exception as exc:
            return {**payload, "image_error": f"{type(exc).__name__}: {exc}"}

    def validate_custom_html(self, payload: dict[str, Any], topic: str, source_material: str | None = None) -> dict[str, Any]:
        html = str(payload.get("html") or CustomHtmlAppSkill().fallback_widget(topic, "", ""))
        topic_context = "\n".join(
            str(item)
            for item in [
                topic,
                payload.get("topic"),
                payload.get("title"),
                source_material,
            ]
            if item
        )
        output = CustomHtmlAppSkill().run(SkillInput(topic=topic_context or topic, payload={"html": html}))
        if not output.payload.get("valid"):
            fallback = f"<section><h2>{topic}</h2><p>原始 HTML 未通过安全校验，已降级为安全学习卡片。你仍然可以继续让导师基于这个主题生成更细的版本。</p></section>"
            output = CustomHtmlAppSkill().run(SkillInput(topic=topic_context or topic, payload={"html": fallback}))
        return {
            **payload,
            "html": output.payload.get("html", html),
            "sandbox": output.payload.get("sandbox", "allow-scripts"),
            "sanitized": bool(output.payload.get("sanitized")),
            "fallback_used": bool(output.payload.get("fallback_used")),
        }

    async def materialize(
        self,
        bundle: "HermesTaskResult",
        *,
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
        fallback_refs: list[dict[str, Any]],
        capability: str | None = None,
        source_material: str | None = None,
    ) -> MaterializedBundle:
        trace: list[str] = []
        title_namer = ComponentTitleNamer()
        resources: list[LearningResource] = []
        normalized_resources: list[LearningResource] = []
        for item in bundle.resources:
            resource = self.normalize_resource(item, fallback_refs)
            normalized_resources.append(resource)

        if normalized_resources:
            trace.extend(await title_namer.rename_resources(normalized_resources, source_material=source_material or ""))

        for resource in normalized_resources:
            saved = self.store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="hermes_resource_bundle")
            resources.append(saved)

        apps: list[CanvasApp] = []
        group_id = new_id("group")
        type_counts: dict[str, int] = {}
        for index, spec in enumerate(bundle.apps):
            resource_index = int(spec.get("resource_index", index if index < len(resources) else 0) or 0)
            resource = resources[resource_index] if 0 <= resource_index < len(resources) else None
            app_type = spec.get("app_type") or (APP_TYPE_BY_RESOURCE.get(resource.type) if resource else "custom.html")
            if app_type == "infographic":
                app_type = "custom.html"
            if app_type in {"interactive.demo", "animation.demo", "html.app", "custom_html"}:
                app_type = "custom.html"
            app_type = str(app_type)
            type_index = type_counts.get(app_type, 0)
            type_counts[app_type] = type_index + 1
            payload = spec.get("payload") if isinstance(spec.get("payload"), dict) else {}
            if resource and not payload:
                payload = resource.content.copy()
            topic = (resource.target_topic if resource else spec.get("topic")) or "学习主题"
            if app_type == "resource.center":
                payload.setdefault(
                    "resources",
                    [
                        {
                            "resource_id": item.resource_id,
                            "title": item.title,
                            "type": item.type,
                            "personalized_reason": item.personalized_reason,
                            "source_refs": item.source_refs,
                        }
                        for item in resources
                    ],
                )
            if app_type == "video.player":
                video_resources = [item for item in resources if item.type == "video"]
                if resource and resource.type == "video" and all(item.resource_id != resource.resource_id for item in video_resources):
                    video_resources.insert(0, resource)
                payload = {**video_player_payload(str(topic), video_resources), **payload}
            if app_type == "custom.html":
                payload = self.validate_custom_html(payload, str(topic), source_material=source_material)
            if app_type == "image.explanation" and capability == "custom_infographic":
                payload.setdefault("infographic_render_mode", "image")
                payload.setdefault("provider_alias", "nanobanana")
                payload.setdefault("visual_brief", f"面向学习者的“{topic}”信息图，适合全屏展示。")
            payload = await self.enrich_image_payload(str(app_type), payload, str(topic))
            x, y = self.semantic_app_position(app_type, index, type_index)
            width, height = SIZE_BY_APP_TYPE.get(str(app_type), (420, 320))
            app = CanvasApp(
                app_id=spec.get("app_id") or new_id("app"),
                app_type=app_type,
                title=spec.get("title") or (resource.title if resource else "Hermes 学习 App"),
                icon=spec.get("icon") or ICON_BY_APP_TYPE.get(str(app_type), "Sparkles"),
                render_mode="sandbox_iframe" if app_type == "custom.html" else "native_react",
                state="focused" if index == 0 else "window",
                position=CanvasPosition(x=float(spec.get("x", x)), y=float(spec.get("y", y))),
                size=CanvasSize(width=float(spec.get("width", width)), height=float(spec.get("height", height))),
                z_index=80 if index == 0 else 20 + index,
                group_id=spec.get("group_id") or f"agent-generated-{capability or 'canvas'}",
                payload=payload,
                source={
                    "student_id": student_id,
                    "course_id": course_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "run_id": run_id,
                    "resource_id": resource.resource_id if resource else None,
                    "skill_name": "hermes_resource_bundle",
                    "capability": capability,
                    "source_material": source_material,
                },
                source_refs=resource.source_refs if resource else fallback_refs,
                personalized_reason=spec.get("personalized_reason") or (resource.personalized_reason if resource else "由 Hermes 创建。"),
                actions=spec.get("actions") or ACTIONS_BY_APP_TYPE.get(str(app_type), [{"label": "让导师解释", "action": "tutor.explain"}]),
            )
            apps.append(app)

        if apps:
            trace.extend(await title_namer.rename_apps(apps, source_material=source_material or ""))

        saved_apps: list[CanvasApp] = []
        for app in apps:
            saved_app = self.store.save_app(app, student_id=student_id, course_id=course_id, agent="hermes_runtime", skill="canvas_materializer")
            saved_apps.append(saved_app)
        return MaterializedBundle(resources=resources, apps=saved_apps, trace=["validated_resources", *trace, "created_canvas_apps", *bundle.trace])
