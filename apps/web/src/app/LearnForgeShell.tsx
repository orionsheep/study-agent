import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";
import type { CanvasApp, CanvasViewport, ChatAppLink, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";
import { AppLinkFlightLayer } from "../features/applink-flight/AppLinkFlightLayer";
import { useAppLinkFlight } from "../features/applink-flight/useAppLinkFlight";
import { SpatialCanvas } from "../features/app-canvas/SpatialCanvas";
import { TopBar } from "../features/app-canvas/TopBar";
import { TutorChat } from "../features/tutor-chat/TutorChat";
import {
  approveAndGenerate,
  cancelChatRun,
  createCanvasApp,
  fetchApps,
  fetchChatMessages,
  fetchDashboard,
  logoutAccount,
  patchApp,
  postAppEvent,
  streamChatMessage,
  type ModelProvider,
  type SessionContext
} from "../lib/api/client";
import { applyAgentEvent, applyTraceEvent, type ChatMessage, type TraceItem } from "../lib/events/agentEvents";
import { loadJson, saveJson } from "../lib/state/localStorage";
import { buildResourceCanvasAppRequest } from "./LearnForgeApp";

// #15: append a chat→canvas link to the rail, deduping by link_id and capping to the
// most recent 6 entries. Shared by the app.create / app.link.create event branches.
function appendUniqueLink(links: ChatAppLink[], link: ChatAppLink): ChatAppLink[] {
  if (links.some((item) => item.link_id === link.link_id)) return links;
  return [...links, link].slice(-6);
}

type Props = {
  sessionContext: SessionContext;
  onLogout: () => void;
};

export function LearnForgeShell({ sessionContext, onLogout }: Props) {
  const [apps, setApps] = useState<CanvasApp[]>([]);
  const [dashboard, setDashboard] = useState<DashboardSnapshot | undefined>();
  const [shellMessages, setShellMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text: "你好，我会在右侧陪你学习，把路径、Demo、题目、笔记和仪表盘放到左侧空间画布。你可以直接要求生成路径、资源包或互动演示。",
      links: [],
      resources: []
    }
  ]);
  const [generatedLinks, setGeneratedLinks] = useState<ChatAppLink[]>([]);
  const [trace, setTrace] = useState<TraceItem[]>([]);
  const [memoryActive, setMemoryActive] = useState(false);
  // Hermes 实时状态:思考过程 + thinking 文字
  const [reasoningText, setReasoningText] = useState("");
  const [currentThinking, setCurrentThinking] = useState("");
  const [chatActivities, setChatActivities] = useState<Array<{ anchorMessageId: string; trace: TraceItem[]; isActive: boolean }>>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [backgroundTasks, setBackgroundTasks] = useState<Array<{run_id: string; label: string; progress: number; detail: string; status: 'running'|'completed'}>>([]);
  const [pendingConsent, setPendingConsent] = useState<{run_id: string; capability: string; topic: string; original_message: string} | null>(null);
  const [modelProvider, setModelProvider] = useState<ModelProvider>(() => {
    const stored = loadJson<ModelProvider>("learnforge.settings.modelProvider", "gemini");
    return stored === "gemini" ? "gemini" : "gemini";
  });
  const [viewport, setViewport] = useState<CanvasViewport>(() => loadJson("learnforge.canvas.viewport", { x: 0, y: 0, scale: 1 }));
  const [splitPercent, setSplitPercent] = useState(() => loadJson("learnforge.shell.splitPercent", 68));
  const [canvasHidden, setCanvasHidden] = useState(() => loadJson("learnforge.shell.canvasHidden", false));
  const [learningFocus, setLearningFocus] = useState(() => loadJson<{ topic: string; courseLabel: string; objective: string }>(
    "learnforge.learningFocus", { topic: "", courseLabel: "", objective: "" }
  ));
  const shellRef = useRef<HTMLElement | null>(null);
  // #5: holds the AbortController for the in-flight chat stream so we can cancel it on
  // session switch or unmount. Without this, switching conversations left the previous
  // SSE pump running and writing events into the new session's state.
  const streamAbortRef = useRef<AbortController | null>(null);
  const activeRunIdRef = useRef<string | null>(null);
  const setActiveRun = useCallback((runId: string | null) => {
    activeRunIdRef.current = runId;
    setActiveRunId(runId);
  }, []);
  // #17: mirror of `apps` that always holds the latest list. Callbacks read from this ref
  // so their identity stays stable across streamed app.create events (which would otherwise
  // rebuild openWindow/addResourceToCanvas on every new app and re-render the whole canvas).
  const appsRef = useRef<CanvasApp[]>(apps);
  appsRef.current = apps;

  useEffect(() => {
    saveJson("learnforge.shell.canvasHidden", canvasHidden);
  }, [canvasHidden]);

  // ---- Window manager state (single source of truth) ----
  const windowsStorageKey = `learnforge.canvas.windows.${sessionContext.conversationId}`;
  const [openWindowIds, setOpenWindowIds] = useState<string[]>(() => {
    const stored = loadJson<string[]>(windowsStorageKey, []);
    return Array.isArray(stored) ? stored.filter((id) => typeof id === "string") : [];
  });
  // #17: ref mirror of openWindowIds so callbacks can read the latest value without
  // re-creating on every change.
  const openWindowIdsRef = useRef<string[]>(openWindowIds);
  openWindowIdsRef.current = openWindowIds;
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [fullscreenId, setFullscreenId] = useState<string | null>(null);
  const [zOrder, setZOrder] = useState<string[]>([]);

  useEffect(() => {
    saveJson(windowsStorageKey, openWindowIds);
  }, [windowsStorageKey, openWindowIds]);

  useEffect(() => {
    // #5: cancel any stream still running from the previous session before loading the
    // new one, otherwise its events leak into the new conversation's state.
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    fetchApps(sessionContext).then(setApps).catch(() => setTrace((items) => [
      ...items,
      { id: `backend-wait-${Date.now()}`, name: "backend", status: "running", detail: "等待连接", raw: "backend:running:等待连接" }
    ]));
    fetchDashboard(sessionContext).then(setDashboard).catch(() => undefined);
    fetchChatMessages(sessionContext)
      .then((rows) => {
        if (rows.length) {
          setShellMessages(rows.map((r) => ({ id: r.id, role: r.role as ChatMessage["role"], text: r.text, links: r.links ?? [], resources: [] })));
        }
      })
      .catch(() => undefined);
    return () => {
      // Cancel the in-flight stream when this effect re-runs (session change) or unmounts.
      streamAbortRef.current?.abort();
      streamAbortRef.current = null;
    };
  }, [sessionContext]);

  useEffect(() => {
    saveJson("learnforge.canvas.viewport", viewport);
  }, [viewport]);

  useEffect(() => {
    saveJson("learnforge.shell.splitPercent", splitPercent);
  }, [splitPercent]);

  useEffect(() => {
    saveJson("learnforge.settings.modelProvider", modelProvider);
  }, [modelProvider]);

  useEffect(() => {
    saveJson("learnforge.learningFocus", learningFocus);
  }, [learningFocus]);

  const startSplitDrag = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const shell = shellRef.current;
    if (!shell) return;
    const stacked = window.matchMedia("(max-width: 760px)").matches;
    const previousCursor = document.body.style.cursor;
    const previousSelect = document.body.style.userSelect;
    document.body.style.cursor = stacked ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";

    const update = (clientX: number, clientY: number) => {
      const rect = shell.getBoundingClientRect();
      const raw = stacked ? ((clientY - rect.top) / rect.height) * 100 : ((clientX - rect.left) / rect.width) * 100;
      const min = stacked ? 44 : 48;
      const max = stacked ? 72 : 74;
      setSplitPercent(Math.min(max, Math.max(min, Math.round(raw))));
    };

    update(event.clientX, event.clientY);
    const onMove = (moveEvent: PointerEvent) => update(moveEvent.clientX, moveEvent.clientY);
    const onUp = () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousSelect;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  }, []);

  const computeCenterPos = useCallback((app: CanvasApp, cascadeCount: number) => {
    const shell = shellRef.current;
    const canvasWidth = shell ? shell.getBoundingClientRect().width * (splitPercent / 100) : window.innerWidth * 0.68;
    const canvasHeight = shell ? shell.getBoundingClientRect().height : window.innerHeight;
    const cx = (canvasWidth / 2 - viewport.x) / viewport.scale;
    const cy = (canvasHeight / 2 - viewport.y) / viewport.scale;
    const cascade = (cascadeCount % 5) * 28;
    return {
      x: Math.round(cx - app.size.width / 2 + cascade),
      y: Math.round(cy - app.size.height / 2 + cascade)
    };
  }, [splitPercent, viewport.x, viewport.y, viewport.scale]);

  const focusWindow = useCallback((appId: string) => {
    setFocusedId(appId);
    setZOrder((z) => [...z.filter((id) => id !== appId), appId]);
  }, []);

  const openWindow = useCallback((appId: string) => {
    const app = appsRef.current.find((item) => item.app_id === appId);
    if (!app) return;
    const pinned = ["app-profile", "app-dashboard", "app-resource"].includes(appId);
    // #17: read openWindowIds via a ref-backed getter pattern — use a functional setState
    // below for the append, and for the existence check fall back to a ref so this callback
    // doesn't need openWindowIds in its deps.
    const openIdsRef = openWindowIdsRef.current;
    const alreadyOpen = pinned || openIdsRef.includes(appId);
    if (!alreadyOpen) {
      const pos = computeCenterPos(app, openIdsRef.length);
      setApps((current) => current.map((item) => (item.app_id === appId ? { ...item, position: pos } : item)));
      patchApp(appId, { position: pos }, sessionContext).catch(() => undefined);
      setOpenWindowIds((ids) => (ids.includes(appId) ? ids : [...ids, appId]));
    }
    focusWindow(appId);
  }, [computeCenterPos, focusWindow, sessionContext]);

  const closeWindow = useCallback((appId: string) => {
    setOpenWindowIds((ids) => ids.filter((id) => id !== appId));
    setZOrder((z) => z.filter((id) => id !== appId));
    setFocusedId((f) => (f === appId ? null : f));
    setFullscreenId((fs) => (fs === appId ? null : fs));
  }, []);

  const focusAppById = useCallback((appId: string, nextState?: CanvasApp["state"]) => {
    openWindow(appId);
    if (nextState === "fullscreen") setFullscreenId(appId);
  }, [openWindow]);

  const toggleFullscreen = useCallback((appId: string) => {
    setFullscreenId((cur) => (cur === appId ? null : appId));
  }, []);

  const { flight, open } = useAppLinkFlight(focusAppById, sessionContext);

  const applyEvent = useCallback((event: Parameters<typeof applyAgentEvent>[1]) => {
    if (event.type === "run.started") {
      setActiveRun(event.run_id);
    }
    if (event.type === "run.done") {
      setActiveRun(null);
      setIsStreaming(false);
    }
    setApps((currentApps) => applyAgentEvent({ apps: currentApps, messages: [], trace: [], backgroundTasks: [] }, event).apps);
    setShellMessages((currentMessages) => applyAgentEvent({ apps: [], messages: currentMessages, trace: [], backgroundTasks: [] }, event).messages);
    // #15: both app.create (carrying an inline link) and app.link.create append to the
    // generated-links rail. Dedup by link_id and cap to the last 6 (single shared helper
    // instead of two near-identical inline slices).
    const link = (event.type === "app.create" || event.type === "app.link.create") ? event.link : undefined;
    if (link) {
      setGeneratedLinks((links) => appendUniqueLink(links, link));
    }
    if (event.type === "dashboard.update") {
      setDashboard(event.dashboard);
    }
    if (event.type === "memory.update") {
      setMemoryActive(true);
    }
    // Hermes SDK callback 透传的实时状态
    if (event.type === "hermes.reasoning") {
      setReasoningText((prev) => (prev + (event.text || "")).slice(-4000));
    }
    if (event.type === "hermes.thinking" || event.type === "hermes.status") {
      setCurrentThinking(event.text || "");
    }
    if (event.type === "hermes.tool_call") {
      const tools = (event.tools || []).join(", ") || `迭代 ${event.iteration}`;
      setTrace((items) => [...items.slice(-12), {
        id: `hermes-tool-${Date.now()}`,
        name: "hermes_tool",
        status: "running",
        detail: `工具调用: ${tools}`,
        raw: `hermes_tool:running:${tools}`,
      }]);
    }
    if (event.type === "context.update") {
      const ctx = event as { type: 'context.update'; topic: string; capability: string; course_label?: string; learning_objective?: string };
      setLearningFocus({
        topic: ctx.topic || "",
        courseLabel: ctx.course_label || "",
        objective: ctx.learning_objective || "",
      });
    }
    // Handle consent_required — show confirmation UI for heavy tasks
    if (event.type === "consent_required") {
      setPendingConsent({
        run_id: event.run_id,
        capability: event.capability,
        topic: event.topic,
        original_message: event.original_message,
      });
      setIsStreaming(false); // unblock input
    }
    // Handle background task events — unblock the chat input
    if (event.type === "background.task_started") {
      setIsStreaming(false); // unblock input so user can continue chatting
      // #8: event is narrowed to the background.task_started union member by the type
      // check above, so the fields are statically known — no `as any` needed.
      setBackgroundTasks((tasks) => [...tasks, {
        run_id: event.run_id,
        label: event.label,
        progress: 0,
        detail: "正在准备…",
        status: "running"
      }]);
      setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
        activity.isActive && index === currentActivities.length - 1
          ? { ...activity, isActive: false }
          : activity
      ));
    }
    if (event.type === "background.task_progress") {
      setBackgroundTasks((tasks) => tasks.map(t =>
        t.run_id === event.run_id ? { ...t, progress: event.progress, detail: event.detail } : t
      ));
    }
    if (event.type === "background.task_completed") {
      setBackgroundTasks((tasks) => tasks.map(t =>
        t.run_id === event.run_id ? { ...t, status: "completed" as const, progress: 1, detail: event.detail } : t
      ));
    }
    setTrace((currentTrace) => applyTraceEvent(currentTrace, event));
    setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
      activity.isActive && index === currentActivities.length - 1
        ? { ...activity, trace: applyTraceEvent(activity.trace, event) }
        : activity
    )
    );
  }, [setActiveRun]);

  const send = async (text: string, attachments?: Array<{ name: string; preview?: string }>) => {
    const now = Date.now();
    const userMessage: ChatMessage = {
      id: `user-${now}`,
      role: "user",
      text,
      links: [],
      resources: [],
      attachments: attachments?.length ? attachments : undefined,
    };
    const initialTrace: TraceItem[] = [
      { id: `backend-send-${now}`, name: "backend", status: "running", detail: "请求已发送", raw: "backend:running:请求已发送" }
    ];
    setShellMessages((items) => [...items, userMessage]);
    setGeneratedLinks([]);
    setTrace(initialTrace);
    setChatActivities((activities) => [...activities.slice(-7), { anchorMessageId: userMessage.id, trace: initialTrace, isActive: true }]);
    setActiveRun(null);
    setIsStreaming(true);
    // 重置 Hermes 实时状态
    setReasoningText("");
    setCurrentThinking("");
    // Extract image data URLs for multimodal understanding by the AI model.
    const imageData = attachments?.filter((item) => item.preview?.startsWith("data:image/")).map((item) => item.preview!) ?? undefined;
    const names = attachments?.map((item) => item.name).join("、");
    const backendText = names ? `${text}\n（用户上传了附件：${names}）`.trim() : text;
    let controller: AbortController | null = null;
    try {
      // #5: create a fresh AbortController for this turn; cancel any prior one first.
      streamAbortRef.current?.abort();
      controller = new AbortController();
      streamAbortRef.current = controller;
      await streamChatMessage(backendText, applyEvent, sessionContext, modelProvider, imageData, controller.signal);
      const fresh = await fetchDashboard(sessionContext);
      setDashboard(fresh);
    } catch (error) {
      // Intentional cancel (session switch / unmount) — don't surface as an error.
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      const detail = error instanceof Error ? error.message : "未知错误";
      const failedTraceItem: TraceItem = {
        id: `backend-failed-${Date.now()}`,
        name: "backend",
        status: "failed",
        detail: "连接失败",
        raw: "backend:failed:连接失败"
      };
      setTrace((items) => [
        ...items.slice(-8),
        failedTraceItem
      ]);
      setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
        activity.isActive && index === currentActivities.length - 1
          ? { ...activity, trace: [...activity.trace.slice(-8), failedTraceItem] }
          : activity
      )
      );
      setShellMessages((items) => [
        ...items,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: `我这次没有连上后端聊天流：${detail}。请确认 LearnForge API 服务正在运行，然后再试一次。`,
          links: [],
          resources: []
        }
      ]);
    } finally {
      if (controller && streamAbortRef.current === controller) {
        streamAbortRef.current = null;
      }
      setActiveRun(null);
      setIsStreaming(false);
      setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
        activity.isActive && index === currentActivities.length - 1 ? { ...activity, isActive: false } : activity
      ));
    }
  };

  // ── Consent flow: approve heavy generation ──
  const approveGeneration = useCallback(async () => {
    if (!pendingConsent) return;
    const consent = pendingConsent;
    setPendingConsent(null); // dismiss banner immediately
    const text = `确认生成: ${consent.topic}`;
    const userMessage: ChatMessage = {
      id: `user-approve-${Date.now()}`,
      role: "user",
      text,
      links: [],
      resources: [],
    };
    setShellMessages((items) => [...items, userMessage]);
    setIsStreaming(true);
    const controller = new AbortController();
    streamAbortRef.current?.abort();
    streamAbortRef.current = controller;
    try {
      await approveAndGenerate(
        { capability: consent.capability, topic: consent.topic, original_message: consent.original_message },
        applyEvent,
        sessionContext,
        modelProvider,
        controller.signal,
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
    } finally {
      if (streamAbortRef.current === controller) streamAbortRef.current = null;
      setIsStreaming(false);
    }
  }, [pendingConsent, sessionContext, modelProvider, applyEvent]);

  const dismissConsent = useCallback(() => {
    setPendingConsent(null);
  }, []);

  const stopAgentRun = useCallback(async () => {
    const runId = activeRunIdRef.current;
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setActiveRun(null);
    setIsStreaming(false);
    const cancelledTraceItem: TraceItem = {
      id: `cancelled-${Date.now()}`,
      name: "cancelled",
      status: "cancelled",
      detail: "已停止当前 Agent 任务",
      raw: "cancelled:cancelled:已停止当前 Agent 任务"
    };
    setTrace((items) => [...items.slice(-8), cancelledTraceItem]);
    setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
      activity.isActive && index === currentActivities.length - 1
        ? { ...activity, trace: [...activity.trace.slice(-8), cancelledTraceItem], isActive: false }
        : activity
    ));
    if (!runId) return;
    try {
      await cancelChatRun(runId, sessionContext);
    } catch (error) {
      console.warn("[LearnForge] 停止后端 Agent 失败", error);
    }
  }, [sessionContext, setActiveRun]);

  const onAppEvent = async (appId: string, eventType: string, payload: Record<string, unknown>) => {
    setTrace((items) => [
      ...items.slice(-14),
      { id: `${appId}-${eventType}-${Date.now()}`, name: "app_event", status: "running", detail: `${appId}:${eventType}`, raw: `app_event:running:${appId}:${eventType}` }
    ]);
    const response = await postAppEvent(appId, eventType, payload, sessionContext);
    const typed = response as { dashboard?: DashboardSnapshot; app?: CanvasApp | null; action_status?: string; reason?: string | null };
    if (typed.app && eventType !== "layout.drag" && eventType !== "layout.resize") {
      setApps((current) => current.map((app) => (app.app_id === typed.app!.app_id ? typed.app! : app)));
    }
    if (typed.action_status && typed.action_status !== "recorded") {
      const status = typed.action_status;
      setTrace((items) => [
        ...items.slice(-14),
        { id: `${eventType}-${status}-${Date.now()}`, name: eventType, status, detail: typed.reason ?? "", raw: `${eventType}:${status}:${typed.reason ?? ""}` }
      ]);
    }
    if (typed.dashboard) setDashboard(typed.dashboard);
  };

  const deleteApp = useCallback((appId: string) => {
    setApps((current) => current.filter((app) => app.app_id !== appId));
    setOpenWindowIds((ids) => ids.filter((id) => id !== appId));
    setZOrder((z) => z.filter((id) => id !== appId));
    setFocusedId((f) => (f === appId ? null : f));
    setFullscreenId((fs) => (fs === appId ? null : fs));
    onAppEvent(appId, "app.delete", { app_id: appId }).catch(() => undefined);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addResourceToCanvas = useCallback(async (resource: LearningResource, targetPosition?: { x: number; y: number }) => {
    setTrace((items) => [
      ...items.slice(-14),
      { id: `drop-${Date.now()}`, name: "canvas_materializer", status: "running", detail: "拖曳资源到画布", raw: "canvas_materializer:running:拖曳资源到画布" }
    ]);
    const app = await createCanvasApp(buildResourceCanvasAppRequest(resource), sessionContext);
    // #14: avoid Math.max(...spread) which can overflow the call stack for huge app lists.
    // #17: read the latest apps via a ref so this callback's identity stays stable
    // (it no longer needs `apps` in deps, which previously rebuilt it on every stream).
    const nextZ = appsRef.current.reduce((max, a) => Math.max(max, a.z_index ?? 0), 30) + 1;
    const nextApp = { ...app, position: targetPosition ?? app.position, z_index: nextZ } as CanvasApp;
    setApps((current) => [...current, nextApp]);
    patchApp(nextApp.app_id, { position: targetPosition ?? app.position, payload: nextApp.payload }, sessionContext).catch(() => undefined);
    setOpenWindowIds((ids) => (ids.includes(nextApp.app_id) ? ids : [...ids, nextApp.app_id]));
    focusWindow(nextApp.app_id);
    setTrace((items) => [
      ...items.slice(-14),
      { id: `drop-done-${Date.now()}`, name: "canvas_materializer", status: "completed", detail: `已拖入 ${nextApp.title}`, raw: `canvas_materializer:completed:已拖入 ${nextApp.title}` }
    ]);
  }, [focusWindow, sessionContext]);

  return (
    <div className="lf-root">
      <TopBar
        isStreaming={isStreaming}
        traceLatest={trace.at(-1)}
        memoryActive={memoryActive}
        canvasHidden={canvasHidden}
        onToggleCanvas={() => setCanvasHidden((v) => !v)}
        onLogout={() => { logoutAccount(); onLogout(); }}
        currentTopic={learningFocus.topic}
        courseLabel={learningFocus.courseLabel}
        learningObjective={learningFocus.objective}
      />
      <main
        ref={shellRef}
        className={`learnforge-shell ${canvasHidden ? "canvas-hidden" : ""}`}
        style={{
          "--canvas-pane": `${splitPercent}%`,
          "--canvas-pane-mobile": `${Math.max(44, Math.min(72, splitPercent))}%`
        } as CSSProperties}
      >
      {!canvasHidden ? (
        <>
        <SpatialCanvas
          apps={apps}
          dashboard={dashboard}
          viewport={viewport}
          setViewport={setViewport}
          setApps={setApps}
          openWindowIds={openWindowIds}
          focusedId={focusedId}
          fullscreenId={fullscreenId}
          zOrder={zOrder}
          openWindow={openWindow}
          closeWindow={closeWindow}
          focusWindow={focusWindow}
          toggleFullscreen={toggleFullscreen}
          deleteApp={deleteApp}
          onAppEvent={onAppEvent}
          onDashboardUpdate={setDashboard}
          onResourceDrop={addResourceToCanvas}
          sessionContext={sessionContext}
        />
        <div
          className="pane-resizer"
          data-testid="pane-resizer"
          role="separator"
          aria-label="拖动调整画布和导师窗口比例"
          aria-orientation="vertical"
          aria-valuemin={44}
          aria-valuemax={74}
          aria-valuenow={splitPercent}
          title="拖动调整左右窗口比例，双击恢复默认"
          onPointerDown={startSplitDrag}
          onDoubleClick={() => setSplitPercent(68)}
          // #22: make the divider keyboard-operable. Arrow keys nudge by 2%, Home/End
          // jump to the min/max, so keyboard-only users aren't locked out of resizing.
          tabIndex={0}
          onKeyDown={(event) => {
            const min = 48;
            const max = 74;
            if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
              event.preventDefault();
              setSplitPercent((current) => Math.max(min, current - 2));
            } else if (event.key === "ArrowRight" || event.key === "ArrowUp") {
              event.preventDefault();
              setSplitPercent((current) => Math.min(max, current + 2));
            } else if (event.key === "Home") {
              event.preventDefault();
              setSplitPercent(min);
            } else if (event.key === "End") {
              event.preventDefault();
              setSplitPercent(max);
            }
          }}
        >
          <span />
        </div>
        </>
      ) : null}
      {pendingConsent ? (
        <div className="lf-consent-banner" style={{
          position: "fixed", bottom: "120px", left: "50%", transform: "translateX(-50%)",
          zIndex: 1000, background: "linear-gradient(135deg, #1e293b, #0f172a)",
          border: "1px solid rgba(100,216,255,.35)", borderRadius: "16px",
          padding: "20px 28px", maxWidth: "520px", width: "calc(100% - 40px)",
          boxShadow: "0 24px 80px rgba(0,0,0,.55)", color: "#e2e8f0",
          display: "flex", flexDirection: "column", gap: "14px",
        }}>
          <div style={{ fontSize: "15px", lineHeight: "1.55" }}>
            <strong style={{ color: "#64d8ff" }}>
              {pendingConsent.capability === "ppt" ? "📊 生成 PPT" :
               pendingConsent.capability === "interactive_demo" ? "🎮 生成交互演示" :
               pendingConsent.capability === "detailed_analysis" ? "📝 生成分析报告" :
               pendingConsent.capability === "image_explanation" ? "🎨 生成示意图" :
               pendingConsent.capability === "mindmap" ? "🧠 生成思维导图" :
               pendingConsent.capability === "quiz" ? "📋 生成练习题" :
               `⚡ 生成 ${pendingConsent.capability}`}
            </strong>
            <div style={{ marginTop: "6px", color: "#94a3b8", fontSize: "14px" }}>
              主题：{pendingConsent.topic}
            </div>
            <div style={{ marginTop: "4px", color: "#64748b", fontSize: "12px" }}>
              ⚡️ 这是一个比较耗时的任务，确认后会在后台生成，不影响你继续提问。
            </div>
          </div>
          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
            <button onClick={dismissConsent} style={{
              padding: "10px 22px", borderRadius: "10px", border: "1px solid rgba(255,255,255,.18)",
              background: "transparent", color: "#94a3b8", cursor: "pointer",
              fontSize: "14px", fontWeight: 600,
            }}>
              取消
            </button>
            <button onClick={approveGeneration} style={{
              padding: "10px 22px", borderRadius: "10px", border: "none",
              background: "linear-gradient(135deg, #22d3ee, #3b82f6)", color: "#fff",
              cursor: "pointer", fontSize: "14px", fontWeight: 700,
            }}>
              开始生成
            </button>
          </div>
        </div>
      ) : null}
      <TutorChat
        messages={shellMessages}
        generatedLinks={generatedLinks}
        activities={chatActivities}
        isStreaming={isStreaming}
        backgroundTasks={backgroundTasks}
        reasoningText={reasoningText}
        currentThinking={currentThinking}
        modelProvider={modelProvider}
        onModelProviderChange={setModelProvider}
        onSend={send}
        canStop={isStreaming || !!activeRunId}
        onStop={stopAgentRun}
        onSummarize={async () => { await send("请把本轮学习总结到笔记 App"); }}
        onOpenLink={(link: ChatAppLink, rect: DOMRect) => { open(link, rect).catch(() => undefined); }}
        onAddResourceToCanvas={addResourceToCanvas}
      />
      <AppLinkFlightLayer flight={flight} />
      </main>
    </div>
  );
}
