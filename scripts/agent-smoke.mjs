#!/usr/bin/env node

const API_BASE = process.env.LEARNFORGE_API_BASE || 'http://127.0.0.1:8001';
const studentId = process.env.LEARNFORGE_STUDENT_ID || 'demo-student';
const courseId = process.env.LEARNFORGE_COURSE_ID || 'ai-course';
const provider = process.env.LEARNFORGE_MODEL_PROVIDER || 'gemini';
const timeoutMs = Number(process.env.LEARNFORGE_SMOKE_TIMEOUT_MS || 260000);

function assert(condition, message, details = {}) {
  if (!condition) {
    const error = new Error(message);
    error.details = details;
    throw error;
  }
}

function withTimeout(promise, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs)),
  ]);
}

async function request(path, init = {}, conversationId) {
  const response = await withTimeout(fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Student-Id': studentId,
      'X-Course-Id': courseId,
      'X-Conversation-Id': conversationId,
      ...(init.headers || {}),
    },
  }), path);
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function postChat(conversationId, message) {
  return request('/api/chat/message', {
    method: 'POST',
    body: JSON.stringify({
      student_id: studentId,
      course_id: courseId,
      conversation_id: conversationId,
      model_provider: provider,
      message,
    }),
  }, conversationId);
}

async function listApps(conversationId) {
  const data = await request('/api/canvas/apps', {}, conversationId);
  return Array.isArray(data) ? data : data.apps || [];
}

function eventsOf(data, type) {
  return (data.events || []).filter((event) => event && event.type === type);
}

function summarizeSteps(data) {
  return eventsOf(data, 'run.step').map((event) => ({
    step: event.step_name,
    status: event.status,
    detail: event.detail,
  }));
}

async function smokeFreshCanvas() {
  const conversationId = `smoke-fresh-${Date.now()}`;
  const apps = await listApps(conversationId);
  const generated = apps.filter((app) => app && !String(app.app_id || '').startsWith('app-'));
  assert(generated.length === 0, 'fresh conversation should not include generated apps', { generated });
  assert(apps.some((app) => app.title === '学习笔记模板'), 'fresh canvas should include neutral notes template');
  return { conversationId, appCount: apps.length };
}

async function smokeImage() {
  const conversationId = `smoke-image-${Date.now()}`;
  const data = await postChat(conversationId, '请生成一张排序算法教学图片，展示冒泡排序、快速排序、归并排序的核心区别。');
  const imageApps = eventsOf(data, 'app.create').map((event) => event.app).filter((app) => app?.app_type === 'image.explanation');
  const links = eventsOf(data, 'app.link.create').map((event) => event.link);
  assert(imageApps.length > 0, 'image request should create image.explanation app', { steps: summarizeSteps(data) });
  assert(String(imageApps[0].payload?.image_url || '').startsWith('data:image/'), 'image app should include Gemini data URL', imageApps[0]);
  assert(links.some((link) => link?.action === 'fullscreen'), 'image request should create fullscreen AppLink', { links });
  return { conversationId, title: imageApps[0].title, linkCount: links.length };
}

async function smokeInteractiveDemo() {
  const conversationId = `smoke-demo-${Date.now()}`;
  const data = await postChat(conversationId, '请演示一下物理里面的动能定理，生成一个可以交互的演示应用。');
  const demoApps = eventsOf(data, 'app.create').map((event) => event.app).filter((app) => app?.app_type === 'physics.work_energy_demo');
  const links = eventsOf(data, 'app.link.create').map((event) => event.link);
  const hermesFailed = eventsOf(data, 'run.step').some((event) => event.step_name === 'hermes_runtime' && event.status === 'failed');
  assert(demoApps.length > 0, 'interactive request should create physics.work_energy_demo app', { steps: summarizeSteps(data) });
  assert(links.some((link) => link?.action === 'fullscreen'), 'interactive request should create fullscreen AppLink', { links });
  assert(!hermesFailed, 'Hermes runtime should not fail; provider fallback should remain a native trace', { steps: summarizeSteps(data) });
  return { conversationId, title: demoApps[0].title, linkCount: links.length };
}

async function smokeNotesContext() {
  const conversationId = `smoke-notes-${Date.now()}`;
  await postChat(conversationId, '请详细讲解一下排序算法的核心思想，重点比较冒泡排序、快速排序和归并排序。');
  await postChat(conversationId, '请把刚才内容整理成学习笔记');
  const apps = await listApps(conversationId);
  const notes = apps.filter((app) => app?.app_type === 'notes.session' && !String(app.app_id || '').startsWith('app-'));
  assert(notes.length === 1, 'notes summary should create one generated notes.session app', { notes });
  assert(notes[0].title === '排序算法学习笔记', 'notes title should stay bound to recent user topic', notes[0]);
  assert(notes[0].payload?.topic === '排序算法', 'notes topic should stay bound to recent user topic', notes[0]);
  assert(!JSON.stringify(notes[0]).includes('梯度'), 'notes should not include stale gradient context', notes[0]);
  return { conversationId, title: notes[0].title };
}

async function main() {
  const selected = new Set(process.argv.slice(2));
  const runAll = selected.size === 0 || selected.has('--all');
  const checks = [
    ['fresh-canvas', smokeFreshCanvas],
    ['image', smokeImage],
    ['interactive-demo', smokeInteractiveDemo],
    ['notes-context', smokeNotesContext],
  ];
  const results = [];
  for (const [name, fn] of checks) {
    if (!runAll && !selected.has(name)) continue;
    process.stdout.write(`learnforge smoke ${name} ... `);
    const result = await fn();
    results.push({ name, ...result });
    process.stdout.write('ok\n');
  }
  console.log(JSON.stringify({ apiBase: API_BASE, provider, results }, null, 2));
}

main()
  .then(() => {
    process.exit(0);
  })
  .catch((error) => {
    console.error('\nlearnforge smoke failed:', error.message);
    if (error.details) console.error(JSON.stringify(error.details, null, 2));
    process.exit(1);
  });
