from __future__ import annotations

import pytest

from app.canvas.materializer import CanvasMaterializer
from app.cram.engine import (
    CramSessionCreate,
    CramStage,
    advance_cram_session,
    build_cram_dashboard_summary,
    classify_exam_mode,
    create_cram_session,
)
from app.cram.openstax_seed import OPENSTAX_CRAM_BOOKS, openstax_book_seed_payload
from app.hermes_runtime.task_executor import HermesTaskResult


class _FakeCramMaterializerStore:
    def __init__(self) -> None:
        self.sessions = []
        self.apps = []

    def create_cram_session(self, request):
        session = create_cram_session(request)
        self.sessions.append(session)
        return session

    def get_cram_session(self, session_id, **_kwargs):
        return next((session for session in self.sessions if session.session_id == session_id), None)

    def save_app(self, app, **_kwargs):
        self.apps.append(app)
        return app


def test_openstax_seed_contains_at_least_twenty_verified_books():
    payload = openstax_book_seed_payload()

    assert len(payload) >= 20
    assert all(book["provider"] == "openstax" for book in payload)
    assert all(book["details_url"].startswith("https://openstax.org/details/books/") for book in payload)
    assert all(book["pdf_url"].startswith("https://assets.openstax.org/") for book in payload)
    assert {book["exam_mode"] for book in payload} >= {"conceptual_cram", "practice_heavy"}
    assert any(book["slug"] == "principles-management" for book in payload)
    assert any(book["slug"] == "calculus-volume-1" for book in payload)


def test_classify_exam_mode_marks_conceptual_and_practice_heavy_courses():
    assert classify_exam_mode(["名词解释", "简答", "案例分析"]) == "conceptual_cram"
    assert classify_exam_mode(["选择题", "判断题", "论述题"]) == "conceptual_cram"
    assert classify_exam_mode(["计算题", "推导题", "证明题"]) == "practice_heavy"


def test_create_cram_session_deconstructs_points_and_tracks_priorities():
    session = create_cram_session(
        CramSessionCreate(
            student_id="stu-cram",
            course_id="course-management",
            course_title="管理学",
            exam_types=["选择题", "案例分析", "简答题"],
            must_know=["期望理论", "公平理论"],
            key_points=["霍桑实验"],
            textbook="Principles of Management",
        )
    )

    assert session.stage == CramStage.DECONSTRUCT
    assert session.progress.total_points >= 6
    assert session.progress.must_know_total >= 4
    assert session.progress.key_point_total >= 2
    assert session.knowledge_points[0].priority == "must_know"
    assert session.knowledge_points[0].hook in {"acronym", "contrast", "absurd", "none"}
    assert session.source_refs[0]["title"] == "Principles of Management"


def test_advance_cram_session_runs_teach_test_remediate_loop():
    session = create_cram_session(
        CramSessionCreate(
            student_id="stu-cram",
            course_id="course-management",
            course_title="管理学",
            exam_types=["选择题", "案例分析"],
            must_know=["期望理论"],
            key_points=["霍桑实验"],
        )
    )

    taught = advance_cram_session(session, action="confirm_deconstruction")
    assert taught.stage == CramStage.TEACH
    assert taught.progress.taught_points == min(3, taught.progress.total_points)

    tested = advance_cram_session(taught, action="teach_next_batch")
    assert tested.stage in {CramStage.TEACH, CramStage.TEST}
    while tested.stage == CramStage.TEACH:
        tested = advance_cram_session(tested, action="teach_next_batch")
    assert tested.progress.generated_questions > 0

    remediating = advance_cram_session(
        tested,
        action="submit_test_results",
        payload={
            "results": [
                {
                    "knowledge_point_id": tested.knowledge_points[0].id,
                    "is_correct": False,
                    "user_answer": "把激励理解成工资越高越好",
                }
            ]
        },
    )
    assert remediating.stage == CramStage.REMEDIATE
    assert remediating.progress.wrong_points == 1
    assert remediating.remediation_items[0].root_cause in {
        "concept_confusion",
        "logic_bias",
        "memory_gap",
        "transfer_failure",
    }

    finished = advance_cram_session(
        remediating,
        action="submit_remediation_results",
        payload={"results": [{"knowledge_point_id": tested.knowledge_points[0].id, "is_correct": False}]},
    )
    assert finished.stage == CramStage.SUMMARY
    assert finished.progress.stubborn_points == 1
    assert finished.next_actions[0].startswith("明天优先复习")


def test_cram_dashboard_summary_projects_session_into_learning_dashboard():
    session = create_cram_session(
        CramSessionCreate(
            student_id="stu-cram",
            course_id="course-management",
            course_title="管理学",
            exam_types=["名词解释", "案例分析"],
            must_know=["期望理论"],
            key_points=["霍桑实验"],
        )
    )
    session = advance_cram_session(session, action="confirm_deconstruction")

    summary = build_cram_dashboard_summary([session], OPENSTAX_CRAM_BOOKS)

    assert summary["active_session"]["session_id"] == session.session_id
    assert summary["active_session"]["stage"] == "teach"
    assert summary["active_session"]["course_title"] == "管理学"
    assert summary["kpis"]["openstax_books"] >= 20
    assert summary["kpis"]["must_know_coverage"] > 0
    assert summary["recommended_books"][0]["slug"]


@pytest.mark.asyncio
async def test_canvas_materializer_persists_hermes_exam_cram_as_cram_session():
    store = _FakeCramMaterializerStore()
    result = await CanvasMaterializer(store).materialize(
        HermesTaskResult(
            capability="exam_cram",
            topic="管理学",
            apps=[
                {
                    "app_type": "exam.cram",
                    "title": "管理学期末速成",
                    "payload": {
                        "course_title": "管理学期末速成",
                        "exam_types": ["简答题", "案例分析"],
                        "must_know": ["期望理论", "公平理论"],
                        "key_points": ["霍桑实验"],
                        "textbook": "Principles of Management",
                    },
                }
            ],
        ),
        student_id="stu-cram",
        course_id="course-management",
        conversation_id="conv-cram",
        message_id="msg-cram",
        run_id="run-cram",
        fallback_refs=[],
        capability="exam_cram",
        source_material="帮我做管理学期末速成",
    )

    assert len(store.sessions) == 1
    app = result.apps[0]
    assert app.app_type == "exam.cram"
    assert app.payload["session_id"] == store.sessions[0].session_id
    assert app.payload["session"]["progress"]["total_points"] >= 6
    assert app.payload["stage"] == "deconstruct"
    assert app.source_refs[0]["source_id"] == "openstax:principles-management"


@pytest.mark.asyncio
async def test_canvas_materializer_reuses_existing_cram_session_id_without_duplicate_create():
    store = _FakeCramMaterializerStore()
    existing = store.create_cram_session(
        CramSessionCreate(
            student_id="stu-cram",
            course_id="course-management",
            course_title="管理学",
            exam_types=["简答题"],
            must_know=["期望理论"],
            key_points=["霍桑实验"],
            textbook="Principles of Management",
        )
    )

    result = await CanvasMaterializer(store).materialize(
        HermesTaskResult(
            capability="exam_cram",
            topic="管理学",
            apps=[
                {
                    "app_type": "exam.cram",
                    "title": "管理学期末速成",
                    "payload": {
                        "session_id": existing.session_id,
                        "course_title": "管理学期末速成",
                    },
                }
            ],
        ),
        student_id="stu-cram",
        course_id="course-management",
        conversation_id="conv-cram",
        message_id="msg-cram",
        run_id="run-cram",
        fallback_refs=[],
        capability="exam_cram",
        source_material="继续打开管理学期末速成",
    )

    assert len(store.sessions) == 1
    app = result.apps[0]
    assert app.payload["session_id"] == existing.session_id
    assert app.payload["session"]["session_id"] == existing.session_id
    assert app.payload["course_title"] == "管理学"
