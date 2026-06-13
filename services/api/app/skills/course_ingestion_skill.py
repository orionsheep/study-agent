from __future__ import annotations

from app.database.store import get_store
from app.rag.course_seed import SEED_COURSE
from app.skills.base import SkillInput, SkillOutput


class CourseIngestionSkill:
    skill_name = "course_ingestion_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        store = get_store()
        graph = store.knowledge_graph(data.course_id)
        return SkillOutput(skill_name=self.skill_name, payload={"course": SEED_COURSE, "graph": graph}, trace=["parsed_course_seed", "built_chunks", "built_prerequisites"])
