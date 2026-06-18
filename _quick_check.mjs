import { chromium } from "playwright";
const BASE = "http://127.0.0.1:3000";
const S = `q-${Date.now()}`;
const APP = { app_id: "a", title: "英语工作区", app_type: "english.workspace", status: "ready", state: "window", position: { x: 20, y: 20 }, size: { width: 1280, height: 840 }, z_index: 40, group_id: "system-modules", payload: {}, source_refs: [], render_mode: "native_react", source: {}, actions: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
const b = await chromium.launch({ channel: "chrome", headless: true });
const p = await (await b.newContext({ viewport: { width: 1680, height: 1050 } })).newPage();
await p.addInitScript((s) => { localStorage.setItem("learnforge.auth.token", "q"); localStorage.setItem("learnforge.session.context", JSON.stringify({ studentId: s, courseId: "ai-course", conversationId: "c" })); }, S);
await p.route("**/api/auth/me", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ token: "q", user: { user_id: "u" }, student: { student_id: S, course_id: "ai-course", profile_status: "completed" }, onboarding: { status: "completed" } }) }));
await p.route("**/api/canvas/apps", async (r) => { if (r.request().method() === "POST") { await r.fulfill({ contentType: "application/json", body: JSON.stringify({ payload: { app: APP } }) }); return; } await r.fallback(); });
await p.route("**/api/canvas/apps?*", (r) => r.request().method() === "GET" ? r.fulfill({ contentType: "application/json", body: JSON.stringify({ apps: [] }) }) : r.fallback());
await p.goto(BASE, { waitUntil: "domcontentloaded" });
await p.waitForTimeout(1500);
await p.getByTitle("英语工作区").first().click();
await p.waitForTimeout(2500);
const ws = p.locator(".native-app-body-workspace").first();
await ws.locator('input[placeholder*="搜索"]').first().fill("hello", { timeout: 10000 });
await p.waitForTimeout(2000);
await ws.locator('button:has(span:has-text("hello"))').first().click({ timeout: 8000 });
await p.waitForTimeout(3000);

// Check WordDetail rendered content
const detail = await ws.evaluate(() => {
  const h1 = document.querySelector(".native-app-body-workspace h1");
  const md = document.querySelector(".english-markdown");
  const phonetic = document.querySelector(".native-app-body-workspace span");
  return {
    h1Text: h1?.textContent,
    h1Size: h1 ? (() => { const r = h1.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; })() : null,
    markdownPresent: !!md,
    markdownText: md?.textContent?.slice(0, 120),
    markdownSize: md ? (() => { const r = md.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; })() : null,
  };
});
console.log("WordDetail:", JSON.stringify(detail, null, 2));
await p.screenshot({ path: "/tmp/lf_q_detail.png" });
await b.close();
