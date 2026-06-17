# LearnForge 项目记忆系统（EduMem0）状态检查报告

> 检查时间：2026-06-17  
> 检查范围：services/api/app/edumem0/、数据库层、API 路由、Agent/Skill 集成、前端展示、测试覆盖

---

## 一、整体状态：✅ 功能完整，核心链路通畅

EduMem0 是一个面向教育场景的持久化记忆系统，设计灵感来自 Mem0。它支持 12 种记忆类型，具备置信度、衰减、冲突解决策略，已实现从前端事件到后端存储再到检索注入的完整闭环。

---

## 二、架构概览

| 层级 | 核心文件 | 状态 |
|------|----------|------|
| **客户端入口** | `client.py` | ✅ 完整 |
| **数据模型** | `schemas.py` | ✅ 12 种类型已定义 |
| **提取器** | `extractor.py` | ⚠️ 规则式，偏简单 |
| **检索器** | `retriever.py` | ✅ 6 种场景检索 |
| **更新器** | `updater.py` | ✅ 重复+冲突策略 |
| **存储层** | `store.py` + `postgres_store.py` | ✅ 支持 SQLite/Postgres |
| **置信度策略** | `confidence_policy.py` | ✅ 8 种证据类型 |
| **衰减策略** | `decay_policy.py` | ⚠️ 有策略但未实际应用 |
| **冲突解决** | `conflict_resolver.py` | ⚠️ 6 对硬编码词对 |
| **辅助工厂** | `preference_memory.py` / `misconception_memory.py` / `path_memory.py` / `app_interaction_memory.py` | ✅ 完整 |

---

## 三、记忆类型（12 种）

| 类型 | 用途 | 衰减率 |
|------|------|--------|
| profile | 学习画像 | 0.0 |
| mastery | 掌握度 | 0.08 |
| misconception | 误区 | 0.08 |
| resource_preference | 资源偏好 | 0.025 |
| learning_event | 学习事件 | 0.04 |
| learning_path | 学习路径 | 0.025 |
| agent_state | Agent 状态 | 0.04 |
| spatial_layout | 画布布局 | 0.0 |
| app_interaction | App 交互 | 0.04 |
| resource_feedback | 资源反馈 | 0.025 |
| session_summary | 会话摘要 | 0.04 |
| tutor_pedagogy | 导师教学法 | 0.04 |

---

## 四、数据库层

### 表结构
- `edu_memories` 表包含：id, student_id, course_id, knowledge_point_id, memory_type, content, structured_payload, confidence, importance, decay_rate, evidence_type, source_event_id, source_agent, valid_from, valid_until, embedding, tags, version, created_at, updated_at

### 索引
- `idx_edu_memories_student_course` — 学生+课程
- `idx_edu_memories_student_course_type` — 学生+课程+类型
- `idx_edu_memories_student_course_kp` — 学生+课程+知识点
- `idx_edu_memories_student_course_updated` — 学生+课程+更新时间
- `idx_edu_memories_source_event` — 学生+源事件

### 状态
- ✅ 支持 SQLite 和 Postgres 两种后端
- ✅ 有 `ON CONFLICT` 更新逻辑（支持版本递增）
- ⚠️ `embedding` 字段始终为 `None`，**没有向量搜索能力**
- ⚠️ `search_memories` 的实现是**先加载 200 条再 Python 端过滤**，非数据库级查询

---

## 五、API 端点

| 端点 | 方法 | 状态 |
|------|------|------|
| `/api/memory/{student_id}` | GET | ✅ |
| `/api/memory/search` | POST | ✅ |
| `/api/memory/extract-from-chat` | POST | ✅ |
| `/api/memory/app-event` | POST | ✅ |
| `/api/memory/quiz-result` | POST | ✅ |
| `/api/memory/layout-event` | POST | ✅ |
| `/api/memory/resource-feedback` | POST | ✅ |
| `/api/dashboard/{student_id}/memory-evidence` | GET | ✅ |
| `/api/profile/{student_id}` | GET | ✅ 返回画像+证据 |

---

## 六、Agent / Skill 集成

### 6.1 记忆 Agent
- `MemoryAgent` (`agents/memory_agent.py`)：协调 EduMem0，从聊天提取或记录应用事件
- `MemoryUpdateSkill` (`skills/memory_update_skill.py`)：同上，作为 Skill 封装

### 6.2 编排器调用链
- `UnifiedOrchestrator` 在 `profile_agent` 之后调用 `memory_agent`
- 调用被标记为**非致命**（失败不阻塞主流程）
- 在 `capability=chat` 的 plan 中，steps 为 `[---

## 六、Agent / Skill 集成（续）

### 6.2 编排器调用链（续）
- `UnifiedOrchestrator` 在 `profile_agent` 之后调用 `memory_agent`
- 调用被标记为**非致命**（失败不阻塞主流程）
- 在 `capability=chat` 的 plan 中，memory_agent 是标准步骤之一

### 6.3 Tutor 上下文注入
- `build_tutor_context()` 在 `main.py` 中检索 `profile`/`mastery`/`misconception`/`resource_preference` 类型的记忆
- 注入到 `TutorTurnContext.student_memories` 中
- `TutorAgent` 在 `tutor_agent.py` 中**实际使用了这些记忆**：
  - 读取 profile 的 weak_points
  - 检索 mastery/misconception 记忆
  - 生成 `_personal_prefix()` 个性化开场白（如"我记得你的情况——你在数学推导上还需要加强"）
- ✅ **这是记忆系统真正产生价值的地方**

---

## 七、前端集成

### 7.1 记忆状态展示
- `TopBar.tsx`：当 `memoryActive` 为 true 时显示 **"记忆已就绪"** 标签（带 Brain 图标）
- 提示文案："LearnForge 正在根据你的学习记录个性化内容"

### 7.2 Agent 驾驶舱
- `AgentCockpit.tsx`：trace 中包含 `memory` 步骤，但 `shouldShowAgentStep()` 将其**默认隐藏**
- `agentEvents.ts`：`memory.update` 事件会触发 trace 推送 `memory:completed:已记住:xxx`

### 7.3 事件处理
- `applyAgentEvent()` 中 `memory.update` 会设置 `memoryActive: true`
- 让 UI 能感知"它在记住你"

---

## 八、测试覆盖

| 测试文件 | 用例数 | 覆盖场景 |
|----------|--------|----------|
| `test_memory_end_to_end.py` | 4 | 聊天画像提取、App 事件更新、布局空间记忆、测验误区记忆 |
| `test_memory_closed_loop.py` | 6 | 画像提取持久化、重复/冲突策略、资源反馈、上下文检索过滤、语义历史降噪 |
| `test_memory_security_isolation.py` | - | 安全隔离（未读取内容） |

---

## 九、存在的问题与优化建议

### 🔴 高优先级

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **检索效率低** | `postgres_store.py:search_memories` | 数据量大时性能差 | 改为数据库级 SQL 过滤，而非加载 200 条再 Python 过滤 |
| **无向量搜索** | `edu_memories.embedding` | 无法语义检索 | 接入向量数据库（如 pgvector）或至少实现文本相似度索引 |
| **衰减未实际应用** | `decay_policy.py` | 记忆不会随时间贬值 | 在检索时调用 `DecayPolicy.apply()` 计算 effective_confidence |

### 🟡 中优先级

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **提取器过于简单** | `extractor.py` | 只能识别硬编码关键词 | 接入 LLM 提取（如 onboarding_message 中的 `extract_dimensions_with_llm`） |
| **冲突检测太简单** | `conflict_resolver.py` | 只能识别 6 对硬编码对抗词 | 使用 LLM 或语义相似度检测语义冲突 |
| **没有记忆管理 UI** | 前端 | 用户无法查看/编辑记忆 | 新增记忆面板，展示证据链和来源 |
| **AgentCockpit 隐藏 memory** | `AgentCockpit.tsx` | 用户感知不到记忆更新 | 从 shouldShowAgentStep 的隐藏列表中移除 "memory" |

### 🟢 低优先级

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **embedding 字段空转** | schema | 存储浪费 | 要么接入向量，要么移除字段 |
| **记忆类型未全部使用** | 12 种 | 部分设计过剩 | 聚焦实际使用的 5-6 种，其余可标记为预留 |

---

## 十、总结

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构完整性** | ⭐⭐⭐⭐⭐ | 分层清晰，组件齐全 |
| **功能实现** | ⭐⭐⭐⭐ | 12 种类型，策略层都有 |
| **检索效率** | ⭐⭐ | 无向量，Python 端过滤 |
| **前端感知** | ⭐⭐⭐ | TopBar 有提示，但 Cockpit 隐藏 |
| **测试覆盖** | ⭐⭐⭐⭐ | 端到端+闭环+安全 |
| **生产就绪** | ⭐⭐⭐ | 小数据量可用，大数据量需优化检索 |

**一句话：记忆系统的骨架搭得很完整，甚至能跑起来让用户感知到"它在记住你"；但检索效率和智能提取还有明显优化空间。**
