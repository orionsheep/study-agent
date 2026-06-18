import type { AgentStreamEvent, CanvasApp, ChatAppLink, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";

export type ChatAttachment = {
  name: string;
  preview?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  links: ChatAppLink[];
  resources: LearningResource[];
  attachments?: ChatAttachment[];
  skillLabel?: { label: string; color: string; bgColor: string; borderColor: string };
};

export type TraceItem = {
  id: string;
  name: string;
  status: string;
  detail: string;
  label?: string;
  raw: string;
};

export type BackgroundTask = {
  run_id: string;
  label: string;
  task_type: string;
  progress: number;
  detail: string;
  status: 'running' | 'completed';
};

export type EventApplyResult = {
  apps: CanvasApp[];
  dashboard?: DashboardSnapshot;
  messages: ChatMessage[];
  trace: TraceItem[];
  backgroundTasks: BackgroundTask[];
  // 记忆系统是否在本轮被激活过 —— 让 UI 能提示用户"它在记住你"。
  memoryActive?: boolean;
  // Hermes 实时状态 —— SDK callback 透传过来的思考/状态文本。
  reasoningText?: string;
  currentThinking?: string;
};

export function upsertApp(apps: CanvasApp[], app: CanvasApp): CanvasApp[] {
  const exists = apps.some((item) => item.app_id === app.app_id);
  return exists ? apps.map((item) => (item.app_id === app.app_id ? app : item)) : [...apps, app];
}

export function patchAppInList(apps: CanvasApp[], appId: string, patch: Partial<CanvasApp>): CanvasApp[] {
  return apps.map((item) => (item.app_id === appId ? { ...item, ...patch, updated_at: new Date().toISOString() } : item));
}

export function appendAssistantDelta(messages: ChatMessage[], messageId: string, text: string): ChatMessage[] {
  const index = messages.findIndex((message) => message.id === messageId);
  if (index === -1) {
    return [...messages, { id: messageId, role: "assistant", text, links: [], resources: [] }];
  }
  return messages.map((message) => (message.id === messageId ? { ...message, text: message.text + text } : message));
}

export function attachLink(messages: ChatMessage[], link: ChatAppLink): ChatMessage[] {
  const target = messages.find((message) => message.id === link.message_id);
  if (!target) {
    return [...messages, { id: link.message_id, role: "assistant", text: "", links: [link], resources: [] }];
  }
  if (target.links.some((item) => item.link_id === link.link_id)) {
    return messages;
  }
  return messages.map((message) => (message.id === target.id ? { ...message, links: [...message.links, link] } : message));
}

export function attachResource(messages: ChatMessage[], resource: LearningResource, messageId?: string): ChatMessage[] {
  // Dedup: if this resource is already attached to ANY message, skip.
  if (messages.some((m) => m.resources.some((r) => r.resource_id === resource.resource_id))) {
    return messages;
  }

  const target = messageId
    ? messages.find((message) => message.id === messageId)
    : [...messages].reverse().find((message) => message.role === "assistant");

  if (target) {
    return messages.map((message) =>
      message.id === target.id ? { ...message, resources: [...message.resources, resource] } : message
    );
  }

  // No target message found — create a placeholder so the resource is never silently dropped.
  // When a later assistant.delta arrives with the same messageId, appendAssistantDelta will
  // find this placeholder and append text to it. If messageId is unknown, use a generated id
  // that is unlikely to collide with backend-generated message ids.
  const placeholderId = messageId || `resource-placeholder-${resource.resource_id}`;
  return [...messages, { id: placeholderId, role: "assistant", text: "", links: [], resources: [resource] }];
}

function pushTrace(trace: TraceItem[], item: Omit<TraceItem, "id" | "raw">): TraceItem[] {
  const raw = `${item.name}:${item.status}:${item.detail}`;
  return [
    ...trace.slice(-23),
    {
      ...item,
      id: `${item.name}-${item.status}-${Date.now()}-${trace.length}`,
      raw
    }
  ];
}

export function applyTraceEvent(trace: TraceItem[], event: AgentStreamEvent): TraceItem[] {
  switch (event.type) {
    case "run.step":
      return pushTrace(trace, { name: event.step_name, status: event.status, detail: event.detail ?? "" });
    case "memory.update":
      // 用户可见的记忆反馈:让"它在记住你"这件事被感知到。
      return pushTrace(trace, { name: "memory", status: "completed", detail: `已记住:${event.summary}` });
    case "app.create":
      return pushTrace(trace, { name: "app_create", status: "completed", detail: `${event.app.title} · ${event.app.app_type}` });
    case "app.update":
      return pushTrace(trace, { name: "app_update", status: "completed", detail: event.app_id });
    case "app.link.create":
      return pushTrace(trace, { name: "app_link", status: "completed", detail: event.link.label });
    case "resource.create":
      return pushTrace(trace, { name: "resource_create", status: "completed", detail: `${event.resource.title} · ${event.resource.type}` });
    case "path.update":
      return pushTrace(trace, { name: "path", status: "completed", detail: event.path.title });
    case "verifier.result":
      return pushTrace(trace, { name: "verifier", status: "completed", detail: String(event.result.score) });
    case "context.update":
      return pushTrace(trace, { name: "context", status: "completed", detail: `${event.topic} · ${event.capability}` });
    default:
      return trace;
  }
}

export function applyAgentEvent(state: EventApplyResult, event: AgentStreamEvent): EventApplyResult {
  switch (event.type) {
    case "assistant.delta":
      return { ...state, messages: appendAssistantDelta(state.messages, event.message_id, event.text) };
    case "app.create":
      return {
        ...state,
        apps: upsertApp(state.apps, event.app),
        messages: event.link ? attachLink(state.messages, event.link) : state.messages,
        trace: applyTraceEvent(state.trace, event)
      };
    case "app.update":
      return { ...state, apps: patchAppInList(state.apps, event.app_id, event.patch), trace: applyTraceEvent(state.trace, event) };
    case "app.focus":
      return { ...state, apps: patchAppInList(state.apps, event.app_id, { state: "focused" }) };
    case "app.link.create":
      return { ...state, messages: attachLink(state.messages, event.link), trace: applyTraceEvent(state.trace, event) };
    case "resource.create": {
      return {
        ...state,
        messages: attachResource(state.messages, event.resource, event.message_id),
        trace: applyTraceEvent(state.trace, event)
      };
    }
    case "dashboard.update":
      return { ...state, dashboard: event.dashboard };
    case "memory.update":
      // 标记记忆已激活,TopBar 会展示"记忆已就绪"提示。
      return { ...state, trace: applyTraceEvent(state.trace, event), memoryActive: true };
    case "run.step":
    case "path.update":
    case "verifier.result":
      return { ...state, trace: applyTraceEvent(state.trace, event) };
    // ── Hermes SDK callback 透传的实时状态 ──
    case "hermes.reasoning": {
      // 累积 LLM 思考过程文本(类似 assistant.delta 的拼接)
      const prev = state.reasoningText ?? "";
      return { ...state, reasoningText: (prev + (event.text || "")).slice(-4000) };
    }
    case "hermes.thinking":
      // "正在做什么"的状态文字(如 🔍 搜索中...)
      return { ...state, currentThinking: event.text || "" };
    case "hermes.status":
      return { ...state, currentThinking: event.text || "" };
    case "hermes.tool_call": {
      // 工具调用作为 trace step 展示
      const toolNames = (event.tools || []).join(", ") || `迭代 ${event.iteration}`;
      return {
        ...state,
        trace: applyTraceEvent(state.trace, {
          type: "run.step",
          run_id: event.run_id,
          step_name: "hermes_tool",
          status: "running",
          detail: `工具调用: ${toolNames}`,
        } as AgentStreamEvent),
      };
    }
    case "background.task_started":
      return {
        ...state,
        backgroundTasks: [...state.backgroundTasks, {
          run_id: event.run_id,
          label: event.label,
          task_type: event.task_type,
          progress: 0,
          detail: "正在准备…",
          status: "running"
        }]
      };
    case "background.task_progress":
      return {
        ...state,
        backgroundTasks: state.backgroundTasks.map(t =>
          t.run_id === event.run_id ? { ...t, progress: event.progress, detail: event.detail } : t
        )
      };
    case "background.task_completed":
      return {
        ...state,
        backgroundTasks: state.backgroundTasks.map(t =>
          t.run_id === event.run_id ? { ...t, status: "completed" as const, progress: 1, detail: event.detail } : t
        )
      };
    default:
      return state;
  }
}
