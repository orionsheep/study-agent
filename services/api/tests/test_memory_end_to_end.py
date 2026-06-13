from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_profile_memory_and_dashboard_evidence():
    response = client.post(
        "/api/profile/extract",
        json={"student_id": "demo-student", "course_id": "ai-course", "conversation_id": "demo", "message": "我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码。"},
    )
    assert response.status_code == 200
    assert response.json()["memories"][0]["memory_type"] == "profile"
    dashboard = client.get("/api/dashboard/demo-student").json()
    assert dashboard["memory_evidence"]


def test_app_event_updates_memory():
    response = client.post("/api/canvas/apps/app-energy/events", json={"student_id": "demo-student", "event_type": "parameter_change", "payload": {"force": 12}})
    assert response.status_code == 200
    assert response.json()["memory"]["memory_type"] == "app_interaction"


def test_layout_event_updates_spatial_memory():
    response = client.post("/api/memory/layout-event", json={"student_id": "demo-student", "app_id": "app-gradient", "position": {"x": 10, "y": 20}})
    assert response.status_code == 200
    assert response.json()["memory"]["memory_type"] == "spatial_layout"


def test_quiz_updates_mastery_and_misconception():
    response = client.post("/api/quiz/quiz-q-gradient-lr/submit", json={"student_id": "demo-student", "answer": "稳定加速"})
    assert response.status_code == 200
    payload = response.json()["evaluation"]["payload"]
    assert payload["submission"]["is_correct"] is False
    assert any(memory["memory_type"] == "misconception" for memory in payload["memories"])
