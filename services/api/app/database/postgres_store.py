from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.database.schema import REQUIRED_TABLES
from app.database.store import FOUNDATION_APP_TYPES, dumps, loads, merge_profile_dicts, snippet_for, stable_id
from app.edumem0.decay_policy import DecayPolicy
from app.schemas.app_protocol import (
    CanvasApp,
    CanvasPosition,
    CanvasSize,
    DashboardSnapshot,
    EduMemoryItem,
    LearningResource,
    VerifierResult,
    new_id,
    utc_now,
)


def _require_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except Exception as exc:  # pragma: no cover - only used in Postgres runtime.
        raise RuntimeError("Postgres runtime requires installing services/api[postgres].") from exc
    return psycopg, dict_row


class PostgresLearningStore:
    """Postgres-first store for production paths.

    It implements the core surface used by auth, onboarding, profile, memory,
    resources, canvas, chat, RAG document ingestion, and dashboard APIs.
    """

    decay = DecayPolicy()

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url
        self.path = Path("postgres://learnforge")
        psycopg, dict_row = _require_psycopg()
        self.conn = psycopg.connect(self.database_url.replace("postgresql+psycopg://", "postgresql://"), row_factory=dict_row)
        self.create_schema()

    def create_schema(self) -> None:
        schema = Path(__file__).resolve().with_name("postgres_schema.sql").read_text(encoding="utf-8")
        with self.conn.cursor() as cursor:
            cursor.execute(schema)
        self.conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except Exception:
            self.conn.rollback()
            raise

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except Exception:
            self.conn.rollback()
            raise

    def table_names(self) -> list[str]:
        rows = self.fetchall("SELECT tablename AS name FROM pg_tables WHERE schemaname='public'")
        return sorted(row["name"] for row in rows)

    def schema_ready(self) -> bool:
        return set(REQUIRED_TABLES).issubset(set(self.table_names()))

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.fetchone("SELECT * FROM users WHERE lower(email)=lower(%s)", (email.strip(),))

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.fetchone("SELECT * FROM users WHERE id=%s", (user_id,))

    def create_user_account(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        student_id: str | None = None,
        course_id: str = "ai-course",
    ) -> dict[str, Any]:
        now = utc_now()
        cleaned_email = email.strip().lower()
        if self.get_user_by_email(cleaned_email):
            raise ValueError("email_exists")
        user_id = stable_id("usr", cleaned_email)
        target_student = student_id or stable_id("stu", cleaned_email)
        self.execute(
            "INSERT INTO users(id,email,password_hash,display_name,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s)",
            (user_id, cleaned_email, password_hash, display_name, now, now),
        )
        self.execute(
            "INSERT INTO students(id,display_name,created_at,updated_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (target_student, display_name, now, now),
        )
        self.execute(
            "INSERT INTO courses(id,title,description,created_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (course_id, "默认学习空间", "新用户画像构建与个性化学习空间。", now),
        )
        self.execute(
            "INSERT INTO student_accounts(id,user_id,student_id,role,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT (user_id, student_id) DO NOTHING",
            (stable_id("acct", f"{user_id}:{target_student}"), user_id, target_student, "owner", now),
        )
        self.start_onboarding(target_student, course_id)
        self.ensure_default_apps(target_student, course_id, full=True)
        return {"id": user_id, "email": cleaned_email, "display_name": display_name, "student_id": target_student, "course_id": course_id}

    def _foundation_app_id(self, base_id: str, student_id: str, course_id: str) -> str:
        if student_id == "demo-student" and course_id == "ai-course":
            return base_id
        return stable_id(base_id, f"{student_id}:{course_id}:{base_id}")

    def _foundation_default_apps(self, student_id: str, course_id: str) -> list[CanvasApp]:
        refs: list[dict[str, Any]] = []
        return [
            CanvasApp(
                app_id=self._foundation_app_id("app-profile", student_id, course_id),
                app_type="profile.dashboard",
                title="学习画像",
                icon="UserRound",
                position=CanvasPosition(x=40, y=40),
                size=CanvasSize(width=330, height=250),
                z_index=2,
                payload={"summary": "画像构建完成后会在这里展示你的学习状态。"},
                source={"student_id": student_id, "course_id": course_id},
                source_refs=refs,
                actions=[{"label": "更新画像", "action": "profile.refresh"}],
            ),
            CanvasApp(
                app_id=self._foundation_app_id("app-dashboard", student_id, course_id),
                app_type="dashboard.learning",
                title="学习仪表盘",
                icon="Gauge",
                position=CanvasPosition(x=1450, y=60),
                size=CanvasSize(width=410, height=360),
                z_index=8,
                payload={"student_id": student_id},
                source={"student_id": student_id, "course_id": course_id},
                source_refs=refs,
                actions=[{"label": "刷新证据链", "action": "dashboard.refresh"}],
            ),
            CanvasApp(
                app_id=self._foundation_app_id("app-resource", student_id, course_id),
                app_type="resource.center",
                title="资源中心",
                icon="BookOpen",
                position=CanvasPosition(x=1860, y=60),
                size=CanvasSize(width=380, height=320),
                z_index=15,
                payload={"filters": ["document", "quiz", "code"]},
                source={"student_id": student_id, "course_id": course_id},
                source_refs=refs,
                actions=[{"label": "筛选资源", "action": "resource.filter"}],
            ),
        ]

    def ensure_default_apps(self, student_id: str, course_id: str = "ai-course", *, full: bool = False) -> list[CanvasApp]:
        existing = self.list_apps(student_id, course_id=course_id)
        candidates = self._foundation_default_apps(student_id, course_id)
        if existing and not full:
            candidates = [app for app in candidates if app.app_type in FOUNDATION_APP_TYPES]
        for app in candidates:
            if not self.get_app(app.app_id, student_id=student_id, course_id=course_id):
                self.save_app(app, student_id=student_id, course_id=course_id, agent="system_seed", skill="default_canvas")
        return self.list_apps(student_id, course_id=course_id)

    def create_auth_session(self, *, token: str, user_id: str, student_id: str, course_id: str) -> dict[str, Any]:
        now = utc_now()
        self.execute(
            """
            INSERT INTO auth_sessions(token,user_id,student_id,course_id,expires_at,created_at,last_seen_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (token) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at
            """,
            (token, user_id, student_id, course_id, None, now, now),
        )
        return {"token": token, "user_id": user_id, "student_id": student_id, "course_id": course_id}

    def get_auth_session(self, token: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM auth_sessions WHERE token=%s", (token,))
        if row:
            self.execute("UPDATE auth_sessions SET last_seen_at=%s WHERE token=%s", (utc_now(), token))
        return row

    def user_student_context(self, user_id: str) -> dict[str, Any] | None:
        return self.fetchone(
            """
            SELECT u.id AS user_id, u.email, u.display_name, a.student_id, s.display_name AS student_name,
                   COALESCE(sess.course_id, 'ai-course') AS course_id
            FROM users u
            JOIN student_accounts a ON a.user_id = u.id
            JOIN students s ON s.id = a.student_id
            LEFT JOIN auth_sessions sess ON sess.user_id = u.id
            WHERE u.id=%s
            ORDER BY sess.last_seen_at DESC NULLS LAST
            LIMIT 1
            """,
            (user_id,),
        )

    def get_profile(self, student_id: str, course_id: str | None = None) -> dict[str, Any]:
        if course_id:
            row = self.fetchone(
                "SELECT profile_json FROM student_profiles WHERE student_id=%s AND course_id=%s ORDER BY updated_at DESC LIMIT 1",
                (student_id, course_id),
            )
        else:
            row = self.fetchone("SELECT profile_json FROM student_profiles WHERE student_id=%s ORDER BY updated_at DESC LIMIT 1", (student_id,))
        return dict(row["profile_json"]) if row and isinstance(row.get("profile_json"), dict) else {}

    def save_profile(self, student_id: str, profile: dict[str, Any], course_id: str | None = None) -> dict[str, Any]:
        now = utc_now()
        target_course = course_id or "ai-course"
        existing = self.fetchone(
            "SELECT id, profile_json, version, created_at FROM student_profiles WHERE student_id=%s AND course_id=%s ORDER BY updated_at DESC LIMIT 1",
            (student_id, target_course),
        )
        merged = merge_profile_dicts(dict(existing["profile_json"]) if existing else {}, profile or {})
        profile_id = existing["id"] if existing else stable_id("profile", f"{student_id}:{target_course}")
        version = int(existing["version"]) + 1 if existing else 1
        created_at = existing["created_at"] if existing else now
        self.execute(
            """
            INSERT INTO student_profiles(id,student_id,course_id,profile_json,version,created_at,updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET profile_json=EXCLUDED.profile_json, version=EXCLUDED.version, updated_at=EXCLUDED.updated_at
            """,
            (profile_id, student_id, target_course, dumps(merged), version, created_at, now),
        )
        return merged

    def profile_status(self, student_id: str, course_id: str | None = None) -> str:
        profile = self.get_profile(student_id, course_id=course_id)
        required = ["school", "major", "grade", "schedule", "learning_goal", "knowledge_foundation", "weak_points", "preferred_resources", "learning_pace", "available_study_time", "interests", "mastery_map", "subject_confidence"]
        filled = [key for key in required if profile.get(key) not in (None, "", [], {})]
        if not profile:
            return "not_started"
        return "completed" if len(filled) >= 10 else "collecting"

    def onboarding_missing_fields(self, student_id: str, course_id: str | None = None) -> list[str]:
        labels = {"school": "学校信息", "major": "专业", "grade": "年级", "schedule": "课表", "learning_goal": "学习目标", "knowledge_foundation": "基础水平", "weak_points": "薄弱点", "preferred_resources": "偏好资源", "learning_pace": "学习节奏", "available_study_time": "可用学习时间", "interests": "兴趣方向", "mastery_map": "掌握图谱", "subject_confidence": "科目置信度"}
        profile = self.get_profile(student_id, course_id=course_id)
        return [label for key, label in labels.items() if profile.get(key) in (None, "", [], {})]

    def start_onboarding(self, student_id: str, course_id: str = "ai-course") -> dict[str, Any]:
        now = utc_now()
        row = self.fetchone("SELECT * FROM onboarding_sessions WHERE student_id=%s AND course_id=%s ORDER BY updated_at DESC LIMIT 1", (student_id, course_id))
        missing = self.onboarding_missing_fields(student_id, course_id)
        if row:
            row["missing_fields"] = row.get("missing_fields") or []
            return row
        session_id = stable_id("onboard", f"{student_id}:{course_id}")
        self.execute(
            "INSERT INTO onboarding_sessions(id,student_id,course_id,status,current_step,missing_fields,summary,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (session_id, student_id, course_id, "collecting", "collect_sources", dumps(missing), "画像构建已开始。", now, now),
        )
        return self.get_latest_onboarding(student_id, course_id) or {}

    def get_latest_onboarding(self, student_id: str, course_id: str | None = None) -> dict[str, Any] | None:
        row = self.fetchone(
            "SELECT * FROM onboarding_sessions WHERE student_id=%s AND course_id=%s ORDER BY updated_at DESC LIMIT 1",
            (student_id, course_id or "ai-course"),
        )
        if row and not isinstance(row.get("missing_fields"), list):
            row["missing_fields"] = loads(row.get("missing_fields"), [])
        return row

    def update_onboarding(self, student_id: str, course_id: str, *, status: str | None = None, current_step: str | None = None, summary: str | None = None) -> dict[str, Any]:
        current = self.start_onboarding(student_id, course_id)
        missing = self.onboarding_missing_fields(student_id, course_id)
        self.execute(
            "UPDATE onboarding_sessions SET status=%s,current_step=%s,missing_fields=%s,summary=%s,updated_at=%s WHERE id=%s",
            (status or current["status"], current_step or current["current_step"], dumps(missing), summary if summary is not None else current["summary"], utc_now(), current["id"]),
        )
        return self.get_latest_onboarding(student_id, course_id) or current

    def save_profile_source(self, **kwargs: Any) -> dict[str, Any]:
        now = utc_now()
        source_id = new_id("psrc")
        self.execute(
            """
            INSERT INTO profile_sources(id,student_id,course_id,onboarding_session_id,source_type,title,raw_text,extracted_text,structured_payload,parser_status,parser_reason,file_name,mime_type,url,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                source_id,
                kwargs["student_id"],
                kwargs["course_id"],
                kwargs.get("onboarding_session_id"),
                kwargs["source_type"],
                kwargs["title"],
                kwargs.get("raw_text", ""),
                kwargs.get("extracted_text", ""),
                dumps(kwargs.get("structured_payload") or {}),
                kwargs.get("parser_status", "parsed"),
                kwargs.get("parser_reason"),
                kwargs.get("file_name"),
                kwargs.get("mime_type"),
                kwargs.get("url"),
                now,
            ),
        )
        return {"id": source_id, "created_at": now, **kwargs}

    def list_profile_sources(self, student_id: str, course_id: str | None = None, limit: int = 80) -> list[dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM profile_sources WHERE student_id=%s AND course_id=%s ORDER BY created_at DESC LIMIT %s",
            (student_id, course_id or "ai-course", limit),
        )
        for row in rows:
            if not isinstance(row.get("structured_payload"), dict):
                row["structured_payload"] = loads(row.get("structured_payload"), {})
        return rows

    def save_chat_message(self, *, student_id: str, course_id: str, conversation_id: str, role: str, text: str, metadata: dict[str, Any] | None = None, message_id: str | None = None) -> dict[str, Any]:
        now = utc_now()
        row_id = message_id or new_id("chatmsg")
        self.execute(
            "INSERT INTO chat_messages(id,student_id,course_id,conversation_id,role,text,metadata,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (row_id, student_id, course_id, conversation_id, role, text, dumps(metadata or {}), now),
        )
        return {"id": row_id, "student_id": student_id, "course_id": course_id, "conversation_id": conversation_id, "role": role, "text": text, "metadata": metadata or {}, "created_at": now}

    def list_chat_messages(self, *, student_id: str, course_id: str, conversation_id: str, limit: int = 8) -> list[dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM chat_messages WHERE student_id=%s AND course_id=%s AND conversation_id=%s ORDER BY created_at DESC LIMIT %s",
            (student_id, course_id, conversation_id, limit),
        )
        rows.reverse()
        for row in rows:
            row["metadata"] = row.get("metadata") if isinstance(row.get("metadata"), dict) else loads(row.get("metadata"), {})
        return rows

    def create_memory(self, memory: EduMemoryItem) -> EduMemoryItem:
        if memory.source_event_id:
            existing = self.get_memory_by_source_event_id(memory.student_id, memory.source_event_id, memory.course_id)
            if existing:
                memory.id = existing.id
                memory.version = existing.version + 1
        memory.updated_at = utc_now()
        self.execute(
            """
            INSERT INTO edu_memories(id,student_id,course_id,knowledge_point_id,memory_type,content,structured_payload,confidence,importance,decay_rate,evidence_type,source_event_id,source_agent,valid_from,valid_until,embedding,tags,version,created_at,updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET structured_payload=EXCLUDED.structured_payload, confidence=EXCLUDED.confidence, importance=EXCLUDED.importance, tags=EXCLUDED.tags, version=EXCLUDED.version, updated_at=EXCLUDED.updated_at
            """,
            (memory.id, memory.student_id, memory.course_id, memory.knowledge_point_id, memory.memory_type, memory.content, dumps(memory.structured_payload), memory.confidence, memory.importance, memory.decay_rate, memory.evidence_type, memory.source_event_id, memory.source_agent, memory.valid_from, memory.valid_until, memory.embedding, memory.tags, memory.version, memory.created_at, memory.updated_at),
        )
        return memory

    def _memory_from_row(self, row: dict[str, Any]) -> EduMemoryItem:
        item = EduMemoryItem(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row.get("course_id"),
            knowledge_point_id=row.get("knowledge_point_id"),
            memory_type=row["memory_type"],
            content=row["content"],
            structured_payload=row.get("structured_payload") if isinstance(row.get("structured_payload"), dict) else loads(row.get("structured_payload"), {}),
            confidence=row["confidence"],
            importance=row["importance"],
            decay_rate=row["decay_rate"],
            evidence_type=row["evidence_type"],
            source_event_id=row.get("source_event_id"),
            source_agent=row.get("source_agent"),
            valid_from=str(row["valid_from"]).replace("+00:00", "Z"),
            valid_until=str(row["valid_until"]) if row.get("valid_until") else None,
            embedding=row.get("embedding"),
            tags=list(row.get("tags") or []),
            version=row["version"],
            created_at=str(row["created_at"]).replace("+00:00", "Z"),
            updated_at=str(row["updated_at"]).replace("+00:00", "Z"),
        )
        item.effective_confidence = item.confidence
        return item

    def get_memory_by_source_event_id(self, student_id: str, source_event_id: str, course_id: str | None = None) -> EduMemoryItem | None:
        where = ["student_id=%s", "source_event_id=%s"]
        params: list[Any] = [student_id, source_event_id]
        if course_id:
            where.append("course_id=%s")
            params.append(course_id)
        row = self.fetchone(f"SELECT * FROM edu_memories WHERE {' AND '.join(where)} ORDER BY updated_at DESC LIMIT 1", tuple(params))
        return self._memory_from_row(row) if row else None

    def list_memories(self, student_id: str, *, course_id: str | None = None, knowledge_point_id: str | None = None, conversation_id: str | None = None, limit: int = 50) -> list[EduMemoryItem]:
        where = ["student_id=%s"]
        params: list[Any] = [student_id]
        if course_id:
            where.append("course_id=%s")
            params.append(course_id)
        if knowledge_point_id:
            where.append("knowledge_point_id=%s")
            params.append(knowledge_point_id)
        params.append(limit)
        rows = self.fetchall(f"SELECT * FROM edu_memories WHERE {' AND '.join(where)} ORDER BY updated_at DESC LIMIT %s", tuple(params))
        return [self._memory_from_row(row) for row in rows]

    def search_memories(self, student_id: str, *, query: str | None = None, memory_types: list[str] | None = None, course_id: str | None = None, knowledge_point_id: str | None = None, limit: int = 10) -> list[EduMemoryItem]:
        memories = self.list_memories(student_id, course_id=course_id, limit=200)
        if memory_types:
            memories = [item for item in memories if item.memory_type in memory_types]
        if query:
            lowered = query.lower()
            memories = [item for item in memories if lowered in item.content.lower() or lowered in dumps(item.structured_payload).lower()]
        memories.sort(key=lambda item: item.confidence * item.importance, reverse=True)
        return memories[:limit]

    def save_resource(self, resource: LearningResource, *, student_id: str = "demo-student", course_id: str = "ai-course", knowledge_point_id: str | None = None, created_by_skill: str = "seed") -> LearningResource:
        now = utc_now()
        quality = resource.quality_check.model_dump() if resource.quality_check else {}
        content = dict(resource.content)
        content.setdefault("target_topic", resource.target_topic)
        content.setdefault("tags", resource.tags)
        self.execute(
            """
            INSERT INTO resources(id,student_id,course_id,knowledge_point_id,type,title,difficulty,content_json,file_url,source_refs,personalized_reason,quality_score,verifier_result,created_by_skill,status,created_at,updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET content_json=EXCLUDED.content_json, updated_at=EXCLUDED.updated_at
            """,
            (resource.resource_id, student_id, course_id, knowledge_point_id, resource.type, resource.title, resource.difficulty, dumps(content), None, dumps(resource.source_refs), resource.personalized_reason, quality.get("score"), dumps(quality), created_by_skill, "published" if quality.get("passed", True) else "review", now, now),
        )
        return resource

    def get_resource(self, resource_id: str) -> LearningResource | None:
        row = self.fetchone("SELECT * FROM resources WHERE id=%s", (resource_id,))
        if not row:
            return None
        content = row.get("content_json") if isinstance(row.get("content_json"), dict) else loads(row.get("content_json"), {})
        quality = row.get("verifier_result") if isinstance(row.get("verifier_result"), dict) else loads(row.get("verifier_result"), {})
        return LearningResource(resource_id=row["id"], type=row["type"], title=row["title"], target_topic=content.get("target_topic") or row["title"], difficulty=row.get("difficulty") or "adaptive", content=content, source_refs=row.get("source_refs") or [], personalized_reason=row.get("personalized_reason") or "", tags=content.get("tags", []), quality_check=VerifierResult(**quality) if quality else None)

    def list_resources(self, student_id: str = "demo-student", course_id: str | None = None, *, query: str | None = None, tag: str | None = None, resource_type: str | None = None, limit: int | None = None) -> list[LearningResource]:
        where = ["student_id=%s"]
        params: list[Any] = [student_id]
        if course_id:
            where.append("course_id=%s")
            params.append(course_id)
        params.append(limit or 500)
        rows = self.fetchall(f"SELECT id FROM resources WHERE {' AND '.join(where)} ORDER BY created_at LIMIT %s", tuple(params))
        resources = [resource for row in rows if (resource := self.get_resource(row["id"]))]
        if resource_type:
            resources = [resource for resource in resources if resource.type == resource_type]
        if query:
            resources = [resource for resource in resources if query.lower() in dumps(resource.model_dump()).lower()]
        return resources

    def save_course_document_from_chunks(self, course_id: str, title: str, chunks: list[str], file_url: str | None = None, parser: str = "api_text", document_id: str | None = None) -> dict[str, Any]:
        now = utc_now()
        doc_id = document_id or stable_id("doc-api", f"{course_id}:{title}:{'|'.join(chunks)}")
        self.execute(
            "INSERT INTO course_documents(id,course_id,title,file_url,parser,created_at) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title",
            (doc_id, course_id, title, file_url, parser, now),
        )
        self.execute("DELETE FROM document_chunks WHERE document_id=%s AND course_id=%s", (doc_id, course_id))
        saved = []
        for index, chunk in enumerate(chunks):
            chunk_id = stable_id("chunk", f"{doc_id}:{index}:{chunk}")
            source_ref = {"document_id": doc_id, "chunk_id": chunk_id, "course_id": course_id, "section": title, "quote_span": [0, min(80, len(chunk))], "confidence": 0.84, "source_type": "api_upload"}
            self.execute(
                "INSERT INTO document_chunks(id,document_id,course_id,chunk_index,content,source_ref,embedding,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (chunk_id, doc_id, course_id, index, chunk, dumps(source_ref), None, now),
            )
            saved.append({"chunk_id": chunk_id, "content": chunk, "source_ref": source_ref})
        return {"document_id": doc_id, "course_id": course_id, "title": title, "chunks": saved, "chunk_count": len(saved)}

    def retrieve_chunks(self, topic: str, limit: int = 3, course_id: str | None = None, *, min_score: float = 0.0) -> list[dict[str, Any]]:
        if course_id:
            rows = self.fetchall("SELECT * FROM document_chunks WHERE course_id=%s ORDER BY chunk_index LIMIT %s", (course_id, limit))
        else:
            rows = self.fetchall("SELECT * FROM document_chunks ORDER BY chunk_index LIMIT %s", (limit,))
        return [{"chunk_id": row["id"], "content": row["content"], "source_ref": row["source_ref"], "score": 1.0, "matched_terms": [], "vector_score": 0, "snippet": snippet_for(row["content"], topic)} for row in rows]

    def save_app(self, app: CanvasApp, *, student_id: str = "demo-student", course_id: str = "ai-course", agent: str = "app_canvas_agent", skill: str = "app_generation_skill") -> CanvasApp:
        layout = {"position": app.position.model_dump(), "size": app.size.model_dump(), "z_index": app.z_index, "group_id": app.group_id, "course_id": course_id}
        payload = dict(app.payload)
        payload["_actions"] = app.actions
        self.execute(
            """
            INSERT INTO canvas_apps(id,student_id,conversation_id,resource_id,app_type,title,icon,status,render_mode,state,layout,payload,source_refs,personalized_reason,created_by_agent,created_by_skill,created_at,updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET layout=EXCLUDED.layout,payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at
            """,
            (app.app_id, student_id, app.source.get("conversation_id"), app.source.get("resource_id"), app.app_type, app.title, app.icon, app.status, app.render_mode, app.state, dumps(layout), dumps(payload), dumps(app.source_refs), app.personalized_reason, agent, skill, app.created_at, utc_now()),
        )
        app.source["student_id"] = student_id
        app.source["course_id"] = course_id
        return app

    def _app_from_row(self, row: dict[str, Any]) -> CanvasApp:
        layout = row.get("layout") if isinstance(row.get("layout"), dict) else loads(row.get("layout"), {})
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else loads(row.get("payload"), {})
        actions = payload.pop("_actions", []) if isinstance(payload, dict) else []
        return CanvasApp(app_id=row["id"], app_type=row["app_type"], title=row["title"], icon=row.get("icon"), status=row["status"], render_mode=row["render_mode"], state=row["state"], position=CanvasPosition(**layout.get("position", {"x": 0, "y": 0})), size=CanvasSize(**layout.get("size", {"width": 320, "height": 220})), z_index=layout.get("z_index", 1), group_id=layout.get("group_id"), payload=payload, source={"resource_id": row.get("resource_id"), "conversation_id": row.get("conversation_id"), "student_id": row.get("student_id"), "course_id": layout.get("course_id")}, source_refs=row.get("source_refs") or [], personalized_reason=row.get("personalized_reason"), actions=actions, created_at=str(row["created_at"]), updated_at=str(row["updated_at"]))

    def list_apps(self, student_id: str = "demo-student", course_id: str | None = None, conversation_id: str | None = None) -> list[CanvasApp]:
        where = ["student_id=%s"]
        params: list[Any] = [student_id]
        if course_id:
            where.append("layout->>'course_id'=%s")
            params.append(course_id)
        rows = self.fetchall(f"SELECT * FROM canvas_apps WHERE {' AND '.join(where)} ORDER BY (layout->>'z_index')::int", tuple(params))
        return [self._app_from_row(row) for row in rows]

    def get_app(self, app_id: str, student_id: str | None = None, course_id: str | None = None) -> CanvasApp | None:
        where = ["id=%s"]
        params: list[Any] = [app_id]
        if student_id:
            where.append("student_id=%s")
            params.append(student_id)
        if course_id:
            where.append("layout->>'course_id'=%s")
            params.append(course_id)
        row = self.fetchone(f"SELECT * FROM canvas_apps WHERE {' AND '.join(where)}", tuple(params))
        return self._app_from_row(row) if row else None

    def update_app(self, app_id: str, patch: dict[str, Any], *, student_id: str | None = None, course_id: str | None = None) -> CanvasApp | None:
        app = self.get_app(app_id, student_id=student_id, course_id=course_id)
        if not app:
            return None
        if "title" in patch:
            app.title = str(patch["title"])
        if "icon" in patch:
            app.icon = str(patch["icon"])
        if "render_mode" in patch:
            app.render_mode = str(patch["render_mode"])
        if "state" in patch:
            app.state = patch["state"]
        if "position" in patch:
            app.position = CanvasPosition(**patch["position"])
        if "size" in patch:
            app.size = CanvasSize(**patch["size"])
        if "payload" in patch:
            app.payload.update(patch["payload"])
        if "status" in patch:
            app.status = patch["status"]
        if "actions" in patch and isinstance(patch["actions"], list):
            app.actions = patch["actions"]
        if "z_index" in patch:
            app.z_index = int(patch["z_index"])
        if "group_id" in patch:
            app.group_id = patch["group_id"]
        return self.save_app(app, student_id=student_id or str(app.source.get("student_id")), course_id=course_id or str(app.source.get("course_id")))

    def recent_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        return []

    def dashboard(self, student_id: str = "demo-student", course_id: str | None = None, conversation_id: str | None = None) -> DashboardSnapshot:
        profile = self.get_profile(student_id, course_id=course_id or "ai-course")
        memories = self.list_memories(student_id, course_id=course_id, limit=12)
        profile_mastery = profile.get("mastery_map", {})
        mastery = profile_mastery if isinstance(profile_mastery, dict) else {}
        raw_weak_points = profile.get("weak_points", [])
        if isinstance(raw_weak_points, list):
            weak_points = raw_weak_points
        elif raw_weak_points in (None, "", {}):
            weak_points = []
        else:
            weak_points = [str(raw_weak_points)]
        return DashboardSnapshot(student_id=student_id, profile=profile, mastery=mastery, weak_points=weak_points, recommendations=[], memory_evidence=memories, recent_runs=[], path_progress=0, canvas_activity=[])


def is_postgres_url(database_url: str) -> bool:
    return bool(re.match(r"^postgres(?:ql)?(\+psycopg)?://", database_url))
