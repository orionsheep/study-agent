# 全局选词查单词 + 英语工作区联动 — 详细规划

> 版本：2026-06-17  
> 背景：用户希望在任意应用中（HTML 阅读、NativeApp 等）选中单词后，右键/浮层调起英语工作区查单词。英语工作区的 AI 聊天直接对接 LearnForge Agent，废弃原 DeepSeek 独立后端。

---

## 一、核心架构

```
┌─────────────────────────────────────────────────────────────┐
│  LearnForge 应用层（任意 App）                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ HTML iframe     │  │ NativeApp       │  │ 文科笔记本   │  │
│  │ (custom-html)   │  │ (resource.center│  │ (humanities) │  │
│  │                 │  │  video.player   │  │             │  │
│  │ 选词 → postMessage│  │ 选词 → 全局事件  │  │ 选词 → 全局事件│  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘  │
│           │                      │                   │         │
│           └──────────────────────┴───────────────────┘         │
│                      ↓ 全局浮动工具条                             │
│           ┌────────────────────────────┐                        │
│           │ 浮动查单词工具条 (Floating) │  ← 显示"查单词"按钮    │
│           │  - 选词检测                 │                        │
│           │  - 位置计算（避开选中区域）  │                        │
│           └────────────┬───────────────┘                        │
│                        ↓ 点击                                     │
│           ┌────────────────────────────┐                        │
│           │ 调起英语工作区                │                        │
│           │  - 如果已存在：聚焦 + 传入单词 │                        │
│           │  - 如果不存在：创建 + 传入单词 │                        │
│           └────────────┬───────────────┘                        │
└────────────────────────┼───────────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────────┐
│  LearnForge Shell      │                                       │
│  ┌─────────────────────┴──────────────────────────────────┐   │
│  │  LearnForgeShell.tsx                                   │   │
│  │  - createCanvasApp() 创建 english.workspace            │   │
│  │  - openWindow() 聚焦已存在的 english.workspace         │   │
│  │  - onAppEvent('english.lookup', {word}) 处理请求       │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  SpatialCanvas                                         │   │
│  │  - 窗口管理（openWindow/focusWindow/closeWindow）      │   │
│  │  - 接收 onAppEvent 并路由到对应组件                     │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────────┐
│  English Workspace     │                                       │
│  ┌─────────────────────┴──────────────────────────────────┐   │
│  │ EnglishWorkspaceApp.tsx                                  │   │
│  │  - 接收 payload.incoming_word → 自动选词                │   │
│  │  - 裂变图自动以该单词为中心渲染                         │   │
│  │  - AI 聊天面板自动以该单词为上下文初始化                 │   │
│  │  - 单词详情面板自动加载该单词                           │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ AIChatPanel（对接 LearnForge Agent）                     │   │
│  │  - 调用 streamChatMessage(..., requestedSkill='english_chat')│
│  │  - 通过 SSE 接收 assistant.delta 事件                   │
│  │  - 逐字渲染 Markdown 回复                               │
│  │  - 支持取消（AbortController）                            │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────────┐
│  Agent 层              │                                       │
│  ┌─────────────────────┴──────────────────────────────────┐   │
│  │ OrchestratorAgent                                      │   │
│  │  - 检测到 english_chat 请求 → 路由到 EnglishAgent       │   │
│  │  - 或全局英语意图检测 → 自动创建英语工作区              │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ EnglishAgent（使用 LearnForge LLM，非 DeepSeek）        │   │
│  │  - 从 EduMem0 检索英语记忆（薄弱点/已掌握/学习计划）      │   │
│  │  - 从 english_word_service 获取单词详情/学习历史        │   │
│  │  - 构建增强 prompt → 调用 generate_stream(Gemini)      │   │
│  │  - 自动分析对话 → 记录 misconception/mastery 到 EduMem0  │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、废弃组件清单（english-word-fission 独立 AI 系统）

| 废弃组件 | 位置 | 原因 |
|----------|------|------|
| `AIChatWindow.tsx` | `src/components/AIChatWindow.tsx` | 独立 DeepSeek 后端，与 LearnForge Agent 重复 |
| `/api/ai/chat` | `src/app/api/ai/chat/route.ts` | 直接调用 DeepSeek API，不经过 LearnForge Agent |
| `/api/ai/context` | `src/app/api/ai/context/route.ts` | 获取学习历史，功能由 EnglishAgent 替代 |
| `/api/ai/messages` | `src/app/api/ai/messages/route.ts` | 会话管理，由 LearnForge 统一处理 |
| `/api/ai/sessions` | `src/app/api/ai/sessions/route.ts` | 会话管理，由 LearnForge 统一处理 |
| `chat_sessions` 表 | Prisma schema | 独立会话系统，无法被 EduMem0 感知 |
| `chat_messages` 表 | Prisma schema | 同上 |
| `data/ai_prompts/` | 本地提示词文件 | 提示词由 EnglishAgent 在 LearnForge 中管理 |

---

## 三、新增组件清单

### 3.1 全局浮动查单词工具条

```
文件：apps/web/src/features/selection-toolbar/SelectionToolbar.tsx
```

**功能：**
- 监听全局 `selectionchange` 事件
- 检测选中的文本是否为单词（正则：`/^[a-zA-Z]+$/`）
- 计算浮动工具条位置（避开选中区域，智能定位）
- 显示"查单词"按钮 + 发音按钮（可选）
- 点击后触发 `english:lookup` 全局事件

**实现：**
```tsx
// SelectionToolbar.tsx
import { useEffect, useState, useRef } from 'react';
import { BookOpen, Volume2 } from 'lucide-react';

export function SelectionToolbar() {
  const [selection, setSelection] = useState<{ text: string; rect: DOMRect } | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleSelectionChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) {
        setSelection(null);
        return;
      }
      
      const text = sel.toString().trim();
      // 只处理纯英文单词（1-30个字母）
      if (!/^[a-zA-Z]{1,30}$/.test(text)) {
        setSelection(null);
        return;
      }
      
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      // 排除在输入框中的选词
      const container = range.commonAncestorContainer.parentElement;
      if (container?.closest('input, textarea, [contenteditable]')) {
        setSelection(null);
        return;
      }
      
      setSelection({ text, rect });
    };
    
    document.addEventListener('selectionchange', handleSelectionChange);
    document.addEventListener('click', () => {
      // 点击其他地方时，如果点击的不是工具条本身，则隐藏
      setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || sel.toString().trim() === '') {
          setSelection(null);
        }
      }, 10);
    });
    
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, []);
  
  const handleLookup = () => {
    if (!selection) return;
    
    // 触发全局事件，由 LearnForgeShell 监听
    window.dispatchEvent(new CustomEvent('english:lookup', {
      detail: { word: selection.text.toLowerCase(), source: 'selection-toolbar' }
    }));
    
    setSelection(null);
  };
  
  if (!selection) return null;
  
  // 计算位置：在选中文本上方居中显示
  const toolbarWidth = 140;
  const left = selection.rect.left + selection.rect.width / 2 - toolbarWidth / 2;
  const top = selection.rect.top - 48; // 上方 48px
  
  return (
    <div
      ref={toolbarRef}
      className="selection-toolbar"
      style={{
        position: 'fixed',
        left: Math.max(8, Math.min(window.innerWidth - toolbarWidth - 8, left)),
        top: Math.max(8, top),
        zIndex: 9999,
      }}
    >
      <span className="st-word">{selection.text}</span>
      <button className="st-btn" onClick={handleLookup} title="查单词">
        <BookOpen size={14} />
        <span>查单词</span>
      </button>
      <button className="st-btn" title="发音（可选）">
        <Volume2 size={14} />
      </button>
    </div>
  );
}
```

**CSS 样式（`styles.css`）：**
```css
.selection-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(12px);
  border-radius: 10px;
  border: 1px solid rgba(100, 216, 255, 0.25);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  animation: stIn 0.18s ease;
}
.selection-toolbar .st-word {
  font-weight: 700;
  color: #64d8ff;
  font-size: 13px;
  padding-right: 6px;
  border-right: 1px solid rgba(255,255,255,0.15);
}
.selection-toolbar .st-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(100, 216, 255, 0.15);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.selection-toolbar .st-btn:hover {
  background: rgba(100, 216, 255, 0.35);
}
@keyframes stIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
}
```

### 3.2 HTML iframe 内选词支持

在 `CustomHtmlAppRenderer` 的 `learnForgeBridgeScript` 中增加选词检测脚本：

```javascript
// 添加到 bridge script 中
function installSelectionBridge() {
  let toolbar = null;
  
  function showToolbar(word, rect) {
    if (toolbar) toolbar.remove();
    toolbar = document.createElement('div');
    toolbar.className = 'lf-selection-toolbar';
    toolbar.innerHTML = `
      <span class="lf-st-word">${word}</span>
      <button class="lf-st-btn" data-action="lookup">查单词</button>
    `;
    toolbar.style.cssText = `
      position: fixed;
      left: ${rect.left + rect.width/2 - 70}px;
      top: ${rect.top - 40}px;
      z-index: 99999;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      background: rgba(15,23,42,0.92);
      border-radius: 8px;
      border: 1px solid rgba(100,216,255,0.25);
      font-family: system-ui, sans-serif;
      font-size: 13px;
    `;
    toolbar.querySelector('[data-action="lookup"]').onclick = () => {
      send({ type: 'english:lookup', word: word.toLowerCase() });
      toolbar.remove();
      toolbar = null;
    };
    document.body.appendChild(toolbar);
  }
  
  document.addEventListener('selectionchange', () => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) {
      if (toolbar) { toolbar.remove(); toolbar = null; }
      return;
    }
    const text = sel.toString().trim();
    if (!/^[a-zA-Z]{1,30}$/.test(text)) {
      if (toolbar) { toolbar.remove(); toolbar = null; }
      return;
    }
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    showToolbar(text, rect);
  });
  
  document.addEventListener('click', (e) => {
    if (toolbar && !toolbar.contains(e.target)) {
      toolbar.remove();
      toolbar = null;
    }
  });
}
installSelectionBridge();
```

**CustomHtmlAppRenderer 接收消息：**
```tsx
useEffect(() => {
  const handler = (event: MessageEvent) => {
    const message = event.data || {};
    if (event.origin !== "null" && event.origin !== window.location.origin) return;
    if (event.source !== iframeRef.current?.contentWindow || message.widgetId !== widgetId) return;
    
    // ... 现有消息处理 ...
    
    // 新增：处理 english:lookup 事件
    if (message.type === 'english:lookup' && message.word) {
      // 将事件转发给 LearnForgeShell 的全局事件系统
      window.dispatchEvent(new CustomEvent('english:lookup', {
        detail: { word: message.word, source: 'iframe' }
      }));
    }
  };
  window.addEventListener("message", handler);
  return () => window.removeEventListener("message", handler);
}, [widgetId]);
```

### 3.3 LearnForgeShell 中处理 english:lookup 事件

```tsx
// LearnForgeShell.tsx

useEffect(() => {
  const handleEnglishLookup = async (e: CustomEvent<{ word: string; source: string }>) => {
    const { word } = e.detail;
    
    // 1. 查找是否已存在英语工作区
    const existingApp = appsRef.current.find(
      app => app.app_type === 'english.workspace'
    );
    
    if (existingApp) {
      // 更新 payload 中的 incoming_word
      const updatedPayload = {
        ...existingApp.payload,
        incoming_word: word,
        incoming_timestamp: Date.now(),
      };
      
      // 更新 app payload
      setApps(current => current.map(app => 
        app.app_id === existingApp.app_id
          ? { ...app, payload: updatedPayload }
          : app
      ));
      
      // 发送事件给组件
      await onAppEvent(existingApp.app_id, 'english.lookup', { word });
      
      // 打开/聚焦窗口
      openWindow(existingApp.app_id);
    } else {
      // 创建新的英语工作区
      const app = await createCanvasApp({
        app_type: 'english.workspace',
        title: '英语工作区',
        payload: {
          mode: 'fission',
          selected_library: 'default',
          selected_word: word,
          incoming_word: word,
          incoming_timestamp: Date.now(),
        },
      }, sessionContext);
      
      const nextApp = {
        ...app,
        position: computeCenterPos(app, openWindowIdsRef.current.length),
      } as CanvasApp;
      
      setApps(current => [...current, nextApp]);
      setOpenWindowIds(ids => [...ids, nextApp.app_id]);
      focusWindow(nextApp.app_id);
    }
    
    // 可选：同时记录到 EduMem0（作为 app_interaction）
    await postAppEvent('english.lookup', { word, source: e.detail.source });
  };
  
  window.addEventListener('english:lookup', handleEnglishLookup as EventListener);
  return () => window.removeEventListener('english:lookup', handleEnglishLookup as EventListener);
}, [sessionContext, computeCenterPos, openWindow, focusWindow, onAppEvent]);
```

---

## 四、EnglishWorkspaceApp 接收 incoming_word

```tsx
// EnglishWorkspaceApp.tsx

export function EnglishWorkspaceApp({ app, onEvent }: Props) {
  const [selectedWord, setSelectedWord] = useState<string | null>(
    app.payload?.selected_word || null
  );
  const [activeTab, setActiveTab] = useState<'fission' | 'quiz' | 'chat' | 'plan'>('fission');
  const [selectedLibrary, setSelectedLibrary] = useState<string>(
    app.payload?.selected_library || 'default'
  );
  const [incomingWord, setIncomingWord] = useState<string | null>(null);
  
  const api = useEnglishAPI();
  
  // 监听 incoming_word 变化（从外部调起）
  useEffect(() => {
    const word = app.payload?.incoming_word;
    if (word && word !== incomingWord) {
      setIncomingWord(word);
      setSelectedWord(word);
      setActiveTab('fission'); // 自动切换到裂变图，展示该单词
      
      // 清除 incoming_word，避免重复触发
      onEvent(app.app_id, 'app.update', {
        payload: { ...app.payload, incoming_word: null }
      });
      
      // 通知 Agent（可选）
      onEvent(app.app_id, 'english.word_lookup', { word });
    }
  }, [app.payload?.incoming_word, app.payload?.incoming_timestamp]);
  
  const handleWordSelect = useCallback((word: string) => {
    setSelectedWord(word);
    onEvent(app.app_id, 'english.word_select', { word, library: selectedLibrary });
  }, [app.app_id, onEvent, selectedLibrary]);
  
  return (
    <div className="english-workspace">
      <div className="ew-toolbar">
        <Languages size={16} />
        <span>英语工作区</span>
        {incomingWord && (
          <span className="ew-incoming-badge">
            正在查看：{incomingWord}
          </span>
        )}
        <div className="ew-tabs">
          {(['fission', 'quiz', 'chat', 'plan'] as const).map(tab => (
            <button 
              key={tab} 
              className={activeTab === tab ? 'active' : ''} 
              onClick={() => setActiveTab(tab)}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>
      </div>
      
      <div className="ew-layout">
        {/* 左列：单词列表 */}
        <div className="ew-left">
          <WordList
            onWordSelect={handleWordSelect}
            selectedWord={selectedWord}
            selectedLibrary={selectedLibrary}
            onLibraryChange={setSelectedLibrary}
            highlightWord={incomingWord} // 高亮传入的单词
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

---

## 五、AIChatPanel 对接 LearnForge Agent（废弃原 DeepSeek）

```tsx
// AIChatPanel.tsx

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
    
    try {
      await streamChatMessage(
        userMessage,
        (event: AgentStreamEvent) => {
          switch (event.type) {
            case 'assistant.delta':
              setStreamingText(prev => prev + event.text);
              break;
            case 'run.step':
              if (event.detail) {
                setStreamingText(prev => prev + `\n[${event.step_name}: ${event.detail}]\n`);
              }
              break;
            case 'app.update':
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
      
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: streamingText || '抱歉，我暂时无法回答这个问题。'
      }]);
      setStreamingText('');
      
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
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

---

## 六、EnglishAgent 实现（使用 LearnForge LLM）

```python
# services/api/app/agents/english_agent.py

import json
from typing import Optional

class EnglishAgent:
    """处理英语学习相关的 Agent，直接调用 LearnForge 的 LLM（Gemini）"""
    
    def __init__(self, mem0_client, word_service, llm):
        self.mem0 = mem0_client
        self.word_service = word_service
        self.llm = llm  # LearnForge 的 LLM 生成器
    
    async def handle_chat(self, student_id: str, word: Optional[str], message: str, 
                          history: list, stream_callback=None) -> str:
        """处理英语工作区中的 AI 聊天"""
        
        # 1. 获取学生的英语记忆上下文
        context = self._get_english_context(student_id)
        
        # 2. 获取单词详情（如果 word 不为空）
        word_detail = None
        if word:
            word_detail = await self.word_service.get_word_detail(word)
        
        # 3. 从 english-word-fission 获取学习历史
        user_context = await self.word_service.get_user_context(student_id)
        
        # 4. 构建增强 prompt
        prompt_parts = ["你是一位专业的英语教师。"]
        
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
        from app.hermes_runtime import generate_stream
        response = await generate_stream(
            prompt=prompt,
            model_provider="gemini",
            temperature=0.7,
            stream_callback=stream_callback
        )
        
        # 6. 记录到 EduMem0
        await self._analyze_and_record_memory(student_id, word, message, response)
        
        return response
    
    async def _analyze_and_record_memory(self, student_id: str, word: Optional[str], 
                                           user_message: str, assistant_response: str):
        """分析对话，自动记录记忆"""
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
                await self.mem0.add_memory(
                    student_id=student_id,
                    memory_type="misconception",
                    content=f"单词 {word} 掌握薄弱：{result.get('error_type')}",
                    structured_payload={"subject": "english", "topic": word, "error_type": result.get("error_type")},
                    confidence=0.7,
                    tags=["english", "vocabulary", "weak"]
                )
            
            if result.get("has_progress") and word:
                await self.mem0.add_memory(
                    student_id=student_id,
                    memory_type="mastery",
                    content=f"单词 {word} 掌握良好",
                    structured_payload={"subject": "english", "topic": word, "score": 0.85},
                    confidence=0.85,
                    tags=["english", "vocabulary", "mastered"]
                )
        except:
            pass
```

---

## 七、实施优先级

| 优先级 | 任务 | 工时 | 说明 |
|--------|------|------|------|
| **P0** | 全局浮动选词工具条（SelectionToolbar） | 1.5h | 任意应用中选词即可调起 |
| **P0** | HTML iframe 内选词桥接（bridge script） | 1h | 在 iframe 内也能选词 |
| **P0** | LearnForgeShell 处理 `english:lookup` | 1h | 创建或聚焦英语工作区 |
| **P0** | EnglishWorkspaceApp 接收 `incoming_word` | 0.5h | 自动聚焦传入的单词 |
| **P1** | AIChatPanel 对接 LearnForge Agent | 1.5h | 废弃 DeepSeek，用 streamChatMessage |
| **P1** | EnglishAgent 实现 | 2h | 使用 LearnForge LLM，集成 EduMem0 |
| **P1** | Orchestrator 注册 EnglishAgent | 0.5h | 添加英语意图检测和路由 |
| **P2** | 测验/裂变图/单词列表组件提取 | 3h | 从原项目提取到 LearnForge |
| **P2** | EduMem0 集成（测验记录同步） | 1h | 记录 mastery/misconception |
| **P2** | 测试覆盖 | 1h | 端到端测试 |

**总计：约 13 小时（1.5-2 天）**

---

## 八、关键设计决策

1. **废弃 DeepSeek 独立后端**：AI 聊天直接对接 LearnForge 的 `streamChatMessage`，使用 Gemini 模型，通过 `requestedSkill='english_chat'` 触发 EnglishAgent
2. **统一会话管理**：不再使用 `chat_sessions`/`chat_messages` 表，所有聊天历史由 LearnForge 统一会话系统管理
3. **全局选词检测**：在 `LearnForgeShell` 层面挂载 `SelectionToolbar`，覆盖所有应用（包括 HTML iframe 通过 postMessage 桥接）
4. **跨应用调起**：通过 `window.dispatchEvent(new CustomEvent('english:lookup', ...))` 全局事件，由 `LearnForgeShell` 统一处理窗口创建/聚焦
5. **英语工作区状态同步**：通过 `payload.incoming_word` 字段传递选中的单词，工作区自动切换到该单词的裂变图/详情/AI 聊天
