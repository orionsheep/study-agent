from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.store import get_store
from app.main import app


pytestmark = pytest.mark.skipif(
    os.environ.get("LEARNFORGE_POSTGRES_INTEGRATION") != "1",
    reason="Postgres integration tests run only when LEARNFORGE_POSTGRES_INTEGRATION=1",
)


def test_postgres_auth_onboarding_memory_canvas_dashboard_core() -> None:
    assert os.environ["DATABASE_URL"].startswith(("postgres://", "postgresql://", "postgresql+psycopg://"))
    get_store.cache_clear()
    client = TestClient(app)

    email = f"pg-{uuid4().hex}@example.com"
    registered = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "display_name": "PG Smoke"},
    )
    assert registered.status_code == 200, registered.text
    auth = registered.json()
    token = auth["token"]
    student_id = auth["student"]["student_id"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).json()["student"]["student_id"] == student_id
    assert client.get("/api/dashboard/not-this-student", headers=headers).status_code == 403

    initial_apps = client.get("/api/canvas/apps", headers=headers)
    assert initial_apps.status_code == 200, initial_apps.text
    initial_types = {item["app_type"] for item in initial_apps.json()["apps"]}
    assert {"profile.dashboard", "dashboard.learning", "resource.center"}.issubset(initial_types)

    started = client.post("/api/onboarding/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["onboarding"]["status"] in {"collecting", "ready_to_generate"}

    school_source = client.post(
        "/api/onboarding/sources",
        headers=headers,
        json={
            "source_type": "school_info",
            "title": "学校信息",
            "school": "Postgres 测试大学",
            "major": "软件工程",
            "grade": "大一",
        },
    )
    assert school_source.status_code == 200, school_source.text
    assert school_source.json()["sources"]

    message = client.post(
        "/api/onboarding/message",
        headers=headers,
        json={
            "message": "我想系统学习机器学习，Python 基础一般，线性代数薄弱，喜欢图解和代码示例，每周 6 小时。"
        },
    )
    assert message.status_code == 200, message.text

    generated = client.post("/api/onboarding/generate-profile", headers=headers)
    assert generated.status_code == 200, generated.text
    payload = generated.json()
    assert payload["profile_status"] == "completed"
    assert payload["onboarding"]["status"] == "completed"
    profile = payload["profile"]
    for key in ["school", "major", "grade", "learning_goal", "weak_points", "preferred_resources"]:
        assert profile.get(key)

    memories = client.get(f"/api/memory/{student_id}", headers=headers)
    assert memories.status_code == 200, memories.text
    assert memories.json()["memories"]

    app_response = client.post(
        "/api/canvas/apps",
        headers=headers,
        json={
            "app_type": "notes.session",
            "title": "Postgres 核心验证笔记",
            "payload": {"body": "画像构建后创建画布 App"},
        },
    )
    assert app_response.status_code == 200, app_response.text
    app_id = app_response.json()["payload"]["app"]["app_id"]

    listed = client.get("/api/canvas/apps", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(item["app_id"] == app_id for item in listed.json()["apps"])

    dashboard = client.get(f"/api/dashboard/{student_id}", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["student_id"] == student_id
