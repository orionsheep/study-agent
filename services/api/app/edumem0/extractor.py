from __future__ import annotations

from dataclasses import dataclass

from app.edumem0.confidence_policy import ConfidencePolicy
from app.edumem0.decay_policy import DecayPolicy
from app.schemas.app_protocol import EduMemoryItem


@dataclass(frozen=True)
class _SubjectHint:
    subject: str
    score: float


class MemoryExtractor:
    def __init__(self) -> None:
        self.confidence = ConfidencePolicy()
        self.decay = DecayPolicy()
        self._knowledge_point_map = {
            "kp-optimization": ["梯度下降", "学习率", "优化", "gd", "loss"],
            "kp-math": ["数学", "导数", "链式法则", "微分", "积分", "推导"],
            "kp-nn": ["神经网络", "反向传播", "激活", "全连接", "神经元"],
            "kp-energy": ["动能", "能量", "力", "位移", "功"],
            "kp-safety": ["安全", "引用", "一致性", "验收", "安全评测"],
        }
        self._subject_map = {
            "数学": ["数学", "数学基础", "数学推导", "微积分", "线性代数"],
            "编程": ["python", "代码", "作业", "脚本", "项目"],
            "机器学习": ["神经网络", "优化", "模型", "训练", "学习率", "损失", "激活"],
            "物理": ["力", "动能", "物理", "位移"],
        }

    def from_chat(self, student_id: str, message: str, course_id: str | None = "ai-course") -> list[EduMemoryItem]:
        text = message.strip()
        lowered = text.lower()

        dimensions: dict[str, str | list[str] | dict[str, float]] = {}
        if "大一" in text:
            dimensions["grade"] = "大一"
        if "软件工程" in text:
            dimensions["major"] = "软件工程"
        if "python" in lowered:
            dimensions["knowledge_foundation"] = "Python 一般"
        weak_terms = ["弱", "薄弱", "一般", "困难"]
        if any(term in text for term in weak_terms) and any(topic in text for topic in ["数学", "线性代数", "推导"]):
            weak_points: list[str] = []
            if "线性代数" in text:
                weak_points.append("线性代数")
            if "数学" in text or "推导" in text:
                weak_points.append("数学推导")
            dimensions["weak_points"] = weak_points or ["数学推导"]
        if "图解" in text:
            dimensions.setdefault("preferred_resources", []).append("图解")
        if "代码" in text:
            dimensions.setdefault("preferred_resources", [])
            dimensions["preferred_resources"] = list(dict.fromkeys([*dimensions["preferred_resources"], "代码练习"]))
            dimensions["interests"] = ["代码实验"]
        if "图解" in text or "可视化" in text:
            dimensions["cognitive_style"] = "图解优先，配合互动可视化"
        if "小步" in text or "分阶段" in text or "练习" in text:
            dimensions["learning_pace"] = "小步练习，分阶段推进"
        if "神经网络" in text:
            dimensions["learning_goal"] = dimensions.get("learning_goal", "") or "学习神经网络"
            dimensions.setdefault("interests", [])
            dimensions["interests"] = list(dict.fromkeys([*dimensions["interests"], "神经网络训练"]))

        knowledge_point_hits = self._extract_knowledge_point_hints(lowered)
        subjects = self._extract_subjects(lowered)

        if subjects:
            dimensions["subjects"] = [item.subject for item in subjects]
            dimensions["subject_confidence"] = {item.subject: item.score for item in subjects}
        else:
            dimensions["subjects"] = ["待补充"]
            dimensions["subject_confidence"] = {"待补充": 0.25}

        if not dimensions:
            dimensions["learning_goal"] = text[:80]

        dimensions.setdefault("cognitive_style", "对话诊断后自适应")
        dimensions.setdefault("learning_pace", "分阶段练习")

        mastery_default = 0.55
        if any(term in text for term in weak_terms):
            mastery_default = 0.35
        dimensions["mastery_map"] = {
            "数学推导基础": 0.35 if any(term in text for term in weak_terms) else 0.55,
            "Python": 0.52 if "python" in lowered else 0.4,
            "神经网络": 0.24 if "神经网络" in text else 0.0,
        }

        if not knowledge_point_hits:
            # 不强制要求一次性提供完整科目图谱，默认给到待补充状态。
            dimensions.setdefault("knowledge_point_hints", ["待补充"])
            dimensions.setdefault("course_focus", course_id or "未知课程")
        else:
            dimensions["knowledge_point_hints"] = knowledge_point_hits

        if "学习目标" in text or "学习目标" in text:
            dimensions.setdefault("learning_goal", text[:80])
        elif "学习" in text and "目标" in text and "learning_goal" not in dimensions:
            dimensions["learning_goal"] = text[:80]

        content = f"从对话提取学习画像：{dimensions}"
        return [
            EduMemoryItem(
                student_id=student_id,
                course_id=course_id,
                knowledge_point_id=knowledge_point_hits[0] if knowledge_point_hits else None,
                memory_type="profile",
                content=content,
                structured_payload={
                    "dimensions": dimensions,
                    "raw_text": text,
                    "knowledge_point_hints": knowledge_point_hits,
                },
                confidence=self.confidence.score("chat"),
                importance=0.72,
                decay_rate=self.decay.rate_for_type("profile"),
                evidence_type="chat",
                source_agent="profile_agent",
                tags=["profile", "chat_extraction"],
            )
        ]

    def _extract_knowledge_point_hints(self, lowered_message: str) -> list[str]:
        knowledge_points: list[str] = []
        for kp_id, signals in self._knowledge_point_map.items():
            if any(signal in lowered_message for signal in signals):
                knowledge_points.append(kp_id)
        return knowledge_points

    def _extract_subjects(self, lowered_message: str) -> list[_SubjectHint]:
        hits: list[_SubjectHint] = []
        for subject, signals in self._subject_map.items():
            matched = [s for s in signals if s in lowered_message]
            if not matched:
                continue
            if any("进阶" in lowered_message or "提高" in lowered_message for _ in [subject]):
                score = 0.72
            elif any("弱" in lowered_message or "一般" in lowered_message for _ in [subject]):
                score = 0.6
            else:
                score = 0.82
            hits.append(_SubjectHint(subject=subject, score=round(min(0.95, score + (len(matched) - 1) * 0.08), 2)))
        return sorted(hits, key=lambda item: item.score, reverse=True)
