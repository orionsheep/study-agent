import { test, expect } from "@playwright/test";

/**
 * English Workspace smoke test.
 *
 * Verifies the full chain that previously broke:
 *   vite /api proxy → LearnForge 8011 → english-word-fission 3011 → real DB
 *
 * Covers the current English workspace workbench:
 *   - Word library/search (virtualized words + Chinese definitions)
 *   - Word detail and fission graph panes
 *   - Stats, quiz, and immersive mode switches
 *
 * Auth is stubbed the same way as product-flow.spec.ts (a fake token + a /api/auth/me
 * mock) so we can reach the shell. Critically, the English API endpoints are NOT mocked —
 * they flow through the real vite proxy → 8011 → 3011 → DB chain under test.
 */

const API_BASE = "http://127.0.0.1:3000";
const E2E_STUDENT_ID = `e2e-en-${Date.now()}`;

test.beforeEach(async ({ page }) => {
  await page.addInitScript((studentId) => {
    window.localStorage.setItem("learnforge.auth.token", "e2e-token");
    window.localStorage.setItem("learnforge.session.context", JSON.stringify({
      studentId,
      courseId: "ai-course",
      conversationId: `conv-${studentId}`,
    }));
  }, E2E_STUDENT_ID);
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        token: "e2e-token",
        user: { user_id: "user-e2e", email: "e2e@learnforge.test", display_name: "E2E Learner" },
        student: { student_id: E2E_STUDENT_ID, course_id: "ai-course", profile_status: "completed" },
        onboarding: { status: "completed", current_step: "completed" }
      })
    });
  });
  // The English workspace is created on-demand by POSTing to /api/canvas/apps. With a
  // stub auth token the real backend rejects it, so fulfil the creation locally with a
  // ready english.workspace app. All subsequent /api/english/* reads still hit the real chain.
  await page.route("**/api/canvas/apps", async (route) => {
    if (route.request().method() === "POST") {
      const reqBody = route.request().postDataJSON();
      const appType = String(reqBody?.app_type ?? "");
      if (appType === "english.workspace" || appType === "humanities.notebook") {
        const app = {
          app_id: `app-e2e-${appType}`,
          title: String(reqBody?.title ?? "英语工作区"),
          app_type: appType,
          status: "ready",
          state: "window",
          position: { x: 240, y: 120 },
          size: { width: 1100, height: 720 },
          z_index: 20,
          group_id: "system-modules",
          payload: reqBody?.payload ?? {},
          source_refs: [],
          render_mode: "native_react",
          source: {},
          actions: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({ app })
        });
        return;
      }
    }
    await route.fallback();
  });
});

test.describe("English Workspace — end to end", () => {
  test("proxy delivers real word data from EFW backend", async ({ request }) => {
    const words = await request.get(`${API_BASE}/api/english/words?search=hello`);
    expect(words.ok()).toBeTruthy();
    const body = await words.json();
    const wordItems = Array.isArray(body) ? body : body.words;
    const wordTexts = wordItems.map((item: unknown) => typeof item === "string" ? item : String((item as { word?: unknown })?.word ?? ""));
    expect(wordTexts).toContain("hello");

    const detail = await request.get(`${API_BASE}/api/english/words/hello`);
    expect(detail.ok()).toBeTruthy();
    const detailBody = await detail.json();
    expect(String(detailBody.content ?? detailBody.definition ?? "")).toContain("hello");

    const libs = await request.get(`${API_BASE}/api/english/libraries`);
    expect(libs.ok()).toBeTruthy();
    const libsBody = await libs.json();
    const libArray = Array.isArray(libsBody) ? libsBody : libsBody.libraries;
    expect(libArray.length).toBeGreaterThan(0);

    const fission = await request.get(`${API_BASE}/api/english/fission?word=hello`);
    expect(fission.ok()).toBeTruthy();
    const fissionBody = await fission.json();
    expect(Array.isArray(fissionBody.nodes) ? fissionBody.nodes.length : 0).toBeGreaterThan(0);
  });

  test("English workspace opens and workbench modes render", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));

    await page.goto(API_BASE);
    await expect(page.getByTestId("app-dock")).toBeVisible({ timeout: 20_000 });

    // Open the English workspace via the dock entry (virtual system module).
    await page.getByTitle("英语工作区").first().click({ timeout: 10_000 });

    // Wait for the current three-column workspace to materialize. This used to be
    // a tabbed UI; the restored EFW workspace now shows library, detail, and graph
    // panes simultaneously.
    const englishWindow = page.getByTestId("canvas-app-app-e2e-english.workspace");
    await expect(englishWindow.getByRole("textbox", { name: "搜索单词..." })).toBeVisible({ timeout: 20_000 });
    await expect(englishWindow.locator('button:has-text("考纲"), button:has-text("四六级"), button:has-text("托福")').first()).toBeVisible({ timeout: 15_000 });
    await expect(englishWindow.getByText("选择一个单词查看详情")).toBeVisible();
    await expect(englishWindow.getByText("选择一个单词查看裂变图")).toBeVisible();

    // Search uses the real /api/english/words?query=... chain, then selecting a
    // result hydrates WordDetail and FissionGraph.
    await englishWindow.getByRole("textbox", { name: "搜索单词..." }).fill("hello");
    const helloWord = englishWindow.getByRole("button", { name: /^hello\b.*喂/i }).last();
    await expect(helloWord).toBeAttached({ timeout: 15_000 });
    await helloWord.evaluate((node) => (node as HTMLButtonElement).click());
    await expect(englishWindow.getByText("右侧讨论：")).toBeVisible({ timeout: 10_000 });

    // Footer actions switch the same workspace into stats, quiz, and immersive
    // modes without leaving the canvas window.
    await page.getByTitle("英语学习统计").click();
    await expect(page.getByText("返回工作区")).toBeVisible({ timeout: 10_000 });
    await page.getByText("返回工作区").click();

    await page.getByTitle("单词测验").click();
    await expect(page.getByText(/测验 · hello|单词测验/)).toBeVisible({ timeout: 10_000 });
    await page.getByText("返回工作区").click();

    await page.getByTitle("进入浸润模式").first().click();
    await expect(page.getByTitle("退出浸润模式")).toBeVisible({ timeout: 10_000 });

    // Surface any non-network console errors as a test failure.
    const fatalErrors = consoleErrors.filter((msg) =>
      !/Failed to load resource|net::ERR|favicon|404|ERR_NETWORK|ERR_INTERNET/i.test(msg)
    );
    expect(fatalErrors, `console errors:\n${fatalErrors.join("\n")}`).toEqual([]);
  });
});
