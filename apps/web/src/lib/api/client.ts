import type { AgentStreamEvent, CanvasApp, DashboardSnapshot, ChatAppLink, LearningResource } from "@learnforge/app-protocol";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8011";
const TOKEN_KEY = "learnforge.auth.token";
const JSON_REQUEST_TIMEOUT_MS = 30_000;

export type SessionContext = {
  studentId: string;
  courseId: string;
  conversationId: string;
};

export type ModelProvider = "gemini";
export type ChatAttachmentPayload = { name: string; preview?: string };
export type ChatContextPayload = {
  active_context?: "english" | "notebooklm" | "general";
  english_word?: string;
  notebooklm?: NotebookLMContext;
};
export type NotebookLMContext = {
  notebookId?: string;
  learnforgeNotebookId?: string;
  openNotebookId?: string;
  notebookTitle?: string;
  sourceId?: string;
  sourceTitle?: string;
  sourceRefs?: Array<Record<string, unknown>>;
  citation?: string;
  kind?: string;
  mode?: "source" | "selection" | "workspace";
};

// #25: single source of truth for the model picker. UI surfaces (ChatHeader etc.)
// import this instead of hardcoding their own copy, so labels stay in sync with the
// ModelProvider union above.
export const MODEL_OPTIONS: { provider: ModelProvider; label: string; caption: string }[] = [
  { provider: "gemini", label: "Gemini 3.1 Pro", caption: "Google Gemini" },
  ];

export const DEFAULT_SESSION_CONTEXT: SessionContext = {
  studentId: "demo-student",
  courseId: "ai-course",
  conversationId: "demo-conversation"
};

export type AuthPayload = {
  token: string;
  user: { user_id: string; email?: string; display_name?: string };
  student: { student_id: string; course_id: string; profile_status: string };
  onboarding?: Record<string, unknown>;
};

export type OnboardingStatus = {
  onboarding: Record<string, unknown>;
  profile_status: string;
  profile: Record<string, unknown>;
  coverage: number;
  missing_fields: string[];
  sources: Array<Record<string, unknown>>;
  next_actions: string[];
};

export function getAuthToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setAuthToken(token: string) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function sessionHeaders(context: SessionContext): Record<string, string> {
  const token = getAuthToken();
  return {
    "X-Student-Id": context.studentId,
    "X-Course-Id": context.courseId,
    "X-Conversation-Id": context.conversationId,
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export function sessionRequestHeaders(context: SessionContext): Record<string, string> {
  return sessionHeaders(context);
}

async function jsonFetch<T>(path: string, init?: RequestInit, context = DEFAULT_SESSION_CONTEXT): Promise<T> {
  const controller = init?.signal ? null : new AbortController();
  const timeout = controller ? setTimeout(() => controller.abort(), JSON_REQUEST_TIMEOUT_MS) : null;
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...init,
      signal: init?.signal ?? controller?.signal,
      headers: {
        "Content-Type": "application/json",
        ...sessionHeaders(context),
        ...(init?.headers ?? {})
      }
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("请求超时，请检查 LearnForge API 是否正在运行。");
    }
    throw error;
  } finally {
    if (timeout) clearTimeout(timeout);
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      const detail = payload?.detail;
      const code = typeof detail?.code === "string" ? detail.code : "";
      const rawMessage = typeof detail?.message === "string" ? detail.message : "";
      const friendly: Record<string, string> = {
        INVALID_AUTH_INPUT: "请输入有效邮箱，并使用至少 6 位密码。",
        EMAIL_EXISTS: "这个邮箱已经注册过了，可以切换到登录。",
        INVALID_CREDENTIALS: "邮箱或密码不正确。",
        INVALID_SESSION: "登录状态已失效，请重新登录。",
        AUTH_REQUIRED: "请先登录后再继续。"
      };
      message = friendly[code] || rawMessage || message;
    } catch {
      // Keep the HTTP status fallback when the response body is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function fetchApps(context = DEFAULT_SESSION_CONTEXT): Promise<CanvasApp[]> {
  const data = await jsonFetch<{ apps: CanvasApp[] }>(`/api/canvas/apps?student_id=${encodeURIComponent(context.studentId)}`, undefined, context);
  return data.apps;
}

export async function fetchDashboard(context = DEFAULT_SESSION_CONTEXT): Promise<DashboardSnapshot> {
  return jsonFetch<DashboardSnapshot>(`/api/dashboard/${encodeURIComponent(context.studentId)}`, undefined, context);
}

export type OpenStaxCramBook = {
  slug: string;
  title: string;
  subject: string;
  provider: "openstax" | string;
  exam_mode: "conceptual_cram" | "practice_heavy" | string;
  details_url?: string;
  web_url?: string;
  pdf_url?: string;
  license?: string;
  tags?: string[];
};

export type CramSessionResponse = {
  session: Record<string, unknown>;
  app?: CanvasApp;
  dashboard?: DashboardSnapshot;
};

export async function fetchOpenStaxCramBooks(context = DEFAULT_SESSION_CONTEXT): Promise<OpenStaxCramBook[]> {
  const data = await jsonFetch<{ books: OpenStaxCramBook[] }>("/api/cram/openstax-books", undefined, context);
  return data.books;
}

export async function createCramSession(payload: {
  course_title: string;
  topics?: string[];
  must_know?: string[];
  key_points?: string[];
  exam_types?: string[];
  textbook?: string;
}, context = DEFAULT_SESSION_CONTEXT): Promise<CramSessionResponse> {
  return jsonFetch<CramSessionResponse>("/api/cram/sessions", {
    method: "POST",
    body: JSON.stringify(payload)
  }, context);
}

export async function advanceCramSession(sessionId: string, payload: {
  action: string;
  payload?: Record<string, unknown>;
}, context = DEFAULT_SESSION_CONTEXT): Promise<CramSessionResponse> {
  return jsonFetch<CramSessionResponse>(`/api/cram/sessions/${encodeURIComponent(sessionId)}/advance`, {
    method: "POST",
    body: JSON.stringify(payload)
  }, context);
}

export async function fetchLearningPath(pathId = "path-neural-network") {
  return jsonFetch(`/api/learning-path/${pathId}`);
}

export async function postAppEvent(appId: string, eventType: string, payload: Record<string, unknown>, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch(`/api/canvas/apps/${appId}/events`, {
    method: "POST",
    body: JSON.stringify({
      student_id: context.studentId,
      course_id: context.courseId,
      conversation_id: context.conversationId,
      event_type: eventType,
      payload
    })
  }, context);
}

export async function createCanvasApp(payload: {
  app_type: string;
  title: string;
  payload?: Record<string, unknown>;
  source_refs?: Array<Record<string, unknown>>;
}, context = DEFAULT_SESSION_CONTEXT): Promise<CanvasApp> {
  const data = await jsonFetch<{ payload?: { app?: CanvasApp }; app?: CanvasApp }>("/api/canvas/apps", {
    method: "POST",
    body: JSON.stringify({
      student_id: context.studentId,
      course_id: context.courseId,
      conversation_id: context.conversationId,
      app_type: payload.app_type,
      title: payload.title,
      payload: payload.payload ?? {},
      source_refs: payload.source_refs ?? []
    })
  }, context);
  const app = data.payload?.app ?? data.app;
  if (!app) throw new Error("canvas app create response did not include app");
  return app;
}

export async function postResourceFeedback(payload: {
  resource_id?: string;
  app_id?: string;
  preference: string;
  sentiment: string;
  rating?: number;
  comment?: string;
}, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch<{ feedback_id: string; memory: unknown; dashboard: DashboardSnapshot }>("/api/memory/resource-feedback", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...payload })
  }, context);
}

export async function fetchResources(
  params: { query?: string; tag?: string; resource_type?: string; limit?: number } = {},
  context = DEFAULT_SESSION_CONTEXT
): Promise<LearningResource[]> {
  const search = new URLSearchParams({
    student_id: context.studentId,
    course_id: context.courseId,
    limit: String(params.limit ?? 240)
  });
  if (params.query) search.set("query", params.query);
  if (params.tag) search.set("tag", params.tag);
  if (params.resource_type) search.set("resource_type", params.resource_type);
  const data = await jsonFetch<{ resources: LearningResource[] }>(`/api/resources?${search.toString()}`, undefined, context);
  return data.resources;
}

export type NotebookLMStatus = {
  status: string;
  provider?: string;
  reason?: string;
  web_url?: string;
  api_url?: string;
  embed_url?: string;
};

export type NotebookLMBootstrap = NotebookLMStatus & {
  notebook_id?: string;
  learnforge_notebook_id?: string;
  external_id?: string;
};

export type NotebookLMSyncResult = NotebookLMBootstrap & {
  synced?: Array<Record<string, unknown>>;
  blocked?: Array<Record<string, unknown>> | boolean;
};

export type NotebookLMSource = {
  id: string;
  title: string;
  summary?: string;
  chunk_count?: number;
  source_refs?: Array<Record<string, unknown>>;
  source_id?: string;
  source_role?: string;
  source_scope?: string;
  ingest_type?: string;
  upload_status?: string;
  sync_status?: string;
  open_notebook_source_id?: string;
  original_url?: string;
  mime_type?: string;
  metadata?: Record<string, unknown>;
};

export type NotebookLMNotebook = {
  id: string;
  title: string;
  purpose: "course_official" | "system_review" | "personal_review" | "temporary" | string;
  owner_scope: "course" | "system" | "user" | string;
  owner_id: string;
  course_id?: string;
  description?: string;
  tags?: string[];
  open_notebook_id?: string;
  sync_status?: string;
  assignment_status?: string;
  source_count?: number;
  rank?: number;
};

export async function fetchNotebookLMStatus(context = DEFAULT_SESSION_CONTEXT): Promise<NotebookLMStatus> {
  return jsonFetch<NotebookLMStatus>("/api/notebooklm/status", undefined, context);
}

export async function bootstrapNotebookLM(context = DEFAULT_SESSION_CONTEXT, learnforgeNotebookId?: string): Promise<NotebookLMBootstrap> {
  return jsonFetch<NotebookLMBootstrap>("/api/notebooklm/bootstrap", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, learnforge_notebook_id: learnforgeNotebookId ?? null })
  }, context);
}

export async function syncNotebookLMSources(context = DEFAULT_SESSION_CONTEXT, learnforgeNotebookId?: string): Promise<NotebookLMSyncResult> {
  return jsonFetch<NotebookLMSyncResult>("/api/notebooklm/sources/sync", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, learnforge_notebook_id: learnforgeNotebookId ?? null })
  }, context);
}

export async function fetchNotebookLMSources(context = DEFAULT_SESSION_CONTEXT): Promise<NotebookLMSource[]> {
  const data = await jsonFetch<{ sources: NotebookLMSource[] }>("/api/notebooklm/sources", undefined, context);
  return data.sources;
}

export async function fetchNotebookLMNotebooks(context = DEFAULT_SESSION_CONTEXT): Promise<NotebookLMNotebook[]> {
  const data = await jsonFetch<{ notebooks: NotebookLMNotebook[] }>("/api/notebooklm/notebooks", undefined, context);
  return data.notebooks;
}

export async function createNotebookLMNotebook(payload: { title: string; description?: string; tags?: string[] }, context = DEFAULT_SESSION_CONTEXT): Promise<NotebookLMNotebook> {
  const data = await jsonFetch<{ notebook: NotebookLMNotebook }>("/api/notebooklm/notebooks", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...payload })
  }, context);
  return data.notebook;
}

export async function fetchNotebookLMNotebookSources(notebookId: string, context = DEFAULT_SESSION_CONTEXT): Promise<{ notebook: NotebookLMNotebook; sources: NotebookLMSource[] }> {
  return jsonFetch<{ notebook: NotebookLMNotebook; sources: NotebookLMSource[] }>(`/api/notebooklm/notebooks/${encodeURIComponent(notebookId)}/sources`, undefined, context);
}

export async function syncNotebookLMNotebook(notebookId: string, context = DEFAULT_SESSION_CONTEXT): Promise<NotebookLMSyncResult> {
  return jsonFetch<NotebookLMSyncResult>(`/api/notebooklm/notebooks/${encodeURIComponent(notebookId)}/sync`, {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId })
  }, context);
}

export async function addNotebookLMTextSource(notebookId: string, payload: { title: string; content: string; sync?: boolean }, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch(`/api/notebooklm/notebooks/${encodeURIComponent(notebookId)}/sources/text`, {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...payload })
  }, context);
}

export async function addNotebookLMLinkSource(notebookId: string, payload: { url: string; title?: string; sync?: boolean }, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch(`/api/notebooklm/notebooks/${encodeURIComponent(notebookId)}/sources/link`, {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...payload })
  }, context);
}

export async function uploadNotebookLMFileSource(notebookId: string, payload: { file: File; title?: string; sync?: boolean }, context = DEFAULT_SESSION_CONTEXT) {
  const search = new URLSearchParams({
    filename: payload.file.name || "upload.bin",
    sync: String(payload.sync ?? true),
  });
  if (payload.title) search.set("title", payload.title);
  // 注意：filename/title 不能放进 HTTP 头（X-Filename 等），因为中文等非 ASCII 文件名
  // 会让浏览器 fetch 直接抛 "Failed to fetch"、请求根本发不出去。这里只走 query string
  // （URLSearchParams 会自动 percent-encode），后端 backend 用 `header or query` 读取。
  const response = await fetch(apiUrl(`/api/notebooklm/notebooks/${encodeURIComponent(notebookId)}/sources/upload?${search.toString()}`), {
    method: "POST",
    headers: {
      ...sessionHeaders(context),
      "Content-Type": payload.file.type || "application/octet-stream",
    },
    body: payload.file,
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

export async function recordNotebookLMEvent(eventType: string, payload: Record<string, unknown>, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch("/api/notebooklm/events", {
    method: "POST",
    body: JSON.stringify({
      student_id: context.studentId,
      course_id: context.courseId,
      event_type: eventType,
      payload
    })
  }, context);
}

export async function patchApp(appId: string, patch: Record<string, unknown>, context = DEFAULT_SESSION_CONTEXT): Promise<CanvasApp> {
  return jsonFetch<CanvasApp>(`/api/canvas/apps/${appId}`, {
    method: "PATCH",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...patch })
  }, context);
}

export async function openAppLink(link: ChatAppLink, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch(`/api/canvas/applink/${link.link_id}/open`, { method: "POST" }, context);
}

export async function submitQuiz(questionId: string, answer: unknown, context = DEFAULT_SESSION_CONTEXT) {
  return jsonFetch(`/api/quiz/${questionId}/submit`, {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, answer })
  }, context);
}

export async function sendChatMessage(message: string, context = DEFAULT_SESSION_CONTEXT, modelProvider: ModelProvider = "gemini", imageData?: string[], attachments?: ChatAttachmentPayload[], requestedSkill?: string, contextPayload?: ChatContextPayload): Promise<{ events: AgentStreamEvent[]; assistant_text: string }> {
  return jsonFetch("/api/chat/message", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, conversation_id: context.conversationId, model_provider: modelProvider, message, image_data: imageData ?? null, attachments: attachments ?? null, requested_skill: requestedSkill ?? null, context_payload: contextPayload ?? null })
  }, context);
}

export async function streamChatMessage(message: string, onEvent: (event: AgentStreamEvent) => void, context = DEFAULT_SESSION_CONTEXT, modelProvider: ModelProvider = "gemini", imageData?: string[], signal?: AbortSignal, attachments?: ChatAttachmentPayload[], requestedSkill?: string, contextPayload?: ChatContextPayload): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...sessionHeaders(context) },
      body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, conversation_id: context.conversationId, model_provider: modelProvider, message, image_data: imageData ?? null, attachments: attachments ?? null, requested_skill: requestedSkill ?? null, context_payload: contextPayload ?? null }),
      signal,
    });
  } catch (error) {
    // #5: AbortError means the caller intentionally cancelled (session switch / logout).
    // Surface it as a rethrown AbortError so callers can distinguish it from real errors.
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    const detail = error instanceof Error ? error.message : "network error";
    throw new Error(`无法连接 LearnForge API (${API_BASE}): ${detail}`);
  }
  if (!response.ok || !response.body) {
    throw new Error(`chat stream failed: ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const line = block.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        // #6: a single malformed SSE line must not abort the whole stream.
        try {
          onEvent(JSON.parse(line.slice(6)) as AgentStreamEvent);
        } catch (parseError) {
          console.warn("[LearnForge] 跳过无法解析的 SSE 事件行", parseError);
        }
      }
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw error;
  }
}

export async function cancelChatRun(runId: string, context = DEFAULT_SESSION_CONTEXT): Promise<{ status: string; run_id: string; active_process_terminated?: boolean }> {
  return jsonFetch(
    `/api/chat/runs/${encodeURIComponent(runId)}/cancel`,
    { method: "POST", body: JSON.stringify({}) },
    context,
  );
}

export async function fetchSystemStatus() {
  return jsonFetch("/api/system/status");
}

export async function registerAccount(payload: { email: string; password: string; display_name?: string }): Promise<AuthPayload> {
  const data = await jsonFetch<AuthPayload>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  setAuthToken(data.token);
  return data;
}

export async function loginAccount(payload: { email: string; password: string }): Promise<AuthPayload> {
  const data = await jsonFetch<AuthPayload>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  setAuthToken(data.token);
  return data;
}

export async function fetchAuthMe(): Promise<AuthPayload> {
  const token = getAuthToken();
  if (!token) throw new Error("missing auth token");
  return jsonFetch<AuthPayload>("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });
}

export async function fetchOnboardingStatus(context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus> {
  return jsonFetch<OnboardingStatus>("/api/onboarding/status", undefined, context);
}

export async function startOnboarding(context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus> {
  return jsonFetch<OnboardingStatus>("/api/onboarding/start", { method: "POST" }, context);
}

export async function postOnboardingMessage(message: string, context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus & { memories?: unknown[] }> {
  return jsonFetch<OnboardingStatus & { memories?: unknown[] }>("/api/onboarding/message", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, message })
  }, context);
}

export async function postOnboardingSource(payload: {
  source_type: string;
  title: string;
  text?: string;
  url?: string;
  school?: string;
  major?: string;
  grade?: string;
}, context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus> {
  return jsonFetch<OnboardingStatus>("/api/onboarding/sources", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, ...payload })
  }, context);
}

export async function uploadOnboardingFile(file: File, sourceType = "document", context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus> {
  const form = new FormData();
  form.set("file", file);
  form.set("source_type", sourceType);
  form.set("title", file.name);
  const response = await fetch(`${API_BASE}/api/onboarding/sources`, {
    method: "POST",
    headers: sessionHeaders(context),
    body: form
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<OnboardingStatus>;
}

export async function generateOnboardingProfile(context = DEFAULT_SESSION_CONTEXT): Promise<OnboardingStatus & { profile: Record<string, unknown> }> {
  return jsonFetch<OnboardingStatus & { profile: Record<string, unknown> }>("/api/onboarding/generate-profile", { method: "POST" }, context);
}

export type ChatMessageRecord = {
  id: string;
  student_id: string;
  course_id: string;
  conversation_id: string;
  role: string;
  text: string;
  metadata: Record<string, unknown>;
  links?: ChatAppLink[];
  resources?: LearningResource[];
  created_at: string;
};

export async function fetchChatMessages(context = DEFAULT_SESSION_CONTEXT): Promise<ChatMessageRecord[]> {
  const params = new URLSearchParams({ student_id: context.studentId, course_id: context.courseId, conversation_id: context.conversationId });
  const result = await jsonFetch<{ messages: ChatMessageRecord[] }>(`/api/chat/messages?${params.toString()}`, undefined, context);
  return result.messages ?? [];
}

export async function logoutAccount() {
  try {
    await jsonFetch("/api/auth/logout", { method: "POST" });
  } catch {
    // logout is best-effort
  }
  setAuthToken("");
}
