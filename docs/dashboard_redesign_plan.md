# LearnForge 仪表盘重新规划详细方案

> 版本：2026-06-17  
> 基于截图和代码分析，对三个弃用仪表盘进行重新规划

---

## 一、现状诊断

### 1.1 截图中的三个仪表盘

| 位置 | 类型 | 当前显示 | 核心问题 |
|------|------|----------|----------|
| 左侧 | `profile.dashboard` | 75% 画像覆盖、0 记忆证据、0 薄弱点 | 数据聚合缺失，展示与数据脱节 |
| 中间 | `dashboard.learning` | 路径进度 0%、平均掌握 30%、记忆证据 12 | `path_progress` 未计算，路径是硬编码 |
| 右侧 | `resource.center` | 92 资源、8 模块、引用覆盖 100% | 相对正常，但无学习状态关联 |

### 1.2 根因分析

**问题1：store.dashboard() 数据聚合不完整**

```python
# services/api/app/database/store.py
def dashboard(self, student_id, course_id, conversation_id):
    profile = self.get_profile(student_id, course_id=course_id)
    mastery_rows = self.fetchall("SELECT ... FROM mastery_records ...")
    mastery = {row["knowledge_point_id"]: row["mastery_score"] for row in mastery_rows}
    raw_weak_points = profile.get("weak_points", [])  # ← 可能为空
    weak_points = raw_weak_points if isinstance(raw_weak_points, list) else []
    memories = self.list_memories(student_id, course_id=course_id, limit=12)
    apps = self.fetchall("SELECT ... FROM canvas_apps ...")
    
    return DashboardSnapshot(
        student_id=student_id,
        profile=profile,
        mastery=mastery,
        weak_points=weak_points,  # ← 可能为空
        memory_evidence=memories,  # ← 有12条，但前端只展示 profile 类型
        path_progress=0,  # ← 始终为0，未计算
        recommendations=[],  # ← 始终为空
        recent_runs=[],  # ← 始终为空
    )
```

**问题2：ProfileDashboard 前端过滤过窄**

```tsx
// apps/web/src/features/learning-apps/NativeAppRenderer.tsx
const profileEvidence = evidence.filter((item) => item.memory_type === "profile");
```

`evidence` 中有 12 条记忆，但只过滤 `profile` 类型，导致显示为 0。

**问题3：LearningPathApp 路径硬编码**

```tsx
const stages = [
  { id: "stage-math", title: "补齐数学推导基础", progress: 38, status: "进行中" },
  { id: "stage-opt", title: "梯度下降与学习率", progress: 42, status: "推荐" },
  { id: "stage-nn", title: "神经网络训练闭环", progress: 25, status: "锁定" }
];
```

路径不是动态生成的，进度也是写死的。

**问题4：薄弱点展示逻辑不一致**

- 画像面板：`dashboard?.weak_points?.length` → 来自 `profile.weak_points`
- 仪表盘面板：`dashboard?.weak_points?.length` → 同样来源
- 但 `misconception` 类型的记忆存储在 `edu_memories` 表中，没有被展示

---

## 二、重新规划方案

### 2.1 仪表盘结构重组

保留 **3 个面板**，但重新定位：

| 面板 | 类型 | 定位 | 数据职责 |
|------|------|------|----------|
| **学习画像** | `profile.dashboard` | 我是谁（静态画像） | profile + 6维特征 + 证据链 |
| **学习进度** | `dashboard.learning` | 我学到哪了（动态追踪） | mastery + 路径 + 薄弱点 + 活动 |
| **资源中心** | `resource.center` | 我该学什么（资源推荐） | 资源库 + 学习状态标记 + 引用 |

**删除/合并：**
- `LearningPathApp`（学习路径）的硬编码 stages → 整合到 `dashboard.learning` 中作为"路径里程碑"区域
- `KnowledgeGraphApp`（知识图谱）的静态 SVG → 保留但改为动态加载 `app.payload.nodes`

### 2.2 详细修改清单

#### P0 — 数据修复（必须先做，否则面板无数据）

**修改1：store.dashboard() 完整数据聚合**

文件：`services/api/app/database/store.py`

```python
def dashboard(self, student_id, course_id, conversation_id):
    profile = self.get_profile(student_id, course_id=course_id)
    
    # 1. 掌握度：从 mastery_records 表 + edu_memories mastery 类型
    mastery_rows = self.fetchall(
        "SELECT knowledge_point_id, mastery_score FROM mastery_records WHERE student_id=? AND course_id=?",
        (student_id, course_id)
    )
    mastery = {row["knowledge_point_id"]: row["mastery_score"] for row in mastery_rows}
    
    # 2. 薄弱点：从 edu_memories misconception 类型（比 profile.weak_points 更可靠）
    misconception_memories = self.search_memories(
        student_id, memory_types=["misconception"], course_id=course_id, limit=10
    )
    weak_points = [
        m.structured_payload.get("misconception_tags", [m.content[:20]])[0]
        for m in misconception_memories
    ]
    # 兜底：如果 misconception 为空，再用 profile.weak_points
    if not weak_points:
        raw = profile.get("weak_points", [])
        weak_points = raw if isinstance(raw, list) else []
    
    # 3. 记忆证据：全部 12 种类型，不限于 profile
    all_memories = self.list_memories(student_id, course_id=course_id, limit=30)
    
    # 4. 路径进度：计算实际进度（已掌握知识点 / 总知识点）
    total_kps = len(mastery)
    mastered_kps = sum(1 for v in mastery.values() if v >= 0.6)
    path_progress = mastered_kps / total_kps if total_kps > 0 else 0
    
    # 5. 学习活动：从 canvas_apps 表读取最近交互
    apps = self.fetchall(
        "SELECT app_type, title, updated_at FROM canvas_apps WHERE student_id=? ORDER BY updated_at DESC LIMIT 8",
        (student_id,)
    )
    canvas_activity = [{"type": row["app_type"], "title": row["title"], "at": row["updated_at"]} for row in apps]
    
    # 6. 推荐：从 learning_path 记忆生成
    path_memories = self.search_memories(
        student_id, memory_types=["learning_path"], course_id=course_id, limit=5
    )
    recommendations = [
        {"title": m.content, "reason": "基于学习路径推荐", "score": m.confidence}
        for m in path_memories
    ]
    
    return DashboardSnapshot(
        student_id=student_id,
        profile=profile,
        mastery=mastery,
        weak_points=weak_points,
        memory_evidence=all_memories,  # 全部30条，不限类型
        path_progress=path_progress,  # 实际计算值
        canvas_activity=canvas_activity,
        recommendations=recommendations,
    )
```

**修改2：DashboardSnapshot 扩展字段**

文件：`services/api/app/schemas/app_protocol.py`

```python
class DashboardSnapshot(BaseModel):
    student_id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    mastery: dict[str, float] = Field(default_factory=dict)
    weak_points: list[str] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    memory_evidence: list[EduMemoryItem] = Field(default_factory=list)
    canvas_activity: list[dict[str, Any]] = Field(default_factory=list)  # 新增
    activity_calendar: list[dict[str, Any]] = Field(default_factory=list)  # 新增：学习活动日历
    path_progress: float = 0
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    
    # 新增：赛题要求的6维画像结构
    profile_dimensions: dict[str, Any] = Field(default_factory=dict)  # 知识基础/认知风格/易错点/动机/时间/交互
    evaluation_score: float | None = None  # 综合评估得分
```

**修改3：ProfileDashboard 证据展示修复**

文件：`apps/web/src/features/learning-apps/NativeAppRenderer.tsx`

```tsx
// 旧：只过滤 profile 类型
const profileEvidence = evidence.filter((item) => item.memory_type === "profile");

// 新：展示所有与画像相关的证据类型
const profileEvidence = evidence.filter((item) =>
  ["profile", "misconception", "mastery", "resource_preference"].includes(item.memory_type)
);
```

同时，将"薄弱点"的数据源改为从 `dashboard.weak_points` 读取（后端已修复）。

#### P1 — 前端展示增强

**修改4：ProfileDashboard 新增6维画像展示**

在现有"画像维度"区域基础上，增加一个可视化区域：

```tsx
// 新增：6维雷达图（用 CSS/SVG 实现）
function ProfileRadarChart({ dimensions }: { dimensions: Record<string, number> }) {
  // 6个维度：知识基础、认知风格、易错点、学习动机、时间模式、交互偏好
  // 每个维度 0-100 分
  // 用 SVG 多边形绘制雷达图
}
```

**修改5：LearningDashboardApp 新增掌握热力图**

在"知识点掌握度"进度条基础上，改为热力图：

```tsx
// 新增：掌握热力图
function MasteryHeatmap({ mastery }: { mastery: Record<string, float> }) {
  // 将知识点按课程模块分组
  // 每个知识点用色块表示：绿色(>=0.7)、黄色(0.4-0.7)、红色(<0.4)
  // 点击可展开详情
}
```

**修改6：LearningDashboardApp 新增路径里程碑**

替换原来的硬编码 `LearningPathApp`，改为从后端动态读取：

```tsx
// 从 dashboard 读取 path_progress 和 canvas_activity
// 展示：已完成里程碑、当前里程碑、下一个里程碑
// 里程碑从 learning_path 记忆中提取
```

**修改7：ResourceCenterApp 新增学习状态标记**

在资源列表中增加状态标记：

```tsx
// 每个资源旁边显示：已学/在学/未学/推荐
// 状态从 app_interaction 记忆和 mastery 记录推断
// 已学 = 有交互记录且掌握度 >= 0.6
// 在学 = 有交互记录但掌握度 < 0.6
// 未学 = 无交互记录
// 推荐 = 系统推荐但未学
```

**修改8：LearningDashboardApp 新增学习活动日历图（Activity Calendar）**

参照 GitHub Contribution Graph 风格，展示学习活动强度：

```tsx
// 新增：学习活动日历图
function ActivityCalendar({
  data,
  viewMode = "daily" // "daily" | "weekly" | "cumulative"
}: {
  data: ActivityDay[];
  viewMode?: string;
}) {
  // 展示最近一年的学习活动
  // 每个方块 = 一天，颜色深浅 = 活动强度
  // 活动强度计算：会话时长 + App 交互 + 测验 + 记忆更新
  // 颜色方案：浅色(0) → 中浅(1-2) → 中等(3-5) → 深色(6-10) → 最深(>10)
}

interface ActivityDay {
  date: string;        // "2025-06-17"
  intensity: number;   // 0-10+，活动强度
  events: ActivityEvent[];  // 当天具体事件列表
}

interface ActivityEvent {
  type: "session" | "quiz" | "app_open" | "memory_update" | "resource_view";
  title: string;
  duration_minutes?: number;
  score?: number;
}
```

**前端实现要点：**
- 用 CSS Grid 实现 7 行（周一~周日）× 53 列（周）的网格布局
- 每个方块 10px×10px，间距 2px
- 悬停显示 tooltip：日期 + 当日事件摘要
- 右上角切换视图：每日/每周/累计
- 图例：颜色等级说明

**后端数据聚合：**

```python
# services/api/app/database/store.py 中 dashboard() 扩展

def _get_activity_calendar(self, student_id, course_id, days=365):
    """获取过去一年的每日学习活动强度"""
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=days)
    
    # 1. 会话活动（从 session_summary 记忆）
    session_memories = self.search_memories(
        student_id,
        memory_types=["session_summary"],
        course_id=course_id,
        limit=200
    )
    
    # 2. App 交互（从 canvas_apps 表）
    app_rows = self.fetchall(
        "SELECT app_type, updated_at FROM canvas_apps WHERE student_id=? AND updated_at >= ?",
        (student_id, start.isoformat())
    )
    
    # 3. 测验记录（从 quiz_results 或 eval_sessions 表）
    quiz_rows = self.fetchall(
        "SELECT score, completed_at FROM quiz_results WHERE student_id=? AND completed_at >= ?",
        (student_id, start.isoformat())
    )
    
    # 4. 记忆更新（从 edu_memories 表）
    memory_rows = self.fetchall(
        "SELECT memory_type, created_at FROM edu_memories WHERE student_id=? AND created_at >= ?",
        (student_id, start.isoformat())
    )
    
    # 按日期聚合
    calendar = {}
    for day in range(days):
        date = (end - timedelta(days=day)).strftime("%Y-%m-%d")
        calendar[date] = {"intensity": 0, "events": []}
    
    # 聚合会话时长
    for m in session_memories:
        date = m.created_at.strftime("%Y-%m-%d") if hasattr(m.created_at, 'strftime') else str(m.created_at)[:10]
        if date in calendar:
            duration = m.structured_payload.get("duration_minutes", 30)
            calendar[date]["intensity"] += min(duration / 10, 3)  # 每10分钟=1强度，上限3
            calendar[date]["events"].append({"type": "session", "title": f"学习会话 {duration}分钟"})
    
    # 聚合 App 交互
    for row in app_rows:
        date = str(row["updated_at"])[:10]
        if date in calendar:
            calendar[date]["intensity"] += 1
            calendar[date]["events"].append({"type": "app_open", "title": f"使用 {row['app_type']}"})
    
    # 聚合测验
    for row in quiz_rows:
        date = str(row["completed_at"])[:10]
        if date in calendar:
            calendar[date]["intensity"] += 2
            score = row.get("score", 0)
            calendar[date]["events"].append({"type": "quiz", "title": f"完成测验 得分{score}", "score": score})
    
    # 聚合记忆更新
    for row in memory_rows:
        date = str(row["created_at"])[:10]
        if date in calendar:
            calendar[date]["intensity"] += 0.5
            calendar[date]["events"].append({"type": "memory_update", "title": f"更新记忆: {row['memory_type']}"})
    
    return [
        {"date": date, "intensity": round(data["intensity"]), "events": data["events"]}
        for date, data in sorted(calendar.items())
    ]
```

**颜色方案（适配 light theme）：**

```css
/* 浅色主题下的活动日历颜色 */
.activity-cell {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background-color: #ebedf0;  /* 强度0：无活动 */
}
.activity-cell.intensity-1 { background-color: #9be9a8; }  /* 浅绿 */
.activity-cell.intensity-2 { background-color: #40c463; }  /* 中绿 */
.activity-cell.intensity-3 { background-color: #30a14e; }  /* 深绿 */
.activity-cell.intensity-4 { background-color: #216e39; }  /* 最深绿 */
.activity-cell.intensity-5 { background-color: #0e4429; }  /* 超深 */
```

**放置位置：** 建议放在 `dashboard.learning`（学习进度）面板中，作为"学习活动概览"区域，放在"掌握热力图"上方或并列。

#### P2 — 新增系统应用（可选）

**修改8：新增"学习效果评估"面板（加分项）**

类型：`evaluation.overview`

展示内容：
- 综合评估得分（从 mastery + quiz + interaction 计算）
- 最近测验成绩趋势图
- 学习时间分布（从 session_summary 记忆推断）
- 误区消除进度（misconception 的 confidence 变化）

**修改9：新增"学习活动时间线"面板**

类型：`activity.timeline`

展示内容：
- 按时间倒序展示所有学习活动
- 包括：打开 App、完成测验、查看资源、提交笔记
- 数据来源：`canvas_activity` + `memory_evidence`

---

## 三、实施步骤

### 阶段1：数据修复（1-2天）

1. 修改 `store.dashboard()` 完整聚合数据
2. 扩展 `DashboardSnapshot` 字段
3. 确保 `list_memories()` 返回正确类型数据
4. 测试 `/api/dashboard/{student_id}` 返回数据完整性

### 阶段2：前端修复（1-2天）

1. 修复 `ProfileDashboard` 证据过滤逻辑
2. 修复薄弱点展示（从 `dashboard.weak_points` 读取）
3. 修复 `LearningDashboardApp` 的 `path_progress` 展示
4. 删除 `LearningPathApp` 的硬编码 stages（改为从 dashboard 读取）

### 阶段3：展示增强（2-3天）

1. 画像面板：6维雷达图
2. 进度面板：掌握热力图
3. **进度面板：学习活动日历图（Activity Calendar）**
4. 进度面板：路径里程碑
5. 资源面板：学习状态标记

### 阶段4：新增面板（可选，1-2天）

1. 学习效果评估面板
2. 学习活动时间线面板

---

## 四、数据源映射表

| 面板 | 展示字段 | 后端数据源 | 数据表/记忆类型 |
|------|----------|----------|----------------|
| 学习画像 | 画像覆盖 | `profile` 表 | `user_profiles` |
| 学习画像 | 记忆证据链 | `memory_evidence` | `edu_memories` (全部类型) |
| 学习画像 | 薄弱点 | `weak_points` | `edu_memories` (misconception) |
| 学习画像 | 科目置信度 | `mastery` | `mastery_records` |
| 学习进度 | 路径进度 | `path_progress` | `mastery_records` 计算 |
| 学习进度 | 平均掌握 | `mastery` | `mastery_records` |
| 学习进度 | 知识点掌握度 | `mastery` | `mastery_records` |
| 学习进度 | 当前薄弱点 | `weak_points` | `edu_memories` (misconception) |
| 学习进度 | 智能推荐 | `recommendations` | `edu_memories` (learning_path) |
| 学习进度 | 最近活动 | `canvas_activity` | `canvas_apps` |
| **学习进度** | **活动日历图** | **`activity_calendar`** | **综合：`session_summary` + `canvas_apps` + `quiz_results` + `edu_memories`** |
| 资源中心 | 资源列表 | `resources` | `resources` 表 |
| 资源中心 | 模块/标签 | `modules` / `tags` | `resources` 表 |
| 资源中心 | 引用覆盖 | `sourceRefs` | `resources` 表 |
| 资源中心 | 学习状态 | 推断 | `edu_memories` (app_interaction) + `mastery_records` |

---

## 五、一句话总结

> **三个仪表盘的核心问题是"前端展示正常，但后端数据聚合不完整"。`store.dashboard()` 是最关键的修复点——它目前只聚合了 profile、mastery 和 memory，但缺失了 path_progress 计算、weak_points 从 misconception 读取、canvas_activity 聚合。修复数据层后，前端只需做展示优化（雷达图、热力图、状态标记）。**
