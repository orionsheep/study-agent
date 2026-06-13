from __future__ import annotations

import re

from app.schemas.app_protocol import LearningResource
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class NotesSkill(BaseResourceSkill):
    skill_name = "notes_skill"

    def infer_topic(self, data: SkillInput, source_summary: str) -> str:
        raw_topic = str(data.topic or data.payload.get("topic") or "").strip()
        topic_hint = str(data.payload.get("topic_hint") or "").strip()
        generic_note_commands = {"笔记", "总结", "总结为笔记", "整理成笔记", "本节学习总结", "学习笔记"}
        if topic_hint:
            return topic_hint[:80]
        if raw_topic and raw_topic not in generic_note_commands and len(raw_topic) > 2:
            return raw_topic[:80]
        patterns = [
            r"(?:关于|围绕|主题是|主题为|讲解|介绍)([^，。！？\\n]{2,32})",
            r"([\u4e00-\u9fffA-Za-z0-9]{0,12}(?:算法|模型|定理|结构|函数|系统|协议|语法|单词|文章|概念))",
            r"[《“]([^》”]{2,24})[》”]",
            r"(?:核心|主要|当前)([^，。！？\\n]{2,24})",
        ]
        for pattern in patterns:
            match = re.search(pattern, source_summary)
            if match:
                candidate = match.group(1).strip(" ：:、，。！？ ")
                candidate = re.sub(r"^(所有|全部|这些|几种|几类|常见|主流|核心|经典|最经典的?)", "", candidate).strip()
                if candidate and candidate not in {"所有", "全部", "核心", "主要"}:
                    return candidate[:80]
        first_sentence = re.split(r"[。！？\\n]", source_summary.strip())[0].strip()
        return (first_sentence[:40] if first_sentence else raw_topic or "当前学习主题")

    def run(self, data: SkillInput) -> SkillOutput:
        source_summary = str(data.payload.get("source_summary") or data.payload.get("last_assistant_answer") or "").strip()
        topic = self.infer_topic(data, source_summary)
        refs = [
            {
                "document_id": "conversation",
                "chunk_id": f"chat-{data.student_id}-{topic}",
                "course_id": data.course_id,
                "chapter": "Tutor Chat",
                "section": topic,
                "quote_span": [0, min(120, len(source_summary))],
                "confidence": 0.92,
            }
        ] if source_summary else self.source_refs(topic)
        key_points = data.payload.get("key_points") if isinstance(data.payload.get("key_points"), list) else []
        if not key_points:
            key_points = [
                f"围绕“{topic}”梳理核心概念、适用场景和常见误区",
                "把知识点拆成可复习的小块，而不是混入无关主题",
                "后续可以继续转成题库、导图、信息图或代码实验",
            ]
        resource = LearningResource(
            type="notes",
            title=f"{topic}学习笔记",
            target_topic=topic,
            content={
                "topic": topic,
                "key_conclusions": key_points,
                "source_summary": source_summary[:1200],
                "review_prompts": [f"用自己的话解释“{topic}”的核心思想", f"列出“{topic}”最容易混淆的两个点"],
                "next_actions": ["补一个例子", "转成 3 道自测题", "需要时再生成图解或信息图"],
                "linked_app_ids": data.payload.get("linked_app_ids") if isinstance(data.payload.get("linked_app_ids"), list) else [],
            },
            source_refs=refs,
            personalized_reason=f"把当前关于“{topic}”的讨论整理成可复习笔记，避免串到其他学科或旧主题。",
            tags=["notes", "session_summary", topic],
        )
        output = SkillOutput(skill_name=self.skill_name, resource=resource, trace=["summarized_session", "topic_bound_notes"])
        self.validate(output)
        return output
