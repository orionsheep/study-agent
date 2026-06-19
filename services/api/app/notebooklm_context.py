from __future__ import annotations

import json
import re
from typing import Any

from app.database.store import get_store


KIND_TO_INTENT = {
    "summary": "notebooklm_summarize_sources",
    "study_guide": "notebooklm_generate_study_guide",
    "quiz": "notebooklm_generate_quiz",
    "flashcards": "notebooklm_generate_flashcards",
    "audio_overview": "notebooklm_audio_overview",
    "podcast": "notebooklm_audio_overview",
}


class NotebookContextResolver:
    """Resolve NotebookLM source context for Hermes without choosing product intent."""

    block_pattern = re.compile(r"\[NotebookLM Context\](.*?)\[/NotebookLM Context\]", re.DOTALL | re.IGNORECASE)

    def parse_message(self, message: str) -> dict[str, Any]:
        text = str(message or "")
        match = self.block_pattern.search(text)
        if not match:
            return {"query": text.strip(), "metadata": {}, "source_refs": []}
        block = match.group(1)
        metadata: dict[str, Any] = {}
        source_refs: list[dict[str, Any]] = []
        refs_match = re.search(r"source_refs_json:\s*(\[.*\])", block, re.DOTALL)
        if refs_match:
            try:
                parsed_refs = json.loads(refs_match.group(1))
                if isinstance(parsed_refs, list):
                    source_refs = [item for item in parsed_refs if isinstance(item, dict)]
            except Exception:
                source_refs = []
            block_without_refs = block[: refs_match.start()]
        else:
            block_without_refs = block
        for raw_line in block_without_refs.splitlines():
            if ":" not in raw_line:
                continue
            key, value = raw_line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                metadata[key] = value
        clean_query = self.block_pattern.sub("", text).strip()
        return {"query": clean_query or text.strip(), "metadata": metadata, "source_refs": source_refs}

    def parse_context_payload(self, context_payload: dict[str, Any] | None, message: str) -> dict[str, Any] | None:
        if not isinstance(context_payload, dict):
            return None
        notebook = context_payload.get("notebooklm")
        if not isinstance(notebook, dict):
            return None
        metadata: dict[str, Any] = {}
        field_map = {
            "learnforgeNotebookId": "learnforge_notebook_id",
            "openNotebookId": "open_notebook_id",
            "notebookId": "notebook_id",
            "notebookTitle": "notebook_title",
            "sourceId": "source_id",
            "sourceTitle": "source_title",
            "kind": "task_kind",
        }
        for source_key, target_key in field_map.items():
            value = notebook.get(source_key)
            if isinstance(value, str) and value.strip():
                metadata[target_key] = value.strip()
        source_refs = notebook.get("sourceRefs")
        clean_query = self.block_pattern.sub("", str(message or "")).strip()
        return {
            "query": clean_query or str(message or "").strip(),
            "metadata": metadata,
            "source_refs": [item for item in source_refs if isinstance(item, dict)] if isinstance(source_refs, list) else [],
        }

    def resolve(self, *, student_id: str, course_id: str, message: str, context_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        parsed = self.parse_context_payload(context_payload, message) or self.parse_message(message)
        metadata = parsed["metadata"]
        notebooks = get_store().ensure_default_notebooks(student_id=student_id, course_id=course_id)
        requested_id = str(metadata.get("learnforge_notebook_id") or metadata.get("notebook_id") or "").strip()
        notebook = None
        if requested_id:
            notebook = get_store().get_notebook(requested_id, student_id=student_id, course_id=course_id)
        if not notebook:
            notebook = next((item for item in notebooks if item.get("purpose") == "course_official"), None)
        source_ids = []
        if metadata.get("source_id"):
            source_ids.append(str(metadata["source_id"]))
        kind = str(metadata.get("task_kind") or "").strip().lower()
        return {
            "query": parsed["query"],
            "learnforge_notebook_id": str(notebook.get("id")) if notebook else None,
            "open_notebook_id": str(notebook.get("open_notebook_id") or "") if notebook else "",
            "source_ids": source_ids,
            "source_refs": parsed["source_refs"],
            "intent": KIND_TO_INTENT.get(kind, "notebooklm_chat"),
            "kind": kind,
            "memory_scope": {
                "student_id": student_id,
                "course_id": course_id,
                "notebook_id": str(notebook.get("id")) if notebook else None,
            },
            "metadata": metadata,
        }
