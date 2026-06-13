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
  const target = messageId
    ? messages.find((message) => message.id === messageId)
    : [...messages].reverse().find((message) => message.role === "assistant");
  if (!target) {
    return messageId
      ? [...messages, { id: messageId, role: "assistant", text: "", links: [], resources: [resource] }]
      : messages;
  }
  if (target.resources.some((item) => item.resource_id === resource.resource_id)) return messages;
  return messages.map((message) =>
    message.id === target.id ? { ...message, resources: [...message.resources, resource] } : message
  );
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
      return pushTrace(trace, { name: "memory", status: "completed", detail: event.summary });
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
    case "run.step":
    case "memory.update":
    case "path.update":
    case "verifier.result":
      return { ...state, trace: applyTraceEvent(state.trace, event) };
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
