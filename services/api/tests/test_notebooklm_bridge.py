from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.cram.openstax_seed import OPENSTAX_CRAM_BOOKS
from app.notebooklm_service import OpenNotebookBridge, is_binary_like_source_text, notebook_key, sanitize_notebook_sources
from app.database.store import get_store
from app.schemas.app_protocol import CanvasApp, CanvasPosition, CanvasSize, utc_now


client = TestClient(app)


def ensure_test_identity(student_id: str, course_id: str = "ai-course") -> None:
    store = get_store()
    now = utc_now()
    if store.__class__.__name__ == "PostgresLearningStore":
        store.execute(
            "INSERT INTO students(id,display_name,created_at,updated_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (student_id, student_id, now, now),
        )
        store.execute(
            "INSERT INTO courses(id,title,description,created_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (course_id, course_id, "NotebookLM bridge test course.", now),
        )
        return
    store.execute(
        "INSERT OR IGNORE INTO students(id, display_name, created_at, updated_at) VALUES(?,?,?,?)",
        (student_id, student_id, now, now),
    )
    store.execute(
        "INSERT OR IGNORE INTO courses(id, title, description, created_at) VALUES(?,?,?,?)",
        (course_id, course_id, "NotebookLM bridge test course.", now),
    )


@pytest.mark.asyncio
async def test_notebooklm_status_offline_is_blocked(monkeypatch):
    class FailingAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, url: str):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.notebooklm_service.httpx.AsyncClient", FailingAsyncClient)

    result = await OpenNotebookBridge().status()

    assert result["status"] == "blocked_sidecar_unreachable"
    assert result["provider"] == "open_notebook"
    assert "embed=learnforge&mode=sources" in result["embed_url"]


@pytest.mark.asyncio
async def test_notebooklm_bootstrap_is_stable_for_student_course(monkeypatch):
    async def fake_status(self):
        return {"status": "ready", "provider": "open_notebook"}

    async def fake_post_first_json(self, paths, payload):
        return {"status": "ready", "path": paths[0], "data": {"id": payload["external_id"]}}

    monkeypatch.setattr(OpenNotebookBridge, "status", fake_status)
    monkeypatch.setattr(OpenNotebookBridge, "_post_first_json", fake_post_first_json)

    first = await OpenNotebookBridge().bootstrap(student_id="stu-a", course_id="course-a")
    second = await OpenNotebookBridge().bootstrap(student_id="stu-a", course_id="course-a")

    assert first["status"] == "ready"
    assert first["notebook_id"] == notebook_key("stu-a", "course-a")
    assert second["notebook_id"] == first["notebook_id"]
    assert "embed=learnforge&mode=sources" in first["embed_url"]


@pytest.mark.asyncio
async def test_notebooklm_retrieve_returns_chunks_not_answer(monkeypatch):
    async def fake_bootstrap(self, *, student_id: str, course_id: str):
        return {"status": "ready", "notebook_id": notebook_key(student_id, course_id)}

    async def fake_post_first_json(self, paths, payload):
        return {
            "status": "ready",
            "path": paths[0],
            "data": {
                "chunks": [{"title": "Source A", "content": "grounded source text"}],
                "citations": [{"source_id": "src-a", "chunk_id": "chunk-a", "title": "Source A"}],
            },
        }

    monkeypatch.setattr(OpenNotebookBridge, "bootstrap", fake_bootstrap)
    monkeypatch.setattr(OpenNotebookBridge, "_post_first_json", fake_post_first_json)

    result = await OpenNotebookBridge().retrieve(
        student_id="stu-a",
        course_id="course-a",
        query="Explain this source",
    )

    assert result["status"] == "ready"
    assert result["chunks"][0]["content"] == "grounded source text"
    assert result["citations"][0]["chunk_id"] == "chunk-a"
    assert result["answer"] is None


@pytest.mark.asyncio
async def test_notebooklm_retrieve_drops_citations_without_real_chunks(monkeypatch):
    async def fake_bootstrap(self, *, student_id: str, course_id: str):
        return {"status": "ready", "notebook_id": notebook_key(student_id, course_id)}

    async def fake_post_first_json(self, paths, payload):
        return {
            "status": "ready",
            "path": paths[0],
            "data": {
                "chunks": [],
                "citations": [{"source_id": "src-a", "chunk_id": "chunk-a", "title": "Source A"}],
            },
        }

    monkeypatch.setattr(OpenNotebookBridge, "bootstrap", fake_bootstrap)
    monkeypatch.setattr(OpenNotebookBridge, "_post_first_json", fake_post_first_json)

    result = await OpenNotebookBridge().retrieve(
        student_id="stu-no-chunks",
        course_id="course-no-chunks",
        query="Explain this source",
    )

    assert result["chunks"] == []
    assert result["citations"] == []


def test_notebooklm_source_quality_gate_filters_binary_pdf_refs():
    sources = [
        {
            "id": "source-bad",
            "title": "坏 PDF",
            "summary": "%PDF-1.7 1 0 obj <</Type/Page/Resources<</Font/F0>>>> endobj",
            "source_refs": [
                {"document_id": "doc-bad", "chunk_id": "chunk-bad", "snippet": "%PDF-1.7 2 0 obj <</XObject>> endobj"},
                {"document_id": "doc-good", "chunk_id": "chunk-good", "snippet": "这一段是可引用的课程讲义文本。"},
            ],
        }
    ]

    cleaned = sanitize_notebook_sources(sources)

    assert is_binary_like_source_text("%PDF-1.7 1 0 obj <</Type/Pages>> endobj")
    assert cleaned[0]["summary"] == ""
    assert cleaned[0]["source_refs"] == [{"document_id": "doc-good", "chunk_id": "chunk-good", "snippet": "这一段是可引用的课程讲义文本。"}]


def test_notebooklm_publish_blocks_without_sources():
    response = client.post(
        "/api/notebooklm/publish",
        json={
            "student_id": "stu-publish",
            "course_id": "course-publish",
            "kind": "study_guide",
            "title": "No sources",
            "content": {"summary": "missing citations"},
            "source_refs": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["status"] == "blocked_missing_sources"


def test_notebooklm_sources_lists_course_documents():
    response = client.get(
        "/api/notebooklm/sources",
        headers={"X-Student-Id": "demo-student", "X-Course-Id": "ai-course"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"]
    assert payload["sources"][0]["source_refs"]


def test_notebooklm_notebooks_include_course_and_personal_defaults():
    response = client.get(
        "/api/notebooklm/notebooks",
        headers={"X-Student-Id": "demo-student", "X-Course-Id": "ai-course"},
    )

    assert response.status_code == 200
    purposes = {item["purpose"] for item in response.json()["notebooks"]}
    assert "course_official" in purposes
    assert "personal_review" in purposes


def test_notebooklm_course_knowledge_base_includes_default_openstax_books():
    notebooks = client.get(
        "/api/notebooklm/notebooks",
        headers={"X-Student-Id": "demo-student", "X-Course-Id": "ai-course"},
    ).json()["notebooks"]
    course_notebook = next(item for item in notebooks if item["purpose"] == "course_official")

    sources = client.get(
        f"/api/notebooklm/notebooks/{course_notebook['id']}/sources",
        headers={"X-Student-Id": "demo-student", "X-Course-Id": "ai-course"},
    ).json()["sources"]
    openstax_sources = [
        item for item in sources
        if str(item.get("metadata", {}).get("provider") or "") == "openstax"
    ]

    assert len(openstax_sources) >= min(20, len(OPENSTAX_CRAM_BOOKS))
    assert any(item["metadata"].get("source_id") == "openstax:principles-management" for item in openstax_sources)
    assert all(item["source_scope"] == "course_official" for item in openstax_sources)
    assert all(item["file_url"] and item["original_url"] for item in openstax_sources)


def test_notebooklm_event_records_real_canvas_app_id_from_payload():
    ensure_test_identity("stu-nblm-event")
    app_model = CanvasApp(
        app_id="app-nblm-event",
        app_type="notebooklm.workspace",
        title="NotebookLM",
        icon="BookOpen",
        position=CanvasPosition(x=0, y=0),
        size=CanvasSize(width=720, height=520),
    )
    get_store().save_app(app_model, student_id="stu-nblm-event", course_id="ai-course")

    response = client.post(
        "/api/notebooklm/events",
        headers={"X-Student-Id": "stu-nblm-event", "X-Course-Id": "ai-course"},
        json={
            "event_type": "notebooklm.context_select",
            "payload": {
                "app_id": "app-nblm-event",
                "source_id": "openstax:principles-management",
                "source_title": "Principles of Management",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "recorded"
    assert payload["event"]["app_id"] == "app-nblm-event"


def test_notebooklm_text_upload_defaults_to_personal_notebook(monkeypatch):
    async def fake_sync(self, *, student_id: str, course_id: str, learnforge_notebook_id: str):
        return {"status": "blocked_sidecar_unreachable", "synced": [], "blocked": True, "learnforge_notebook_id": learnforge_notebook_id}

    monkeypatch.setattr(OpenNotebookBridge, "sync_notebook_sources", fake_sync)
    ensure_test_identity("stu-nblm-upload")
    notebooks = client.get(
        "/api/notebooklm/notebooks",
        headers={"X-Student-Id": "stu-nblm-upload", "X-Course-Id": "ai-course"},
    ).json()["notebooks"]
    personal = next(item for item in notebooks if item["purpose"] == "personal_review")

    response = client.post(
        f"/api/notebooklm/notebooks/{personal['id']}/sources/text",
        headers={"X-Student-Id": "stu-nblm-upload", "X-Course-Id": "ai-course"},
        json={"title": "我的复习材料", "content": "第一段材料。\n\n第二段材料。", "sync": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "saved_not_synced"
    assert payload["source"]["source_scope"] == "personal_notebook"
    sources = client.get(
        f"/api/notebooklm/notebooks/{personal['id']}/sources",
        headers={"X-Student-Id": "stu-nblm-upload", "X-Course-Id": "ai-course"},
    ).json()["sources"]
    assert any(item["title"] == "我的复习材料" and item["source_scope"] == "personal_notebook" for item in sources)
    course_notebook = next(item for item in notebooks if item["purpose"] == "course_official")
    official_sources = get_store().list_notebook_sources(course_notebook["id"], student_id="stu-nblm-upload", course_id="ai-course")
    assert all(item["title"] != "我的复习材料" for item in official_sources)


def test_notebooklm_link_upload_saves_source(monkeypatch):
    async def fake_fetch(url: str):
        return {
            "source_type": "url",
            "title": "链接标题",
            "raw_text": url,
            "extracted_text": "链接正文材料",
            "structured_payload": {"url": url},
            "parser_status": "parsed",
            "parser_reason": None,
        }

    async def fake_sync(self, *, student_id: str, course_id: str, learnforge_notebook_id: str):
        return {"status": "ready", "synced": [{"document_id": "x"}], "blocked": [], "learnforge_notebook_id": learnforge_notebook_id}

    monkeypatch.setattr("app.notebooklm_service.fetch_url_source", fake_fetch)
    monkeypatch.setattr(OpenNotebookBridge, "sync_notebook_sources", fake_sync)
    ensure_test_identity("stu-nblm-link")
    notebooks = client.get(
        "/api/notebooklm/notebooks",
        headers={"X-Student-Id": "stu-nblm-link", "X-Course-Id": "ai-course"},
    ).json()["notebooks"]
    personal = next(item for item in notebooks if item["purpose"] == "personal_review")

    response = client.post(
        f"/api/notebooklm/notebooks/{personal['id']}/sources/link",
        headers={"X-Student-Id": "stu-nblm-link", "X-Course-Id": "ai-course"},
        json={"url": "https://example.com/lesson", "sync": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["source"]["ingest_type"] == "link"
    assert payload["source"]["original_url"] == "https://example.com/lesson"


def test_notebooklm_file_upload_saves_original_and_source(monkeypatch):
    async def fake_sync(self, *, student_id: str, course_id: str, learnforge_notebook_id: str):
        return {"status": "ready", "synced": [{"document_id": "x"}], "blocked": [], "learnforge_notebook_id": learnforge_notebook_id}

    monkeypatch.setattr(OpenNotebookBridge, "sync_notebook_sources", fake_sync)
    ensure_test_identity("stu-nblm-file")
    notebooks = client.get(
        "/api/notebooklm/notebooks",
        headers={"X-Student-Id": "stu-nblm-file", "X-Course-Id": "ai-course"},
    ).json()["notebooks"]
    personal = next(item for item in notebooks if item["purpose"] == "personal_review")

    response = client.post(
        f"/api/notebooklm/notebooks/{personal['id']}/sources/upload",
        headers={
            "X-Student-Id": "stu-nblm-file",
            "X-Course-Id": "ai-course",
            "Content-Type": "text/plain",
            "X-Filename": "note.txt",
        },
        content=b"NotebookLM upload text",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["ingest_type"] == "file_upload"
    assert payload["source"]["metadata"]["artifact_id"]
    assert payload["source"]["metadata"]["object_key"]


def test_notebooklm_publish_preserves_source_metadata():
    ensure_test_identity("stu-publish", "course-publish")
    source_refs = [{"source_id": "src-1", "chunk_id": "chunk-1", "title": "Verified Source"}]
    response = client.post(
        "/api/notebooklm/publish",
        json={
            "student_id": "stu-publish",
            "course_id": "course-publish",
            "kind": "flashcards",
            "title": "来源闪卡",
            "content": {"cards": [{"front": "Q", "back": "A"}]},
            "source_refs": source_refs,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "published"
    assert payload["resource"]["source_refs"] == source_refs
    assert payload["resource"]["content"]["notebooklm_kind"] == "flashcards"
