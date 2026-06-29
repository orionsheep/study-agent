---
name: cram-engine-skill
category: learnforge
description: LearnForge exam sprint / Cram Engine orchestration skill.
---

# Cram Engine Skill

Use this skill when LearnForge asks for exam sprint learning,期末速成,考前冲刺,突击复习,or Cram-style study planning.

Return ONLY valid JSON. No markdown fences. No prose outside JSON.

Required shape:
{
  "capability": "exam_cram",
  "summary": "short Chinese summary",
  "trace": ["exam_mode_classified", "openstax_sources_selected", "cram_session_created"],
  "resources": [
    {
      "type": "reading|quiz|notes",
      "title": "Chinese title",
      "target_topic": "topic",
      "difficulty": "adaptive",
      "content": {},
      "source_refs": [{"source_id":"openstax:<slug>","title":"OpenStax book title","locator":"chapter or concept"}],
      "personalized_reason": "why it supports the sprint",
      "tags": ["cram","openstax"]
    }
  ],
  "apps": [
    {
      "app_type": "exam.cram",
      "title": "期末速成",
      "payload": {
        "course_title": "course or exam title",
        "stage": "deconstruct|teach|test|remediate|summary",
        "exam_mode": "conceptual_cram|practice_heavy",
        "must_know": ["high-priority knowledge point"],
        "key_points": ["supporting point"],
        "next_actions": ["下一步动作"]
      },
      "personalized_reason": "why this sprint is appropriate"
    },
    {
      "app_type": "dashboard.learning",
      "title": "学习仪表盘",
      "payload": {"active_tab":"overview"},
      "personalized_reason": "show cram progress with the rest of the student's learning data"
    },
    {
      "app_type": "quiz.practice",
      "title": "速成诊断题",
      "payload": {"questions":[]},
      "personalized_reason": "validate the current cram batch"
    }
  ]
}

Rules:
- Follow the cram-engine loop: 1) deconstruct exam scope into must-know/key-point nodes, 2) teach the next compact batch with memory hooks, 3) generate diagnostic questions, 4) remediate wrong/stubborn points and summarize.
- Prefer OpenStax sources when they match the course. Use source_refs with `openstax:<slug>` ids and real book titles.
- Classify exam_mode as `practice_heavy` for calculation/problem-heavy exams, otherwise `conceptual_cram`.
- Do not substitute generic resource.center or custom.html for the primary app. The primary app_type MUST be `exam.cram`.
- Keep generated content general and capability-level; do not hardcode one demo topic.
