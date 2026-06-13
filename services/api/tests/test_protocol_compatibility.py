from app.schemas.app_protocol import (
    AgentRun,
    AgentStep,
    AgentStreamEvent,
    CanvasApp,
    CanvasFrame,
    CanvasConnector,
    ChatAppLink,
    DashboardSnapshot,
    LearningPath,
    LearningPathStage,
    LearningResource,
    QuizQuestion,
    QuizSubmission,
    StudentProfile,
)


def test_python_protocol_schemas_accept_required_fixtures():
    app = CanvasApp(app_type="notes.session", title="Notes", position={"x": 0, "y": 0}, size={"width": 320, "height": 240})
    link = ChatAppLink(message_id="m", app_id=app.app_id, label="open")
    resource = LearningResource(type="document", title="Doc", target_topic="x", source_refs=[{"document_id": "d", "chunk_id": "c", "course_id": "ai-course"}], personalized_reason="fit")
    stage = LearningPathStage(title="Stage")
    path = LearningPath(title="Path", stages=[stage])
    dash = DashboardSnapshot(student_id="demo-student")
    step = AgentStep(run_id="r", step_order=1, agent_or_skill="tutor_agent")
    run = AgentRun(task_type="chat", steps=[step])
    question = QuizQuestion(prompt="Q", answer="A", explanation="E")
    submission = QuizSubmission(student_id="s", question_id=question.question_id, answer="A", is_correct=True)
    profile = StudentProfile(student_id="s")
    frame = CanvasFrame(frame_id="f", title="Frame", position={"x": 0, "y": 0}, size={"width": 1, "height": 1})
    connector = CanvasConnector(connector_id="c", source_app_id="a", target_app_id="b", label="rel", relation="supports")
    assert app.app_id and link.link_id and resource.resource_id and path.path_id
    assert dash.student_id and run.run_id and submission.submission_id and profile.student_id and frame.frame_id and connector.connector_id
