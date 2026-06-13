from __future__ import annotations

from app.skills.base import SkillInput, SkillOutput
from app.skills.code_practice_skill import CodePracticeSkill
from app.skills.document_skill import DocumentSkill
from app.skills.image_generation_skill import ImageGenerationSkill
from app.skills.mindmap_skill import MindmapSkill
from app.skills.notes_skill import NotesSkill
from app.skills.ppt_skill import PPTSkill
from app.skills.quiz_skill import QuizSkill
from app.skills.reading_material_skill import ReadingMaterialSkill
from app.skills.video_script_skill import VideoScriptSkill


class ResourceBundleSkill:
    skill_name = "resource_bundle_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        skills = [
            DocumentSkill(),
            MindmapSkill(),
            QuizSkill(),
            CodePracticeSkill(),
            ReadingMaterialSkill(),
            PPTSkill(),
            VideoScriptSkill(),
            ImageGenerationSkill(),
            NotesSkill(),
        ]
        resources = [skill.run(data).resource for skill in skills]
        return SkillOutput(
            skill_name=self.skill_name,
            payload={"resources": [resource.model_dump() for resource in resources if resource]},
            trace=["created_full_resource_types", "verified_resource_set"],
        )
