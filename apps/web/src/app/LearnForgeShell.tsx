import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";
import type { CanvasApp, CanvasViewport, ChatAppLink, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";
import { AppLinkFlightLayer } from "../features/applink-flight/AppLinkFlightLayer";
import { useAppLinkFlight } from "../features/applink-flight/useAppLinkFlight";
import { SpatialCanvas } from "../features/app-canvas/SpatialCanvas";
import { TopBar } from "../features/app-canvas/TopBar";
import { TutorChat } from "../features/tutor-chat/TutorChat";
import {
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
  const [chatActivities, setChatActivities] = useState<Array<{ anchorMessageId: string; trace: TraceItem[]; isActive: boolean }>>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [backgroundTasks, setBackgroundTasks] = useState<Array<{run_id: string; label: string; progress: number; detail: string; status: 'running'|'completed'}>>([]);
  const [modelProvider, setModelProvider] = useState<ModelProvider>(() => {
    const stored = loadJson<ModelProvider>("learnforge.settings.modelProvider", "gemini");
    return stored === "mimo" || stored === "gemini" ? stored : "gemini";
  });
  const [viewport, setViewport] = useState<CanvasViewport>(() => loadJson("learnforge.canvas.viewport", { x: 0, y: 0, scale: 1 }));
  const [splitPercent, setSplitPercent] = useState(() => loadJson("learnforge.shell.splitPercent", 68));
  const [canvasHidden, setCanvasHidden] = useState(() => loadJson("learnforge.shell.canvasHidden", false));
  const [learningFocus, setLearningFocus] = useState(() => loadJson<{ topic: string; courseLabel: string; objective: string }>(
    "learnforge.learningFocus", { topic: "", courseLabel: "", objective: "" }
  ));
  const shellRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    saveJson("learnforge.shell.canvasHidden", canvasHidden);
  }, [canvasHidden]);

  // ---- Window manager state (single source of truth) ----
  const windowsStorageKey = `learnforge.canvas.windows.${sessionContext.conversationId}`;
  const [openWindowIds, setOpenWindowIds] = useState<string[]>(() => {
    const stored = loadJson<string[]>(windowsStorageKey, []);
    return Array.isArray(stored) ? stored.filter((id) => typeof id === "string") : [];
  });
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [fullscreenId, setFullscreenId] = useState<string | null>(null);
  const [zOrder, setZOrder] = useState<string[]>([]);

  useEffect(() => {
    saveJson(windowsStorageKey, openWindowIds);
  }, [windowsStorageKey, openWindowIds]);

  useEffect(() => {
    fetchApps(sessionContext).then(setApps).catch(() => setTrace((items) => [
      ...items,
      { id: `backend-wait-${Date.now()}`, name: "backend", status: "running", detail: "等待连接", raw: "backend:running:等待连接" }
    ]));
    fetchDashboard(sessionContext).then(setDashboard).catch(() => undefined);
    fetchChatMessages(sessionContext)
      .then((rows) => {
        if (rows.length) {
          setShellMessages(rows.map((r) => ({ id: r.id, role: r.role as ChatMessage["role"], text: r.text, links: [], resources: [] })));
        }
      })
      .catch(() => undefined);
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
    const app = apps.find((item) => item.app_id === appId);
    if (!app) return;
    const pinned = ["app-profile", "app-dashboard", "app-resource"].includes(appId);
    const alreadyOpen = pinned || openWindowIds.includes(appId);
    if (!alreadyOpen) {
      const pos = computeCenterPos(app, openWindowIds.length);
      setApps((current) => current.map((item) => (item.app_id === appId ? { ...item, position: pos } : item)));
      patchApp(appId, { position: pos }, sessionContext).catch(() => undefined);
      setOpenWindowIds((ids) => (ids.includes(appId) ? ids : [...ids, appId]));
    }
    focusWindow(appId);
  }, [apps, openWindowIds, computeCenterPos, focusWindow, sessionContext]);

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
    setApps((currentApps) => applyAgentEvent({ apps: currentApps, messages: [], trace: [], backgroundTasks: [] }, event).apps);
    setShellMessages((currentMessages) => applyAgentEvent({ apps: [], messages: currentMessages, trace: [], backgroundTasks: [] }, event).messages);
    if (event.type === "app.create" && event.link) {
      const link = event.link;
      setGeneratedLinks((links) => (links.some((item) => item.link_id === link.link_id) ? links : [...links.slice(-5), link]));
    }
    if (event.type === "app.link.create" && event.link) {
      const link = event.link;
      setGeneratedLinks((links) => (links.some((item) => item.link_id === link.link_id) ? links : [...links.slice(-5), link]));
    }
    if (event.type === "dashboard.update") {
      setDashboard(event.dashboard);
    }
    if (event.type === "context.update") {
      const ctx = event as { type: 'context.update'; topic: string; capability: string; course_label?: string; learning_objective?: string };
      setLearningFocus({
        topic: ctx.topic || "",
        courseLabel: ctx.course_label || "",
        objective: ctx.learning_objective || "",
      });
    }
    // Handle background task events — unblock the chat input
    if (event.type === "background.task_started") {
      setIsStreaming(false); // unblock input so user can continue chatting
      setBackgroundTasks((tasks) => [...tasks, {
        run_id: (event as any).run_id,
        label: (event as any).label,
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
        t.run_id === (event as any).run_id ? { ...t, progress: (event as any).progress, detail: (event as any).detail } : t
      ));
    }
    if (event.type === "background.task_completed") {
      setBackgroundTasks((tasks) => tasks.map(t =>
        t.run_id === (event as any).run_id ? { ...t, status: "completed" as const, progress: 1, detail: (event as any).detail } : t
      ));
    }
    setTrace((currentTrace) => applyTraceEvent(currentTrace, event));
    setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
      activity.isActive && index === currentActivities.length - 1
        ? { ...activity, trace: applyTraceEvent(activity.trace, event) }
        : activity
    )
    );
  }, []);

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
    setTrace(initialTrace);
    setChatActivities((activities) => [...activities.slice(-7), { anchorMessageId: userMessage.id, trace: initialTrace, isActive: true }]);
    setIsStreaming(true);
    // Extract image data URLs for multimodal understanding by the AI model.
    const imageData = attachments?.filter((item) => item.preview?.startsWith("data:image/")).map((item) => item.preview!) ?? undefined;
    const names = attachments?.map((item) => item.name).join("、");
    const backendText = names ? `${text}\n（用户上传了附件：${names}）`.trim() : text;
    try {
      await streamChatMessage(backendText, applyEvent, sessionContext, modelProvider, imageData);
      const fresh = await fetchDashboard(sessionContext);
      setDashboard(fresh);
    } catch (error) {
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
      setIsStreaming(false);
      setChatActivities((currentActivities) => currentActivities.map((activity, index) =>
        activity.isActive && index === currentActivities.length - 1 ? { ...activity, isActive: false } : activity
      ));
    }
  };

  const onAppEvent = async (appId: string, eventType: string, payload: Record<string, unknown>) => {
    setTrace((items) => [
      ...items.slice(-14),
      { id: `${appId}-${eventType}-${Date.now()}`, name: "app_event", status: "running", detail: `${appId}:${eventType}`, raw: `app_event:running:${appId}:${eventType}` }
    ]);
    const response = await postAppEvent(appId, eventType, payload, sessionContext);
    const typed = response as { dashboard?: DashboardSnapshot; app?: CanvasApp | null; action_status?: string; reason?: string | null };
    if (typed.app) {
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
    const nextApp = { ...app, position: targetPosition ?? app.position, z_index: Math.max(30, ...apps.map((a) => a.z_index ?? 0)) + 1 } as CanvasApp;
    setApps((current) => [...current, nextApp]);
    patchApp(nextApp.app_id, { position: targetPosition ?? app.position, payload: nextApp.payload }, sessionContext).catch(() => undefined);
    setOpenWindowIds((ids) => (ids.includes(nextApp.app_id) ? ids : [...ids, nextApp.app_id]));
    focusWindow(nextApp.app_id);
    setTrace((items) => [
      ...items.slice(-14),
      { id: `drop-done-${Date.now()}`, name: "canvas_materializer", status: "completed", detail: `已拖入 ${nextApp.title}`, raw: `canvas_materializer:completed:已拖入 ${nextApp.title}` }
    ]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apps]);

  return (
    <div className="lf-root">
      <TopBar
        isStreaming={isStreaming}
        traceLatest={trace.at(-1)}
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
        >
          <span />
        </div>
        </>
      ) : null}
      <TutorChat
        messages={shellMessages}
        generatedLinks={generatedLinks}
        activities={chatActivities}
        isStreaming={isStreaming}
        backgroundTasks={backgroundTasks}
        modelProvider={modelProvider}
        onModelProviderChange={setModelProvider}
        onSend={send}
        onSummarize={async () => { await send("请把本轮学习总结到笔记 App"); }}
        onOpenLink={(link: ChatAppLink, rect: DOMRect) => { open(link, rect).catch(() => undefined); }}
        onAddResourceToCanvas={addResourceToCanvas}
      />
      <AppLinkFlightLayer flight={flight} />
      </main>
    </div>
  );
}
