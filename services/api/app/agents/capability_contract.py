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
            # "演示" 仍保留——但 ppt 在 ordered 检测里排在前面,
            # 所以"演示文稿"会先命中 ppt,不会被这里的"演示"劫持。
            "互动演示", "演示一下", "演示", "动画", "模拟", "仿真", "可交互", "交互演示", "动态演示",
            # phrasings like "生成一个X的交互模型" must be a single demo, not a resource bundle
            "交互模型", "互动模型", "演示模型", "动态模型", "可视化模型", "仿真模型",
            "交互式", "互动式", "交互", "互动", "可视化", "模拟器", "演示动画", "交互动画",
            "可以玩", "可玩的", "能玩", "能操作", "可操作", "操作模型",
        ],
        hermes_skills=["custom-html-app-skill", "code-practice-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=[],
        requires_canvas=True,
    ),
    "ppt": CapabilitySpec(
        name="ppt",
        task_type="hermes_ppt",
        keywords=["ppt", "幻灯", "课件", "演示文稿", "讲义", "汇报", "报告", "slide", "deck", "presentation"],
        # hermes_skills 去掉 custom-html-app-skill:避免 Hermes 在 PPT 场景误选动画 skill。
        # PPT 只用 guizang-ppt-skill / ppt-skill,这俩才是真正的 PPT 生成器。
        hermes_skills=["guizang-ppt-skill", "ppt-skill", "verifier-skill", "app-generation-skill"],
        expected_app_types=["custom.html"],
        expected_resource_types=["ppt"],
        requires_canvas=True,
    ),
    "video_search": CapabilitySpec(
        name="video_search",
        task_type="video_recommendations",
        keywords=["搜索视频", "找视频", "推荐视频", "查视频", "b站", "哔哩", "bilibili", "课程视频"],
        hermes_skills=[],
        expected_app_types=["video.player"],
        expected_resource_types=["video"],
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


GENERATION_MARKERS = ["生成", "制作", "做成", "做一个", "放到画布", "画布", "canvas", "app", "创建", "转成", "输出"]
SEARCH_GENERATION_MARKERS = ["搜索", "找", "推荐", "查", "检索"]
CONTEXT_MARKERS = ["上一句", "刚刚", "上面", "基于", "把刚才", "上一轮", "刚才", "这个", "这个模型", "该模型", "此模型", "这个内容", "这部分"]
# 画像标记收紧:不再用宽泛的"我是"/"喜欢"做子串匹配——它们会劫持
# "我是不是应该..."/"我喜欢用动画学物理"等正常请求。改用完整短语,
# 要求明确的"自我介绍/画像构建"语义。
PROFILE_MARKERS = [
    "我是大一", "我是高三", "我是高二", "我是高一", "我是初三", "我是初二",
    "我是初一", "我是大四", "我是大三", "我是大二", "我是一名学生", "我是学生",
    "我的画像", "学习画像", "更新画像", "建立画像",
]
IMAGE_ASSET_MARKERS = ["图片", "图像", "插图", "配图", "出图", "画图", "教学图片", "教学插画", "image", "illustration"]
INFOGRAPHIC_MARKERS = ["信息图", "infographic", "海报", "可视化海报", "视觉总结", "图文卡片"]
PPT_STRONG_MARKERS = ["ppt", "幻灯", "课件", "演示文稿", "slide", "deck", "presentation"]
PPT_GENERATIVE_MARKERS = ["讲义", "汇报", "报告"]
IMAGE_GENERATIVE_MARKERS = ["生成图片", "生成图像", "生成一张", "生成张", "画图", "出图", "做图", "配图", "教学图", "示意图", "插图"]
DIRECT_ANSWER_RECALL_MARKERS = [
    "还记得", "记不记得", "前面聊", "刚才聊", "之前聊", "聊了什么", "说了什么",
    "我和你聊", "我跟你聊", "上面说", "前面说", "刚刚说",
]
DIRECT_ANSWER_EXPLAIN_MARKERS = [
    "是什么", "为什么", "怎么理解", "如何理解", "解释一下", "讲一下", "说一下",
    "区别是什么", "有什么区别", "核心思想", "原理是什么",
]
PROBLEM_ANALYSIS_CONTEXT_MARKERS = [
    "这道题", "这题", "题目", "作业", "试卷", "拍题", "批改", "逐题", "每题",
    "图片", "截图", "上传",
]
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
    "这个模型", "该模型", "此模型", "这个内容", "这部分内容", "上面内容",
    "交互模型", "可交互模型", "互动模型", "动态模型", "仿真模型",
}
TOPIC_SUFFIX_PATTERN = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9]{0,22}(?:算法|定理|模型|结构|函数|系统|协议|语法|单词|文章|概念|实验|公式|排序|力学|电路|编程|网络|数据库|操作系统|神经网络))"
)


def _contains_any(message: str, terms: list[str]) -> bool:
    return any(term.lower() in message for term in terms)


def has_explicit_artifact_intent(message: str) -> bool:
    lowered = message.lower()
    has_generation = _contains_any(lowered, GENERATION_MARKERS)
    if _contains_any(lowered, PPT_STRONG_MARKERS):
        return True
    if _contains_any(lowered, PPT_GENERATIVE_MARKERS) and has_generation:
        return True
    if _contains_any(lowered, IMAGE_GENERATIVE_MARKERS):
        return True
    if _contains_any(lowered, INFOGRAPHIC_MARKERS) and (has_generation or _contains_any(lowered, IMAGE_GENERATIVE_MARKERS)):
        return True
    if _contains_any(lowered, INTERACTIVE_MODEL_SIGNALS) and (
        has_generation or _contains_any(lowered, INTERACTIVE_CORRECTION)
    ):
        return True
    if has_generation and _contains_any(lowered, CAPABILITIES["interactive_demo"].keywords):
        return True
    if _contains_any(lowered, ["可以玩", "可玩的", "能玩", "能操作", "可操作"]) and _contains_any(lowered, ["三维", "3d", "模型", "魔方", "模拟器"]):
        return True
    if _contains_any(lowered, CAPABILITIES["video_search"].keywords) and _contains_any(lowered, SEARCH_GENERATION_MARKERS):
        return True
    if _contains_any(lowered, ["视频脚本", "分镜", "动画脚本"]) and has_generation:
        return True
    if _contains_any(lowered, CAPABILITIES["mindmap"].keywords) and has_generation:
        return True
    if _contains_any(lowered, CAPABILITIES["code_lab"].keywords) and has_generation:
        return True
    if _contains_any(lowered, CAPABILITIES["quiz"].keywords) and _contains_any(lowered, ["生成", "出", "出题", "制作", "做一组", "练习题", "题库", "测验"]):
        return True
    if _contains_any(lowered, CAPABILITIES["notes"].keywords) and _contains_any(lowered, ["整理", "保存", "生成", "做成", "总结到"]):
        return True
    if _contains_any(lowered, CAPABILITIES["learning_path"].keywords) and _contains_any(lowered, ["生成", "规划", "制定", "做", "创建"]):
        return True
    if _contains_any(lowered, CAPABILITIES["dashboard"].keywords) and _contains_any(lowered, ["打开", "生成", "查看", "看一下"]):
        return True
    if _contains_any(lowered, CAPABILITIES["resource_bundle"].keywords) and has_generation:
        return True
    return False


def is_direct_answer_request(message: str) -> bool:
    lowered = message.lower().strip()
    if not lowered or has_explicit_artifact_intent(lowered):
        return False
    if _contains_any(lowered, DIRECT_ANSWER_RECALL_MARKERS):
        return True
    if _contains_any(lowered, DIRECT_ANSWER_EXPLAIN_MARKERS):
        return True
    return False


def detect_infographic_render_mode(message: str) -> str:
    lowered = message.lower()
    if _contains_any(lowered, INFOGRAPHIC_HTML_MARKERS):
        return "html"
    if _contains_any(lowered, INFOGRAPHIC_IMAGE_MARKERS):
        return "image"
    return "image"


def clean_topic(candidate: str) -> str:
    topic = candidate.strip(" ：:，。！？、\n\t\"'《》“”")
    prefixes = ["请", "你", "帮我", "给我", "现在", "基于", "根据", "把", "将", "用", "对", "关于", "围绕", "生成一张", "生成张", "生成一个", "生成一份", "演示一下", "演示", "详细讲解一下", "详细讲解", "讲解一下", "讲一下", "介绍一下", "介绍", "我们正在学习", "正在学习", "我们正在讲", "正在讲", "我们刚刚讲了", "刚刚讲了", "讲了", "刚刚", "上一句", "上面", "当前", "本轮学习", "本节学习", "一下", "所有", "全部", "几种", "几类", "常见"]
    # 注意:不要把 "主流"/"核心"/"经典"/"最经典" 放进 prefixes —— 它们是主题的有机组成部分
    # ("主流排序算法""核心数据结构"),剥掉会导致标题残缺(如 "主流的排序" → "的排序")。
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


# 明确的"交互动画/3D模型"信号词——不含单独的"模型"/"动画"(太宽泛),
# 只含明确带"交互/3D/动态/仿真"语境的词。
INTERACTIVE_MODEL_SIGNALS = [
    "3d", "三维", "可交互", "交互动画", "交互模型", "互动模型",
    "动态模型", "可视化模型", "仿真模型", "模拟器", "互动演示", "动态演示",
]
INTERACTIVE_CORRECTION = [
    "我要的是", "不是练习题", "不是题", "不要练习题", "别做练习题", "不是报告", "不是讲解",
    "不是ppt", "不是 ppt", "不要ppt", "不要 ppt", "不是幻灯片", "不要幻灯片",
    "不是幻灯", "不要幻灯", "我要交互模型", "我要可交互模型", "我要的是交互模型",
    "我要的是可交互模型", "生成可交互模型不是ppt", "生成交互模型不是ppt",
]
PPT_CORRECTION = [
    "不是交互模型", "不是可交互模型", "不要交互模型", "不要可交互模型",
    "我要ppt", "我要 ppt", "我要的是ppt", "我要的是 ppt", "我要幻灯片",
]
PLAYABLE_INTENT = ["可以玩", "可玩的", "能玩", "能操作", "可操作"]


def detect_capability(message: str) -> CapabilitySpec:
    lowered = message.lower()
    if _contains_any(lowered, PROFILE_MARKERS):
        return CapabilitySpec(name="profile_build", task_type="profile_build", keywords=PROFILE_MARKERS, requires_canvas=False)
    has_generation = _contains_any(lowered, GENERATION_MARKERS)
    has_interactive_model = _contains_any(lowered, INTERACTIVE_MODEL_SIGNALS)
    has_interactive_correction = _contains_any(lowered, INTERACTIVE_CORRECTION)
    has_ppt_correction = _contains_any(lowered, PPT_CORRECTION)

    if is_direct_answer_request(lowered):
        return CAPABILITIES["answer_only"]

    # Explicit skill locks. These are authoritative for user-requested artifacts:
    # PPT stays PPT, images stay image-generation, and interactive models stay custom.html demos.
    if has_interactive_correction and not has_ppt_correction:
        return CAPABILITIES["interactive_demo"]
    if has_ppt_correction:
        return CAPABILITIES["ppt"]
    # Detailed analysis report requests must beat the generic PPT "报告" marker.
    if _contains_any(lowered, ["html报告", "html 报告"]) or (
        has_generation and _contains_any(lowered, ["分析报告", "解析报告", "详细分析报告", "详细解析报告"])
    ):
        return CAPABILITIES["detailed_analysis"]
    if _contains_any(lowered, PPT_STRONG_MARKERS) or (
        _contains_any(lowered, PPT_GENERATIVE_MARKERS) and has_generation
    ):
        return CAPABILITIES["ppt"]
    if _contains_any(lowered, IMAGE_GENERATIVE_MARKERS):
        return CAPABILITIES["image_explanation"]
    if _contains_any(lowered, INFOGRAPHIC_MARKERS) and (has_generation or _contains_any(lowered, IMAGE_GENERATIVE_MARKERS)):
        return CAPABILITIES["custom_infographic"]
    if (has_interactive_model or _contains_any(lowered, CAPABILITIES["interactive_demo"].keywords)) and (
        has_generation or has_interactive_correction
    ):
        return CAPABILITIES["interactive_demo"]
    has_playable = _contains_any(lowered, PLAYABLE_INTENT) or "我要的是" in lowered
    has_spatial = _contains_any(lowered, ["三维", "3d", "模拟器"])
    if has_playable and has_spatial:
        return CAPABILITIES["interactive_demo"]

    # Detailed analysis is for problem/assignment/image-analysis work, not ordinary
    # direct questions such as "解释一下这个概念".
    if _contains_any(lowered, IMAGE_ASSET_MARKERS) and _contains_any(lowered, IMAGE_GENERATIVE_MARKERS):
        return CAPABILITIES["image_explanation"]
    # 特定产物意图(ppt/mindmap/quiz/video_script 等)。注意 video_script 排在
    # interactive_demo 前面——"动画脚本"命中 video_script 而非 interactive_demo。
    ordered = [
        "mindmap",
        "quiz",
        "code_lab",
        "video_search",
        "video_script",
        "interactive_demo",
        "notes",
        "learning_path",
        "dashboard",
        "resource_bundle",
    ]
    for name in ordered:
        spec = CAPABILITIES[name]
        if _contains_any(lowered, spec.keywords) and has_explicit_artifact_intent(lowered):
            return spec
    return CAPABILITIES["answer_only"]


def resolve_generation_topic(message: str, last_assistant_answer: str | None = None) -> tuple[str, str, str]:
    lowered = message.lower()
    topic = extract_learning_topic(message)
    context_source = "current_message"
    source_material = message
    if last_assistant_answer and (not topic or is_generic_topic(topic)):
        context_source = "last_assistant_answer"
        source_material = last_assistant_answer[:3000]
        referenced_topic = extract_learning_topic(last_assistant_answer)
        if referenced_topic and not is_generic_topic(referenced_topic):
            topic = referenced_topic
        else:
            topic = topic or referenced_topic
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
        "capability_locked": True,
        "route_source": "capability_contract",
    }
