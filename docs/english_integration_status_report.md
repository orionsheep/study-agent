# LearnForge 英语融入项目 — 实施状态报告

> 生成时间：2026-06-17  
> 基于 4 份规划文档和代码库实际审查

---

## 一、规划文档总览

本项目共有 **4 份规划文档**，构成了英语学习融入 LearnForge 的完整蓝图：

| # | 文档 | 核心内容 | 预计工时 |
|---|------|----------|----------|
| 1 | `docs/english_humanities_modules_plan.md` | 总体架构：英语工作区 + 文科笔记本，Dock 三分隔线四区域 | 26.5h |
| 2 | `docs/english_word_fission_integration_plan.md` | english-word-fission 融合详细实施（7 个阶段） | 17h |
| 3 | `docs/english_word_lookup_integration_plan.md` | 全局选词查单词 + 英语工作区联动 | 13h |
| 4 | `docs/immersive_mode_integration_plan.md` | 沉浸式裂变图全屏模式 | 8.5h |

---

## 二、已完成的工作（上次会话）

### ✅ 2.1 类型定义层（阶段 7 — 已完成）

| 文件 | 状态 | 说明 |
|------|------|------|
| `packages/app-protocol/src/types.ts` | ✅ | `CanvasAppType` 已包含 `english.workspace` 和 `humanities.notebook` |
| `services/api/app/schemas/app_protocol.py` | ✅ | `CanvasAppType` Literal 已包含两项 |

### ✅ 2.2 Dock 四区域改造（阶段 4 — 已完成）

| 文件 | 状态 | 说明 |
|------|------|------|
| `apps/web/src/features/app-canvas/pinned.ts` | ✅ | `isSystemModule()` 和 `isRealTimeResource()` 已实现 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | ✅ | Dock 已改为四区域（系统应用 | 系统模块 | 实时资源 | 文件夹），三条 `dock-sep` 分隔线 |
| `apps/web/src/app/styles.css` | ✅ | `.dock-sep` 样式已定义（渐变竖线） |

**关键细节：**
- 系统模块（英语工作区、文科笔记本）在 Dock 上**固定显示**，即使 apps 数组中不存在
- 点击未创建的系统模块会触发 `system_module.create` 事件自动创建
- 实时资源区限制为最近使用的 3 个，避免 Dock 过长

### ✅ 2.3 NativeAppRenderer 渲染分支（阶段 3 — 已完成骨架）

| 文件 | 状态 | 说明 |
|------|------|------|
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | ✅ 骨架 | 图标映射、标签映射、渲染分支均已加入 |

**已实现的骨架组件（内联在 NativeAppRenderer.tsx 中）：**

- `EnglishWorkspaceApp`（第 1334-1417 行）
  - 4 个 Tab：单词列表 / 裂变图 / 测验 / AI 对话
  - 监听 `payload.incoming_word` 变化，自动切换到裂变图 Tab
  - ⚠️ 4 个 Tab 的内容**全部是占位文本**，没有真实功能

- `EnglishChatPanel`（第 1434-1530+ 行）
  - 聊天 UI 已实现（消息列表、输入框、发送按钮）
  - ⚠️ AI 回复是**硬编码占位**（800ms 后显示固定文本），未对接 LearnForge Agent

- `HumanitiesNotebookApp`（第 1420-1431 行）
  - 纯占位："功能开发中，敬请期待"

### ✅ 2.4 SpatialCanvas 元数据

| 文件 | 状态 | 说明 |
|------|------|------|
| `SpatialCanvas.tsx` | ✅ | `appTypeLabel` 含"英语工作区"/"文科笔记本"，`appAccent` 含对应渐变色 |

### ✅ 2.5 全局选词查词（阶段 P0 — 已完成）

| 文件 | 状态 | 说明 |
|------|------|------|
| `apps/web/src/components/selection-toolbar/SelectionToolbar.tsx` | ✅ | 全局选词检测 + 浮动工具条 + "查单词"按钮 |
| `apps/web/src/app/LearnForgeShell.tsx` | ✅ | `handleEnglishLookup` 处理：打开/创建英语工作区并传入 `incoming_word` |
| `LearnForgeShell.tsx` | ✅ | `system_module.create` 事件处理 |
| `LearnForgeShell.tsx` | ✅ | `<SelectionToolbar onLookup={handleEnglishLookup} />` 已挂载 |

### ✅ 2.6 后端 API 代理层（阶段 1 — 已完成）

| 文件 | 状态 | 说明 |
|------|------|------|
| `services/api/app/english_word_service.py` | ✅ 200行 | 代理到 `http://localhost:3011`（english-word-fission 后端） |
| `services/api/app/routes/english_routes.py` | ✅ 149行 | `/api/english` 前缀下 10 个路由端点 |
| `services/api/app/main.py` | ✅ | english_router 已注册 |

**已实现的 API 端点：**
- `GET /api/english/health` — 健康检查
- `GET /api/english/fission` — 裂变图数据
- `GET /api/english/words` — 单词列表
- `GET /api/english/words/{word}` — 单词详情
- `GET /api/english/quiz` — 测验数据
- `POST /api/english/quiz/submit` — 提交测验结果
- `GET /api/english/libraries` — 获取词库
- `POST /api/english/libraries` — 创建词库
- `GET /api/english/study-plan` — 获取学习计划
- `PUT /api/english/study-plan` — 更新学习计划

---

## 三、未完成的工作（需要继续执行）

### ❌ 3.1 前端真实组件（核心功能 — 未开始）

规划中提到的独立目录 `apps/web/src/features/learning-apps/english/` **完全不存在**。以下组件均未创建：

| 组件 | 规划来源 | 状态 | 优先级 |
|------|----------|------|--------|
| `FissionGraph.tsx` | 裂变图（d3-force 力导向图 + 粒子系统） | ❌ 未实现 | P1 |
| `WordList.tsx` | 单词列表（虚拟滚动 + 搜索 + 分组） | ❌ 未实现 | P1 |
| `WordDetail.tsx` | 单词详情（音标、释义、例句） | ❌ 未实现 | P1 |
| `WordNote.tsx` | 单词笔记编辑 | ❌ 未实现 | P2 |
| `QuizPanel.tsx` | 测验面板（拼写/选择/回忆） | ❌ 未实现 | P1 |
| `StudyPlanPanel.tsx` | 学习计划面板 | ❌ 未实现 | P2 |
| `WordLibraryPicker.tsx` | 词库选择器 | ❌ 未实现 | P2 |
| `useEnglishAPI.ts` | API Hook | ❌ 未实现 | P1 |
| `useWordData.ts` | 数据管理 Hook | ❌ 未实现 | P1 |
| `client.ts` | API 客户端 | ❌ 未实现 | P1 |
| `english.ts` | 类型定义 | ❌ 未实现 | P1 |

### ❌ 3.2 AIChatPanel 对接 LearnForge Agent（未实现）

| 项目 | 状态 | 说明 |
|------|------|------|
| 真实 `streamChatMessage` 调用 | ❌ | 当前为硬编码 800ms 后固定回复 |
| SSE 流式渲染 | ❌ | 无 `assistant.delta` 事件处理 |
| `requestedSkill='english_chat'` | ❌ | 未传递 |
| `AbortController` 取消支持 | ❌ | 未实现 |
| Markdown 渲染 | ❌ | 当前为纯文本 |

### ❌ 3.3 EnglishAgent 后端（完全未实现）

| 文件 | 状态 | 说明 |
|------|------|------|
| `services/api/app/agents/english_agent.py` | ❌ 不存在 | 应包含 `handle_chat()`, `recommend_words()`, `generate_quiz()` 等 |
| `orchestrator_agent.py` 注册 | ❌ | 无英语意图检测，无 EnglishAgent 引用 |
| `app_canvas_agent.py` 元数据 | ⚠️ 待验证 | `ICON_BY_APP_TYPE` / `SIZE_BY_APP_TYPE` 是否包含新类型 |

### ❌ 3.4 EduMem0 集成（未实现）

| 项目 | 状态 | 说明 |
|------|------|------|
| 测验记录 → mastery 记忆 | ❌ | `english_word_service.py` 中无 EduMem0 同步 |
| 低分 → misconception 记忆 | ❌ | 未实现 |
| 学习进度 → profile 记忆 | ❌ | 未实现 |
| `EnglishContextRetriever` | ❌ | `edumem0/retriever.py` 中未新增 |
| 对话分析自动记忆 | ❌ | EnglishAgent 不存在，无法实现 |

### ❌ 3.5 沉浸式模式（未实现）

| 项目 | 状态 | 说明 |
|------|------|------|
| `english.setImmersive` 事件处理 | ❌ | 前端发出但 LearnForgeShell 无 handler |
| `ImmersiveView` 组件 | ❌ | 不存在 |
| `FloatingPanel` 可拖拽面板 | ❌ | 不存在 |
| `pageFullscreen` 集成 | ❌ | 未实现 |

### ❌ 3.6 HTML iframe 内选词桥接（未实现）

| 项目 | 状态 | 说明 |
|------|------|------|
| `CustomHtmlAppRenderer` bridge script | ❌ | 未添加 `selectionchange` 监听 |
| `english:lookup` postMessage 桥接 | ❌ | 未实现 |

### ❌ 3.7 docker-compose.yml（未配置）

| 项目 | 状态 | 说明 |
|------|------|------|
| `english-word-fission` 服务 | ❌ | docker-compose.yml 中未添加 |

---

## 四、完成度汇总

| 模块 | 总项 | 已完成 | 未完成 | 完成率 |
|------|------|--------|--------|--------|
| 类型定义 | 2 | 2 | 0 | 100% |
| Dock 改造 | 3 | 3 | 0 | 100% |
| NativeAppRenderer 骨架 | 3 | 3 | 0 | 100% |
| 后端 API 代理层 | 3 | 3 | 0 | 100% |
| 全局选词查词 | 3 | 3 | 0 | 100% |
| 前端真实组件 | 11 | 0 | 11 | 0% |
| AIChatPanel Agent 对接 | 5 | 0 | 5 | 0% |
| EnglishAgent | 3 | 0 | 3 | 0% |
| EduMem0 集成 | 5 | 0 | 5 | 0% |
| 沉浸式模式 | 4 | 0 | 4 | 0% |
| HTML iframe 选词 | 2 | 0 | 2 | 0% |
| docker-compose | 1 | 0 | 1 | 0% |
| **总计** | **45** | **14** | **31** | **31%** |

---

## 五、建议的执行顺序

基于规划文档的优先级和当前完成情况，建议按以下顺序继续：

### 第一批：核心可用（约 8 小时）

1. **提取 `useEnglishAPI` + `client.ts`** (1h) — 前端 API 调用基础
2. **实现 `WordList` 组件** (1.5h) — 虚拟滚动单词列表 + 搜索
3. **实现 `WordDetail` 组件** (1h) — 单词详情面板
4. **实现 `FissionGraph` 组件** (2h) — d3-force 力导向图
5. **实现 `QuizPanel` 组件** (1.5h) — 测验面板
6. **将内联组件拆分到 `english/` 目录** (1h) — 代码整理

### 第二批：Agent 智能（约 4 小时）

7. **AIChatPanel 对接 streamChatMessage** (1.5h) — 真实 AI 回复
8. **创建 `EnglishAgent`** (1.5h) — 英语 Agent 实现
9. **Orchestrator 注册 EnglishAgent** (1h) — 意图检测和路由

### 第三批：记忆系统（约 2 小时）

10. **EduMem0 测验同步** (1h) — mastery/misconception 记忆
11. **EnglishContextRetriever** (1h) — 检索英语记忆上下文

### 第四批：增强体验（约 5 小时）

12. **沉浸式模式** (3h) — ImmersiveView + FloatingPanel
13. **HTML iframe 选词桥接** (1h)
14. **docker-compose 配置** (1h)

**总计剩余约 19 小时（2.5-3 天）**

---

## 六、关键依赖关系

```
useEnglishAPI + client.ts
    ↓
WordList → WordDetail → FissionGraph → QuizPanel
    ↓                                    ↓
    └───────── EnglishWorkspaceApp ───────┘
                      ↓
              AIChatPanel 对接 Agent
                      ↓
              EnglishAgent (后端)
                      ↓
          Orchestrator 注册 + EduMem0 集成
                      ↓
                沉浸模式 + iframe 桥接
```

---

## 七、风险与注意事项

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| d3-force 依赖冲突 | 原项目使用 `react-force-graph-2d`，需检查与 LearnForge 依赖兼容性 | 安装前检查 package.json |
| english-word-fission 后端未启动 | API 代理层会返回 503 | 先启动原项目或 mock 数据 |
| 现有内联组件需拆分 | EnglishWorkspaceApp 目前内联在 NativeAppRenderer.tsx 中（170+ 行） | 拆分时注意保持接口一致 |
| CSS 样式隔离 | 原项目可能使用 Tailwind，与 LearnForge 样式系统冲突 | 使用 CSS Module 或内联样式 |
| AGENTS.md 规则 | 所有 Agent 决策必须由 Hermes 执行，不能用 Python 外部路由 | EnglishAgent 需融入 Hermes 运行时 |
