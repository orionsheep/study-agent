from __future__ import annotations

import hashlib
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.database.store import get_store, stable_id
from app.onboarding import fetch_url_source, parse_profile_upload
from app.rag.chunker import TextChunker
from app.schemas.app_protocol import LearningResource, new_id
from app.storage.artifacts import ObjectStorage, artifact_object_key


NOTEBOOKLM_TRANSFORM_KINDS = {"summary", "study_guide", "quiz", "flashcards", "podcast", "audio_overview", "notes"}


def notebook_key(student_id: str, course_id: str) -> str:
    return stable_id("onb", f"{student_id}:{course_id}")


def notebook_external_key(student_id: str, course_id: str, learnforge_notebook_id: str) -> str:
    return stable_id("onb", f"{student_id}:{course_id}:{learnforge_notebook_id}")


def notebook_embed_url(notebook_id: str | None = None) -> str:
    settings = get_settings()
    base = settings.open_notebook_web_url.rstrip("/")
    query = "embed=learnforge&mode=sources"
    if notebook_id:
        query = f"{query}&notebook_id={notebook_id}"
    return f"{base}?{query}"


def _resource_type_for_transform(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized == "quiz":
        return "quiz"
    if normalized == "study_guide":
        return "reading"
    return "notes"


def _title_for_transform(kind: str, title: str | None) -> str:
    if title and title.strip():
        return title.strip()
    labels = {
        "summary": "NotebookLM 来源总结",
        "study_guide": "NotebookLM 学习指南",
        "quiz": "NotebookLM 来源测验",
        "flashcards": "NotebookLM 闪卡",
        "podcast": "NotebookLM 音频概览",
        "audio_overview": "NotebookLM 音频概览",
        "notes": "NotebookLM 来源笔记",
    }
    return labels.get(kind.strip().lower(), "NotebookLM 来源产物")


def _compact_chunks(text: str, *, size: int = 900) -> list[str]:
    cleaned = str(text or "").strip()
    if not cleaned:
        return []
    return TextChunker().chunk(cleaned, size=size) or [cleaned]


_BINARY_SOURCE_PATTERN = re.compile(r"%PDF-\d|endobj\b|/\s*Type\s*/\s*Page\b|/\s*Font\b|/\s*XObject\b|xref\b|trailer\b", re.I)


def is_binary_like_source_text(text: Any) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    sample = value[:800]
    if _BINARY_SOURCE_PATTERN.search(sample):
        return True
    control_count = sum(1 for ch in sample if (ord(ch) < 32 and ch not in "\n\r\t") or ch == "\ufffd")
    return control_count / max(1, len(sample)) >= 0.02


def _usable_source_ref(ref: dict[str, Any]) -> bool:
    text = ref.get("snippet") or ref.get("quote") or ref.get("content") or ref.get("text")
    if str(text or "").strip():
        return not is_binary_like_source_text(text)
    return bool(ref.get("chunk_id") or ref.get("document_id") or ref.get("source_id"))


def sanitize_notebook_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for source in sources:
        item = dict(source)
        refs = item.get("source_refs") if isinstance(item.get("source_refs"), list) else []
        item["source_refs"] = [ref for ref in refs if isinstance(ref, dict) and _usable_source_ref(ref)]
        if is_binary_like_source_text(item.get("summary")):
            item["summary"] = ""
        if not item["source_refs"] and not item.get("summary"):
            item["quality_status"] = "blocked_no_usable_text"
        cleaned.append(item)
    return cleaned


def _document_source_ref(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": source.get("document_id") or source.get("id") or source.get("source_id"),
        "course_id": source.get("course_id"),
        "title": source.get("title"),
        "source_scope": source.get("source_scope"),
        "ingest_type": source.get("ingest_type"),
        "original_url": source.get("original_url"),
        "upload_status": source.get("upload_status"),
    }


class OpenNotebookBridge:
    """Thin adapter around Open Notebook.

    Open Notebook is treated as a source/search/transformation sidecar. This adapter
    never fabricates NotebookLM answers; if the sidecar is unavailable or an API
    surface is unsupported it returns an honest blocked status.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_url = self.settings.open_notebook_api_url.rstrip("/")
        self.timeout = httpx.Timeout(float(self.settings.open_notebook_timeout_seconds))

    def _headers(self) -> dict[str, str]:
        password = self.settings.open_notebook_password.strip()
        if not password:
            return {}
        return {"Authorization": f"Bearer {password}"}

    async def status(self) -> dict[str, Any]:
        if self.settings.notebooklm_provider.strip().lower() != "open_notebook":
            return {
                "status": "blocked_provider_disabled",
                "provider": self.settings.notebooklm_provider,
                "reason": "NOTEBOOKLM_PROVIDER is not open_notebook.",
                "web_url": self.settings.open_notebook_web_url,
                "api_url": self.api_url,
                "embed_url": notebook_embed_url(),
            }
        probes = ["/health", "/api/health", "/openapi.json", "/docs"]
        last_error = ""
        headers = self._headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for path in probes:
                try:
                    response = await client.get(f"{self.api_url}{path}", headers=headers)
                    if response.status_code < 500:
                        return {
                            "status": "ready",
                            "provider": "open_notebook",
                            "reason": f"Open Notebook API responded at {path}.",
                            "web_url": self.settings.open_notebook_web_url,
                            "api_url": self.api_url,
                            "embed_url": notebook_embed_url(),
                            "health_path": path,
                        }
                    last_error = f"HTTP {response.status_code} at {path}"
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
        return {
            "status": "blocked_sidecar_unreachable",
            "provider": "open_notebook",
            "reason": last_error or "Open Notebook API did not respond.",
            "web_url": self.settings.open_notebook_web_url,
            "api_url": self.api_url,
            "embed_url": notebook_embed_url(),
        }

    async def bootstrap_notebook(self, *, student_id: str, course_id: str, learnforge_notebook_id: str) -> dict[str, Any]:
        store = get_store()
        notebook = store.get_notebook(learnforge_notebook_id, student_id=student_id, course_id=course_id)
        if not notebook:
            return {
                "status": "blocked_notebook_missing",
                "reason": f"Notebook {learnforge_notebook_id} is not assigned to this student/course.",
                "notebook_id": learnforge_notebook_id,
                "embed_url": notebook_embed_url(),
            }
        health = await self.status()
        if health["status"] != "ready":
            external_id = notebook_external_key(student_id, course_id, learnforge_notebook_id)
            return {**health, "notebook_id": external_id, "learnforge_notebook_id": learnforge_notebook_id, "embed_url": notebook_embed_url(external_id)}

        existing_open_id = str(notebook.get("open_notebook_id") or "")
        if existing_open_id:
            existing = await self._get_json("/api/notebooks")
            existing_data = existing.get("data")
            if isinstance(existing_data, list) and any(str(item.get("id") or "") == existing_open_id for item in existing_data if isinstance(item, dict)):
                return {
                    "status": "ready",
                    "provider": "open_notebook",
                    "notebook_id": existing_open_id,
                    "learnforge_notebook_id": learnforge_notebook_id,
                    "external_id": notebook_external_key(student_id, course_id, learnforge_notebook_id),
                    "embed_url": notebook_embed_url(existing_open_id),
                    "api_path": existing.get("path"),
                    "data": notebook,
                }
            store.set_notebook_open_notebook_id(learnforge_notebook_id, "", "not_synced")

        external_id = notebook_external_key(student_id, course_id, learnforge_notebook_id)
        notebook_name = f"LearnForge {notebook.get('title') or learnforge_notebook_id} ({external_id})"
        existing = await self._get_json("/api/notebooks")
        existing_data = existing.get("data")
        if isinstance(existing_data, list):
            for item in existing_data:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "")
                description = str(item.get("description") or "")
                if name == notebook_name or external_id in description:
                    open_id = str(item.get("id") or external_id)
                    store.set_notebook_open_notebook_id(learnforge_notebook_id, open_id, "ready")
                    return {
                        "status": "ready",
                        "provider": "open_notebook",
                        "notebook_id": open_id,
                        "learnforge_notebook_id": learnforge_notebook_id,
                        "external_id": external_id,
                        "embed_url": notebook_embed_url(open_id),
                        "api_path": existing.get("path"),
                        "data": item,
                    }

        payload = {
            "name": notebook_name,
            "title": notebook_name,
            "description": (
                f"LearnForge Notebook library external_id={external_id} "
                f"student_id={student_id} course_id={course_id} learnforge_notebook_id={learnforge_notebook_id}"
            ),
            "external_id": external_id,
        }
        created = await self._post_first_json(["/api/notebooks", "/notebooks", "/api/notebook", "/notebook"], payload)
        if created["status"] != "ready":
            return {**created, "notebook_id": external_id, "learnforge_notebook_id": learnforge_notebook_id, "embed_url": notebook_embed_url(external_id)}
        data = created.get("data") if isinstance(created.get("data"), dict) else {}
        open_id = str(data.get("id") or data.get("notebook_id") or external_id)
        store.set_notebook_open_notebook_id(learnforge_notebook_id, open_id, "ready")
        return {
            "status": "ready",
            "provider": "open_notebook",
            "notebook_id": open_id,
            "learnforge_notebook_id": learnforge_notebook_id,
            "external_id": external_id,
            "embed_url": notebook_embed_url(open_id),
            "api_path": created.get("path"),
            "data": data,
        }

    async def _post_first_json(self, paths: list[str], payload: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        headers = self._headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for path in paths:
                try:
                    response = await client.post(f"{self.api_url}{path}", json=payload, headers=headers)
                    if response.status_code in {200, 201, 202}:
                        return {
                            "status": "ready",
                            "path": path,
                            "data": response.json() if response.content else {},
                        }
                    errors.append(f"{path}: HTTP {response.status_code}")
                except Exception as exc:
                    errors.append(f"{path}: {type(exc).__name__}")
        return {
            "status": "blocked_unsupported_api",
            "reason": "; ".join(errors[-5:]) or "No Open Notebook endpoint accepted the request.",
        }

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = self._headers()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.api_url}{path}", params=params, headers=headers)
            if response.status_code in {200, 201, 202}:
                return {"status": "ready", "path": path, "data": response.json() if response.content else {}}
            return {"status": "blocked_unsupported_api", "reason": f"{path}: HTTP {response.status_code}"}
        except Exception as exc:
            return {"status": "blocked_unsupported_api", "reason": f"{path}: {type(exc).__name__}"}

    async def bootstrap(self, *, student_id: str, course_id: str) -> dict[str, Any]:
        health = await self.status()
        nb_id = notebook_key(student_id, course_id)
        if health["status"] != "ready":
            return {**health, "notebook_id": nb_id, "embed_url": notebook_embed_url(nb_id)}
        notebook_name = f"LearnForge {course_id} ({nb_id})"
        existing = await self._get_json("/api/notebooks")
        existing_data = existing.get("data")
        if isinstance(existing_data, list):
            for item in existing_data:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "")
                description = str(item.get("description") or "")
                if name == notebook_name or nb_id in description:
                    notebook_id = str(item.get("id") or nb_id)
                    return {
                        "status": "ready",
                        "provider": "open_notebook",
                        "notebook_id": notebook_id,
                        "external_id": nb_id,
                        "embed_url": notebook_embed_url(notebook_id),
                        "api_path": existing.get("path"),
                        "data": item,
                    }
        payload = {
            "name": notebook_name,
            "title": notebook_name,
            "description": f"LearnForge NotebookLM bridge external_id={nb_id} student_id={student_id} course_id={course_id}",
            "external_id": nb_id,
        }
        created = await self._post_first_json(
            ["/api/notebooks", "/notebooks", "/api/notebook", "/notebook"],
            payload,
        )
        if created["status"] != "ready":
            return {**created, "notebook_id": nb_id, "embed_url": notebook_embed_url(nb_id)}
        data = created.get("data") if isinstance(created.get("data"), dict) else {}
        return {
            "status": "ready",
            "provider": "open_notebook",
            "notebook_id": str(data.get("id") or data.get("notebook_id") or nb_id),
            "external_id": nb_id,
            "embed_url": notebook_embed_url(str(data.get("id") or data.get("notebook_id") or nb_id)),
            "api_path": created.get("path"),
            "data": data,
        }

    def _require_notebook(self, *, student_id: str, course_id: str, learnforge_notebook_id: str) -> dict[str, Any]:
        store = get_store()
        notebook = store.get_notebook(learnforge_notebook_id, student_id=student_id, course_id=course_id)
        if notebook:
            return notebook
        defaults = store.ensure_default_notebooks(student_id=student_id, course_id=course_id)
        notebook = next((item for item in defaults if item.get("id") == learnforge_notebook_id), None)
        if not notebook:
            raise ValueError("notebook_not_found")
        return notebook

    async def repair_notebook_sources(self, *, student_id: str, course_id: str, learnforge_notebook_id: str) -> None:
        store = get_store()
        for source in store.list_notebook_sources(learnforge_notebook_id, student_id=student_id, course_id=course_id):
            await self._repair_source_if_needed(source, student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)

    async def _repair_source_if_needed(
        self,
        source: dict[str, Any],
        *,
        student_id: str,
        course_id: str,
        learnforge_notebook_id: str,
    ) -> None:
        source_id = str(source.get("source_id") or source.get("id") or "")
        if not source_id or str(source.get("parser") or "") != "notebooklm_file":
            return
        store = get_store()
        chunks = store.list_document_chunks(course_id, source_id)
        if any(not is_binary_like_source_text(chunk.get("content")) for chunk in chunks):
            return
        metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
        artifact_id = str(metadata.get("artifact_id") or "").strip()
        object_key = str(metadata.get("object_key") or "").strip()
        if not object_key and artifact_id:
            artifact = store.get_artifact(artifact_id) if hasattr(store, "get_artifact") else None
            if artifact:
                object_key = str(artifact.get("object_key") or "")
        if not object_key:
            return
        try:
            raw, content_type = ObjectStorage().get_bytes(object_key)
        except Exception:
            return
        parsed = await parse_profile_upload(
            data=raw,
            filename=str(metadata.get("filename") or source.get("title") or "notebooklm-source"),
            mime_type=str(source.get("mime_type") or content_type or "application/octet-stream"),
            source_type="document",
        )
        text = str(parsed.get("extracted_text") or parsed.get("raw_text") or "").strip()
        chunks = [chunk for chunk in _compact_chunks(text) if not is_binary_like_source_text(chunk)]
        parser_status = str(parsed.get("parser_status") or ("parsed" if chunks else "blocked_parser_limited"))
        store.save_course_document_from_chunks(
            course_id=course_id,
            title=str(source.get("title") or parsed.get("title") or "NotebookLM 来源"),
            chunks=chunks,
            file_url=source.get("file_url"),
            parser="notebooklm_file",
            document_id=source_id,
            ingest_type=str(source.get("ingest_type") or "file_upload"),
            owner_scope=str(source.get("owner_scope") or "user"),
            owner_id=str(source.get("owner_id") or student_id),
            source_scope=str(source.get("source_scope") or "personal_notebook"),
            mime_type=source.get("mime_type"),
            upload_status="ready" if chunks else parser_status,
            metadata={
                **metadata,
                "repair_status": "reparsed" if chunks else "blocked_parser_limited",
                "parser_status": parser_status,
                "parser_reason": parsed.get("parser_reason"),
                "learnforge_notebook_id": learnforge_notebook_id,
            },
        )

    async def ingest_text_source(
        self,
        *,
        student_id: str,
        course_id: str,
        learnforge_notebook_id: str,
        title: str,
        content: str,
        sync: bool = True,
    ) -> dict[str, Any]:
        self._require_notebook(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)
        chunks = _compact_chunks(content)
        if not chunks:
            return {"status": "blocked_empty_source", "reason": "Text source content is empty.", "source": None}
        document_id = stable_id("doc-nblm-text", f"{course_id}:{learnforge_notebook_id}:{title}:{content}")
        saved = get_store().save_course_document_from_chunks(
            course_id=course_id,
            title=title or "粘贴文本",
            chunks=chunks,
            parser="notebooklm_text",
            document_id=document_id,
            ingest_type="text",
            owner_scope="user",
            owner_id=student_id,
            source_scope="personal_notebook",
            upload_status="ready",
            metadata={"learnforge_notebook_id": learnforge_notebook_id, "source_channel": "notebooklm_text"},
        )
        attach = get_store().attach_document_to_notebook(
            notebook_id=learnforge_notebook_id,
            document_id=str(saved["document_id"]),
            student_id=student_id,
            course_id=course_id,
            source_role="personal",
        )
        sync_result = await self.sync_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id) if sync else {"status": "not_synced"}
        return {"status": "ready" if sync_result.get("status") == "ready" else "saved_not_synced", "source": saved, "attachment": attach, "sync": sync_result}

    async def ingest_link_source(
        self,
        *,
        student_id: str,
        course_id: str,
        learnforge_notebook_id: str,
        url: str,
        title: str | None = None,
        sync: bool = True,
    ) -> dict[str, Any]:
        self._require_notebook(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)
        parsed = await fetch_url_source(url)
        source_title = (title or str(parsed.get("title") or url)).strip() or url
        text = str(parsed.get("extracted_text") or "").strip()
        chunks = _compact_chunks(text)
        status = str(parsed.get("parser_status") or ("ready" if chunks else "blocked_fetch_error"))
        document_id = stable_id("doc-nblm-link", f"{course_id}:{learnforge_notebook_id}:{url}")
        saved = get_store().save_course_document_from_chunks(
            course_id=course_id,
            title=source_title,
            chunks=chunks,
            file_url=url,
            parser="notebooklm_link",
            document_id=document_id,
            ingest_type="link",
            owner_scope="user",
            owner_id=student_id,
            source_scope="personal_notebook",
            original_url=url,
            upload_status="ready" if chunks else status,
            metadata={
                "learnforge_notebook_id": learnforge_notebook_id,
                "source_channel": "notebooklm_link",
                "parser_status": status,
                "parser_reason": parsed.get("parser_reason"),
                "structured_payload": parsed.get("structured_payload") if isinstance(parsed.get("structured_payload"), dict) else {},
            },
        )
        attach = get_store().attach_document_to_notebook(
            notebook_id=learnforge_notebook_id,
            document_id=str(saved["document_id"]),
            student_id=student_id,
            course_id=course_id,
            source_role="personal",
        )
        sync_result = await self.sync_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id) if sync else {"status": "not_synced"}
        return {"status": "ready" if sync_result.get("status") == "ready" else "saved_not_synced", "source": saved, "attachment": attach, "sync": sync_result, "fetch": parsed}

    async def ingest_file_source(
        self,
        *,
        student_id: str,
        course_id: str,
        learnforge_notebook_id: str,
        filename: str,
        data: bytes,
        mime_type: str | None = None,
        title: str | None = None,
        sync: bool = True,
    ) -> dict[str, Any]:
        self._require_notebook(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)
        if not data:
            return {"status": "blocked_empty_source", "reason": "Uploaded file is empty.", "source": None}
        digest = hashlib.sha256(data).hexdigest()
        artifact_id = stable_id("artifact-nblm", f"{student_id}:{course_id}:{learnforge_notebook_id}:{filename}:{digest}")
        object_key = artifact_object_key(kind="notebooklm.source", artifact_id=artifact_id, filename=filename)
        stored = ObjectStorage().put_bytes(object_key=object_key, data=data, content_type=mime_type or "application/octet-stream")
        get_store().save_artifact(
            artifact_id=artifact_id,
            kind="notebooklm.source",
            object_key=stored.object_key,
            content_type=stored.content_type,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            title=title or filename,
            student_id=student_id,
            course_id=course_id,
            metadata={"upload_status": "ready", "filename": filename, "learnforge_notebook_id": learnforge_notebook_id},
        )
        parsed = await parse_profile_upload(data=data, filename=filename, mime_type=mime_type, source_type="document")
        source_title = (title or str(parsed.get("title") or filename)).strip() or filename
        text = str(parsed.get("extracted_text") or parsed.get("raw_text") or "").strip()
        chunks = _compact_chunks(text)
        parser_status = str(parsed.get("parser_status") or ("ready" if chunks else "blocked_parser_limited"))
        document_id = stable_id("doc-nblm-file", f"{course_id}:{learnforge_notebook_id}:{filename}:{digest}")
        saved = get_store().save_course_document_from_chunks(
            course_id=course_id,
            title=source_title,
            chunks=chunks,
            file_url=f"/api/artifacts/{artifact_id}/content",
            parser="notebooklm_file",
            document_id=document_id,
            ingest_type="file_upload",
            owner_scope="user",
            owner_id=student_id,
            source_scope="personal_notebook",
            mime_type=mime_type,
            upload_status="ready" if chunks else parser_status,
            metadata={
                "learnforge_notebook_id": learnforge_notebook_id,
                "source_channel": "notebooklm_file",
                "artifact_id": artifact_id,
                "object_key": stored.object_key,
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "filename": filename,
                "parser_status": parser_status,
                "parser_reason": parsed.get("parser_reason"),
            },
        )
        attach = get_store().attach_document_to_notebook(
            notebook_id=learnforge_notebook_id,
            document_id=str(saved["document_id"]),
            student_id=student_id,
            course_id=course_id,
            source_role="personal",
        )
        sync_result = await self.sync_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id) if sync else {"status": "not_synced"}
        return {"status": "ready" if sync_result.get("status") == "ready" else "saved_not_synced", "source": saved, "attachment": attach, "sync": sync_result, "artifact_id": artifact_id, "parser": parsed}

    async def sync_course_sources(self, *, student_id: str, course_id: str) -> dict[str, Any]:
        notebooks = get_store().ensure_default_notebooks(student_id=student_id, course_id=course_id)
        course_notebook = next((item for item in notebooks if item.get("purpose") == "course_official"), None)
        if course_notebook:
            return await self.sync_notebook_sources(
                student_id=student_id,
                course_id=course_id,
                learnforge_notebook_id=str(course_notebook["id"]),
            )
        bootstrap = await self.bootstrap(student_id=student_id, course_id=course_id)
        if bootstrap["status"] != "ready":
            return {**bootstrap, "synced": [], "blocked": True}
        notebook_id = str(bootstrap.get("notebook_id") or notebook_key(student_id, course_id))
        store = get_store()
        documents = store.list_course_documents(course_id)
        synced: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for document in documents:
            chunks = store.list_document_chunks(course_id, str(document["document_id"]))
            content = "\n\n".join(str(chunk.get("content") or "") for chunk in chunks).strip()
            if not content:
                continue
            doc_id = str(document["document_id"])
            payload = {
                "notebooks": [notebook_id],
                "type": "text",
                "title": document.get("title") or doc_id,
                "content": content,
                "embed": True,
                "async_processing": False,
            }
            result = await self._post_first_json(
                [
                    "/api/sources/json",
                    "/api/sources",
                    f"/api/notebooks/{notebook_id}/sources",
                    f"/notebooks/{notebook_id}/sources",
                    "/sources",
                ],
                payload,
            )
            item = {"document_id": doc_id, "title": document.get("title"), "chunk_count": len(chunks), "result": result}
            if result["status"] == "ready":
                synced.append(item)
            else:
                blocked.append(item)
        return {
            "status": "ready" if not blocked else "partial",
            "provider": "open_notebook",
            "notebook_id": notebook_id,
            "embed_url": notebook_embed_url(notebook_id),
            "synced": synced,
            "blocked": blocked,
        }

    async def sync_notebook_sources(self, *, student_id: str, course_id: str, learnforge_notebook_id: str) -> dict[str, Any]:
        bootstrap = await self.bootstrap_notebook(
            student_id=student_id,
            course_id=course_id,
            learnforge_notebook_id=learnforge_notebook_id,
        )
        if bootstrap["status"] != "ready":
            return {**bootstrap, "synced": [], "blocked": True}
        open_notebook_id = str(bootstrap.get("notebook_id") or "")
        store = get_store()
        await self.repair_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)
        sources = store.list_notebook_sources(learnforge_notebook_id, student_id=student_id, course_id=course_id)
        synced: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for source in sources:
            source_id = str(source["source_id"])
            if source.get("open_notebook_source_id") and source.get("sync_status") == "ready":
                synced.append({"document_id": source_id, "title": source.get("title"), "chunk_count": source.get("chunk_count", 0), "result": {"status": "ready", "path": "cached", "data": {"id": source.get("open_notebook_source_id")}}})
                continue
            chunks = store.list_document_chunks(course_id, source_id)
            usable_chunks = [chunk for chunk in chunks if not is_binary_like_source_text(chunk.get("content"))]
            content = "\n\n".join(str(chunk.get("content") or "") for chunk in usable_chunks).strip()
            title = source.get("title") or source_id
            if str(source.get("ingest_type") or "").lower() == "link" and source.get("original_url"):
                payload = {
                    "notebooks": [open_notebook_id],
                    "type": "link",
                    "title": title,
                    "url": source.get("original_url"),
                    "embed": True,
                    "async_processing": False,
                }
            elif content:
                payload = {
                    "notebooks": [open_notebook_id],
                    "type": "text",
                    "title": title,
                    "content": content,
                    "embed": True,
                    "async_processing": False,
                }
            else:
                store.mark_notebook_source_synced(learnforge_notebook_id, source_id, None, "blocked_no_content")
                blocked.append({
                    "document_id": source_id,
                    "title": title,
                    "chunk_count": 0,
                    "result": {"status": "blocked_no_content", "reason": "Source has no parsed text and no supported URL for Open Notebook sync."},
                })
                continue
            result = await self._post_first_json(
                [
                    "/api/sources/json",
                    "/api/sources",
                    f"/api/notebooks/{open_notebook_id}/sources",
                    f"/notebooks/{open_notebook_id}/sources",
                    "/sources",
                ],
                payload,
            )
            item = {
                "document_id": source_id,
                "title": title,
                "chunk_count": len(usable_chunks),
                "ingest_type": source.get("ingest_type"),
                "source_scope": source.get("source_scope"),
                "result": result,
            }
            if result["status"] == "ready":
                data = result.get("data") if isinstance(result.get("data"), dict) else {}
                nested_source = data.get("source") if isinstance(data.get("source"), dict) else {}
                open_source_id = data.get("id") or data.get("source_id") or nested_source.get("id")
                store.mark_notebook_source_synced(learnforge_notebook_id, source_id, str(open_source_id or ""), "ready")
                synced.append(item)
            else:
                store.mark_notebook_source_synced(learnforge_notebook_id, source_id, None, "blocked")
                blocked.append(item)
        return {
            "status": "ready" if not blocked else "partial",
            "provider": "open_notebook",
            "notebook_id": open_notebook_id,
            "learnforge_notebook_id": learnforge_notebook_id,
            "embed_url": notebook_embed_url(open_notebook_id),
            "synced": synced,
            "blocked": blocked,
        }

    def _local_keyword_chunks(
        self,
        *,
        course_id: str,
        learnforge_notebook_id: str,
        student_id: str,
        query: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """在 LearnForge 自己存的 document_chunks 里按关键词检索某 notebook 的来源。

        Open Notebook 未配 embedding 时，向量搜索拿不到结果；这里用关键词命中兜底，
        保证上传资料至少能被召回。query 同时按空格分词 + 中文单字拆分。
        """
        store = get_store()
        try:
            sources = store.list_notebook_sources(learnforge_notebook_id, student_id=student_id, course_id=course_id)
        except Exception:
            return []
        raw_query = (query or "").strip()
        terms = [t for t in re.split(r"\s+", raw_query) if t]
        terms += [ch for ch in raw_query if "一" <= ch <= "鿿"]
        terms = [t.lower() for t in terms if t]
        if not terms:
            return []
        scored: list[dict[str, Any]] = []
        for src in sources:
            source_id = str(src.get("source_id") or "")
            title = str(src.get("title") or "")
            try:
                chunks = store.list_document_chunks(course_id, source_id)
            except Exception:
                chunks = []
            for idx, ch in enumerate(chunks, 1):
                content = str(ch.get("content") or "")
                if not content or is_binary_like_source_text(content):
                    continue
                lowered = content.lower()
                hits = sum(1 for term in terms if term in lowered)
                if hits > 0:
                    scored.append({
                        "source_id": source_id,
                        "document_id": source_id,
                        "chunk_id": str(ch.get("chunk_id") or f"{source_id}-chunk-{idx}"),
                        "title": title,
                        "content": content,
                        "snippet": content[:300],
                        "score": float(hits),
                    })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    async def retrieve(
        self,
        *,
        student_id: str,
        course_id: str,
        query: str,
        source_ids: list[str] | None = None,
        limit: int = 8,
        learnforge_notebook_id: str | None = None,
    ) -> dict[str, Any]:
        if learnforge_notebook_id:
            bootstrap = await self.bootstrap_notebook(
                student_id=student_id,
                course_id=course_id,
                learnforge_notebook_id=learnforge_notebook_id,
            )
        else:
            bootstrap = await self.bootstrap(student_id=student_id, course_id=course_id)
        if bootstrap["status"] != "ready":
            return {**bootstrap, "chunks": [], "citations": [], "query": query, "answer": None}
        notebook_id = str(bootstrap.get("notebook_id") or notebook_key(student_id, course_id))
        if learnforge_notebook_id:
            await self.repair_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=learnforge_notebook_id)
        payload = {
            "query": query,
            "type": "text",
            "limit": limit,
            "search_sources": True,
            "search_notes": False,
            "minimum_score": 0.0,
            "notebook_id": notebook_id,
            "source_ids": source_ids or [],
            "mode": "retrieve_only",
        }
        result = await self._post_first_json(
            [
                "/api/search",
                f"/api/notebooks/{notebook_id}/search",
                f"/notebooks/{notebook_id}/search",
                "/search",
            ],
            payload,
        )
        if result["status"] != "ready":
            return {**result, "notebook_id": notebook_id, "chunks": [], "citations": [], "query": query, "answer": None}
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        chunks = data.get("chunks") or data.get("results") or data.get("items") or []
        citations = data.get("citations") or data.get("source_refs") or []
        if isinstance(chunks, list):
            chunks = [
                chunk for chunk in chunks
                if not (isinstance(chunk, dict) and is_binary_like_source_text(chunk.get("snippet") or chunk.get("content") or chunk.get("text")))
            ]
        if isinstance(citations, list):
            citations = [ref for ref in citations if isinstance(ref, dict) and _usable_source_ref(ref)]
        if not citations and isinstance(chunks, list):
            citations = [
                {
                    "source_id": chunk.get("source_id") or chunk.get("id") or chunk.get("source", {}).get("id"),
                    "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                    "title": chunk.get("title") or chunk.get("source_title") or chunk.get("source", {}).get("title"),
                    "snippet": chunk.get("snippet") or chunk.get("content") or chunk.get("text"),
                    "score": chunk.get("score"),
                }
                for chunk in chunks
                if isinstance(chunk, dict)
            ]
        # Open Notebook 未配置 embedding（或没结果、或返回空内容 chunk）时，
        # 回退到 LearnForge 本地关键词检索，保证上传的资料至少能按词被召回。
        has_real_content = any(
            str(c.get("snippet") or c.get("content") or c.get("text") or "").strip()
            for c in chunks if isinstance(c, dict)
        )
        if (not chunks or not has_real_content) and learnforge_notebook_id:
            local = self._local_keyword_chunks(
                course_id=course_id,
                learnforge_notebook_id=learnforge_notebook_id,
                student_id=student_id,
                query=query,
                limit=limit,
            )
            if local:
                chunks = local
                citations = [
                    {
                        "source_id": c.get("source_id") or c.get("document_id"),
                        "chunk_id": c.get("chunk_id"),
                        "title": c.get("title"),
                        "snippet": c.get("snippet") or c.get("content"),
                        "score": c.get("score"),
                    }
                    for c in local
                ]
        has_real_content = any(
            str(c.get("snippet") or c.get("content") or c.get("text") or "").strip()
            for c in chunks if isinstance(c, dict)
        )
        if not has_real_content:
            citations = []
        return {
            "status": "ready",
            "provider": "open_notebook",
            "notebook_id": notebook_id,
            "query": query,
            "chunks": chunks,
            "citations": citations,
            "answer": None,
            "api_path": result.get("path"),
        }

    async def transform(
        self,
        *,
        student_id: str,
        course_id: str,
        kind: str,
        prompt: str,
        source_ids: list[str] | None = None,
        learnforge_notebook_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = kind.strip().lower()
        if normalized not in NOTEBOOKLM_TRANSFORM_KINDS:
            return {"status": "blocked_invalid_transform", "reason": f"Unsupported transform kind: {kind}"}
        if learnforge_notebook_id:
            bootstrap = await self.bootstrap_notebook(
                student_id=student_id,
                course_id=course_id,
                learnforge_notebook_id=learnforge_notebook_id,
            )
        else:
            bootstrap = await self.bootstrap(student_id=student_id, course_id=course_id)
        if bootstrap["status"] != "ready":
            return {**bootstrap, "kind": normalized}
        notebook_id = str(bootstrap.get("notebook_id") or notebook_key(student_id, course_id))
        payload = {
            "notebook_id": notebook_id,
            "kind": normalized,
            "transformation": normalized,
            "prompt": prompt,
            "source_ids": source_ids or [],
            "metadata": {
                "student_id": student_id,
                "course_id": course_id,
                "learnforge_notebook_id": learnforge_notebook_id,
                "visible_answer_channel": "learnforge_hermes",
            },
        }
        result = await self._post_first_json(
            [
                f"/api/notebooks/{notebook_id}/transformations",
                "/api/transformations",
                f"/notebooks/{notebook_id}/transformations",
                "/transformations",
            ],
            payload,
        )
        return {**result, "notebook_id": notebook_id, "learnforge_notebook_id": learnforge_notebook_id, "kind": normalized}


def publish_notebooklm_output(
    *,
    student_id: str,
    course_id: str,
    kind: str,
    title: str | None,
    content: dict[str, Any],
    source_refs: list[dict[str, Any]],
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_kind = kind.strip().lower()
    if not source_refs and citations:
        source_refs = citations
    if not source_refs:
        return {"status": "blocked_missing_sources", "reason": "NotebookLM outputs must include source_refs or citations."}
    resource_type = _resource_type_for_transform(normalized_kind)
    resource = LearningResource(
        resource_id=new_id("res-nblm"),
        type=resource_type,  # type: ignore[arg-type]
        title=_title_for_transform(normalized_kind, title),
        target_topic=str(content.get("target_topic") or content.get("topic") or title or "NotebookLM"),
        difficulty=str(content.get("difficulty") or "adaptive"),
        content={**content, "notebooklm_kind": normalized_kind, "citations": citations or source_refs},
        source_refs=source_refs,
        personalized_reason="来自 NotebookLM 来源工作台，经 Hermes 验收后发布到 LearnForge。",
        estimated_minutes=content.get("estimated_minutes") if isinstance(content.get("estimated_minutes"), int) else None,
        tags=["#NotebookLM", "#来源驱动", f"#{normalized_kind}"],
    )
    saved = get_store().save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="notebooklm_bridge")
    return {"status": "published", "resource": saved.model_dump()}
