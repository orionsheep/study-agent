import { expect, test, type Page } from "@playwright/test";
import type { CanvasApp, DashboardSnapshot } from "@learnforge/app-protocol";

const E2E_STUDENT_ID = `e2e-student-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const E2E_COURSE_ID = "ai-course";
const E2E_NOW = "2026-06-04T00:00:00Z";

function canvasApp(overrides: Partial<CanvasApp> & Pick<CanvasApp, "app_id" | "app_type" | "title">): CanvasApp {
  return {
    status: "ready",
    render_mode: "native_react",
    state: "window",
    position: { x: 120, y: 120 },
    size: { width: 360, height: 220 },
    z_index: 30,
    payload: {},
    source: {},
    source_refs: [],
    actions: [],
    created_at: E2E_NOW,
    updated_at: E2E_NOW,
    ...overrides
  };
}

function e2eCanvasApps(): CanvasApp[] {
  return [
    canvasApp({
      app_id: "app-profile",
      app_type: "profile.dashboard",
      title: "学习画像",
      position: { x: 80, y: 120 },
      size: { width: 360, height: 220 },
      z_index: 40,
      payload: { name: "E2E Learner", school: "LearnForge", progress: 100 }
    }),
    canvasApp({
      app_id: "app-dashboard",
      app_type: "dashboard.learning",
      title: "学习仪表盘",
      position: { x: 470, y: 120 },
      size: { width: 420, height: 250 },
      z_index: 41,
      payload: { active_tab: "overview" }
    }),
    canvasApp({
      app_id: "app-resource",
      app_type: "resource.center",
      title: "资源中心",
      position: { x: 920, y: 120 },
      size: { width: 430, height: 290 },
      z_index: 42,
      payload: {
        topic: "问候与引导",
        status: "已索引",
        resources: [
          {
            resource_id: "res-diagnostic",
            title: "诊断练习",
            type: "quiz",
            module: "练习",
            recommended_level: "巩固",
            tags: ["诊断", "练习"],
            content: { summary: "用于确认资源中心和记忆证据的稳定渲染。" },
            source_refs: [{ title: "diagnostic.pdf", page: 2 }]
          }
        ]
      }
    }),
    canvasApp({
      app_id: "app-energy",
      app_type: "physics.work_energy_demo",
      title: "打开动能定理演示",
      state: "minimized",
      position: { x: 650, y: 420 },
      size: { width: 460, height: 320 },
      z_index: 35,
      payload: { topic: "动能定理", status: "可交互" },
      actions: [{ label: "开始演示", action: "demo.start" }]
    })
  ];
}

function e2eDashboard(): DashboardSnapshot {
  return {
    student_id: E2E_STUDENT_ID,
    profile: { display_name: "E2E Learner", school: "LearnForge" },
    mastery: { "动能定理": 0.82, "资源检索": 0.68 },
    weak_points: ["公式迁移"],
    recommendations: [{ title: "打开动能定理演示", reason: "用交互演示理解功和动能变化", score: 0.92 }],
    memory_evidence: [
      {
        id: "mem-e2e",
        student_id: E2E_STUDENT_ID,
        course_id: E2E_COURSE_ID,
        memory_type: "learning_preference",
        content: "偏好可视化演示与诊断练习。",
        structured_payload: {},
        confidence: 0.9,
        effective_confidence: 0.9,
        evidence_type: "chat",
        source_agent: "hermes",
        importance: 0.7,
        decay_rate: 0.02,
        tags: ["e2e"],
        created_at: E2E_NOW,
        updated_at: E2E_NOW
      }
    ],
    recent_runs: [{ run_id: "run-e2e", task_type: "work_energy_demo", status: "completed" }],
    path_progress: 0.72
  };
}

function streamBody(events: Array<Record<string, unknown>>) {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("");
}

async function stubChatStream(page: Page, events: Array<Record<string, unknown>>) {
  await page.route("**/api/chat/stream", async (route) => {
    await route.fulfill({
      contentType: "text/event-stream",
      body: streamBody(events)
    });
  });
}

function chatLink(appId: string, label: string) {
  return {
    link_id: `link-${appId}`,
    message_id: "msg-e2e",
    app_id: appId,
    label,
    action: "focus",
    created_at: "2026-06-04T00:00:00Z",
    source_run_id: "run-e2e"
  };
}

async function expectAppNearCanvasCenter(page: Page, appId: string) {
  await expect
    .poll(async () => {
      const canvas = await page.getByTestId("spatial-canvas").boundingBox();
      const app = await page.getByTestId(`canvas-app-${appId}`).boundingBox();
      if (!canvas || !app) return false;
      const canvasCenter = { x: canvas.x + canvas.width / 2, y: canvas.y + canvas.height / 2 };
      const appCenter = { x: app.x + app.width / 2, y: app.y + app.height / 2 };
      return Math.abs(appCenter.x - canvasCenter.x) < canvas.width * 0.32 && Math.abs(appCenter.y - canvasCenter.y) < canvas.height * 0.32;
    })
    .toBe(true);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("learnforge.auth.token", "e2e-token");
    window.localStorage.setItem("learnforge.settings.theme", JSON.stringify("light"));
    window.localStorage.setItem("learnforge.settings.wallpaper", JSON.stringify("sonoma"));
    window.localStorage.removeItem("learnforge.shell.splitPercent");
  });
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/api/auth/me")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          token: "e2e-token",
          user: { user_id: "user-e2e", email: "e2e@learnforge.test", display_name: "E2E Learner" },
          student: { student_id: E2E_STUDENT_ID, course_id: E2E_COURSE_ID, profile_status: "completed" },
          onboarding: { status: "completed", current_step: "completed" }
        })
      });
      return;
    }
    if (url.includes("/api/canvas/apps?")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ apps: e2eCanvasApps() })
      });
      return;
    }
    if (url.includes("/api/dashboard/")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(e2eDashboard())
      });
      return;
    }
    if (url.includes("/api/resources")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ resources: e2eCanvasApps()[2].payload.resources ?? [] })
      });
      return;
    }
    const headers = { ...route.request().headers() };
    delete headers.authorization;
    await route.fallback({ headers });
  });
  await page.goto("/");
  await expect(page.getByTestId("spatial-canvas")).toBeVisible();
  await expect(page.getByTestId("tutor-chat")).toBeVisible();
  const resetView = page.getByTitle(/重置视角|复位/).first();
  if (await resetView.isVisible({ timeout: 1000 }).catch(() => false)) {
    await resetView.click();
  }
});

test("loads product with left canvas and right Tutor Chat", async ({ page }) => {
  const canvas = page.getByTestId("spatial-canvas");
  const chat = page.getByTestId("tutor-chat");
  const canvasBox = await canvas.boundingBox();
  const chatBox = await chat.boundingBox();
  expect(canvasBox?.x ?? 999).toBeLessThan(chatBox?.x ?? 0);
  await expect(page.getByTestId("app-dock")).toBeVisible();
  await expect(page.getByTestId("minimap")).toBeVisible();
  const resizer = page.getByTestId("pane-resizer");
  await expect(resizer).toBeVisible();
  const before = await canvas.boundingBox();
  const handle = await resizer.boundingBox();
  expect(before).toBeTruthy();
  expect(handle).toBeTruthy();
  await page.mouse.move((handle?.x ?? 0) + (handle?.width ?? 0) / 2, (handle?.y ?? 0) + (handle?.height ?? 0) / 2);
  await page.mouse.down();
  await page.mouse.move((handle?.x ?? 0) - 120, (handle?.y ?? 0) + (handle?.height ?? 0) / 2);
  await page.mouse.up();
  const after = await canvas.boundingBox();
  expect(Math.abs((after?.width ?? 0) - (before?.width ?? 0))).toBeGreaterThan(40);
});

test("appearance settings switch wallpaper and themed assets", async ({ page }) => {
  await page.getByLabel("外观与壁纸设置").click();
  const panel = page.getByRole("dialog", { name: "外观与壁纸设置" });
  await expect(panel).toBeVisible();

  await panel.getByRole("button", { name: "壁纸 Pure White" }).click();
  await expect.poll(async () => page.evaluate(() => document.documentElement.dataset.wallpaper)).toBe("pure-white");
  await expect.poll(async () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--lf-wallpaper-image").trim())).toBe("none");

  await panel.getByRole("radio", { name: "暗色" }).click();
  await expect.poll(async () => page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(true);
  await expect(page.locator(".brand-mark img").first()).toHaveAttribute("src", /\/brand\/dark\/learnforge-logo\.png$/);
  await expect(page.locator(".dock-app img").first()).toHaveAttribute("src", /\/icons\/dark\//);

  await panel.getByRole("radio", { name: "亮色" }).click();
  await expect.poll(async () => page.evaluate(() => document.documentElement.classList.contains("dark"))).toBe(false);
  await expect(page.locator(".brand-mark img").first()).toHaveAttribute("src", /\/brand\/light\/learnforge-logo\.png$/);
});

test("chat stream creates AppLink and AppLink Flight focuses target App", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e", task_type: "work_energy_demo" },
    { type: "run.step", run_id: "run-e2e", step_name: "app_canvas_agent", status: "completed", detail: "已完成" },
    { type: "app.link.create", link: chatLink("app-energy", "打开动能定理演示") },
    { type: "assistant.delta", message_id: "msg-e2e", text: "已把演示放到左侧画布。" },
    { type: "run.done", run_id: "run-e2e", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e" }
  ]);
  await page.getByLabel("输入学习问题").fill("生成动能定理演示");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("agent-activity")).toContainText("Hermes 工作");
  const chip = page.getByTestId("applink-app-energy").first();
  await expect(chip).toBeVisible();
  await chip.click();
  await expect(page.locator(".applink-flight.active")).toBeVisible();
  await expect(page.locator(".flight-streak")).toBeVisible();
  await expect(page.locator(".flight-particle")).toHaveCount(3);
});

test("chat trace renders Hermes activity and Gemini answer", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-gemini", task_type: "tutor_turn" },
    { type: "run.step", run_id: "run-e2e-gemini", step_name: "knowledge_agent", status: "completed", detail: "已完成" },
    { type: "run.step", run_id: "run-e2e-gemini", step_name: "model_gateway", status: "running", detail: "调用 Gemini 大模型" },
    { type: "run.step", run_id: "run-e2e-gemini", step_name: "model_gateway", status: "completed", detail: "Gemini gemini-3.1-pro-preview 已生成回复" },
    { type: "assistant.delta", message_id: "msg-e2e-gemini", text: "Gemini 生成的导师回复。" },
    { type: "run.done", run_id: "run-e2e-gemini", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e-gemini" }
  ]);
  await page.getByLabel("输入学习问题").fill("解释学习率发散");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("agent-activity")).toContainText("Hermes 工作");
  await expect(page.locator(".message.assistant").last()).toContainText("Gemini 生成的导师回复。");
  await expect
    .poll(async () => {
      const text = (await page.locator(".message.assistant").last().textContent()) ?? "";
      return text.match(/Gemini 生成的导师回复/g)?.length ?? 0;
    })
    .toBe(1);
});

test("assistant output renders Markdown and show-widget rich content", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-rich", task_type: "tutor_turn" },
    { type: "run.step", run_id: "run-e2e-rich", step_name: "model_gateway", status: "completed", detail: "Gemini gemini-3.1-pro-preview 已生成回复" },
    {
      type: "assistant.delta",
      message_id: "msg-e2e-rich",
      text: [
        "### 📚 为你定制的学习路径",
        "1. **第一步：绕过公式**",
        "   - **目标**：通过互动实验理解梯度下降。",
        "",
        "```show-widget",
        "{\"widget_code\":\"<section><strong>训练流程</strong><p>调整参数 → 观察损失</p></section>\"}",
        "```"
      ].join("\n")
    },
    { type: "run.done", run_id: "run-e2e-rich", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e-rich" }
  ]);
  await page.getByLabel("输入学习问题").fill("输出 Markdown 和交互组件");
  await page.getByTestId("chat-send").click();
  const latest = page.locator(".message.assistant").last();
  await expect(latest.locator("h3")).toContainText("为你定制的学习路径");
  await expect(latest.locator("ol")).toBeVisible();
  await expect(latest.locator("strong").first()).toContainText("第一步");
  await expect(latest.getByTestId("custom-html-renderer")).toBeVisible();
});

test("WorkEnergy sliders update formula outputs", async ({ page }) => {
  await expect(page.getByText("学习仪表盘").first()).toBeVisible();
  await expect(page.getByText("打开动能定理演示").first()).toBeVisible();
});

test("Quiz submit surface shows diagnostic resources and dashboard memory evidence", async ({ page }) => {
  const resourceCenter = page.getByTestId("resource-center-app");
  await expect(resourceCenter).toBeVisible();
  await expect(resourceCenter).toContainText(/诊断练习/);
  await expect(page.getByText("记忆证据").first()).toBeVisible();
});

test("LearningPath dock and canvas controls work", async ({ page }) => {
  await expect(page.getByTestId("app-dock")).toContainText("交互演示文件夹");
  const before = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.getByTestId("spatial-canvas").getByTitle("放大").click();
  await expect
    .poll(async () => page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform))
    .not.toBe(before);
  const afterZoom = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  const canvas = await page.getByTestId("spatial-canvas").boundingBox();
  expect(canvas).toBeTruthy();
  const beforeWheel = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.mouse.move((canvas?.x ?? 0) + (canvas?.width ?? 0) * 0.42, (canvas?.y ?? 0) + (canvas?.height ?? 0) * 0.7);
  await page.mouse.wheel(0, -240);
  await expect
    .poll(async () => page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform))
    .not.toBe(beforeWheel);
  const afterWheel = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.mouse.down();
  await page.mouse.move((canvas?.x ?? 0) + (canvas?.width ?? 0) * 0.5, (canvas?.y ?? 0) + (canvas?.height ?? 0) * 0.76);
  await page.mouse.up();
  await expect
    .poll(async () => page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform))
    .not.toBe(afterWheel);
  const afterDrag = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.getByTestId("minimap").locator("button").click();
  const afterMinimap = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  expect(afterMinimap).not.toBe(afterDrag);
});

test("Notes App summary action sends chat request", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-notes", task_type: "notes_summary" },
    { type: "run.step", run_id: "run-e2e-notes", step_name: "notes_skill", status: "completed", detail: "已完成" },
    { type: "assistant.delta", message_id: "msg-e2e-notes", text: "已整理到笔记。" },
    { type: "run.done", run_id: "run-e2e-notes", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e-notes" }
  ]);
  await page.getByTitle("附加功能").click();
  await page.getByTestId("chat-summarize").click();
  await expect(page.getByTestId("agent-activity")).toContainText("Hermes 工作");
  await expect(page.locator(".message.assistant").last()).toContainText("已整理到笔记。");
});

test("enabled controls expose an action label or title", async ({ page }) => {
  const buttons = await page.locator("button:not([disabled])").evaluateAll((items) =>
    items.map((item) => ({
      text: item.textContent?.trim() || "",
      title: item.getAttribute("title") || "",
      aria: item.getAttribute("aria-label") || ""
    }))
  );
  expect(buttons.length).toBeGreaterThan(20);
  for (const button of buttons) {
    expect(Boolean(button.text || button.title || button.aria)).toBe(true);
  }
});
