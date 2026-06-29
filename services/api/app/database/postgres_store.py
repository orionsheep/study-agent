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
    ChatAppLink,
    DashboardSnapshot,
    EduMemoryItem,
    LearningResource,
    QuizQuestion,
    QuizSubmission,
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


def _iso(value: Any) -> str | None:
    """Normalize a DB timestamp/str to an ISO-8601 string.

    PostgreSQL returns ``timestamp without time zone`` columns as Python
    ``datetime`` objects; SQLite (and the legacy code path) stored them as
    ISO strings. Most pydantic models in this project declare ``created_at``
    as ``str``, so a raw ``datetime`` trips validation. This helper converts
    either form to a plain string, appending a ``Z`` when the value carries
    no timezone marker (matching the legacy SQLite format).
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # datetime → ISO string. naive datetimes get a trailing 'Z' to match the
    # legacy "2026-06-04T10:02:10Z" format the frontend expects.
    try:
        iso = value.isoformat()
    except (AttributeError, ValueError):
        return str(value)
    if "+" not in iso and not iso.endswith("Z"):
        iso = iso + "Z"
    return iso


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
            row["links"] = []
            row["resources"] = []
        if rows:
            message_ids = [row["id"] for row in rows]
            run_message_ids: dict[str, list[str]] = {}
            for row in rows:
                run_id = row.get("metadata", {}).get("run_id")
                if row.get("role") == "assistant" and run_id:
                    run_message_ids[str(run_id)] = [row["id"]]
            link_rows = self.fetchall(
                """
                SELECT id, message_id, app_id, label, action, anchor_text, source_run_id, created_at
                FROM chat_app_links
                WHERE message_id = ANY(%s) OR source_run_id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """,
                (message_ids, list(run_message_ids)),
            )
            links_by_message: dict[str, list[dict[str, Any]]] = {}
            for link_row in link_rows:
                direct_message_ids = [link_row["message_id"]] if link_row["message_id"] in message_ids else []
                run_message_targets = run_message_ids.get(str(link_row.get("source_run_id") or ""), [])
                for target_message_id in direct_message_ids or run_message_targets:
                    link = ChatAppLink(
                        link_id=link_row["id"],
                        message_id=target_message_id,
                        app_id=link_row["app_id"],
                        label=link_row["label"],
                        action=link_row["action"],
                        anchor_text=link_row.get("anchor_text"),
                        source_run_id=link_row.get("source_run_id"),
                        created_at=_iso(link_row["created_at"]),
                    ).model_dump()
                    links_by_message.setdefault(target_message_id, []).append(link)
            for row in rows:
                row["links"] = links_by_message.get(row["id"], [])
            resource_rows = self.fetchall(
                """
                SELECT
                  l.id AS link_id,
                  l.message_id AS link_message_id,
                  l.source_run_id AS link_source_run_id,
                  r.*
                FROM chat_resource_links l
                JOIN resources r ON r.id = l.resource_id
                WHERE l.message_id = ANY(%s) OR l.source_run_id = ANY(%s)
                ORDER BY l.created_at ASC, l.id ASC
                """,
                (message_ids, list(run_message_ids)),
            )
            resources_by_message: dict[str, list[dict[str, Any]]] = {}
            seen_resources: set[tuple[str, str]] = set()
            for resource_row in resource_rows:
                direct_message_ids = [resource_row["link_message_id"]] if resource_row["link_message_id"] in message_ids else []
                run_message_targets = run_message_ids.get(str(resource_row.get("link_source_run_id") or ""), [])
                resource = self._resource_from_row(resource_row)
                if not resource:
                    continue
                for target_message_id in direct_message_ids or run_message_targets:
                    key = (target_message_id, resource.resource_id)
                    if key in seen_resources:
                        continue
                    seen_resources.add(key)
                    resources_by_message.setdefault(target_message_id, []).append(resource.model_dump())
            for row in rows:
                row["resources"] = resources_by_message.get(row["id"], [])
        return rows

    def create_chat_link(self, message_id: str, app_id: str, label: str, action: str = "focus", run_id: str | None = None) -> ChatAppLink:
        link = ChatAppLink(message_id=message_id, app_id=app_id, label=label, action=action, source_run_id=run_id, anchor_text=label)
        self.execute(
            """
            INSERT INTO chat_app_links(id, message_id, app_id, label, action, anchor_text, source_run_id, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              label=EXCLUDED.label,
              action=EXCLUDED.action,
              anchor_text=EXCLUDED.anchor_text,
              source_run_id=EXCLUDED.source_run_id
            """,
            (link.link_id, link.message_id, link.app_id, link.label, link.action, link.anchor_text, link.source_run_id, link.created_at),
        )
        return link

    def create_chat_resource_link(self, message_id: str, resource_id: str, run_id: str | None = None) -> dict[str, Any]:
        link_id = stable_id("reslink", f"{message_id}:{resource_id}:{run_id or ''}")
        created_at = utc_now()
        self.execute(
            """
            INSERT INTO chat_resource_links(id, message_id, resource_id, source_run_id, created_at)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET source_run_id=EXCLUDED.source_run_id
            """,
            (link_id, message_id, resource_id, run_id, created_at),
        )
        return {
            "id": link_id,
            "message_id": message_id,
            "resource_id": resource_id,
            "source_run_id": run_id,
            "created_at": created_at,
        }

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
            valid_from=_iso(row["valid_from"]),
            valid_until=_iso(row["valid_until"]),
            embedding=row.get("embedding"),
            tags=list(row.get("tags") or []),
            version=row["version"],
            created_at=_iso(row["created_at"]),
            updated_at=_iso(row["updated_at"]),
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

    def _resource_from_row(self, row: dict[str, Any]) -> LearningResource | None:
        if not row:
            return None
        content = row.get("content_json") if isinstance(row.get("content_json"), dict) else loads(row.get("content_json"), {})
        quality = row.get("verifier_result") if isinstance(row.get("verifier_result"), dict) else loads(row.get("verifier_result"), {})
        return LearningResource(resource_id=row["id"], type=row["type"], title=row["title"], target_topic=content.get("target_topic") or row["title"], difficulty=row.get("difficulty") or "adaptive", content=content, source_refs=row.get("source_refs") or [], personalized_reason=row.get("personalized_reason") or "", tags=content.get("tags", []), quality_check=VerifierResult(**quality) if quality else None)

    def get_resource(self, resource_id: str) -> LearningResource | None:
        row = self.fetchone("SELECT * FROM resources WHERE id=%s", (resource_id,))
        return self._resource_from_row(row)

    def list_resources(self, student_id: str = "demo-student", course_id: str | None = None, *, query: str | None = None, tag: str | None = None, resource_type: str | None = None, limit: int | None = None) -> list[LearningResource]:
        # Full rows in one query (avoids per-row get_resource() N+1); type pushed to SQL.
        where = ["student_id=%s"]
        params: list[Any] = [student_id]
        if course_id:
            where.append("(course_id=%s OR course_id IS NULL)")
            params.append(course_id)
        if resource_type:
            where.append("type=%s")
            params.append(resource_type)
        params.append(limit or 500)
        rows = self.fetchall(f"SELECT * FROM resources WHERE {' AND '.join(where)} ORDER BY created_at LIMIT %s", tuple(params))
        resources = [resource for row in rows if (resource := self._resource_from_row(row))]
        if tag:
            normalized_tag = (tag or "").casefold()
            resources = [
                resource
                for resource in resources
                if normalized_tag in {item.casefold() for item in resource.tags}
                or normalized_tag in str(resource.content.get("module_name", "")).casefold()
            ]
        if query:
            resources = [resource for resource in resources if (query or "").lower() in dumps(resource.model_dump()).lower()]
        return resources

    def save_learning_focus(self, student_id: str, course_id: str, topic: str, objective: str | None = None, course_label: str | None = None) -> None:
        from datetime import datetime, timezone
        focus = {
            "topic": topic,
            "objective": objective or "",
            "course_label": course_label or "",
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
        }
        profile = self.get_profile(student_id, course_id=course_id)
        profile["_learning_focus"] = focus
        self.save_profile(student_id, profile, course_id=course_id)

    def get_learning_focus(self, student_id: str, course_id: str) -> dict[str, str]:
        focus = (self.get_profile(student_id, course_id=course_id) or {}).get("_learning_focus") or {}
        return focus if isinstance(focus, dict) else {}

    def save_course_document_from_chunks(
        self,
        course_id: str,
        title: str,
        chunks: list[str],
        file_url: str | None = None,
        parser: str = "api_text",
        document_id: str | None = None,
        ingest_type: str = "course_seed",
        owner_scope: str = "course",
        owner_id: str | None = None,
        source_scope: str = "course_official",
        original_url: str | None = None,
        mime_type: str | None = None,
        upload_status: str = "ready",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        doc_id = document_id or stable_id("doc-api", f"{course_id}:{title}:{'|'.join(chunks)}")
        self.execute(
            """
            INSERT INTO course_documents(
              id,course_id,title,file_url,parser,ingest_type,owner_scope,owner_id,
              source_scope,original_url,mime_type,upload_status,metadata,created_at
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              title=EXCLUDED.title,
              file_url=EXCLUDED.file_url,
              parser=EXCLUDED.parser,
              ingest_type=EXCLUDED.ingest_type,
              owner_scope=EXCLUDED.owner_scope,
              owner_id=EXCLUDED.owner_id,
              source_scope=EXCLUDED.source_scope,
              original_url=EXCLUDED.original_url,
              mime_type=EXCLUDED.mime_type,
              upload_status=EXCLUDED.upload_status,
              metadata=EXCLUDED.metadata
            """,
            (
                doc_id,
                course_id,
                title,
                file_url,
                parser,
                ingest_type,
                owner_scope,
                owner_id,
                source_scope,
                original_url,
                mime_type,
                upload_status,
                dumps(metadata or {}),
                now,
            ),
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
        return {
            "document_id": doc_id,
            "course_id": course_id,
            "title": title,
            "ingest_type": ingest_type,
            "owner_scope": owner_scope,
            "owner_id": owner_id,
            "source_scope": source_scope,
            "original_url": original_url,
            "mime_type": mime_type,
            "upload_status": upload_status,
            "metadata": metadata or {},
            "chunks": saved,
            "chunk_count": len(saved),
        }

    def list_course_documents(self, course_id: str) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT d.id AS document_id, d.course_id, d.title, d.file_url, d.parser, d.created_at,
                   d.ingest_type, d.owner_scope, d.owner_id, d.source_scope, d.original_url,
                   d.mime_type, d.upload_status, d.metadata,
                   COUNT(c.id) AS chunk_count
            FROM course_documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id AND c.course_id = d.course_id
            WHERE d.course_id=%s
            GROUP BY d.id, d.course_id, d.title, d.file_url, d.parser, d.created_at,
                     d.ingest_type, d.owner_scope, d.owner_id, d.source_scope, d.original_url,
                     d.mime_type, d.upload_status, d.metadata
            ORDER BY d.created_at DESC
            """,
            (course_id,),
        )
        for row in rows:
            if not isinstance(row.get("metadata"), dict):
                row["metadata"] = loads(row.get("metadata"), {})
        return rows

    def list_document_chunks(self, course_id: str, document_id: str) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT id AS chunk_id, document_id, course_id, chunk_index, content, source_ref, embedding, created_at
            FROM document_chunks
            WHERE course_id=%s AND document_id=%s
            ORDER BY chunk_index
            """,
            (course_id, document_id),
        )
        for row in rows:
            if not isinstance(row.get("source_ref"), dict):
                row["source_ref"] = loads(row.get("source_ref"), {})
            if not isinstance(row.get("embedding"), list):
                row["embedding"] = loads(row.get("embedding"), [])
        return rows

    def _ensure_notebook_schema(self) -> None:
        self.create_schema()

    def _course_title(self, course_id: str) -> str:
        row = self.fetchone("SELECT title FROM courses WHERE id=%s", (course_id,))
        return str(row["title"]) if row and row.get("title") else course_id

    def _ensure_course_notebook_sources(self, *, course_id: str) -> None:
        self._ensure_notebook_schema()
        now = utc_now()
        course_notebook_id = stable_id("nblm", f"course:{course_id}:official")
        if not self.fetchone("SELECT 1 FROM notebooks WHERE id=%s", (course_notebook_id,)):
            return
        for document in self.list_course_documents(course_id):
            document_id = str(document["document_id"])
            self.execute(
                """
                INSERT INTO notebook_sources(id, notebook_id, source_id, source_kind, source_role, sync_status, open_notebook_source_id, synced_at, created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (notebook_id, source_id) DO NOTHING
                """,
                (
                    stable_id("nbsrc", f"{course_notebook_id}:{document_id}"),
                    course_notebook_id,
                    document_id,
                    "course_document",
                    "official",
                    "not_synced",
                    None,
                    None,
                    now,
                ),
            )

    def ensure_default_notebooks(self, *, student_id: str, course_id: str) -> list[dict[str, Any]]:
        self._ensure_notebook_schema()
        now = utc_now()
        course_title = self._course_title(course_id)
        defaults = [
            {
                "id": stable_id("nblm", f"course:{course_id}:official"),
                "owner_scope": "course",
                "owner_id": course_id,
                "course_id": course_id,
                "title": f"{course_title} · 课程知识库",
                "purpose": "course_official",
                "description": "课程级正式资料，用于学习路径、资源生成、引用校验和 NotebookLM 复习。",
                "tags": ["课程正式资料", "Source of Truth"],
                "rank": 10,
                "assigned_reason": "系统根据当前课程自动分配。",
            },
            {
                "id": stable_id("nblm", f"user:{student_id}:{course_id}:review"),
                "owner_scope": "user",
                "owner_id": student_id,
                "course_id": course_id,
                "title": "我的复习 Notebook",
                "purpose": "personal_review",
                "description": "用户上传和临时复习资料，不会自动进入课程正式知识库。",
                "tags": ["我的上传", "复习"],
                "rank": 40,
                "assigned_reason": "个人复习空间。",
            },
        ]
        for item in defaults:
            self.execute(
                """
                INSERT INTO notebooks(id, owner_scope, owner_id, course_id, title, purpose, description, tags, open_notebook_id, sync_status, created_at, updated_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    item["id"],
                    item["owner_scope"],
                    item["owner_id"],
                    item["course_id"],
                    item["title"],
                    item["purpose"],
                    item["description"],
                    dumps(item["tags"]),
                    None,
                    "not_synced",
                    now,
                    now,
                ),
            )
            self.execute(
                """
                INSERT INTO notebook_assignments(id, notebook_id, student_id, course_id, status, rank, assigned_reason, created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (notebook_id, student_id, course_id) DO NOTHING
                """,
                (
                    stable_id("nassign", f"{item['id']}:{student_id}:{course_id}"),
                    item["id"],
                    student_id,
                    course_id,
                    "active",
                    item["rank"],
                    item["assigned_reason"],
                    now,
                ),
            )
        self._ensure_course_notebook_sources(course_id=course_id)
        return self.list_notebooks(student_id=student_id, course_id=course_id)

    def list_notebooks(self, *, student_id: str, course_id: str) -> list[dict[str, Any]]:
        self._ensure_notebook_schema()
        if not self.fetchone("SELECT 1 FROM notebook_assignments WHERE student_id=%s AND course_id=%s LIMIT 1", (student_id, course_id)):
            return self.ensure_default_notebooks(student_id=student_id, course_id=course_id)
        self._ensure_course_notebook_sources(course_id=course_id)
        rows = self.fetchall(
            """
            SELECT n.*, a.status AS assignment_status, a.rank, a.assigned_reason,
                   COUNT(ns.source_id) AS source_count
            FROM notebook_assignments a
            JOIN notebooks n ON n.id = a.notebook_id
            LEFT JOIN notebook_sources ns ON ns.notebook_id = n.id
            WHERE a.student_id=%s AND a.course_id=%s AND a.status != 'archived'
            GROUP BY n.id, n.owner_scope, n.owner_id, n.course_id, n.title, n.purpose, n.description, n.tags,
                     n.open_notebook_id, n.sync_status, n.created_at, n.updated_at,
                     a.status, a.rank, a.assigned_reason
            ORDER BY a.rank ASC, n.updated_at DESC
            """,
            (student_id, course_id),
        )
        for row in rows:
            if not isinstance(row.get("tags"), list):
                row["tags"] = loads(row.get("tags"), [])
        return rows

    def get_notebook(self, notebook_id: str, *, student_id: str | None = None, course_id: str | None = None) -> dict[str, Any] | None:
        self._ensure_notebook_schema()
        if student_id and course_id:
            row = self.fetchone(
                """
                SELECT n.* FROM notebooks n
                JOIN notebook_assignments a ON a.notebook_id = n.id
                WHERE n.id=%s AND a.student_id=%s AND a.course_id=%s AND a.status != 'archived'
                """,
                (notebook_id, student_id, course_id),
            )
        else:
            row = self.fetchone("SELECT * FROM notebooks WHERE id=%s", (notebook_id,))
        if not row:
            return None
        if not isinstance(row.get("tags"), list):
            row["tags"] = loads(row.get("tags"), [])
        return row

    def create_notebook(
        self,
        *,
        student_id: str,
        course_id: str,
        title: str,
        purpose: str = "personal_review",
        description: str | None = None,
        tags: list[str] | None = None,
        owner_scope: str = "user",
        owner_id: str | None = None,
        rank: int = 50,
    ) -> dict[str, Any]:
        self._ensure_notebook_schema()
        now = utc_now()
        notebook_id = new_id("nblm")
        cleaned_title = (title or "我的 Notebook").strip() or "我的 Notebook"
        self.execute(
            """
            INSERT INTO notebooks(id, owner_scope, owner_id, course_id, title, purpose, description, tags, open_notebook_id, sync_status, created_at, updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                notebook_id,
                owner_scope,
                owner_id or student_id,
                course_id,
                cleaned_title,
                purpose,
                description or "",
                dumps(tags or ["我的上传"]),
                None,
                "not_synced",
                now,
                now,
            ),
        )
        self.execute(
            """
            INSERT INTO notebook_assignments(id, notebook_id, student_id, course_id, status, rank, assigned_reason, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (notebook_id, student_id, course_id) DO NOTHING
            """,
            (
                stable_id("nassign", f"{notebook_id}:{student_id}:{course_id}"),
                notebook_id,
                student_id,
                course_id,
                "active",
                rank,
                "用户创建的个人 Notebook。",
                now,
            ),
        )
        notebook = self.get_notebook(notebook_id, student_id=student_id, course_id=course_id)
        return notebook or {"id": notebook_id, "title": cleaned_title, "purpose": purpose, "source_count": 0}

    def attach_document_to_notebook(
        self,
        *,
        notebook_id: str,
        document_id: str,
        student_id: str,
        course_id: str,
        source_role: str = "primary",
        source_kind: str = "course_document",
    ) -> dict[str, Any] | None:
        self._ensure_notebook_schema()
        if not self.get_notebook(notebook_id, student_id=student_id, course_id=course_id):
            return None
        document = self.fetchone("SELECT id FROM course_documents WHERE id=%s AND course_id=%s", (document_id, course_id))
        if not document:
            return None
        now = utc_now()
        source_id = stable_id("nbsrc", f"{notebook_id}:{document_id}")
        self.execute(
            """
            INSERT INTO notebook_sources(id, notebook_id, source_id, source_kind, source_role, sync_status, open_notebook_source_id, synced_at, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (notebook_id, source_id) DO NOTHING
            """,
            (source_id, notebook_id, document_id, source_kind, source_role, "not_synced", None, None, now),
        )
        self.execute("UPDATE notebooks SET updated_at=%s WHERE id=%s", (now, notebook_id))
        return {
            "id": source_id,
            "notebook_id": notebook_id,
            "source_id": document_id,
            "source_kind": source_kind,
            "source_role": source_role,
            "sync_status": "not_synced",
            "created_at": now,
        }

    def set_notebook_open_notebook_id(self, notebook_id: str, open_notebook_id: str, sync_status: str = "ready") -> None:
        self._ensure_notebook_schema()
        self.execute(
            "UPDATE notebooks SET open_notebook_id=%s, sync_status=%s, updated_at=%s WHERE id=%s",
            (open_notebook_id, sync_status, utc_now(), notebook_id),
        )

    def mark_notebook_source_synced(self, notebook_id: str, source_id: str, open_notebook_source_id: str | None, sync_status: str) -> None:
        self._ensure_notebook_schema()
        self.execute(
            """
            UPDATE notebook_sources
            SET open_notebook_source_id=%s, sync_status=%s, synced_at=%s
            WHERE notebook_id=%s AND source_id=%s
            """,
            (open_notebook_source_id, sync_status, utc_now(), notebook_id, source_id),
        )

    def list_notebook_sources(self, notebook_id: str, *, student_id: str | None = None, course_id: str | None = None) -> list[dict[str, Any]]:
        self._ensure_notebook_schema()
        if student_id and course_id and not self.get_notebook(notebook_id, student_id=student_id, course_id=course_id):
            return []
        rows = self.fetchall(
            """
            SELECT ns.*, d.course_id, d.title, d.file_url, d.parser,
                   d.ingest_type, d.owner_scope, d.owner_id, d.source_scope, d.original_url,
                   d.mime_type, d.upload_status, d.metadata,
                   d.created_at AS document_created_at
            FROM notebook_sources ns
            JOIN course_documents d ON d.id = ns.source_id
            WHERE ns.notebook_id=%s AND ns.source_kind='course_document'
            ORDER BY d.created_at DESC
            """,
            (notebook_id,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row.get("metadata"), dict):
                row["metadata"] = loads(row.get("metadata"), {})
            chunks = self.list_document_chunks(str(row["course_id"]), str(row["source_id"]))
            refs = []
            for chunk in chunks[:12]:
                source_ref = chunk.get("source_ref") if isinstance(chunk.get("source_ref"), dict) else {}
                refs.append({**source_ref, "document_id": row["source_id"], "chunk_id": chunk.get("chunk_id"), "title": row.get("title") or row["source_id"], "snippet": str(chunk.get("content") or "")[:360]})
            row["id"] = row["source_id"]
            row["summary"] = refs[0]["snippet"] if refs else ""
            row["chunk_count"] = len(chunks)
            row["source_refs"] = refs
            result.append(row)
        return result

    def record_notebook_memory_event(self, *, notebook_id: str | None, student_id: str, course_id: str | None, event_type: str, source_refs: list[dict[str, Any]] | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_notebook_schema()
        event_id = new_id("nbevt")
        now = utc_now()
        self.execute(
            """
            INSERT INTO notebook_memory_events(id, notebook_id, student_id, course_id, event_type, source_refs, payload, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (event_id, notebook_id, student_id, course_id, event_type, dumps(source_refs or []), dumps(payload or {}), now),
        )
        return {"id": event_id, "notebook_id": notebook_id, "student_id": student_id, "course_id": course_id, "event_type": event_type, "source_refs": source_refs or [], "payload": payload or {}, "created_at": now}

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
        return CanvasApp(app_id=row["id"], app_type=row["app_type"], title=row["title"], icon=row.get("icon"), status=row["status"], render_mode=row["render_mode"], state=row["state"], position=CanvasPosition(**layout.get("position", {"x": 0, "y": 0})), size=CanvasSize(**layout.get("size", {"width": 320, "height": 220})), z_index=layout.get("z_index", 1), group_id=layout.get("group_id"), payload=payload, source={"resource_id": row.get("resource_id"), "conversation_id": row.get("conversation_id"), "student_id": row.get("student_id"), "course_id": layout.get("course_id")}, source_refs=row.get("source_refs") or [], personalized_reason=row.get("personalized_reason"), actions=actions, created_at=_iso(row["created_at"]), updated_at=_iso(row["updated_at"]))

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

    def _artifact_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifact_id": row["id"],
            "kind": row["kind"],
            "object_key": row["object_key"],
            "content_type": row["content_type"],
            "sha256": row["sha256"],
            "size_bytes": int(row["size_bytes"] or 0),
            "title": row.get("title"),
            "source_run_id": row.get("source_run_id"),
            "student_id": row.get("student_id"),
            "course_id": row.get("course_id"),
            "conversation_id": row.get("conversation_id"),
            "metadata": row.get("metadata_json") or {},
            "created_at": _iso(row["created_at"]),
        }

    def save_artifact(
        self,
        *,
        artifact_id: str,
        kind: str,
        object_key: str,
        content_type: str,
        sha256: str,
        size_bytes: int,
        title: str | None = None,
        source_run_id: str | None = None,
        student_id: str | None = None,
        course_id: str | None = None,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        self.execute(
            """
            INSERT INTO artifacts(
              id, kind, object_key, content_type, sha256, size_bytes, title, source_run_id,
              student_id, course_id, conversation_id, metadata_json, created_at
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              kind=EXCLUDED.kind,
              object_key=EXCLUDED.object_key,
              content_type=EXCLUDED.content_type,
              sha256=EXCLUDED.sha256,
              size_bytes=EXCLUDED.size_bytes,
              title=EXCLUDED.title,
              source_run_id=EXCLUDED.source_run_id,
              student_id=EXCLUDED.student_id,
              course_id=EXCLUDED.course_id,
              conversation_id=EXCLUDED.conversation_id,
              metadata_json=EXCLUDED.metadata_json
            """,
            (
                artifact_id,
                kind,
                object_key,
                content_type,
                sha256,
                int(size_bytes),
                title,
                source_run_id,
                student_id,
                course_id,
                conversation_id,
                dumps(metadata or {}),
                now,
            ),
        )
        row = self.fetchone("SELECT * FROM artifacts WHERE id=%s", (artifact_id,))
        return self._artifact_from_row(row) if row else {
            "artifact_id": artifact_id,
            "kind": kind,
            "object_key": object_key,
            "content_type": content_type,
            "sha256": sha256,
            "size_bytes": int(size_bytes),
            "title": title,
            "source_run_id": source_run_id,
            "student_id": student_id,
            "course_id": course_id,
            "conversation_id": conversation_id,
            "metadata": metadata or {},
            "created_at": now,
        }

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM artifacts WHERE id=%s", (artifact_id,))
        return self._artifact_from_row(row) if row else None

    def latest_artifact_for_context(
        self,
        *,
        student_id: str,
        course_id: str | None = None,
        conversation_id: str | None = None,
        kinds: list[str] | None = None,
    ) -> dict[str, Any] | None:
        where = ["student_id=%s"]
        params: list[Any] = [student_id]
        if course_id:
            where.append("course_id=%s")
            params.append(course_id)
        if conversation_id:
            where.append("conversation_id=%s")
            params.append(conversation_id)
        if kinds:
            where.append("kind = ANY(%s)")
            params.append(kinds)
        row = self.fetchone(
            f"SELECT * FROM artifacts WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 1",
            tuple(params),
        )
        return self._artifact_from_row(row) if row else None

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

    def create_run(self, student_id: str, task_type: str, input_json: dict[str, Any]) -> str:
        run_id = new_id("run")
        now = utc_now()
        self.execute(
            """
            INSERT INTO agent_runs(id, student_id, task_type, input_json, output_json, status, model_name, latency_ms, created_at, updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (run_id, student_id, task_type, dumps(input_json or {}), dumps({}), "running", None, 0, now, now),
        )
        return run_id

    def add_step(
        self,
        run_id: str,
        order: int,
        name: str,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        status: str = "completed",
    ) -> str:
        step_id = new_id("step")
        self.execute(
            """
            INSERT INTO agent_steps(id, run_id, step_order, agent_or_skill, input_json, output_json, status, latency_ms, error_message, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (step_id, run_id, order, name, dumps(input_json or {}), dumps(output_json or {}), status, 0, None, utc_now()),
        )
        return step_id

    def finish_run(self, run_id: str, output_json: dict[str, Any], status: str = "completed") -> None:
        self.execute(
            "UPDATE agent_runs SET output_json=%s, status=%s, updated_at=%s WHERE id=%s",
            (dumps(output_json or {}), status, utc_now(), run_id),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM agent_runs WHERE id=%s", (run_id,))
        if not row:
            return None
        steps = self.fetchall("SELECT * FROM agent_steps WHERE run_id=%s ORDER BY step_order", (run_id,))
        return {
            "run_id": row["id"],
            "student_id": row["student_id"],
            "task_type": row["task_type"],
            "input_json": row.get("input_json") if isinstance(row.get("input_json"), dict) else loads(row.get("input_json"), {}),
            "output_json": row.get("output_json") if isinstance(row.get("output_json"), dict) else loads(row.get("output_json"), {}),
            "status": row["status"],
            "model_name": row.get("model_name"),
            "latency_ms": row.get("latency_ms") or 0,
            "created_at": _iso(row["created_at"]),
            "updated_at": _iso(row["updated_at"]),
            "steps": [
                {
                    **dict(step),
                    "input_json": step.get("input_json") if isinstance(step.get("input_json"), dict) else loads(step.get("input_json"), {}),
                    "output_json": step.get("output_json") if isinstance(step.get("output_json"), dict) else loads(step.get("output_json"), {}),
                    "created_at": _iso(step["created_at"]),
                }
                for step in steps
            ],
        }

    def recent_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM agent_runs ORDER BY updated_at DESC LIMIT %s", (limit,))
        return [
            {
                "run_id": row["id"],
                "task_type": row["task_type"],
                "status": row["status"],
                "created_at": _iso(row["created_at"]),
            }
            for row in rows
        ]

    def save_quiz_question(self, question: QuizQuestion, resource_id: str | None = None) -> QuizQuestion:
        self.execute(
            """
            INSERT INTO quiz_questions(id, resource_id, question_type, prompt, options, answer, explanation, knowledge_point_id, difficulty, misconception_tags, source_refs)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              resource_id=EXCLUDED.resource_id,
              question_type=EXCLUDED.question_type,
              prompt=EXCLUDED.prompt,
              options=EXCLUDED.options,
              answer=EXCLUDED.answer,
              explanation=EXCLUDED.explanation,
              knowledge_point_id=EXCLUDED.knowledge_point_id,
              difficulty=EXCLUDED.difficulty,
              misconception_tags=EXCLUDED.misconception_tags,
              source_refs=EXCLUDED.source_refs
            """,
            (
                question.question_id,
                resource_id,
                question.question_type,
                question.prompt,
                dumps(question.options),
                dumps(question.answer),
                question.explanation,
                question.knowledge_point_id,
                question.difficulty,
                dumps(question.misconception_tags),
                dumps(question.source_refs),
            ),
        )
        return question

    def get_quiz_question(self, question_id: str) -> QuizQuestion | None:
        row = self.fetchone("SELECT * FROM quiz_questions WHERE id=%s", (question_id,))
        if not row:
            return None
        return QuizQuestion(
            question_id=row["id"],
            question_type=row["question_type"],
            prompt=row["prompt"],
            options=row.get("options") if isinstance(row.get("options"), list) else loads(row.get("options"), []),
            answer=row.get("answer") if not isinstance(row.get("answer"), str) else loads(row.get("answer"), row.get("answer")),
            explanation=row.get("explanation") or "",
            knowledge_point_id=row.get("knowledge_point_id"),
            difficulty=row.get("difficulty") or "adaptive",
            misconception_tags=row.get("misconception_tags") if isinstance(row.get("misconception_tags"), list) else loads(row.get("misconception_tags"), []),
            source_refs=row.get("source_refs") if isinstance(row.get("source_refs"), list) else loads(row.get("source_refs"), []),
        )

    def save_quiz_submission(self, submission: QuizSubmission) -> QuizSubmission:
        self.execute(
            """
            INSERT INTO quiz_submissions(id, student_id, question_id, answer, is_correct, evaluation, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              answer=EXCLUDED.answer,
              is_correct=EXCLUDED.is_correct,
              evaluation=EXCLUDED.evaluation
            """,
            (
                submission.submission_id,
                submission.student_id,
                submission.question_id,
                dumps(submission.answer),
                bool(submission.is_correct),
                dumps(submission.evaluation),
                submission.created_at,
            ),
        )
        return submission

    def ensure_openstax_book_seeds(self) -> list[dict[str, Any]]:
        from app.cram.openstax_seed import OPENSTAX_CRAM_BOOKS

        now = utc_now()
        for book in OPENSTAX_CRAM_BOOKS:
            self.execute(
                """
                INSERT INTO openstax_book_seeds(
                  id, slug, title, subject, provider, exam_mode, details_url, web_url,
                  pdf_url, license, metadata, created_at, updated_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (slug) DO UPDATE SET
                  title=EXCLUDED.title,
                  subject=EXCLUDED.subject,
                  provider=EXCLUDED.provider,
                  exam_mode=EXCLUDED.exam_mode,
                  details_url=EXCLUDED.details_url,
                  web_url=EXCLUDED.web_url,
                  pdf_url=EXCLUDED.pdf_url,
                  license=EXCLUDED.license,
                  metadata=EXCLUDED.metadata,
                  updated_at=EXCLUDED.updated_at
                """,
                (
                    stable_id("openstax", book.slug),
                    book.slug,
                    book.title,
                    book.subject,
                    book.provider,
                    book.exam_mode,
                    book.details_url,
                    book.web_url,
                    book.pdf_url,
                    book.license,
                    dumps({"tags": book.tags}),
                    now,
                    now,
                ),
            )
        return self.list_openstax_book_seeds()

    def list_openstax_book_seeds(self) -> list[dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM openstax_book_seeds ORDER BY subject, title")
        if not rows:
            return self.ensure_openstax_book_seeds()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = row.get("metadata") if isinstance(row.get("metadata"), dict) else loads(row.get("metadata"), {})
            item["created_at"] = _iso(item.get("created_at"))
            item["updated_at"] = _iso(item.get("updated_at"))
            result.append(item)
        return result

    def save_cram_session(self, session: Any) -> Any:
        from app.cram.engine import CramSession

        typed = session if isinstance(session, CramSession) else CramSession.model_validate(session)
        self.execute(
            """
            INSERT INTO cram_sessions(id, student_id, course_id, course_title, status, stage, session_json, created_at, updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
              course_title=EXCLUDED.course_title,
              status=EXCLUDED.status,
              stage=EXCLUDED.stage,
              session_json=EXCLUDED.session_json,
              updated_at=EXCLUDED.updated_at
            """,
            (
                typed.session_id,
                typed.student_id,
                typed.course_id,
                typed.course_title,
                typed.status,
                typed.stage.value,
                dumps(typed.model_dump(mode="json")),
                typed.created_at,
                typed.updated_at,
            ),
        )
        return typed

    def create_cram_session(self, request: Any) -> Any:
        from app.cram.engine import CramSessionCreate, create_cram_session

        data = request if isinstance(request, CramSessionCreate) else CramSessionCreate.model_validate(request)
        now = utc_now()
        self.execute(
            "INSERT INTO students(id, display_name, created_at, updated_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
            (data.student_id, data.student_id, now, now),
        )
        self.execute(
            "INSERT INTO courses(id, title, description, created_at) VALUES(%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title",
            (data.course_id, data.course_title, "Cram Engine exam sprint course.", now),
        )
        session = create_cram_session(data)
        saved = self.save_cram_session(session)
        self.record_cram_stage_event(saved, "cram.session.created", {"exam_types": data.exam_types})
        return saved

    def _cram_session_from_value(self, value: Any) -> Any:
        from app.cram.engine import CramSession

        payload = value if isinstance(value, dict) else loads(value, {})
        return CramSession.model_validate(payload)

    def get_cram_session(self, session_id: str, *, student_id: str | None = None, course_id: str | None = None) -> Any | None:
        clauses = ["id=%s"]
        params: list[Any] = [session_id]
        if student_id:
            clauses.append("student_id=%s")
            params.append(student_id)
        if course_id:
            clauses.append("course_id=%s")
            params.append(course_id)
        row = self.fetchone("SELECT session_json FROM cram_sessions WHERE " + " AND ".join(clauses), tuple(params))
        return self._cram_session_from_value(row["session_json"]) if row else None

    def list_cram_sessions(self, student_id: str, course_id: str | None = None, *, limit: int = 12) -> list[Any]:
        if course_id:
            rows = self.fetchall(
                "SELECT session_json FROM cram_sessions WHERE student_id=%s AND course_id=%s ORDER BY updated_at DESC LIMIT %s",
                (student_id, course_id, limit),
            )
        else:
            rows = self.fetchall(
                "SELECT session_json FROM cram_sessions WHERE student_id=%s ORDER BY updated_at DESC LIMIT %s",
                (student_id, limit),
            )
        return [self._cram_session_from_value(row["session_json"]) for row in rows]

    def advance_cram_session(self, session_id: str, *, action: str, payload: dict[str, Any] | None = None, student_id: str | None = None, course_id: str | None = None) -> Any:
        from app.cram.engine import advance_cram_session

        session = self.get_cram_session(session_id, student_id=student_id, course_id=course_id)
        if not session:
            raise ValueError("cram_session_not_found")
        updated = advance_cram_session(session, action=action, payload=payload or {})
        self.save_cram_session(updated)
        self.record_cram_stage_event(updated, action, payload or {})
        return updated

    def record_cram_stage_event(self, session: Any, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event_id = new_id("cramevt")
        event_payload = payload or {}
        self.execute(
            """
            INSERT INTO cram_stage_events(id, session_id, student_id, course_id, stage, event_type, payload, created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                event_id,
                session.session_id,
                session.student_id,
                session.course_id,
                session.stage.value,
                event_type,
                dumps(event_payload),
                utc_now(),
            ),
        )
        return {"id": event_id, "session_id": session.session_id, "event_type": event_type, "payload": event_payload}

    def cram_dashboard_summary(self, student_id: str, course_id: str | None = None) -> dict[str, Any]:
        from app.cram.engine import build_cram_dashboard_summary
        from app.cram.openstax_seed import OPENSTAX_CRAM_BOOKS

        sessions = self.list_cram_sessions(student_id, course_id=course_id)
        self.ensure_openstax_book_seeds()
        return build_cram_dashboard_summary(sessions, OPENSTAX_CRAM_BOOKS)

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
        return DashboardSnapshot(
            student_id=student_id,
            profile=profile,
            mastery=mastery,
            weak_points=weak_points,
            recommendations=[],
            memory_evidence=memories,
            recent_runs=self.recent_runs(),
            path_progress=0,
            canvas_activity=[],
            cram=self.cram_dashboard_summary(student_id, course_id=course_id),
        )


def is_postgres_url(database_url: str) -> bool:
    return bool(re.match(r"^postgres(?:ql)?(\+psycopg)?://", database_url))
