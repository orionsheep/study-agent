# english-word-fission 融合进 LearnForge 英语工作区 — 详细规划

> 版本：2026-06-17  
> 背景：用户有一个完整的 `english-word-fission` 项目（Next.js + Prisma + 1.45GB 单词数据），需要将其融合为 LearnForge 的英语工作区模块。  
> 文科笔记本（humanities.notebook）暂时只占位，后续开发。

---

## 一、english-word-fission 项目结构分析

### 1.1 项目概况

| 属性 | 值 |
|------|-----|
| **框架** | Next.js 16 + React 19 + TypeScript |
| **数据库** | Prisma + PostgreSQL (`LPT_english` schema) |
| **数据** | 1.45GB（CSV 词典 + 裂变关联数据） |
| **运行端口** | 3011 |
| **核心可视化** | d3-force 力导向图（react-force-graph-2d） |
| **虚拟滚动** | @tanstack/react-virtual |
| **多语言** | next-intl（zh/en） |

### 1.2 核心数据层

**文件数据（1.45GB，不依赖数据库）：**

| 文件 | 内容 | 大小 |
|------|------|------|
| `data/word_fission_data.csv` | 单词裂变关联（同义词、反义词、派生词） | 大 |
| `data/ecdict_extracted.csv` | ECDICT 词典（音标、释义、翻译、Collins 级别、BNC/FRQ 频率） | 大 |
| `data/word_text_database/` | 单词文本数据库 | 中 |
| `data/word_library/` | 系统词库 | 中 |

**数据库表（`LPT_english` schema）：**

| 表 | 用途 |
|----|------|
| `User` | 用户（email, preferredLanguage, role） |
| `QuizRecord` | 测验记录（word, testType, score, timestamp） |
| `StudyPlan` | 学习计划（dailyGoal） |
| `UserLibrary` | 用户自定义词库 |
| `UserLibraryWord` | 词库中的单词 |
| `WordVisit` | 单词访问记录 |
| `word_notes` | 单词笔记 |
| `chat_sessions` | ~~AI 聊天会话（废弃，统一用 LearnForge Agent 系统）~~ |
| `chat_messages` | ~~AI 聊天消息（废弃，统一用 LearnForge Agent 系统）~~ |
| `note_interactions` | 笔记交互 |

### 1.3 核心 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/fission?word=xxx` | GET | 获取单词裂变图数据（nodes + links） |
| `/api/words?query=xxx&includeDefinitions=true` | GET | 获取单词列表（支持搜索） |
| `/api/words/[word]` | GET | 获取单词详情 |
| `/api/quiz/data` | POST | 获取测验数据（批量单词） |
| `/api/quiz/words` | GET | 获取测验单词列表 |
| `/api/quiz/record` | POST | 记录测验结果 |
| `/api/libraries` | GET | 获取系统词库 |
| `/api/library-groups` | GET | 获取词库分组 |
| `/api/user/progress` | GET | 获取用户学习进度 |
| `/api/user/libraries/*` | GET/POST | 用户自定义词库管理 |

### 1.4 核心前端组件

| 组件 | 功能 | 复杂度 |
|------|------|--------|
| `FissionGraph` | d3-force 力导向图 + 粒子系统 + 可配置参数 | 高 |
| `WordList` | 虚拟滚动单词列表 + 搜索 + 分组 | 中 |
| `WordDetail` | 单词详情面板（音标、释义、例句） | 中 |
| `WordTooltip` | 悬停提示 | 低 |
| `WordNote` | 单词笔记编辑 | 低 |
| `~~AIChatWindow~~` | ~~AI 聊天窗口（废弃，统一用 LearnForge Agent）~~ | — |
| `ThreeColumnLayout` | 三列布局（列表 + 详情 + 图） | 中 |
| `PanelFissionGraph` | 面板式裂变图 | 中 |
| 测验组件 | 拼写/选择/回忆三种模式 | 中 |
| `ImmersiveToggle` | 沉浸式模式切换 | 低 |
| `FullscreenButton` | 全屏按钮 | 低 |
| `LoginModal` / `SettingsModal` | 登录/设置 | 中 |
| `SettingsContext` | 全局设置（语言、主题、布局等） | 中 |

---

## 二、融合方案设计

### 2.1 核心原则

1. **数据不动**：1.45GB 的 CSV 数据保留在原项目，不迁移
2. **后端独立**：english-word-fission 继续作为独立服务运行（端口 3011）
3. **前端融合**：提取核心组件到 LearnForge 的 `EnglishWorkspaceApp`
4. **记忆互通**：测验记录、学习进度同步到 EduMem0
5. **统一认证**：LearnForge 的 `student_id` 映射到 english-word-fission 的 `user_id`

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     LearnForge 前端                         │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              EnglishWorkspaceApp                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │  │
│  │  │ 单词列表  │  │ 单词详情  │  │  裂变图（力导向）   │  │  │
│  │  │ (虚拟滚动)│  │ + 笔记   │  │  + 粒子效果        │  │  │
│  │  └──────────┘  └──────────┘  └────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  AI 聊天窗口（对接 LearnForge Agent）           │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  测验面板（拼写/选择/回忆）                    │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                         ↑                                   │
│  ┌──────────────────────┴──────────────────────────┐       │
│  │  LearnForge API（Python FastAPI）                │       │
│  │  ┌─────────────────────────────────────────┐    │       │
│  │  │ english_word_service.py（API 代理层）     │    │       │
│  │  │  - 转发单词查询 → english-word-fission    │    │       │
│  │  │  - 同步测验记录 → EduMem0                 │    │       │
│  │  │  - 认证映射：student_id ↔ user_id         │    │       │
│  │  └─────────────────────────────────────────┘    │       │
│  └──────────────────────────────────────────────────┘       │
│                         ↑                                   │
├─────────────────────────┼───────────────────────────────────┤
│                         │ API 调用                             │
│  ┌──────────────────────┴──────────────────────────┐          │
│  │  english-word-fission（Next.js，端口 3011）     │          │
│  │  ┌─────────────────────────────────────────┐    │          │
│  │  │ 文件数据（1.45GB CSV）                   │    │          │
│  │  │  - word_fission_data.csv                 │    │          │
│  │  │  - ecdict_extracted.csv                  │    │          │
│  │  │  - word_text_database/                   │    │          │
│  │  └─────────────────────────────────────────┘    │          │
│  │  ┌─────────────────────────────────────────┐    │          │
│  │  │ PostgreSQL 数据库（LPT_english schema）   │    │          │
│  │  │  - QuizRecord、StudyPlan、UserLibrary      │    │          │
│  │  │  - word_notes ~~（chat_sessions 废弃）~~     │    │          │
│  │  └─────────────────────────────────────────┘    │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                │
│  ┌──────────────────────────────────────────────────┐          │
│  │  EduMem0（LearnForge 记忆系统）                    │          │
│  │  - 从测验记录提取 mastery 记忆                     │          │
│  │  - 从学习进度提取 preference 记忆                 │          │
│  │  - 从笔记提取 learning_event 记忆                  │          │
│  └──────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、具体实施步骤

### 阶段 1：后端 API 代理层（P0，约 2 小时）

#### 3.1.1 创建 `services/api/app/english_word_service.py`

```python
"""
English Word Service Proxy
将 english-word-fission 的 API 封装为 LearnForge 可用的服务
"""

import os
import httpx
from typing import Optional

# english-word-fission 服务地址
EFW_BASE_URL = os.environ.get("EFW_BASE_URL", "http://localhost:3011")
_efw_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _efw_client
    if _efw_client is None:
        _efw_client = httpx.AsyncClient(base_url=EFW_BASE_URL, timeout=30.0)
    return _efw_client


class EnglishWordService:
    """封装 english-word-fission 的 API"""
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        # 学生 ID 映射到 english-word-fission 的用户 ID
        # 如果没有映射，自动创建用户
        self.efw_user_id = self._resolve_user_id(student_id)
    
    def _resolve_user_id(self, student_id: str) -> str:
        """将 LearnForge 的 student_id 映射到 english-word-fission 的 user_id"""
        # 方案：使用 student_id 的哈希或前缀
        # 也可以在 LearnForge 数据库中维护映射表
        return f"learnforge_{student_id}"
    
    async def get_fission_data(self, word: str) -> dict:
        """获取单词裂变图数据"""
        client = _get_client()
        resp = await client.get("/api/fission", params={"word": word})
        resp.raise_for_status()
        return resp.json()
    
    async def get_word_list(self, query: str = "", include_definitions: bool = False) -> list:
        """获取单词列表"""
        client = _get_client()
        resp = await client.get("/api/words", params={
            "query": query,
            "includeDefinitions": str(include_definitions).lower()
        })
        resp.raise_for_status()
        return resp.json()
    
    async def get_word_detail(self, word: str) -> dict:
        """获取单词详情"""
        client = _get_client()
        resp = await client.get(f"/api/words/{word}")
        resp.raise_for_status()
        return resp.json()
    
    async def get_quiz_data(self, words: list[str]) -> list:
        """获取测验数据"""
        client = _get_client()
        resp = await client.post("/api/quiz/data", json={"words": words})
        resp.raise_for_status()
        return resp.json()
    
    async def record_quiz(self, word: str, test_type: int, score: int) -> dict:
        """记录测验结果，并同步到 EduMem0"""
        client = _get_client()
        resp = await client.post("/api/quiz/record", json={
            "userId": self.efw_user_id,
            "word": word,
            "testType": test_type,
            "score": score
        })
        resp.raise_for_status()
        
        # 同步到 EduMem0
        await self._sync_quiz_to_mem0(word, test_type, score)
        
        return resp.json()
    
    async def get_user_progress(self) -> dict:
        """获取用户学习进度"""
        client = _get_client()
        resp = await client.get("/api/user/progress", params={"userId": self.efw_user_id})
        resp.raise_for_status()
        return resp.json()
    
    async def get_libraries(self) -> list:
        """获取系统词库"""
        client = _get_client()
        resp = await client.get("/api/libraries")
        resp.raise_for_status()
        return resp.json()
    
    async def get_user_libraries(self) -> list:
        """获取用户自定义词库"""
        client = _get_client()
        resp = await client.get("/api/user/libraries", params={"userId": self.efw_user_id})
        resp.raise_for_status()
        return resp.json()
    
    async def _sync_quiz_to_mem0(self, word: str, test_type: int, score: int):
        """将测验记录同步到 EduMem0"""
        from app.edumem0.client import EduMem0Client
        
        mem0 = EduMem0Client()
        
        # 计算掌握度（0-1）
        mastery = score / 100.0
        
        # 写入 mastery 记忆
        mem0.add_memory(
            student_id=self.student_id,
            memory_type="mastery",
            content=f"单词 {word} 掌握度 {mastery:.0%}",
            structured_payload={
                "subject": "english",
                "topic": word,
                "score": mastery,
                "test_type": test_type
            },
            confidence=mastery,
            tags=["english", "vocabulary", "quiz"]
        )
        
        # 如果得分低，记录 misconception
        if score < 60:
            mem0.add_memory(
                student_id=self.student_id,
                memory_type="misconception",
                content=f"单词 {word} 掌握薄弱，需要复习",
                structured_payload={
                    "subject": "english",
                    "topic": word,
                    "score": score
                },
                confidence=1.0 - mastery,
                tags=["english", "vocabulary", "weak"]
            )
```

#### 3.1.2 在 `services/api/app/main.py` 中注册 API 路由

```python
from app.english_word_service import EnglishWordService

# 在 app 创建后注册路由
@app.get("/api/english/fission")
async def get_english_fission(word: str, student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.get_fission_data(word)

@app.get("/api/english/words")
async def get_english_words(query: str = "", include_definitions: bool = False, student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.get_word_list(query, include_definitions)

@app.get("/api/english/words/{word}")
async def get_english_word_detail(word: str, student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.get_word_detail(word)

@app.post("/api/english/quiz/record")
async def record_english_quiz(word: str, test_type: int, score: int, student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.record_quiz(word, test_type, score)

@app.get("/api/english/progress")
async def get_english_progress(student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.get_user_progress()

@app.get("/api/english/libraries")
async def get_english_libraries(student_id: str = Depends(get_current_student_id)):
    service = EnglishWordService(student_id)
    return await service.get_libraries()
```

#### 3.1.3 在 `docker-compose.yml` 中启动 english-word-fission

```yaml
services:
  # ... 现有服务 ...
  
  english-word-fission:
    image: english-word-fission:latest
    build:
      context: ./english-word-fission  # 或者指向桌面路径
      dockerfile: Dockerfile
    ports:
      - "3011:3011"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/learnforge?schema=LPT_english
      - NEXTAUTH_SECRET=xxx
    volumes:
      - ./english-word-fission/data:/app/data:ro  # 只读挂载 1.45GB 数据
    depends_on:
      - postgres
    networks:
      - learnforge-network
```

---

### 阶段 2：前端 EnglishWorkspaceApp 组件（P0，约 4 小时）

#### 3.2.1 提取核心组件到 LearnForge

**文件清单：**

```
apps/web/src/features/learning-apps/english/
├── EnglishWorkspaceApp.tsx       # 主组件（入口）
├── components/
│   ├── FissionGraph.tsx            # 裂变图（从原项目提取，适配 CanvasApp）
│   ├── WordList.tsx                # 单词列表（虚拟滚动）
│   ├── WordDetail.tsx              # 单词详情
│   ├── WordNote.tsx                # 单词笔记
│   ├── AIChatPanel.tsx             # AI 聊天（对接 LearnForge Agent）
│   ├── QuizPanel.tsx               # 测验面板（拼写/选择/回忆）
│   ├── WordLibraryPicker.tsx       # 词库选择器
│   └── StudyPlanPanel.tsx          # 学习计划面板
├── hooks/
│   ├── useEnglishAPI.ts            # 封装 API 调用
│   ├── useWordData.ts              # 单词数据管理
│   └── useStudyProgress.ts         # 学习进度追踪
├── types/
│   └── english.ts                  # 类型定义
└── api/
    └── client.ts                   # 对接 LearnForge API 的客户端
```

#### 3.2.2 `EnglishWorkspaceApp.tsx` 主组件设计

```tsx
// apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx

import { useState, useCallback } from 'react';
import { Languages } from 'lucide-react';
import type { CanvasApp } from '@learnforge/app-protocol';
import WordList from './components/WordList';
import WordDetail from './components/WordDetail';
import FissionGraph from './components/FissionGraph';
import QuizPanel from './components/QuizPanel';
import AIChatPanel from './components/AIChatPanel';
import StudyPlanPanel from './components/StudyPlanPanel';
import { useEnglishAPI } from './hooks/useEnglishAPI';

interface Props {
  app: CanvasApp;
  onEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void;
}

const TAB_LABELS: Record<string, string> = {
  fission: '裂变图',
  quiz: '测验',
  chat: 'AI 对话',
  plan: '学习计划',
};

export function EnglishWorkspaceApp({ app, onEvent }: Props) {
  const [selectedWord, setSelectedWord] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'fission' | 'quiz' | 'chat' | 'plan'>('fission');
  const [selectedLibrary, setSelectedLibrary] = useState<string>('default');
  
  const api = useEnglishAPI();
  
  const handleWordSelect = useCallback((word: string) => {
    setSelectedWord(word);
    // 触发 Agent 事件，记录单词访问
    onEvent(app.app_id, 'english.word_select', { word, library: selectedLibrary });
  }, [app.app_id, onEvent, selectedLibrary]);
  
  const handleQuizComplete = useCallback((word: string, testType: number, score: number) => {
    // 记录到后端（会自动同步到 EduMem0）
    api.recordQuiz(word, testType, score);
    onEvent(app.app_id, 'english.quiz_complete', { word, testType, score });
  }, [api, app.app_id, onEvent]);
  
  return (
    <div className="english-workspace">
      {/* 顶部工具栏 */}
      <div className="ew-toolbar">
        <Languages size={16} />
        <span>英语工作区</span>
        <div className="ew-tabs">
          {(['fission', 'quiz', 'chat', 'plan'] as const).map(tab => (
            <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>
      </div>
      
      {/* 主内容区：三列布局 */}
      <div className="ew-layout">
        {/* 左列：单词列表 */}
        <div className="ew-left">
          <WordList
            onWordSelect={handleWordSelect}
            selectedWord={selectedWord}
            selectedLibrary={selectedLibrary}
            onLibraryChange={setSelectedLibrary}
          />
        </div>
        
        {/* 中列：单词详情 + 动态面板 */}
        <div className="ew-center">
          {selectedWord && (
            <>
              <WordDetail word={selectedWord} />
              {activeTab === 'quiz' && (
                <QuizPanel word={selectedWord} onComplete={handleQuizComplete} />
              )}
              {activeTab === 'chat' && (
                <AIChatPanel word={selectedWord} appId={app.app_id} onEvent={onEvent} />
              )}
              {activeTab === 'plan' && (
                <StudyPlanPanel />
              )}
            </>
          )}
        </div>
        
        {/* 右列：裂变图 */}
        <div className="ew-right">
          {activeTab === 'fission' && selectedWord && (
            <FissionGraph word={selectedWord} />
          )}
        </div>
      </div>
    </div>
  );
}
```

#### 3.2.3 `useEnglishAPI.ts` — API 封装

```tsx
// apps/web/src/features/learning-apps/english/hooks/useEnglishAPI.ts

import { useCallback } from 'react';
import { apiClient } from '../api/client';

export function useEnglishAPI() {
  const getFissionData = useCallback(async (word: string) => {
    return apiClient.get(`/english/fission?word=${encodeURIComponent(word)}`);
  }, []);
  
  const getWordList = useCallback(async (query: string = '', includeDefinitions: boolean = false) => {
    return apiClient.get(`/english/words?query=${encodeURIComponent(query)}&includeDefinitions=${includeDefinitions}`);
  }, []);
  
  const getWordDetail = useCallback(async (word: string) => {
    return apiClient.get(`/english/words/${encodeURIComponent(word)}`);
  }, []);
  
  const getQuizData = useCallback(async (words: string[]) => {
    return apiClient.post('/english/quiz/data', { words });
  }, []);
  
  const recordQuiz = useCallback(async (word: string, testType: number, score: number) => {
    return apiClient.post('/english/quiz/record', { word, testType, score });
  }, []);
  
  const getProgress = useCallback(async () => {
    return apiClient.get('/english/progress');
  }, []);
  
  const getLibraries = useCallback(async () => {
    return apiClient.get('/english/libraries');
  }, []);
  
  return {
    getFissionData,
    getWordList,
    getWordDetail,
    getQuizData,
    recordQuiz,
    getProgress,
    getLibraries,
  };
}
```

#### 3.2.4 `AIChatPanel.tsx` — 直接对接 LearnForge Agent（废弃独立 AI 后端）

**关键决策：废弃 english-word-fission 的独立 AI 聊天系统**

english-word-fission 原有的 AI 聊天是一个完全独立的系统：
- 后端：Next.js API 路由 `/api/ai/chat`, `/api/ai/context`, `/api/ai/messages`, `/api/ai/sessions`
- 调用方式：直接 SSE 流式调用 DeepSeek API
- 会话管理：独立的 `chat_sessions` + `chat_messages` 表
- 提示词管理：基于 `data/ai_prompts/` 的本地模板文件

**废弃原因：**
1. 与 LearnForge 的 Hermes Agent 系统完全重复
2. DeepSeek 的 API 调用与 LearnForge 的 Gemini 模型配置不一致
3. 会话数据无法被 EduMem0 记忆系统感知
4. 无法利用 LearnForge 的 orchestrator 协同（如 profile/tutor/evaluator 等 Agent）

**废弃清单：**
| 组件 | 位置 | 处理方式 |
|------|------|----------|
| `chat_sessions` 表 | Prisma schema | 从数据库中移除（或保留但不使用） |
| `chat_messages` 表 | Prisma schema | 从数据库中移除（或保留但不使用） |
| `/api/ai/chat` 路由 | `src/app/api/ai/chat/route.ts` | 废弃 |
| `/api/ai/context` 路由 | `src/app/api/ai/context/route.ts` | 废弃 |
| `/api/ai/messages` 路由 | `src/app/api/ai/messages/route.ts` | 废弃 |
| `/api/ai/sessions` 路由 | `src/app/api/ai/sessions/route.ts` | 废弃 |
| `data/ai_prompts/` 目录 | `data/ai_prompts/` | 废弃（提示词由 EnglishAgent 在 LearnForge 中管理） |
| `AIChatWindow.tsx` 组件 | `src/components/AIChatWindow.tsx` | UI 样式参考，但通信逻辑重写 |

**新架构：AIChatPanel 直接对接 LearnForge 的 Agent 系统**

```tsx
// apps/web/src/features/learning-apps/english/components/AIChatPanel.tsx

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles, Loader2 } from 'lucide-react';
import { streamChatMessage } from '@/lib/api/client'; // 使用 LearnForge 的 API
import { useSession } from '@/hooks/useSession';
import ReactMarkdown from 'react-markdown';
import type { AgentStreamEvent } from '@learnforge/app-protocol';

interface Props {
  word: string | null;       // 当前选中的单词（可为 null，表示全局聊天）
  appId: string;
  onEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export function AIChatPanel({ word, appId, onEvent }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const session = useSession();
  
  // 初始系统提示：根据当前单词上下文
  useEffect(() => {
    if (word) {
      setMessages([
        {
          id: 'system-init',
          role: 'assistant',
          content: `你好！我是你的英语学习助手。当前单词是 **${word}**，你可以问我关于这个单词的任何问题，比如：\n- 这个词的词源是什么？\n- 如何在句子中使用它？\n- 有哪些近义词和反义词？\n- 它的常见搭配是什么？`
        }
      ]);
    } else {
      setMessages([
        {
          id: 'system-init',
          role: 'assistant',
          content: '你好！我是你的英语学习助手。你可以问我任何英语相关的问题，比如语法、词汇、发音、写作技巧等。我会根据你的学习历史和薄弱点来个性化回答。'
        }
      ]);
    }
  }, [word]);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);
  
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading || !session) return;
    
    const userMessage = input.trim();
    const messageId = `msg-${Date.now()}`;
    setInput('');
    setMessages(prev => [...prev, { id: messageId, role: 'user', content: userMessage }]);
    setIsLoading(true);
    setStreamingText('');
    
    // 取消之前的请求
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    
    // 构建英语专用的上下文信息
    const englishContext = {
      word: word || null,
      app_type: 'english.workspace',
      app_id: appId,
    };
    
    // 使用 LearnForge 的 streamChatMessage，但标记为 english 专用请求
    // 通过 requestedSkill 或消息内容中的特殊标记来触发 EnglishAgent
    try {
      await streamChatMessage(
        userMessage,
        (event: AgentStreamEvent) => {
          switch (event.type) {
            case 'assistant.delta':
              setStreamingText(prev => prev + event.text);
              break;
            case 'run.step':
              // 显示 Agent 思考步骤（如 "正在检索记忆..."）
              if (event.detail) {
                setStreamingText(prev => prev + `\n[${event.step_name}: ${event.detail}]\n`);
              }
              break;
            case 'app.update':
              // EnglishAgent 可能更新工作区 payload
              if (event.app_id === appId) {
                onEvent(appId, 'app.update', event.patch);
              }
              break;
          }
        },
        session,
        'gemini', // 使用 LearnForge 配置的模型
        undefined, // 无图片
        abortRef.current.signal,
        undefined, // 无附件
        'english_chat' // 通过 requestedSkill 指定 EnglishAgent
      );
      
      // 流式完成后，将 streamingText 转为固定消息
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: streamingText || '抱歉，我暂时无法回答这个问题。'
      }]);
      setStreamingText('');
      
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        // 用户取消了，不报错
        return;
      }
      console.error('English chat error:', error);
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '❌ 连接出错，请重试。'
      }]);
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  }, [input, isLoading, word, appId, session, streamingText, onEvent]);
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  return (
    <div className="ew-chat-panel">
      <div className="ew-chat-header">
        <Sparkles size={14} />
        <span>{word ? `AI 英语助手 · ${word}` : 'AI 英语助手'}</span>
      </div>
      
      <div className="ew-chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`ew-chat-msg ${msg.role}`}>
            <div className={`ew-chat-bubble ${msg.role}`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-sm">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        
        {streamingText && (
          <div className="ew-chat-msg assistant">
            <div className="ew-chat-bubble assistant">
              <div className="prose prose-sm">
                <ReactMarkdown>{streamingText}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
        
        {isLoading && !streamingText && (
          <div className="ew-chat-msg assistant">
            <div className="ew-chat-bubble assistant ew-loading">
              <Loader2 size={14} className="animate-spin" />
              <span>思考中...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="ew-chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={word ? `问关于 "${word}" 的问题...` : '输入英语问题...'}
          rows={1}
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading || !input.trim()}>
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
```

**AIChatPanel 与 LearnForge Agent 的通信流程：**

```
用户输入消息
    ↓
AIChatPanel 调用 streamChatMessage(message, ..., requestedSkill='english_chat')
    ↓
POST /api/chat/stream (LearnForge API)
    ↓
Orchestrator 识别 requestedSkill='english_chat' → 路由到 EnglishAgent
    ↓
EnglishAgent 处理：
  1. 从 EduMem0 检索学生的英语相关记忆
     - profile: 英语水平、薄弱点
     - mastery: 已掌握的单词/语法点
     - misconception: 常见错误
     - app_interaction: 最近的英语学习活动
  2. 从 english-word-fission 后端获取上下文
     - 通过 english_word_service.py 代理
     - 获取当前单词的详细数据、测验历史
  3. 构建增强 prompt（含记忆 + 单词上下文）
  4. 调用 LLM (Gemini) 生成回答
  5. 通过 SSE 流式返回给前端
    ↓
AIChatPanel 接收 assistant.delta 事件，逐字渲染
    ↓
EnglishAgent 同时记录到 EduMem0
     - 如果用户暴露了新薄弱点 → misconception 记忆
     - 如果用户掌握了新概念 → mastery 记忆
     - 更新 session_summary 记忆
```

**EnglishAgent 需要实现的关键能力：**

| 能力 | 说明 | 记忆交互 |
|------|------|----------|
| 单词查询 | 用户问某个单词的词义/用法 | 读取 mastery 判断掌握度，记录到 app_interaction |
| 语法讲解 | 用户问语法问题 | 读取 misconception 查看历史错误，生成针对性讲解 |
| 拼写练习 | 用户请求拼写练习 | 从 QuizRecord 获取薄弱单词，推荐测验 |
| 造句批改 | 用户提交句子 | 检查错误，记录到 misconception，更新 mastery |
| 学习建议 | 用户问"我该怎么学英语" | 读取 profile 和 mastery，生成个性化建议 |
| 上下文感知 | 用户在裂变图点击了单词 | 通过 app_id 关联，EnglishAgent 知道当前单词 |

---

### 阶段 3：组件适配与 NativeAppRenderer 集成（P0，约 1 小时）

#### 3.3.1 `NativeAppRenderer.tsx` 新增分支

```tsx
// 在 iconMap 中新增
const iconMap: Partial<Record<CanvasApp["app_type"], typeof Boxes>> = {
  // ... 现有 ...
  "english.workspace": Languages,
  "humanities.notebook": Library, // 占位
};

// 在 appTypeLabels 中新增
const appTypeLabels: Partial<Record<CanvasApp["app_type"], string>> = {
  // ... 现有 ...
  "english.workspace": "英语工作区",
  "humanities.notebook": "文科笔记本",
};

// 在渲染逻辑中新增
export function NativeAppRenderer({ ... }) {
  // ... 现有 ...
  return (
    <div className={bodyClassName}>
      {/* ... 现有分支 ... */}
      {app.app_type === "english.workspace" ? (
        <EnglishWorkspaceApp app={app} onEvent={onEvent} />
      ) : null}
      {app.app_type === "humanities.notebook" ? (
        <div className="placeholder-app">
          <Library size={48} />
          <p>文科笔记本（即将推出）</p>
        </div>
      ) : null}
      {/* ... 现有 ... */}
    </div>
  );
}
```

#### 3.3.2 `appTypeLabel` 和 `appAccent` 函数新增

```tsx
// 在 SpatialCanvas.tsx 中
function appTypeLabel(appType: string): string {
  const labels: Record<string, string> = {
    // ... 现有 ...
    "english.workspace": "英语工作区",
    "humanities.notebook": "文科笔记本",
  };
  return labels[appType] ?? "学习应用";
}

function appAccent(appType: string): string {
  const accents: Record<string, string> = {
    // ... 现有 ...
    "english.workspace": "linear-gradient(135deg, #f59e0b, #ef4444)",
    "humanities.notebook": "linear-gradient(135deg, #8b5cf6, #ec4899)",
  };
  return accents[appType] ?? "linear-gradient(135deg, #3b82f6, #8b5cf6)";
}
```

---

### 阶段 4：Dock 改造为四区域（P0，约 1 小时）

已在 `docs/english_humanities_modules_plan.md` 中详细规划，此处简述：

Dock 顺序：**系统应用（画像/仪表/资源） → 系统模块（文科/英语） → 生成模块（PPT/图解/视频） → 文件夹**

```tsx
// SpatialCanvas.tsx Dock 改造

const SYSTEM_MODULE_TYPES = new Set(["english.workspace", "humanities.notebook"]);
const REALTIME_TYPES = new Set(["ppt.preview", "image.explanation", "video.script", "video.player", "custom.html"]);

function isSystemModule(app: Pick<CanvasApp, "app_type">): boolean {
  return SYSTEM_MODULE_TYPES.has(app.app_type as string);
}

function isRealTimeResource(app: Pick<CanvasApp, "app_type">): boolean {
  return REALTIME_TYPES.has(app.app_type as string) && !isPinnedApp(app) && !isSystemModule(app);
}

// Dock 渲染：左区 | 中区 | 右区
<footer className="app-dock dock glass glass-hi">
  {(() => {
    const pinnedApps = apps.filter(isPinnedApp).slice(0, 3);
    const systemModules = apps.filter(isSystemModule);
    const realTimeApps = apps.filter(isRealTimeResource);
    const contentApps = [...folderApps];
    
    return (
      <>
        {/* 左区 */}
        {pinnedApps.map(renderDockBtn)}
        {realTimeApps.length > 0 && pinnedApps.length > 0 && <div className="dock-sep" />}
        {realTimeApps.map(renderDockBtn)}
        
        {/* 中区 */}
        {systemModules.length > 0 && <div className="dock-sep" />}
        {systemModules.map(renderDockBtn)}
        
        {/* 右区 */}
        {contentApps.length > 0 && (pinnedApps.length > 0 || systemModules.length > 0 || realTimeApps.length > 0) && <div className="dock-sep" />}
        {contentApps.map(renderDockBtn)}
      </>
    );
  })()}
</footer>
```

---

### 阶段 5：EduMem0 记忆集成（P1，约 1.5 小时）

#### 3.5.1 测验记录 → EduMem0

在 `english_word_service.py` 的 `record_quiz()` 中已经实现同步逻辑：

```python
# 写入 mastery 记忆
{
    "memory_type": "mastery",
    "content": f"单词 {word} 掌握度 {mastery:.0%}",
    "structured_payload": {
        "subject": "english",
        "topic": word,
        "score": mastery,
        "test_type": test_type
    },
    "confidence": mastery,
    "tags": ["english", "vocabulary", "quiz"]
}

# 如果得分低，记录 misconception
{
    "memory_type": "misconception",
    "content": f"单词 {word} 掌握薄弱，需要复习",
    "structured_payload": {
        "subject": "english",
        "topic": word,
        "score": score
    },
    "confidence": 1.0 - mastery,
    "tags": ["english", "vocabulary", "weak"]
}
```

#### 3.5.2 学习进度 → EduMem0

```python
# 定期同步学习进度
async def sync_progress_to_mem0(self):
    progress = await self.get_user_progress()
    
    # 总词汇量
    mem0.add_memory(
        student_id=self.student_id,
        memory_type="profile",
        content=f"英语词汇量约 {progress.get('vocabulary_count', 0)} 个",
        structured_payload={
            "subject": "english",
            "dimension": "vocabulary_count",
            "value": progress.get('vocabulary_count', 0)
        },
        tags=["english", "profile"]
    )
    
    # 平均测验得分
    avg_score = progress.get('avg_score', 0)
    mem0.add_memory(
        student_id=self.student_id,
        memory_type="mastery",
        content=f"英语测验平均得分 {avg_score}",
        structured_payload={
            "subject": "english",
            "dimension": "avg_score",
            "value": avg_score
        },
        confidence=avg_score / 100.0,
        tags=["english", "quiz"]
    )
```

#### 3.5.3 检索场景

```python
# 在 edumem0/retriever.py 中新增英语检索场景

class EnglishContextRetriever:
    """为英语工作区检索记忆上下文"""
    
    def get_tutor_context(self, student_id: str, current_word: str | None = None) -> dict:
        """获取英语辅导上下文"""
        # 1. 获取薄弱单词
        weak_words = self.store.search_memories(
            student_id,
            memory_types=["misconception"],
            tags=["english", "vocabulary"],
            limit=5
        )
        
        # 2. 获取高掌握度单词
        strong_words = self.store.search_memories(
            student_id,
            memory_types=["mastery"],
            tags=["english", "vocabulary"],
            limit=5
        )
        
        # 3. 获取学习计划
        study_plan = self.store.search_memories(
            student_id,
            memory_types=["preference"],
            tags=["english", "study_plan"],
            limit=1
        )
        
        return {
            "weak_words": [m.content for m in weak_words],
            "strong_words": [m.content for m in strong_words],
            "study_plan": study_plan[0].content if study_plan else None,
            "current_word": current_word
        }
```

---

### 阶段 6：Agent 集成（P1，约 1.5 小时）

#### 3.6.1 EnglishAgent 设计

```python
# services/api/app/agents/english_agent.py

class EnglishAgent:
    """处理英语学习相关的 Agent"""
    
    def __init__(self, mem0_client: EduMem0Client, word_service: EnglishWordService):
        self.mem0 = mem0_client
        self.word_service = word_service
    
    async def handle_chat(self, student_id: str, word: str | None, message: str, history: list, stream_callback=None) -> str:
        """处理英语工作区中的 AI 聊天（通过 LearnForge 的 LLM 生成）"""
        # 1. 获取学生的英语记忆上下文
        context = self._get_english_context(student_id)
        
        # 2. 获取单词详情（如果 word 不为空）
        word_detail = None
        if word:
            word_detail = await self.word_service.get_word_detail(word)
        
        # 3. 从 english-word-fission 获取学习历史
        user_context = await self.word_service.get_user_context(student_id)
        
        # 4. 构建增强 prompt（提示词由 EnglishAgent 在 LearnForge 中管理，不用外部文件）
        prompt_parts = ["""你是一位专业的英语教师。"""]
        
        if word:
            prompt_parts.append(f"""
当前单词：{word}
单词详情：{word_detail}
""")
        
        prompt_parts.append(f"""
学生背景：
- 薄弱单词：{', '.join(context['weak_words']) or '暂无'}
- 已掌握单词：{', '.join(context['strong_words']) or '暂无'}
- 学习历史：最近访问 {user_context.get('recent_history_count', 0)} 个单词，测验 {user_context.get('recent_test_count', 0)} 次
""")
        
        prompt_parts.append(f"学生问题：{message}")
        
        if word:
            prompt_parts.append("""
请用中文回答，重点解释单词的用法、搭配和常见误区。如果学生拼写错误，温和纠正。
""")
        else:
            prompt_parts.append("""
请用中文回答，根据学生的英语水平和历史表现给出个性化建议。如果是语法问题，给出简洁清晰的解释和示例。
""")
        
        prompt = "\n".join(prompt_parts)
        
        # 5. 调用 LearnForge 的 LLM（Gemini，通过 Hermes 运行时）
        # 注意：这里不是直接调用 DeepSeek，而是使用 LearnForge 的 generate_stream 方法
        from app.hermes_runtime import generate_stream
        response = await generate_stream(
            prompt=prompt,
            model_provider="gemini",
            temperature=0.7,
            stream_callback=stream_callback
        )
        
        # 6. 记录到 EduMem0（如果学生暴露了新的薄弱点）
        # EnglishAgent 的分析逻辑：如果 LLM 检测到学生有错误，自动记录
        await self._analyze_and_record_memory(student_id, word, message, response)
        
        return response
    
    async def _analyze_and_record_memory(self, student_id: str, word: str | None, user_message: str, assistant_response: str):
        """分析对话，自动记录记忆"""
        # 使用 LLM 快速判断是否有新记忆需要记录
        analysis_prompt = f"""分析以下英语学习对话，判断是否需要记录学生的薄弱点或进步。

对话：
学生：{user_message}
教师：{assistant_response}

请判断：
1. 学生是否有明显错误？如果有，是什么错误？
2. 学生是否展示了新的掌握？
3. 是否需要推荐复习某个单词？

只输出 JSON，格式：{{"has_error": bool, "error_type": str|null, "has_progress": bool, "recommend_review": str|null}}"""
        
        analysis = await self.llm.generate(analysis_prompt, temperature=0.1)
        
        try:
            result = json.loads(analysis)
            
            if result.get("has_error") and word:
                # 记录 misconception
                await self.mem0.add_memory(
                    student_id=student_id,
                    memory_type="misconception",
                    content=f"单词 {word} 掌握薄弱：{result.get('error_type')}",
                    structured_payload={"subject": "english", "topic": word, "error_type": result.get("error_type")},
                    confidence=0.7,
                    tags=["english", "vocabulary", "weak"]
                )
            
            if result.get("has_progress") and word:
                # 更新 mastery
                await self.mem0.add_memory(
                    student_id=student_id,
                    memory_type="mastery",
                    content=f"单词 {word} 掌握良好",
                    structured_payload={"subject": "english", "topic": word, "score": 0.85},
                    confidence=0.85,
                    tags=["english", "vocabulary", "mastered"]
                )
        except:
            pass  # 分析失败不影响主流程
    
    async def recommend_words(self, student_id: str, count: int = 10) -> list:
        """根据记忆推荐单词"""
        # 1. 获取薄弱点
        misconceptions = self.mem0.search(
            student_id,
            memory_types=["misconception"],
            tags=["english", "vocabulary"]
        )
        
        # 2. 获取已掌握单词
        mastered = self.mem0.search(
            student_id,
            memory_types=["mastery"],
            tags=["english", "vocabulary"]
        )
        
        # 3. 从 english-word-fission 获取候选单词
        libraries = await self.word_service.get_libraries()
        
        # 4. 过滤和排序
        mastered_words = {m.structured_payload.get("topic") for m in mastered}
        weak_words = [m.structured_payload.get("topic") for m in misconceptions]
        
        # 推荐逻辑：优先薄弱单词，其次新单词
        recommendations = []
        for w in weak_words[:count]:
            recommendations.append({"word": w, "reason": "需要复习"})
        
        # 补充新单词
        for lib in libraries:
            for w in lib.get("words", []):
                if w not in mastered_words and len(recommendations) < count:
                    recommendations.append({"word": w, "reason": "新单词"})
        
        return recommendations
    
    async def generate_quiz(self, student_id: str, words: list[str], test_type: int) -> list:
        """生成个性化测验"""
        # 获取测验数据
        quiz_data = await self.word_service.get_quiz_data(words)
        return quiz_data
    
    def _get_english_context(self, student_id: str) -> dict:
        """获取学生英语学习的记忆上下文"""
        weak = self.mem0.search(student_id, memory_types=["misconception"], tags=["english"], limit=5)
        strong = self.mem0.search(student_id, memory_types=["mastery"], tags=["english"], limit=5)
        return {
            "weak_words": [m.content for m in weak],
            "strong_words": [m.content for m in strong]
        }
```

#### 3.6.2 在 Orchestrator 中注册

```python
# services/api/app/agents/orchestrator_agent.py

from app.agents.english_agent import EnglishAgent

class UnifiedOrchestrator:
    def __init__(self, ...):
        # ... 现有 Agent ...
        self.english_agent = EnglishAgent(mem0_client, word_service)
    
    def _detect_english_intent(self, message: str) -> bool:
        """检测英语相关意图"""
        english_keywords = [
            "单词", "英语", "english", "vocabulary", "grammar",
            "拼写", "听力", "口语", "写作", "阅读",
            "背单词", "词库", "裂变图", "测验"
        ]
        return any(k in message.lower() for k in english_keywords)
    
    async def run(self, ...):
        # ... 现有流程 ...
        
        # 如果检测到英语意图，调用 EnglishAgent
        if self._detect_english_intent(message):
            # 创建或打开英语工作区
            await self._create_or_open_english_workspace(student_id, course_id)
        
        # ... 现有流程 ...
    
    async def _create_or_open_english_workspace(self, student_id, course_id):
        """创建或打开英语工作区"""
        # 检查是否已存在
        existing = await self.store.find_app_by_type(student_id, "english.workspace")
        if not existing:
            # 创建新的英语工作区
            app = await self.canvas_agent.create_app(
                student_id=student_id,
                course_id=course_id,
                app_type="english.workspace",
                title="英语工作区",
                payload={
                    "mode": "fission",
                    "selected_library": "default",
                    "selected_word": None
                }
            )
            return app
        return existing
```

---

### 阶段 7：类型定义扩展（P0，约 0.5 小时）

#### 3.7.1 `packages/app-protocol/src/types.ts`

```typescript
export type CanvasAppType =
  // ... 现有类型 ...
  | "english.workspace"    // 英语工作区
  | "humanities.notebook"; // 文科笔记本（占位）
```

#### 3.7.2 `services/api/app/schemas/app_protocol.py`

```python
CanvasAppType = Literal[
    # ... 现有类型 ...
    "english.workspace",
    "humanities.notebook",
]
```

#### 3.7.3 `services/api/app/agents/app_canvas_agent.py`

```python
ICON_BY_APP_TYPE = {
    # ... 现有 ...
    "english.workspace": "Languages",
    "humanities.notebook": "Library",
}

SIZE_BY_APP_TYPE = {
    # ... 现有 ...
    "english.workspace": (960, 640),
    "humanities.notebook": (960, 640),
}
```

---

## 四、文科笔记本占位（humanities.notebook）

### 4.1 占位实现

在 `NativeAppRenderer.tsx` 中渲染一个简单的占位界面：

```tsx
{app.app_type === "humanities.notebook" ? (
  <div className="placeholder-humanities">
    <Library size={64} />
    <h3>文科笔记本</h3>
    <p>类似 NotebookLM 的文档智能处理系统</p>
    <p>功能：文档上传、智能摘要、RAG 问答、播客生成、概念图谱</p>
    <p style={{ color: '#888', marginTop: 16 }}>即将推出...</p>
  </div>
) : null}
```

### 4.2 类型定义已包含

在 `CanvasAppType` 中已加入 `"humanities.notebook"`，Dock 中区已预留位置。

---

## 五、完整文件修改清单

### 5.1 新增文件（约 15 个）

| 文件 | 说明 | 来源 |
|------|------|------|
| `services/api/app/english_word_service.py` | API 代理层 | 新写 |
| `services/api/app/agents/english_agent.py` | 英语 Agent | 新写 |
| `apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx` | 主组件 | 新写 |
| `apps/web/src/features/learning-apps/english/components/FissionGraph.tsx` | 裂变图 | 提取自原项目 |
| `apps/web/src/features/learning-apps/english/components/WordList.tsx` | 单词列表 | 提取自原项目 |
| `apps/web/src/features/learning-apps/english/components/WordDetail.tsx` | 单词详情 | 提取自原项目 |
| `apps/web/src/features/learning-apps/english/components/WordNote.tsx` | 单词笔记 | 提取自原项目 |
| `apps/web/src/features/learning-apps/english/components/AIChatPanel.tsx` | AI 聊天（对接 LearnForge Agent，废弃原 DeepSeek 独立后端） | 新写 |
| `apps/web/src/features/learning-apps/english/components/QuizPanel.tsx` | 测验面板 | 提取自原项目 |
| `apps/web/src/features/learning-apps/english/components/StudyPlanPanel.tsx` | 学习计划 | 新写 |
| `apps/web/src/features/learning-apps/english/hooks/useEnglishAPI.ts` | API Hook | 新写 |
| `apps/web/src/features/learning-apps/english/hooks/useWordData.ts` | 数据管理 | 新写 |
| `apps/web/src/features/learning-apps/english/api/client.ts` | API 客户端 | 新写 |
| `apps/web/src/features/learning-apps/english/types/english.ts` | 类型定义 | 新写 |

### 5.2 修改文件（约 10 个）

| 文件 | 修改内容 |
|------|----------|
| `packages/app-protocol/src/types.ts` | `CanvasAppType` 新增 2 项 |
| `services/api/app/schemas/app_protocol.py` | `CanvasAppType` Literal 新增 2 项 |
| `services/api/app/agents/app_canvas_agent.py` | `ICON_BY_APP_TYPE` / `SIZE_BY_APP_TYPE` 新增 2 项 |
| `services/api/app/agents/orchestrator_agent.py` | 注册 EnglishAgent，添加英语意图检测 |
| `services/api/app/main.py` | 注册英语 API 路由 |
| `services/api/app/edumem0/retriever.py` | 新增 `EnglishContextRetriever` |
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | 新增 2 个 `app_type` 分支 |
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | `iconMap` / `appTypeLabels` 新增 2 项 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | Dock 渲染逻辑改为三区域 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | `appTypeLabel` / `appAccent` 新增 2 项 |
| `docker-compose.yml` | 新增 `english-word-fission` 服务 |

---

## 六、实施优先级与工时估算

| 阶段 | 任务 | 工时 | 优先级 |
|------|------|------|--------|
| **P0** | 类型定义扩展（3个文件） | 0.5h | 必须先做 |
| **P0** | 后端 API 代理层 | 2h | 必须先做 |
| **P0** | 前端 `EnglishWorkspaceApp` 骨架 + 路由集成 | 1h | 可先跑起来 |
| **P0** | Dock 改造为三区域 | 1h | UI 立即生效 |
| **P1** | 提取裂变图组件（FissionGraph） | 2h | 核心亮点 |
| **P1** | 提取单词列表组件（WordList） | 1.5h | 核心功能 |
| **P1** | 提取单词详情 + 笔记组件 | 1h | 基础功能 |
| **P1** | 测验面板（QuizPanel） | 1.5h | 学习闭环 |
| **P1** | AI 聊天面板（对接 LearnForge Agent，废弃原 DeepSeek 后端） | 1h | 智能交互 |
| **P1** | EnglishAgent 实现（使用 LearnForge LLM，非 DeepSeek） | 1.5h | Agent 智能 |
| **P1** | EduMem0 集成（测验同步） | 1h | 个性化 |
| **P2** | 学习计划面板 | 1h | 完整体验 |
| **P2** | 词库选择器 | 1h | 用户体验 |
| **P2** | 测试覆盖 | 1h | 质量保障 |

**总计：约 17 小时（2-3 天）**

---

## 七、风险与注意事项

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| **1.45GB 数据迁移** | 数据量大，迁移成本高 | 不迁移，保留原项目作为后端服务 |
| **组件依赖冲突** | 原项目使用 d3-force、react-force-graph-2d，可能与 LearnForge 依赖冲突 | 检查依赖版本，必要时做适配层 |
| **认证映射** | LearnForge 的 student_id 与 english-word-fission 的 user_id 需要映射 | 使用 `learnforge_{student_id}` 前缀自动映射 |
| **CSS 样式冲突** | 原项目可能使用 Tailwind CSS，与 LearnForge 的样式系统冲突 | 使用 CSS Module 或 scoped 样式隔离 |
| **性能问题** | 裂变图渲染大量节点可能性能差 | 使用虚拟化、按需加载、分页 |
| **跨域问题** | 前端直接调用 english-word-fission（端口 3011）可能跨域 | 通过 LearnForge API 代理层转发，避免跨域 |

---

## 八、总结

### 核心方案

> **english-word-fission 作为独立后端服务运行，LearnForge 通过 API 代理层调用它的功能。前端提取核心组件（裂变图、单词列表、测验等）到 `EnglishWorkspaceApp`，与 EduMem0 和 Agent 深度集成。文科笔记本暂时占位。**

### 架构优势

1. **数据不动**：1.45GB 数据无需迁移，零风险
2. **独立演进**：english-word-fission 可以独立更新维护
3. **体验融合**：前端组件统一在 LearnForge 画布中，体验一致
4. **记忆互通**：测验记录、学习进度自动同步到 EduMem0
5. **Agent 智能**：EnglishAgent 基于记忆提供个性化推荐和辅导

### 交付物

| 交付物 | 说明 |
|--------|------|
| 英语工作区模块 | 完整的英语学习工具（裂变图、单词列表、测验、AI 聊天） |
| 双分隔线 Dock | 左区（pinned+实时资源）| 中区（系统模块）| 右区（文件夹） |
| 文科笔记本占位 | 已预留类型和 Dock 位置，待后续开发 |
| API 代理层 | 封装 english-word-fission 的 API |
| EduMem0 集成 | 测验记录、学习进度自动同步到记忆系统 |
| Agent 集成 | EnglishAgent 提供个性化推荐和辅导 |

---

## 下一步建议

建议按以下顺序实施：

1. **先做类型定义和 API 代理层**（2.5h）→ 基础就绪
2. **再做 Dock 改造**（1h）→ UI 立即看到三区域效果
3. **再做 EnglishWorkspaceApp 骨架**（1h）→ 可以打开空壳
4. **逐步提取核心组件**（裂变图 → 单词列表 → 测验 → AI 聊天）→ 功能完善
5. **最后做 EduMem0 和 Agent 集成** → 智能化

**是否立即开始实施？** 如果是，我可以从类型定义和 API 代理层开始。
