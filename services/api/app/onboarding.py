from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from html import unescape
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from app.core.config import get_settings, missing_secret
from app.edumem0.client import EduMem0Client
from app.schemas.app_protocol import EduMemoryItem


PROFILE_FIELDS = [
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


def compact_text(text: str, limit: int = 6000) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:limit]


async def extract_dimensions_with_llm(message: str) -> dict[str, Any]:
    """Use the LLM (Gemini) to parse a free-form message into the 13 profile
    dimensions as JSON. Far more robust than keyword rules — handles any school,
    major, grade, study time, etc. Returns only non-empty fields; {} on failure."""
    import json as _json

    text = (message or "").strip()
    if not text:
        return {}
    from app.model_gateway.base import ChatMessage
    from app.model_gateway.router import ModelGatewayRouter

    system = (
        "你是学习画像抽取器。从用户中文自述里抽取以下字段，返回严格 JSON，无 markdown、无多余文字。\n"
        "字段：school(学校)、major(专业)、grade(年级)、schedule(课表/上课时间)、learning_goal(学习目标)、"
        "knowledge_foundation(知识基础)、weak_points(薄弱点,数组)、preferred_resources(偏好资源,数组)、"
        "learning_pace(学习节奏)、available_study_time(每周可用学习时间)、interests(兴趣,数组)、"
        "mastery_map(对象,知识点->0~1)、subject_confidence(对象,科目->0~1)。\n"
        "只输出用户明确提到或可合理推断的字段；没有信息的字段直接省略，不要编造。数组字段用 JSON 数组。"
    )
    user = f"用户自述：\n{text[:1500]}\n\n只返回 JSON 对象。"
    try:
        client = ModelGatewayRouter().client()
        response = await client.complete(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            stream=False,
        )
        raw = client.extract_assistant_text(response).strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return {}
        data = _json.loads(raw[start : end + 1])
    except _json.JSONDecodeError:
        # Model returned something we couldn't parse — profile extraction is best-effort.
        logging.getLogger("learnforge").warning("extract_dimensions_with_llm: non-JSON model output, skipping")
        return {}
    except Exception:
        logging.getLogger("learnforge").exception("extract_dimensions_with_llm: unexpected failure, skipping")
        return {}
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key in PROFILE_FIELDS:
        value = data.get(key)
        if value in (None, "", [], {}):
            continue
        cleaned[key] = value
    return cleaned


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_csv_schedule(text: str) -> tuple[str, dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return text, {"rows": [], "schedule": []}
    schedule = []
    for row in rows[:80]:
        normalized = {str(key or "").strip().lower(): str(value or "").strip() for key, value in row.items()}
        course = (
            normalized.get("course")
            or normalized.get("课程")
            or normalized.get("课程名")
            or normalized.get("name")
            or next((value for value in normalized.values() if value), "")
        )
        schedule.append(
            {
                "course": course,
                "weekday": normalized.get("weekday") or normalized.get("星期") or normalized.get("周几") or normalized.get("day"),
                "time": normalized.get("time") or normalized.get("时间") or normalized.get("节次") or normalized.get("period"),
                "location": normalized.get("location") or normalized.get("地点") or normalized.get("教室"),
                "teacher": normalized.get("teacher") or normalized.get("老师") or normalized.get("教师"),
                "note": normalized.get("note") or normalized.get("备注"),
            }
        )
    summary = "；".join(
        " ".join(str(part) for part in [item.get("weekday"), item.get("time"), item.get("course")] if part)
        for item in schedule[:12]
    )
    return summary or text[:1200], {"rows": rows[:80], "schedule": schedule}


def _parse_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    texts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
    return "\n".join(texts)


def _parse_xlsx(data: bytes) -> tuple[str, dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root:
                shared.append("".join(t.text or "" for t in si.iter() if t.tag.endswith("}t")))
        sheet_name = next((name for name in archive.namelist() if name.startswith("xl/worksheets/sheet")), "")
        if not sheet_name:
            return "", {"rows": [], "schedule": []}
        root = ElementTree.fromstring(archive.read(sheet_name))
    rows: list[list[str]] = []
    for row in root.iter():
        if not row.tag.endswith("}row"):
            continue
        values: list[str] = []
        for cell in [node for node in row if node.tag.endswith("}c")]:
            cell_type = cell.attrib.get("t")
            value_node = next((node for node in cell if node.tag.endswith("}v")), None)
            value = value_node.text if value_node is not None and value_node.text is not None else ""
            if cell_type == "s" and value.isdigit() and int(value) < len(shared):
                value = shared[int(value)]
            values.append(value)
        if any(item.strip() for item in values):
            rows.append(values)
    if not rows:
        return "", {"rows": [], "schedule": []}
    headers = [item.strip() or f"列{i + 1}" for i, item in enumerate(rows[0])]
    dict_rows = [dict(zip(headers, row)) for row in rows[1:80]]
    csv_text = io.StringIO()
    writer = csv.DictWriter(csv_text, fieldnames=headers)
    writer.writeheader()
    writer.writerows(dict_rows)
    summary, payload = _parse_csv_schedule(csv_text.getvalue())
    payload["rows"] = dict_rows
    return summary, payload


def _parse_pdf(data: bytes) -> tuple[str, str]:
    """抽取 PDF 文本。

    优先用 pypdf 做真正的结构化抽取（按页 extract_text）。旧实现只是把原始字节
    decode 成文本，拿到的是 `%PDF-1.7 ... 1 0 obj` 这种二进制标记，存进 chunk 后
    既不能检索也不能被 Open Notebook 向量化。

    抽不出文字（扫描件 / 图片型 PDF）时返回空字符串，绝不把原始字节当文本存。
    """
    try:
        from pypdf import PdfReader
        import io as _io
        reader = PdfReader(_io.BytesIO(data))
    except Exception as exc:  # pypdf 未安装或文件损坏
        return "", f"PDF 解析器不可用：{type(exc).__name__}: {exc}"
    parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            parts.append(page_text)
    text = "\n".join(parts).strip()
    if len(text) < 80:
        return "", "PDF 抽取到的文字过短（可能是扫描件或图片型 PDF），请上传可选中文字的 PDF，或补充文字说明。"
    # 保留较完整内容（上限 50000 字），交给下游 _compact_chunks 切片
    return compact_text(text, 50000), "PDF 文本已用 pypdf 抽取；扫描件/图片型 PDF 可能仍需 OCR。"


def classify_source(filename: str | None, mime_type: str | None, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    if "image/" in mime or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if name.endswith(".csv"):
        return "schedule"
    if name.endswith(".xlsx"):
        return "schedule"
    if name.endswith((".docx", ".doc")):
        return "office"
    if name.endswith(".pdf"):
        return "document"
    return "document"


async def parse_profile_upload(
    *,
    data: bytes,
    filename: str | None,
    mime_type: str | None,
    source_type: str | None = None,
) -> dict[str, Any]:
    kind = classify_source(filename, mime_type, source_type)
    name = filename or "学习资料"
    try:
        if kind == "image":
            settings = get_settings()
            if missing_secret(settings.gemini_api_key):
                return {
                    "source_type": "image",
                    "title": name,
                    "raw_text": "",
                    "extracted_text": "",
                    "structured_payload": {"ocr_provider": "gemini", "bytes": len(data)},
                    "parser_status": "blocked_ocr_credentials",
                    "parser_reason": "GEMINI_API_KEY 缺失，图片 OCR 未执行。",
                }
            return {
                "source_type": "image",
                "title": name,
                "raw_text": "",
                "extracted_text": "",
                "structured_payload": {"ocr_provider": "gemini", "bytes": len(data)},
                "parser_status": "blocked_ocr_runtime",
                "parser_reason": "图片 OCR 管线预留，当前版本先保存来源。",
            }
        if name.lower().endswith(".xlsx"):
            text, payload = _parse_xlsx(data)
            return {"source_type": "schedule", "title": name, "raw_text": "", "extracted_text": text, "structured_payload": payload, "parser_status": "parsed", "parser_reason": None}
        if name.lower().endswith((".docx", ".doc")):
            text = _parse_docx(data)
            return {"source_type": "office", "title": name, "raw_text": "", "extracted_text": compact_text(text), "structured_payload": {}, "parser_status": "parsed", "parser_reason": None}
        if name.lower().endswith(".pdf"):
            text, reason = _parse_pdf(data)
            return {
                "source_type": "document",
                "title": name,
                "raw_text": "",
                "extracted_text": text,
                "structured_payload": {},
                "parser_status": "parsed" if text else "blocked_parser_limited",
                "parser_reason": reason,
            }
        text = _decode_bytes(data)
        if name.lower().endswith(".csv") or kind == "schedule":
            summary, payload = _parse_csv_schedule(text)
            return {"source_type": "schedule", "title": name, "raw_text": text[:12000], "extracted_text": compact_text(summary), "structured_payload": payload, "parser_status": "parsed", "parser_reason": None}
        return {"source_type": kind, "title": name, "raw_text": text[:12000], "extracted_text": compact_text(text), "structured_payload": {}, "parser_status": "parsed", "parser_reason": None}
    except Exception as exc:
        text = _decode_bytes(data)
        return {
            "source_type": kind,
            "title": name,
            "raw_text": text[:12000],
            "extracted_text": compact_text(text),
            "structured_payload": {},
            "parser_status": "blocked_parser_error",
            "parser_reason": f"{type(exc).__name__}: {exc}",
        }


async def fetch_url_source(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    title = parsed.netloc or url
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        text = response.text
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = compact_text(unescape(re.sub(r"<[^>]+>", " ", title_match.group(1))), 120)
        visible = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.IGNORECASE)
        visible = re.sub(r"<[^>]+>", " ", visible)
        return {
            "source_type": "url",
            "title": title,
            "raw_text": url,
            "extracted_text": compact_text(unescape(visible)),
            "structured_payload": {"url": url, "status_code": response.status_code},
            "parser_status": "parsed",
            "parser_reason": None,
        }
    except Exception as exc:
        return {
            "source_type": "url",
            "title": title,
            "raw_text": url,
            "extracted_text": "",
            "structured_payload": {"url": url},
            "parser_status": "blocked_fetch_error",
            "parser_reason": f"{type(exc).__name__}: {exc}",
        }


def infer_profile_from_text(text: str) -> dict[str, Any]:
    lowered = text.lower()
    profile: dict[str, Any] = {}
    school_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]+(?:大学|学院|学校|中学|高中))", text)
    if school_match:
        profile["school"] = school_match.group(1)
    if "软件工程" in text:
        profile["major"] = "软件工程"
    elif "计算机" in text:
        profile["major"] = "计算机相关"
    for grade in ["大一", "大二", "大三", "大四", "高一", "高二", "高三", "研一", "研二"]:
        if grade in text:
            profile["grade"] = grade
            break
    if "python" in lowered:
        profile["knowledge_foundation"] = "Python 一般" if "一般" in text else "Python 有基础"
    weak_terms = ["弱", "薄弱", "一般", "困难"]
    if any(term in text for term in weak_terms) and any(topic in text for topic in ["数学", "线性代数", "推导"]):
        weak_points: list[str] = []
        if "线性代数" in text:
            weak_points.append("线性代数")
        if "数学" in text or "推导" in text:
            weak_points.append("数学推导")
        profile["weak_points"] = weak_points or ["数学推导"]
    if "图解" in text or "可视化" in text:
        profile.setdefault("preferred_resources", []).append("图解")
        profile["cognitive_style"] = "图解优先，配合互动可视化"
    if "代码" in text or "编程" in text:
        profile.setdefault("preferred_resources", []).append("代码练习")
        profile.setdefault("interests", []).append("代码实验")
    if "小步" in text or "分阶段" in text:
        profile["learning_pace"] = "小步练习，分阶段推进"
    if "每天" in text or "每周" in text or "小时" in text:
        time_match = re.search(r"((?:每天|每周)?[^，。；\n]{0,8}\d+(?:\.\d+)?\s*(?:小时|h|分钟))", text, re.IGNORECASE)
        if time_match:
            profile["available_study_time"] = time_match.group(1)
    if "神经网络" in text:
        profile["learning_goal"] = "学习神经网络"
        profile.setdefault("interests", []).append("神经网络训练")
    elif "目标" in text:
        profile["learning_goal"] = compact_text(text, 80)
    profile.setdefault("learning_pace", "分阶段练习")
    profile.setdefault("preferred_resources", [])
    profile["preferred_resources"] = list(dict.fromkeys(profile.get("preferred_resources", [])))
    if profile.get("interests"):
        profile["interests"] = list(dict.fromkeys(profile["interests"]))
    return profile


def infer_profile_from_sources(sources: list[dict[str, Any]], messages: list[str]) -> dict[str, Any]:
    combined = "\n".join(
        [
            *(str(source.get("extracted_text") or source.get("raw_text") or "") for source in sources),
            *messages,
        ]
    )
    profile = infer_profile_from_text(combined)
    schedules = [
        source.get("structured_payload", {}).get("schedule")
        for source in sources
        if source.get("source_type") == "schedule" and isinstance(source.get("structured_payload"), dict)
    ]
    schedule_items = [item for block in schedules if isinstance(block, list) for item in block]
    if schedule_items:
        profile["schedule"] = schedule_items[:24]
        subjects = [str(item.get("course") or "") for item in schedule_items if isinstance(item, dict) and item.get("course")]
        if subjects:
            profile["subjects"] = list(dict.fromkeys(subjects))[:12]
    if "schedule" not in profile and "课表" in combined:
        profile["schedule"] = compact_text(combined, 1000)
    profile.setdefault("school", "待补充")
    profile.setdefault("major", "待补充")
    profile.setdefault("grade", "待补充")
    profile.setdefault("learning_goal", "建立个性化学习路径")
    profile.setdefault("knowledge_foundation", "待诊断")
    profile.setdefault("weak_points", [])
    profile.setdefault("preferred_resources", ["图解", "短练习"])
    profile.setdefault("learning_pace", "分阶段练习")
    profile.setdefault("available_study_time", "待补充")
    profile.setdefault("interests", [])
    profile.setdefault("schedule", [])
    profile.setdefault("mastery_map", {"数学推导基础": 0.35 if "数学" in combined and ("弱" in combined or "一般" in combined) else 0.5})
    profile.setdefault("subject_confidence", {"待补充": 0.25})
    return profile


def profile_memory_from_source(student_id: str, course_id: str, source: dict[str, Any], profile: dict[str, Any] | None = None) -> EduMemoryItem:
    dimensions = profile or infer_profile_from_text(str(source.get("extracted_text") or source.get("raw_text") or ""))
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        memory_type="profile",
        content=f"画像来源 {source.get('title')} 提供了学习信息：{compact_text(str(source.get('extracted_text') or source.get('raw_text') or ''), 240)}",
        structured_payload={
            "dimensions": dimensions,
            "source_id": source.get("id"),
            "source_type": source.get("source_type"),
            "parser_status": source.get("parser_status"),
        },
        confidence=0.56 if source.get("parser_status") == "parsed" else 0.32,
        importance=0.72,
        decay_rate=0.0,
        evidence_type="chat" if source.get("source_type") == "chat_message" else "system_inferred",
        source_event_id=source.get("id"),
        source_agent="profile_agent",
        tags=["profile", "onboarding", str(source.get("source_type") or "source")],
    )


def write_profile_memories(student_id: str, course_id: str, sources: list[dict[str, Any]], profile: dict[str, Any]) -> list[EduMemoryItem]:
    client = EduMem0Client()
    memories: list[EduMemoryItem] = []
    for source in sources[:24]:
        memories.append(client.add(profile_memory_from_source(student_id, course_id, source, profile)))
    return memories
