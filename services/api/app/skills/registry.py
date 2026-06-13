from __future__ import annotations

from app.skills.app_generation_skill import AppGenerationSkill
from app.skills.code_practice_skill import CodePracticeSkill
from app.skills.course_ingestion_skill import CourseIngestionSkill
from app.skills.custom_html_app_skill import CustomHtmlAppSkill
from app.skills.dashboard_skill import DashboardSkill
from app.skills.document_skill import DocumentSkill
from app.skills.image_generation_skill import ImageGenerationSkill
from app.skills.memory_update_skill import MemoryUpdateSkill
from app.skills.mindmap_skill import MindmapSkill
from app.skills.notes_skill import NotesSkill
from app.skills.ppt_skill import PPTSkill
from app.skills.quiz_skill import QuizSkill
from app.skills.reading_material_skill import ReadingMaterialSkill
from app.skills.resource_bundle_skill import ResourceBundleSkill
from app.skills.verifier_skill import VerifierSkill
from app.skills.video_script_skill import VideoScriptSkill


class SkillRegistry:
    def __init__(self) -> None:
        self.skills = {
            "document_skill": DocumentSkill(),
            "mindmap_skill": MindmapSkill(),
            "quiz_skill": QuizSkill(),
            "ppt_skill": PPTSkill(),
            "code_practice_skill": CodePracticeSkill(),
            "image_generation_skill": ImageGenerationSkill(),
            "video_script_skill": VideoScriptSkill(),
            "reading_material_skill": ReadingMaterialSkill(),
            "notes_skill": NotesSkill(),
            "dashboard_skill": DashboardSkill(),
            "resource_bundle_skill": ResourceBundleSkill(),
            "app_generation_skill": AppGenerationSkill(),
            "custom_html_app_skill": CustomHtmlAppSkill(),
            "verifier_skill": VerifierSkill(),
            "memory_update_skill": MemoryUpdateSkill(),
            "course_ingestion_skill": CourseIngestionSkill(),
        }

    def get(self, name: str):
        return self.skills[name]

    def names(self) -> list[str]:
        return sorted(self.skills)
