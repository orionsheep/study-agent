import { expect, test, type Page } from "@playwright/test";

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
    window.localStorage.removeItem("learnforge.shell.splitPercent");
  });
  await page.goto("/");
  await expect(page.getByTestId("spatial-canvas")).toBeVisible();
  await expect(page.getByTestId("tutor-chat")).toBeVisible();
  await page.getByTitle("重置视角").click();
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
  await page.locator(".chat-input textarea").fill("生成动能定理演示");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("run-trace")).toContainText(/app_canvas_agent|tutor_agent/);
  await expect(page.getByTestId("agent-activity")).toContainText(/写入画布|导师响应/);
  const chip = page.getByTestId("applink-app-energy").first();
  await expect(chip).toBeVisible();
  await chip.click();
  await expect(page.locator(".applink-flight.active")).toBeVisible();
  await expect(page.locator(".flight-streak")).toBeVisible();
  await expect(page.locator(".flight-particle")).toHaveCount(3);
  await expect(page.getByTestId("canvas-app-app-energy")).toHaveClass(/focused/);
  await expectAppNearCanvasCenter(page, "app-energy");
});

test("chat trace exposes the selected model gateway step", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-mimo", task_type: "tutor_turn" },
    { type: "run.step", run_id: "run-e2e-mimo", step_name: "knowledge_agent", status: "completed", detail: "已完成" },
    { type: "run.step", run_id: "run-e2e-mimo", step_name: "model_gateway", status: "running", detail: "调用 MiMo 大模型" },
    { type: "run.step", run_id: "run-e2e-mimo", step_name: "model_gateway", status: "completed", detail: "MiMo mimo-v2.5-pro 已生成回复" },
    { type: "assistant.delta", message_id: "msg-e2e-mimo", text: "MiMo 生成的导师回复。" },
    { type: "run.done", run_id: "run-e2e-mimo", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e-mimo" }
  ]);
  await page.locator(".chat-input textarea").fill("解释学习率发散");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("agent-activity")).toContainText("MiMo");
  await expect(page.getByTestId("run-trace")).toContainText("model_gateway:completed");
  await expect(page.locator(".message.assistant").last()).toContainText("MiMo 生成的导师回复。");
  await expect
    .poll(async () => {
      const text = (await page.locator(".message.assistant").last().textContent()) ?? "";
      return text.match(/MiMo 生成的导师回复/g)?.length ?? 0;
    })
    .toBe(1);
});

test("assistant output renders Markdown and show-widget rich content", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-rich", task_type: "tutor_turn" },
    { type: "run.step", run_id: "run-e2e-rich", step_name: "model_gateway", status: "completed", detail: "MiMo mimo-v2.5-pro 已生成回复" },
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
  await page.locator(".chat-input textarea").fill("输出 Markdown 和交互组件");
  await page.getByTestId("chat-send").click();
  const latest = page.locator(".message.assistant").last();
  await expect(latest.locator("h3")).toContainText("为你定制的学习路径");
  await expect(latest.locator("ol")).toBeVisible();
  await expect(latest.locator("strong").first()).toContainText("第一步");
  await expect(latest.getByTestId("custom-html-renderer")).toBeVisible();
});

test("WorkEnergy sliders update formula outputs", async ({ page }) => {
  const app = page.getByTestId("canvas-app-app-energy");
  await expect(app.getByTestId("work-energy-demo")).toBeVisible();
  await app.locator("input[type='range']").nth(2).fill("8");
  await expect(app).toContainText("55.0");
});

test("Quiz submit shows feedback and dashboard memory evidence", async ({ page }) => {
  await page.locator(".canvas-search input").fill("诊断题");
  await page.locator(".canvas-search button").click();
  const quiz = page.getByTestId("canvas-app-app-quiz");
  await expect(quiz).toHaveClass(/focused/);
  await quiz.getByTestId("quiz-submit").click();
  await expect(quiz.getByTestId("quiz-feedback")).toContainText("需要复习");
  await page.locator(".canvas-search input").fill("学习仪表盘");
  await page.locator(".canvas-search button").click();
  await expect(page.getByTestId("canvas-app-app-dashboard")).toHaveClass(/focused/);
  await expect(page.getByTestId("memory-evidence")).toContainText(/profile|misconception|app_interaction/);
});

test("LearningPath stage click focuses App and canvas controls work", async ({ page }) => {
  await page.getByTestId("path-stage-stage-opt").click();
  await expect(page.getByTestId("canvas-app-app-quiz")).toHaveClass(/focused/);
  await expectAppNearCanvasCenter(page, "app-quiz");
  const before = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.getByTitle("放大").click();
  const afterZoom = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  expect(afterZoom).not.toBe(before);
  const canvas = await page.getByTestId("spatial-canvas").boundingBox();
  expect(canvas).toBeTruthy();
  const beforeWheel = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  await page.mouse.move((canvas?.x ?? 0) + (canvas?.width ?? 0) * 0.42, (canvas?.y ?? 0) + (canvas?.height ?? 0) * 0.7);
  await page.mouse.wheel(0, -240);
  const afterWheel = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  expect(afterWheel).not.toBe(beforeWheel);
  await page.mouse.down();
  await page.mouse.move((canvas?.x ?? 0) + (canvas?.width ?? 0) * 0.5, (canvas?.y ?? 0) + (canvas?.height ?? 0) * 0.76);
  await page.mouse.up();
  const afterDrag = await page.locator(".canvas-world").evaluate((node) => getComputedStyle(node).transform);
  expect(afterDrag).not.toBe(afterWheel);
  await page.getByTitle("自动整理").click();
  await page.getByTitle("保存布局").click();
  await page.getByTestId("minimap").locator("button").click();
  await expect(page.locator(".undo-chip")).toBeVisible();
});

test("Notes App creation from chat summary works", async ({ page }) => {
  await stubChatStream(page, [
    { type: "run.started", run_id: "run-e2e-notes", task_type: "notes_summary" },
    { type: "run.step", run_id: "run-e2e-notes", step_name: "notes_skill", status: "completed", detail: "已完成" },
    { type: "assistant.delta", message_id: "msg-e2e-notes", text: "已整理到笔记。" },
    { type: "run.done", run_id: "run-e2e-notes", status: "completed" },
    { type: "assistant.done", message_id: "msg-e2e-notes" }
  ]);
  await page.getByTestId("chat-summarize").click();
  await expect(page.getByTestId("canvas-app-app-notes")).toHaveClass(/focused/);
  await expect(page.getByTestId("notes-app")).toBeVisible();
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
