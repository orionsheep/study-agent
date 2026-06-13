import type { AgentStreamEvent, CanvasApp, DashboardSnapshot, ChatAppLink, LearningResource } from "@learnforge/app-protocol";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "learnforge.auth.token";

export type SessionContext = {
  studentId: string;
  courseId: string;
  conversationId: string;
};

export type ModelProvider = "mimo" | "gemini";

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

async function jsonFetch<T>(path: string, init?: RequestInit, context = DEFAULT_SESSION_CONTEXT): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...sessionHeaders(context),
      ...(init?.headers ?? {})
    }
  });
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

export async function sendChatMessage(message: string, context = DEFAULT_SESSION_CONTEXT, modelProvider: ModelProvider = "gemini", imageData?: string[]): Promise<{ events: AgentStreamEvent[]; assistant_text: string }> {
  return jsonFetch("/api/chat/message", {
    method: "POST",
    body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, conversation_id: context.conversationId, model_provider: modelProvider, message, image_data: imageData ?? null })
  }, context);
}

export async function streamChatMessage(message: string, onEvent: (event: AgentStreamEvent) => void, context = DEFAULT_SESSION_CONTEXT, modelProvider: ModelProvider = "gemini", imageData?: string[]): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...sessionHeaders(context) },
      body: JSON.stringify({ student_id: context.studentId, course_id: context.courseId, conversation_id: context.conversationId, model_provider: modelProvider, message, image_data: imageData ?? null })
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "network error";
    throw new Error(`无法连接 LearnForge API (${API_BASE}): ${detail}`);
  }
  if (!response.ok || !response.body) {
    throw new Error(`chat stream failed: ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const line = block.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(6)) as AgentStreamEvent);
    }
  }
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
