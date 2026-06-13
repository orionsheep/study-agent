from app.hermes_runtime.skill_sync import REQUIRED_HERMES_SKILLS, HermesSkillSync


def test_required_hermes_skill_files_exist():
    sync = HermesSkillSync()
    paths = sync.sync()
    assert len(paths) == len(REQUIRED_HERMES_SKILLS)
    assert all(path.name == "SKILL.md" and path.exists() for path in paths)


def test_guizang_ppt_skill_is_synced_with_assets():
    sync = HermesSkillSync()
    sync.sync()
    for root in [sync.skills_root(), sync.hermes_home_skills_root()]:
        skill_root = root / "guizang-ppt-skill"
        assert (skill_root / "SKILL.md").exists()
        assert (skill_root / "assets" / "template.html").exists()
        assert (skill_root / "assets" / "template-swiss.html").exists()
        assert (skill_root / "references" / "layouts-swiss.md").exists()
        assert (skill_root / "scripts" / "validate-swiss-deck.mjs").exists()
