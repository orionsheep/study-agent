import { chromium } from "playwright";

const BASE = "http://127.0.0.1:3000";
const S = `fi-${Date.now()}`;
const APP = { app_id: "app-fi", title: "英语工作区", app_type: "english.workspace", status: "ready", state: "window", position: { x: 20, y: 20 }, size: { width: 1280, height: 840 }, z_index: 40, group_id: "system-modules", payload: {}, source_refs: [], render_mode: "native_react", source: {}, actions: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() };

async function openAndSelect(p, word) {
  await p.getByTitle("英语工作区").first().click({ timeout: 10000 });
  await p.waitForTimeout(2500);
  const ws = p.locator(".native-app-body-workspace").first();
  // Select via search
  await ws.locator('input[placeholder*="搜索"]').first().fill(word, { timeout: 10000 });
  await p.waitForTimeout(2500);
  const row = ws.locator('button:has(span:has-text("' + word + '"))').first();
  if (await row.count()) { await row.click({ timeout: 8000 }); await p.waitForTimeout(4000); }
  return ws;
}

async function checkGraph(p, ws, label) {
  const info = await ws.evaluate((el) => {
    const cont = el.querySelector(".fission-graph-container");
    const canvas = cont?.querySelector("canvas");
    if (!canvas) return { hasCanvas: false };
    const cr = canvas.getBoundingClientRect();
    const w = parseInt(canvas.getAttribute("width"));
    const h = parseInt(canvas.getAttribute("height"));
    // Check if graph rendered nodes: sample non-black pixels in center region
    const ctx = canvas.getContext("2d");
    let coloredPixels = 0;
    try {
      const data = ctx.getImageData(w/2 - 100, h/2 - 100, 200, 200).data;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i] > 30 || data[i+1] > 30 || data[i+2] > 30) coloredPixels++;
      }
    } catch(e) { return { hasCanvas: true, sampleError: e.message }; }
    return {
      hasCanvas: true,
      canvasSize: `${w}x${h}`,
      cssSize: `${Math.round(cr.width)}x${Math.round(cr.height)}`,
      match: w === Math.round(cr.width),
      coloredPixels,  // nodes drawn = colored pixels > 0
      containerSize: (() => { const r = cont.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; })(),
    };
  }).catch(() => ({ error: "eval failed" }));
  console.log(`[${label}]`, JSON.stringify(info));

  // Probe node hover
  const box = await ws.locator(".fission-graph-container canvas").first().boundingBox().catch(() => null);
  let hoverHits = 0;
  if (box) {
    for (let gx = 0.2; gx <= 0.85; gx += 0.13) {
      for (let gy = 0.2; gy <= 0.85; gy += 0.13) {
        await p.mouse.move(box.x + box.width * gx, box.y + box.height * gy);
        await p.waitForTimeout(60);
        const cur = await p.evaluate(([x,y]) => {
          const el = document.elementFromPoint(x,y);
          let n = el; for(let i=0;i<4&&n;i++){ if(n.style&&n.style.cursor==="pointer")return"p"; n=n.parentElement;} return ".";
        }, [box.x + box.width*gx, box.y + box.height*gy]);
        if (cur === "p") hoverHits++;
      }
    }
  }
  console.log(`[${label}] hover hits:`, hoverHits);
  return { info, hoverHits };
}

async function main() {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const p = await (await b.newContext({ viewport: { width: 1680, height: 1050 } })).newPage();
  const errs = [];
  p.on("pageerror", (e) => errs.push(e.message));
  await p.addInitScript((s) => { localStorage.setItem("learnforge.auth.token", "f"); localStorage.setItem("learnforge.session.context", JSON.stringify({ studentId: s, courseId: "ai-course", conversationId: "c" })); }, S);
  await p.route("**/api/auth/me", (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ token: "f", user: { user_id: "u" }, student: { student_id: S, course_id: "ai-course", profile_status: "completed" }, onboarding: { status: "completed" } }) }));
  await p.route("**/api/canvas/apps", async (r) => { if (r.request().method() === "POST") { await r.fulfill({ contentType: "application/json", body: JSON.stringify({ payload: { app: APP } }) }); return; } await r.fallback(); });
  await p.route("**/api/canvas/apps?*", (r) => r.request().method() === "GET" ? r.fulfill({ contentType: "application/json", body: JSON.stringify({ apps: [] }) }) : r.fallback());
  await p.goto(BASE, { waitUntil: "domcontentloaded" });
  await p.waitForTimeout(1500);

  // ── Scenario 1: first word load ──────────────────────────────────────
  console.log("=== Scenario 1: load 'hello' ===");
  let ws = await openAndSelect(p, "hello");
  await checkGraph(p, ws, "hello");

  // ── Scenario 2: switch to a different word quickly ───────────────────
  console.log("\n=== Scenario 2: quick switch to 'world' ===");
  await ws.locator('input[placeholder*="搜索"]').first().fill("world", { timeout: 10000 });
  await p.waitForTimeout(1500); // shorter wait — simulate fast switching
  const worldRow = ws.locator('button:has(span:has-text("world"))').first();
  if (await worldRow.count()) { await worldRow.click({ timeout: 8000 }); }
  await p.waitForTimeout(2500);
  await checkGraph(p, ws, "world-quick");

  // ── Scenario 3: switch to immersive and back, then check dashboard ──
  console.log("\n=== Scenario 3: immersive toggle then back ===");
  // go back to hello first
  await p.locator('input[placeholder*="搜索"]').first().fill("hello");
  await p.waitForTimeout(2000);
  await ws.locator('button:has(span:has-text("hello"))').first().click({ timeout: 8000 });
  await p.waitForTimeout(3000);
  await p.locator('button:has-text("Immersive")').first().click({ timeout: 8000 });
  await p.waitForTimeout(2500);
  // exit immersive
  await ws.locator('button[title="退出浸润模式"]').first().click({ force: true }).catch(() => {});
  await p.waitForTimeout(2500);
  await checkGraph(p, ws, "after-immersive");

  // ── Scenario 4: resize window then check graph ───────────────────────
  console.log("\n=== Scenario 4: after window resize ===");
  // Simulate by dispatching resize
  await p.evaluate(() => window.dispatchEvent(new Event("resize")));
  await p.waitForTimeout(2000);
  await checkGraph(p, ws, "after-resize");

  console.log("\n=== pageerrors ===");
  errs.slice(0, 10).forEach((e) => console.log("  -", e.slice(0, 160)));
  console.log("total:", errs.length);
  await b.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
