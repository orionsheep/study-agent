# LearnForge 系统自带模块规划：英语工作区 + 文科 Notebook

> 版本：2026-06-17  
> 目标：新增两个系统级核心模块，改造 Dock 为三分隔线四区域布局

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        画布空间 (Canvas)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ 学习画像     │  │ 学习仪表盘   │  │ 资源中心     │  pinned  │
│  │ (pinned)     │  │ (pinned)     │  │ (pinned)     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  用户生成的实时资源窗口（PPT/图片/视频/模型等）            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Dock（三分隔线四区域）                                           │
│  ┌──────────┬──────────┬──────────┬──────────┐                 │
│  │ 左区：   │ 左中区： │ 右中区： │ 右区：   │                 │
│  │ 系统应用 │ 系统模块 │ 生成模块 │ 文件夹   │                 │
│  │          │          │          │          │                 │
│  │ [画像]   │ [文科]   │ [PPT]    │ [📁]     │                 │
│  │ [仪表]   │ [英语]   │ [图解]   │ [📁]     │                 │
│  │ [资源]   │          │ [视频]   │          │                 │
│  │          │          │ [模型]   │          │                 │
│  └──────────┴──────────┴──────────┴──────────┘                 │
│       ↑ sep1    ↑ sep2    ↑ sep3                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、Dock 改造：从单分隔线到三分隔线四区域

### 2.1 当前结构（单分隔线）

```
左侧：pinned apps（3个监控应用）
  │
  ├─ 学习画像
  ├─ 学习仪表盘
  └─ 资源中心
  │
  [dock-sep] ← 单分隔线
  │
右侧：folder apps（用户生成的文件夹）
```

### 2.2 新结构（三分隔线四区域）

```
左区：系统应用（pinned）
  ├─ 学习画像（pinned）
  ├─ 学习仪表盘（pinned）
  └─ 资源中心（pinned）
  │
  [dock-sep 1] ← 第一条分隔线
  │
左中区：系统自带模块
  ├─ 文科笔记本（humanities.notebook）
  └─ 英语工作区（english.workspace）
  │
  [dock-sep 2] ← 第二条分隔线
  │
右中区：实时生成资源
  ├─ PPT 预览（实时生成）
  ├─ 教学图解（实时生成）
  ├─ 教学视频（实时生成）
  └─ 互动演示（实时生成）
  │
  [dock-sep 3] ← 第三条分隔线
  │
右区：folder apps
  └─ 各个文件夹（资源文件夹）
```

### 2.3 分类逻辑

```typescript
// 新增分类函数
function isSystemModule(app: CanvasApp): boolean {
  return app.app_type === "english.workspace" || app.app_type === "humanities.notebook";
}

function isRealTimeResource(app: CanvasApp): boolean {
  const realTimeTypes = new Set([
    "ppt.preview", "image.explanation", "video.script", "video.player", "custom.html"
  ]);
  return realTimeTypes.has(app.app_type as string);
}

// Dock 渲染逻辑
const pinnedApps = apps.filter(isPinnedApp).slice(0, 3);
const systemModules = apps.filter(isSystemModule);
const realTimeApps = apps.filter(a => isRealTimeResource(a) && !isPinnedApp(a) && !isSystemModule(a));
const folderApps = apps.filter(isFolderApp);

// 左区：系统应用（pinned）
// 左中区：系统自带模块
// 右中区：实时生成资源
// 右区：文件夹
```

### 2.4 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | Dock 渲染逻辑改为四区域 |
| `apps/web/src/features/app-canvas/pinned.ts` | 新增 `isSystemModule()` 函数 |
| `apps/web/src/app/styles.css` | 可能需要调整 dock 宽度和间距 |

### 2.5 SpatialCanvas.tsx Dock 渲染代码修改

```tsx
// 在 SpatialCanvas.tsx 中，替换现有 dock 渲染逻辑

// 新增分类函数（可以放在文件顶部或单独文件中）
const SYSTEM_MODULE_TYPES = new Set(["english.workspace", "humanities.notebook"]);
const REALTIME_TYPES = new Set(["ppt.preview", "image.explanation", "video.script", "video.player", "custom.html"]);

function isSystemModule(app: Pick<CanvasApp, "app_type">): boolean {
  return SYSTEM_MODULE_TYPES.has(app.app_type as string);
}

function isRealTimeResource(app: Pick<CanvasApp, "app_type">): boolean {
  return REALTIME_TYPES.has(app.app_type as string) && !isPinnedApp(app) && !isSystemModule(app);
}

// 在 SpatialCanvas.tsx 的 footer 中：
<footer className="app-dock dock glass glass-hi" data-testid="app-dock">
  {(() => {
    const pinnedApps = apps.filter(isPinnedApp).slice(0, 3);
    const systemModules = apps.filter(isSystemModule);
    const realTimeApps = apps.filter(isRealTimeResource);
    const contentApps = [...folderApps]; // 保持原有 folder apps
    
    const renderDockBtn = (app: CanvasApp) => { ... }; // 保持原有
    
    return (
      <>
        {/* 左区：系统应用（pinned） */}
        {pinnedApps.map(renderDockBtn)}
        
        {/* 左中区：系统自带模块 */}
        {systemModules.length > 0 && pinnedApps.length > 0 && (
          <div className="dock-sep" aria-hidden="true" />
        )}
        {systemModules.map(renderDockBtn)}
        
        {/* 右中区：实时生成资源 */}
        {realTimeApps.length > 0 && (pinnedApps.length > 0 || systemModules.length > 0) && (
          <div className="dock-sep" aria-hidden="true" />
        )}
        {realTimeApps.map(renderDockBtn)}
        
        {/* 右区：Folder Apps */}
        {contentApps.length > 0 && (pinnedApps.length > 0 || systemModules.length > 0 || realTimeApps.length > 0) && (
          <div className="dock-sep" aria-hidden="true" />
        )}
        {contentApps.map(renderDockBtn)}
      </>
    );
  })()}
</footer>
```

---

## 三、模块一：英语工作区（english.workspace）

### 3.1 定位

一个专门的英语学习工作区，集成单词学习、语法练习、听力训练、口语对话、阅读材料等功能。与 AI Agent 深度连接，实现个性化英语学习路径。

### 3.2 功能规划

| 功能 | 说明 | 与 Agent 连接 |
|------|------|--------------|
| **单词本** | 单词记忆、复习、测试 | Agent 根据学习记录推荐单词 |
| **语法检查** | 输入句子检查语法错误 | Agent 提供语法讲解和纠正 |
| **听力练习** | 播放音频 + 填空/选择 | Agent 根据难度调整内容 |
| **口语对话** | 语音输入 + AI 对话 | Agent 充当英语对话伙伴 |
| **阅读理解** | 文章 + 问题 | Agent 根据水平推荐文章 |
| **写作练习** | 作文 + AI 批改 | Agent 批改作文并给出建议 |

### 3.3 数据模型（payload）

```typescript
interface EnglishWorkspacePayload {
  // 当前学习模式
  mode: "vocabulary" | "grammar" | "listening" | "speaking" | "reading" | "writing";
  
  // 单词本数据
  vocabulary: {
    wordList: Array<{
      word: string;
      phonetic: string;
      meaning: string;
      example: string;
      mastery: number; // 0-1
      nextReview: string; // ISO date
      tags: string[]; // CET-4, CET-6, TOEFL, etc.
    }>;
    dailyGoal: number; // 每日目标单词数
    todayLearned: number;
  };
  
  // 语法练习记录
  grammar: {
    currentTopic: string;
    exercisesCompleted: number;
    accuracy: number;
    weakPoints: string[];
  };
  
  // 听力练习记录
  listening: {
    currentAudioUrl: string;
    transcript: string;
    questions: Array<{ question: string; options: string[]; correct: number; }>;
    score: number;
  };
  
  // 口语对话记录
  speaking: {
    conversationHistory: Array<{ role: "user" | "agent"; text: string; }>;
    topic: string;
    fluencyScore: number;
  };
  
  // 阅读材料
  reading: {
    currentArticle: {
      title: string;
      content: string;
      difficulty: "easy" | "medium" | "hard";
      questions: Array<{ question: string; answer: string; }>;
    };
  };
  
  // 写作练习
  writing: {
    prompt: string;
    userEssay: string;
    agentFeedback: string;
    score: number;
  };
}
```

### 3.4 前端组件

```tsx
// apps/web/src/features/learning-apps/EnglishWorkspaceApp.tsx

export function EnglishWorkspaceApp({ app, onEvent }: Props) {
  const payload = app.payload as EnglishWorkspacePayload;
  const [mode, setMode] = useState(payload.mode || "vocabulary");
  
  return (
    <div className="english-workspace">
      {/* 顶部模式切换 */}
      <div className="ew-mode-bar">
        {["vocabulary", "grammar", "listening", "speaking", "reading", "writing"].map(m => (
          <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m as any)}>
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      
      {/* 模式内容区 */}
      <div className="ew-content">
        {mode === "vocabulary" && <VocabularyPanel data={payload.vocabulary} onEvent={onEvent} />}
        {mode === "grammar" && <GrammarPanel data={payload.grammar} onEvent={onEvent} />}
        {mode === "listening" && <ListeningPanel data={payload.listening} onEvent={onEvent} />}
        {mode === "speaking" && <SpeakingPanel data={payload.speaking} onEvent={onEvent} />}
        {mode === "reading" && <ReadingPanel data={payload.reading} onEvent={onEvent} />}
        {mode === "writing" && <WritingPanel data={payload.writing} onEvent={onEvent} />}
      </div>
    </div>
  );
}
```

### 3.5 后端 Agent 集成

```python
# services/api/app/agents/english_agent.py

class EnglishAgent:
    """专门处理英语学习相关的 Agent"""
    
    def vocabulary_recommend(self, student_id: str, count: int = 10) -> list[dict]:
        """根据学生记忆推荐单词"""
        # 从 EduMem0 读取学生的英语相关记忆
        memories = self.mem0_client.search(student_id, memory_types=["mastery"], tags=["english"])
        # 根据薄弱点推荐单词
        ...
    
    def grammar_check(self, sentence: str, student_id: str) -> dict:
        """检查语法并给出纠正"""
        # 调用 LLM 进行语法检查
        ...
    
    def generate_listening_material(self, student_id: str, topic: str, difficulty: str) -> dict:
        """生成听力材料"""
        # 生成音频文本 + 问题
        ...
    
    def speaking_conversation(self, student_id: str, message: str, context: list) -> str:
        """口语对话回复"""
        # 作为英语对话伙伴回复
        ...
    
    def essay_feedback(self, essay: str, student_id: str) -> dict:
        """作文批改"""
        # 调用 LLM 批改作文
        ...
```

### 3.6 与 EduMem0 的集成

```python
# 英语相关记忆类型扩展

# mastery: 记录英语各维度掌握度
{
    "memory_type": "mastery",
    "content": "词汇量 3500",
    "structured_payload": {
        "subject": "english",
        "dimension": "vocabulary",
        "score": 0.6
    },
    "tags": ["english", "vocabulary"]
}

# misconception: 记录英语常见错误
{
    "memory_type": "misconception",
    "content": "时态混用：过去完成时和现在完成时区分不清",
    "structured_payload": {
        "subject": "english",
        "grammar_point": "perfect_tenses"
    },
    "tags": ["english", "grammar"]
}

# preference: 记录英语学习偏好
{
    "memory_type": "resource_preference",
    "content": "喜欢通过电影片段学习英语",
    "structured_payload": {
        "subject": "english",
        "preference_type": "learning_style"
    },
    "tags": ["english", "preference"]
}
```

---

## 四、模块二：文科笔记本（humanities.notebook）

### 4.1 定位

类似 NotebookLM 的文科文档处理系统。学生可以上传文科资料（历史文献、文学文本、哲学论文、社会学科材料等），系统会：
- 生成深度摘要和关键概念提取
- 创建问答对话（学生对文档提问）
- 生成播客式音频概览（可选）
- 生成时间线、人物关系图、概念图
- 与 AI Agent 连接进行深度讨论

### 4.2 功能规划

| 功能 | 说明 | 与 Agent 连接 |
|------|------|--------------|
| **文档上传** | 支持 PDF、Word、Markdown、TXT | Agent 自动解析内容 |
| **智能摘要** | 生成多层级摘要（概览/详细） | Agent 生成结构化摘要 |
| **问答对话** | 基于文档内容的 RAG 问答 | Agent 使用文档做上下文 |
| **播客生成** | 生成对话式播客脚本 | Agent 生成双角色对话 |
| **概念图谱** | 提取关键概念并关联 | Agent 生成概念关系图 |
| **时间线** | 提取历史事件时间线 | Agent 生成时间线数据 |
| **人物关系** | 提取人物及其关系 | Agent 生成人物关系图 |
| **对比分析** | 多文档对比分析 | Agent 跨文档分析 |

### 4.3 数据模型（payload）

```typescript
interface HumanitiesNotebookPayload {
  // 当前笔记本信息
  notebook: {
    notebookId: string;
    title: string;
    description: string;
    createdAt: string;
    updatedAt: string;
  };
  
  // 源文档列表
  sources: Array<{
    sourceId: string;
    title: string;
    type: "pdf" | "docx" | "txt" | "md" | "url";
    url: string;
    content: string; // 提取的文本内容
    pageCount: number;
    extractedAt: string;
  }>;
  
  // 生成的摘要
  summaries: Array<{
    summaryId: string;
    sourceIds: string[]; // 基于哪些源文档
    level: "overview" | "detailed" | "deep";
    content: string;
    keyConcepts: string[];
    generatedAt: string;
  }>;
  
  // 问答记录
  qaHistory: Array<{
    qaId: string;
    question: string;
    answer: string;
    sourceRefs: Array<{ sourceId: string; page: number; quote: string; }>;
    createdAt: string;
  }>;
  
  // 播客脚本
  podcasts: Array<{
    podcastId: string;
    title: string;
    script: Array<{ speaker: "host" | "guest"; text: string; }>;
    audioUrl?: string;
    duration: number;
    basedOn: string[]; // sourceIds
    createdAt: string;
  }>;
  
  // 概念图谱
  conceptGraph: {
    nodes: Array<{ id: string; label: string; type: "concept" | "person" | "event" | "place"; }>;
    edges: Array<{ source: string; target: string; relation: string; }>;
  };
  
  // 时间线
  timeline: Array<{
    eventId: string;
    date: string;
    title: string;
    description: string;
    sourceRef: string;
  }>;
  
  // 人物关系
  characters: Array<{
    characterId: string;
    name: string;
    role: string;
    relations: Array<{ targetId: string; relation: string; }>;
  }>;
}
```

### 4.4 前端组件

```tsx
// apps/web/src/features/learning-apps/HumanitiesNotebookApp.tsx

export function HumanitiesNotebookApp({ app, onEvent }: Props) {
  const payload = app.payload as HumanitiesNotebookPayload;
  const [activeTab, setActiveTab] = useState<"sources" | "chat" | "summary" | "podcast" | "graph" | "timeline">("sources");
  
  return (
    <div className="humanities-notebook">
      {/* 左侧边栏：源文档列表 */}
      <div className="hn-sidebar">
        <div className="hn-sources">
          {payload.sources.map(source => (
            <div key={source.sourceId} className="hn-source-item">
              <span className="hn-source-icon">{source.type}</span>
              <span className="hn-source-title">{source.title}</span>
            </div>
          ))}
          <button className="hn-add-source" onClick={() => onEvent(app.app_id, "notebook.add_source", {})}>
            + 添加文档
          </button>
        </div>
      </div>
      
      {/* 右侧主内容区 */}
      <div className="hn-main">
        {/* 顶部标签栏 */}
        <div className="hn-tabs">
          {["sources", "chat", "summary", "podcast", "graph", "timeline"].map(tab => (
            <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab as any)}>
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>
        
        {/* 内容区 */}
        <div className="hn-content">
          {activeTab === "sources" && <SourcesPanel sources={payload.sources} />}
          {activeTab === "chat" && <ChatPanel history={payload.qaHistory} onAsk={(q) => onEvent(app.app_id, "notebook.ask", { question: q })} />}
          {activeTab === "summary" && <SummaryPanel summaries={payload.summaries} />}
          {activeTab === "podcast" && <PodcastPanel podcasts={payload.podcasts} />}
          {activeTab === "graph" && <ConceptGraphPanel graph={payload.conceptGraph} />}
          {activeTab === "timeline" && <TimelinePanel timeline={payload.timeline} />}
        </div>
      </div>
    </div>
  );
}
```

### 4.5 后端 Agent 集成

```python
# services/api/app/agents/humanities_agent.py

class HumanitiesAgent:
    """处理文科文档的 Agent，类似 NotebookLM"""
    
    def __init__(self, mem0_client: EduMem0Client, retriever: CourseRetriever):
        self.mem0 = mem0_client
        self.retriever = retriever
    
    async def process_document(self, notebook_id: str, source_id: str, content: str) -> dict:
        """处理上传的文档，生成摘要、概念图谱、时间线"""
        # 1. 提取关键信息
        summary = await self._generate_summary(content)
        concepts = await self._extract_concepts(content)
        timeline = await self._extract_timeline(content)
        characters = await self._extract_characters(content)
        
        # 2. 存储到 EduMem0
        self.mem0.add_memory(
            student_id=...,
            memory_type="learning_event",
            content=f"上传了文档: {source_id}",
            structured_payload={"notebook_id": notebook_id, "source_id": source_id},
            tags=["humanities", "document_upload"]
        )
        
        return {
            "summary": summary,
            "concepts": concepts,
            "timeline": timeline,
            "characters": characters
        }
    
    async def answer_question(self, notebook_id: str, question: str, source_ids: list[str]) -> dict:
        """基于文档内容回答问题"""
        # 1. 从源文档检索相关内容
        contexts = await self._retrieve_contexts(notebook_id, source_ids, question)
        
        # 2. 调用 LLM 生成答案
        answer = await self._generate_answer(question, contexts)
        
        return {
            "answer": answer,
            "source_refs": contexts
        }
    
    async def generate_podcast(self, notebook_id: str, source_ids: list[str], style: str = "conversational") -> dict:
        """生成播客式对话脚本"""
        # 1. 获取源文档内容
        contents = await self._get_contents(notebook_id, source_ids)
        
        # 2. 生成双角色对话
        script = await self._generate_dialogue(contents, style)
        
        return {
            "script": script,
            "duration_estimate": len(script) * 3  // 每秒约3个字
        }
    
    async def generate_concept_graph(self, notebook_id: str, source_ids: list[str]) -> dict:
        """生成概念图谱"""
        # 提取概念和关系
        ...
    
    async def compare_documents(self, notebook_id: str, source_ids: list[str]) -> dict:
        """多文档对比分析"""
        ...
```

### 4.6 与 EduMem0 的集成

```python
# 文科相关记忆

# learning_event: 记录学习活动
{
    "memory_type": "learning_event",
    "content": "阅读了《中国近代史》第三章",
    "structured_payload": {
        "subject": "humanities",
        "activity_type": "reading",
        "notebook_id": "notebook_xxx",
        "source_id": "source_xxx",
        "duration_minutes": 30
    },
    "tags": ["humanities", "history", "reading"]
}

# mastery: 记录文科知识掌握度
{
    "memory_type": "mastery",
    "content": "辛亥革命 掌握度 0.7",
    "structured_payload": {
        "subject": "humanities",
        "topic": "辛亥革命",
        "sub_subject": "history"
    },
    "tags": ["humanities", "history"]
}

# misconception: 记录文科误区
{
    "memory_type": "misconception",
    "content": "混淆了戊戌变法和义和团运动的时间顺序",
    "structured_payload": {
        "subject": "humanities",
        "topic": "近代史",
        "sub_subject": "history"
    },
    "tags": ["humanities", "history", "timeline"]
}
```

---

## 五、完整修改清单

### 5.1 类型定义层

| 文件 | 修改 |
|------|------|
| `packages/app-protocol/src/types.ts` | `CanvasAppType` 新增 `english.workspace` 和 `humanities.notebook` |
| `services/api/app/schemas/app_protocol.py` | `CanvasAppType` Literal 新增两项 |
| `services/api/app/agents/app_canvas_agent.py` | `ICON_BY_APP_TYPE` 和 `SIZE_BY_APP_TYPE` 新增两项 |

### 5.2 前端渲染层

| 文件 | 修改 |
|------|------|
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | 新增两个 `app_type` 的分支渲染 |
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | `iconMap` 和 `appTypeLabels` 新增两项 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | `appTypeLabel` 函数新增两项 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | `appAccent` 函数新增两项渐变 |
| `apps/web/src/features/learning-apps/EnglishWorkspaceApp.tsx` | **新增** 英语工作区组件 |
| `apps/web/src/features/learning-apps/HumanitiesNotebookApp.tsx` | **新增** 文科笔记本组件 |

### 5.3 Dock 层

| 文件 | 修改 |
|------|------|
| `apps/web/src/features/app-canvas/pinned.ts` | 新增 `isSystemModule()` 和 `isRealTimeResource()` |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | Dock 渲染逻辑改为三区域（左/中/右） |
| `apps/web/src/app/styles.css` | 可能调整 dock 最大宽度 |

### 5.4 后端 Agent 层

| 文件 | 修改 |
|------|------|
| `services/api/app/agents/english_agent.py` | **新增** 英语 Agent |
| `services/api/app/agents/humanities_agent.py` | **新增** 文科 Agent |
| `services/api/app/agents/orchestrator_agent.py` | 注册两个新 Agent |
| `services/api/app/main.py` | 可能需要新增 API 路由 |
| `services/api/app/hermes_runtime/config_writer.py` | 如果需要通过 Hermes 暴露工具，可能需要配置 |

### 5.5 与 EduMem0 集成

| 文件 | 修改 |
|------|------|
| `services/api/app/edumem0/extractor.py` | 从英语/文科交互中提取记忆 |
| `services/api/app/edumem0/retriever.py` | 新增英语/文科相关检索场景 |
| `services/api/app/edumem0/client.py` | 确保新模块能正确调用记忆 API |

### 5.6 测试

| 文件 | 修改 |
|------|------|
| `services/api/tests/test_agents_and_skills.py` | 新增英语/文科 Agent 测试 |

---

## 六、实施优先级

| 优先级 | 任务 | 预计工时 | 影响 |
|--------|------|----------|------|
| **P0** | 扩展 `CanvasAppType` 类型定义 | 0.5h | 全链路基础 |
| **P0** | Dock 改造为三区域 | 1h | UI 立即生效 |
| **P0** | 创建 `EnglishWorkspaceApp` 骨架 + `HumanitiesNotebookApp` 骨架 | 2h | 模块可运行 |
| **P1** | 英语模块核心功能（单词本 + 语法检查） | 4h | 可用 |
| **P1** | 文科模块核心功能（文档上传 + 问答） | 4h | 可用 |
| **P1** | 后端 `EnglishAgent` + `HumanitiesAgent` | 3h | Agent 连接 |
| **P2** | 英语模块扩展（听力、口语、写作） | 4h | 完整 |
| **P2** | 文科模块扩展（播客、概念图、时间线） | 4h | 完整 |
| **P2** | EduMem0 集成（记忆提取和检索） | 2h | 个性化 |
| **P3** | 测试覆盖 | 2h | 质量 |

**总计：约 26.5 小时（3-4 天）**

---

## 七、Dock 视觉示意

### 当前状态（单分隔线）

```
┌────────────────────────────────────────────────────┐
│ [画像] [仪表] [资源] │ [📁历史] [📁文学] [📁哲学]      │
└────────────────────────────────────────────────────┘
         ↑ 单分隔线
```

### 目标状态（双分隔线）

```
┌──────────────────────────────────────────────────────────────┐
│ [画像] [仪表] [资源] │ [PPT] [图解] [视频] │ [文科] [英语] │ [📁] [📁] │
└──────────────────────────────────────────────────────────────┘
         ↑ sep1            ↑ sep2              ↑ sep3
```

**系统自带模块的图标建议**：
- 英语工作区：`Languages` 或 `BookOpen`（lucide-react）
- 文科笔记本：`Library` 或 `ScrollText`（lucide-react）

**渐变颜色建议**：
- 英语工作区：`linear-gradient(135deg, #f59e0b, #ef4444)`（暖色，语言活力）
- 文科笔记本：`linear-gradient(135deg, #8b5cf6, #ec4899)`（紫粉，人文气质）

---

## 八、Agent 连接方式

### 8.1 英语模块的 Agent 连接

```
用户输入："帮我练习一下英语单词"
    ↓
Orchestrator 检测到英语意图
    ↓
调用 EnglishAgent
    ↓
EnglishAgent 从 EduMem0 读取学生英语记忆
    ↓
生成个性化单词列表 + 练习模式
    ↓
创建/更新 english.workspace App
    ↓
通过 SSE 推送到前端
    ↓
前端打开英语工作区，显示单词练习
```

### 8.2 文科模块的 Agent 连接

```
用户输入："上传一篇关于辛亥革命的文章"
    ↓
Orchestrator 检测到文科文档意图
    ↓
调用 HumanitiesAgent
    ↓
HumanitiesAgent 处理文档（提取文本、生成摘要）
    ↓
创建/更新 humanities.notebook App
    ↓
通过 SSE 推送到前端
    ↓
前端打开文科笔记本，显示文档和摘要

后续：
用户输入："这篇文章的核心观点是什么？"
    ↓
HumanitiesAgent 使用文档内容做 RAG 回答
    ↓
更新 notebook 的 qaHistory
    ↓
前端显示问答记录
```

---

## 九、总结

| 维度 | 规划 |
|------|------|
| **新模块** | 2 个（英语工作区 + 文科笔记本） |
| **Dock 改造** | 从单分隔线 → 双分隔线（左/中/右三区域） |
| **新增文件** | 约 10 个（前端组件 + 后端 Agent + 类型定义） |
| **修改文件** | 约 8 个（类型定义、渲染器、Dock、Orchestrator） |
| **预计工时** | 26.5 小时（3-4 天） |
| **核心价值** | 英语：专项学习工具；文科：NotebookLM 式文档智能处理 |
