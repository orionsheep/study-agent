from __future__ import annotations

import json
import re
from typing import Any

from app.model_gateway.base import ChatMessage
from app.model_gateway.errors import ModelGatewayError, ProviderBlocked
from app.model_gateway.router import ModelGatewayRouter
from app.schemas.app_protocol import CanvasApp, LearningResource


TITLE_MAX_CHARS = 24

APP_TYPE_NOUNS = {
    "custom.html": "信息图",
    "mindmap.concept": "思维导图",
    "quiz.practice": "诊断题",
    "code.lab": "代码实验",
    "ppt.preview": "PPT预览",
    "video.script": "视频脚本",
    "video.player": "视频播放器",
    "image.explanation": "教学图解",
    "physics.work_energy_demo": "互动演示",
    "math.gradient_descent_demo": "互动演示",
    "notes.session": "学习笔记",
    "resource.center": "资源中心",
    "learning.path": "学习路径",
    "dashboard.learning": "学习仪表盘",
    "knowledge.graph": "知识图谱",
    "profile.dashboard": "学习画像",
}

RESOURCE_TYPE_NOUNS = {
    "document": "讲义",
    "mindmap": "思维导图",
    "quiz": "练习组",
    "ppt": "PPT大纲",
    "code_practice": "代码实验",
    "image": "教学图解",
    "video_script": "视频脚本",
    "reading": "阅读卡",
    "notes": "学习笔记",
    "dashboard": "学习仪表盘",
    "app_bundle": "资源包",
}

GENERIC_TITLE_EXACT = {
    "",
    "app",
    "App",
    "学习App",
    "学习 App",
    "Hermes学习App",
    "Hermes 学习 App",
    "学习资源",
    "资源",
    "组件",
    "自定义组件",
    "自定义组件沙箱",
    "测试",
    "测试题",
    "练习题",
    "题库练习",
    "自测题",
    "诊断题",
    "测试代码",
    "代码实验",
    "Python代码实验",
    "Python 代码实验",
    "测试PPT",
    "测试 PPT",
    "微课PPT预览",
    "微课 PPT 预览",
    "教学图解资产",
    "60秒动画脚本",
    "60 秒动画脚本",
    "测试信息图",
    "信息图",
    "测试导图",
    "概念思维导图",
}

STOP_WORDS = {
    "请",
    "用",
    "自己",
    "话",
    "解释",
    "说明",
    "一下",
    "为什么",
    "怎么",
    "什么",
    "测试",
    "题目",
    "题",
    "选择",
    "完成",
    "根据",
    "以下",
    "这个",
    "一个",
    "如何",
}


def clean_text(value: Any, limit: int = 320) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def sanitize_title(title: str) -> str:
    cleaned = clean_text(title, TITLE_MAX_CHARS * 2)
    cleaned = re.sub(r"^(标题|名称|name|title)\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" \t\r\n\"'`“”‘’[]【】")
    cleaned = re.sub(r"[。；;,.，、]+$", "", cleaned)
    if len(cleaned) > TITLE_MAX_CHARS:
        cleaned = cleaned[:TITLE_MAX_CHARS].rstrip(" -·：:，,、")
    return cleaned


def is_generic_component_title(title: str) -> bool:
    cleaned = sanitize_title(title).replace(" ", "")
    if cleaned in GENERIC_TITLE_EXACT:
        return True
    if cleaned.startswith("测试") and len(cleaned) <= 8:
        return True
    return bool(
        re.fullmatch(
            r"(测试|练习|自测|诊断)?(题|测试题|练习题|题库|导图|代码|PPT|视频脚本|信息图|图解|资源|组件|App)(第?\d+组?)?",
            cleaned,
            flags=re.IGNORECASE,
        )
    )


def compact_content(value: Any, limit: int = 560) -> str:
    pieces: list[str] = []

    def add(item: Any) -> None:
        text = clean_text(item, 180)
        if text and text not in pieces:
            pieces.append(text)

    def walk(item: Any, depth: int = 0) -> None:
        if len(" ".join(pieces)) >= limit or depth > 3:
            return
        if isinstance(item, dict):
            priority = [
                "topic",
                "target_topic",
                "teaching_goal",
                "visual_brief",
                "summary",
                "title",
                "prompt",
                "stem",
                "question",
                "scene",
                "narration",
                "expected_output",
                "starter_code",
                "html",
            ]
            for key in priority:
                if key in item:
                    walk(item[key], depth + 1)
            for key, child in item.items():
                if key not in priority:
                    walk(child, depth + 1)
        elif isinstance(item, list):
            for child in item[:6]:
                walk(child, depth + 1)
        elif isinstance(item, str | int | float | bool):
            add(item)

    walk(value)
    return clean_text(" | ".join(pieces), limit)


def extract_topic_hint(topic: str | None, payload: dict[str, Any] | None, content_text: str) -> str:
    for candidate in [
        topic,
        (payload or {}).get("topic"),
        (payload or {}).get("target_topic"),
        (payload or {}).get("teaching_goal"),
    ]:
        cleaned = sanitize_title(str(candidate or ""))
        if cleaned and not is_generic_component_title(cleaned):
            return cleaned[:14]

    text = clean_text(content_text, 260)
    patterns = [
        r"(?:解释|理解|掌握|围绕|关于|学习|讲解|演示)([\u4e00-\u9fffA-Za-z0-9·+\- ]{2,18})",
        r"([\u4e00-\u9fffA-Za-z0-9·+\- ]{2,18})(?:的核心|的步骤|为什么|怎么|练习|诊断|实验)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            cleaned = sanitize_title(match.group(1))
            if cleaned and not is_generic_component_title(cleaned):
                return cleaned[:14]

    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9·+\-]{2,}", text)
    for token in tokens:
        cleaned = sanitize_title(token)
        if cleaned and cleaned not in STOP_WORDS and not is_generic_component_title(cleaned):
            return cleaned[:14]
    return "当前内容"


def fallback_component_title(
    current_title: str | None,
    *,
    component_type: str,
    topic: str | None = None,
    payload: dict[str, Any] | None = None,
    content_text: str | None = None,
) -> str:
    title = sanitize_title(current_title or "")
    if title and not is_generic_component_title(title):
        return title

    noun = APP_TYPE_NOUNS.get(component_type) or RESOURCE_TYPE_NOUNS.get(component_type) or "学习组件"
    content = content_text or compact_content(payload or {})
    hint = extract_topic_hint(topic, payload, content)
    if hint.endswith(noun) or noun in hint[-6:]:
        return sanitize_title(hint) or noun
    return sanitize_title(f"{hint}{noun}") or noun


def ensure_unique_title(title: str, used: set[str], *, fallback_seed: str) -> str:
    base = sanitize_title(title) or sanitize_title(fallback_seed) or "学习组件"
    candidate = base
    index = 2
    while candidate in used:
        suffix = f"第{index}组"
        candidate = f"{base[: max(1, TITLE_MAX_CHARS - len(suffix))]}{suffix}"
        index += 1
    used.add(candidate)
    return candidate


class ComponentTitleNamer:
    """Generate content-aware titles for resources and canvas apps.

    The normal path uses the configured LLM in one batch per chunk. If that is
    unavailable, deterministic content-derived titles keep the UI non-generic.
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider
        self.router = ModelGatewayRouter()

    async def rename_resources(self, resources: list[LearningResource], *, source_material: str = "") -> list[str]:
        drafts = [
            {
                "index": index,
                "kind": "resource",
                "component_type": resource.type,
                "current_title": resource.title,
                "topic": resource.target_topic,
                "content": compact_content(resource.content),
            }
            for index, resource in enumerate(resources)
        ]
        titles, trace = await self._generate_titles(drafts, source_material=source_material)
        used: set[str] = set()
        for draft, resource in zip(drafts, resources):
            index = int(draft["index"])
            llm_title = sanitize_title(titles.get(index, ""))
            candidate = llm_title or fallback_component_title(
                resource.title,
                component_type=resource.type,
                topic=resource.target_topic,
                payload=resource.content,
                content_text=str(draft["content"]),
            )
            if not llm_title and not is_generic_component_title(resource.title) and resource.title not in used:
                candidate = resource.title
            resource.title = ensure_unique_title(candidate, used, fallback_seed=str(draft["content"]) or resource.target_topic)
        return trace

    async def rename_apps(self, apps: list[CanvasApp], *, source_material: str = "") -> list[str]:
        drafts = [
            {
                "index": index,
                "kind": "app",
                "component_type": app.app_type,
                "current_title": app.title,
                "topic": app.payload.get("topic") or app.payload.get("target_topic") or app.source.get("source_material"),
                "content": compact_content({"payload": app.payload, "source": app.source, "reason": app.personalized_reason}),
            }
            for index, app in enumerate(apps)
        ]
        titles, trace = await self._generate_titles(drafts, source_material=source_material)
        original_counts: dict[str, int] = {}
        for app in apps:
            original_counts[app.title] = original_counts.get(app.title, 0) + 1
        used: set[str] = set()
        for draft, app in zip(drafts, apps):
            index = int(draft["index"])
            llm_title = sanitize_title(titles.get(index, ""))
            candidate = llm_title or fallback_component_title(
                app.title,
                component_type=app.app_type,
                topic=str(draft.get("topic") or ""),
                payload=app.payload,
                content_text=str(draft["content"]),
            )
            if (
                not llm_title
                and not is_generic_component_title(app.title)
                and original_counts.get(app.title, 0) == 1
                and app.title not in used
            ):
                candidate = app.title
            app.title = ensure_unique_title(candidate, used, fallback_seed=str(draft["content"]) or app.app_type)
        return trace

    async def _generate_titles(self, drafts: list[dict[str, Any]], *, source_material: str = "") -> tuple[dict[int, str], list[str]]:
        titles: dict[int, str] = {}
        trace: list[str] = []
        for start in range(0, len(drafts), 12):
            chunk = drafts[start : start + 12]
            try:
                chunk_titles = await self._generate_title_chunk(chunk, source_material=source_material)
                titles.update(chunk_titles)
                trace.append(f"llm_component_titles:{len(chunk_titles)}/{len(chunk)}")
            except (ModelGatewayError, ProviderBlocked, TimeoutError, ValueError, KeyError, TypeError) as exc:
                trace.append(f"component_title_fallback:{type(exc).__name__}")
        return titles, trace

    async def _generate_title_chunk(self, drafts: list[dict[str, Any]], *, source_material: str = "") -> dict[int, str]:
        system = (
            "你是 LearnForge 的组件命名助手。你的任务是根据每个生成组件的实际内容，为它输出具体、可辨识、中文为主的短标题。"
            "标题必须体现题干、主题、实验目标、PPT内容、图解对象或脚本主题，禁止只叫“测试题”“练习题”“学习资源”“App”“组件”。"
            "同一批标题必须互不重复。标题建议 6-18 个汉字，最长不超过 24 个字符。不要使用引号、编号前缀或解释。"
        )
        user = (
            "请只返回 JSON：{\"titles\":[{\"index\":0,\"title\":\"...\"}]}。\n"
            "命名规则：\n"
            "1. quiz 要根据题干/考点命名，如“学习率发散诊断题”。\n"
            "2. code/ppt/video/image/html/mindmap 要根据内容目标命名，而不是按类型泛称。\n"
            "3. 如果内容很相近，也要用考点或场景区分。\n"
            f"源材料摘要：{clean_text(source_material, 900)}\n"
            f"组件列表：{json.dumps(drafts, ensure_ascii=False)}"
        )
        client = self.router.client(self.provider)
        response = await client.complete([ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)], stream=False)
        text = client.extract_assistant_text(response).strip()
        data = self._parse_json(text)
        raw_titles = data.get("titles", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if not isinstance(raw_titles, list):
            raise ValueError("title JSON must contain a titles list")
        parsed: dict[int, str] = {}
        for item in raw_titles:
            if not isinstance(item, dict):
                continue
            index = int(item.get("index"))
            title = sanitize_title(str(item.get("title") or ""))
            if title and not is_generic_component_title(title):
                parsed[index] = title
        return parsed

    def _parse_json(self, text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise
