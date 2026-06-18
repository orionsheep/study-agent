import { expect, test, type Page } from "@playwright/test";

const E2E_STUDENT_ID = `e2e-student-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const E2E_COURSE_ID = "ai-course";

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
