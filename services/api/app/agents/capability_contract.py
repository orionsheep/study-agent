from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class CapabilitySpec(BaseModel):
    name: str
    task_type: str
    keywords: list[str] = Field(default_factory=list)
    context_keywords: list[str] = Field(default_factory=list)
    hermes_skills: list[str] = Field(default_factory=list)
    expected_app_types: list[str] = Field(default_factory=list)
    expected_resource_types: list[str] = Field(default_factory=list)
    requires_canvas: bool = False
    requires_image_url: bool = False


CAPABILITIES: dict[str, CapabilitySpec] = {
    "resource_bundle": CapabilitySpec(
        name="resource_bundle",
        task_type="hermes_resource_bundle",
        keywords=["资料包", "资源包", "资源", "学习包", "全套", "一套"],
        hermes_skills=["resource-bundle-skill", "document-skill", "mindmap-skill", "quiz-skill", "code-practice-skill", "ppt-skill", "video-script-skill", "reading-material-skill"],
        expected_app_types=["resource.center", "mindmap.concept", "quiz.practice", "code.lab", "ppt.preview", "video.script", "notes.session"],
        expected_resource_types=["document", "mindmap", "quiz", "code_practice", "ppt", "video_script", "reading"],
        requires_canvas=True,
    ),
    "custom_infographic": CapabilitySpec(
        name="custom_infographic",
        task_type="hermes_custom_infographic",
        keywords=["信息图", "infographic", "海报", "可视化海报", "视觉总结"],
        context_keywords=["上一句", "刚刚", "上面", "基于", "把刚才", "上一轮"],
        hermes_skills=["custom-html-app-skill", "document-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=["document"],
        requires_canvas=True,
    ),
    "image_explanation": CapabilitySpec(
        name="image_explanation",
        task_type="hermes_image_explanation",
        keywords=["图片", "画图", "出图", "插图", "配图", "教学图", "教学插画", "生成图像"],
        context_keywords=["上一句", "刚刚", "上面", "基于", "把刚才", "上一轮"],
        hermes_skills=["image-generation-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["image.explanation"],
        expected_resource_types=[],
        requires_canvas=True,
        requires_image_url=True,
    ),
    "mindmap": CapabilitySpec(
        name="mindmap",
        task_type="hermes_mindmap",
        keywords=["思维导图", "导图", "知识图", "概念图"],
        hermes_skills=["mindmap-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["mindmap.concept"],
        expected_resource_types=["mindmap"],
        requires_canvas=True,
    ),
    "quiz": CapabilitySpec(
        name="quiz",
        task_type="hermes_quiz",
        keywords=["题库", "题目", "练习题", "测试题", "测验", "quiz", "出题"],
        hermes_skills=["quiz-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["quiz.practice"],
        expected_resource_types=["quiz"],
        requires_canvas=True,
    ),
    "code_lab": CapabilitySpec(
        name="code_lab",
        task_type="hermes_code_lab",
        keywords=["代码实验", "代码", "实验", "编程练习", "code lab", "demo"],
        hermes_skills=["code-practice-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["code.lab"],
        expected_resource_types=["code_practice"],
        requires_canvas=True,
    ),
    "interactive_demo": CapabilitySpec(
        name="interactive_demo",
        task_type="hermes_interactive_demo",
        keywords=[
            "互动演示", "演示一下", "演示", "动画", "模拟", "仿真", "可交互", "交互演示", "动态演示",
            # phrasings like "生成一个X的交互模型" must be a single demo, not a resource bundle
            "交互模型", "互动模型", "演示模型", "动态模型", "可视化模型", "仿真模型",
            "交互式", "互动式", "交互", "互动", "可视化", "模拟器", "演示动画", "交互动画",
        ],
        hermes_skills=["custom-html-app-skill", "code-practice-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=["document"],
        requires_canvas=True,
    ),
    "ppt": CapabilitySpec(
        name="ppt",
        task_type="hermes_ppt",
        keywords=["ppt", "幻灯", "课件", "演示文稿"],
        hermes_skills=["guizang-ppt-skill", "ppt-skill", "custom-html-app-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=["ppt"],
        requires_canvas=True,
    ),
    "video_script": CapabilitySpec(
        name="video_script",
        task_type="hermes_video_script",
        keywords=["视频脚本", "分镜", "动画脚本", "短视频", "视频"],
        hermes_skills=["video-script-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["video.script"],
        expected_resource_types=["video_script"],
        requires_canvas=True,
    ),
    "notes": CapabilitySpec(
        name="notes",
        task_type="notes_summary",
        keywords=["总结到笔记", "整理成笔记", "整理成学习笔记", "学习笔记", "保存笔记", "生成笔记", "做成笔记", "笔记 app", "笔记app"],
        hermes_skills=["notes-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["notes.session"],
        expected_resource_types=["notes"],
        requires_canvas=True,
    ),
    "learning_path": CapabilitySpec(
        name="learning_path",
        task_type="learning_path",
        keywords=["学习路径", "路径", "学习计划", "路线"],
        hermes_skills=["document-skill", "reading-material-skill", "app-generation-skill"],
        expected_app_types=["learning.path"],
        requires_canvas=True,
    ),
    "dashboard": CapabilitySpec(
        name="dashboard",
        task_type="dashboard",
        keywords=["仪表盘", "dashboard", "学习状态", "掌握度"],
        expected_app_types=["dashboard.learning"],
        requires_canvas=True,
    ),
    "detailed_analysis": CapabilitySpec(
        name="detailed_analysis",
        task_type="detailed_analysis",
        keywords=[],
        hermes_skills=["detailed-analysis-skill", "verifier-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=[],
        requires_canvas=True,
    ),
    "answer_only": CapabilitySpec(
        name="answer_only",
        task_type="tutor_turn",
        keywords=[],
        expected_app_types=[],
        requires_canvas=False,
    ),
}


GENERATION_MARKERS = ["生成", "制作", "做成", "放到画布", "画布", "canvas", "app", "创建", "转成", "输出", "演示", "动画", "模拟", "仿真"]
CONTEXT_MARKERS = ["上一句", "刚刚", "上面", "基于", "把刚才", "上一轮", "刚才"]
PROFILE_MARKERS = ["我是", "画像", "喜欢", "大一"]
IMAGE_ASSET_MARKERS = ["图片", "图像", "插图", "配图", "出图", "画图", "教学图片", "教学插画", "image", "illustration"]
INFOGRAPHIC_MARKERS = ["信息图", "infographic", "海报", "可视化海报", "视觉总结", "图文卡片"]
DETAILED_ANALYSIS_MARKERS = [
    "分析这道题", "讲解这道题", "分析这道", "讲解这道", "帮我讲解", "讲解一下",
    "给我讲", "给我讲解", "帮忙讲解", "批改作业", "改作业", "帮我看看这道题",
    "这道题怎么做", "这题怎么做", "这题什么", "这题怎么解",
    "看看作业", "分析题目", "分析作业", "讲解题目", "讲解作业",
    "详细分析", "详细讲解", "题目解析", "试题分析",
    "逐题讲解", "一道一道讲", "每题都讲",
    "作业视频", "拍题", "批改", "改一下",
    "analyse", "analyze this", "solve this problem", "explain this question",
]
INFOGRAPHIC_IMAGE_MARKERS = ["一张图", "图片版", "海报", "精美", "视觉冲击", "成品图", "出图", "封面", "插画风", "nano banana", "nanobanana", "香蕉"]
INFOGRAPHIC_HTML_MARKERS = ["html版", "html 版", "网页", "可编辑", "可复制", "可交互", "表格", "流程卡片", "左侧打开", "代码渲染", "html"]
GENERIC_TOPIC_TERMS = {
    "图片", "图像", "图解", "教学图", "信息图", "海报", "笔记", "总结", "资源", "资源包", "资料包",
    "演示", "动画", "互动演示", "app", "canvas", "画布", "ppt", "课件", "题库", "练习", "代码实验",
    "路线图", "学习路径", "路径", "学习计划", "当前主题",
}
TOPIC_SUFFIX_PATTERN = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9]{0,22}(?:算法|定理|模型|结构|函数|系统|协议|语法|单词|文章|概念|实验|公式|排序|力学|电路|编程|网络|数据库|操作系统|神经网络))"
)


def _contains_any(message: str, terms: list[str]) -> bool:
    return any(term.lower() in message for term in terms)


def detect_infographic_render_mode(message: str) -> str:
    lowered = message.lower()
    if _contains_any(lowered, INFOGRAPHIC_HTML_MARKERS):
        return "html"
    if _contains_any(lowered, INFOGRAPHIC_IMAGE_MARKERS):
        return "image"
    return "image"


def clean_topic(candidate: str) -> str:
    topic = candidate.strip(" ：:，。！？、\n\t\"'《》“”")
    prefixes = ["请", "你", "帮我", "给我", "现在", "基于", "根据", "把", "将", "用", "对", "关于", "围绕", "演示一下", "演示", "详细讲解一下", "详细讲解", "讲解一下", "讲一下", "介绍一下", "介绍", "我们正在学习", "正在学习", "我们正在讲", "正在讲", "我们刚刚讲了", "刚刚讲了", "讲了", "刚刚", "上一句", "上面", "当前", "本轮学习", "本节学习", "一下", "所有", "全部", "几种", "几类", "常见", "主流", "核心", "经典", "最经典"]
    suffixes = ["生成", "制作", "做成", "整理", "总结", "输出", "列出", "打开", "放到", "画布", "canvas", "app", "图片", "图像", "信息图", "笔记", "资源包", "资料包", "演示", "动画", "互动演示", "可交互", "详细", "讲解", "介绍", "一下", "都", "给列出来", "学习笔记"]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if topic.lower().startswith(prefix.lower()):
                topic = topic[len(prefix):].strip(" ：:，。！？、\n\t\"'《》“”")
                changed = True
        next_topic = re.sub(r"^(数学|物理|英语|计算机|文科|理科|科学)?(里面的|上面的|中的|里的)", "", topic).strip(" ：:，。！？、\n\t\"'《》“”")
        if next_topic != topic:
            topic = next_topic
            changed = True
        for suffix in suffixes:
            if topic.lower().endswith(suffix.lower()):
                topic = topic[: -len(suffix)].strip(" ：:，。！？、\n\t\"'《》“”")
                changed = True
    topic = topic.strip(" ：:，。！？、\n\t\"'《》“”")
    return topic


def is_generic_topic(topic: str | None) -> bool:
    if not topic:
        return True
    normalized = clean_topic(topic).lower()
    if not normalized:
        return True
    return normalized in GENERIC_TOPIC_TERMS or any(term in normalized for term in ["笔记", "总结", "生成图片", "教学图片", "信息图", "路线图", "学习路径", "app"])


def extract_learning_topic(text: str | None) -> str | None:
    if not text:
        return None
    source = str(text)
    quoted = re.search(r"[《“\"]([^》”\"]{2,40})[》”\"]", source)
    if quoted:
        candidate = clean_topic(quoted.group(1))
        if candidate and candidate.lower() not in GENERIC_TOPIC_TERMS:
            return candidate[:80]
    for match in TOPIC_SUFFIX_PATTERN.finditer(source):
        candidate = clean_topic(match.group(1))
        if candidate and not is_generic_topic(candidate) and len(candidate) >= 2:
            return candidate[:80]
    patterns = [
        r"(?:关于|围绕|主题是|主题为|讲解|介绍|学习|演示)([^，。！？\n]{2,48})",
        r"(?:基于|根据)([^，。！？\n]{2,48})",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            candidate = clean_topic(match.group(1))
            if candidate and not is_generic_topic(candidate):
                return candidate[:80]
    return None


def detect_capability(message: str) -> CapabilitySpec:
    lowered = message.lower()
    if _contains_any(lowered, PROFILE_MARKERS):
        return CapabilitySpec(name="profile_build", task_type="profile_build", keywords=PROFILE_MARKERS, requires_canvas=False)
    # 详细分析标记优先于图片/信息图标记：当用户说"分析这道题（图片）"时，
    # 应路由到 detailed_analysis 而非 image_explanation
    if _contains_any(lowered, DETAILED_ANALYSIS_MARKERS):
        return CAPABILITIES["detailed_analysis"]
    if _contains_any(lowered, INFOGRAPHIC_MARKERS):
        return CAPABILITIES["custom_infographic"]
    if _contains_any(lowered, IMAGE_ASSET_MARKERS):
        return CAPABILITIES["image_explanation"]
    # Specific artifact intents must win over broad bundle words such as "一套/全套/资源".
    # Example: "生成一套大学物理的简单介绍ppt" is a PPT deck request, not a full resource pack.
    ordered = [
        "mindmap",
        "quiz",
        "interactive_demo",
        "code_lab",
        "ppt",
        "video_script",
        "notes",
        "learning_path",
        "dashboard",
        "resource_bundle",
    ]
    for name in ordered:
        spec = CAPABILITIES[name]
        if _contains_any(lowered, spec.keywords):
            return spec
    if _contains_any(lowered, GENERATION_MARKERS):
        return CAPABILITIES["resource_bundle"]
    return CAPABILITIES["answer_only"]


def resolve_generation_topic(message: str, last_assistant_answer: str | None = None) -> tuple[str, str, str]:
    lowered = message.lower()
    topic = extract_learning_topic(message)
    context_source = "current_message"
    source_material = message
    if last_assistant_answer and (_contains_any(lowered, CONTEXT_MARKERS) or not topic):
        context_source = "last_assistant_answer"
        source_material = last_assistant_answer[:3000]
        topic = topic or extract_learning_topic(last_assistant_answer)
    return topic or clean_topic(message) or "当前学习主题", context_source, source_material


def contract_payload(spec: CapabilitySpec, topic: str, context_source: str, source_material: str | None = None) -> dict[str, Any]:
    return {
        "capability": spec.name,
        "topic": topic,
        "source_material": source_material or topic,
        "context_source": context_source,
        "expected_app_types": spec.expected_app_types,
        "expected_resource_types": spec.expected_resource_types,
        "requires_canvas": spec.requires_canvas,
        "requires_image_url": spec.requires_image_url,
        "hermes_skills": spec.hermes_skills,
    }
