# LearnForge 沉浸式模式（Immersive Mode）融合规划

> 版本：2026-06-17  
> 目标：将 english-word-fission 的 `immersive/page.tsx` 全屏裂变图 + 浮动面板体验融入 LearnForge 的 SpatialCanvas 窗口体系

---

## 一、原系统 Immersive 模式分析

```
src/app/immersive/page.tsx
├── 全屏黑色背景 bg-black
├── 全屏 FissionGraph (w-screen h-screen, 居中 svg, 全屏交互)
├── 浮动 DraggableContainer (WordList) — 左下角, 400×600, 可拖拽/缩放/最小化
├── 浮动 DraggableContainer (WordDetail) — 右下角, 400×600, 可拖拽/缩放/最小化
└── 返回 Dashboard 的浮动按钮

src/components/ImmersiveToggle.tsx
├── 浮动圆形按钮 (fixed bottom-6 right-6)
├── 点击切换 /immersive ↔ / 路由
└── 带 URL 参数传递 currentWord
```

**核心体验：**
1. 裂变图占满全屏，作为背景
2. 所有 UI 悬浮在裂变图之上（玻璃态面板）
3. 面板可拖拽、缩放、最小化
4. 视觉上"完全沉浸"，无标题栏、无 Dock、无多余元素

---

## 二、融合方案：复用 LearnForge 的 `pageFullscreenId` 机制

### 核心洞察

LearnForge 的 `SpatialCanvas` 已经完美支持 Immersive 所需的所有能力：

| 原系统功能 | LearnForge 等价物 | 状态 |
|----------|------------------|------|
| 全屏黑色背景 | `pageFullscreenId` 的 CSS 覆盖 + `backdrop-blur-3xl bg-black` | ✅ 已存在 |
| 全屏裂变图 | CanvasApp 窗口进入 `pageFullscreen` | ✅ 已存在 |
| 可拖拽浮动面板 | `CanvasApp` 窗口本身支持拖拽 + 缩放 | ✅ 已存在 |
| 最小化面板 | `minimizeApp` / `minimizeId` 机制 | ✅ 已存在 |
| 浮动按钮 | `DockToggle` 在 `pageFullscreen` 模式下一直显示 | ✅ 已存在 |
| 返回普通模式 | 按 ESC 或点击浮动按钮退出全屏 | ✅ 已存在 |

**所以不需要新建页面，只需要在现有窗口内实现"沉浸式视图模式"。**

---

## 三、具体融合方案

### 方案A：裂变图窗口的沉浸式模式（推荐）

**场景：** 用户在英语工作区中点击裂变图 Tab → 裂变图窗口内有一个"沉浸模式"按钮 → 点击后该窗口进入 `pageFullscreen`

```
英语工作区窗口 (CanvasApp)
├── Tab1: 单词列表
├── Tab2: 裂变图
│   ├── 裂变图渲染区域 (FissionGraph)
│   └── 工具栏：["沉浸模式"按钮]
│
沉浸模式按钮 → 触发 pageFullscreen(appId)
│
进入 pageFullscreen 后：
├── 整个窗口占满屏幕 (fixed inset 0, zIndex 1200)
├── 背景变为黑色 (#000000)
├── 裂变图占满全屏 (w-full h-full)
├── 单词列表和详情作为子窗口浮在上方（通过位置偏移）
└── 左下角显示最小化 Dock（可点击最小化）
```

**技术实现：**

在 `EnglishWorkspaceApp` 内部实现一个 `ImmersiveView` 组件：

```tsx
// 英语工作区内部状态
const [immersiveMode, setImmersiveMode] = useState(false);

// 点击沉浸模式按钮
const enterImmersive = () => {
  // 1. 通知 SpatialCanvas：这个窗口需要 pageFullscreen
  onEvent(appId, 'window.pageFullscreen', { enabled: true });
  
  // 2. 切换内部状态，改变布局
  setImmersiveMode(true);
};

// 英语工作区布局根据 immersiveMode 切换
{immersiveMode ? (
  <ImmersiveLayout 
    selectedWord={selectedWord}
    onWordSelect={handleWordSelect}
    onExit={() => {
      setImmersiveMode(false);
      onEvent(appId, 'window.pageFullscreen', { enabled: false });
    }}
  />
) : (
  <StandardLayout ... />
)}
```

`ImmersiveLayout` 内部结构：

```tsx
function ImmersiveLayout({ selectedWord, onWordSelect, onExit }) {
  return (
    <div className="w-full h-full bg-black relative overflow-hidden">
      {/* 全屏裂变图背景 */}
      <div className="absolute inset-0">
        <FissionGraph 
          centerWord={selectedWord} 
          width={window.innerWidth} 
          height={window.innerHeight}
        />
      </div>
      
      {/* 浮动单词列表面板（仿 DraggableContainer）*/}
      <FloatingPanel
        title="单词列表"
        initialPosition={{ x: 20, y: window.innerHeight - 620 }}
        initialSize={{ width: 400, height: 600 }}
      >
        <WordList onSelect={onWordSelect} highlightWord={selectedWord} />
      </FloatingPanel>
      
      {/* 浮动单词详情面板 */}
      <FloatingPanel
        title="单词详情"
        initialPosition={{ x: window.innerWidth - 420, y: 20 }}
        initialSize={{ width: 400, height: 500 }}
      >
        <WordDetail word={selectedWord} />
      </FloatingPanel>
      
      {/* 退出沉浸模式按钮 */}
      <button 
        className="fixed bottom-6 right-6 z-50 p-4 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-xl"
        onClick={onExit}
      >
        <LayoutDashboard size={24} />
      </button>
    </div>
  );
}
```

**`FloatingPanel` 组件（提取自 `DraggableContainer`）：**

```tsx
// apps/web/src/features/learning-apps/english/components/FloatingPanel.tsx
// 直接复用 english-word-fission 的 DraggableContainer 组件
// 将 glassmorphism 样式应用到 LearnForge 的窗口上
// 支持：拖拽标题栏、8方向缩放、最小化、关闭

// 样式复用：
// background: rgba(20, 20, 20, 0.25)
// backdropFilter: blur(20px) saturate(180%)
// border: 1px solid rgba(255, 255, 255, 0.08)
// boxShadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5)
// 标题栏：bg-gradient-to-b from-white/5 to-transparent
```

---

### 方案B：从全局选词直接进入沉浸模式

**场景：** 用户在 HTML 阅读器中选中一个英文单词 → 浮动工具条点击"查单词" → 英语工作区创建并进入沉浸模式

```tsx
// LearnForgeShell 处理 english:lookup
function handleEnglishLookup(word: string) {
  // 1. 查找或创建英语工作区
  const existingApp = canvasApps.find(a => a.app_type === 'english.workspace');
  
  if (existingApp) {
    // 2a. 已存在 → 进入沉浸模式 + 设置单词
    onEvent(existingApp.id, 'english.setImmersive', { word });
    pageFullscreenAppId(existingApp.id); // 让 SpatialCanvas 进入 pageFullscreen
  } else {
    // 2b. 不存在 → 创建新窗口，直接进入沉浸模式
    const newApp = createCanvasApp({
      app_type: 'english.workspace',
      payload: { incoming_word: word, initial_mode: 'immersive' }
    });
    pageFullscreenAppId(newApp.id);
  }
}
```

---

### 方案C：Link图（裂变图）作为英语工作区内部功能

**场景：** 在英语工作区的裂变图 Tab 中，点击"沉浸模式"按钮 → 窗口进入 `pageFullscreen`，裂变图占满全屏

**说明：** Link图（裂变图沉浸模式）是英语工作区的内部功能，不在 Dock 上有独立按钮。用户从英语工作区内部进入沉浸模式。

**Dock 布局（中间区域只放两个系统应用）：**
```
Dock:
[画像][仪表][资源] │ [文科] [英语] │ [PPT][图解][视频] │ [📁][📁]
```

**Link图沉浸模式的入口：**
- 英语工作区 → 裂变图 Tab → "沉浸模式"按钮 → 进入 `pageFullscreen`
- 或：全局选词 → "在 Link图查看" → 英语工作区创建并直接进入沉浸模式
- 或：全局选词 → "在 Link图查看" → 英语工作区创建并直接进入沉浸模式

**说明：** Link图（裂变图沉浸模式）是英语工作区的内部功能，不在 Dock 上有独立按钮。

---

## 四、推荐方案：方案A + 方案C 的组合

| 模式 | 触发方式 | 用途 |
|------|----------|------|
| **英语工作区沉浸模式** | 英语工作区内部按钮 | 在已有英语工作区中临时进入沉浸学习 |
| **全局选词沉浸模式** | 全局选词 → "在 Link图查看" | 快速查看单词关系网络，直接进入沉浸模式 |

### 组合场景示例

```
场景1：在 HTML 阅读器中阅读英文论文
  → 选中单词 "fission"
  → 浮动工具条：["查单词" | "在 Link图查看"]
  → 点击"在 Link图查看" → 打开英语工作区并直接进入沉浸模式
  → 裂变图以 "fission" 为中心展开
  → 浮动面板显示单词列表和详情
  → 按 ESC 退出沉浸模式，回到英语工作区正常视图

场景2：在英语工作区中学习
  → 切换到裂变图 Tab
  → 点击"沉浸模式"按钮
  → 窗口进入 pageFullscreen，裂变图占满全屏
  → 继续拖拽面板学习
  → 按 ESC 退出沉浸模式
```

---

## 五、需要修改的文件

### 前端

| 文件 | 修改 | 说明 |
|------|------|------|
| `packages/app-protocol/src/types.ts` | 新增 `english.fission_graph` | 独立裂变图窗口类型 |
| `services/api/app/schemas/app_protocol.py` | 新增 `english.fission_graph` | 后端类型同步 |
| `apps/web/src/features/learning-apps/NativeAppRenderer.tsx` | 新增 `english.fission_graph` 分支 | 渲染独立裂变图窗口 |
| `apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx` | 新增 `ImmersiveLayout` 组件 | 沉浸模式内部布局 |
| `apps/web/src/features/learning-apps/english/components/FloatingPanel.tsx` | **新文件** | 从 `DraggableContainer` 提取玻璃态浮动面板 |
| `apps/web/src/features/learning-apps/english/components/FissionGraph.tsx` | 提取自原项目 | 适配 CanvasApp 尺寸 |
| `apps/web/src/app/LearnForgeShell.tsx` | 处理 `english.setImmersive` 事件 | 支持外部触发沉浸模式 |
| `apps/web/src/features/app-canvas/SpatialCanvas.tsx` | 确认 `pageFullscreen` 对沉浸模式的支持 | 可能不需要修改 |
| `apps/web/src/app/styles.css` | 新增 `.glass-panel` 样式 | 玻璃态浮动面板 |

### 后端

无需新增后端文件（Link图沉浸模式是英语工作区内部功能）。

---

## 六、视觉设计规格

### 沉浸模式色彩

| 元素 | 颜色 | 说明 |
|------|------|------|
| 背景 | `#000000` | 纯黑，最大化裂变图粒子对比度 |
| 浮动面板背景 | `rgba(20, 20, 20, 0.25)` | 玻璃态，背景可见但降低干扰 |
| 面板边框 | `rgba(255, 255, 255, 0.08)` | 极细边框，不抢眼 |
| 面板标题 | `rgba(255, 255, 255, 0.9)` | 白色文字 + 文字阴影 |
| 面板阴影 | `0 25px 50px -12px rgba(0, 0, 0, 0.5)` | 深度阴影，漂浮感 |
| 裂变图粒子 | 原版色彩 | 继承原系统配色 |
| 退出按钮 | `bg-white/10 hover:bg-white/20` | 半透明，hover 高亮 |

### 交互细节

1. **进入沉浸模式**：300ms ease-in-out 过渡，窗口从正常尺寸扩展到全屏
2. **浮动面板**：拖拽时显示半透明边框，松手后恢复玻璃态
3. **最小化面板**：收缩为标题栏圆点（类似 macOS Dock），点击恢复
4. **ESC 退出**：监听 ESC 键，退出 pageFullscreen
5. **单词联动**：选中单词时，裂变图平滑过渡到新中心（d3-force 动画）

---

## 七、实施优先级

| 阶段 | 任务 | 工时 | 说明 |
|------|------|------|------|
| **P0** | `FloatingPanel` 组件提取 | 1h | 从 `DraggableContainer` 提取玻璃态浮动面板 |
| **P0** | 英语工作区沉浸模式布局 | 1.5h | `ImmersiveLayout` + 内部切换逻辑 |
| **P0** | 与 `pageFullscreen` 集成 | 1h | 触发 `pageFullscreen` 事件 + ESC 退出 |
| **P1** | 全局选词 → 在 Link图查看 | 1h | 浮动工具条新增按钮 + 事件处理 |
| **P2** | 动画与视觉优化 | 1h | 过渡动画、粒子响应 |
| **P2** | 测试 | 1h | 沉浸模式进入/退出、单词联动、面板拖拽 |

**总计：约 6.5 小时（1 天）**

---

## 八、风险与注意事项

| 风险 | 说明 | 缓解方案 |
|------|------|----------|
| **原系统的 `FissionGraph` 依赖 `d3-force` 和 `canvas` 尺寸** | 全屏时尺寸变化可能触发重计算 | 监听 `window.resize`，防抖重渲染 |
| **玻璃态面板在 CanvasApp 内部 zIndex 冲突** | 面板被其他窗口遮挡 | 确保沉浸模式下面板 zIndex 高于其他窗口 |
| **pageFullscreen 模式下 Dock 被隐藏** | 用户找不到退出按钮 | 最小化 Dock 在左下角保留，+ 退出按钮 |
| **多窗口同时 pageFullscreen 冲突** | 只能一个窗口全屏 | 进入沉浸模式时关闭其他全屏窗口 |
| **原系统的 `FissionGraph` 有 `isImmersive` 参数** | 用于调整布局 | 直接映射为 `immersiveMode` 状态 |

---

## 九、与原系统的对比

| 维度 | 原系统 (`immersive/page.tsx`) | LearnForge 融合方案 |
|------|------------------------------|-------------------|
| 路由方式 | 独立页面 `/immersive` | 窗口内视图模式（无路由切换） |
| 背景 | 纯黑 `bg-black` | 纯黑 + `backdrop-blur` |
| 浮动面板 | `DraggableContainer` 固定定位 | `FloatingPanel` 在 CanvasApp 内 |
| 切换方式 | 按钮跳转路由 | 按钮触发 `pageFullscreen` |
| 与主系统关系 | 完全独立，状态丢失 | 保持在 CanvasApp 内，状态连续 |
| 窗口管理 | 无 | 支持最小化、拖拽、缩放、关闭 |
| 多任务 | 不支持 | 支持（沉浸式窗口 + 其他窗口） |
| 记忆集成 | 无 |  EduMem0 记录沉浸式学习行为 |

**核心优势：原系统的沉浸式体验被完整保留，但 LearnForge 的窗口管理让体验更灵活、多任务友好。**
