import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import type { CanvasApp, CanvasViewport, ChatAppLink, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";
import { NativeAppRenderer } from "../src/features/learning-apps/NativeAppRenderer";
import { SpatialCanvas } from "../src/features/app-canvas/SpatialCanvas";
import { AppLinkChip } from "../src/features/applink-flight/AppLinkChip";
import { RichMessageContent } from "../src/features/tutor-chat/RichMessageContent";
import { TutorChat } from "../src/features/tutor-chat/TutorChat";
import { buildResourceCanvasAppRequest } from "../src/app/LearnForgeApp";
import { DEFAULT_SESSION_CONTEXT } from "../src/lib/api/client";
import type { ChatMessage, TraceItem } from "../src/lib/events/agentEvents";

function render(node: React.ReactNode) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return { host, cleanup: () => act(() => root.unmount()) };
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
      payload: { html },
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
    expect(iframe?.srcdoc).not.toContain("lf-generated-document");
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
    expect(host.textContent).toContain("已完成");
    expect(host.textContent).toContain("Hermes 反馈");
    expect(host.textContent).toContain("写入学习画布");
    expect(host.textContent).toContain("模型通道已自动处理");
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
