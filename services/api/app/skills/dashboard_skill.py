from __future__ import annotations

from app.database.store import get_store
from app.skills.base import BaseResourceSkill, SkillInput, SkillOutput


class DashboardSkill(BaseResourceSkill):
    skill_name = "dashboard_skill"

    def run(self, data: SkillInput) -> SkillOutput:
        dashboard = get_store().dashboard(data.student_id)
        return SkillOutput(skill_name=self.skill_name, payload={"dashboard": dashboard.model_dump()}, trace=["aggregated_profile", "aggregated_memory", "aggregated_runs"])
