import React from "react";
import { act } from "react-dom/test-utils";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import type { CanvasApp, CanvasViewport, ChatAppLink, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";
import { NativeAppRenderer } from "../src/features/learning-apps/NativeAppRenderer";
import { SpatialCanvas } from "../src/features/app-canvas/SpatialCanvas";
import { AppLinkChip } from "../src/features/applink-flight/AppLinkChip";
import { RichMessageContent } from "../src/features/tutor-chat/RichMessageContent";
import { normalizeLatexForHtml } from "../src/features/custom-html-app/CustomHtmlAppRenderer";
import { TutorChat } from "../src/features/tutor-chat/TutorChat";
import { ChatComposer } from "../src/components/chat/ChatComposer";
import { buildResourceCanvasAppRequest } from "../src/app/LearnForgeApp";
import { DEFAULT_SESSION_CONTEXT, patchApp } from "../src/lib/api/client";
import type { ChatMessage, TraceItem } from "../src/lib/events/agentEvents";

vi.mock("../src/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("../src/lib/api/client")>("../src/lib/api/client");
  return {
    ...actual,
    fetchNotebookLMStatus: vi.fn(async () => ({ status: "ready", provider: "open_notebook", embed_url: "http://localhost:8502?embed=learnforge&mode=sources" })),
    fetchNotebookLMNotebooks: vi.fn(async () => [
      { id: "nblm-course", title: "人工智能导论 · 课程知识库", purpose: "course_official", owner_scope: "course", owner_id: "ai-course", source_count: 1, tags: ["课程正式资料"] },
      { id: "nblm-personal", title: "我的复习 Notebook", purpose: "personal_review", owner_scope: "user", owner_id: "demo-student", source_count: 1, tags: ["我的上传"] },
    ]),
    bootstrapNotebookLM: vi.fn(async (_context, notebookId?: string) => ({ status: "ready", notebook_id: `open-${notebookId || "course"}`, learnforge_notebook_id: notebookId, embed_url: "http://localhost:8502?embed=learnforge&mode=sources" })),
    fetchNotebookLMNotebookSources: vi.fn(async (notebookId: string) => ({
      notebook: { id: notebookId, title: "我的复习 Notebook", purpose: "personal_review", owner_scope: "user", owner_id: "demo-student", source_count: 1 },
      sources: [
        { id: "src-one", title: "第一章讲义", summary: "导论片段", chunk_count: 1, source_refs: [{ document_id: "src-one", chunk_id: "chunk-one", title: "第一章讲义", snippet: "导论片段" }], source_scope: "personal_notebook", ingest_type: "text", sync_status: "ready" },
      ],
    })),
    createNotebookLMNotebook: vi.fn(async () => ({ id: "nblm-new", title: "新的复习 Notebook", purpose: "personal_review", owner_scope: "user", owner_id: "demo-student", source_count: 0 })),
    syncNotebookLMNotebook: vi.fn(async () => ({ status: "ready", synced: [], blocked: [] })),
    addNotebookLMLinkSource: vi.fn(async () => ({ status: "ready" })),
    addNotebookLMTextSource: vi.fn(async () => ({ status: "ready" })),
    uploadNotebookLMFileSource: vi.fn(async () => ({ status: "ready" })),
    patchApp: vi.fn(async (_appId: string, patch: Record<string, unknown>) => ({
      app_id: _appId,
      app_type: "dashboard.learning",
      title: "updated",
      status: "ready",
      render_mode: "native_react",
      state: "window",
      position: patch.position ?? { x: 0, y: 0 },
      size: patch.size ?? { width: 360, height: 280 },
      z_index: 1,
      payload: {},
      source: {},
      source_refs: [],
      actions: [],
      created_at: "now",
      updated_at: "now",
    })),
  };
});

function render(node: React.ReactNode) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return {
    host,
    rerender: (next: React.ReactNode) => act(() => root.render(next)),
    cleanup: () => act(() => root.unmount()),
  };
}

function pointerEvent(type: string, init: { clientX: number; clientY: number; pointerId?: number }) {
  const event = new MouseEvent(type, { bubbles: true, clientX: init.clientX, clientY: init.clientY }) as MouseEvent & { pointerId: number };
  Object.defineProperty(event, "pointerId", { value: init.pointerId ?? 1 });
  return event;
}

function installPointerRuntime() {
  const previousRaf = window.requestAnimationFrame;
  const previousCancel = window.cancelAnimationFrame;
  const previousCapture = HTMLElement.prototype.setPointerCapture;
  window.requestAnimationFrame = ((callback: FrameRequestCallback) => {
    callback(0);
    return 1;
  }) as typeof window.requestAnimationFrame;
  window.cancelAnimationFrame = vi.fn() as typeof window.cancelAnimationFrame;
  Object.defineProperty(HTMLElement.prototype, "setPointerCapture", { configurable: true, value: vi.fn() });
  return () => {
    window.requestAnimationFrame = previousRaf;
    window.cancelAnimationFrame = previousCancel;
    if (previousCapture) {
      Object.defineProperty(HTMLElement.prototype, "setPointerCapture", { configurable: true, value: previousCapture });
    } else {
      delete (HTMLElement.prototype as Partial<HTMLElement>).setPointerCapture;
    }
  };
}

const dashboard: DashboardSnapshot = {
  student_id: "demo-student",
  profile: { major: "软件工程", weak_points: ["数学推导"] },
  mastery: { "kp-optimization": 0.42 },
  weak_points: ["数学推导"],
  recommendations: [],
  memory_evidence: [
    {
      id: "mem-1",
      student_id: "demo-student",
      memory_type: "profile",
      content: "偏好图解和代码",
      structured_payload: {},
      confidence: 0.7,
      evidence_type: "chat",
      importance: 0.8,
      decay_rate: 0,
      tags: [],
      created_at: "now",
      updated_at: "now"
    }
  ],
  recent_runs: [],
  path_progress: 0.32
};

const app: CanvasApp = {
  app_id: "app-dashboard",
  app_type: "dashboard.learning",
  title: "仪表盘",
  status: "ready",
  render_mode: "native_react",
  state: "window",
  position: { x: 0, y: 0 },
  size: { width: 360, height: 280 },
  z_index: 1,
  payload: {},
  source: {},
  source_refs: [],
  actions: [],
  created_at: "now",
  updated_at: "now"
};

describe("component behavior", () => {
  it("drags app windows with an imperative preview and commits layout once on pointerup", () => {
    const restorePointerRuntime = installPointerRuntime();
    const floatingApp: CanvasApp = {
      ...app,
      app_id: "app-free",
      app_type: "notes.session",
      title: "自由窗口",
      position: { x: 100, y: 120 },
      size: { width: 360, height: 280 },
    };
    const setApps = vi.fn();
    const focusWindow = vi.fn();
    const onAppEvent = vi.fn();
    const patchAppMock = vi.mocked(patchApp);
    patchAppMock.mockClear();
    const viewport: CanvasViewport = { x: 0, y: 0, scale: 1 };
    const canvas = (
      <SpatialCanvas
        apps={[floatingApp]}
        dashboard={dashboard}
        viewport={viewport}
        setViewport={() => undefined}
        setApps={setApps}
        openWindowIds={["app-free"]}
        focusedId="app-free"
        fullscreenId={null}
        zOrder={["app-free"]}
        openWindow={() => undefined}
        closeWindow={() => undefined}
        focusWindow={focusWindow}
        toggleFullscreen={() => undefined}
        deleteApp={() => undefined}
        onAppEvent={onAppEvent}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const { host, rerender, cleanup } = render(canvas);
    const titlebar = host.querySelector(".app-titlebar") as HTMLElement;
    const frame = host.querySelector('[data-window-frame="app-free"]') as HTMLElement;

    act(() => titlebar.dispatchEvent(pointerEvent("pointerdown", { clientX: 10, clientY: 20, pointerId: 7 })));
    act(() => window.dispatchEvent(pointerEvent("pointermove", { clientX: 25, clientY: 32, pointerId: 7 })));

    expect(frame.style.transform).toBe("translate3d(15px, 12px, 0)");
    expect(setApps).not.toHaveBeenCalled();
    rerender(canvas);
    expect(frame.style.transform).toBe("translate3d(15px, 12px, 0)");

    act(() => window.dispatchEvent(pointerEvent("pointerup", { clientX: 25, clientY: 32, pointerId: 7 })));

    expect(setApps).toHaveBeenCalledTimes(1);
    const committed = setApps.mock.calls[0][0] as CanvasApp[];
    expect(committed[0].position).toEqual({ x: 115, y: 132 });
    expect(patchAppMock).toHaveBeenCalledWith(
      "app-free",
      expect.objectContaining({ position: { x: 115, y: 132 } }),
      DEFAULT_SESSION_CONTEXT
    );
    expect(onAppEvent).toHaveBeenCalledWith(
      "app-free",
      "layout.drag",
      expect.objectContaining({ position: { x: 115, y: 132 } })
    );
    cleanup();
    restorePointerRuntime();
  });

  it("resizes app windows with an imperative preview and commits final size once", () => {
    const restorePointerRuntime = installPointerRuntime();
    const floatingApp: CanvasApp = {
      ...app,
      app_id: "app-resize",
      app_type: "notes.session",
      title: "可缩放窗口",
      position: { x: 80, y: 90 },
      size: { width: 360, height: 280 },
    };
    const setApps = vi.fn();
    const onAppEvent = vi.fn();
    const patchAppMock = vi.mocked(patchApp);
    patchAppMock.mockClear();
    const viewport: CanvasViewport = { x: 0, y: 0, scale: 1 };
    const { host, cleanup } = render(
      <SpatialCanvas
        apps={[floatingApp]}
        dashboard={dashboard}
        viewport={viewport}
        setViewport={() => undefined}
        setApps={setApps}
        openWindowIds={["app-resize"]}
        focusedId="app-resize"
        fullscreenId={null}
        zOrder={["app-resize"]}
        openWindow={() => undefined}
        closeWindow={() => undefined}
        focusWindow={() => undefined}
        toggleFullscreen={() => undefined}
        deleteApp={() => undefined}
        onAppEvent={onAppEvent}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const handle = host.querySelector(".resize-handle") as HTMLElement;
    const frame = host.querySelector('[data-window-frame="app-resize"]') as HTMLElement;

    act(() => handle.dispatchEvent(pointerEvent("pointerdown", { clientX: 100, clientY: 100, pointerId: 8 })));
    act(() => window.dispatchEvent(pointerEvent("pointermove", { clientX: 145, clientY: 130, pointerId: 8 })));

    expect(frame.style.width).toBe("405px");
    expect(frame.style.height).toBe("310px");
    expect(setApps).not.toHaveBeenCalled();

    act(() => window.dispatchEvent(pointerEvent("pointerup", { clientX: 145, clientY: 130, pointerId: 8 })));

    expect(setApps).toHaveBeenCalledTimes(1);
    const committed = setApps.mock.calls[0][0] as CanvasApp[];
    expect(committed[0].size).toEqual({ width: 405, height: 310 });
    expect(patchAppMock).toHaveBeenCalledWith(
      "app-resize",
      expect.objectContaining({ size: { width: 405, height: 310 } }),
      DEFAULT_SESSION_CONTEXT
    );
    expect(onAppEvent).toHaveBeenCalledWith(
      "app-resize",
      "layout.resize",
      expect.objectContaining({ size: { width: 405, height: 310 } })
    );
    cleanup();
    restorePointerRuntime();
  });

  it("renders NotebookLM inside the transformed canvas world so it follows pan and zoom", async () => {
    const notebookApp: CanvasApp = {
      ...app,
      app_id: "app-notebooklm-canvas",
      app_type: "notebooklm.workspace",
      title: "NotebookLM",
      position: { x: 420, y: 260 },
      size: { width: 900, height: 620 },
    };
    const viewport: CanvasViewport = { x: -30, y: -20, scale: 0.72 };
    const { host, cleanup } = render(
      <SpatialCanvas
        apps={[notebookApp]}
        dashboard={dashboard}
        viewport={viewport}
        setViewport={() => undefined}
        setApps={() => undefined}
        openWindowIds={["app-notebooklm-canvas"]}
        focusedId="app-notebooklm-canvas"
        fullscreenId={null}
        zOrder={["app-notebooklm-canvas"]}
        openWindow={() => undefined}
        closeWindow={() => undefined}
        focusWindow={() => undefined}
        toggleFullscreen={() => undefined}
        deleteApp={() => undefined}
        onAppEvent={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const world = host.querySelector(".canvas-world") as HTMLElement;
    const nativeLayer = host.querySelector(".native-app-layer") as HTMLElement;
    const frame = host.querySelector('[data-window-frame="app-notebooklm-canvas"]') as HTMLElement;

    expect(frame).toBeTruthy();
    expect(world.contains(frame)).toBe(true);
    expect(nativeLayer.contains(frame)).toBe(false);
    expect(frame.classList.contains("native-window-frame")).toBe(false);
    cleanup();
  });

  it("renders dashboard memory evidence", () => {
    const { host, cleanup } = render(<NativeAppRenderer app={app} dashboard={dashboard} onEvent={() => undefined} onFocusApp={() => undefined} sessionContext={DEFAULT_SESSION_CONTEXT} />);
    expect(host.textContent).toContain("偏好图解和代码");
    expect(host.textContent).toContain("70%");
    expect(host.textContent).toContain("聊天记录");
    expect(host.querySelector("[data-testid='memory-evidence']")).toBeTruthy();
    expect(host.querySelector("[data-testid='memory-evidence-profile']")).toBeTruthy();
    cleanup();
  });

  it("renders profile coverage and evidence summary", () => {
    const profileApp = { ...app, app_id: "app-profile", app_type: "profile.dashboard" as const };
    const { host, cleanup } = render(<NativeAppRenderer app={profileApp} dashboard={dashboard} onEvent={() => undefined} onFocusApp={() => undefined} sessionContext={DEFAULT_SESSION_CONTEXT} />);
    expect(host.querySelector("[data-testid='profile-dashboard']")).toBeTruthy();
    expect(host.textContent).toContain("画像覆盖");
    expect(host.textContent).toContain("证据链");
    cleanup();
  });

  it("renders NotebookLM as a two-column source workbench with uploads in a secondary view", async () => {
    const notebookApp: CanvasApp = {
      ...app,
      app_id: "app-notebooklm-test",
      app_type: "notebooklm.workspace",
      title: "NotebookLM",
    };
    const { host, cleanup } = render(
      <NativeAppRenderer app={notebookApp} dashboard={dashboard} onEvent={() => undefined} onFocusApp={() => undefined} sessionContext={DEFAULT_SESSION_CONTEXT} />
    );
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(host.querySelector("[data-testid='notebooklm-workspace']")).toBeTruthy();
    expect(host.querySelector("[data-testid='notebooklm-notebooks']")).toBeTruthy();
    expect(host.querySelector("[data-testid='notebooklm-sources']")).toBeTruthy();
    expect(host.querySelector(".nblm-actions")).toBeFalsy();
    expect(host.textContent).toContain("课程知识库");
    expect(host.textContent).toContain("我的 Notebook");
    expect(host.textContent).toContain("生成");
    expect(host.querySelector("[data-testid='notebooklm-source-manager']")).toBeFalsy();
    expect(host.querySelector("[data-testid='notebooklm-generate-menu']")).toBeFalsy();
    expect(host.textContent).not.toContain("上传文件");
    expect(host.textContent).not.toContain("添加链接");
    expect(host.textContent).not.toContain("粘贴文本");

    act(() => (host.querySelector("[data-testid='notebooklm-manage-sources']") as HTMLButtonElement).click());
    expect(host.querySelector("[data-testid='notebooklm-source-manager']")).toBeTruthy();
    expect(host.textContent).toContain("上传文件");
    expect(host.textContent).toContain("添加链接");
    expect(host.textContent).toContain("粘贴文本");

    act(() => (host.querySelector("[data-testid='notebooklm-generate-button']") as HTMLButtonElement).click());
    expect(host.querySelector("[data-testid='notebooklm-generate-menu']")).toBeTruthy();
    expect(host.textContent).toContain("学习指南");
    expect(host.querySelector(".chat-composer")).toBeFalsy();
    cleanup();
  });

  it("opens AppLink chip with its bounding rect", () => {
    let opened = "";
    const { host, cleanup } = render(
      <AppLinkChip
        link={{ link_id: "l1", message_id: "m1", app_id: "app-gradient", label: "打开实验台", action: "focus", created_at: "now" }}
        onOpen={(link) => {
          opened = link.app_id;
        }}
      />
    );
    act(() => (host.querySelector("button") as HTMLButtonElement).click());
    expect(opened).toBe("app-gradient");
    cleanup();
  });

  it("renders AI markdown and show-widget fences as rich content", () => {
    const markdown = [
      "### 📚 为你定制的学习路径",
      "1. **第一步：绕过公式**",
      "   - **目标**：先用互动实验理解梯度下降。",
      "",
      "```show-widget",
      "{\"widget_code\":\"<section><strong>训练流程</strong></section>\"}",
      "```"
    ].join("\n");
    const { host, cleanup } = render(<RichMessageContent text={markdown} />);
    expect(host.querySelector("h3")?.textContent).toContain("为你定制的学习路径");
    expect(host.querySelector("ol")).toBeTruthy();
    expect(host.querySelector("strong")?.textContent).toContain("第一步");
    expect(host.querySelector("[data-testid='custom-html-renderer']")).toBeTruthy();
    cleanup();
  });

  it("keeps full-document custom HTML layout in the sandbox", () => {
    const html = `<!doctype html>
<html>
  <head><meta name="viewport" content="width=device-width,initial-scale=1"><title>3D Demo</title></head>
  <body><main id="main-content"><aside id="controls">控制台</aside><section id="canvas-container"><canvas id="scene"></canvas></section></main></body>
</html>`;
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-full-doc",
      app_type: "custom.html",
      title: "可交互3D演示",
      size: { width: 900, height: 620 },
      payload: { html, artifact_kind: "interactive_model" },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe).toBeTruthy();
    expect(iframe?.srcdoc).toContain('id="main-content"');
    expect(iframe?.srcdoc).toContain('id="canvas-container"');
    expect(iframe?.srcdoc).toContain('<body>');
    expect(iframe?.srcdoc).not.toContain("MutationObserver");
    expect(iframe?.srcdoc).not.toContain("ResizeObserver");
    expect(iframe?.srcdoc).not.toContain("nudgeVisuals");
    expect(iframe?.srcdoc).not.toContain("window.dispatchEvent(new Event('resize'))");
    expect(iframe?.srcdoc).not.toContain('data-lf-runtime="math-renderer"');
    expect(iframe?.srcdoc).not.toContain("lf-generated-document");
    cleanup();
  });

  it("preserves legacy full-document interactive artifacts without front-end runtime resize", () => {
    const html = `<!doctype html>
<html>
  <head><title>气体扩散</title></head>
  <body>
    <main class="container">
      <h1>气体扩散物理模型动态实验室</h1>
      <canvas id="simCanvas" width="600" height="400"></canvas>
      <script>
        const p_red_left = 0.5;
        const canvas = document.getElementById('simCanvas');
        window.addEventListener('resize', () => { canvas.dataset.ownResize = String(p_red_left); });
      </script>
    </main>
  </body>
</html>`;
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-gas-legacy",
      app_type: "custom.html",
      title: "气体扩散动态模拟物理实验室",
      payload: { html, layout: "model_generated_interactive_demo" },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe?.srcdoc.match(/气体扩散物理模型动态实验室/g) ?? []).toHaveLength(1);
    expect(iframe?.srcdoc.match(/<canvas\b/g) ?? []).toHaveLength(1);
    expect(iframe?.srcdoc).toContain("window.addEventListener('resize'");
    expect(iframe?.srcdoc).not.toContain("window.dispatchEvent(new Event('resize'))");
    expect(iframe?.srcdoc).not.toContain("MutationObserver");
    expect(iframe?.srcdoc).not.toContain("ResizeObserver");
    expect(iframe?.srcdoc).not.toContain("nudgeVisuals");
    expect(iframe?.srcdoc).not.toContain('data-lf-runtime="math-renderer"');
    expect(iframe?.srcdoc).not.toContain("katex.min.js");
    cleanup();
  });

  it("injects math rendering runtime and normalizes escaped LaTeX in custom HTML", () => {
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-math",
      app_type: "custom.html",
      title: "公式报告",
      payload: {
        html: "<section><h1>动量守恒</h1><p>$\\\\frac{1}{2}mv_0^2$ 和 $E\\_k$</p></section>",
      },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe?.srcdoc).toContain("renderMathInElement");
    expect(iframe?.srcdoc).toContain("katex.min.js");
    expect(iframe?.srcdoc).toContain('data-lf-runtime="math-renderer"');
    expect(iframe?.srcdoc).toContain("$\\frac{1}{2}mv_0^2$");
    expect(iframe?.srcdoc).toContain("$E_k$");
    cleanup();
  });

  it("repairs LaTeX commands damaged by JSON escape decoding", () => {
    const damaged = "<section><p>$$h = frac12(m+M)v^2$$ $$\theta = arccos left(1 - frac{h}{l} right)$$ $$\text{式1}$$</p></section>";
    const normalized = normalizeLatexForHtml(damaged);

    expect(normalized).toContain("$$h = \\frac{1}{2}(m+M)v^2$$");
    expect(normalized).toContain("$$\\theta = \\arccos \\left(1 - \\frac{h}{l} \\right)$$");
    expect(normalized).toContain("$$\\text{式1}$$");
    expect(normalized).not.toContain("frac12");
  });

  it("does not inject math runtime into non-math interactive HTML", () => {
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-no-math",
      app_type: "custom.html",
      title: "气体实验室",
      payload: {
        html: "<section><h1>气体扩散动态模拟物理实验室</h1><canvas></canvas><button>暂停模拟</button></section>",
      },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe?.srcdoc).not.toContain('data-lf-runtime="math-renderer"');
    expect(iframe?.srcdoc).not.toContain("katex.min.js");
    expect(iframe?.srcdoc).not.toContain("lf-fit-root");
    expect(iframe?.srcdoc).not.toContain("lfFitScale");
    expect(iframe?.srcdoc).not.toContain("MutationObserver");
    expect(iframe?.srcdoc).not.toContain("ResizeObserver");
    expect(iframe?.srcdoc).not.toContain("nudgeVisuals");
    expect(iframe?.srcdoc).not.toContain("window.dispatchEvent(new Event('resize'))");
    cleanup();
  });

  it("suggestion buttons pass a structured requested skill", () => {
    const onGenerate = vi.fn();
    const { host, cleanup } = render(
      <RichMessageContent
        text={"讲解完成。\n\n[[generate:interactive_demo:动量守恒:demo]]生成动量守恒可交互模型[[/generate]]"}
        onGenerate={onGenerate}
      />
    );
    const button = host.querySelector("[data-testid='generate-suggestions'] button") as HTMLButtonElement | null;
    expect(button).toBeTruthy();
    act(() => button?.click());

    expect(onGenerate).toHaveBeenCalledWith(
      expect.stringContaining("动量守恒"),
      undefined,
      expect.objectContaining({ key: "demo", label: "生成动量守恒可交互模型" }),
    );
    cleanup();
  });

  it("detailed explanation suggestion passes the explain requested skill", () => {
    const onGenerate = vi.fn();
    const { host, cleanup } = render(
      <RichMessageContent
        text={"可以继续展开。\n\n[[generate:detailed_analysis:动量守恒:explain]]生成详细讲解[[/generate]]"}
        onGenerate={onGenerate}
      />
    );
    const button = host.querySelector("[data-testid='generate-suggestions'] button") as HTMLButtonElement | null;
    expect(button?.textContent).toContain("生成详细讲解");
    act(() => button?.click());

    expect(onGenerate).toHaveBeenCalledWith(
      "请基于动量守恒生成详细讲解",
      undefined,
      expect.objectContaining({ key: "explain", label: "生成详细讲解" }),
    );
    cleanup();
  });

  it("composer skill menu includes detailed explanation generation", () => {
    const onActiveSkillChange = vi.fn();
    const { host, cleanup } = render(
      <ChatComposer
        input=""
        onInputChange={() => undefined}
        onSubmit={() => undefined}
        isStreaming={false}
        attachments={[]}
        onAddFiles={() => undefined}
        onRemoveAttachment={() => undefined}
        listening={false}
        onToggleVoice={() => undefined}
        imageInputRef={React.createRef<HTMLInputElement>()}
        fileInputRef={React.createRef<HTMLInputElement>()}
        waveCanvasRef={React.createRef<HTMLCanvasElement>()}
        onActiveSkillChange={onActiveSkillChange}
        onSummarize={() => undefined}
      />
    );
    const trigger = host.querySelector("button[title='附加功能']") as HTMLButtonElement | null;
    act(() => trigger?.click());
    const detailedButton = Array.from(host.querySelectorAll(".composer-skill-item")).find((button) =>
      button.textContent?.includes("生成详细讲解"),
    ) as HTMLButtonElement | undefined;

    expect(detailedButton).toBeTruthy();
    act(() => detailedButton?.click());
    expect(onActiveSkillChange).toHaveBeenCalledWith(
      expect.objectContaining({
        key: "explain",
        label: "生成详细讲解",
        prompt: "请生成详细讲解，做成可在画布打开的 HTML 讲解报告",
      }),
    );
    cleanup();
  });

  it("injects LearnForge deck navigation bridge for custom HTML PPT decks", () => {
    const html = `<!doctype html>
<html>
  <head><title>Deck</title></head>
  <body><main class="deck"><section class="slide" data-layout="S01">第一页</section><section class="slide" data-layout="S02">第二页</section></main></body>
</html>`;
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-ppt-deck",
      app_type: "custom.html",
      title: "网页 PPT",
      payload: { html, deck_kind: "guizang-web-ppt" },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe).toBeTruthy();
    expect(iframe?.srcdoc).toContain("const ENABLE_DECK_BRIDGE = true;");
    expect(iframe?.srcdoc).toContain("window.LFDeck");
    expect(iframe?.srcdoc).toContain("deck:navigate");
    expect(iframe?.srcdoc).toContain("ArrowRight");
    expect(iframe?.getAttribute("sandbox")).not.toContain("allow-same-origin");
    cleanup();
  });

  it("forces deck navigation bridge from custom HTML PPT payload metadata", () => {
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-ppt-metadata",
      app_type: "custom.html",
      title: "网页 PPT",
      payload: {
        html: "<main><section>第一页</section><section>第二页</section></main>",
        deck_kind: "guizang-web-ppt",
      },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe?.srcdoc).toContain("window.LFDeck");
    expect(iframe?.srcdoc).toContain("const ENABLE_DECK_BRIDGE = true;");
    cleanup();
  });

  it("does not add a second deck controller when the generated PPT already handles navigation", () => {
    const html = `<!doctype html>
<html>
  <head><title>Deck</title></head>
  <body>
    <main class="deck"><section class="slide">第一页</section><section class="slide">第二页</section></main>
    <script>
      window.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowRight') document.querySelectorAll('.slide')[1].scrollIntoView({ behavior: 'smooth' });
      });
    </script>
  </body>
</html>`;
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-html-ppt-native-nav",
      app_type: "custom.html",
      title: "网页 PPT",
      payload: { html, deck_kind: "guizang-web-ppt" },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={htmlApp}
        isFullscreen
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const iframe = host.querySelector("[data-testid='custom-html-renderer']") as HTMLIFrameElement | null;

    expect(iframe?.srcdoc).toContain("const ENABLE_DECK_BRIDGE = false;");
    expect(iframe?.srcdoc).toContain("window.addEventListener('keydown'");
    cleanup();
  });

  it("shows a dedicated exit control for fullscreen custom HTML apps", () => {
    const htmlApp: CanvasApp = {
      ...app,
      app_id: "app-rubik",
      app_type: "custom.html",
      title: "可交互3D魔方还原演示模型",
      payload: { html: "<section>demo</section>" },
      actions: [{ label: "全屏演示", action: "custom.fullscreen" }],
    };
    const viewport: CanvasViewport = { x: 0, y: 0, scale: 1 };
    const toggleFullscreen = vi.fn();
    const { host, cleanup } = render(
      <SpatialCanvas
        apps={[htmlApp]}
        dashboard={dashboard}
        viewport={viewport}
        setViewport={() => undefined}
        setApps={() => undefined}
        openWindowIds={["app-rubik"]}
        focusedId="app-rubik"
        fullscreenId="app-rubik"
        zOrder={["app-rubik"]}
        openWindow={() => undefined}
        closeWindow={() => undefined}
        focusWindow={() => undefined}
        toggleFullscreen={toggleFullscreen}
        deleteApp={() => undefined}
        onAppEvent={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );
    const exit = host.querySelector(".fullscreen-exit-button") as HTMLButtonElement | null;

    expect(exit).toBeTruthy();
    expect(exit?.textContent).toContain("退出演示");
    act(() => exit?.click());
    expect(toggleFullscreen).toHaveBeenCalledWith("app-rubik");
    toggleFullscreen.mockClear();
    act(() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })));
    expect(toggleFullscreen).toHaveBeenCalledWith("app-rubik");
    cleanup();
  });

  it("renders generated artifact rail from event links even when messages have no links", () => {
    const messages: ChatMessage[] = [
      { id: "m1", role: "assistant", text: "我已经生成了一个演示。", links: [], resources: [] }
    ];
    const generatedLinks: ChatAppLink[] = [
      { link_id: "link-demo", message_id: "m1", app_id: "app-demo", label: "打开 动能定理互动演示", action: "fullscreen", created_at: "now" }
    ];
    const { host, cleanup } = render(
      <TutorChat
        messages={messages}
        generatedLinks={generatedLinks}
        activities={[]}
        isStreaming={false}
        backgroundTasks={[]}
        modelProvider="gemini"
        onModelProviderChange={() => undefined}
        onSend={async () => undefined}
        onSummarize={async () => undefined}
        onOpenLink={() => undefined}
        onAddResourceToCanvas={() => undefined}
      />
    );

    expect(host.textContent).toContain("本轮生成物");
    expect(host.textContent).toContain("打开 动能定理互动演示");
    expect(host.querySelector("[data-testid='applink-app-demo']")).toBeTruthy();
    cleanup();
  });

  it("renders structured Hermes runtime trace details", () => {
    const messages: ChatMessage[] = [
      { id: "u1", role: "user", text: "帮我生成一个演示。", links: [], resources: [] },
      { id: "m1", role: "assistant", text: "我会调用 Hermes 生成。", links: [], resources: [] }
    ];
    const trace: TraceItem[] = [
      {
        id: "t1",
        name: "hermes_runtime",
        status: "running",
        detail: "加载 LearnForge profile、Skills、Toolsets/MCP",
        raw: "hermes_runtime:running:加载 LearnForge profile、Skills、Toolsets/MCP"
      },
      {
        id: "t2",
        name: "hermes_native_trace",
        status: "completed",
        detail: "hermes_provider_fallback:xiaomi->gemini:HTTP 402",
        raw: "hermes_native_trace:completed:hermes_provider_fallback:xiaomi->gemini:HTTP 402"
      },
      {
        id: "t3",
        name: "canvas_materializer",
        status: "completed",
        detail: "已完成",
        raw: "canvas_materializer:completed:已完成"
      }
    ];

    const { host, cleanup } = render(
      <TutorChat
        messages={messages}
        generatedLinks={[]}
        activities={[{ anchorMessageId: "u1", trace, isActive: false }]}
        isStreaming={false}
        backgroundTasks={[]}
        modelProvider="gemini"
        onModelProviderChange={() => undefined}
        onSend={async () => undefined}
        onSummarize={async () => undefined}
        onOpenLink={() => undefined}
        onAddResourceToCanvas={() => undefined}
      />
    );

    expect(host.querySelector("[aria-label='AI 学习导师工作过程']")).toBeTruthy();
    expect(host.textContent).toContain("Hermes 工作");
    expect(host.textContent).toContain("2/3 步骤");
    expect(host.textContent).not.toContain("hermes_provider_fallback:xiaomi->gemini");
    const userMessage = host.querySelector(".message.user");
    const activityMessage = host.querySelector("[data-testid='agent-activity-turn']");
    const assistantMessage = host.querySelector(".message.assistant:not(.agent-activity-message)");
    expect(userMessage?.compareDocumentPosition(activityMessage!)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(activityMessage?.compareDocumentPosition(assistantMessage!)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    cleanup();
  });

  it("previews Bilibili video cards lazily in chat", () => {
    const video: LearningResource = {
      resource_id: "res-video-preview",
      type: "video",
      title: "数据结构 B站视频",
      target_topic: "数据结构",
      difficulty: "中级",
      content: { url: "https://www.bilibili.com/video/BVTEST", bvid: "BVTEST", author: "测试UP", description: "链表和树" },
      source_refs: [],
      personalized_reason: "适合当前主题",
      tags: ["#B站视频"]
    };
    const messages: ChatMessage[] = [
      { id: "m-video", role: "assistant", text: "找到这些视频。", links: [], resources: [video] }
    ];
    const { host, cleanup } = render(
      <TutorChat
        messages={messages}
        generatedLinks={[]}
        activities={[]}
        isStreaming={false}
        backgroundTasks={[]}
        modelProvider="gemini"
        onModelProviderChange={() => undefined}
        onSend={async () => undefined}
        onSummarize={async () => undefined}
        onOpenLink={() => undefined}
        onAddResourceToCanvas={() => undefined}
      />
    );

    expect(host.querySelector("[data-testid='video-resource-card-res-video-preview']")).toBeTruthy();
    expect(host.querySelector("iframe")).toBeFalsy();
    const previewButton = Array.from(host.querySelectorAll("button")).find((button) => button.textContent?.includes("预览")) as HTMLButtonElement;
    act(() => previewButton.click());
    const iframe = host.querySelector("iframe") as HTMLIFrameElement;
    expect(iframe).toBeTruthy();
    expect(iframe.src).toContain("player.bilibili.com/player.html");
    expect(iframe.src).toContain("BVTEST");
    cleanup();
  });

  it("renders dedicated Bilibili video player app", () => {
    const videoApp: CanvasApp = {
      ...app,
      app_id: "app-video-player",
      app_type: "video.player",
      title: "数据结构 B站视频播放器",
      payload: {
        topic: "数据结构",
        videos: [
          {
            resource_id: "res-video-player",
            type: "video",
            title: "数据结构 B站视频",
            target_topic: "数据结构",
            difficulty: "中级",
            content: { url: "https://www.bilibili.com/video/BVTEST", bvid: "BVTEST", author: "测试UP", play: 12000 },
            source_refs: [],
            personalized_reason: "适合当前主题",
            tags: []
          }
        ],
        selected_resource_id: "res-video-player",
        selected_bvid: "BVTEST",
        embed_url: "https://player.bilibili.com/player.html?bvid=BVTEST&poster=1&autoplay=0&danmaku=0&p=1",
        embed_options: { autoplay: false, danmaku: false, poster: true, page: 1 }
      }
    };
    const { host, cleanup } = render(<NativeAppRenderer app={videoApp} dashboard={dashboard} onEvent={() => undefined} onFocusApp={() => undefined} sessionContext={DEFAULT_SESSION_CONTEXT} />);
    const iframe = host.querySelector("[data-testid='bilibili-player-iframe']") as HTMLIFrameElement;
    expect(host.querySelector("[data-testid='video-player-app']")).toBeTruthy();
    expect(iframe.src).toContain("player.bilibili.com/player.html");
    expect(iframe.src).toContain("BVTEST");
    expect(host.textContent).toContain("数据结构 B站视频");
    cleanup();
  });

  it("keeps generated images contained and zoomable", () => {
    const imageApp: CanvasApp = {
      ...app,
      app_id: "app-image-viewer",
      app_type: "image.explanation",
      title: "排序算法中文信息图",
      payload: {
        image_url: "data:image/png;base64,test-image",
        provider_alias: "nanobanana",
        visual_brief: "排序算法中文信息图",
        overlay_labels: [{ text: "核心概念", x: 0.2, y: 0.2 }]
      }
    };
    const { host, cleanup } = render(<NativeAppRenderer app={imageApp} dashboard={dashboard} onEvent={() => undefined} onFocusApp={() => undefined} sessionContext={DEFAULT_SESSION_CONTEXT} />);
    expect(host.querySelector("[data-testid='image-viewer']")).toBeTruthy();
    expect(host.textContent).toContain("100%");
    const zoomIn = host.querySelector("button[title='放大']") as HTMLButtonElement;
    act(() => zoomIn.click());
    expect(host.textContent).toContain("120%");
    cleanup();
  });

  it("builds video resources as dedicated video.player app requests", () => {
    const video: LearningResource = {
      resource_id: "res-video-canvas",
      type: "video",
      title: "操作系统 B站课",
      target_topic: "操作系统",
      difficulty: "中级",
      content: { url: "https://www.bilibili.com/video/BVCANVAS", bvid: "BVCANVAS", author: "测试UP" },
      source_refs: [],
      personalized_reason: "适合当前主题",
      tags: []
    };
    const request = buildResourceCanvasAppRequest(video);
    const payload = request.payload as Record<string, unknown>;
    expect(request.app_type).toBe("video.player");
    expect(request.title).toContain("B站视频播放器");
    expect(payload.selected_bvid).toBe("BVCANVAS");
    expect(String(payload.embed_url)).toContain("player.bilibili.com/player.html");
    expect(payload).not.toHaveProperty("resource_kind", "video");
  });
});
