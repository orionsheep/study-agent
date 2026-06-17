# LearnForge 记忆系统（EduMem0）升级规划 — 满足赛题要求

> 版本：2026-06-17  
> 目标：将当前 EduMem0 从"骨架"升级为满足赛题要求的完整记忆系统

---

## 一、当前 EduMem0 状态 vs 赛题要求

### 赛题核心要求（从 `notebooklm_open_source_evaluation.md` 提取）

| 赛题要求 | 当前状态 | 满足度 |
|----------|----------|--------|
| **6维动态画像**（知识基础、认知风格、易错点偏好、学习动机、时间模式、交互偏好） | `profile` 类型只有 `weak_points`、`grade`、`major`、`knowledge_foundation`、`cognitive_style`、`learning_pace`，缺少完整6维结构 | **40%** |
| **多智能体资源生成** | 有 `resource_preference` 类型但无资源生成记录，无反馈闭环 | **30%** |
| **个性化路径规划** | `learning_path` 类型只有类型定义，无路径生成引擎 | **20%** |
| **智能辅导（加分）** | `misconception` 有基础，但无辅导策略生成 | **50%** |
| **学习效果评估（加分）** | `mastery` 有基础，但无评估模型和动态调整引擎 | **30%** |

---

## 二、升级模块规划

### 模块1：6维动态画像扩展（P0，最高优先级）

#### 1.1 扩展 `profile` 类型的 `structured_payload`

当前 `profile` 的 `structured_payload` 结构：

```python
# 当前（extractor.py 硬编码提取）
dimensions = {
    "grade": "大一",
    "major": "软件工程",
    "knowledge_foundation": "Python 一般",
    "weak_points": ["线性代数", "数学推导"],
    "preferred_resources": ["图解"],
    "interests": ["代码实验"],
    "cognitive_style": "图解优先，配合互动可视化",
    "learning_pace": "小步练习，分阶段推进",
    "learning_goal": "学习神经网络",
    "subjects": ["机器学习"],
    "subject_confidence": {"机器学习": 0.75}
}
```

赛题要求的 6 维结构：

```python
# 目标（6维画像）
class ProfileDimensions(BaseModel):
    """6维学生画像，直接映射赛题要求"""
    
    # 维度1：知识基础（Knowledge Base）
    knowledge_base: dict[str, float]  # {"数学": 0.6, "Python": 0.8, "线性代数": 0.4}
    
    # 维度2：认知风格（Cognitive Style）
    cognitive_style: str  # "visual" | "auditory" | "practical" | "reading" | "mixed"
    cognitive_style_evidence: list[str]  # 提取依据（如"用户说喜欢图解"）
    
    # 维度3：易错点偏好（Misconception Tendency）
    misconception_tendency: dict[str, list[str]]  # {"数学": ["符号混淆", "计算粗心"]}
    
    # 维度4：学习动机（Learning Motivation）
    motivation: str  # "goal_oriented" | "interest_oriented" | "task_oriented" | "mixed"
    motivation_evidence: list[str]
    
    # 维度5：时间模式（Time Pattern）
    time_pattern: dict  # {"active_hours": ["19:00-22:00"], "session_duration_avg": 45, "preferred_days": ["周末"]}
    
    # 维度6：交互偏好（Interaction Preference）
    interaction_preference: str  # "active_exploration" | "guided" | "autonomous" | "collaborative"
    interaction_evidence: list[str]
```

#### 1.2 在 `extractor.py` 中接入 LLM 辅助提取

当前 `extractor.py` 是硬编码关键词匹配，需要升级为 LLM 辅助提取。

```python
# services/api/app/edumem0/extractor.py

async def extract_with_llm(self, student_id: str, message: str, course_id: str) -> list[EduMemoryItem]:
    """使用 LLM 从用户消息中提取 6 维画像特征"""
    
    prompt = f"""从以下用户消息中提取学生的 6 维画像特征。

用户消息："{message}"

请提取以下维度（如果无法提取，返回 null）：
1. 知识基础：学生对各学科/前置知识的掌握程度（0-1 分数）
2. 认知风格：视觉型/听觉型/实践型/阅读型/混合型，及证据
3. 易错点偏好：该学生常犯的特定错误类型（如符号混淆、概念误解）
4. 学习动机：目标导向/兴趣导向/任务导向/混合型，及证据
5. 时间模式：活跃时段、单次学习时长、偏好日期
6. 交互偏好：主动探索/引导式/自主式/协作式，及证据

输出 JSON：
{{
    "knowledge_base": {{"学科名": 0.X}},
    "cognitive_style": {{
        "style": "visual|auditory|practical|reading|mixed",
        "evidence": ["用户说..."]
    }},
    "misconception_tendency": {{
        "学科名": ["错误类型1", "错误类型2"]
    }},
    "motivation": {{
        "type": "goal_oriented|interest_oriented|task_oriented|mixed",
        "evidence": ["用户说..."]
    }},
    "time_pattern": {{
        "active_hours": ["HH:MM-HH:MM"],
        "session_duration_avg": 分钟数,
        "preferred_days": ["weekend|weekday"]
    }},
    "interaction_preference": {{
        "type": "active_exploration|guided|autonomous|collaborative",
        "evidence": ["用户说..."]
    }}
}}"""

    # 调用 LLM
    response = await self.llm.generate(prompt)
    dimensions = json.loads(response)
    
    # 生成 EduMemoryItem
    return [EduMemoryItem(
        student_id=student_id,
        memory_type="profile",
        content=f"6维画像更新：{json.dumps(dimensions, ensure_ascii=False)[:200]}...",
        structured_payload=dimensions,
        confidence=0.75,  # LLM 提取的默认置信度
        evidence_type="llm_extraction",
        source_agent="memory_extractor",
    )]
```

#### 1.3 `from_chat` 方法保留规则式提取作为 fallback

```python
def from_chat(self, student_id, message, course_id):
    # 1. 先尝试规则式提取（快速、低成本）
    rule_based = self._rule_based_extract(message, course_id)
    
    # 2. 如果规则式提取不足（置信度低），触发 LLM 提取
    if not rule_based or self._confidence(rule_based) < 0.5:
        return self.extract_with_llm(student_id, message, course_id)
    
    return rule_based
```

#### 1.4 修改 `profile_memory.py` 支持 6 维结构

```python
# services/api/app/edumem0/profile_memory.py

def build_user_profile(student_id, message, course_id="default") -> EduMemoryItem:
    """从 onboarding 消息构建 6 维画像"""
    
    # 调用 LLM 提取
    dimensions = await extract_with_llm(student_id, message, course_id)
    
    return EduMemoryItem(
        student_id=student_id,
        course_id=course_id,
        memory_type="profile",
        content=f"用户画像：{dimensions['cognitive_style']['style']}型学习者，" 
                f"动机：{dimensions['motivation']['type']}，"
                f"交互偏好：{dimensions['interaction_preference']['type']}",
        structured_payload=dimensions,  # 完整的 6 维结构
        confidence=0.75,
        importance=0.9,  # 画像是最重要的记忆
        decay_rate=0.0,  # 画像不随时间衰减
        evidence_type="onboarding_extraction",
        source_agent="profile_agent",
    )
```

---

### 模块2：路径规划引擎（P0）

#### 2.1 新增 `PathPlanner` 类

```python
# services/api/app/edumem0/path_planner.py

from typing import TypedDict

class KnowledgeNode(TypedDict):
    id: str
    title: str
    prerequisites: list[str]
    difficulty: float  # 0-1
    estimated_time: int  # 分钟

class LearningPath(TypedDict):
    stages: list[dict]
    total_estimated_time: int
    difficulty_distribution: dict

class PathPlanner:
    def __init__(self, knowledge_graph: dict, mem0_store):
        self.kg = knowledge_graph  # 知识点依赖图
        self.store = mem0_store
    
    def generate_path(
        self,
        student_id: str,
        course_id: str,
        target_knowledge: str,  # 目标知识点
        profile: ProfileDimensions,
    ) -> LearningPath:
        """根据 6 维画像生成个性化学习路径"""
        
        # 1. 获取目标知识点的所有前置依赖
        prerequisites = self._get_all_prerequisites(target_knowledge)
        
        # 2. 获取学生的当前掌握状态
        mastery = self.store.search(
            student_id, memory_types=["mastery"], course_id=course_id
        )
        mastery_map = {m.knowledge_point_id: m.confidence for m in mastery}
        
        # 3. 识别知识缺口（前置知识点中掌握度 < 0.6 的）
        gaps = [p for p in prerequisites if mastery_map.get(p, 0) < 0.6]
        
        # 4. 按认知风格排序资源
        resources = self._get_resources_for_knowledge(target_knowledge)
        sorted_resources = self._sort_by_cognitive_style(resources, profile.cognitive_style)
        
        # 5. 按学习动机调整路径结构
        if profile.motivation == "goal_oriented":
            # 目标导向：直接冲核心，边学边补基础
            stages = [
                {"title": "快速入门", "topics": gaps[:2], "mode": "overview"},
                {"title": "核心攻克", "topics": [target_knowledge], "mode": "deep"},
                {"title": "基础巩固", "topics": gaps[2:], "mode": "review"},
            ]
        elif profile.motivation == "interest_oriented":
            # 兴趣导向：先探索相关有趣内容
            related_interesting = self._get_related_interesting(target_knowledge, profile.interests)
            stages = [
                {"title": "兴趣探索", "topics": related_interesting, "mode": "explore"},
                {"title": "核心学习", "topics": [target_knowledge], "mode": "deep"},
                {"title": "基础补全", "topics": gaps, "mode": "review"},
            ]
        else:  # task_oriented or mixed
            # 任务导向：按依赖顺序系统学习
            stages = [
                {"title": "基础补全", "topics": gaps, "mode": "sequential"},
                {"title": "核心概念", "topics": [target_knowledge], "mode": "deep"},
                {"title": "拓展深化", "topics": self._get_extensions(target_knowledge), "mode": "extend"},
            ]
        
        # 6. 按时间模式调整每日推荐量
        daily_recommendation = self._adjust_daily_volume(profile.time_pattern)
        
        # 7. 按交互偏好调整资源类型
        resource_types = self._adjust_resource_types(profile.interaction_preference)
        
        return LearningPath(
            stages=stages,
            total_estimated_time=sum(self._estimate_time(s) for s in stages),
            difficulty_distribution=self._calculate_difficulty(stages, mastery_map),
            daily_recommendation=daily_recommendation,
            resource_types=resource_types,
        )
```

#### 2.2 在 `planner_agent.py` 中集成

```python
# services/api/app/agents/planner_agent.py

from app.edumem0.path_planner import PathPlanner

class PlannerAgent:
    def __init__(self, mem0_client, path_planner, knowledge_graph):
        self.mem0 = mem0_client
        self.planner = path_planner
        self.kg = knowledge_graph
    
    async def create_learning_plan(self, student_id, course_id, target_topic):
        # 1. 获取 6 维画像
        profile = self.mem0.get_profile(student_id, course_id)
        
        # 2. 生成路径
        path = self.planner.generate_path(student_id, course_id, target_topic, profile)
        
        # 3. 将路径写入记忆
        await self.mem0.add_memory(
            student_id=student_id,
            memory_type="learning_path",
            content=f"学习路径：{target_topic}，预计 {path['total_estimated_time']} 分钟",
            structured_payload=path,
            confidence=0.8,
            source_agent="planner_agent",
        )
        
        return path
```

#### 2.3 知识图谱基础

```python
# services/api/app/edumem0/knowledge_graph.py

# 简单实现：课程-知识点-依赖关系
# 未来可扩展为 Neo4j 或 NetworkX

DEFAULT_KNOWLEDGE_GRAPH = {
    "kp-optimization": {
        "title": "梯度下降",
        "prerequisites": ["kp-derivatives", "kp-vectors"],
        "difficulty": 0.7,
        "estimated_time": 45,
    },
    "kp-derivatives": {
        "title": "导数",
        "prerequisites": ["kp-limits"],
        "difficulty": 0.5,
        "estimated_time": 30,
    },
    # ... 更多知识点
}
```

---

### 模块3：资源生成闭环（P1）

#### 3.1 扩展 `resource_preference` 为 `resource_generation` 记忆类型

```python
# services/api/app/edumem0/resource_generation.py

from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResourceGenerationRecord:
    """记录资源生成历史，用于后续优化"""
    resource_id: str
    resource_type: str  # "ppt" | "quiz" | "video" | "code" | "image" | "model"
    topic: str
    agent_role: str  # "planner" | "tutor" | "generator" | "evaluator"
    generation_params: dict  # 生成时的参数（如难度、风格、认知风格适配）
    timestamp: datetime
    quality_score: float | None = None  # 后续评估得分
    usage_count: int = 0
    feedback_summary: list[dict] = None  # 用户反馈汇总

class ResourceGenerationTracker:
    def __init__(self, store):
        self.store = store
    
    async def record_generation(self, student_id, resource_record: ResourceGenerationRecord):
        """记录一次资源生成"""
        await self.store.add_memory(
            student_id=student_id,
            memory_type="resource_generation",
            content=f"生成 {resource_record.resource_type}：{resource_record.topic}",
            structured_payload={
                "resource_id": resource_record.resource_id,
                "resource_type": resource_record.resource_type,
                "topic": resource_record.topic,
                "agent_role": resource_record.agent_role,
                "generation_params": resource_record.generation_params,
                "timestamp": resource_record.timestamp.isoformat(),
            },
            confidence=0.9,
            source_agent=resource_record.agent_role,
        )
    
    async def record_feedback(self, student_id, resource_id, feedback_type: str, rating: float):
        """记录用户对资源的反馈"""
        await self.store.add_memory(
            student_id=student_id,
            memory_type="resource_feedback",
            content=f"反馈 {resource_id}：{feedback_type}，评分 {rating}",
            structured_payload={
                "resource_id": resource_id,
                "feedback_type": feedback_type,  # "helpful" | "confusing" | "too_easy" | "too_hard" | "liked" | "disliked"
                "rating": rating,
            },
            confidence=0.8,
            source_agent="user_feedback",
        )
    
    def get_resource_history(self, student_id, resource_type=None, limit=20):
        """获取资源生成历史，用于优化"""
        filters = {"memory_type": "resource_generation"}
        if resource_type:
            filters["resource_type"] = resource_type
        return self.store.search(student_id, filters=filters, limit=limit)
```

#### 3.2 在 Generator Agent 中集成

```python
# services/api/app/agents/generator_agent.py

from app.edumem0.resource_generation import ResourceGenerationTracker

class GeneratorAgent:
    def __init__(self, mem0_client, resource_tracker):
        self.mem0 = mem0_client
        self.tracker = resource_tracker
    
    async def generate_resource(self, student_id, course_id, topic, resource_type):
        # 1. 获取画像（用于适配生成参数）
        profile = self.mem0.get_profile(student_id, course_id)
        
        # 2. 获取历史生成记录（避免重复生成相同内容）
        history = self.tracker.get_resource_history(student_id, resource_type, limit=10)
        
        # 3. 根据认知风格调整生成参数
        generation_params = self._adapt_to_profile(profile, resource_type)
        
        # 4. 生成资源
        resource = await self._generate(topic, resource_type, generation_params)
        
        # 5. 记录生成历史
        await self.tracker.record_generation(student_id, ResourceGenerationRecord(
            resource_id=resource.id,
            resource_type=resource_type,
            topic=topic,
            agent_role="generator",
            generation_params=generation_params,
            timestamp=datetime.now(),
        ))
        
        return resource
```

---

### 模块4：学习效果评估模型（P1）

#### 4.1 新增 `EvaluationModel` 类

```python
# services/api/app/edumem0/evaluation_model.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class EvaluationDimension:
    name: str
    score: float  # 0-1
    weight: float
    evidence: list[str]

@dataclass
class EvaluationReport:
    overall_score: float  # 0-1
    dimensions: list[EvaluationDimension]
    weak_areas: list[str]
    recommendations: list[str]
    trend: str  # "improving" | "stable" | "declining"

class LearningEvaluationModel:
    """综合评估学习效果，输出评估报告"""
    
    def __init__(self, store):
        self.store = store
        self.dimension_weights = {
            "knowledge_mastery": 0.35,
            "learning_activity": 0.20,
            "resource_utilization": 0.15,
            "misconception_elimination": 0.15,
            "path_adherence": 0.15,
        }
    
    async def evaluate(self, student_id: str, course_id: str) -> EvaluationReport:
        """综合评估学习效果"""
        
        # 维度1：知识掌握度（quiz + 练习 + 互动）
        mastery = self._evaluate_mastery(student_id, course_id)
        
        # 维度2：学习活跃度（App 交互 + 会话 + 时间模式）
        activity = self._evaluate_activity(student_id, course_id)
        
        # 维度3：资源利用率（生成资源的使用和反馈）
        utilization = self._evaluate_resource_utilization(student_id, course_id)
        
        # 维度4：误区消除率（misconception 的减少趋势）
        misconception_elimination = self._evaluate_misconception_elimination(student_id, course_id)
        
        # 维度5：路径遵循度（实际学习 vs 规划路径）
        path_adherence = self._evaluate_path_adherence(student_id, course_id)
        
        # 计算总分
        dimensions = [mastery, activity, utilization, misconception_elimination, path_adherence]
        overall_score = sum(d.score * d.weight for d in dimensions)
        
        # 识别薄弱区域
        weak_areas = [d.name for d in dimensions if d.score < 0.5]
        
        # 生成建议
        recommendations = self._generate_recommendations(dimensions, weak_areas)
        
        # 计算趋势（与上次评估对比）
        trend = self._calculate_trend(student_id, course_id, overall_score)
        
        # 将评估报告写入记忆
        await self._save_evaluation(student_id, course_id, overall_score, dimensions, trend)
        
        return EvaluationReport(
            overall_score=overall_score,
            dimensions=dimensions,
            weak_areas=weak_areas,
            recommendations=recommendations,
            trend=trend,
        )
    
    def _evaluate_mastery(self, student_id, course_id) -> EvaluationDimension:
        """评估知识掌握度"""
        mastery_records = self.store.search(
            student_id, memory_types=["mastery"], course_id=course_id
        )
        if not mastery_records:
            return EvaluationDimension("knowledge_mastery", 0.0, 0.35, ["无掌握度记录"])
        
        scores = [m.confidence for m in mastery_records]
        avg_score = sum(scores) / len(scores)
        
        # 计算掌握度分布
        high_mastery = sum(1 for s in scores if s >= 0.8)
        medium_mastery = sum(1 for s in scores if 0.5 <= s < 0.8)
        low_mastery = sum(1 for s in scores if s < 0.5)
        
        evidence = [
            f"已评估 {len(scores)} 个知识点",
            f"高掌握度：{high_mastery}，中掌握度：{medium_mastery}，低掌握度：{low_mastery}",
        ]
        
        return EvaluationDimension("knowledge_mastery", avg_score, 0.35, evidence)
    
    def _evaluate_activity(self, student_id, course_id) -> EvaluationDimension:
        """评估学习活跃度"""
        # 获取最近 30 天的交互记录
        interactions = self.store.search(
            student_id, memory_types=["app_interaction", "session_summary"],
            course_id=course_id, limit=100
        )
        
        if not interactions:
            return EvaluationDimension("learning_activity", 0.0, 0.20, ["无活动记录"])
        
        # 计算活跃天数、平均会话时长、总学习时长
        from collections import defaultdict
        daily_activity = defaultdict(float)
        for interaction in interactions:
            date = interaction.created_at.date()
            # 从 structured_payload 提取时长
            duration = interaction.structured_payload.get("duration_minutes", 0)
            daily_activity[date] += duration
        
        active_days = len(daily_activity)
        total_days = 30
        avg_daily_minutes = sum(daily_activity.values()) / active_days if active_days > 0 else 0
        
        # 活跃度评分：活跃天数比例 * 0.5 + 日均时长评分 * 0.5
        activity_ratio = active_days / total_days
        duration_score = min(avg_daily_minutes / 60, 1.0)  # 假设60分钟为满分
        score = activity_ratio * 0.5 + duration_score * 0.5
        
        evidence = [
            f"近30天活跃 {active_days} 天",
            f"平均每日学习 {avg_daily_minutes:.0f} 分钟",
        ]
        
        return EvaluationDimension("learning_activity", score, 0.20, evidence)
    
    def _evaluate_resource_utilization(self, student_id, course_id) -> EvaluationDimension:
        """评估资源利用率"""
        feedback = self.store.search(
            student_id, memory_types=["resource_feedback"], course_id=course_id, limit=50
        )
        generations = self.store.search(
            student_id, memory_types=["resource_generation"], course_id=course_id, limit=50
        )
        
        if not generations:
            return EvaluationDimension("resource_utilization", 0.0, 0.15, ["无资源生成记录"])
        
        # 计算利用率：有反馈的资源 / 总生成资源
        generated_ids = {g.structured_payload.get("resource_id") for g in generations}
        feedback_ids = {f.structured_payload.get("resource_id") for f in feedback}
        utilized_count = len(generated_ids & feedback_ids)
        utilization_rate = utilized_count / len(generated_ids) if generated_ids else 0
        
        # 计算平均满意度
        if feedback:
            avg_rating = sum(f.structured_payload.get("rating", 0) for f in feedback) / len(feedback)
        else:
            avg_rating = 0
        
        score = utilization_rate * 0.6 + (avg_rating / 5) * 0.4  # 假设评分 5 分制
        
        evidence = [
            f"生成资源 {len(generated_ids)} 个，被使用 {utilized_count} 个",
            f"平均满意度 {avg_rating:.1f}/5",
        ]
        
        return EvaluationDimension("resource_utilization", score, 0.15, evidence)
    
    def _evaluate_misconception_elimination(self, student_id, course_id) -> EvaluationDimension:
        """评估误区消除率"""
        misconceptions = self.store.search(
            student_id, memory_types=["misconception"], course_id=course_id, limit=100
        )
        
        if not misconceptions:
            return EvaluationDimension("misconception_elimination", 1.0, 0.15, ["无记录误区"])
        
        # 按知识点分组，统计误区消除
        # 假设：如果同一个知识点有新的 mastery 记忆且 confidence >= 0.7，认为误区已消除
        misconception_map = {}
        for m in misconceptions:
            kp = m.knowledge_point_id or "unknown"
            misconception_map.setdefault(kp, []).append(m)
        
        eliminated = 0
        for kp, m_list in misconception_map.items():
            # 查找该知识点是否有高掌握度记录
            mastery_records = self.store.search(
                student_id, memory_types=["mastery"], knowledge_point_id=kp, course_id=course_id
            )
            if mastery_records and max(m.confidence for m in mastery_records) >= 0.7:
                eliminated += 1
        
        elimination_rate = eliminated / len(misconception_map) if misconception_map else 0
        
        evidence = [
            f"记录误区 {len(misconception_map)} 个知识点",
            f"已消除 {eliminated} 个，消除率 {elimination_rate:.0%}",
        ]
        
        return EvaluationDimension("misconception_elimination", elimination_rate, 0.15, evidence)
    
    def _evaluate_path_adherence(self, student_id, course_id) -> EvaluationDimension:
        """评估路径遵循度"""
        # 获取规划路径
        paths = self.store.search(
            student_id, memory_types=["learning_path"], course_id=course_id, limit=10
        )
        
        # 获取实际学习轨迹（mastery + learning_event 的时间线）
        actual_events = self.store.search(
            student_id, memory_types=["mastery", "learning_event"], course_id=course_id, limit=100
        )
        
        if not paths or not actual_events:
            return EvaluationDimension("path_adherence", 0.5, 0.15, ["路径或学习记录不足"])
        
        # 简单实现：计算实际学习知识点与规划路径的重合度
        latest_path = paths[0]
        planned_topics = set()
        for stage in latest_path.structured_payload.get("stages", []):
            planned_topics.update(stage.get("topics", []))
        
        actual_topics = {e.knowledge_point_id for e in actual_events if e.knowledge_point_id}
        
        adherence = len(actual_topics & planned_topics) / len(planned_topics) if planned_topics else 0
        
        evidence = [
            f"规划路径包含 {len(planned_topics)} 个知识点",
            f"实际学习 {len(actual_topics)} 个，重合 {len(actual_topics & planned_topics)} 个",
        ]
        
        return EvaluationDimension("path_adherence", adherence, 0.15, evidence)
    
    def _generate_recommendations(self, dimensions: list[EvaluationDimension], weak_areas: list[str]) -> list[str]:
        """根据评估结果生成改进建议"""
        recommendations = []
        
        if "knowledge_mastery" in weak_areas:
            recommendations.append("建议加强核心知识点练习，系统推荐针对性测验")
        if "learning_activity" in weak_areas:
            recommendations.append("学习活跃度较低，建议设定每日学习提醒，每次20-30分钟")
        if "resource_utilization" in weak_areas:
            recommendations.append("生成资源利用率不高，建议反馈资源质量，帮助系统优化推荐")
        if "misconception_elimination" in weak_areas:
            recommendations.append("部分误区尚未消除，建议回顾错题并针对性练习")
        if "path_adherence" in weak_areas:
            recommendations.append("实际学习偏离规划路径，建议重新评估学习目标或调整路径难度")
        
        if not recommendations:
            recommendations.append("学习状态良好，建议继续当前节奏，挑战更高难度内容")
        
        return recommendations
    
    def _calculate_trend(self, student_id, course_id, current_score: float) -> str:
        """计算趋势：与上次评估对比"""
        # 获取上次评估
        previous_evaluations = self.store.search(
            student_id, memory_types=["evaluation"], course_id=course_id, limit=2
        )
        
        if len(previous_evaluations) < 2:
            return "stable"  # 无历史数据
        
        previous_score = previous_evaluations[1].structured_payload.get("overall_score", 0)
        
        diff = current_score - previous_score
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        return "stable"
    
    async def _save_evaluation(self, student_id, course_id, overall_score, dimensions, trend):
        """将评估结果保存为记忆"""
        await self.store.add_memory(
            student_id=student_id,
            memory_type="evaluation",
            content=f"学习效果评估：总分 {overall_score:.0%}，趋势 {trend}",
            structured_payload={
                "overall_score": overall_score,
                "dimensions": [
                    {"name": d.name, "score": d.score, "weight": d.weight, "evidence": d.evidence}
                    for d in dimensions
                ],
                "trend": trend,
            },
            confidence=0.85,
            source_agent="evaluation_model",
        )
```

#### 4.2 在 `evaluator_agent.py` 中集成

```python
# services/api/app/agents/evaluator_agent.py

from app.edumem0.evaluation_model import LearningEvaluationModel

class EvaluatorAgent:
    def __init__(self, mem0_client, evaluation_model):
        self.mem0 = mem0_client
        self.evaluator = evaluation_model
    
    async def evaluate_student(self, student_id, course_id):
        """触发学习效果评估"""
        report = await self.evaluator.evaluate(student_id, course_id)
        
        # 根据评估结果调整路径
        if report.trend == "declining" or report.overall_score < 0.5:
            # 触发路径调整
            await self._adjust_path(student_id, course_id, report)
        
        return report
    
    async def _adjust_path(self, student_id, course_id, report):
        """根据评估结果调整学习路径"""
        # 获取当前路径
        paths = self.mem0.search(
            student_id, memory_types=["learning_path"], course_id=course_id, limit=1
        )
        
        if not paths:
            return
        
        current_path = paths[0].structured_payload
        
        # 根据薄弱区域调整路径
        for weak_area in report.weak_areas:
            if weak_area == "knowledge_mastery":
                # 增加基础复习阶段
                current_path["stages"].insert(0, {
                    "title": "基础巩固（自动调整）",
                    "topics": report.weak_areas[:3],  # 取前3个薄弱知识点
                    "mode": "review",
                    "reason": "评估显示掌握度不足",
                })
            elif weak_area == "misconception_elimination":
                # 增加误区专项训练
                current_path["stages"].append({
                    "title": "误区专项（自动调整）",
                    "topics": [],
                    "mode": "misconception_drill",
                    "reason": "评估显示误区未消除",
                })
        
        # 保存调整后的路径
        await self.mem0.add_memory(
            student_id=student_id,
            memory_type="learning_path",
            content="路径已根据评估结果自动调整",
            structured_payload=current_path,
            confidence=0.8,
            source_agent="evaluator_agent",
        )
```

---

### 模块5：冲突解决策略升级（P1）

#### 5.1 扩展 `conflict_resolver.py`

当前只有 6 对硬编码对抗词，需要升级为 LLM 辅助语义冲突检测。

```python
# services/api/app/edumem0/conflict_resolver.py

class ConflictResolver:
    # 保留原有硬编码对抗词（作为快速路径）
    ANTONYM_PAIRS = [
        ("掌握", "薄弱"),
        ("精通", "困难"),
        ("喜欢", "讨厌"),
        ("理解", "误解"),
        ("熟练", "生疏"),
        ("正确", "错误"),
    ]
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def detect_conflict(self, old_memory: EduMemoryItem, new_memory: EduMemoryItem) -> bool:
        """检测两个记忆是否冲突"""
        
        # 1. 快速路径：硬编码对抗词
        if self._has_antonym_conflict(old_memory.content, new_memory.content):
            return True
        
        # 2. 中等路径：关键词否定检测
        if self._has_negation_conflict(old_memory.content, new_memory.content):
            return True
        
        # 3. 慢速路径：LLM 语义冲突检测（可选）
        if self.llm and self._has_semantic_conflict(old_memory, new_memory):
            return True
        
        return False
    
    def _has_antonym_conflict(self, old_text: str, new_text: str) -> bool:
        """硬编码对抗词检测"""
        for pos, neg in self.ANTONYM_PAIRS:
            if pos in old_text and neg in new_text:
                return True
            if neg in old_text and pos in new_text:
                return True
        return False
    
    def _has_negation_conflict(self, old_text: str, new_text: str) -> bool:
        """否定词检测：如"不再喜欢"与"喜欢""""
        negation_patterns = ["不再", "不", "没", "未", "放弃"]
        for neg in negation_patterns:
            if neg + old_text[:20] in new_text or old_text[:20] + neg in new_text:
                return True
        return False
    
    async def _has_semantic_conflict(self, old: EduMemoryItem, new: EduMemoryItem) -> bool:
        """LLM 语义冲突检测"""
        if not self.llm:
            return False
        
        prompt = f"""判断以下两条记忆是否矛盾：

记忆1（类型：{old.memory_type}，内容：{old.content}）
记忆2（类型：{new.memory_type}，内容：{new.content}）

请回答：是否矛盾？只输出 "yes" 或 "no"。"""
        
        response = await self.llm.generate(prompt)
        return "yes" in response.lower()
    
    def resolve(self, old_memory: EduMemoryItem, new_memory: EduMemoryItem) -> EduMemoryItem:
        """解决冲突：合并或选择置信度更高的"""
        
        if old_memory.confidence >= new_memory.confidence:
            # 保留旧记忆，但添加新记忆为证据
            merged_content = f"{old_memory.content}（更新：{new_memory.content}）"
            return EduMemoryItem(
                **old_memory.__dict__,
                content=merged_content,
                version=old_memory.version + 1,
            )
        else:
            # 新记忆置信度更高，替换
            return EduMemoryItem(
                **new_memory.__dict__,
                version=old_memory.version + 1,
            )
```

---

### 模块6：检索效率升级（P1）

#### 6.1 数据库级查询优化

当前 `search_memories` 加载 200 条再 Python 端过滤，改为数据库级过滤。

```python
# services/api/app/database/postgres_store.py

def search_memories(self, student_id, memory_types=None, course_id=None, 
                    knowledge_point_id=None, tags=None, min_confidence=0.0, 
                    limit=200, order_by="updated_at DESC"):
    """优化：数据库级过滤，避免加载大量数据"""
    
    # 构建 SQL 条件
    conditions = ["student_id = ?"]
    params = [student_id]
    
    if memory_types:
        placeholders = ",".join("?" * len(memory_types))
        conditions.append(f"memory_type IN ({placeholders})")
        params.extend(memory_types)
    
    if course_id:
        conditions.append("course_id = ?")
        params.append(course_id)
    
    if knowledge_point_id:
        conditions.append("knowledge_point_id = ?")
        params.append(knowledge_point_id)
    
    if tags:
        # PostgreSQL 中 tags 是数组，使用 ANY
        placeholders = ",".join("?" * len(tags))
        conditions.append(f"tags && ARRAY[{placeholders}]")
        params.extend(tags)
    
    if min_confidence > 0:
        conditions.append("confidence >= ?")
        params.append(min_confidence)
    
    # 查询时直接过滤，不需要在 Python 端过滤
    sql = f"""
        SELECT * FROM edu_memories
        WHERE {" AND ".join(conditions)}
        ORDER BY {order_by}
        LIMIT ?
    """
    params.append(limit)
    
    rows = self._conn.execute(sql, params).fetchall()
    return [EduMemoryItem.from_row(row) for row in rows]
```

#### 6.2 `embedding` 字段实际化（可选，P2）

如果启用向量搜索，需要接入 `pgvector` 或外部向量服务（如 OpenAI Embedding）。

```python
# 如果启用向量搜索，将 embedding 字段从 None 改为实际向量
# 1. 安装 pgvector 扩展
# 2. 在 edu_memories 表上创建向量索引
# 3. 在 extract 时调用 embedding 模型生成向量
# 4. 在 search 时使用相似度查询
```

---

## 三、修改文件清单

### 后端修改

| 文件 | 修改 | 说明 |
|------|------|------|
| `services/api/app/edumem0/schemas.py` | 新增 `ProfileDimensions` | 6维画像数据模型 |
| `services/api/app/edumem0/extractor.py` | 接入 LLM 辅助提取 | 新增 `extract_with_llm` |
| `services/api/app/edumem0/profile_memory.py` | 支持 6维结构 | 更新 `build_user_profile` |
| `services/api/app/edumem0/path_planner.py` | **新文件** | 路径规划引擎 |
| `services/api/app/edumem0/knowledge_graph.py` | **新文件** | 知识点依赖图 |
| `services/api/app/edumem0/resource_generation.py` | **新文件** | 资源生成追踪器 |
| `services/api/app/edumem0/evaluation_model.py` | **新文件** | 学习效果评估模型 |
| `services/api/app/edumem0/conflict_resolver.py` | 升级 | LLM 语义冲突检测 |
| `services/api/app/edumem0/retriever.py` | 扩展 | 新增 `get_planner_context`、`get_evaluator_context` |
| `services/api/app/edumem0/store.py` | 优化 | 数据库级过滤 |
| `services/api/app/database/postgres_store.py` | 优化 | 数据库级过滤 |
| `services/api/app/agents/planner_agent.py` | 集成 | 调用 `PathPlanner` |
| `services/api/app/agents/generator_agent.py` | 集成 | 调用 `ResourceGenerationTracker` |
| `services/api/app/agents/evaluator_agent.py` | 集成 | 调用 `EvaluationModel` |
| `services/api/app/agents/profile_agent.py` | 更新 | 在 onboarding 中使用 6维提取 |
| `services/api/app/agents/tutor_agent.py` | 更新 | 利用 6维画像生成个性化辅导 |
| `services/api/app/agents/memory_agent.py` | 更新 | 在提取时调用 LLM 辅助 |
| `services/api/app/agents/orchestrator_agent.py` | 更新 | 协调评估和路径调整 |
| `services/api/app/edumem0/preference_memory.py` | 合并 | 功能合并到 `resource_generation.py` |
| `services/api/app/edumem0/misconception_memory.py` | 合并 | 功能合并到 `schemas.py` |
| `services/api/app/edumem0/path_memory.py` | 合并 | 功能合并到 `path_planner.py` |
| `services/api/app/edumem0/app_interaction_memory.py` | 合并 | 功能合并到 `schemas.py` |

### 前端修改

| 文件 | 修改 | 说明 |
|------|------|------|
| `apps/web/src/features/learning-apps/.../ProfileDashboard.tsx` | 更新 | 展示 6维画像雷达图 |
| `apps/web/src/features/learning-apps/.../LearningDashboard.tsx` | 更新 | 展示路径里程碑、评估报告 |
| `apps/web/src/features/learning-apps/.../ResourceCenter.tsx` | 更新 | 展示资源使用状态 |
| `apps/web/src/lib/api/client.ts` | 新增 | 评估 API、路径 API |

---

## 四、实施优先级

| 阶段 | 任务 | 工时 | 说明 |
|------|------|------|------|
| **P0** | 6维画像数据模型 + LLM 提取 | 2h | 核心：更新 schemas.py + extractor.py |
| **P0** | 更新 `profile_memory.py` + `profile_agent.py` | 1h |  onboarding 时生成完整画像 |
| **P0** | 路径规划引擎（骨架） | 2h | `path_planner.py` + `knowledge_graph.py`（基础依赖图） |
| **P0** | 在 `planner_agent.py` 中集成路径规划 | 1h | 替换硬编码路径 |
| **P1** | 资源生成追踪器 | 1.5h | `resource_generation.py` + 在 Generator 中集成 |
| **P1** | 评估模型（骨架） | 2h | `evaluation_model.py` + 5 个维度评估 |
| **P1** | 在 `evaluator_agent.py` 中集成 | 1h | 自动评估 + 路径调整 |
| **P1** | 冲突解决升级 | 1h | LLM 语义冲突检测 |
| **P1** | 检索效率优化 | 1h | 数据库级过滤 |
| **P2** | 前端雷达图（6维画像） | 2h | 画像面板展示 |
| **P2** | 前端评估报告展示 | 2h | 仪表盘新增评估卡片 |
| **P2** | 前端路径里程碑展示 | 1.5h | 学习进度面板 |
| **P2** | 测试覆盖 | 2h | 端到端测试 |
| **P3** | 向量搜索（可选） | 3h | `pgvector` + embedding 接入 |

**总计：约 22 小时（3 天）**

---

## 五、风险与注意事项

| 风险 | 说明 | 缓解方案 |
|------|------|----------|
| **LLM 提取成本** | 每次聊天都调用 LLM 提取画像，成本较高 | 规则式提取优先，LLM 仅在置信度低时触发 |
| **知识图谱维护** | `knowledge_graph.py` 需要手动维护 | 初期硬编码，后期从课程数据自动生成 |
| **评估模型主观性** | 5 个维度的权重是经验值 | 收集真实数据后通过回归分析优化权重 |
| **6维画像隐私** | 包含学习动机、时间模式等敏感信息 | 加密存储，用户可查看/删除自己的画像 |
| **路径规划实时性** | 复杂路径规划可能需要秒级计算 | 预计算 + 缓存，用户触发时直接返回 |
| **数据库级过滤兼容性** | SQLite 和 PostgreSQL 的数组语法不同 | 使用条件编译或抽象层处理差异 |

---

## 六、与原系统的对比

| 维度 | 当前 EduMem0 | 升级后 |
|------|-------------|--------|
| 画像维度 | 3-4维（年级、专业、薄弱点） | 6维完整画像 |
| 提取方式 | 硬编码关键词 | 规则式 + LLM 辅助 |
| 路径规划 | 硬编码 | 基于画像 + 知识图谱动态生成 |
| 资源生成 | 无记录 | 完整追踪 + 反馈闭环 |
| 评估 | 无 | 5维度综合评估 + 动态调整 |
| 冲突检测 | 6对硬编码对抗词 | 对抗词 + 语义冲突检测 |
| 检索 | 加载 200 条 Python 过滤 | 数据库级过滤 |
| 向量搜索 | 字段空转 | 可选启用（pgvector） |

---

## 七、与赛题要求的对应关系

| 赛题要求 | 实现模块 | 文件 |
|----------|----------|------|
| **6维动态画像** | 模块1 | `extractor.py`, `profile_memory.py`, `schemas.py` |
| **多智能体资源生成** | 模块3 | `resource_generation.py`, `generator_agent.py` |
| **个性化路径规划** | 模块2 | `path_planner.py`, `knowledge_graph.py`, `planner_agent.py` |
| **智能辅导（加分）** | 模块1 + 模块2 | `tutor_agent.py` 利用画像和路径 |
| **学习效果评估（加分）** | 模块4 | `evaluation_model.py`, `evaluator_agent.py` |

---

## 八、建议实施顺序

```
第1天：模块1（6维画像）
  ├── 更新 schemas.py（新增 ProfileDimensions）
  ├── 更新 extractor.py（接入 LLM 辅助）
  ├── 更新 profile_memory.py（支持6维）
  └── 更新 profile_agent.py（onboarding 中生成完整画像）

第2天：模块2（路径规划）+ 模块3（资源闭环）
  ├── 新增 path_planner.py + knowledge_graph.py
  ├── 在 planner_agent.py 中集成
  ├── 新增 resource_generation.py
  └── 在 generator_agent.py 中集成

第3天：模块4（评估模型）+ 前端展示
  ├── 新增 evaluation_model.py
  ├── 在 evaluator_agent.py 中集成
  ├── 更新前端仪表盘（雷达图、评估报告、路径里程碑）
  └── 测试
```
