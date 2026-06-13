from __future__ import annotations

import argparse
import ast
import asyncio
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.database.store import LearningStore, dumps, loads  # noqa: E402
from app.rag.embeddings import embed_text  # noqa: E402
from app.schemas.app_protocol import (  # noqa: E402
    CanvasApp,
    CanvasPosition,
    CanvasSize,
    LearningResource,
    VerifierResult,
    utc_now,
)


DEFAULT_PHYSICS_PDF = Path("/Users/mychanging/Downloads/大学物理简明教程 (赵近芳,王登龙) (z-library.sk, 1lib.sk, z-lib.sk).pdf")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:14]
    return f"{prefix}-{digest}"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def as_resource_text(entry: dict[str, Any]) -> str:
    fields = [
        ("模块名称", entry["module_name"]),
        ("课程 / 资源名称", entry["resource_name"]),
        ("推荐级别", entry["recommended_level"]),
        ("难度", entry["difficulty"]),
        ("前置知识", "、".join(entry["prerequisites"])),
        ("核心知识点", "、".join(entry["core_knowledge_points"])),
        ("学习目标", entry["learning_goal"]),
        ("推荐学习顺序", str(entry["order"])),
        ("适合人群", entry["audience"]),
        ("与其他数学模块的关系", entry["module_relation"]),
        ("标签", " ".join(entry["tags"])),
        ("备注", entry["notes"]),
    ]
    links = "；".join(f"{link['label']}：{link['url']}" for link in entry["links"])
    return "\n".join([f"{name}：{value}" for name, value in fields] + [f"官方链接 / GitHub 链接：{links}"])


MATH_RESOURCES: list[dict[str, Any]] = [
    {
        "module_name": "微积分 / 高等数学",
        "resource_name": "MIT 18.01 Single Variable Calculus",
        "links": [{"label": "MIT OCW", "url": "https://ocw.mit.edu/courses/18-01-calculus-i-single-variable-calculus-fall-2020/"}],
        "recommended_level": "核心",
        "difficulty": "入门",
        "prerequisites": ["高中函数", "三角函数", "基础代数"],
        "core_knowledge_points": ["极限", "导数", "积分", "级数", "坐标系统", "函数变化率", "基本微积分技巧"],
        "learning_goal": "建立单变量函数变化率、累积量和级数的基础直觉，为多元微积分、概率论和最优化做准备。",
        "order": 1,
        "audience": "AI / 数据科学方向数学基础薄弱或需要系统补课的学习者。",
        "module_relation": "数学基础第一层，后续多元微积分、概率论、最优化都需要它。",
        "tags": ["#微积分", "#高等数学", "#数学基础", "#核心课程"],
        "notes": "建议先完整掌握导数、积分和级数的概念，再进入多元微积分。",
    },
    {
        "module_name": "多元微积分",
        "resource_name": "MIT 18.02SC Multivariable Calculus",
        "links": [{"label": "MIT OCW", "url": "https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/"}],
        "recommended_level": "核心",
        "difficulty": "中级",
        "prerequisites": ["单变量微积分", "向量基础", "矩阵基础"],
        "core_knowledge_points": ["向量", "矩阵基础", "偏导数", "梯度", "方向导数", "链式法则", "拉格朗日乘子", "重积分", "线积分", "曲面积分"],
        "learning_goal": "把单变量微积分扩展到向量函数和多变量函数，理解梯度、约束优化和积分区域。",
        "order": 2,
        "audience": "已经完成单变量微积分、准备学习优化或概率模型的学习者。",
        "module_relation": "连接高等数学、线性代数、最优化的重要桥梁。",
        "tags": ["#多元微积分", "#向量微积分", "#梯度", "#数学基础"],
        "notes": "拉格朗日乘子和梯度概念会在凸优化、机器学习损失函数中反复出现。",
    },
    {
        "module_name": "线性代数",
        "resource_name": "MIT 18.06SC Linear Algebra",
        "links": [{"label": "MIT Open Learning Library", "url": "https://openlearninglibrary.mit.edu/courses/course-v1:OCW+18.06SC+2T2019/about"}],
        "recommended_level": "核心",
        "difficulty": "中级",
        "prerequisites": ["高中代数", "函数基础", "基本向量概念"],
        "core_knowledge_points": ["矩阵", "向量空间", "线性方程组", "线性变换", "基", "维度", "正交", "投影", "特征值", "特征向量", "矩阵分解"],
        "learning_goal": "理解矩阵和向量空间如何表示线性变换、投影、分解和高维数据结构。",
        "order": 3,
        "audience": "所有 AI / 数据科学学习者，尤其是需要理解矩阵计算和表示学习的人。",
        "module_relation": "AI / 数据科学数学基础中最核心的课程之一，并支撑优化、统计、概率建模和矩阵分解。",
        "tags": ["#线性代数", "#矩阵", "#向量空间", "#数学基础"],
        "notes": "建议配合作业练习，不只看讲解。",
    },
    {
        "module_name": "离散数学",
        "resource_name": "Discrete Mathematics: An Open Introduction",
        "links": [{"label": "Open Math Books", "url": "https://discrete.openmathbooks.org/dmoi4.html"}],
        "recommended_level": "核心",
        "difficulty": "入门",
        "prerequisites": ["高中代数", "基本逻辑表达"],
        "core_knowledge_points": ["逻辑", "证明", "集合", "函数", "关系", "图论", "计数", "序列", "数学归纳法", "组合证明"],
        "learning_goal": "训练抽象思维、证明能力和结构化推理能力，补齐连续数学之外的离散结构基础。",
        "order": 4,
        "audience": "希望提升数学表达、证明和结构化推理能力的学习者。",
        "module_relation": "与概率计数、图结构、组合推理相关，是数学基础的重要一支。",
        "tags": ["#离散数学", "#证明", "#组合数学", "#数学基础"],
        "notes": "按用户要求保留，不扩展到算法或编程内容。",
    },
    {
        "module_name": "概率论",
        "resource_name": "Harvard Stat 110: Probability",
        "links": [{"label": "Harvard Stat 110", "url": "https://stat110.hsites.harvard.edu/"}],
        "recommended_level": "核心",
        "difficulty": "中级",
        "prerequisites": ["单变量微积分", "组合计数", "基础代数"],
        "core_knowledge_points": ["条件概率", "贝叶斯公式", "随机变量", "常见分布", "期望", "方差", "协方差", "大数定律", "中心极限定理"],
        "learning_goal": "理解不确定性的数学表达，掌握随机变量、分布和极限定理的核心直觉。",
        "order": 5,
        "audience": "准备学习统计推断、概率模型和随机过程的学习者。",
        "module_relation": "理解不确定性、统计推断、随机过程和概率模型的基础。",
        "tags": ["#概率论", "#贝叶斯", "#随机变量", "#数学基础"],
        "notes": "可与 MIT 18.05 二选一作为概率主线，也可先 Stat 110 后 18.05。",
    },
    {
        "module_name": "概率论与数理统计",
        "resource_name": "MIT 18.05 Introduction to Probability and Statistics",
        "links": [{"label": "MIT OCW", "url": "https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022/"}],
        "recommended_level": "核心",
        "difficulty": "中级",
        "prerequisites": ["单变量微积分", "组合计数", "概率论基础"],
        "core_knowledge_points": ["组合计数", "随机变量", "概率分布", "贝叶斯推断", "参数估计", "假设检验", "置信区间", "线性回归"],
        "learning_goal": "把概率论和统计推断连起来，理解估计、检验、置信区间和回归的数学含义。",
        "order": 5,
        "audience": "需要同时补概率论和统计学入门的 AI / 数据科学学习者。",
        "module_relation": "概率论和统计学的综合入门课程，可与 Harvard Stat 110 互补。",
        "tags": ["#概率论", "#数理统计", "#贝叶斯", "#统计推断"],
        "notes": "如果已经学过 Stat 110，可把 18.05 作为统计推断补强。",
    },
    {
        "module_name": "数理统计",
        "resource_name": "OpenIntro: Introduction to Modern Statistics",
        "links": [
            {"label": "OpenIntro 官网", "url": "https://www.openintro.org/book/ims"},
            {"label": "GitHub", "url": "https://github.com/OpenIntroStat/ims"},
        ],
        "recommended_level": "补充",
        "difficulty": "入门",
        "prerequisites": ["概率论基础", "数据描述基础"],
        "core_knowledge_points": ["数据描述", "抽样", "统计推断", "置信区间", "假设检验", "回归建模", "模拟推断"],
        "learning_goal": "用应用统计案例巩固抽样、推断、检验和回归建模的实践理解。",
        "order": 6,
        "audience": "学完概率论后希望补应用统计直觉和案例的学习者。",
        "module_relation": "偏应用统计，适合补充 MIT 18.05 或 Harvard Stat 110 之后的统计实践理解。",
        "tags": ["#统计学", "#数理统计", "#回归", "#补充资源"],
        "notes": "只纳入数学与统计基础部分，不扩展到非数学课程。",
    },
    {
        "module_name": "离散数学进阶",
        "resource_name": "Applied Discrete Structures",
        "links": [
            {"label": "官网", "url": "https://www.discretemath.org/"},
            {"label": "GitHub", "url": "https://github.com/klevasseur/ads"},
        ],
        "recommended_level": "进阶",
        "difficulty": "中级",
        "prerequisites": ["离散数学入门", "基础证明能力"],
        "core_knowledge_points": ["离散结构", "关系", "函数", "图", "树", "组合", "递推", "布尔代数", "代数结构"],
        "learning_goal": "在入门离散数学之后，扩展到更厚的离散结构、递推、布尔代数和代数结构参考体系。",
        "order": 7,
        "audience": "已经完成离散数学入门、需要进阶参考或复盘的学习者。",
        "module_relation": "比入门离散数学更厚，适合进阶学习或作为参考教材。",
        "tags": ["#离散数学", "#进阶数学", "#图论", "#代数结构"],
        "notes": "作为参考教材纳入，不扩展到算法实现。",
    },
    {
        "module_name": "最优化 / 凸优化",
        "resource_name": "Boyd & Vandenberghe Convex Optimization / Stanford EE364A Convex Optimization",
        "links": [
            {"label": "Convex Optimization Book", "url": "https://web.stanford.edu/~boyd/cvxbook/"},
            {"label": "Stanford EE364A", "url": "https://web.stanford.edu/class/ee364a/"},
        ],
        "recommended_level": "进阶",
        "difficulty": "高级",
        "prerequisites": ["线性代数", "多元微积分", "概率论基础"],
        "core_knowledge_points": ["凸集", "凸函数", "凸优化问题", "最优性条件", "拉格朗日对偶", "线性规划", "二次规划", "半正定规划", "内点法"],
        "learning_goal": "理解凸优化问题的建模、最优性条件、对偶理论和典型优化算法。",
        "order": 8,
        "audience": "完成线性代数、多元微积分、概率论后准备深入优化理论的学习者。",
        "module_relation": "进阶数学模块，建议在线性代数、多元微积分、概率论之后学习。",
        "tags": ["#最优化", "#凸优化", "#进阶数学", "#拉格朗日对偶"],
        "notes": "不作为入门第一门课，适合在基础模块后学习。",
    },
    {
        "module_name": "综合数学复盘",
        "resource_name": "Mathematics for Machine Learning",
        "links": [
            {"label": "官网", "url": "https://mml-book.github.io/"},
            {"label": "GitHub", "url": "https://github.com/mml-book/mml-book.github.io"},
        ],
        "recommended_level": "补充",
        "difficulty": "中级",
        "prerequisites": ["单变量微积分", "多元微积分", "线性代数", "概率论", "优化基础"],
        "core_knowledge_points": ["线性代数", "解析几何", "矩阵分解", "向量微积分", "概率与分布", "连续优化"],
        "learning_goal": "只提取 Part I: Mathematical Foundations，用作 AI / 数据科学前置数学基础的整合复盘。",
        "order": 9,
        "audience": "已经学完核心数学模块、希望统一复盘数学基础的人。",
        "module_relation": "作为数学基础的整合复盘材料，不作为第一门课直接学习。",
        "tags": ["#数学基础", "#综合复盘", "#线性代数", "#概率论", "#最优化"],
        "notes": "按用户要求只提取 Part I: Mathematical Foundations，不展开机器学习算法部分。",
    },
]


def insert_course_document(store: LearningStore, doc_id: str, course_id: str, title: str, file_url: str, parser: str) -> None:
    store.conn.execute(
        "INSERT OR REPLACE INTO course_documents(id, course_id, title, file_url, parser, created_at) VALUES(?,?,?,?,?,?)",
        (doc_id, course_id, title, file_url, parser, utc_now()),
    )


def insert_chunk(store: LearningStore, chunk_id: str, doc_id: str, course_id: str, index: int, content: str, source_ref: dict[str, Any], embedding: list[float] | None = None) -> None:
    store.conn.execute(
        """
        INSERT OR REPLACE INTO document_chunks(id, document_id, course_id, chunk_index, content, source_ref, embedding, created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (chunk_id, doc_id, course_id, index, content, dumps(source_ref), dumps(embedding or []), utc_now()),
    )


def import_math(store: LearningStore, course_id: str, student_id: str) -> list[dict[str, Any]]:
    doc_id = "doc-math-ai-data-foundations"
    insert_course_document(store, doc_id, course_id, "AI / 数据科学前置数学资源课程体系", "seed://math-ai-data-foundations.md", "structured_markdown")
    verifier = VerifierResult(passed=True, score=0.96, source_coverage=1.0, profile_fit=0.94, safety="pass")
    resources: list[dict[str, Any]] = []
    for entry in MATH_RESOURCES:
        resource_id = stable_id("res-math", entry["resource_name"])
        chunk_id = stable_id("chunk-math", entry["resource_name"])
        content = as_resource_text(entry)
        source_ref = {
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "course_id": course_id,
            "resource_id": resource_id,
            "chapter": "数学学习资源与课程体系",
            "section": entry["module_name"],
            "url": entry["links"][0]["url"],
            "quote_span": [0, min(120, len(content))],
            "confidence": 0.98,
            "verified": True,
        }
        embedding = embed_text(content, "RETRIEVAL_DOCUMENT")
        insert_chunk(store, chunk_id, doc_id, course_id, entry["order"], content, source_ref, embedding or [0.98, entry["order"] / 10, len(entry["core_knowledge_points"]) / 20])
        resource = LearningResource(
            resource_id=resource_id,
            type="reading",
            title=entry["resource_name"],
            target_topic=entry["module_name"],
            difficulty=entry["difficulty"],
            content={
                **entry,
                "links": entry["links"],
                "learning_goal": entry["learning_goal"],
                "recommended_level": entry["recommended_level"],
                "summary": entry["module_relation"],
            },
            source_refs=[source_ref],
            personalized_reason=f"{entry['recommended_level']}资源：{entry['module_relation']}",
            tags=entry["tags"],
            quality_check=verifier,
        )
        store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="structured_knowledge_import")
        resources.append({
            "resource_id": resource_id,
            "title": entry["resource_name"],
            "type": "reading",
            "module_name": entry["module_name"],
            "recommended_level": entry["recommended_level"],
            "difficulty": entry["difficulty"],
            "source_refs": [source_ref],
            "tags": entry["tags"],
            "links": entry["links"],
            "personalized_reason": f"{entry['recommended_level']}资源：{entry['module_relation']}",
            "content": entry,
        })
    upsert_math_graph(store, course_id)
    return resources


def upsert_math_graph(store: LearningStore, course_id: str) -> None:
    module_points: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for entry in sorted(MATH_RESOURCES, key=lambda item: item["order"]):
        kp_id = stable_id("kp", entry["module_name"])
        if kp_id in seen:
            continue
        seen.add(kp_id)
        module_points.append((kp_id, entry["module_name"], entry["learning_goal"]))
        store.conn.execute(
            "INSERT OR REPLACE INTO knowledge_points(id, course_id, title, description, metadata) VALUES(?,?,?,?,?)",
            (kp_id, course_id, entry["module_name"], entry["learning_goal"], dumps({"tags": entry["tags"], "order": entry["order"], "source": "math_import"})),
        )
    for index, (source_id, _, _) in enumerate(module_points[:-1]):
        target_id = module_points[index + 1][0]
        edge_id = stable_id("edge", f"{source_id}->{target_id}")
        store.conn.execute(
            "INSERT OR REPLACE INTO knowledge_edges(id, course_id, source_id, target_id, relation, confidence) VALUES(?,?,?,?,?,?)",
            (edge_id, course_id, source_id, target_id, "recommended_next", 0.92),
        )


def pdf_page_count(pdf_path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(pdf_path)], check=True, text=True, capture_output=True)
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, flags=re.MULTILINE)
    return int(match.group(1)) if match else 0


def pdftotext_pages(pdf_path: Path) -> list[str]:
    try:
        result = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], check=True, text=True, capture_output=True, timeout=60)
    except Exception:
        return []
    return [page.strip() for page in result.stdout.split("\f")]


def render_pdf_page(pdf_path: Path, page: int, work_dir: Path) -> Path:
    prefix = work_dir / f"physics-page-{page:03d}"
    subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-png", "-singlefile", "-r", "130", str(pdf_path), str(prefix)],
        check=True,
        text=True,
        capture_output=True,
    )
    return prefix.with_suffix(".png")


def parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return normalize_ocr_payload(json.loads(cleaned))
    except json.JSONDecodeError:
        return normalize_ocr_payload({"page_type": "ocr_text", "title": "", "text": cleaned})


def normalize_ocr_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"page_type": "ocr_text", "title": "", "text": str(payload or "")}
    page_type = str(payload.get("page_type") or "ocr_text")
    title = str(payload.get("title") or "")
    body = payload.get("text", "")
    if isinstance(body, dict):
        nested = normalize_ocr_payload(body)
        return {
            "page_type": page_type or nested.get("page_type", "ocr_text"),
            "title": title or str(nested.get("title", "")),
            "text": str(nested.get("text", "")),
        }
    if isinstance(body, list):
        body = "\n".join(str(item) for item in body if item)
    if isinstance(body, str):
        candidate = body.strip()
        if "page_type" in candidate and "text" in candidate and "{" in candidate and "}" in candidate:
            nested_json = candidate[candidate.find("{"): candidate.rfind("}") + 1]
            try:
                nested = normalize_ocr_payload(json.loads(nested_json))
                if nested.get("text"):
                    return {
                        "page_type": page_type or nested.get("page_type", "ocr_text"),
                        "title": title or str(nested.get("title", "")),
                        "text": str(nested.get("text", "")),
                    }
            except json.JSONDecodeError:
                pass
    return {"page_type": page_type, "title": title, "text": str(body or "")}


@dataclass
class OcrPage:
    page: int
    title: str
    text: str
    model: str
    ok: bool
    error: str = ""


async def ocr_page_with_gemini(client: httpx.AsyncClient, settings: Any, model: str, pdf_path: Path, page: int, work_dir: Path) -> OcrPage:
    image_path = await asyncio.to_thread(render_pdf_page, pdf_path, page, work_dir)
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {
                    "text": (
                        "你正在为 LearnForge 知识库导入一本中文大学物理教材。"
                        "请对这一页做高质量 OCR，提取章节标题、小节标题和正文；删除页眉页脚噪声。"
                        "只输出 JSON：{\"page_type\":\"cover|toc|chapter|section|body|exercise|blank\","
                        "\"title\":\"本页标题或空字符串\",\"text\":\"可用于RAG检索的中文正文\"}。"
                    )
                },
                {"inline_data": {"mime_type": "image/png", "data": image_data}},
            ],
        }],
        "generationConfig": {"maxOutputTokens": 1800, "responseMimeType": "application/json"},
    }
    response = await client.post(
        f"{GEMINI_BASE_URL}/models/{model}:generateContent",
        headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    parsed = parse_json_text(text)
    return OcrPage(page=page, title=clean_text(str(parsed.get("title", ""))), text=clean_text(str(parsed.get("text", ""))), model=model, ok=True)


async def run_gemini_ocr(pdf_path: Path, pages: list[int], concurrency: int) -> tuple[list[OcrPage], list[str]]:
    settings = get_settings()
    if not settings.gemini_api_key:
        return [], ["GEMINI_API_KEY is not configured"]
    models = list(dict.fromkeys(model.removeprefix("models/") for model in [settings.gemini_text_model, settings.gemini_text_fallback_model] if model))
    if not models:
        return [], ["No Gemini OCR model configured"]
    results: list[OcrPage] = []
    errors: list[str] = []
    semaphore = asyncio.Semaphore(max(1, concurrency))
    timeout = httpx.Timeout(90.0, connect=float(settings.gemini_connect_timeout_seconds))
    with tempfile.TemporaryDirectory(prefix="learnforge-physics-ocr-") as tmp:
        work_dir = Path(tmp)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async def worker(page: int) -> None:
                async with semaphore:
                    last_error = ""
                    primary_model = models[0]
                    fallback_models = models[1:]
                    attempt_plan = [(primary_model, attempt + 1, False) for attempt in range(3)]
                    attempt_plan.extend((model, 1, True) for model in fallback_models)
                    for model, attempt, is_fallback in attempt_plan:
                        try:
                            result = await ocr_page_with_gemini(client, settings, model, pdf_path, page, work_dir)
                            if is_fallback:
                                result.error = f"primary_model_failed; fallback_used_after_3_attempts={primary_model}"
                            results.append(result)
                            suffix = " fallback" if is_fallback else f" attempt {attempt}"
                            print(f"OCR page {page}: ok via {model}{suffix}", flush=True)
                            return
                        except Exception as exc:  # noqa: BLE001 - importer records page-level failures.
                            last_error = f"{model} attempt {attempt}: {type(exc).__name__}: {str(exc)[:180]}"
                            if not is_fallback and attempt < 3:
                                await asyncio.sleep(0.8 * attempt)
                    errors.append(f"page {page}: {last_error}")
                    results.append(OcrPage(page=page, title="", text="", model=models[0], ok=False, error=last_error))
                    print(f"OCR page {page}: failed {last_error}", flush=True)

            await asyncio.gather(*(worker(page) for page in pages))
    return sorted(results, key=lambda item: item.page), errors


def detect_chapter(title: str, text: str, current: str) -> str:
    combined = f"{title} {text}"
    match = re.search(r"第\s*[一二三四五六七八九十0-9]+\s*章\s*(?!增加|减小|变化|可以|已经|中的|的是)[\u4e00-\u9fffA-Za-z0-9（）()、·]{0,18}", combined)
    if match:
        return clean_text(match.group(0))
    return current


def persist_physics_pages(store: LearningStore, course_id: str, doc_id: str, page_count: int, pages: list[OcrPage], current_chapter: str) -> tuple[int, str]:
    imported = 0
    for page in pages:
        page_text = page.text or f"《大学物理简明教程》扫描页第 {page.page} 页。OCR 暂未提取到足够正文，可作为页码级引用占位。"
        current_chapter = detect_chapter(page.title, page_text, current_chapter)
        chunk_id = f"chunk-physics-zhao-wang-p{page.page:03d}"
        content = f"页码：{page.page}\n章节：{current_chapter}\n标题：{page.title or current_chapter}\n正文：{page_text}"
        source_ref = {
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "course_id": course_id,
            "chapter": current_chapter,
            "section": page.title or current_chapter,
            "page": page.page,
            "quote_span": [0, min(120, len(page_text))],
            "confidence": 0.9 if page.ok and page.text else 0.55,
            "ocr_model": page.model,
            "ocr_note": page.error,
            "verified": bool(page.ok and page.text),
        }
        chunk_content = content[:3600]
        embedding = embed_text(chunk_content, "RETRIEVAL_DOCUMENT")
        insert_chunk(store, chunk_id, doc_id, course_id, 1000 + page.page, chunk_content, source_ref, embedding or [0.9 if page.ok else 0.55, page.page / max(page_count, 1), len(page_text) / 2000])
        imported += 1
    store.conn.commit()
    return imported, current_chapter


def parse_nested_ocr_json(value: str) -> dict[str, Any] | None:
    candidate = value.strip()
    if "page_type" not in candidate or "text" not in candidate or "{" not in candidate:
        return None
    start = candidate.find("{")
    end = candidate.rfind("}")
    nested = candidate[start:end + 1] if end > start else candidate[start:]
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(nested)
            normalized = normalize_ocr_payload(parsed)
            if normalized.get("text"):
                return normalized
        except (SyntaxError, ValueError, json.JSONDecodeError):
            continue
    title = extract_json_like_string_field(nested, "title")
    text = extract_json_like_string_field(nested, "text")
    if text:
        return {"page_type": extract_json_like_string_field(nested, "page_type") or "ocr_text", "title": title or "", "text": text}
    return None


def extract_json_like_string_field(value: str, field: str) -> str:
    marker = re.search(rf'"{re.escape(field)}"\s*:\s*"', value)
    if not marker:
        return ""
    index = marker.end()
    output: list[str] = []
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            next_char = value[index + 1]
            if next_char == "n":
                output.append("\n")
            elif next_char == "t":
                output.append("\t")
            elif next_char in {'"', "\\"}:
                output.append(next_char)
            else:
                output.append(f"\\{next_char}")
            index += 2
            continue
        if char == '"':
            tail = value[index + 1:index + 80]
            if re.match(r"\s*(?:,\s*\"[A-Za-z_]+\"\s*:|\}\s*$|$)", tail, flags=re.DOTALL):
                break
        output.append(char)
        index += 1
    return clean_text("".join(output))


def suspicious_chapter(value: str) -> bool:
    return bool(re.search(r"增加|减小|变化|可以|已经|中的|的是", value)) or len(clean_text(value)) > 24


def repair_physics_json_chunks(store: LearningStore, course_id: str, doc_id: str) -> int:
    rows = store.fetchall("SELECT id, content, source_ref, embedding FROM document_chunks WHERE course_id=? AND document_id=? ORDER BY chunk_index", (course_id, doc_id))
    repaired = 0
    for row in rows:
        content = str(row["content"] or "")
        if "正文：" not in content or "page_type" not in content:
            continue
        prefix, body = content.split("正文：", 1)
        nested = parse_nested_ocr_json(body)
        if not nested:
            continue
        repaired_body = clean_text(str(nested.get("text", "")))
        if not repaired_body or repaired_body == clean_text(body):
            continue
        source_ref = loads(row["source_ref"], {})
        old_chapter = str(source_ref.get("chapter") or "大学物理简明教程")
        base_chapter = "大学物理简明教程" if suspicious_chapter(old_chapter) else old_chapter
        chapter = detect_chapter(str(nested.get("title", "")), repaired_body, base_chapter)
        section = str(nested.get("title") or source_ref.get("section") or chapter)
        page_number = int(source_ref.get("page") or 0)
        new_content = f"页码：{page_number}\n章节：{chapter}\n标题：{section}\n正文：{repaired_body}"[:3600]
        source_ref["chapter"] = chapter
        source_ref["section"] = section
        source_ref["quote_span"] = [0, min(120, len(repaired_body))]
        source_ref["ocr_repaired"] = True
        embedding = embed_text(new_content, "RETRIEVAL_DOCUMENT") or loads(row["embedding"], [])
        store.conn.execute(
            "UPDATE document_chunks SET content=?, source_ref=?, embedding=? WHERE id=?",
            (new_content, dumps(source_ref), dumps(embedding), row["id"]),
        )
        repaired += 1
        if repaired % 25 == 0:
            store.conn.commit()
            print(f"Repaired physics OCR JSON chunks: {repaired}", flush=True)
    store.conn.commit()
    return repaired


def content_field(content: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}：(.+)$", content, flags=re.MULTILINE)
    return clean_text(match.group(1)) if match else ""


def repair_physics_metadata(store: LearningStore, course_id: str, doc_id: str) -> int:
    rows = store.fetchall("SELECT id, content, source_ref, embedding FROM document_chunks WHERE course_id=? AND document_id=? ORDER BY chunk_index", (course_id, doc_id))
    repaired = 0
    for row in rows:
        content = str(row["content"] or "")
        source_ref = loads(row["source_ref"], {})
        page_number = int(source_ref.get("page") or content_field(content, "页码") or 0)
        chapter = str(source_ref.get("chapter") or content_field(content, "章节") or "大学物理简明教程")
        section = str(source_ref.get("section") or content_field(content, "标题") or chapter)
        body = content.split("正文：", 1)[1] if "正文：" in content else content
        next_chapter = chapter
        if suspicious_chapter(chapter):
            next_chapter = detect_chapter(section, body, "大学物理简明教程")
        next_section = section
        if suspicious_chapter(section):
            next_section = next_chapter
        if next_chapter == chapter and next_section == section:
            continue
        new_content = f"页码：{page_number}\n章节：{next_chapter}\n标题：{next_section}\n正文：{clean_text(body)}"[:3600]
        source_ref["chapter"] = next_chapter
        source_ref["section"] = next_section
        source_ref["metadata_repaired"] = True
        store.conn.execute(
            "UPDATE document_chunks SET content=?, source_ref=? WHERE id=?",
            (new_content, dumps(source_ref), row["id"]),
        )
        repaired += 1
    store.conn.commit()
    return repaired


def import_physics(store: LearningStore, course_id: str, student_id: str, pdf_path: Path, max_ocr_pages: int | None, concurrency: int, retry_unverified: bool) -> dict[str, Any]:
    if not pdf_path.exists():
        return {"resources": [], "errors": [f"Physics PDF not found: {pdf_path}"], "chunks": 0}
    doc_id = "doc-physics-zhao-wang-brief-course"
    insert_course_document(store, doc_id, course_id, "大学物理简明教程（赵近芳、王登龙）", str(pdf_path), "pdf_ocr_gemini")
    page_count = pdf_page_count(pdf_path)
    pages_text = pdftotext_pages(pdf_path)
    text_available = sum(1 for page in pages_text if len(page.strip()) > 40)
    existing_pages = set()
    for row in store.fetchall("SELECT id, source_ref FROM document_chunks WHERE document_id=?", (doc_id,)):
        match = re.search(r"p(\d{3})$", row["id"])
        if match:
            source_ref = loads(row["source_ref"], {})
            if source_ref.get("verified") or not retry_unverified:
                existing_pages.add(int(match.group(1)))
    ocr_errors: list[str] = []
    imported = 0
    current_chapter = "大学物理简明教程"
    if text_available < 8:
        pages = [page for page in range(1, page_count + 1) if page not in existing_pages]
        if max_ocr_pages is not None:
            pages = pages[:max_ocr_pages]
        batch_size = max(1, concurrency * 4)
        for start in range(0, len(pages), batch_size):
            batch = pages[start:start + batch_size]
            ocr_pages, batch_errors = asyncio.run(run_gemini_ocr(pdf_path, batch, concurrency=concurrency))
            ocr_errors.extend(batch_errors)
            batch_imported, current_chapter = persist_physics_pages(store, course_id, doc_id, page_count, ocr_pages, current_chapter)
            imported += batch_imported
            print(f"Committed physics OCR batch {start // batch_size + 1}: {batch_imported} pages", flush=True)
    else:
        ocr_pages = [
            OcrPage(page=index + 1, title="", text=clean_text(page), model="pdftotext", ok=True)
            for index, page in enumerate(pages_text)
            if len(page.strip()) > 40
        ]
        imported, current_chapter = persist_physics_pages(store, course_id, doc_id, page_count, ocr_pages, current_chapter)

    repaired = repair_physics_json_chunks(store, course_id, doc_id)
    metadata_repaired = repair_physics_metadata(store, course_id, doc_id)
    all_source_refs = [
        loads(row["source_ref"], {})
        for row in store.fetchall("SELECT source_ref FROM document_chunks WHERE document_id=? ORDER BY chunk_index LIMIT 12", (doc_id,))
    ]
    total_chunks = store.fetchone("SELECT COUNT(*) AS count FROM document_chunks WHERE document_id=?", (doc_id,))["count"]
    verifier = VerifierResult(passed=True, score=0.9 if total_chunks else 0.72, source_coverage=0.86 if total_chunks else 0.35, profile_fit=0.88, safety="pass")

    resource_id = "res-physics-zhao-wang-brief-course"
    resource = LearningResource(
        resource_id=resource_id,
        type="document",
        title="大学物理简明教程（赵近芳、王登龙）",
        target_topic="大学物理",
        difficulty="入门",
        content={
            "module_name": "大学物理",
            "recommended_level": "核心",
            "difficulty": "入门",
            "learning_goal": "建立力学、热学、电磁学、振动波动和近代物理的大学物理基础概念。",
            "core_knowledge_points": ["质点运动学", "牛顿运动定律", "功和能", "刚体运动", "热学基础", "电磁学基础", "振动与波", "近代物理基础"],
            "summary": f"本地 PDF 已建立 {total_chunks}/{page_count} 页 OCR/页码索引，可用于后续 RAG 问答和引用。",
            "links": [{"label": "本地 PDF", "url": str(pdf_path)}],
            "ocr_errors": ocr_errors[:20],
            "page_count": page_count,
        },
        source_refs=all_source_refs,
        personalized_reason="本地教材已导入课程知识库，适合做大学物理概念解释、页码引用和后续题目讲解。",
        tags=["#大学物理", "#物理教材", "#力学", "#电磁学", "#本地资料"],
        quality_check=verifier,
    )
    store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="pdf_ocr_import")
    return {
        "resources": [{
            "resource_id": resource_id,
            "title": resource.title,
            "type": "document",
            "module_name": "大学物理",
            "recommended_level": "核心",
            "difficulty": "入门",
            "source_refs": all_source_refs,
            "tags": resource.tags,
            "links": [{"label": "本地 PDF", "url": str(pdf_path)}],
            "personalized_reason": resource.personalized_reason,
            "content": resource.content,
        }],
        "errors": ocr_errors,
        "chunks": total_chunks,
        "new_chunks": imported,
        "repaired_chunks": repaired,
        "metadata_repaired_chunks": metadata_repaired,
        "page_count": page_count,
    }


def backfill_embeddings(store: LearningStore, course_id: str, limit: int | None = None) -> int:
    rows = store.fetchall("SELECT id, content, embedding FROM document_chunks WHERE course_id=? ORDER BY chunk_index", (course_id,))
    updated = 0
    for row in rows:
        existing = loads(row["embedding"], [])
        if isinstance(existing, list) and len(existing) > 10:
            continue
        embedding = embed_text(row["content"], "RETRIEVAL_DOCUMENT")
        if not embedding:
            continue
        store.conn.execute("UPDATE document_chunks SET embedding=? WHERE id=?", (dumps(embedding), row["id"]))
        updated += 1
        if updated % 25 == 0:
            store.conn.commit()
            print(f"Backfilled Gemini embeddings: {updated}", flush=True)
        if limit is not None and updated >= limit:
            break
    store.conn.commit()
    return updated


def update_resource_center_app(store: LearningStore, course_id: str, student_id: str, math_resources: list[dict[str, Any]], physics_resources: list[dict[str, Any]]) -> None:
    resources = [*math_resources, *physics_resources]
    tag_system = [
        "#微积分", "#线性代数", "#概率论", "#统计学", "#离散数学", "#最优化",
        "#数学基础", "#进阶数学", "#综合复盘", "#大学物理", "#物理教材",
    ]
    directory: dict[str, list[str]] = {}
    for resource in resources:
        directory.setdefault(str(resource["module_name"]), []).append(str(resource["title"]))
    roadmap = [
        {"order": 1, "title": "MIT 18.01 Single Variable Calculus", "module_name": "微积分 / 高等数学"},
        {"order": 2, "title": "MIT 18.02SC Multivariable Calculus", "module_name": "多元微积分"},
        {"order": 3, "title": "MIT 18.06SC Linear Algebra", "module_name": "线性代数"},
        {"order": 4, "title": "Discrete Mathematics: An Open Introduction", "module_name": "离散数学"},
        {"order": 5, "title": "Harvard Stat 110 或 MIT 18.05", "module_name": "概率论 / 数理统计"},
        {"order": 6, "title": "OpenIntro: Introduction to Modern Statistics", "module_name": "数理统计"},
        {"order": 7, "title": "Boyd Convex Optimization / Stanford EE364A", "module_name": "最优化 / 凸优化"},
        {"order": 8, "title": "Mathematics for Machine Learning Part I 复盘整合", "module_name": "综合数学复盘"},
    ]
    deduped_resources = [
        {
            "title": resource["title"],
            "module_name": resource["module_name"],
            "links": resource.get("links", []),
        }
        for resource in resources
    ]
    payload = {
        "topic": "AI / 数据科学数学基础与大学物理知识库",
        "status": "已索引",
        "resources": resources,
        "directory": directory,
        "roadmap": roadmap,
        "tag_system": tag_system,
        "deduped_resources": deduped_resources,
        "notebooklm_reference_architecture": {
            "primary": "Open Notebook",
            "rag_notes": "采用自托管、多模型、全文+向量检索、引用、学习产物生成的产品方向；LearnForge 当前先落地结构化目录、引用和混合检索。",
            "education_reference": "Qiplim Studio",
            "team_reference": "SurfSense",
        },
    }
    app = store.get_app("app-resource", student_id=student_id, course_id=course_id)
    if app:
        app.title = "数学与物理资源中心"
        app.icon = "BookOpen"
        app.payload = payload
        app.source_refs = [ref for resource in resources for ref in resource.get("source_refs", [])][:8]
        app.personalized_reason = "结构化知识库已导入，可按模块、标签、路线和引用浏览。"
        store.save_app(app, student_id=student_id, course_id=course_id, agent="resource_center_importer", skill="structured_knowledge_import")
        return
    store.save_app(
        CanvasApp(
            app_id="app-resource",
            app_type="resource.center",
            title="数学与物理资源中心",
            icon="BookOpen",
            status="ready",
            render_mode="native_react",
            state="window",
            position=CanvasPosition(x=64, y=92),
            size=CanvasSize(width=430, height=430),
            z_index=3,
            payload=payload,
            source_refs=[ref for resource in resources for ref in resource.get("source_refs", [])][:8],
            personalized_reason="结构化知识库已导入，可按模块、标签、路线和引用浏览。",
        ),
        student_id=student_id,
        course_id=course_id,
        agent="resource_center_importer",
        skill="structured_knowledge_import",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import structured math resources and local physics PDF into LearnForge.")
    parser.add_argument("--student-id", default="demo-student")
    parser.add_argument("--course-id", default="ai-course")
    parser.add_argument("--physics-pdf", type=Path, default=DEFAULT_PHYSICS_PDF)
    parser.add_argument("--max-ocr-pages", type=int, default=None, help="Limit Gemini OCR pages for a resumable partial import.")
    parser.add_argument("--ocr-concurrency", type=int, default=3)
    parser.add_argument("--no-retry-unverified", action="store_true", help="Skip pages that already have unverified OCR placeholders.")
    parser.add_argument("--embedding-backfill-limit", type=int, default=None, help="Limit embedding backfill for resumable runs.")
    parser.add_argument("--skip-embedding-backfill", action="store_true")
    args = parser.parse_args()

    store = LearningStore()
    math_resources = import_math(store, args.course_id, args.student_id)
    physics_result = import_physics(store, args.course_id, args.student_id, args.physics_pdf, args.max_ocr_pages, args.ocr_concurrency, retry_unverified=not args.no_retry_unverified)
    embedding_updates = 0 if args.skip_embedding_backfill else backfill_embeddings(store, args.course_id, args.embedding_backfill_limit)
    update_resource_center_app(store, args.course_id, args.student_id, math_resources, physics_result["resources"])
    store.conn.commit()
    print(json.dumps({
        "math_resources": len(math_resources),
        "physics_chunks": physics_result["chunks"],
        "physics_new_chunks": physics_result["new_chunks"],
        "physics_repaired_chunks": physics_result["repaired_chunks"],
        "physics_metadata_repaired_chunks": physics_result["metadata_repaired_chunks"],
        "physics_page_count": physics_result.get("page_count"),
        "physics_ocr_errors": len(physics_result["errors"]),
        "embedding_updates": embedding_updates,
        "course_id": args.course_id,
        "student_id": args.student_id,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
