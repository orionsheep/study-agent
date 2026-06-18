from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.session import SessionHeaders, get_session_headers, resolve_session_context
from app.edumem0.client import EduMem0Client
from app.notebooklm_service import OpenNotebookBridge, publish_notebooklm_output
from app.schemas.app_protocol import AppEvent
from app.database.store import get_store


router = APIRouter(prefix="/api/notebooklm", tags=["notebooklm"])


class NotebookBootstrapRequest(BaseModel):
    student_id: str | None = None
    course_id: str | None = None
    learnforge_notebook_id: str | None = None


class NotebookRetrieveRequest(NotebookBootstrapRequest):
    query: str
    source_ids: list[str] = Field(default_factory=list)
    limit: int = 8
    intent: str | None = None


class NotebookTransformRequest(NotebookBootstrapRequest):
    kind: str
    prompt: str = ""
    source_ids: list[str] = Field(default_factory=list)


class NotebookPublishRequest(NotebookBootstrapRequest):
    kind: str
    title: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class NotebookEventRequest(NotebookBootstrapRequest):
    app_id: str = "notebooklm.workspace"
    event_type: str = "notebooklm.event"
    payload: dict[str, Any] = Field(default_factory=dict)


class NotebookCreateRequest(NotebookBootstrapRequest):
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class NotebookTextSourceRequest(NotebookBootstrapRequest):
    title: str = "粘贴文本"
    content: str
    sync: bool = True


class NotebookLinkSourceRequest(NotebookBootstrapRequest):
    url: str
    title: str | None = None
    sync: bool = True


def resolve_notebook_session(
    request: NotebookBootstrapRequest | None,
    headers: SessionHeaders,
) -> tuple[str, str]:
    ctx = resolve_session_context(
        explicit_student_id=request.student_id if request else None,
        explicit_course_id=request.course_id if request else None,
        headers=headers,
    )
    return ctx.student_id, ctx.course_id


@router.get("/status")
async def notebooklm_status() -> dict[str, Any]:
    return await OpenNotebookBridge().status()


@router.post("/bootstrap")
async def notebooklm_bootstrap(
    request: NotebookBootstrapRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    if request.learnforge_notebook_id:
        return await OpenNotebookBridge().bootstrap_notebook(
            student_id=student_id,
            course_id=course_id,
            learnforge_notebook_id=request.learnforge_notebook_id,
        )
    return await OpenNotebookBridge().bootstrap(student_id=student_id, course_id=course_id)


@router.post("/sources/sync")
async def notebooklm_sync_sources(
    request: NotebookBootstrapRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    if request.learnforge_notebook_id:
        return await OpenNotebookBridge().sync_notebook_sources(
            student_id=student_id,
            course_id=course_id,
            learnforge_notebook_id=request.learnforge_notebook_id,
        )
    return await OpenNotebookBridge().sync_course_sources(student_id=student_id, course_id=course_id)


@router.get("/notebooks")
async def notebooklm_notebooks(
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    ctx = resolve_session_context(explicit_student_id=None, explicit_course_id=None, headers=headers)
    notebooks = get_store().ensure_default_notebooks(student_id=ctx.student_id, course_id=ctx.course_id)
    return {"notebooks": notebooks}


@router.post("/notebooks")
async def notebooklm_create_notebook(
    request: NotebookCreateRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    notebook = get_store().create_notebook(
        student_id=student_id,
        course_id=course_id,
        title=request.title,
        description=request.description,
        tags=request.tags or ["我的上传"],
    )
    return {"notebook": notebook}


@router.get("/notebooks/{notebook_id}/sources")
async def notebooklm_notebook_sources(
    notebook_id: str,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    ctx = resolve_session_context(explicit_student_id=None, explicit_course_id=None, headers=headers)
    notebook = get_store().get_notebook(notebook_id, student_id=ctx.student_id, course_id=ctx.course_id)
    if not notebook:
        raise HTTPException(status_code=404, detail={"code": "NOTEBOOK_NOT_FOUND", "message": "notebook not found"})
    return {"notebook": notebook, "sources": get_store().list_notebook_sources(notebook_id, student_id=ctx.student_id, course_id=ctx.course_id)}


@router.post("/notebooks/{notebook_id}/sync")
async def notebooklm_sync_notebook(
    notebook_id: str,
    request: NotebookBootstrapRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    return await OpenNotebookBridge().sync_notebook_sources(student_id=student_id, course_id=course_id, learnforge_notebook_id=notebook_id)


@router.post("/notebooks/{notebook_id}/sources/text")
async def notebooklm_add_text_source(
    notebook_id: str,
    request: NotebookTextSourceRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    result = await OpenNotebookBridge().ingest_text_source(
        student_id=student_id,
        course_id=course_id,
        learnforge_notebook_id=notebook_id,
        title=request.title,
        content=request.content,
        sync=request.sync,
    )
    if result["status"] == "blocked_empty_source":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/notebooks/{notebook_id}/sources/link")
async def notebooklm_add_link_source(
    notebook_id: str,
    request: NotebookLinkSourceRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    return await OpenNotebookBridge().ingest_link_source(
        student_id=student_id,
        course_id=course_id,
        learnforge_notebook_id=notebook_id,
        url=request.url,
        title=request.title,
        sync=request.sync,
    )


@router.post("/notebooks/{notebook_id}/sources/upload")
async def notebooklm_upload_source(
    notebook_id: str,
    request: Request,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    ctx = resolve_session_context(explicit_student_id=None, explicit_course_id=None, headers=headers)
    data = await request.body()
    filename = request.headers.get("x-filename") or request.query_params.get("filename") or "upload.bin"
    title = request.headers.get("x-title") or request.query_params.get("title")
    sync_value = request.headers.get("x-sync") or request.query_params.get("sync") or "true"
    sync = str(sync_value).strip().lower() not in {"0", "false", "no", "off"}
    result = await OpenNotebookBridge().ingest_file_source(
        student_id=ctx.student_id,
        course_id=ctx.course_id,
        learnforge_notebook_id=notebook_id,
        filename=filename,
        data=data,
        mime_type=request.headers.get("content-type"),
        title=title,
        sync=sync,
    )
    if result["status"] == "blocked_empty_source":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/sources")
async def notebooklm_sources(
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    ctx = resolve_session_context(explicit_student_id=None, explicit_course_id=None, headers=headers)
    store = get_store()
    notebooks = store.ensure_default_notebooks(student_id=ctx.student_id, course_id=ctx.course_id)
    course_notebook = next((item for item in notebooks if item.get("purpose") == "course_official"), None)
    if course_notebook:
        return {"sources": store.list_notebook_sources(str(course_notebook["id"]), student_id=ctx.student_id, course_id=ctx.course_id)}
    sources: list[dict[str, Any]] = []
    for document in store.list_course_documents(ctx.course_id):
        document_id = str(document["document_id"])
        chunks = store.list_document_chunks(ctx.course_id, document_id)
        refs: list[dict[str, Any]] = []
        for chunk in chunks[:12]:
            source_ref = chunk.get("source_ref") if isinstance(chunk.get("source_ref"), dict) else {}
            refs.append(
                {
                    **source_ref,
                    "document_id": document_id,
                    "chunk_id": chunk.get("chunk_id"),
                    "title": document.get("title") or document_id,
                    "snippet": str(chunk.get("content") or "")[:360],
                }
            )
        sources.append(
            {
                "id": document_id,
                "title": document.get("title") or document_id,
                "summary": refs[0]["snippet"] if refs else "",
                "chunk_count": document.get("chunk_count", len(chunks)),
                "source_refs": refs,
            }
        )
    return {"sources": sources}


@router.post("/retrieve")
async def notebooklm_retrieve(
    request: NotebookRetrieveRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    return await OpenNotebookBridge().retrieve(
        student_id=student_id,
        course_id=course_id,
        query=request.query,
        source_ids=request.source_ids,
        limit=max(1, min(20, request.limit)),
        learnforge_notebook_id=request.learnforge_notebook_id,
    )


@router.post("/transform")
async def notebooklm_transform(
    request: NotebookTransformRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    return await OpenNotebookBridge().transform(
        student_id=student_id,
        course_id=course_id,
        kind=request.kind,
        prompt=request.prompt,
        source_ids=request.source_ids,
        learnforge_notebook_id=request.learnforge_notebook_id,
    )


@router.post("/publish")
async def notebooklm_publish(
    request: NotebookPublishRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    result = publish_notebooklm_output(
        student_id=student_id,
        course_id=course_id,
        kind=request.kind,
        title=request.title,
        content=request.content,
        source_refs=request.source_refs,
        citations=request.citations,
    )
    if result["status"] == "blocked_missing_sources":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/events")
async def notebooklm_events(
    request: NotebookEventRequest,
    headers: SessionHeaders = Depends(get_session_headers),
) -> dict[str, Any]:
    student_id, course_id = resolve_notebook_session(request, headers)
    event = AppEvent(
        app_id=request.app_id,
        student_id=student_id,
        course_id=course_id,
        event_type=request.event_type,
        payload=request.payload,
    )
    get_store().record_app_event(event)
    get_store().record_notebook_memory_event(
        notebook_id=request.learnforge_notebook_id or str(request.payload.get("learnforge_notebook_id") or request.payload.get("notebook_id") or "") or None,
        student_id=student_id,
        course_id=course_id,
        event_type=request.event_type,
        source_refs=request.payload.get("source_refs") if isinstance(request.payload.get("source_refs"), list) else [],
        payload=request.payload,
    )
    memory = EduMem0Client().record_app_event(event)
    return {"event": event.model_dump(), "memory": memory.model_dump(), "status": "recorded"}
