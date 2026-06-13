from __future__ import annotations

import io
from uuid import uuid4
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.onboarding import parse_profile_upload


client = TestClient(app)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_register_login_me_and_forbidden_mismatch():
    email = f"new-user-auth-{uuid4().hex[:8]}@example.com"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "display_name": "新用户"},
    )
    assert register.status_code == 200
    token = register.json()["token"]
    assert register.json()["student"]["profile_status"] in {"not_started", "collecting"}

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email

    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200
    assert login.json()["student"]["student_id"] == register.json()["student"]["student_id"]

    forbidden = client.get("/api/dashboard/another-student", headers=auth_headers(token))
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN_STUDENT_CONTEXT"


def test_registered_users_get_isolated_default_canvas_apps():
    first = client.post(
        "/api/auth/register",
        json={"email": f"canvas-a-{uuid4().hex[:8]}@example.com", "password": "secret123", "display_name": "画布 A"},
    )
    second = client.post(
        "/api/auth/register",
        json={"email": f"canvas-b-{uuid4().hex[:8]}@example.com", "password": "secret123", "display_name": "画布 B"},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    first_apps = client.get("/api/canvas/apps", headers=auth_headers(first.json()["token"]))
    second_apps = client.get("/api/canvas/apps", headers=auth_headers(second.json()["token"]))
    assert first_apps.status_code == 200
    assert second_apps.status_code == 200

    first_items = first_apps.json()["apps"]
    second_items = second_apps.json()["apps"]
    first_types = {item["app_type"] for item in first_items}
    assert {"profile.dashboard", "dashboard.learning", "resource.center"}.issubset(first_types)
    assert {"physics.work_energy_demo", "math.gradient_descent_demo", "knowledge.graph"}.issubset(first_types)

    first_ids = {item["app_id"] for item in first_items}
    second_ids = {item["app_id"] for item in second_items}
    assert first_ids
    assert second_ids
    assert first_ids.isdisjoint(second_ids)


def test_onboarding_collects_sources_messages_and_generates_profile():
    email = f"onboarding-user-{uuid4().hex[:8]}@example.com"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "display_name": "画像用户"},
    )
    assert register.status_code == 200
    token = register.json()["token"]
    headers = auth_headers(token)

    started = client.post("/api/onboarding/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["onboarding"]["status"] in {"collecting", "ready_to_generate"}

    source = client.post(
        "/api/onboarding/sources",
        headers=headers,
        json={
            "source_type": "school_info",
            "title": "学校信息",
            "school": "星河大学",
            "major": "软件工程",
            "grade": "大一",
            "text": "星河大学 软件工程 大一 每周 5 小时",
        },
    )
    assert source.status_code == 200
    assert source.json()["sources"]

    message = client.post(
        "/api/onboarding/message",
        headers=headers,
        json={"message": "我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码，想学神经网络，希望按小步练习推进。"},
    )
    assert message.status_code == 200
    assert any(item["memory_type"] == "profile" for item in message.json()["memories"])

    generated = client.post("/api/onboarding/generate-profile", headers=headers)
    assert generated.status_code == 200
    profile = generated.json()["profile"]
    filled = [value for value in profile.values() if value not in (None, "", [], {})]
    assert len(filled) >= 10
    assert profile["school"] == "星河大学"
    assert profile["major"] == "软件工程"
    assert generated.json()["profile_status"] == "completed"

    me = client.get("/api/auth/me", headers=headers)
    assert me.json()["student"]["profile_status"] == "completed"


def _zip_bytes(files: dict[str, str]) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return data.getvalue()


@pytest.mark.asyncio
async def test_onboarding_parsers_cover_csv_xlsx_docx_pdf_and_image_blocked():
    csv_result = await parse_profile_upload(
        data="课程,星期,时间,地点,老师\n高等数学,周一,1-2节,A101,王老师\n".encode("utf-8"),
        filename="schedule.csv",
        mime_type="text/csv",
        source_type=None,
    )
    assert csv_result["source_type"] == "schedule"
    assert csv_result["structured_payload"]["schedule"][0]["course"] == "高等数学"

    xlsx_bytes = _zip_bytes(
        {
            "xl/sharedStrings.xml": "<sst xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><si><t>课程</t></si><si><t>星期</t></si><si><t>线性代数</t></si><si><t>周二</t></si></sst>",
            "xl/worksheets/sheet1.xml": "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData><row><c t='s'><v>0</v></c><c t='s'><v>1</v></c></row><row><c t='s'><v>2</v></c><c t='s'><v>3</v></c></row></sheetData></worksheet>",
        }
    )
    xlsx_result = await parse_profile_upload(data=xlsx_bytes, filename="schedule.xlsx", mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert xlsx_result["source_type"] == "schedule"
    assert "线性代数" in str(xlsx_result["structured_payload"])

    docx_bytes = _zip_bytes(
        {
            "word/document.xml": "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>我喜欢图解和代码练习</w:t></w:r></w:p></w:body></w:document>"
        }
    )
    docx_result = await parse_profile_upload(data=docx_bytes, filename="profile.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "图解" in docx_result["extracted_text"]

    pdf_result = await parse_profile_upload(data=("%PDF-1.4 " + "数学推导弱 " * 40).encode("utf-8"), filename="profile.pdf", mime_type="application/pdf")
    assert pdf_result["source_type"] == "document"

    image_result = await parse_profile_upload(data=b"fake-image", filename="profile.png", mime_type="image/png")
    assert image_result["source_type"] == "image"
    assert image_result["parser_status"].startswith("blocked_ocr")
