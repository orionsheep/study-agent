from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_system_status_are_truthful():
    health = client.get("/health").json()
    assert health["components"]["backend"]["status"] == "ready"
    assert health["components"]["database"]["status"] == "ready"
    assert health["components"]["mimo"]["status"].startswith("blocked") or health["components"]["mimo"]["status"] == "ready"
    assert health["components"]["gemini"]["status"].startswith("blocked") or health["components"]["gemini"]["status"] == "ready"
    assert set(health["components"]["model_providers"]) == {"mimo", "gemini"}
    assert health["components"]["hermes"]["status"].startswith("blocked") or health["components"]["hermes"]["status"] == "ready"
    assert health["components"]["image2"]["status"].startswith("blocked") or health["components"]["image2"]["status"] == "ready"
    if not any(status["status"] == "ready" for status in health["components"]["model_providers"].values()):
        assert health["status"] != "ready"


def test_required_api_routes_exist():
    paths = {route.path for route in app.routes}
    required = {
        "/health",
        "/api/system/status",
        "/api/chat/stream",
        "/api/chat/message",
        "/api/courses",
        "/api/courses/{course_id}/documents",
        "/api/courses/{course_id}/ingest",
        "/api/courses/{course_id}/knowledge-graph",
        "/api/profile/extract",
        "/api/profile/{student_id}",
        "/api/learning-path/generate",
        "/api/learning-path/{path_id}",
        "/api/resources",
        "/api/resources/generate",
        "/api/resources/{resource_id}",
        "/api/quiz/{quiz_id}/submit",
        "/api/canvas/apps",
        "/api/canvas/apps/{app_id}",
        "/api/canvas/apps/{app_id}/events",
        "/api/canvas/applink/{link_id}/open",
        "/api/dashboard/{student_id}",
        "/api/agent-runs/{run_id}",
        "/api/memory/{student_id}",
        "/api/memory/search",
        "/api/images/generate",
    }
    assert required.issubset(paths)
