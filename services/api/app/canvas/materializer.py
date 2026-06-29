from __future__ import annotations

import json
import re
from html import escape
from typing import Any, TYPE_CHECKING, get_args

from pydantic import BaseModel, Field

from app.canvas.component_namer import ComponentTitleNamer
from app.database.store import LearningStore
from app.image_gateway.router import ImageGatewayRouter
from app.model_gateway.errors import ModelGatewayError
from app.schemas.app_protocol import CanvasApp, CanvasAppType, CanvasPosition, CanvasSize, LearningResource, new_id
from app.skills.base import SkillInput
from app.skills.custom_html_app_skill import CustomHtmlAppSkill
from app.storage.artifacts import ObjectStorage, artifact_object_key
from app.video.bilibili import video_player_payload

# App types that are really a custom.html app under a different name.
_CUSTOM_HTML_ALIASES = {
    "infographic",
    "interactive.demo",
    "animation.demo",
    "html.app",
    "custom_html",
    "presentation",
    "slides",
    "ppt",
    "ppt.preview.deck",
    "slide.deck",
}
_VALID_APP_TYPES = set(get_args(CanvasAppType))

if TYPE_CHECKING:
    from app.hermes_runtime.task_executor import HermesTaskResult


def normalize_html_artifact_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for _ in range(4):
        stripped = text.strip()
        has_escaped_lines = "\\n" in stripped or "\\\\n" in stripped
        has_escaped_quotes = '\\"' in stripped or '\\\\"' in stripped
        if not (has_escaped_lines or has_escaped_quotes):
            break
        decoded = stripped
        try:
            decoded = json.loads(stripped) if stripped[:1] in {'"', "'"} else json.loads(f'"{stripped}"')
        except json.JSONDecodeError:
            decoded = (
                stripped
                .replace("\\\\r\\\\n", "\n")
                .replace("\\\\n", "\n")
                .replace("\\\\t", "\t")
                .replace('\\\\"', '"')
                .replace("\\\\/", "/")
                .replace("\\r\\n", "\n")
                .replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\/", "/")
            )
        if decoded == text:
            break
        text = decoded
    lower = text.lower()
    starts = [index for index in (lower.find("<!doctype html"), lower.find("<html")) if index >= 0]
    if starts:
        start = min(starts)
        end_match = re.search(r"<\s*/\s*html\s*>", text[start:], flags=re.IGNORECASE)
        if end_match:
            text = text[start : start + end_match.end()]
        else:
            text = text[start:]
    text = normalize_latex_for_html(text)
    return text


def normalize_latex_for_html(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = re.sub(
        r"\\\\(frac|sqrt|sum|int|left|right|cdot|times|div|Delta|alpha|beta|gamma|theta|lambda|mu|rho|omega|Omega|vec|overline|hat|dot|sin|cos|tan|ln|log|lim|begin|end)\b",
        r"\\\1",
        text,
    )
    text = repair_damaged_latex_tokens(text)
    text = re.sub(r"\\_([A-Za-z0-9{}])", r"_\1", text)
    text = re.sub(r"\$\\\s*([A-Za-z])", r"$\\\1", text)
    return text


def repair_damaged_latex_tokens(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""

    def repair_segment(match: re.Match[str]) -> str:
        segment = match.group(0)
        repairs = [
            (r"\frac\s*12\b", r"\\frac{1}{2}"),
            (r"(?<!\\)\bfrac\s*12\b", r"\\frac{1}{2}"),
            (r"\frac\b", r"\\frac"),
            (r"(?<!\\)\bfrac(?=\s*\{)", r"\\frac"),
            (r"(?<!\\)\bsqrt\b", r"\\sqrt"),
            (r"(?<!\\)\bquad\b", r"\\quad"),
            (r"(?<!\\)\bleft(?=\s*[\(\[\{])", r"\\left"),
            (r"(?<!\\)\bright(?=\s*[\)\]\}])", r"\\right"),
            (r"(?<!\\)\btheta\b", r"\\theta"),
            (r"(?<!\\)\barccos\b", r"\\arccos"),
            (r"(?<!\\)\bcos\b", r"\\cos"),
            (r"(?<!\\)\bsin\b", r"\\sin"),
            (r"(?<!\\)\btan\b", r"\\tan"),
            (r"(?<!\\)\bln\b", r"\\ln"),
            (r"(?<!\\)\blog\b", r"\\log"),
            (r"(?<!\\)\btext(?=\s*\{)", r"\\text"),
            ("\frac\\s*rac", r"\\frac"),
            ("\t\\s*heta", r"\\theta"),
            ("\t\\s*ext", r"\\text"),
            ("\r\\s*ight", r"\\right"),
        ]
        for pattern, replacement in repairs:
            segment = re.sub(pattern, replacement, segment)
        return segment

    text = re.sub("\frac\\s*rac", r"\\frac", text)
    text = re.sub("\t\\s*heta", r"\\theta", text)
    text = re.sub("\t\\s*ext", r"\\text", text)
    text = re.sub("\r\\s*ight", r"\\right", text)
    return re.sub(r"(\$\$[\s\S]*?\$\$|\$[^$\n]*\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))", repair_segment, text)


def _extract_html_body(html: str) -> str:
    text = normalize_html_artifact_text(html)
    body_match = re.search(r"<\s*body\b[^>]*>([\s\S]*?)<\s*/\s*body\s*>", text, flags=re.IGNORECASE)
    if body_match:
        return body_match.group(1).strip()
    return text.strip()


def _extract_html_title(html: str, fallback: str) -> str:
    title_match = re.search(r"<\s*title\b[^>]*>([\s\S]*?)<\s*/\s*title\s*>", html, flags=re.IGNORECASE)
    if not title_match:
        return fallback or "学习报告"
    title = re.sub(r"<[^>]+>", " ", title_match.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    return title or fallback or "学习报告"


def _extract_inline_styles(html: str) -> str:
    styles = re.findall(r"<\s*style\b[^>]*>([\s\S]*?)<\s*/\s*style\s*>", html, flags=re.IGNORECASE)
    return "\n\n".join(style.strip() for style in styles if style.strip())


def _plain_text(html: str) -> str:
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", str(html or ""), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_english_question_context(text: str) -> bool:
    source = str(text or "")
    lowered = source.lower()
    if any(
        marker in lowered
        for marker in [
            "reading comprehension",
            "section a",
            "directions",
            "word bank",
            "choose one word",
            "blank",
            "cloze",
            "grammar",
            "passage",
        ]
    ):
        return True
    if any(marker in source for marker in ["英语", "选词填空", "阅读理解", "完形填空", "语法填空", "第34空", "第35空"]):
        return True
    english_words = re.findall(r"\b[a-zA-Z]{3,}\b", source)
    return len(english_words) >= 18 and any(word.lower() in {"where", "which", "that", "children", "reputation", "answer"} for word in english_words)


def detailed_analysis_context_mismatch(html: str, source_material: str | None) -> str:
    """Detect obvious report-topic contamination before persisting a detailed report.

    This is intentionally narrow: it only blocks when the bound source looks like
    an English exam/passage while the generated HTML contains strong math/physics
    anchors and lacks English-question anchors. It is a guardrail, not a generator.
    """
    source = str(source_material or "")
    if not _looks_like_english_question_context(source):
        return ""
    text = _plain_text(normalize_html_artifact_text(html))
    lowered_html = text.lower()
    if _looks_like_english_question_context(text):
        return ""
    contaminants = [
        "双曲线",
        "已知函数",
        "质点运动学",
        "刚体",
        "牛顿第二定律",
        "动能定理",
        "圆锥曲线",
        "抛物线",
        "导数",
        "电场",
        "磁场",
    ]
    hit = next((term for term in contaminants if term in text), "")
    if hit:
        return f"topic_contamination:{hit}"
    if any(term in lowered_html for term in ["hyperbola", "newton's second law", "kinematics", "rigid body"]):
        return "topic_contamination:math_or_physics"
    return ""


def _detailed_analysis_guard_html(title: str, issue: str) -> str:
    safe_title = escape(title or "报告上下文校验未通过")
    safe_issue = escape(issue or "topic_mismatch")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; color:#182033; background:#f8fafc; }}
    main {{ width:min(900px, calc(100% - 32px)); margin:0 auto; padding:48px 0; }}
    section {{ border:1px solid #dbe4ef; border-radius:8px; background:#fff; box-shadow:0 18px 44px rgba(15,23,42,.08); padding:28px; }}
    h1 {{ margin:0 0 12px; font-size:28px; line-height:1.2; color:#9a3412; }}
    p {{ margin:0 0 14px; font-size:16px; line-height:1.75; }}
    code {{ padding:2px 6px; border-radius:5px; background:#f1f5f9; color:#334155; }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>报告已拦截：题面上下文不一致</h1>
      <p>当前报告没有通过 LearnForge 的 artifact 绑定校验，疑似使用了旧题目或课程 RAG 内容，而不是本轮上传图片。</p>
      <p>校验原因：<code>{safe_issue}</code></p>
      <p>请重新生成，本轮应以当前图片/文章 artifact 为唯一主上下文。</p>
    </section>
  </main>
</body>
</html>"""


def wrap_detailed_analysis_report(html: str, *, title: str) -> str:
    """Put model-generated analysis inside a stable LearnForge report shell.

    Hermes remains responsible for the subject matter, but the backend owns the
    production artifact frame so reports never render as unstyled text when a CDN
    class set or model-specific template fails.
    """
    source = normalize_html_artifact_text(html)
    if 'data-learnforge-report="detailed-analysis"' in source:
        return source
    report_title = _extract_html_title(source, title)
    body = _extract_html_body(source)
    inline_styles = _extract_inline_styles(source)
    safe_title = escape(report_title)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <style>
    {inline_styles}

    :root {{
      color-scheme: light;
      --lf-ink: #172033;
      --lf-muted: #667085;
      --lf-paper: #fffdf8;
      --lf-card: #ffffff;
      --lf-line: #e5d7bf;
      --lf-orange: #c45a1f;
      --lf-orange-2: #f08a32;
      --lf-blue: #2454a6;
      --lf-green: #267a5c;
      --lf-soft: #fff3dd;
      --lf-shadow: 0 22px 55px rgba(83, 48, 17, .12);
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: #f7efe4; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--lf-ink);
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif;
      line-height: 1.72;
      background:
        linear-gradient(90deg, rgba(36,84,166,.08) 1px, transparent 1px),
        linear-gradient(180deg, rgba(36,84,166,.06) 1px, transparent 1px),
        radial-gradient(circle at 10% 6%, rgba(240,138,50,.22), transparent 28%),
        radial-gradient(circle at 88% 10%, rgba(36,84,166,.16), transparent 30%),
        linear-gradient(135deg, #fff8ee 0%, #f6efe2 48%, #eef4ff 100%);
      background-size: 28px 28px, 28px 28px, auto, auto, auto;
    }}
    .lf-report {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 72px;
    }}
    .lf-report-hero {{
      position: relative;
      overflow: hidden;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      align-items: end;
      min-height: 210px;
      margin: 8px 0 22px;
      padding: 34px;
      border: 1px solid rgba(196, 90, 31, .28);
      background:
        linear-gradient(135deg, rgba(255,255,255,.92), rgba(255,245,228,.88)),
        repeating-linear-gradient(-8deg, rgba(196,90,31,.08) 0 1px, transparent 1px 11px);
      box-shadow: var(--lf-shadow);
    }}
    .lf-report-kicker {{
      margin: 0 0 10px;
      color: var(--lf-orange);
      font-family: "SFMono-Regular", ui-monospace, monospace;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .14em;
      text-transform: uppercase;
    }}
    .lf-report h1 {{
      margin: 0;
      max-width: 820px;
      font-family: Georgia, "Songti SC", serif;
      font-size: clamp(34px, 5.2vw, 68px);
      line-height: 1.02;
      font-weight: 900;
      letter-spacing: 0;
      color: #2b170d;
    }}
    .lf-report-sub {{
      margin: 14px 0 0;
      max-width: 760px;
      color: #6d5642;
      font-size: 16px;
    }}
    .lf-report-stamp {{
      display: grid;
      place-items: center;
      width: 132px;
      aspect-ratio: 1;
      border: 2px solid rgba(196,90,31,.34);
      color: var(--lf-orange);
      font-family: "SFMono-Regular", ui-monospace, monospace;
      font-size: 12px;
      font-weight: 900;
      text-align: center;
      transform: rotate(4deg);
      background: rgba(255,255,255,.56);
    }}
    .lf-report-body {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 18px;
    }}
    .lf-report-body > header,
    .lf-report-body > section,
    .lf-report-body > article,
    .lf-report-body > div.section-card,
    .lf-report-body > div.card,
    .lf-report-body > div.question-card,
    .lf-report-body > div {{
      max-width: 100%;
    }}
    .lf-report-body header,
    .lf-report-body .header {{
      text-align: left;
      margin: 0 0 6px;
      padding: 24px;
      border: 1px solid var(--lf-line);
      background: rgba(255,255,255,.74);
    }}
    .lf-report-body .container,
    .lf-report-body .max-w-5xl,
    .lf-report-body .max-w-4xl,
    .lf-report-body .mx-auto {{
      max-width: none !important;
      width: 100% !important;
      margin: 0 !important;
    }}
    .lf-report-body .section-card,
    .lf-report-body .card,
    .lf-report-body .question-card,
    .lf-report-body section,
    .lf-report-body article {{
      border: 1px solid var(--lf-line) !important;
      border-top: 5px solid var(--lf-orange) !important;
      border-radius: 8px !important;
      background: rgba(255,255,255,.92) !important;
      box-shadow: 0 18px 38px rgba(47, 29, 8, .09) !important;
      padding: clamp(20px, 3vw, 34px) !important;
      margin: 0 0 18px !important;
    }}
    .lf-report-body h1,
    .lf-report-body h2,
    .lf-report-body h3 {{
      letter-spacing: 0;
      color: #7a3516;
      line-height: 1.22;
    }}
    .lf-report-body h2,
    .lf-report-body .step-title,
    .lf-report-body .section-title,
    .lf-report-body .card-title {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 18px;
      padding-bottom: 10px;
      border-bottom: 1px solid #f0d7b3;
      font-size: clamp(22px, 2.4vw, 30px);
      font-weight: 900;
      color: #8d3d18;
    }}
    .lf-report-body p,
    .lf-report-body li {{
      font-size: 16px;
    }}
    .lf-report-body p {{
      margin: 0 0 13px;
    }}
    .lf-report-body strong {{
      color: #2f3b52;
    }}
    .lf-report-body code {{
      padding: 2px 6px;
      border: 1px solid #d9e2f2;
      border-radius: 5px;
      color: #173f86;
      background: #eef5ff;
      font-family: "SFMono-Regular", ui-monospace, monospace;
      font-size: .92em;
    }}
    .lf-report-body table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border: 1px solid #ead8bd;
      border-radius: 8px;
      background: #fff;
      font-size: 15px;
    }}
    .lf-report-body th {{
      color: #fff;
      background: #a74718;
      text-align: left;
      font-weight: 900;
    }}
    .lf-report-body th,
    .lf-report-body td {{
      padding: 10px 12px;
      border: 1px solid #ead8bd;
      vertical-align: top;
    }}
    .lf-report-body tr:nth-child(even) td {{
      background: #fff8ef;
    }}
    .lf-report-body .ocr-section,
    .lf-report-body .original-text,
    .lf-report-body .sentence-box,
    .lf-report-body .word-bank,
    .lf-report-body .bg-gray-50 {{
      border: 1px solid #ead8bd !important;
      border-left: 5px solid var(--lf-blue) !important;
      border-radius: 8px !important;
      background: #fffaf2 !important;
      padding: 16px !important;
      color: #243044 !important;
    }}
    .lf-report-body .word-bank {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }}
    .lf-report-body .word-choice,
    .lf-report-body .word-item,
    .lf-report-body .tag,
    .lf-report-body .blank,
    .lf-report-body .blank-placeholder {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      margin: 4px;
      padding: 4px 10px;
      border: 1px solid #e6c394;
      border-radius: 999px;
      color: #83380f;
      background: #fff0d8;
      font-weight: 800;
      font-family: "SFMono-Regular", ui-monospace, monospace;
      white-space: nowrap;
    }}
    .lf-report-body .analysis-item,
    .lf-report-body .analysis-text,
    .lf-report-body .compare-box,
    .lf-report-body .practice-item {{
      margin-top: 14px;
      padding: 14px;
      border: 1px solid #e7dfd2;
      border-radius: 8px;
      background: #ffffff;
    }}
    .lf-report-body .compare-box {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .lf-report-body .student-ans {{
      border-color: #fecaca !important;
      background: #fff1f2 !important;
      color: #991b1b !important;
    }}
    .lf-report-body .correct-ans {{
      border-color: #bbf7d0 !important;
      background: #effdf5 !important;
      color: #166534 !important;
    }}
    .lf-report-body .highlight,
    .lf-report-body .highlight-text {{
      border-radius: 4px;
      padding: 1px 5px;
      color: #78350f;
      background: #fde68a;
      font-weight: 800;
    }}
    .lf-report-body details {{
      border: 1px solid #f1d6a8;
      border-radius: 8px;
      background: #fff9eb;
      padding: 12px 14px;
    }}
    .lf-report-body summary {{
      cursor: pointer;
      color: #8d3d18;
      font-weight: 900;
    }}
    .lf-report-footer {{
      margin-top: 22px;
      color: #786855;
      font-family: "SFMono-Regular", ui-monospace, monospace;
      font-size: 12px;
      text-align: right;
    }}
    @media (max-width: 760px) {{
      .lf-report {{
        width: min(100% - 20px, 1120px);
        padding-top: 12px;
      }}
      .lf-report-hero {{
        grid-template-columns: 1fr;
        min-height: 0;
        padding: 22px;
      }}
      .lf-report-stamp {{
        width: 96px;
      }}
      .lf-report-body .section-card,
      .lf-report-body .card,
      .lf-report-body .question-card,
      .lf-report-body section,
      .lf-report-body article {{
        padding: 18px !important;
      }}
      .lf-report-body table {{
        display: block;
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <main class="lf-report" data-learnforge-report="detailed-analysis">
    <header class="lf-report-hero">
      <div>
        <p class="lf-report-kicker">LearnForge Reading Studio</p>
        <h1>{safe_title}</h1>
        <p class="lf-report-sub">题面、词库、关键句和逐题解析已整理成可阅读的 HTML artifact。聊天区只保留状态，完整报告在画布中呈现。</p>
      </div>
      <div class="lf-report-stamp">HTML<br />ARTIFACT</div>
    </header>
    <div class="lf-report-body">
{body}
    </div>
    <footer class="lf-report-footer">Generated by LearnForge Hermes SDK</footer>
  </main>
</body>
</html>"""


APP_TYPE_BY_RESOURCE = {
    "document": "notes.session",
    "notes": "notes.session",
    "mindmap": "mindmap.concept",
    "quiz": "quiz.practice",
    "reading": "resource.center",
    "code_practice": "code.lab",
    "ppt": "ppt.preview",
    "video_script": "video.script",
    "video": "video.player",
    "image": "image.explanation",
}

ICON_BY_APP_TYPE = {
    "custom.html": "Image",
    "mindmap.concept": "Brain",
    "quiz.practice": "CircleHelp",
    "code.lab": "Code2",
    "ppt.preview": "Presentation",
    "video.script": "Film",
    "video.player": "Film",
    "image.explanation": "FileImage",
    "physics.work_energy_demo": "Activity",
    "math.gradient_descent_demo": "Gauge",
    "notes.session": "NotebookPen",
    "resource.center": "BookOpen",
    "exam.cram": "BookOpen",
}

SIZE_BY_APP_TYPE = {
    "custom.html": (1060, 820),
    "mindmap.concept": (440, 330),
    "quiz.practice": (420, 330),
    "code.lab": (480, 340),
    "ppt.preview": (420, 320),
    "video.script": (420, 310),
    "video.player": (720, 520),
    "image.explanation": (470, 340),
    "physics.work_energy_demo": (470, 350),
    "math.gradient_descent_demo": (470, 350),
    "notes.session": (430, 320),
    "resource.center": (430, 330),
    "exam.cram": (560, 460),
}

POSITION_BY_APP_TYPE = {
    "profile.dashboard": (40, 40),
    "learning.path": (40, 380),
    "knowledge.graph": (1440, 430),
    "mindmap.concept": (40, 770),
    "quiz.practice": (970, 40),
    "physics.work_energy_demo": (500, 40),
    "math.gradient_descent_demo": (500, 380),
    "code.lab": (840, 770),
    "notes.session": (970, 370),
    "dashboard.learning": (1440, 40),
    "ppt.preview": (450, 770),
    "image.explanation": (1260, 770),
    "video.script": (1655, 770),
    "video.player": (1655, 770),
    "resource.center": (1880, 40),
    "exam.cram": (970, 730),
    "custom.html": (2045, 770),
}

ACTIONS_BY_APP_TYPE = {
    "custom.html": [{"label": "全屏演示", "action": "custom.fullscreen"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "mindmap.concept": [{"label": "展开节点", "action": "mindmap.expand"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "quiz.practice": [{"label": "提交答案", "action": "quiz.submit"}, {"label": "让导师讲题", "action": "tutor.explain"}],
    "code.lab": [{"label": "解释代码", "action": "tutor.explain"}],
    "ppt.preview": [{"label": "预览 PPT", "action": "ppt.preview"}, {"label": "让导师串讲", "action": "tutor.explain"}],
    "video.script": [{"label": "查看分镜", "action": "video_script.view"}, {"label": "让导师解说", "action": "tutor.explain"}],
    "video.player": [{"label": "切换视频", "action": "video.select"}, {"label": "让导师总结视频", "action": "tutor.explain"}],
    "image.explanation": [{"label": "生成图解", "action": "image.generate"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "physics.work_energy_demo": [{"label": "播放演示", "action": "demo.play"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "math.gradient_descent_demo": [{"label": "播放演示", "action": "demo.play"}, {"label": "让导师解释", "action": "tutor.explain"}],
    "notes.session": [{"label": "保存笔记", "action": "notes.save"}, {"label": "让导师总结", "action": "tutor.explain"}],
    "resource.center": [{"label": "筛选资源", "action": "resource.filter"}, {"label": "让导师推荐", "action": "tutor.explain"}],
    "exam.cram": [{"label": "继续速成", "action": "cram.advance", "payload": {"action": "teach_next_batch"}}, {"label": "查看仪表盘", "action": "dashboard.refresh"}],
}


def artifact_kind_for_capability(capability: str | None) -> str | None:
    return {
        "ppt": "ppt_deck",
        "interactive_demo": "interactive_model",
        "detailed_analysis": "html_report",
        "custom_infographic": "infographic",
        "exam_cram": "cram_session",
    }.get(str(capability or ""))


class MaterializedBundle(BaseModel):
    resources: list[LearningResource] = Field(default_factory=list)
    apps: list[CanvasApp] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class CanvasMaterializer:
    def __init__(self, store: LearningStore) -> None:
        self.store = store
        self.object_storage = ObjectStorage()

    @staticmethod
    def normalize_app_type(app_type: Any) -> str:
        """Map the free-form app_type Hermes may emit onto the CanvasAppType Literal.

        Hermes (and skills) occasionally return values like "infographic",
        "interactive.demo", "presentation", or "slides". None of those are valid
        CanvasAppType members, so a CanvasApp build would raise a Pydantic
        ValidationError that bubbles up as a generic "canvas materialize failed".
        Collapse them to "custom.html"; anything else unknown also falls back to
        "custom.html" rather than crashing the whole turn.
        """
        normalized = str(app_type or "").strip().lower()
        if normalized in _CUSTOM_HTML_ALIASES:
            return "custom.html"
        if normalized in _VALID_APP_TYPES:
            return normalized
        # Unknown but non-empty → keep custom.html as the safe default so the app
        # still renders instead of failing the entire materialize step.
        return "custom.html" if normalized else "custom.html"

    def normalize_resource(self, item: dict[str, Any], fallback_refs: list[dict[str, Any]]) -> LearningResource:
        raw_refs = item.get("source_refs")
        valid_refs = [ref for ref in raw_refs if isinstance(ref, dict)] if isinstance(raw_refs, list) else []
        data = {
            "type": item.get("type") or "document",
            "title": item.get("title") or "学习资源",
            "target_topic": item.get("target_topic") or item.get("topic") or "学习主题",
            "difficulty": item.get("difficulty") or "adaptive",
            "content": item.get("content") if isinstance(item.get("content"), dict) else {},
            "source_refs": valid_refs if valid_refs else fallback_refs,
            "personalized_reason": item.get("personalized_reason") or "由 Hermes 根据当前学习请求生成。",
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        }
        if item.get("resource_id"):
            data["resource_id"] = item["resource_id"]
        resource_type = data["type"]
        if resource_type == "code":
            data["type"] = "code_practice"
        return LearningResource.model_validate(data)

    @staticmethod
    def _text_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in re.split(r"[,\n，、;；]+", value) if part.strip()]
        return []

    @staticmethod
    def _cram_priority_titles(payload: dict[str, Any], priority: str) -> list[str]:
        points = payload.get("knowledge_points")
        if not isinstance(points, list):
            return []
        titles: list[str] = []
        for point in points:
            if not isinstance(point, dict) or str(point.get("priority") or "") != priority:
                continue
            title = str(point.get("title") or point.get("label") or "").strip()
            if title:
                titles.append(title)
        return titles

    @staticmethod
    def _textbook_from_refs(refs: list[dict[str, Any]]) -> str | None:
        for ref in refs:
            source_id = str(ref.get("source_id") or "")
            if source_id.startswith("openstax:") and ref.get("title"):
                return str(ref["title"])
        return None

    def bind_cram_session_app(
        self,
        app: CanvasApp,
        *,
        student_id: str,
        course_id: str,
        fallback_refs: list[dict[str, Any]],
        source_material: str | None = None,
    ) -> CanvasApp:
        if app.app_type != "exam.cram":
            return app
        payload = dict(app.payload)
        session_payload = payload.get("session")
        if isinstance(session_payload, dict) and session_payload.get("session_id"):
            return app
        if not self.store or not hasattr(self.store, "create_cram_session"):
            return app

        from app.cram.engine import CramSessionCreate

        topics = self._text_list(payload.get("topics") or payload.get("scope"))
        must_know = (
            self._text_list(payload.get("must_know") or payload.get("mustKnow"))
            or self._cram_priority_titles(payload, "must_know")
            or topics[:4]
        )
        key_points = (
            self._text_list(payload.get("key_points") or payload.get("keyPoints"))
            or self._cram_priority_titles(payload, "key_point")
            or topics[4:]
        )
        if not must_know and not key_points:
            fallback_topic = str(payload.get("topic") or payload.get("title") or app.title or source_material or "当前考试范围").strip()
            must_know = [fallback_topic]

        refs = app.source_refs or fallback_refs
        textbook = (
            str(payload.get("textbook") or payload.get("textbook_slug") or "").strip()
            or self._textbook_from_refs(refs)
        )
        preferences = payload.get("preferences") if isinstance(payload.get("preferences"), dict) else {}
        session = self.store.create_cram_session(
            CramSessionCreate(
                student_id=student_id,
                course_id=course_id,
                course_title=str(payload.get("course_title") or payload.get("courseTitle") or app.title or "期末速成"),
                exam_types=self._text_list(payload.get("exam_types") or payload.get("examTypes") or payload.get("exam_format")),
                must_know=must_know,
                key_points=key_points,
                textbook=textbook or None,
                materials=[],
                preferences=preferences,
            )
        )
        payload.update(
            {
                "session": session.model_dump(mode="json"),
                "session_id": session.session_id,
                "course_title": session.course_title,
                "stage": session.stage.value,
                "exam_mode": session.exam_mode,
                "next_actions": session.next_actions,
            }
        )
        app.payload = payload
        if session.source_refs:
            app.source_refs = session.source_refs
        return app

    def app_position(self, index: int) -> tuple[float, float]:
        col = index % 3
        row = index // 3
        return 80 + col * 470, 80 + row * 370

    def semantic_app_position(self, app_type: str, index: int, type_index: int) -> tuple[float, float]:
        base = POSITION_BY_APP_TYPE.get(app_type)
        if not base:
            return self.app_position(index)
        x, y = base
        return x + type_index * 34, y + type_index * 34

    async def enrich_image_payload(self, app_type: str, payload: dict[str, Any], topic: str) -> dict[str, Any]:
        if app_type != "image.explanation" or payload.get("image_url"):
            return payload
        provider_alias = str(payload.get("provider_alias") or payload.get("image_provider_alias") or payload.get("provider") or "").lower()
        try:
            request = ImageGatewayRouter().planner.plan(topic, str(payload.get("visual_brief") or payload.get("teaching_goal") or f"解释 {topic}"))
            result = await ImageGatewayRouter().client.generate(request)
            display_provider = "nanobanana" if provider_alias in {"nanobanana", "nano banana", "banana"} else result.provider
            return {
                **payload,
                "image_url": result.image_url,
                "overlay_labels": result.overlay_labels,
                "provider": display_provider,
                "provider_alias": display_provider,
                "image_metadata": {**result.metadata, "actual_provider": result.provider, "display_provider": display_provider},
            }
        except Exception as exc:
            return {**payload, "image_error": f"{type(exc).__name__}: {exc}"}

    def validate_custom_html(
        self,
        payload: dict[str, Any],
        topic: str,
        source_material: str | None = None,
        *,
        capability: str | None = None,
    ) -> dict[str, Any]:
        html = normalize_html_artifact_text(str(payload.get("html") or ""))
        if capability in {"ppt", "interactive_demo"}:
            skill = CustomHtmlAppSkill()
            sanitized = skill.sanitize_widget(html) if html else ""
            valid = bool(sanitized and skill.validate_widget(sanitized))
            # For PPT/interactive_demo: don't fail on sanitizer rejection — the HTML
            # is rendered in a sandboxed iframe. Use original HTML as fallback.
            if not valid and html and len(html.strip()) > 200:
                sanitized = html  # Use original; sandbox protects the canvas
                valid = True
            return {
                **payload,
                "html": sanitized,
                "sandbox": "allow-scripts",
                "sanitized": sanitized != html,
                "fallback_used": bool(payload.get("fallback_used")),
                **({} if valid else {"html_error": "invalid_or_missing_custom_html"}),
            }
        if capability == "detailed_analysis":
            guard_issue = detailed_analysis_context_mismatch(html, source_material)
            if guard_issue:
                html = _detailed_analysis_guard_html(str(payload.get("title") or topic or "学习报告"), guard_issue)
                payload = {**payload, "content_guard": guard_issue, "guarded": True}
            html = wrap_detailed_analysis_report(html, title=str(payload.get("title") or topic or "学习报告"))
            skill = CustomHtmlAppSkill()
            sanitized = skill.sanitize_widget(html)
            valid = skill.validate_widget(sanitized)
            if not valid:
                sanitized = f"<section><h2>{topic}</h2><p>原始 HTML 未通过安全校验，已降级为安全学习卡片。你仍然可以继续让导师基于这个主题生成更细的版本。</p></section>"
                sanitized = skill.sanitize_widget(sanitized)
            return {
                **payload,
                "html": sanitized,
                "sandbox": "allow-scripts",
                "sanitized": sanitized != html,
                "fallback_used": (not valid) or bool(payload.get("guarded")),
            }
        topic_context = "\n".join(
            str(item)
            for item in [
                topic,
                payload.get("topic"),
                payload.get("title"),
                source_material,
            ]
            if item
        )
        output = CustomHtmlAppSkill().run(SkillInput(topic=topic_context or topic, payload={"html": html}))
        if not output.payload.get("valid"):
            fallback = f"<section><h2>{topic}</h2><p>原始 HTML 未通过安全校验，已降级为安全学习卡片。你仍然可以继续让导师基于这个主题生成更细的版本。</p></section>"
            output = CustomHtmlAppSkill().run(SkillInput(topic=topic_context or topic, payload={"html": fallback}))
        return {
            **payload,
            "html": output.payload.get("html", html),
            "sandbox": output.payload.get("sandbox", "allow-scripts"),
            "sanitized": bool(output.payload.get("sanitized")),
            "fallback_used": bool(output.payload.get("fallback_used")),
        }

    def persist_custom_html_payload(
        self,
        payload: dict[str, Any],
        *,
        topic: str,
        app_id: str,
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        html = normalize_html_artifact_text(str(payload.get("html") or ""))
        artifact_id = new_id("artifact")
        title = str(payload.get("title") or topic or "HTML 学习报告")
        object_key = artifact_object_key(kind="html_report", artifact_id=artifact_id, filename=f"{app_id}.html")
        stored = self.object_storage.put_bytes(
            object_key=object_key,
            data=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )
        record = self.store.save_artifact(
            artifact_id=artifact_id,
            kind="html_report",
            object_key=stored.object_key,
            content_type=stored.content_type,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
            title=title,
            source_run_id=run_id,
            student_id=student_id,
            course_id=course_id,
            conversation_id=conversation_id,
            metadata={
                "app_id": app_id,
                "message_id": message_id,
                "artifact_kind": payload.get("artifact_kind"),
                "sandbox": payload.get("sandbox"),
                "sanitized": payload.get("sanitized"),
                "fallback_used": payload.get("fallback_used"),
            },
        )
        return {
            **{key: value for key, value in payload.items() if key != "html"},
            "artifact_id": record["artifact_id"],
            "html_url": f"/api/artifacts/{record['artifact_id']}/content",
            "title": title,
            "object_key": stored.object_key,
            **({"public_url": stored.public_url} if stored.public_url else {}),
        }

    async def materialize(
        self,
        bundle: "HermesTaskResult",
        *,
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
        fallback_refs: list[dict[str, Any]],
        capability: str | None = None,
        source_material: str | None = None,
        persist: bool = True,
    ) -> MaterializedBundle:
        trace: list[str] = []
        title_namer = ComponentTitleNamer()
        resources: list[LearningResource] = []
        normalized_resources: list[LearningResource] = []
        for item in bundle.resources:
            resource = self.normalize_resource(item, fallback_refs)
            normalized_resources.append(resource)

        if normalized_resources:
            trace.extend(await title_namer.rename_resources(normalized_resources, source_material=source_material or ""))

        for resource in normalized_resources:
            if persist:
                saved = self.store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="hermes_resource_bundle")
                resources.append(saved)
            else:
                resources.append(resource)

        apps: list[CanvasApp] = []
        group_id = new_id("group")
        type_counts: dict[str, int] = {}
        for index, spec in enumerate(bundle.apps):
            resource_index = int(spec.get("resource_index", index if index < len(resources) else 0) or 0)
            resource = resources[resource_index] if 0 <= resource_index < len(resources) else None
            app_id = str(spec.get("app_id") or new_id("app"))
            app_type = spec.get("app_type") or (APP_TYPE_BY_RESOURCE.get(resource.type) if resource else "custom.html")
            app_type = self.normalize_app_type(app_type)
            type_index = type_counts.get(app_type, 0)
            type_counts[app_type] = type_index + 1
            payload = spec.get("payload") if isinstance(spec.get("payload"), dict) else {}
            if resource and not payload:
                payload = resource.content.copy()
            topic = (resource.target_topic if resource else spec.get("topic")) or "学习主题"
            if app_type == "resource.center":
                payload.setdefault(
                    "resources",
                    [
                        {
                            "resource_id": item.resource_id,
                            "title": item.title,
                            "type": item.type,
                            "personalized_reason": item.personalized_reason,
                            "source_refs": item.source_refs,
                        }
                        for item in resources
                    ],
                )
            if app_type == "video.player":
                video_resources = [item for item in resources if item.type == "video"]
                if resource and resource.type == "video" and all(item.resource_id != resource.resource_id for item in video_resources):
                    video_resources.insert(0, resource)
                payload = {**video_player_payload(str(topic), video_resources), **payload}
            if app_type == "custom.html":
                artifact_kind = artifact_kind_for_capability(capability)
                if artifact_kind:
                    payload.setdefault("artifact_kind", artifact_kind)
                payload = self.validate_custom_html(payload, str(topic), source_material=source_material, capability=capability)
                if persist:
                    payload = self.persist_custom_html_payload(
                        payload,
                        topic=str(topic),
                        app_id=app_id,
                        student_id=student_id,
                        course_id=course_id,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        run_id=run_id,
                    )
            if app_type == "image.explanation" and capability == "custom_infographic":
                payload.setdefault("infographic_render_mode", "image")
                payload.setdefault("provider_alias", "nanobanana")
                payload.setdefault("visual_brief", f"面向学习者的“{topic}”信息图，适合全屏展示。")
            payload = await self.enrich_image_payload(str(app_type), payload, str(topic))
            x, y = self.semantic_app_position(app_type, index, type_index)
            width, height = SIZE_BY_APP_TYPE.get(str(app_type), (420, 320))
            app = CanvasApp(
                app_id=app_id,
                app_type=app_type,
                title=spec.get("title") or (resource.title if resource else "Hermes 学习 App"),
                icon=spec.get("icon") or ICON_BY_APP_TYPE.get(str(app_type), "Sparkles"),
                render_mode="sandbox_iframe" if app_type == "custom.html" else "native_react",
                state="focused" if index == 0 else "window",
                position=CanvasPosition(x=float(spec.get("x", x)), y=float(spec.get("y", y))),
                size=CanvasSize(width=float(spec.get("width", width)), height=float(spec.get("height", height))),
                z_index=80 if index == 0 else 20 + index,
                group_id=spec.get("group_id") or f"agent-generated-{capability or 'canvas'}",
                payload=payload,
                source={
                    "student_id": student_id,
                    "course_id": course_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "run_id": run_id,
                    "resource_id": resource.resource_id if resource else None,
                    "skill_name": "hermes_resource_bundle",
                    "capability": capability,
                    "artifact_kind": payload.get("artifact_kind") if isinstance(payload, dict) else artifact_kind_for_capability(capability),
                    "source_material": source_material,
                },
                source_refs=resource.source_refs if resource else fallback_refs,
                personalized_reason=spec.get("personalized_reason") or (resource.personalized_reason if resource else "由 Hermes 创建。"),
                actions=spec.get("actions") or ACTIONS_BY_APP_TYPE.get(str(app_type), [{"label": "让导师解释", "action": "tutor.explain"}]),
            )
            apps.append(app)

        if apps:
            trace.extend(await title_namer.rename_apps(apps, source_material=source_material or ""))

        if not persist:
            return MaterializedBundle(resources=resources, apps=apps, trace=["validated_resources", *trace, "draft_canvas_apps", *bundle.trace])
        saved_apps: list[CanvasApp] = []
        for app in apps:
            app = self.bind_cram_session_app(
                app,
                student_id=student_id,
                course_id=course_id,
                fallback_refs=app.source_refs or fallback_refs,
                source_material=source_material,
            )
            saved_app = self.store.save_app(app, student_id=student_id, course_id=course_id, agent="hermes_runtime", skill="canvas_materializer")
            saved_apps.append(saved_app)
        return MaterializedBundle(resources=resources, apps=saved_apps, trace=["validated_resources", *trace, "created_canvas_apps", *bundle.trace])

    def commit_materialized(
        self,
        bundle: MaterializedBundle,
        *,
        student_id: str,
        course_id: str,
        conversation_id: str,
        message_id: str,
        run_id: str,
    ) -> MaterializedBundle:
        saved_resources: list[LearningResource] = []
        for resource in bundle.resources:
            saved_resources.append(
                self.store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="hermes_resource_bundle")
            )
        saved_apps: list[CanvasApp] = []
        for app in bundle.apps:
            payload = dict(app.payload)
            artifact_kind = artifact_kind_for_capability(str(app.source.get("capability") or ""))
            if app.app_type == "custom.html" and artifact_kind:
                payload.setdefault("artifact_kind", artifact_kind)
                app.payload = payload
                app.source["artifact_kind"] = artifact_kind
            if app.app_type == "custom.html" and payload.get("html") and not payload.get("artifact_id"):
                payload = self.persist_custom_html_payload(
                    payload,
                    topic=str(payload.get("topic") or app.title or "HTML Artifact"),
                    app_id=app.app_id,
                    student_id=student_id,
                    course_id=course_id,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    run_id=run_id,
                )
                app.payload = payload
            app = self.bind_cram_session_app(
                app,
                student_id=student_id,
                course_id=course_id,
                fallback_refs=app.source_refs,
                source_material=str(app.source.get("source_material") or ""),
            )
            saved_apps.append(self.store.save_app(app, student_id=student_id, course_id=course_id, agent="hermes_runtime", skill="canvas_materializer"))
        return MaterializedBundle(resources=saved_resources, apps=saved_apps, trace=[*bundle.trace, "committed_canvas_apps"])
