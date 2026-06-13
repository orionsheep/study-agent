from __future__ import annotations

from app.image_gateway.base import ImageRequest


class ImagePromptPlanner:
    def plan(self, topic: str, teaching_goal: str) -> ImageRequest:
        is_infographic = any(marker in f"{topic} {teaching_goal}".lower() for marker in ["信息图", "infographic", "poster", "海报", "visual_brief", "视觉"])
        labels = [
            {"id": "label-1", "text": "概念入口", "x": 0.18, "y": 0.22},
            {"id": "label-2", "text": "关键公式", "x": 0.58, "y": 0.42},
            {"id": "label-3", "text": "错误提醒", "x": 0.72, "y": 0.76},
        ]
        chinese_text_rules = (
            "All visible text inside the image must be Simplified Chinese only. "
            "Do not include English words, placeholder text such as LABEL, lorem ipsum, fake glyphs, garbled text, watermarks, UI chrome, or speech bubbles with unreadable text. "
            "Use fewer than 36 Chinese characters per text block; every character must be large, crisp, and readable."
        )
        if is_infographic:
            prompt = (
                "Create a polished Chinese educational infographic for a learning canvas. "
                "Use the official Nano Banana style pattern: clear subject, concrete scene, strong composition, finished premium asset quality. "
                "Composition: one large Chinese title, 3 to 5 structured panels, icons, arrows, comparison blocks, and generous spacing. "
                "Content must cover: core intuition, key steps, one concrete example, common mistake, and takeaway. "
                f"{chinese_text_rules} "
                f"Topic: {topic}. Teaching goal and visual brief: {teaching_goal}."
            )
        else:
            prompt = (
                "Create a clean Chinese educational diagram for a learning canvas. "
                "Use a clear central visual metaphor, 2 to 4 labeled Chinese callouts, and calm study-focused colors. "
                f"{chinese_text_rules} "
                f"Topic: {topic}. Teaching goal: {teaching_goal}."
            )
        return ImageRequest(prompt=prompt, overlay_labels=labels, teaching_goal=teaching_goal)
