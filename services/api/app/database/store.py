from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.database.schema import REQUIRED_TABLES, SQLITE_SCHEMA
from app.edumem0.decay_policy import DecayPolicy
from app.rag.embeddings import cosine_similarity, embed_text
from app.schemas.app_protocol import (
    AppEvent,
    CanvasApp,
    CanvasPosition,
    CanvasSize,
    ChatAppLink,
    DashboardSnapshot,
    EduMemoryItem,
    LearningPath,
    LearningPathStage,
    LearningResource,
    QuizQuestion,
    QuizSubmission,
    new_id,
    utc_now,
    VerifierResult,
)


def _parse_iso_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value)


def strip_raw_html_report_text(text: str) -> str:
    value = str(text or "")
    marker = "---HERMES_HTML_OUTPUT---"
    if marker in value:
        prefix = value.split(marker, 1)[0].strip()
        return prefix or "✅ 分析完成！报告已生成并推送到画布。"
    lower = value.lower()
    starts = [index for index in (lower.find("<!doctype html"), lower.find("<html")) if index >= 0]
    if starts:
        prefix = value[: min(starts)].strip()
        return prefix or "✅ 分析完成！报告已生成并推送到画布。"
    if "<style" in lower and "{" in value and "}" in value:
        return "✅ 分析完成！报告已生成并推送到画布。"
    return value


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def merge_profile_values(old: Any, new: Any) -> Any:
    if new in (None, "", [], {}):
        return old
    if isinstance(old, dict) and isinstance(new, dict):
        merged = dict(old)
        for key, value in new.items():
            merged[key] = merge_profile_values(merged.get(key), value)
        return merged
    if isinstance(old, list) or isinstance(new, list):
        values = old if isinstance(old, list) else ([old] if old not in (None, "") else [])
        additions = new if isinstance(new, list) else [new]
        result: list[Any] = []
        seen: set[str] = set()
        for item in [*values, *additions]:
            if item in (None, ""):
                continue
            key = dumps(item) if isinstance(item, (dict, list)) else str(item)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
    return new


def merge_profile_dicts(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    merged = dict(old or {})
    for key, value in (new or {}).items():
        merged[key] = merge_profile_values(merged.get(key), value)
    return merged


def first_heading_or_title(text: str, title: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#"):
            return cleaned.strip("# ").strip()[:80] or title
        if re.match(r"^(第[一二三四五六七八九十0-9]+[章节]|[0-9]+[.、])", cleaned):
            return cleaned[:80]
    return title


def snippet_for(text: str, query: str, size: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return ""
    query = (query or "").strip()
    if query:
        index = cleaned.lower().find(query.lower())
        if index >= 0:
            start = max(0, index - size // 3)
            return cleaned[start:start + size]
    return cleaned[:size]


ASCII_STOP_TERMS = {
    "and",
    "the",
    "for",
    "with",
    "video",
    "videos",
    "course",
    "courses",
    "tutorial",
    "tutorials",
}
CJK_STOP_TERMS = {
    "一个",
    "一些",
    "一下",
    "这个",
    "那个",
    "这些",
    "那些",
    "现在",
    "需要",
    "可以",
    "怎么",
    "什么",
    "为什么",
    "学习",
    "课程",
    "视频",
    "推荐",
    "资料",
    "基础",
    "简单",
    "讲解",
    "入门",
    "教程",
    "看看",
    "找到",
    "找找",
    "帮我",
    "请你",
    "给我",
    "方面",
    "语言",
    "的",
}

VIDEO_QUERY_STOP_PHRASES = {
    "帮我",
    "请你",
    "请",
    "给我",
    "找一下",
    "找一找",
    "找",
    "搜索",
    "推荐",
    "查一下",
    "查",
    "有没有",
    "一些",
    "几个",
    "几门",
    "课程",
    "视频库",
    "哔哩哔哩",
    "哔哩",
    "bilibili",
    "b站",
    "B站",
    "上面",
    "里面",
    "相关",
    "优质",
    "高质量",
    "视频",
    "教程",
}
VIDEO_GENERIC_TERMS = {
    "视频课",
    "视频课程",
    "频课",
    "频课程",
    "的视频",
    "的视频课",
    "的视频课程",
    "的视",
    "的视",
    "言的",
    "言的视",
    "言的视频",
    "语言的",
    "语言的视",
    "语言的视频课程",
    "语言教程",
    "言教",
    "言教程",
}

VIDEO_COURSE_MARKERS = {
    "课程",
    "教程",
    "入门",
    "零基础",
    "基础",
    "程序设计",
    "全套",
    "完整版",
    "从入门",
    "速通",
    "期末",
}

VIDEO_SETUP_MARKERS = {
    "下载安装",
    "安装",
    "配置",
    "环境搭建",
    "开发环境",
    "怎么改成中文",
    "vscode",
    "dev c++",
    "vc++6.0",
}

VIDEO_DOMAIN_MARKERS = {
    "数据结构",
    "算法",
    "操作系统",
    "计算机组成",
    "组成原理",
    "数据库",
    "软考",
    "教资",
    "项目",
    "自制",
}

VIDEO_TOPIC_ENTITY_PATTERNS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "rubik_cube": (
        (
            r"魔方|三阶魔方|鲁比克|rubik(?:'s)?|rubiks",
        ),
        (
            r"魔方|三阶魔方|鲁比克|rubik(?:'s)?|rubiks",
        ),
    ),
}

VIDEO_NEGATIVE_LEARNING_TERMS = {
    "搞笑",
    "美女",
    "成人",
    "擦边",
    "福利视频",
    "资源网站",
    "不笑算我输",
    "极限过审",
    "午夜福利",
}

LANGUAGE_ENTITY_PATTERNS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "c_language": (
        (
            r"(?<![a-z0-9+#])c\s*(?:语言|程序设计|编程)(?!\s*(?:\+\+|#))",
            r"\bc\s+language\b",
        ),
        (
            r"(?<![a-z0-9+#])c\s*(?:语言|程序设计|编程)(?!\s*(?:\+\+|#))",
            r"\bc\s+language\b",
        ),
    ),
    "cpp": (
        (r"(?<![a-z0-9])(?:c\+\+|cpp|c plus plus)(?![a-z0-9])",),
        (r"(?<![a-z0-9])(?:c\+\+|cpp|c plus plus)(?![a-z0-9])",),
    ),
    "python": (
        (r"(?<![a-z0-9])python(?![a-z0-9])",),
        (r"(?<![a-z0-9])python(?![a-z0-9])",),
    ),
    "java": (
        (r"(?<![a-z0-9])java(?![a-z0-9])",),
        (r"(?<![a-z0-9])java(?![a-z0-9])",),
    ),
    "go": (
        (r"(?<![a-z0-9])(?:go\s*语言|golang)(?![a-z0-9])",),
        (r"(?<![a-z0-9])(?:go\s*语言|golang)(?![a-z0-9])",),
    ),
    "javascript": (
        (r"(?<![a-z0-9])(?:javascript|js)(?![a-z0-9])",),
        (r"(?<![a-z0-9])(?:javascript|js)(?![a-z0-9])",),
    ),
}

LANGUAGE_ENTITY_TERMS = {
    "c语言",
    "c程序设计",
    "c编程",
    "c++",
    "cpp",
    "python",
    "java",
    "go语言",
    "golang",
    "javascript",
    "js",
}


def compact_ascii_cjk_phrases(value: str) -> set[str]:
    phrases: set[str] = set()
    for match in re.finditer(r"(?<![a-z0-9+#.])([a-z][a-z0-9+#.]*)\s*([\u4e00-\u9fff]{1,8})", value.casefold()):
        ascii_part, cjk_part = match.groups()
        if cjk_part.startswith("语言"):
            phrases.add(f"{ascii_part}语言")
        if cjk_part.startswith("程序设计"):
            phrases.add(f"{ascii_part}程序设计")
        if cjk_part.startswith("编程"):
            phrases.add(f"{ascii_part}编程")
    return phrases


def normalize_video_search_query(value: str) -> str:
    candidate = value or ""
    for phrase in sorted(VIDEO_QUERY_STOP_PHRASES, key=len, reverse=True):
        candidate = re.sub(re.escape(phrase), " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s*的\s*", " ", candidate)
    candidate = re.sub(r"(?<![a-z0-9+#])([a-z])\s+语言", r"\1语言", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ：:，。！？、\n\t\"'《》“”")
    return candidate


def required_video_language_signals(value: str) -> set[str]:
    lowered = value.casefold()
    return {
        name
        for name, (query_patterns, _text_patterns) in LANGUAGE_ENTITY_PATTERNS.items()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in query_patterns)
    }


def required_video_topic_signals(value: str) -> set[str]:
    lowered = value.casefold()
    return {
        name
        for name, (query_patterns, _text_patterns) in VIDEO_TOPIC_ENTITY_PATTERNS.items()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in query_patterns)
    }


def text_matches_language_signal(value: str, signal: str) -> bool:
    patterns = LANGUAGE_ENTITY_PATTERNS.get(signal, ((), ()))[1]
    lowered = value.casefold()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns)


def text_matches_topic_signal(value: str, signal: str) -> bool:
    patterns = VIDEO_TOPIC_ENTITY_PATTERNS.get(signal, ((), ()))[1]
    lowered = value.casefold()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns)


def text_has_negative_video_signal(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in VIDEO_NEGATIVE_LEARNING_TERMS)


def video_search_terms_for(value: str) -> set[str]:
    return (search_terms_for(value) | compact_ascii_cjk_phrases(value)) - VIDEO_GENERIC_TERMS


def video_query_wants_course(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in ("课程", "教程", "入门", "基础", "零基础", "学习", "系统课", "全套"))


def is_primary_c_language_course_title(value: str) -> bool:
    title = value.casefold()
    return bool(re.search(r"c语言\s*(?:程序设计|基础|零基础|入门|速通|全套)", title, flags=re.IGNORECASE)) or any(
        marker in title
        for marker in (
            "c语言程序设计",
            "c语言基础",
            "c语言零基础",
            "c语言入门",
            "c语言全套",
            "尚硅谷c语言",
            "翁恺教你c语言",
        )
    )


def search_terms_for(value: str) -> set[str]:
    lowered = value.lower()
    terms = set(re.findall(r"[a-z0-9_+#.]+", lowered)) | compact_ascii_cjk_phrases(value)
    for cjk_run in re.findall(r"[\u4e00-\u9fff]+", value):
        if len(cjk_run) <= 12 and cjk_run not in CJK_STOP_TERMS:
            terms.add(cjk_run)
        for size in (2, 3, 4):
            terms.update(cjk_run[index:index + size] for index in range(0, max(0, len(cjk_run) - size + 1)))
    return {
        term
        for term in terms
        if (len(term) >= 2 or term in {"ai", "os", "go", "c++", "c#", "js"})
        and term not in ASCII_STOP_TERMS
        and term not in CJK_STOP_TERMS
    }


DEFAULT_APP_ACTIONS: dict[str, list[dict[str, str]]] = {
    "custom.html": [{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "mindmap.concept": [{"label": "展开节点", "action": "mindmap.expand"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "knowledge.graph": [{"label": "查看先修", "action": "knowledge.prerequisites"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "quiz.practice": [{"label": "提交答案", "action": "quiz.submit"}, {"label": "让导师讲题", "action": "tutor.explain"}],
    "code.lab": [{"label": "解释代码", "action": "tutor.explain"}],
    "ppt.preview": [{"label": "预览 PPT", "action": "ppt.preview"}, {"label": "让导师串讲", "action": "tutor.explain"}],
    "video.script": [{"label": "查看分镜", "action": "video_script.view"}, {"label": "让导师解说", "action": "tutor.explain"}],
    "image.explanation": [{"label": "生成图解", "action": "image.generate"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "notes.session": [{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
    "resource.center": [{"label": "筛选资源", "action": "resource.filter"}, {"label": "让导师推荐", "action": "tutor.explain"}],
    "profile.dashboard": [{"label": "更新画像", "action": "profile.refresh"}],
    "learning.path": [{"label": "聚焦当前阶段", "action": "path.focus_current"}],
    "dashboard.learning": [{"label": "刷新证据链", "action": "dashboard.refresh"}],
    "math.gradient_descent_demo": [{"label": "解释学习率", "action": "tutor.explain"}],
    "physics.work_energy_demo": [{"label": "让导师解释", "action": "tutor.explain"}],
    "video.player": [{"label": "切换视频", "action": "video.select"}, {"label": "让导师总结视频", "action": "tutor.explain"}],
}

FOUNDATION_APP_TYPES = {"profile.dashboard", "dashboard.learning", "resource.center"}


class LearningStore:
    decay = DecayPolicy()
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_settings().sqlite_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.create_schema()
        self.seed()

    def create_schema(self) -> None:
        for statement in SQLITE_SCHEMA:
            self.conn.execute(statement)
        self._ensure_course_document_metadata_columns()
        self.conn.commit()

    def _ensure_course_document_metadata_columns(self) -> None:
        existing = {str(row["name"]) for row in self.conn.execute("PRAGMA table_info(course_documents)").fetchall()}
        columns = {
            "ingest_type": "TEXT NOT NULL DEFAULT 'course_seed'",
            "owner_scope": "TEXT NOT NULL DEFAULT 'course'",
            "owner_id": "TEXT",
            "source_scope": "TEXT NOT NULL DEFAULT 'course_official'",
            "original_url": "TEXT",
            "mime_type": "TEXT",
            "upload_status": "TEXT NOT NULL DEFAULT 'ready'",
            "metadata": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, definition in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE course_documents ADD COLUMN {name} {definition}")

    def table_names(self) -> list[str]:
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(row["name"] for row in rows)

    def schema_ready(self) -> bool:
        tables = set(self.table_names())
        return all(table in tables for table in REQUIRED_TABLES)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM users WHERE lower(email)=lower(?)", (email.strip(),))
        return dict(row) if row else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
        return dict(row) if row else None

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
            "INSERT INTO users(id, email, password_hash, display_name, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (user_id, cleaned_email, password_hash, display_name or cleaned_email.split("@")[0], now, now),
        )
        self.execute(
            "INSERT OR IGNORE INTO students(id, display_name, created_at, updated_at) VALUES(?,?,?,?)",
            (target_student, display_name or cleaned_email.split("@")[0], now, now),
        )
        self.execute(
            "INSERT OR IGNORE INTO courses(id, title, description, created_at) VALUES(?,?,?,?)",
            (course_id, "默认学习空间", "新用户画像构建与个性化学习空间。", now),
        )
        self.execute(
            "INSERT OR REPLACE INTO student_accounts(id, user_id, student_id, role, created_at) VALUES(?,?,?,?,?)",
            (stable_id("acct", f"{user_id}:{target_student}"), user_id, target_student, "owner", now),
        )
        self.start_onboarding(target_student, course_id)
        self.ensure_default_apps(target_student, course_id, full=True)
        return {
            "id": user_id,
            "email": cleaned_email,
            "display_name": display_name or cleaned_email.split("@")[0],
            "student_id": target_student,
            "course_id": course_id,
        }

    def create_auth_session(self, *, token: str, user_id: str, student_id: str, course_id: str) -> dict[str, Any]:
        now = utc_now()
        self.execute(
            """
            INSERT OR REPLACE INTO auth_sessions(token, user_id, student_id, course_id, expires_at, created_at, last_seen_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (token, user_id, student_id, course_id, None, now, now),
        )
        return {"token": token, "user_id": user_id, "student_id": student_id, "course_id": course_id}

    def get_auth_session(self, token: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM auth_sessions WHERE token=?", (token,))
        if not row:
            return None
        self.execute("UPDATE auth_sessions SET last_seen_at=? WHERE token=?", (utc_now(), token))
        return dict(row)

    def delete_auth_session(self, token: str) -> None:
        self.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
        self.conn.commit()

    def user_student_context(self, user_id: str) -> dict[str, Any] | None:
        row = self.fetchone(
            """
            SELECT u.id AS user_id, u.email, u.display_name, a.student_id, s.display_name AS student_name,
                   COALESCE(sess.course_id, 'ai-course') AS course_id
            FROM users u
            JOIN student_accounts a ON a.user_id = u.id
            JOIN students s ON s.id = a.student_id
            LEFT JOIN auth_sessions sess ON sess.user_id = u.id
            WHERE u.id=?
            ORDER BY sess.last_seen_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return dict(row) if row else None

    def save_chat_message(
        self,
        *,
        student_id: str,
        course_id: str,
        conversation_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        row_id = message_id or new_id("chatmsg")
        safe_text = strip_raw_html_report_text(text) if role == "assistant" else text
        self.conn.execute(
            """
            INSERT INTO chat_messages(id, student_id, course_id, conversation_id, role, text, metadata, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (row_id, student_id, course_id, conversation_id, role, safe_text, dumps(metadata or {}), now),
        )
        self.conn.commit()
        return {
            "id": row_id,
            "student_id": student_id,
            "course_id": course_id,
            "conversation_id": conversation_id,
            "role": role,
            "text": safe_text,
            "metadata": metadata or {},
            "created_at": now,
        }

    def list_chat_messages(
        self,
        *,
        student_id: str,
        course_id: str,
        conversation_id: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, student_id, course_id, conversation_id, role, text, metadata, created_at
            FROM chat_messages
            WHERE student_id=? AND course_id=? AND conversation_id=?
            ORDER BY datetime(created_at) DESC, rowid DESC
            LIMIT ?
            """,
            (student_id, course_id, conversation_id, limit),
        ).fetchall()
        messages = [
            {
                "id": row["id"],
                "student_id": row["student_id"],
                "course_id": row["course_id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "text": strip_raw_html_report_text(row["text"]) if row["role"] == "assistant" else row["text"],
                "metadata": loads(row["metadata"], {}),
                "created_at": row["created_at"],
                "links": [],
                "resources": [],
            }
            for row in rows
        ]
        if messages:
            message_ids = [message["id"] for message in messages]
            run_message_ids: dict[str, list[str]] = {}
            for message in messages:
                run_id = message.get("metadata", {}).get("run_id")
                if message.get("role") == "assistant" and run_id and str(run_id) not in run_message_ids:
                    run_message_ids[str(run_id)] = [message["id"]]
            conditions = [f"message_id IN ({','.join('?' for _ in message_ids)})"]
            params: list[str] = [*message_ids]
            if run_message_ids:
                conditions.append(f"source_run_id IN ({','.join('?' for _ in run_message_ids)})")
                params.extend(run_message_ids)
            link_rows = self.conn.execute(
                f"""
                SELECT id, message_id, app_id, label, action, anchor_text, source_run_id, created_at
                FROM chat_app_links
                WHERE {" OR ".join(conditions)}
                ORDER BY datetime(created_at) ASC, rowid ASC
                """,
                tuple(params),
            ).fetchall()
            links_by_message: dict[str, list[dict[str, Any]]] = {}
            for link_row in link_rows:
                direct_message_ids = [link_row["message_id"]] if link_row["message_id"] in message_ids else []
                run_message_targets = run_message_ids.get(str(link_row["source_run_id"] or ""), [])
                for target_message_id in direct_message_ids or run_message_targets:
                    link = ChatAppLink(
                        link_id=link_row["id"],
                        message_id=target_message_id,
                        app_id=link_row["app_id"],
                        label=link_row["label"],
                        action=link_row["action"],
                        anchor_text=link_row["anchor_text"],
                        source_run_id=link_row["source_run_id"],
                        created_at=link_row["created_at"],
                    ).model_dump()
                    links_by_message.setdefault(target_message_id, []).append(link)
            resource_rows = self.conn.execute(
                f"""
                SELECT
                  l.id AS link_id,
                  l.message_id AS link_message_id,
                  l.source_run_id AS link_source_run_id,
                  r.*
                FROM chat_resource_links l
                JOIN resources r ON r.id = l.resource_id
                WHERE {" OR ".join(conditions)}
                ORDER BY datetime(l.created_at) ASC, l.rowid ASC
                """,
                tuple(params),
            ).fetchall()
            resources_by_message: dict[str, list[dict[str, Any]]] = {}
            seen_resources: set[tuple[str, str]] = set()
            for resource_row in resource_rows:
                direct_message_ids = [resource_row["link_message_id"]] if resource_row["link_message_id"] in message_ids else []
                run_message_targets = run_message_ids.get(str(resource_row["link_source_run_id"] or ""), [])
                resource = self._resource_from_row(resource_row)
                if not resource:
                    continue
                for target_message_id in direct_message_ids or run_message_targets:
                    key = (target_message_id, resource.resource_id)
                    if key in seen_resources:
                        continue
                    seen_resources.add(key)
                    resources_by_message.setdefault(target_message_id, []).append(resource.model_dump())
            for message in messages:
                message["links"] = links_by_message.get(message["id"], [])
                message["resources"] = resources_by_message.get(message["id"], [])
        return list(reversed(messages))

    def seed(self) -> None:
        now = utc_now()
        self.conn.execute(
            "INSERT OR IGNORE INTO students(id, display_name, created_at, updated_at) VALUES(?,?,?,?)",
            ("demo-student", "演示学习者", now, now),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO courses(id, title, description, created_at) VALUES(?,?,?,?)",
            ("ai-course", "人工智能导论", "机器学习、优化、知识表示与安全评测的入门课程。", now),
        )
        profile = {
            "major": "软件工程",
            "grade": "大一",
            "knowledge_foundation": "Python 一般，数学推导偏弱",
            "learning_goal": "掌握神经网络与可解释 AI",
            "cognitive_style": "图解 + 动手实验",
            "learning_pace": "分阶段练习",
            "weak_points": ["数学推导", "链式法则", "抽象公式"],
            "interests": ["代码实验", "动态可视化"],
            "preferred_resources": ["互动演示", "代码练习", "图解笔记"],
            "mastery_map": {"优化基础": 0.42, "动能定理": 0.55, "神经网络": 0.25},
        }
        self.conn.execute(
            """
            INSERT OR IGNORE INTO student_profiles(id, student_id, course_id, profile_json, version, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            ("profile-demo", "demo-student", "ai-course", dumps(profile), 1, now, now),
        )
        self._seed_knowledge(now)
        self._seed_resources_and_apps(now)
        self.conn.commit()

    def _seed_knowledge(self, now: str) -> None:
        doc_id = "doc-ai-intro"
        self.conn.execute(
            "INSERT OR IGNORE INTO course_documents(id, course_id, title, file_url, parser, created_at) VALUES(?,?,?,?,?,?)",
            (doc_id, "ai-course", "人工智能导论种子讲义", "seed://ai-intro.md", "markdown", now),
        )
        chunks = [
            ("chunk-optimization", 1, "梯度下降通过沿损失函数负梯度方向迭代更新参数，学习率过大可能导致震荡或发散。", "优化基础", 0.96),
            ("chunk-energy", 2, "动能定理说明合外力做功等于物体动能变化，可写作 W = ΔK = 1/2mv2^2 - 1/2mv1^2。", "物理类比", 0.94),
            ("chunk-nn", 3, "神经网络训练依赖前向传播、损失函数、反向传播和优化器，概念之间存在先修关系。", "神经网络", 0.93),
            ("chunk-safety", 4, "学习资源生成必须保留来源引用，经过一致性、安全性和个性化适配检查后才能推送。", "安全验证", 0.91),
        ]
        for chunk_id, index, content, section, confidence in chunks:
            source_ref = {
                "document_id": doc_id,
                "chunk_id": chunk_id,
                "course_id": "ai-course",
                "chapter": "人工智能导论",
                "section": section,
                "quote_span": [0, min(20, len(content))],
                "confidence": confidence,
            }
            self.conn.execute(
                """
                INSERT OR IGNORE INTO document_chunks(id, document_id, course_id, chunk_index, content, source_ref, embedding, created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (chunk_id, doc_id, "ai-course", index, content, dumps(source_ref), dumps([confidence, index / 10]), now),
            )
        points = [
            ("kp-math", "数学推导基础", "链式法则、函数图像与符号推理。"),
            ("kp-optimization", "梯度下降", "学习率、迭代轨迹、损失曲线。"),
            ("kp-nn", "神经网络训练", "前向传播、损失函数、反向传播。"),
            ("kp-safety", "资源安全验证", "引用覆盖、答案一致性、代码与提示安全。"),
            ("kp-energy", "动能定理类比", "用能量变化理解优化步长。"),
        ]
        for kp_id, title, description in points:
            self.conn.execute(
                "INSERT OR IGNORE INTO knowledge_points(id, course_id, title, description, metadata) VALUES(?,?,?,?,?)",
                (kp_id, "ai-course", title, description, dumps({"seed": True})),
            )
        edges = [
            ("edge-math-opt", "kp-math", "kp-optimization", "prerequisite"),
            ("edge-opt-nn", "kp-optimization", "kp-nn", "prerequisite"),
            ("edge-safety-resource", "kp-safety", "kp-nn", "supports"),
            ("edge-energy-opt", "kp-energy", "kp-optimization", "analogy"),
        ]
        for edge_id, source_id, target_id, relation in edges:
            self.conn.execute(
                "INSERT OR IGNORE INTO knowledge_edges(id, course_id, source_id, target_id, relation, confidence) VALUES(?,?,?,?,?,?)",
                (edge_id, "ai-course", source_id, target_id, relation, 0.88),
            )

    def _source_refs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT source_ref FROM document_chunks ORDER BY chunk_index LIMIT 3").fetchall()
        return [loads(row["source_ref"], {}) for row in rows]

    def _seed_resources_and_apps(self, now: str) -> None:
        refs = self._source_refs()
        verifier = VerifierResult(passed=True, score=0.92, source_coverage=0.95, profile_fit=0.9, safety="pass")
        resources = [
            LearningResource(
                resource_id="res-doc-gradient",
                type="document",
                title="梯度下降图解讲义",
                target_topic="梯度下降",
                content={"objectives": ["理解负梯度方向", "观察学习率影响"], "summary": "从地形图理解损失下降。"},
                source_refs=refs,
                personalized_reason="用图解降低公式负担。",
                tags=["图解", "优化"],
                quality_check=verifier,
            ),
            LearningResource(
                resource_id="res-quiz-gradient",
                type="quiz",
                title="梯度下降诊断练习",
                target_topic="梯度下降",
                content={"question_count": 3},
                source_refs=refs,
                personalized_reason="用短题快速暴露学习率误区。",
                tags=["练习", "诊断"],
                quality_check=verifier,
            ),
            LearningResource(
                resource_id="res-code-lab",
                type="code_practice",
                title="NumPy 梯度下降实验",
                target_topic="梯度下降",
                content={"starter_code": "x = 4.0\nfor step in range(8):\n    x = x - lr * 2 * x", "expected_output": "x 逐步靠近 0"},
                source_refs=refs,
                personalized_reason="把公式转成 Python 循环。",
                tags=["代码", "实验"],
                quality_check=verifier,
            ),
            LearningResource(
                resource_id="res-mindmap",
                type="mindmap",
                title="神经网络学习地图",
                target_topic="神经网络",
                content={"nodes": ["数学推导基础", "梯度下降", "神经网络训练", "验证与安全"]},
                source_refs=refs,
                personalized_reason="先看到全局结构，再进入局部练习。",
                tags=["思维导图"],
                quality_check=verifier,
            ),
            LearningResource(
                resource_id="res-reading",
                type="reading",
                title="优化器延伸阅读卡",
                target_topic="优化器",
                content={"guide": "先读学习率，再比较动量与自适应方法。"},
                source_refs=refs,
                personalized_reason="提供课后扩展但保留先修提醒。",
                tags=["阅读"],
                quality_check=verifier,
            ),
        ]
        for resource in resources:
            if not self.get_resource(resource.resource_id):
                self.save_resource(resource, created_by_skill=f"{resource.type}_skill")
        apps = self.default_apps(refs)
        for app in apps:
            if not self.get_app(app.app_id):
                self.save_app(app, agent="app_canvas_agent", skill="app_generation_skill")
        path = LearningPath(
            path_id="path-neural-network",
            title="神经网络入门路径",
            current_stage_id="stage-math",
            overall_progress=0.28,
            stages=[
                LearningPathStage(
                    stage_id="stage-math",
                    title="补齐数学推导基础",
                    status="in_progress",
                    mastery_required=0.55,
                    current_mastery=0.38,
                    recommended_resource_ids=["res-doc-gradient"],
                    app_ids=["app-gradient"],
                    reason="你的资料显示数学推导偏弱，先用图解和实验降低抽象度。",
                ),
                LearningPathStage(
                    stage_id="stage-opt",
                    title="掌握梯度下降",
                    status="recommended",
                    mastery_required=0.65,
                    current_mastery=0.42,
                    recommended_resource_ids=["res-quiz-gradient", "res-code-lab"],
                    app_ids=["app-path", "app-quiz"],
                    reason="通过学习率实验和诊断题建立稳定直觉。",
                ),
                LearningPathStage(
                    stage_id="stage-nn",
                    title="进入神经网络训练",
                    status="locked",
                    mastery_required=0.75,
                    current_mastery=0.25,
                    recommended_resource_ids=["res-mindmap", "res-reading"],
                    app_ids=["app-knowledge"],
                    reason="等优化基础达到阈值后解锁。",
                ),
            ],
            next_actions=["完成梯度下降诊断题", "调节学习率观察发散", "把结论总结到笔记 App"],
        )
        self.save_path("demo-student", "ai-course", path)
        question = QuizQuestion(
            question_id="quiz-q-gradient-lr",
            prompt="当梯度下降的学习率过大时，最可能出现什么现象？",
            options=["更快稳定收敛", "震荡或发散", "损失函数自动变平", "模型不再需要数据"],
            answer="震荡或发散",
            explanation="学习率过大时，更新步子越过低谷，损失会来回震荡甚至增大。",
            knowledge_point_id="kp-optimization",
            misconception_tags=["learning_rate_too_large", "optimization_stability"],
            source_refs=refs,
        )
        self.save_quiz_question(question, "res-quiz-gradient")
        self.create_memory(
            EduMemoryItem(
                id="mem-profile-demo",
                student_id="demo-student",
                course_id="ai-course",
                memory_type="profile",
                content="学习者是软件工程大一，Python 一般，数学推导弱，偏好图解和代码。",
                structured_payload={"dimensions": self.get_profile("demo-student")},
                confidence=0.76,
                importance=0.86,
                decay_rate=0.02,
                evidence_type="chat",
                source_agent="profile_agent",
                tags=["profile", "preference"],
            )
        )

    def default_apps(self, refs: list[dict[str, Any]]) -> list[CanvasApp]:
        custom_html_seed = """
<section class="lfx-lab" data-learnforge-widget="seed-lab-demo">
  <div class="lfx-hero">
    <div>
      <div class="lfx-kicker">LearnForge Lab Runtime</div>
      <h2 class="lfx-title">互动信息图实验台</h2>
      <p class="lfx-sub">这个沙箱支持 HTML、SVG、Canvas、滑块、标签页、自测和数据图表。后续由 Gemini/Hermes 生成的 custom.html 会走同一套高保真运行时。</p>
    </div>
    <div class="lfx-card">
      <strong>运行能力</strong>
      <div class="lfx-bar-stage" data-lf-bars='[{"label":"状态","value":88},{"label":"图表","value":82},{"label":"交互","value":76},{"label":"自测","value":69}]'></div>
    </div>
  </div>
  <div class="lfx-grid">
    <div class="lfx-stage lfx-span-7">
      <svg viewBox="0 0 760 320" role="img" aria-label="学习组件生成流程">
        <defs>
          <linearGradient id="seed-flow" x1="0" x2="1">
            <stop stop-color="#64d8ff"/>
            <stop offset="1" stop-color="#7ef0b2"/>
          </linearGradient>
        </defs>
        <path d="M80 170 C210 40 330 280 460 150 S640 90 700 190" fill="none" stroke="url(#seed-flow)" stroke-width="12" stroke-linecap="round"/>
        <circle cx="80" cy="170" r="34" fill="#64d8ff"/><text x="80" y="176" text-anchor="middle" fill="#06111c" font-weight="900">输入</text>
        <circle cx="300" cy="205" r="42" fill="#ffd166"/><text x="300" y="211" text-anchor="middle" fill="#06111c" font-weight="900">推理</text>
        <circle cx="520" cy="124" r="42" fill="#9b8cff"/><text x="520" y="130" text-anchor="middle" fill="#06111c" font-weight="900">组件</text>
        <circle cx="700" cy="190" r="34" fill="#7ef0b2"/><text x="700" y="196" text-anchor="middle" fill="#06111c" font-weight="900">验证</text>
      </svg>
    </div>
    <article class="lfx-card lfx-span-5" data-lf-quiz>
      <strong>自测</strong>
      <p>一个高质量 custom.html demo 至少应该包含什么？</p>
      <div class="lfx-toolbar">
        <button type="button" data-lf-answer="false">只有标题和段落</button>
        <button type="button" data-lf-answer="true">可视化主体与真实交互</button>
      </div>
      <p data-lf-feedback>选择一个答案。</p>
    </article>
  </div>
</section>
""".strip()
        return [
            CanvasApp(
                app_id="app-profile",
                app_type="profile.dashboard",
                title="学习画像",
                icon="UserRound",
                position=CanvasPosition(x=40, y=40),
                size=CanvasSize(width=330, height=250),
                z_index=2,
                payload={"summary": "软件工程大一，偏好图解和代码。"},
                source_refs=refs[:1],
                actions=[{"label": "更新画像", "action": "profile.refresh"}],
            ),
            CanvasApp(
                app_id="app-path",
                app_type="learning.path",
                title="神经网络学习路径",
                icon="Route",
                position=CanvasPosition(x=420, y=40),
                size=CanvasSize(width=430, height=300),
                z_index=3,
                payload={"path_id": "path-neural-network"},
                source_refs=refs,
                actions=[{"label": "聚焦当前阶段", "action": "path.focus_current"}],
            ),
            CanvasApp(
                app_id="app-energy",
                app_type="physics.work_energy_demo",
                title="动能定理互动演示",
                icon="Activity",
                position=CanvasPosition(x=60, y=360),
                size=CanvasSize(width=430, height=320),
                z_index=4,
                payload={"mass": 2, "initialVelocity": 3, "finalVelocity": 7, "force": 8, "displacement": 5},
                source_refs=refs[1:2],
                actions=[{"label": "让导师解释", "action": "tutor.explain"}],
            ),
            CanvasApp(
                app_id="app-gradient",
                app_type="math.gradient_descent_demo",
                title="梯度下降实验台",
                icon="LineChart",
                position=CanvasPosition(x=540, y=390),
                size=CanvasSize(width=470, height=340),
                z_index=5,
                payload={"learningRate": 0.18, "initialPoint": 4, "iterations": 12},
                source_refs=refs[:1],
                actions=[{"label": "解释学习率", "action": "tutor.explain"}],
            ),
            CanvasApp(
                app_id="app-quiz",
                app_type="quiz.practice",
                title="梯度下降诊断题",
                icon="CircleHelp",
                position=CanvasPosition(x=1040, y=70),
                size=CanvasSize(width=360, height=300),
                z_index=6,
                payload={"question_id": "quiz-q-gradient-lr"},
                source_refs=refs,
                actions=[{"label": "提交答案", "action": "quiz.submit"}],
            ),
            CanvasApp(
                app_id="app-notes",
                app_type="notes.session",
                title="学习笔记模板",
                icon="NotebookPen",
                position=CanvasPosition(x=1040, y=420),
                size=CanvasSize(width=360, height=290),
                z_index=7,
                payload={"topic": "等待当前会话", "key_conclusions": ["还没有保存当前会话的学习笔记。", "当你点击“总结到笔记 App”后，这里会生成本轮主题的笔记。"]},
                source_refs=refs,
                actions=[{"label": "保存笔记", "action": "notes.save"}],
            ),
            CanvasApp(
                app_id="app-dashboard",
                app_type="dashboard.learning",
                title="学习仪表盘",
                icon="Gauge",
                position=CanvasPosition(x=1450, y=60),
                size=CanvasSize(width=410, height=360),
                z_index=8,
                payload={"student_id": "demo-student"},
                source_refs=refs,
                actions=[{"label": "刷新证据链", "action": "dashboard.refresh"}],
            ),
            CanvasApp(
                app_id="app-knowledge",
                app_type="knowledge.graph",
                title="知识关系图",
                icon="Network",
                position=CanvasPosition(x=1460, y=480),
                size=CanvasSize(width=390, height=290),
                z_index=9,
                payload={"course_id": "ai-course"},
                source_refs=refs,
                actions=[{"label": "查看先修", "action": "knowledge.prerequisites"}],
            ),
            CanvasApp(
                app_id="app-mindmap",
                app_type="mindmap.concept",
                title="概念思维导图",
                icon="Brain",
                position=CanvasPosition(x=60, y=760),
                size=CanvasSize(width=380, height=280),
                z_index=10,
                payload={"topic": "神经网络训练"},
                source_refs=refs,
                actions=[{"label": "展开节点", "action": "mindmap.expand"}],
            ),
            CanvasApp(
                app_id="app-code",
                app_type="code.lab",
                title="Python 代码实验",
                icon="Code2",
                position=CanvasPosition(x=470, y=780),
                size=CanvasSize(width=410, height=300),
                z_index=11,
                payload={"resource_id": "res-code-lab"},
                source_refs=refs,
                actions=[{"label": "解释代码", "action": "tutor.explain"}],
            ),
            CanvasApp(
                app_id="app-ppt",
                app_type="ppt.preview",
                title="微课 PPT 预览",
                icon="Presentation",
                position=CanvasPosition(x=910, y=790),
                size=CanvasSize(width=360, height=280),
                z_index=12,
                payload={"slide_count": 3},
                source_refs=refs,
                actions=[{"label": "预览", "action": "ppt.preview"}],
            ),
            CanvasApp(
                app_id="app-image",
                app_type="image.explanation",
                title="教学图解资产",
                icon="FileImage",
                position=CanvasPosition(x=1300, y=830),
                size=CanvasSize(width=370, height=285),
                z_index=13,
                payload={"topic": "学习率"},
                source_refs=refs,
                actions=[{"label": "生成图解", "action": "image.generate"}],
            ),
            CanvasApp(
                app_id="app-video",
                app_type="video.script",
                title="60 秒动画脚本",
                icon="Film",
                position=CanvasPosition(x=1710, y=820),
                size=CanvasSize(width=360, height=280),
                z_index=14,
                payload={"topic": "梯度下降"},
                source_refs=refs,
                actions=[{"label": "查看分镜", "action": "video_script.view"}],
            ),
            CanvasApp(
                app_id="app-resource",
                app_type="resource.center",
                title="资源中心",
                icon="BookOpen",
                position=CanvasPosition(x=1860, y=60),
                size=CanvasSize(width=380, height=320),
                z_index=15,
                payload={"filters": ["document", "quiz", "code"]},
                source_refs=refs,
                actions=[{"label": "筛选资源", "action": "resource.filter"}],
            ),
            CanvasApp(
                app_id="app-custom-html",
                app_type="custom.html",
                title="互动信息图实验台",
                icon="Image",
                position=CanvasPosition(x=1900, y=430),
                size=CanvasSize(width=1060, height=820),
                z_index=16,
                render_mode="sandbox_iframe",
                payload={"html": custom_html_seed},
                source_refs=refs,
                actions=[{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
            ),
        ]

    def default_apps_for_student(self, refs: list[dict[str, Any]], student_id: str, course_id: str) -> list[CanvasApp]:
        apps: list[CanvasApp] = []
        for app in self.default_apps(refs):
            cloned = app.model_copy(deep=True)
            if not (student_id == "demo-student" and course_id == "ai-course"):
                cloned.app_id = stable_id(app.app_id, f"{student_id}:{course_id}:{app.app_id}")
            cloned.source["student_id"] = student_id
            cloned.source["course_id"] = course_id
            if cloned.app_type == "dashboard.learning":
                cloned.payload["student_id"] = student_id
            elif cloned.app_type == "knowledge.graph":
                cloned.payload["course_id"] = course_id
            apps.append(cloned)
        return apps

    def ensure_default_apps(self, student_id: str, course_id: str = "ai-course", *, full: bool = False) -> list[CanvasApp]:
        existing = self.list_apps(student_id, course_id=course_id)
        refs = self._source_refs()
        candidates = self.default_apps_for_student(refs, student_id, course_id)
        if existing and not full:
            candidates = [app for app in candidates if app.app_type in FOUNDATION_APP_TYPES]
        for app in candidates:
            if not self.get_app(app.app_id, student_id=student_id, course_id=course_id):
                self.save_app(app, student_id=student_id, course_id=course_id, agent="system_seed", skill="default_canvas")
        return self.list_apps(student_id, course_id=course_id)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def save_resource(
        self,
        resource: LearningResource,
        *,
        student_id: str = "demo-student",
        course_id: str = "ai-course",
        knowledge_point_id: str | None = None,
        created_by_skill: str = "seed",
    ) -> LearningResource:
        now = utc_now()
        quality = resource.quality_check.model_dump() if resource.quality_check else {}
        target_student = student_id or "demo-student"
        target_course = course_id or "ai-course"
        target_kp = knowledge_point_id
        content = dict(resource.content)
        content.setdefault("target_topic", resource.target_topic)
        if resource.tags:
            content.setdefault("tags", resource.tags)
        if resource.estimated_minutes is not None:
            content.setdefault("estimated_minutes", resource.estimated_minutes)
        self.execute(
            """
            INSERT OR REPLACE INTO resources(
              id, student_id, course_id, knowledge_point_id, type, title, difficulty, content_json, file_url,
              source_refs, personalized_reason, quality_score, verifier_result, created_by_skill, status, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                resource.resource_id,
                target_student,
                target_course,
                target_kp,
                resource.type,
                resource.title,
                resource.difficulty,
                dumps(content),
                None,
                dumps(resource.source_refs),
                resource.personalized_reason,
                quality.get("score"),
                dumps(quality),
                created_by_skill,
                "published" if quality.get("passed", True) else "review",
                now,
                now,
            ),
        )
        return resource

    def get_resource(self, resource_id: str) -> LearningResource | None:
        row = self.fetchone("SELECT * FROM resources WHERE id=?", (resource_id,))
        return self._resource_from_row(row)

    def list_resources(
        self,
        student_id: str = "demo-student",
        course_id: str | None = None,
        *,
        query: str | None = None,
        tag: str | None = None,
        resource_type: str | None = None,
        limit: int | None = None,
    ) -> list[LearningResource]:
        # Fetch full rows in ONE query (avoids the previous per-row get_resource() N+1).
        # type filtering is pushed into SQL; tag/query stay in Python because they
        # operate on content_json (a JSON blob).
        sql = "SELECT * FROM resources WHERE student_id=?"
        params: list[Any] = [student_id]
        if course_id:
            sql += " AND (course_id = ? OR course_id IS NULL)"
            params.append(course_id)
        if resource_type:
            sql += " AND type = ?"
            params.append(resource_type)
        sql += " ORDER BY created_at"
        rows = self.fetchall(sql, tuple(params))
        resources = [res for row in rows if (res := self._resource_from_row(row))]
        if tag:
            normalized_tag = tag.casefold()
            resources = [
                resource
                for resource in resources
                if normalized_tag in {item.casefold() for item in resource.tags}
                or normalized_tag in str(resource.content.get("module_name", "")).casefold()
            ]
        if query:
            normalized_query = query.casefold().strip()
            resources = [
                resource
                for resource in resources
                if normalized_query
                and normalized_query
                in " ".join(
                    [
                        resource.title,
                        resource.type,
                        resource.target_topic,
                        resource.personalized_reason,
                        " ".join(resource.tags),
                        str(resource.content.get("module_name", "")),
                        str(resource.content.get("summary", "")),
                    ]
                ).casefold()
            ]
        return resources[-limit:] if limit and limit > 0 else resources

    def _resource_from_row(self, row: Any) -> LearningResource | None:
        """Materialize a LearningResource directly from a resources-table row.

        Shared by get_resource() and list_resources() so neither needs a separate lookup
        when the full row is already available.
        """
        if not row:
            return None
        content = loads(row["content_json"], {})
        quality = loads(row["verifier_result"], {})
        tags = content.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        estimated_minutes = content.get("estimated_minutes")
        if not isinstance(estimated_minutes, int):
            estimated_minutes = None
        return LearningResource(
            resource_id=row["id"],
            type=row["type"],
            title=row["title"],
            target_topic=content.get("target_topic") or content.get("module_name") or row["title"],
            difficulty=row["difficulty"] or "adaptive",
            content=content,
            source_refs=loads(row["source_refs"], []),
            personalized_reason=row["personalized_reason"] or "",
            estimated_minutes=estimated_minutes,
            tags=[str(tag) for tag in tags if tag],
            quality_check=VerifierResult(**quality) if quality else None,
        )

    def search_video_resources(self, query: str, limit: int = 6) -> list[LearningResource]:
        cleaned_query = (query or "").strip()
        normalized_query = normalize_video_search_query(cleaned_query) or cleaned_query
        query_terms = video_search_terms_for(normalized_query)
        significant_query_terms = {term for term in query_terms if term not in LANGUAGE_ENTITY_TERMS}
        required_language_signals = required_video_language_signals(cleaned_query) | required_video_language_signals(normalized_query)
        required_topic_signals = required_video_topic_signals(cleaned_query) | required_video_topic_signals(normalized_query)
        wants_course = video_query_wants_course(cleaned_query)
        rows = self.fetchall(
            """
            SELECT id, title, content_json, source_refs, personalized_reason, created_at, updated_at
            FROM resources
            WHERE type='video'
            ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC
            """
        )

        def row_score(row: sqlite3.Row) -> float:
            content = loads(row["content_json"], {})
            source_refs = loads(row["source_refs"], [])
            haystack = " ".join(
                [
                    row["title"] or "",
                    row["personalized_reason"] or "",
                    dumps(content),
                    dumps(source_refs),
                ]
            ).casefold()
            title = str(row["title"] or "").casefold()
            topic = str(content.get("target_topic") or content.get("module_name") or "").casefold()
            focused_haystack = " ".join(
                [
                    row["title"] or "",
                    str(content.get("target_topic") or ""),
                    str(content.get("module_name") or ""),
                    str(content.get("author") or ""),
                    " ".join(str(tag) for tag in content.get("tags", []) if isinstance(tag, str)),
                ]
            ).casefold()
            score = 0.0
            if text_has_negative_video_signal(focused_haystack):
                return 0.0

            if required_language_signals:
                language_score = 0.0
                for signal in required_language_signals:
                    if not text_matches_language_signal(focused_haystack, signal):
                        return 0.0
                    language_score += 30.0
                    if text_matches_language_signal(title, signal):
                        language_score += 18.0
                    else:
                        language_score += 8.0
                score += language_score
            if required_topic_signals:
                topic_score = 0.0
                for signal in required_topic_signals:
                    if not text_matches_topic_signal(focused_haystack, signal):
                        return 0.0
                    topic_score += 34.0
                    if text_matches_topic_signal(title, signal):
                        topic_score += 20.0
                    else:
                        topic_score += 8.0
                score += topic_score

            if normalized_query and normalized_query.casefold() in haystack:
                score += 24.0
            if normalized_query and normalized_query.casefold() in f"{title} {topic}":
                score += 60.0
                if not str(row["id"]).startswith("res-bili-"):
                    score += 200.0
            if significant_query_terms and not any(term.casefold() in haystack for term in significant_query_terms):
                return 0.0
            primary_c_language_course = "c_language" in required_language_signals and is_primary_c_language_course_title(title)
            if primary_c_language_course:
                score += 24.0
            if "c_language" in required_language_signals and not primary_c_language_course:
                query_has_domain = any(marker in normalized_query for marker in VIDEO_DOMAIN_MARKERS)
                if not query_has_domain and any(marker in title for marker in VIDEO_DOMAIN_MARKERS):
                    score -= 28.0
            if wants_course:
                course_text = f"{title} {focused_haystack}"
                title_course_like = any(marker in title for marker in VIDEO_COURSE_MARKERS)
                course_like = title_course_like or any(marker in course_text for marker in VIDEO_COURSE_MARKERS)
                setup_like = any(marker in course_text for marker in VIDEO_SETUP_MARKERS)
                if title_course_like:
                    score += 14.0
                elif course_like:
                    score += 7.0
                else:
                    score -= 10.0
                if setup_like and not primary_c_language_course:
                    return 0.0
            for term in query_terms:
                term_lower = term.casefold()
                if term_lower not in haystack:
                    continue
                score += 1.5 if len(term) <= 3 else 3.0
                if term_lower in title:
                    score += 5.0
                if term_lower in topic:
                    score += 3.0
                if term_lower in focused_haystack:
                    score += 1.5
            play = content.get("play")
            if isinstance(play, int | float):
                score += min(4.0, max(0.0, float(play)) / 250000.0)
            return score

        scored = sorted(
            ((row_score(row), row) for row in rows),
            key=lambda item: (item[0], item[1]["updated_at"] or item[1]["created_at"] or "", item[1]["title"]),
            reverse=True,
        )
        if query_terms:
            min_score = 12.0 if (required_language_signals or required_topic_signals) else 3.0
            selected = [row for score, row in scored if score >= min_score][:limit]
        else:
            selected = [row for _score, row in scored[:limit]]
        if not selected and normalized_query and not required_topic_signals:
            loose_terms = {term for term in search_terms_for(normalized_query) if term not in CJK_STOP_TERMS and term not in ASCII_STOP_TERMS}
            loose: list[sqlite3.Row] = []
            for row in rows:
                content = loads(row["content_json"], {})
                haystack = " ".join(
                    [
                        row["title"] or "",
                        str(content.get("target_topic") or ""),
                        str(content.get("description") or ""),
                        " ".join(str(tag) for tag in content.get("tags", []) if isinstance(tag, str)),
                    ]
                ).casefold()
                if any(term.casefold() in haystack for term in loose_terms):
                    loose.append(row)
            selected = loose[:limit]
        return [resource for row in selected if (resource := self.get_resource(row["id"]))]

    def save_course_document_from_chunks(
        self,
        *,
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
        self._ensure_course_document_metadata_columns()
        cleaned_title = (title or "未命名资料").strip() or "未命名资料"
        fingerprint = f"{course_id}\n{cleaned_title}\n" + "\n\n".join(chunks)
        doc_id = document_id or stable_id("doc-api", fingerprint)
        now = utc_now()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO course_documents(
              id, course_id, title, file_url, parser, ingest_type, owner_scope, owner_id,
              source_scope, original_url, mime_type, upload_status, metadata, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                doc_id,
                course_id,
                cleaned_title,
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
        self.conn.execute("DELETE FROM document_chunks WHERE document_id=? AND course_id=?", (doc_id, course_id))
        saved_chunks: list[dict[str, Any]] = []
        for index, chunk in enumerate([item.strip() for item in chunks if item.strip()], start=1):
            chunk_id = f"{doc_id}-chunk-{index:03d}"
            source_ref = {
                "document_id": doc_id,
                "chunk_id": chunk_id,
                "course_id": course_id,
                "title": cleaned_title,
                "section": first_heading_or_title(chunk, cleaned_title),
                "chunk_index": index,
                "quote_span": [0, min(180, len(chunk))],
                "confidence": 0.92,
                "source_type": "api_upload",
                "verified": True,
            }
            embedding = embed_text(chunk, "RETRIEVAL_DOCUMENT")
            self.conn.execute(
                """
                INSERT OR REPLACE INTO document_chunks(id, document_id, course_id, chunk_index, content, source_ref, embedding, created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (chunk_id, doc_id, course_id, index, chunk, dumps(source_ref), dumps(embedding), now),
            )
            saved_chunks.append({"chunk_id": chunk_id, "content": chunk, "source_ref": source_ref})
        self.conn.commit()
        return {
            "document_id": doc_id,
            "course_id": course_id,
            "title": cleaned_title,
            "ingest_type": ingest_type,
            "owner_scope": owner_scope,
            "owner_id": owner_id,
            "source_scope": source_scope,
            "original_url": original_url,
            "mime_type": mime_type,
            "upload_status": upload_status,
            "metadata": metadata or {},
            "chunks": saved_chunks,
            "chunk_count": len(saved_chunks),
        }

    def list_course_documents(self, course_id: str) -> list[dict[str, Any]]:
        self._ensure_course_document_metadata_columns()
        rows = self.fetchall(
            """
            SELECT d.id AS document_id, d.course_id, d.title, d.file_url, d.parser, d.created_at,
                   d.ingest_type, d.owner_scope, d.owner_id, d.source_scope, d.original_url,
                   d.mime_type, d.upload_status, d.metadata,
                   COUNT(c.id) AS chunk_count
            FROM course_documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id AND c.course_id = d.course_id
            WHERE d.course_id=?
            GROUP BY d.id, d.course_id, d.title, d.file_url, d.parser, d.created_at,
                     d.ingest_type, d.owner_scope, d.owner_id, d.source_scope, d.original_url,
                     d.mime_type, d.upload_status, d.metadata
            ORDER BY d.created_at DESC
            """,
            (course_id,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = loads(item.get("metadata"), {})
            result.append(item)
        return result

    def list_document_chunks(self, course_id: str, document_id: str) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT id AS chunk_id, document_id, course_id, chunk_index, content, source_ref, embedding, created_at
            FROM document_chunks
            WHERE course_id=? AND document_id=?
            ORDER BY chunk_index
            """,
            (course_id, document_id),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["source_ref"] = loads(item.get("source_ref"), {})
            item["embedding"] = loads(item.get("embedding"), [])
            result.append(item)
        return result

    def _ensure_notebook_schema(self) -> None:
        for statement in SQLITE_SCHEMA:
            if "notebook" in statement:
                self.conn.execute(statement)
        self.conn.commit()

    def _course_title(self, course_id: str) -> str:
        row = self.fetchone("SELECT title FROM courses WHERE id=?", (course_id,))
        return str(row["title"]) if row and row["title"] else course_id

    def _ensure_course_notebook_sources(self, *, course_id: str) -> None:
        self._ensure_notebook_schema()
        now = utc_now()
        course_notebook_id = stable_id("nblm", f"course:{course_id}:official")
        if not self.fetchone("SELECT 1 FROM notebooks WHERE id=?", (course_notebook_id,)):
            return
        for document in self.list_course_documents(course_id):
            document_id = str(document["document_id"])
            self.execute(
                """
                INSERT OR IGNORE INTO notebook_sources(id, notebook_id, source_id, source_kind, source_role, sync_status, open_notebook_source_id, synced_at, created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
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
                INSERT OR IGNORE INTO notebooks(id, owner_scope, owner_id, course_id, title, purpose, description, tags, open_notebook_id, sync_status, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
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
                INSERT OR IGNORE INTO notebook_assignments(id, notebook_id, student_id, course_id, status, rank, assigned_reason, created_at)
                VALUES(?,?,?,?,?,?,?,?)
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
        self.conn.commit()
        return self.list_notebooks(student_id=student_id, course_id=course_id)

    def list_notebooks(self, *, student_id: str, course_id: str) -> list[dict[str, Any]]:
        self._ensure_notebook_schema()
        self.ensure_default_notebooks(student_id=student_id, course_id=course_id) if not self.fetchone(
            "SELECT 1 FROM notebook_assignments WHERE student_id=? AND course_id=? LIMIT 1",
            (student_id, course_id),
        ) else self._ensure_course_notebook_sources(course_id=course_id)
        rows = self.fetchall(
            """
            SELECT n.*, a.status AS assignment_status, a.rank, a.assigned_reason,
                   COUNT(ns.source_id) AS source_count
            FROM notebook_assignments a
            JOIN notebooks n ON n.id = a.notebook_id
            LEFT JOIN notebook_sources ns ON ns.notebook_id = n.id
            WHERE a.student_id=? AND a.course_id=? AND a.status != 'archived'
            GROUP BY n.id, n.owner_scope, n.owner_id, n.course_id, n.title, n.purpose, n.description, n.tags,
                     n.open_notebook_id, n.sync_status, n.created_at, n.updated_at,
                     a.status, a.rank, a.assigned_reason
            ORDER BY a.rank ASC, n.updated_at DESC
            """,
            (student_id, course_id),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["tags"] = loads(item.get("tags"), [])
            result.append(item)
        return result

    def get_notebook(self, notebook_id: str, *, student_id: str | None = None, course_id: str | None = None) -> dict[str, Any] | None:
        self._ensure_notebook_schema()
        if student_id and course_id:
            row = self.fetchone(
                """
                SELECT n.* FROM notebooks n
                JOIN notebook_assignments a ON a.notebook_id = n.id
                WHERE n.id=? AND a.student_id=? AND a.course_id=? AND a.status != 'archived'
                """,
                (notebook_id, student_id, course_id),
            )
        else:
            row = self.fetchone("SELECT * FROM notebooks WHERE id=?", (notebook_id,))
        if not row:
            return None
        item = dict(row)
        item["tags"] = loads(item.get("tags"), [])
        return item

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
        cleaned_title = (title or "我的 Notebook").strip() or "我的 Notebook"
        notebook_id = new_id("nblm")
        self.execute(
            """
            INSERT INTO notebooks(id, owner_scope, owner_id, course_id, title, purpose, description, tags, open_notebook_id, sync_status, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
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
            INSERT OR IGNORE INTO notebook_assignments(id, notebook_id, student_id, course_id, status, rank, assigned_reason, created_at)
            VALUES(?,?,?,?,?,?,?,?)
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
        self.conn.commit()
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
        document = self.fetchone("SELECT id FROM course_documents WHERE id=? AND course_id=?", (document_id, course_id))
        if not document:
            return None
        now = utc_now()
        source_id = stable_id("nbsrc", f"{notebook_id}:{document_id}")
        self.execute(
            """
            INSERT OR IGNORE INTO notebook_sources(id, notebook_id, source_id, source_kind, source_role, sync_status, open_notebook_source_id, synced_at, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (source_id, notebook_id, document_id, source_kind, source_role, "not_synced", None, None, now),
        )
        self.execute("UPDATE notebooks SET updated_at=? WHERE id=?", (now, notebook_id))
        self.conn.commit()
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
            "UPDATE notebooks SET open_notebook_id=?, sync_status=?, updated_at=? WHERE id=?",
            (open_notebook_id, sync_status, utc_now(), notebook_id),
        )
        self.conn.commit()

    def mark_notebook_source_synced(self, notebook_id: str, source_id: str, open_notebook_source_id: str | None, sync_status: str) -> None:
        self._ensure_notebook_schema()
        self.execute(
            """
            UPDATE notebook_sources
            SET open_notebook_source_id=?, sync_status=?, synced_at=?
            WHERE notebook_id=? AND source_id=?
            """,
            (open_notebook_source_id, sync_status, utc_now(), notebook_id, source_id),
        )
        self.conn.commit()

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
            WHERE ns.notebook_id=? AND ns.source_kind='course_document'
            ORDER BY d.created_at DESC
            """,
            (notebook_id,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = loads(item.get("metadata"), {})
            chunks = self.list_document_chunks(str(item["course_id"]), str(item["source_id"]))
            refs: list[dict[str, Any]] = []
            for chunk in chunks[:12]:
                source_ref = chunk.get("source_ref") if isinstance(chunk.get("source_ref"), dict) else {}
                refs.append(
                    {
                        **source_ref,
                        "document_id": item["source_id"],
                        "chunk_id": chunk.get("chunk_id"),
                        "title": item.get("title") or item["source_id"],
                        "snippet": str(chunk.get("content") or "")[:360],
                    }
                )
            item["id"] = item["source_id"]
            item["summary"] = refs[0]["snippet"] if refs else ""
            item["chunk_count"] = len(chunks)
            item["source_refs"] = refs
            result.append(item)
        return result

    def record_notebook_memory_event(
        self,
        *,
        notebook_id: str | None,
        student_id: str,
        course_id: str | None,
        event_type: str,
        source_refs: list[dict[str, Any]] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_notebook_schema()
        event_id = new_id("nbevt")
        now = utc_now()
        self.execute(
            """
            INSERT INTO notebook_memory_events(id, notebook_id, student_id, course_id, event_type, source_refs, payload, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (event_id, notebook_id, student_id, course_id, event_type, dumps(source_refs or []), dumps(payload or {}), now),
        )
        self.conn.commit()
        return {
            "id": event_id,
            "notebook_id": notebook_id,
            "student_id": student_id,
            "course_id": course_id,
            "event_type": event_type,
            "source_refs": source_refs or [],
            "payload": payload or {},
            "created_at": now,
        }

    def save_app(
        self,
        app: CanvasApp,
        *,
        student_id: str = "demo-student",
        course_id: str = "ai-course",
        agent: str = "app_canvas_agent",
        skill: str = "app_generation_skill",
    ) -> CanvasApp:
        target_student = student_id or str(app.source.get("student_id") or "demo-student")
        target_course = course_id or str(app.source.get("course_id") or "ai-course")
        layout = {
            "position": app.position.model_dump(),
            "size": app.size.model_dump(),
            "z_index": app.z_index,
            "group_id": app.group_id,
            "course_id": target_course,
        }
        payload = dict(app.payload)
        if app.actions:
            payload["_actions"] = app.actions
        self.execute(
            """
            INSERT OR REPLACE INTO canvas_apps(
              id, student_id, conversation_id, resource_id, app_type, title, icon, status, render_mode, state,
              layout, payload, source_refs, personalized_reason, created_by_agent, created_by_skill, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                app.app_id,
                target_student,
                app.source.get("conversation_id"),
                app.source.get("resource_id"),
                app.app_type,
                app.title,
                app.icon,
                app.status,
                app.render_mode,
                app.state,
                dumps(layout),
                dumps(payload),
                dumps(app.source_refs),
                app.personalized_reason,
                agent,
                skill,
                app.created_at,
                utc_now(),
            ),
        )
        app.source["student_id"] = target_student
        app.source["course_id"] = target_course
        return app

    def _app_from_row(self, row: sqlite3.Row, *, course_id: str | None = None) -> CanvasApp:
        layout = loads(row["layout"], {})
        position = layout.get("position", {"x": 0, "y": 0})
        size = layout.get("size", {"width": 320, "height": 220})
        payload = loads(row["payload"], {})
        actions = payload.get("_actions") if isinstance(payload.get("_actions"), list) else DEFAULT_APP_ACTIONS.get(str(row["app_type"]), [])
        payload.pop("_actions", None)
        source = {
            "resource_id": row["resource_id"],
            "conversation_id": row["conversation_id"],
            "student_id": row["student_id"],
            "course_id": layout.get("course_id", course_id),
        }
        return CanvasApp(
            app_id=row["id"],
            app_type=row["app_type"],
            title=row["title"],
            icon=row["icon"],
            status=row["status"],
            render_mode=row["render_mode"],
            state=row["state"],
            position=CanvasPosition(**position),
            size=CanvasSize(**size),
            z_index=layout.get("z_index", 1),
            group_id=layout.get("group_id"),
            payload=payload,
            source=source,
            source_refs=loads(row["source_refs"], []),
            personalized_reason=row["personalized_reason"],
            actions=actions,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_apps(self, student_id: str = "demo-student", course_id: str | None = None, conversation_id: str | None = None) -> list[CanvasApp]:
        sql = "SELECT * FROM canvas_apps WHERE student_id=?"
        params: tuple[Any, ...] = (student_id,)
        if course_id:
            sql += " AND json_extract(layout, '$.course_id') = ?"
            params = (student_id, course_id)
        if conversation_id:
            sql += " AND (conversation_id IS NULL OR conversation_id = ?)"
            params = (*params, conversation_id)
        rows = self.fetchall(sql + " ORDER BY json_extract(layout, '$.z_index')", params)
        return [self._app_from_row(row, course_id=course_id) for row in rows]

    def get_app(self, app_id: str, student_id: str | None = None, course_id: str | None = None) -> CanvasApp | None:
        clauses = ["id=?"]
        params: list[Any] = [app_id]
        if student_id:
            clauses.append("student_id=?")
            params.append(student_id)
        if course_id:
            clauses.append("json_extract(layout, '$.course_id')=?")
            params.append(course_id)
        row = self.fetchone("SELECT * FROM canvas_apps WHERE " + " AND ".join(clauses), tuple(params))
        return self._app_from_row(row) if row else None

    def _artifact_from_row(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        metadata_value = row["metadata_json"] if isinstance(row, sqlite3.Row) else row.get("metadata_json")
        return {
            "artifact_id": row["id"],
            "kind": row["kind"],
            "object_key": row["object_key"],
            "content_type": row["content_type"],
            "sha256": row["sha256"],
            "size_bytes": int(row["size_bytes"] or 0),
            "title": row["title"],
            "source_run_id": row["source_run_id"],
            "student_id": row["student_id"],
            "course_id": row["course_id"],
            "conversation_id": row["conversation_id"],
            "metadata": loads(metadata_value, {}),
            "created_at": row["created_at"],
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
            INSERT OR REPLACE INTO artifacts(
              id, kind, object_key, content_type, sha256, size_bytes, title, source_run_id,
              student_id, course_id, conversation_id, metadata_json, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
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
        row = self.fetchone("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
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
        row = self.fetchone("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
        return self._artifact_from_row(row) if row else None

    def latest_artifact_for_context(
        self,
        *,
        student_id: str,
        course_id: str | None = None,
        conversation_id: str | None = None,
        kinds: list[str] | None = None,
    ) -> dict[str, Any] | None:
        clauses = ["student_id=?"]
        params: list[Any] = [student_id]
        if course_id:
            clauses.append("course_id=?")
            params.append(course_id)
        if conversation_id:
            clauses.append("conversation_id=?")
            params.append(conversation_id)
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            clauses.append(f"kind IN ({placeholders})")
            params.extend(kinds)
        row = self.fetchone(
            f"SELECT * FROM artifacts WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT 1",
            tuple(params),
        )
        return self._artifact_from_row(row) if row else None

    def update_app(
        self,
        app_id: str,
        patch: dict[str, Any],
        *,
        student_id: str | None = None,
        course_id: str | None = None,
    ) -> CanvasApp | None:
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
        if "status" in patch:
            app.status = patch["status"]
        if "position" in patch:
            app.position = CanvasPosition(**patch["position"])
        if "size" in patch:
            app.size = CanvasSize(**patch["size"])
        if "payload" in patch:
            app.payload.update(patch["payload"])
        if "actions" in patch and isinstance(patch["actions"], list):
            app.actions = patch["actions"]
        if "z_index" in patch:
            app.z_index = int(patch["z_index"])
        if "group_id" in patch:
            app.group_id = patch["group_id"]
        app.updated_at = utc_now()
        return self.save_app(
            app,
            student_id=str(app.source.get("student_id") or "demo-student"),
            course_id=str(app.source.get("course_id") or "ai-course"),
        )

    def create_chat_link(self, message_id: str, app_id: str, label: str, action: str = "focus", run_id: str | None = None) -> ChatAppLink:
        link = ChatAppLink(message_id=message_id, app_id=app_id, label=label, action=action, source_run_id=run_id, anchor_text=label)
        self.execute(
            "INSERT OR REPLACE INTO chat_app_links(id, message_id, app_id, label, action, anchor_text, source_run_id, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (link.link_id, link.message_id, link.app_id, link.label, link.action, link.anchor_text, link.source_run_id, link.created_at),
        )
        return link

    def create_chat_resource_link(self, message_id: str, resource_id: str, run_id: str | None = None) -> dict[str, Any]:
        link_id = stable_id("reslink", f"{message_id}:{resource_id}:{run_id or ''}")
        created_at = utc_now()
        self.execute(
            "INSERT OR REPLACE INTO chat_resource_links(id, message_id, resource_id, source_run_id, created_at) VALUES(?,?,?,?,?)",
            (link_id, message_id, resource_id, run_id, created_at),
        )
        return {
            "id": link_id,
            "message_id": message_id,
            "resource_id": resource_id,
            "source_run_id": run_id,
            "created_at": created_at,
        }

    def get_chat_link(self, link_id: str) -> ChatAppLink | None:
        row = self.fetchone("SELECT * FROM chat_app_links WHERE id=?", (link_id,))
        if not row:
            return None
        return ChatAppLink(
            link_id=row["id"],
            message_id=row["message_id"],
            app_id=row["app_id"],
            label=row["label"],
            action=row["action"],
            anchor_text=row["anchor_text"],
            source_run_id=row["source_run_id"],
            created_at=row["created_at"],
        )

    def record_app_event(self, event: AppEvent) -> AppEvent:
        self.execute(
            "INSERT OR REPLACE INTO app_events(id, app_id, student_id, event_type, payload, created_at) VALUES(?,?,?,?,?,?)",
            (event.event_id, event.app_id, event.student_id, event.event_type, dumps(event.payload), event.created_at),
        )
        self.execute(
            "INSERT OR REPLACE INTO learning_events(id, student_id, event_type, payload, created_at) VALUES(?,?,?,?,?)",
            (
                event.event_id,
                event.student_id,
                event.event_type,
                dumps({"app_id": event.app_id, "course_id": event.course_id, "conversation_id": event.conversation_id, **event.payload}),
                event.created_at,
            ),
        )
        return event

    def create_memory(self, memory: EduMemoryItem) -> EduMemoryItem:
        if memory.source_event_id:
            existing = self.get_memory_by_source_event_id(memory.student_id, memory.source_event_id, memory.course_id)
            if existing:
                replay = existing.model_copy(deep=True)
                replay.knowledge_point_id = existing.knowledge_point_id or memory.knowledge_point_id
                replay.evidence_type = existing.evidence_type or memory.evidence_type
                replay.source_event_id = existing.source_event_id or memory.source_event_id
                replay.structured_payload = {
                    **existing.structured_payload,
                    **(memory.structured_payload or {}),
                    "idempotent_replay": True,
                }
                replay.version = existing.version + 1
                replay.updated_at = utc_now()
                replay.confidence = max(existing.confidence, memory.confidence)
                replay.importance = max(existing.importance, memory.importance)
                replay.tags = sorted(set(existing.tags) | set(memory.tags or []))
                replay.content = memory.content or existing.content
                return self._upsert_memory(replay)
        return self._upsert_memory(memory)

    def _upsert_memory(self, memory: EduMemoryItem) -> EduMemoryItem:
        self.execute(
            """
            INSERT OR REPLACE INTO edu_memories(
              id, student_id, course_id, knowledge_point_id, memory_type, content, structured_payload, confidence,
              importance, decay_rate, evidence_type, source_event_id, source_agent, valid_from, valid_until, embedding,
              tags, version, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                memory.id,
                memory.student_id,
                memory.course_id,
                memory.knowledge_point_id,
                memory.memory_type,
                memory.content,
                dumps(memory.structured_payload),
                memory.confidence,
                memory.importance,
                memory.decay_rate,
                memory.evidence_type,
                memory.source_event_id,
                memory.source_agent,
                memory.valid_from,
                memory.valid_until,
                dumps(memory.embedding or []),  # embedding 列暂未使用(记忆检索走关键词),留作未来语义检索扩展
                dumps(memory.tags),
                memory.version,
                memory.created_at,
                memory.updated_at,
            ),
        )
        return memory

    def add_source_agent_memory(self, memory: EduMemoryItem) -> EduMemoryItem:
        memory.structured_payload = {
            **memory.structured_payload,
            "idempotent_replay": True,
            "updated_via_source_event": bool(memory.source_event_id),
        }
        return self._upsert_memory(memory)

    def _memory_from_row(self, row: sqlite3.Row) -> EduMemoryItem:
        item = EduMemoryItem(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            knowledge_point_id=row["knowledge_point_id"],
            memory_type=row["memory_type"],
            content=row["content"],
            structured_payload=loads(row["structured_payload"], {}),
            confidence=row["confidence"],
            importance=row["importance"],
            decay_rate=row["decay_rate"],
            evidence_type=row["evidence_type"],
            source_event_id=row["source_event_id"],
            source_agent=row["source_agent"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            embedding=loads(row["embedding"], []),
            tags=loads(row["tags"], []),
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        valid_from = _parse_iso_ts(item.valid_from)
        item.effective_confidence = round(self.decay.apply(item.confidence, item.decay_rate, valid_from), 3)
        item.decayed = item.effective_confidence < item.confidence
        return item

    def get_memory_by_source_event_id(self, student_id: str, source_event_id: str, course_id: str | None = None) -> EduMemoryItem | None:
        if course_id:
            row = self.fetchone(
                "SELECT * FROM edu_memories WHERE student_id=? AND source_event_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id, source_event_id, course_id),
            )
        else:
            row = self.fetchone("SELECT * FROM edu_memories WHERE student_id=? AND source_event_id=? ORDER BY updated_at DESC LIMIT 1", (student_id, source_event_id))
        return self._memory_from_row(row) if row else None

    def list_memories(
        self,
        student_id: str,
        *,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        conversation_id: str | None = None,
        limit: int = 50,
    ) -> list[EduMemoryItem]:
        clauses = ["student_id=?"]
        params: list[Any] = [student_id]
        if course_id:
            clauses.append("course_id = ?")
            params.append(course_id)
        if knowledge_point_id:
            clauses.append("(knowledge_point_id = ?)")
            params.append(knowledge_point_id)
        if conversation_id:
            clauses.append("(json_extract(structured_payload, '$.conversation_id') IS NULL OR json_extract(structured_payload, '$.conversation_id') = ?)")
            params.append(conversation_id)
        sql = "SELECT * FROM edu_memories WHERE " + " AND ".join(clauses) + " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self.fetchall(sql, tuple(params))
        return [self._memory_from_row(row) for row in rows]

    def search_memories(
        self,
        student_id: str,
        *,
        query: str | None = None,
        memory_types: list[str] | None = None,
        course_id: str | None = None,
        knowledge_point_id: str | None = None,
        limit: int = 10,
    ) -> list[EduMemoryItem]:
        memory_types = memory_types or []
        # 修复:原来先 list_memories(limit=200) 再过滤类型,会让学生在>200条记忆时
        # 丢失早期数据。现在把类型过滤下推到 SQL(WHERE memory_type IN (...)),
        # 再取上限,避免截断导致的老数据不可见。
        clauses = ["student_id = ?"]
        params: list[Any] = [student_id]
        if course_id:
            clauses.append("course_id = ?")
            params.append(course_id)
        if knowledge_point_id:
            clauses.append("knowledge_point_id = ?")
            params.append(knowledge_point_id)
        if memory_types:
            placeholders = ",".join(["?"] * len(memory_types))
            clauses.append(f"memory_type IN ({placeholders})")
            params.extend(memory_types)
        sql = (
            "SELECT * FROM edu_memories WHERE "
            + " AND ".join(clauses)
            + " ORDER BY updated_at DESC LIMIT ?"
        )
        params.append(500)
        rows = self.fetchall(sql, tuple(params))
        memories = [self._memory_from_row(row) for row in rows]
        if query:
            lowered = query.lower()
            memories = [item for item in memories if lowered in item.content.lower() or lowered in dumps(item.structured_payload).lower()]
        memories.sort(key=lambda item: (item.effective_confidence or item.confidence) * item.importance, reverse=True)
        return memories[:limit]

    def get_profile(self, student_id: str, course_id: str | None = None) -> dict[str, Any]:
        if course_id:
            row = self.fetchone(
                "SELECT profile_json FROM student_profiles WHERE student_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id, course_id),
            )
            if not row:
                row = self.fetchone(
                    "SELECT profile_json FROM student_profiles WHERE student_id=? ORDER BY updated_at DESC LIMIT 1",
                    (student_id,),
                )
        else:
            row = self.fetchone(
                "SELECT profile_json FROM student_profiles WHERE student_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id,),
            )
        return loads(row["profile_json"], {}) if row else {}

    def save_profile(self, student_id: str, profile: dict[str, Any], course_id: str | None = None) -> dict[str, Any]:
        now = utc_now()
        target_course = course_id or "ai-course"
        existing_row = self.fetchone(
            "SELECT id, profile_json, version, created_at FROM student_profiles WHERE student_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
            (student_id, target_course),
        )
        existing_profile = loads(existing_row["profile_json"], {}) if existing_row else {}
        merged = merge_profile_dicts(existing_profile, profile or {})
        profile_id = existing_row["id"] if existing_row else stable_id("profile", f"{student_id}:{target_course}")
        version = int(existing_row["version"]) + 1 if existing_row else 1
        created_at = existing_row["created_at"] if existing_row else now
        self.execute(
            """
            INSERT OR REPLACE INTO student_profiles(id, student_id, course_id, profile_json, version, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (profile_id, student_id, target_course, dumps(merged), version, created_at, now),
        )
        return merged

    def profile_status(self, student_id: str, course_id: str | None = None) -> str:
        profile = self.get_profile(student_id, course_id=course_id)
        if not profile:
            return "not_started"
        required = [
            "school",
            "major",
            "grade",
            "schedule",
            "learning_goal",
            "knowledge_foundation",
            "weak_points",
            "preferred_resources",
            "learning_pace",
            "available_study_time",
            "interests",
            "mastery_map",
            "subject_confidence",
        ]
        filled = [key for key in required if profile.get(key) not in (None, "", [], {})]
        # 6/13 core dimensions is enough to enter the canvas; the rest keep
        # filling in during normal use (随学随新). 10 was too strict for a chat flow.
        return "completed" if len(filled) >= 6 else "collecting"

    def onboarding_missing_fields(self, student_id: str, course_id: str | None = None) -> list[str]:
        profile = self.get_profile(student_id, course_id=course_id)
        required_labels = {
            "school": "学校信息",
            "major": "专业",
            "grade": "年级",
            "schedule": "课表",
            "learning_goal": "学习目标",
            "knowledge_foundation": "基础水平",
            "weak_points": "薄弱点",
            "preferred_resources": "偏好资源",
            "learning_pace": "学习节奏",
            "available_study_time": "可用学习时间",
            "interests": "兴趣方向",
            "mastery_map": "掌握图谱",
            "subject_confidence": "科目置信度",
        }
        return [label for key, label in required_labels.items() if profile.get(key) in (None, "", [], {})]

    def start_onboarding(self, student_id: str, course_id: str = "ai-course") -> dict[str, Any]:
        now = utc_now()
        row = self.fetchone(
            "SELECT * FROM onboarding_sessions WHERE student_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
            (student_id, course_id),
        )
        missing = self.onboarding_missing_fields(student_id, course_id)
        if row:
            status = "completed" if self.profile_status(student_id, course_id) == "completed" else row["status"]
            self.execute(
                "UPDATE onboarding_sessions SET status=?, missing_fields=?, updated_at=? WHERE id=?",
                (status, dumps(missing), now, row["id"]),
            )
            return self.get_onboarding_session(row["id"]) or dict(row)
        session_id = stable_id("onboard", f"{student_id}:{course_id}")
        status = "completed" if not missing else "collecting"
        self.execute(
            """
            INSERT OR REPLACE INTO onboarding_sessions(id, student_id, course_id, status, current_step, missing_fields, summary, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (session_id, student_id, course_id, status, "collect_sources", dumps(missing), "画像构建已开始。", now, now),
        )
        return self.get_onboarding_session(session_id) or {
            "id": session_id,
            "student_id": student_id,
            "course_id": course_id,
            "status": status,
            "current_step": "collect_sources",
            "missing_fields": missing,
            "summary": "画像构建已开始。",
            "created_at": now,
            "updated_at": now,
        }

    def get_onboarding_session(self, session_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM onboarding_sessions WHERE id=?", (session_id,))
        if not row:
            return None
        item = dict(row)
        item["missing_fields"] = loads(item.get("missing_fields"), [])
        return item

    def get_latest_onboarding(self, student_id: str, course_id: str | None = None) -> dict[str, Any] | None:
        if course_id:
            row = self.fetchone(
                "SELECT * FROM onboarding_sessions WHERE student_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id, course_id),
            )
        else:
            row = self.fetchone(
                "SELECT * FROM onboarding_sessions WHERE student_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id,),
            )
        if not row:
            return None
        return self.get_onboarding_session(row["id"])

    def update_onboarding(
        self,
        student_id: str,
        course_id: str,
        *,
        status: str | None = None,
        current_step: str | None = None,
        summary: str | None = None,
    ) -> dict[str, Any]:
        session = self.start_onboarding(student_id, course_id)
        next_status = status or session["status"]
        next_step = current_step or session["current_step"]
        next_summary = summary if summary is not None else session["summary"]
        missing = self.onboarding_missing_fields(student_id, course_id)
        self.execute(
            """
            UPDATE onboarding_sessions
            SET status=?, current_step=?, missing_fields=?, summary=?, updated_at=?
            WHERE id=?
            """,
            (next_status, next_step, dumps(missing), next_summary, utc_now(), session["id"]),
        )
        return self.get_onboarding_session(session["id"]) or session

    def save_profile_source(
        self,
        *,
        student_id: str,
        course_id: str,
        source_type: str,
        title: str,
        raw_text: str = "",
        extracted_text: str = "",
        structured_payload: dict[str, Any] | None = None,
        parser_status: str = "parsed",
        parser_reason: str | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        url: str | None = None,
        onboarding_session_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        source_id = new_id("psrc")
        self.execute(
            """
            INSERT INTO profile_sources(
              id, student_id, course_id, onboarding_session_id, source_type, title, raw_text, extracted_text,
              structured_payload, parser_status, parser_reason, file_name, mime_type, url, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                source_id,
                student_id,
                course_id,
                onboarding_session_id,
                source_type,
                title,
                raw_text,
                extracted_text,
                dumps(structured_payload or {}),
                parser_status,
                parser_reason,
                file_name,
                mime_type,
                url,
                now,
            ),
        )
        return {
            "id": source_id,
            "student_id": student_id,
            "course_id": course_id,
            "onboarding_session_id": onboarding_session_id,
            "source_type": source_type,
            "title": title,
            "raw_text": raw_text,
            "extracted_text": extracted_text,
            "structured_payload": structured_payload or {},
            "parser_status": parser_status,
            "parser_reason": parser_reason,
            "file_name": file_name,
            "mime_type": mime_type,
            "url": url,
            "created_at": now,
        }

    def list_profile_sources(self, student_id: str, course_id: str | None = None, limit: int = 80) -> list[dict[str, Any]]:
        if course_id:
            rows = self.fetchall(
                "SELECT * FROM profile_sources WHERE student_id=? AND course_id=? ORDER BY created_at DESC LIMIT ?",
                (student_id, course_id, limit),
            )
        else:
            rows = self.fetchall(
                "SELECT * FROM profile_sources WHERE student_id=? ORDER BY created_at DESC LIMIT ?",
                (student_id, limit),
            )
        items = []
        for row in rows:
            item = dict(row)
            item["structured_payload"] = loads(item.get("structured_payload"), {})
            items.append(item)
        return items

    def save_path(self, student_id: str, course_id: str | None, path: LearningPath) -> LearningPath:
        now = utc_now()
        path_id = getattr(path, "path_id", None) or new_id("path")
        title = getattr(path, "title", None) or "学习路径"
        existing = self.fetchone("SELECT created_at FROM learning_paths WHERE id=?", (path_id,))
        created_at = existing["created_at"] if existing else now
        self.execute(
            """
            INSERT OR REPLACE INTO learning_paths(id, student_id, course_id, title, payload, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (path_id, student_id or "demo-student", course_id, title, path.model_dump_json(), created_at, now),
        )
        return path

    def get_path(self, path_id: str | None = None) -> LearningPath | None:
        if path_id:
            row = self.fetchone("SELECT payload FROM learning_paths WHERE id=? LIMIT 1", (path_id,))
        else:
            row = self.fetchone("SELECT payload FROM learning_paths ORDER BY updated_at DESC LIMIT 1")
        return LearningPath.model_validate_json(row["payload"]) if row else None

    def get_latest_path(self, student_id: str, course_id: str | None = None) -> LearningPath | None:
        if course_id:
            row = self.fetchone(
                "SELECT payload FROM learning_paths WHERE student_id=? AND course_id=? ORDER BY updated_at DESC LIMIT 1",
                (student_id, course_id),
            )
        else:
            row = self.fetchone("SELECT payload FROM learning_paths WHERE student_id=? ORDER BY updated_at DESC LIMIT 1", (student_id,))
        return LearningPath.model_validate_json(row["payload"]) if row else None

    def create_run(self, student_id: str, task_type: str, input_json: dict[str, Any]) -> str:
        run_id = new_id("run")
        now = utc_now()
        self.execute(
            "INSERT INTO agent_runs(id, student_id, task_type, input_json, output_json, status, model_name, latency_ms, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (run_id, student_id, task_type, dumps(input_json), "{}", "running", None, 0, now, now),
        )
        return run_id

    def add_step(self, run_id: str, order: int, name: str, input_json: dict[str, Any] | None = None, output_json: dict[str, Any] | None = None, status: str = "completed") -> str:
        step_id = new_id("step")
        self.execute(
            "INSERT INTO agent_steps(id, run_id, step_order, agent_or_skill, input_json, output_json, status, latency_ms, error_message, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (step_id, run_id, order, name, dumps(input_json or {}), dumps(output_json or {}), status, 0, None, utc_now()),
        )
        return step_id

    def finish_run(self, run_id: str, output_json: dict[str, Any], status: str = "completed") -> None:
        self.execute(
            "UPDATE agent_runs SET output_json=?, status=?, updated_at=? WHERE id=?",
            (dumps(output_json), status, utc_now(), run_id),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.fetchone("SELECT * FROM agent_runs WHERE id=?", (run_id,))
        if not row:
            return None
        steps = self.fetchall("SELECT * FROM agent_steps WHERE run_id=? ORDER BY step_order", (run_id,))
        return {
            "run_id": row["id"],
            "student_id": row["student_id"],
            "task_type": row["task_type"],
            "input_json": loads(row["input_json"], {}),
            "output_json": loads(row["output_json"], {}),
            "status": row["status"],
            "model_name": row["model_name"],
            "latency_ms": row["latency_ms"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "steps": [dict(step) for step in steps],
        }

    def recent_runs(self, limit: int = 8) -> list[dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM agent_runs ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [
            {
                "run_id": row["id"],
                "task_type": row["task_type"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_quiz_question(self, question: QuizQuestion, resource_id: str | None = None) -> QuizQuestion:
        self.execute(
            "INSERT OR REPLACE INTO quiz_questions(id, resource_id, question_type, prompt, options, answer, explanation, knowledge_point_id, difficulty, misconception_tags, source_refs) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
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
        row = self.fetchone("SELECT * FROM quiz_questions WHERE id=?", (question_id,))
        if not row:
            return None
        return QuizQuestion(
            question_id=row["id"],
            question_type=row["question_type"],
            prompt=row["prompt"],
            options=loads(row["options"], []),
            answer=loads(row["answer"], None),
            explanation=row["explanation"] or "",
            knowledge_point_id=row["knowledge_point_id"],
            difficulty=row["difficulty"] or "adaptive",
            misconception_tags=loads(row["misconception_tags"], []),
            source_refs=loads(row["source_refs"], []),
        )

    def save_quiz_submission(self, submission: QuizSubmission) -> QuizSubmission:
        self.execute(
            "INSERT OR REPLACE INTO quiz_submissions(id, student_id, question_id, answer, is_correct, evaluation, created_at) VALUES(?,?,?,?,?,?,?)",
            (
                submission.submission_id,
                submission.student_id,
                submission.question_id,
                dumps(submission.answer),
                1 if submission.is_correct else 0,
                dumps(submission.evaluation),
                submission.created_at,
            ),
        )
        return submission

    def save_feedback(self, student_id: str, payload: dict[str, Any]) -> str:
        feedback_id = new_id("feedback")
        self.execute(
            """
            INSERT OR REPLACE INTO feedbacks(id, student_id, resource_id, app_id, rating, comment, payload, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                feedback_id,
                student_id,
                payload.get("resource_id"),
                payload.get("app_id"),
                payload.get("rating"),
                payload.get("comment"),
                dumps(payload),
                utc_now(),
            ),
        )
        return feedback_id

    def upsert_mastery(self, student_id: str, course_id: str, knowledge_point_id: str, delta: float, evidence: dict[str, Any]) -> float:
        row = self.fetchone(
            "SELECT * FROM mastery_records WHERE student_id=? AND course_id=? AND knowledge_point_id=?",
            (student_id, course_id, knowledge_point_id),
        )
        current = row["mastery_score"] if row else 0.35
        updated = min(1.0, max(0.0, current + delta))
        self.execute(
            "INSERT OR REPLACE INTO mastery_records(id, student_id, course_id, knowledge_point_id, mastery_score, confidence, evidence_json, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (f"mastery-{student_id}-{course_id}-{knowledge_point_id}", student_id, course_id, knowledge_point_id, updated, 0.82, dumps(evidence), utc_now()),
        )
        return updated

    def knowledge_graph(self, course_id: str = "ai-course") -> dict[str, Any]:
        points = [dict(row) for row in self.fetchall("SELECT * FROM knowledge_points WHERE course_id=?", (course_id,))]
        edges = [dict(row) for row in self.fetchall("SELECT * FROM knowledge_edges WHERE course_id=?", (course_id,))]
        return {"course_id": course_id, "nodes": points, "edges": edges}

    def retrieve_chunks(self, topic: str, limit: int = 3, course_id: str | None = None, *, min_score: float = 6.0) -> list[dict[str, Any]]:
        cleaned_topic = (topic or "").strip()
        if not cleaned_topic:
            return []
        query_terms = search_terms_for(cleaned_topic)
        if course_id:
            rows = self.fetchall("SELECT * FROM document_chunks WHERE course_id=? ORDER BY chunk_index", (course_id,))
        else:
            rows = self.fetchall("SELECT * FROM document_chunks ORDER BY chunk_index")
        if not rows:
            return []
        has_real_embeddings = any(
            isinstance(embedding := loads(row["embedding"], []), list) and len(embedding) > 10
            for row in rows[: min(len(rows), 50)]
        )
        query_embedding = embed_text(cleaned_topic, "RETRIEVAL_QUERY") if cleaned_topic and has_real_embeddings else []

        def score(row: sqlite3.Row) -> tuple[float, dict[str, Any]]:
            content = row["content"] or ""
            source = row["source_ref"] or ""
            haystack = f"{content}\n{source}".lower()
            result = 0.0
            matched_terms: list[str] = []
            exact_match = False
            vector_score = 0.0
            if cleaned_topic and cleaned_topic.lower() in haystack:
                result += 24.0
                exact_match = True
            for term in query_terms:
                count = haystack.count(term.lower())
                if count:
                    matched_terms.append(term)
                    result += min(8.0, count * 1.7)
                    if term in source.lower():
                        result += 1.5
            if query_terms and all(term.lower() in haystack for term in list(query_terms)[:5]):
                result += 5.0
            if query_embedding:
                embedding = loads(row["embedding"], [])
                if isinstance(embedding, list) and len(embedding) == len(query_embedding):
                    vector_score = max(0.0, cosine_similarity(query_embedding, [float(value) for value in embedding]))
                    result += vector_score * 35.0
            return result, {
                "matched_terms": sorted(set(matched_terms), key=lambda term: (-len(term), term))[:8],
                "exact_match": exact_match,
                "vector_score": round(vector_score, 4),
            }

        ranked = sorted(((score(row), row) for row in rows), key=lambda item: (-item[0][0], item[1]["chunk_index"]))
        selected = [
            (item_score, meta, row)
            for (item_score, meta), row in ranked
            if item_score >= min_score and (meta["exact_match"] or meta["matched_terms"] or meta["vector_score"] >= 0.78)
        ][:limit]
        return [
            {
                "chunk_id": row["id"],
                "content": row["content"],
                "source_ref": loads(row["source_ref"], {}),
                "score": round(float(item_score), 4),
                "matched_terms": meta["matched_terms"],
                "vector_score": meta["vector_score"],
                "snippet": snippet_for(row["content"], cleaned_topic),
            }
            for item_score, meta, row in selected
        ]

    def dashboard(self, student_id: str = "demo-student", course_id: str | None = None, conversation_id: str | None = None) -> DashboardSnapshot:
        profile = self.get_profile(student_id, course_id=course_id or "ai-course")
        if course_id:
            mastery_rows = self.fetchall(
                "SELECT knowledge_point_id, mastery_score FROM mastery_records WHERE student_id=? AND course_id=?",
                (student_id, course_id),
            )
        else:
            mastery_rows = self.fetchall("SELECT knowledge_point_id, mastery_score FROM mastery_records WHERE student_id=?", (student_id,))
        profile_mastery = profile.get("mastery_map", {})
        mastery = {row["knowledge_point_id"]: row["mastery_score"] for row in mastery_rows} or (profile_mastery if isinstance(profile_mastery, dict) else {})
        raw_weak_points = profile.get("weak_points", [])
        if isinstance(raw_weak_points, list):
            weak_points = raw_weak_points
        elif raw_weak_points in (None, "", {}):
            weak_points = []
        else:
            weak_points = [str(raw_weak_points)]
        memories = self.list_memories(student_id, course_id=course_id, conversation_id=conversation_id, limit=12)
        if course_id:
            apps = self.fetchall(
                "SELECT id, app_type, title, updated_at FROM canvas_apps WHERE student_id=? AND json_extract(layout, '$.course_id')=? ORDER BY updated_at DESC LIMIT 6",
                (student_id, course_id),
            )
        else:
            apps = self.fetchall("SELECT id, app_type, title, updated_at FROM canvas_apps WHERE student_id=? ORDER BY updated_at DESC LIMIT 6", (student_id,))
        return DashboardSnapshot(
            student_id=student_id,
            profile=profile,
            mastery=mastery,
            weak_points=weak_points,
            recommendations=[
                {"title": "先完成梯度下降诊断题", "reason": "数学推导弱点与当前路径匹配", "score": 0.91},
                {"title": "打开动能定理演示", "reason": "用物理能量变化建立优化步长直觉", "score": 0.86},
            ],
            memory_evidence=memories,
            recent_runs=self.recent_runs(),
            path_progress=(latest_path.overall_progress if (latest_path := self.get_latest_path(student_id, course_id=course_id)) else 0),
            canvas_activity=[dict(row) for row in apps],
        )

    # ---- Learning Focus (current topic / objective) ----
    # Persisted inside student_profiles.profile_json under "_learning_focus" so it survives
    # across processes/workers and works for the Postgres backend. An instance-level dict
    # is kept as a hot cache; the DB is the source of truth.

    def save_learning_focus(self, student_id: str, course_id: str, topic: str, objective: str | None = None, course_label: str | None = None) -> None:
        focus = {
            "topic": topic,
            "objective": objective or "",
            "course_label": course_label or "",
            "updated_at": utc_now(),
        }
        profile = self.get_profile(student_id, course_id=course_id)
        profile["_learning_focus"] = focus
        self.save_profile(student_id, profile, course_id=course_id)

    def get_learning_focus(self, student_id: str, course_id: str) -> dict[str, str]:
        focus = (self.get_profile(student_id, course_id=course_id) or {}).get("_learning_focus") or {}
        return focus if isinstance(focus, dict) else {}

@lru_cache
def get_store() -> Any:
    settings = get_settings()
    if settings.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        from app.database.postgres_store import PostgresLearningStore

        return PostgresLearningStore(settings.database_url)
    raise RuntimeError("SQLite runtime has been retired. Set DATABASE_URL to a PostgreSQL connection string.")
