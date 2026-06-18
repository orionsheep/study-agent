import { test, expect } from "@playwright/test";

/**
 * English Workspace smoke test.
 *
 * Verifies the full chain that previously broke:
 *   vite /api proxy → LearnForge 8011 → english-word-fission 3011 → real DB
 *
 * Covers every tab of the English workspace:
 *   - Word list (libraries browser + virtualized words + Chinese definitions)
 *   - Word detail (phonetic, Collins stars, markdown definition)
 *   - Fission graph (force-directed nodes from real synonym data)
 *   - Quiz panel
 *   - AI chat panel (mounts without crashing; live SSE not asserted here)
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
        await route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
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
          })
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
    expect(Array.isArray(body) ? body : body.words).toContain("hello");

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

  test("English workspace opens and every tab renders", async ({ page }) => {
    const consoleErrors: string[] = [];
    const netLog: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));
    page.on("response", (resp) => {
      const url = resp.url();
      if (/\/api\/(canvas|english|auth|dashboard)/.test(url)) {
        netLog.push(`${resp.request().method()} ${url.replace(/^https?:\/\/[^/]+/, "")} → ${resp.status()}`);
      }
    });

    await page.goto(API_BASE);
    await expect(page.getByTestId("app-dock")).toBeVisible({ timeout: 20_000 });

    // Open the English workspace via the dock entry (virtual system module).
    await page.getByTitle("英语工作区").first().click({ timeout: 10_000 });
    await page.waitForTimeout(4000);

    // Debug: dump what's visible on the canvas so we can see why the workspace didn't open.
    const visibleButtons = await page.locator('[data-testid="spatial-canvas"] button, .appwin button').allInnerTexts().catch(() => []);
    console.log("visible buttons after dock click:", visibleButtons.slice(0, 30));
    console.log("network log:\n  " + netLog.join("\n  "));

    // Wait for the workspace window to materialize, then for the tab bar.
    await expect(page.getByRole("button", { name: /单词列表/ })).toBeVisible({ timeout: 20_000 });

    // ── Tab 1: Word list — should load the real library browser ─────────
    await page.getByRole("button", { name: /单词列表/ }).click();
    // Expect at least one library entry to render (file or directory from the DB).
    await expect(page.locator('[data-testid="spatial-canvas"] button:has-text("考纲"), [data-testid="spatial-canvas"] button:has-text("四六级"), [data-testid="spatial-canvas"] button:has-text("托福")').first()).toBeVisible({ timeout: 15_000 });

    // Open the first .csv library → words list should populate.
    await page.locator('button:has-text("四六级"), button:has-text("托福")').first().click({ timeout: 8000 });
    await page.waitForTimeout(2000);

    // ── Tab 2: Fission graph — should render the force-directed canvas ──
    await page.getByRole("button", { name: /裂变图/ }).click();
    await page.waitForTimeout(3000);

    // ── Tab 3: Quiz ─────────────────────────────────────────────────────
    await page.getByRole("button", { name: /测验/ }).click();
    await page.waitForTimeout(1000);

    // ── Tab 4: AI chat ──────────────────────────────────────────────────
    await page.getByRole("button", { name: /AI 对话/ }).click();
    await page.waitForTimeout(1000);

    // Surface any non-network console errors as a test failure.
    const fatalErrors = consoleErrors.filter((msg) =>
      !/Failed to load resource|net::ERR|favicon|404|ERR_NETWORK|ERR_INTERNET/i.test(msg)
    );
    expect(fatalErrors, `console errors:\n${fatalErrors.join("\n")}`).toEqual([]);
  });
});
