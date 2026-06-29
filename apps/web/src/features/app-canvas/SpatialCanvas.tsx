import { useEffect, useMemo, useRef, useState, type DragEvent, type PointerEvent as ReactPointerEvent, type PointerEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { CanvasApp, CanvasViewport, DashboardSnapshot, LearningResource } from "@learnforge/app-protocol";
import { Fullscreen, Grip, LocateFixed, Maximize2, Minus, Plus, Search, Shrink, Sparkles, Trash2, X } from "lucide-react";
import { NativeAppRenderer } from "../learning-apps/NativeAppRenderer";
import { isPinnedApp, isSystemModule, isRealTimeResource } from "./pinned";
import { clampWindowPositionToViewport, samePoint } from "./windowBounds";
import { patchApp, type SessionContext } from "../../lib/api/client";
import {
  APP_ICON_FILES,
  FOLDER_ICON_FILES,
  type FolderIconKey,
  themedAppIcon,
  themedIconAssetFromPath,
} from "../../lib/assets/appearanceAssets";
import { saveJson } from "../../lib/state/localStorage";
import { useTheme } from "../../lib/state/useTheme";

type FolderKey = FolderIconKey;

type Props = {
  apps: CanvasApp[];
  dashboard?: DashboardSnapshot;
  viewport: CanvasViewport;
  setViewport: (viewport: CanvasViewport) => void;
  setApps: (apps: CanvasApp[]) => void;
  // Window-manager state (owned by LearnForgeApp)
  openWindowIds: string[];
  focusedId: string | null;
  fullscreenId: string | null;
  zOrder: string[];
  openWindow: (appId: string) => void;
  closeWindow: (appId: string) => void;
  focusWindow: (appId: string) => void;
  toggleFullscreen: (appId: string) => void;
  deleteApp: (appId: string) => void;
  onAppEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void | Promise<void>;
  onDashboardUpdate?: (dashboard: DashboardSnapshot) => void;
  onResourceDrop?: (resource: LearningResource, position: { x: number; y: number }) => void | Promise<void>;
  sessionContext: SessionContext;
};

type DragState =
  | { kind: "canvas"; startX: number; startY: number; viewport: CanvasViewport }
  | { kind: "app"; appId: string; startX: number; startY: number; x: number; y: number }
  | { kind: "resize"; appId: string; startX: number; startY: number; width: number; height: number };

type WindowInteraction = {
  kind: "app" | "resize";
  appId: string;
  pointerId: number;
  startX: number;
  startY: number;
  scale: number;
  baseX: number;
  baseY: number;
  baseWidth: number;
  baseHeight: number;
  nextX: number;
  nextY: number;
  nextWidth: number;
  nextHeight: number;
  raf?: number;
};

function appStatusClass(app: CanvasApp) {
  if (app.status === "ready") return "st-done";
  if (app.status === "creating") return "st-rec";
  if (app.status === "blocked") return "st-weak";
  if (app.status === "error") return "st-risk";
  return "st-learning";
}

function appStatusLabel(app: CanvasApp) {
  return { ready: "已就绪", creating: "生成中", blocked: "待连接", error: "异常" }[app.status] ?? app.status;
}

function appTypeLabel(appType: string) {
  return {
    "profile.dashboard": "学习画像",
    "learning.path": "学习路径",
    "knowledge.graph": "知识图谱",
    "mindmap.concept": "概念图",
    "quiz.practice": "练习题",
    "physics.work_energy_demo": "物理演示",
    "math.gradient_descent_demo": "数学演示",
    "code.lab": "代码实验",
    "notes.session": "学习笔记",
    "dashboard.learning": "学习仪表盘",
    "ppt.preview": "课件预览",
    "image.explanation": "教学图解",
    "video.script": "视频脚本",
    "video.player": "教学视频",
    "resource.center": "学习资源",
    "resource.folder": "资源文件夹",
    "custom.html": "互动演示",
    "english.workspace": "英语工作区",
    "notebooklm.workspace": "NotebookLM",
    "humanities.notebook": "NotebookLM",
    "exam.cram": "期末速成"
  }[appType] ?? "学习应用";
}

function appAccent(app: CanvasApp) {
  const palette = {
    "profile.dashboard": "linear-gradient(135deg,#5b8cff,#9d7bff)",
    "learning.path": "linear-gradient(135deg,#4ade80,#5b8cff)",
    "knowledge.graph": "linear-gradient(135deg,#9d7bff,#f9a23c)",
    "mindmap.concept": "linear-gradient(135deg,#7aa2ff,#b79dff)",
    "quiz.practice": "linear-gradient(135deg,#f9a23c,#f87a7a)",
    "physics.work_energy_demo": "linear-gradient(135deg,#5b8cff,#4ade80)",
    "math.gradient_descent_demo": "linear-gradient(135deg,#5b8cff,#9d7bff)",
    "code.lab": "linear-gradient(135deg,#222b4a,#5b8cff)",
    "notes.session": "linear-gradient(135deg,#b79dff,#f9a23c)",
    "dashboard.learning": "linear-gradient(135deg,#4ade80,#9d7bff)",
    "ppt.preview": "linear-gradient(135deg,#5b8cff,#b79dff)",
    "image.explanation": "linear-gradient(135deg,#9d7bff,#7aa2ff)",
    "video.script": "linear-gradient(135deg,#f87a7a,#9d7bff)",
    "resource.center": "linear-gradient(135deg,#4ade80,#7aa2ff)",
    "custom.html": "linear-gradient(135deg,#5b8cff,#f9a23c)",
    "english.workspace": "linear-gradient(135deg,#f59e0b,#ef4444)",
    "notebooklm.workspace": "linear-gradient(135deg,#10b981,#38bdf8)",
    "humanities.notebook": "linear-gradient(135deg,#8b5cf6,#ec4899)",
    "exam.cram": "linear-gradient(135deg,#f97316,#22c55e)"
  } as Record<string, string>;
  return palette[app.app_type] ?? "var(--accent-grad)";
}

function AppIcon({ appType, size = 22, className = "", srcOverride }: { appType: string; size?: number; className?: string; srcOverride?: string }) {
  const { theme } = useTheme();
  const src = srcOverride ? themedIconAssetFromPath(srcOverride, theme) : themedAppIcon(appType, theme);
  if (src) {
    return <img src={src} width={size} height={size} alt="" style={{ objectFit: "contain", borderRadius: 6, display: "block" }} className={className} />;
  }
  return <Sparkles size={size} />;
}

type FolderDefinition = {
  key: FolderKey;
  title: string;
  subtitle: string;
  appTypes?: string[];
  matcher?: (app: CanvasApp) => boolean;
  iconType: string;
};

type FolderPayload = {
  folderKey: FolderKey;
  subtitle: string;
  count: number;
  updatedAt?: string;
  items: CanvasApp[];
  recentTitles: string[];
};

function folderIconSrc(app: CanvasApp) {
  const payload = app.payload as Partial<FolderPayload> | undefined;
  const file = payload?.folderKey ? FOLDER_ICON_FILES[payload.folderKey] : FOLDER_ICON_FILES.other;
  return `/icons/${file}`;
}

function customHtmlIsPptDeck(app: CanvasApp): boolean {
  if (app.app_type !== "custom.html") return false;
  const cap = String((app.source as Record<string, unknown>)?.capability ?? app.group_id ?? "").toLowerCase();
  const deckKind = String(app.payload?.deck_kind ?? app.payload?.deckKind ?? app.payload?.layout ?? "").toLowerCase();
  const html = String(app.payload?.html ?? "");
  return cap.includes("ppt") || deckKind.includes("ppt") || deckKind.includes("deck") || /guizang|web ppt|horizontal[- ]swipe|slide deck/i.test(html);
}

// A custom.html app is an interactive demo (not a static infographic) when it was generated
// by the interactive_demo capability, OR its HTML carries a real interactive scene/widget.
function customHtmlIsInteractiveDemo(app: CanvasApp): boolean {
  if (app.app_type !== "custom.html") return false;
  if (customHtmlIsPptDeck(app)) return false;
  const cap = String((app.source as Record<string, unknown>)?.capability ?? app.group_id ?? "").toLowerCase();
  if (cap.includes("interactive_demo")) return true;
  if (cap.includes("custom_infographic") || cap.includes("infographic")) return false;
  const html = String(app.payload?.html ?? "");
  if (/data-learnforge-widget=["'][^"']*-demo["']/i.test(html)) return true;
  return /<\s*(canvas|svg)\b/i.test(html) && /<\s*script\b/i.test(html);
}

function displaySizeForApp(app: CanvasApp) {
  if (customHtmlIsInteractiveDemo(app)) {
    return {
      width: Math.max(1060, app.size.width),
      height: Math.max(820, app.size.height)
    };
  }
  if (app.app_type === "image.explanation") {
    return {
      width: Math.max(980, app.size.width),
      height: Math.max(680, app.size.height)
    };
  }
  // Workspace-class apps (English workspace, NotebookLM) are heavy, multi-pane
  // tools — a 420×300 default leaves almost no usable area after the window chrome.
  // Force a large working area so the content (word list + detail, fission graph, etc.)
  // is actually usable instead of cramped into a tiny strip.
  if (app.app_type === "english.workspace" || app.app_type === "notebooklm.workspace" || app.app_type === "humanities.notebook") {
    return {
      width: Math.max(1080, app.size.width),
      height: Math.max(760, app.size.height)
    };
  }
  return app.size;
}

function minResizeSizeForApp(app: CanvasApp) {
  if (customHtmlIsInteractiveDemo(app)) return { width: 860, height: 620 };
  if (app.app_type === "image.explanation") return { width: 720, height: 520 };
  if (app.app_type === "exam.cram") return { width: 560, height: 460 };
  if (app.app_type === "english.workspace" || app.app_type === "notebooklm.workspace" || app.app_type === "humanities.notebook") {
    return { width: 820, height: 560 };
  }
  return { width: 260, height: 190 };
}

const FOLDER_DEFS: FolderDefinition[] = [
  { key: "notes", title: "学习笔记", subtitle: "课堂总结、阶段复盘、可复习卡片", appTypes: ["notes.session"], iconType: "notes.session" },
  { key: "quiz", title: "题库练习", subtitle: "练习题、测试题、错题巩固、考前速成", appTypes: ["quiz.practice", "exam.cram"], iconType: "quiz.practice" },
  { key: "mindmap", title: "思维导图", subtitle: "知识网络、概念结构、关系梳理", appTypes: ["mindmap.concept"], iconType: "mindmap.concept" },
  { key: "ppt", title: "PPT", subtitle: "演示文稿、课堂汇报、网页幻灯片", appTypes: ["ppt.preview"], matcher: customHtmlIsPptDeck, iconType: "ppt.preview" },
  { key: "infographic", title: "信息图", subtitle: "HTML 信息图、对比图、流程图", matcher: (app) => app.app_type === "custom.html" && !customHtmlIsPptDeck(app) && !customHtmlIsInteractiveDemo(app), iconType: "custom.html" },
  { key: "image", title: "图片解释", subtitle: "Gemini 图片、图解、视觉说明", appTypes: ["image.explanation"], iconType: "image.explanation" },
  { key: "code", title: "代码实验", subtitle: "可运行代码、实验模板、测试样例", appTypes: ["code.lab"], iconType: "code.lab" },
  {
    key: "video",
    title: "视频资源",
    subtitle: "B站课程、视频脚本、分镜素材",
    appTypes: ["video.script", "video.player"],
    matcher: (app) => {
      const resources = Array.isArray(app.payload?.resources) ? app.payload.resources as Array<Record<string, unknown>> : [];
      return app.app_type === "resource.center" && (
        String(app.payload?.resource_kind ?? "").toLowerCase() === "video" ||
        resources.some((resource) => String(resource.type ?? "").toLowerCase() === "video") ||
        /b站|哔哩|视频/.test(app.title)
      );
    },
    iconType: "video.player",
  },
  {
    key: "demo",
    title: "交互演示",
    subtitle: "数学、物理、算法等动态实验",
    matcher: (app) => {
      if (app.app_type.endsWith("_demo") || app.app_type.includes(".demo")) return true;
      // Interactive custom.html apps (Canvas/SVG + script) go to demo folder
      if (app.app_type === "custom.html") {
        const html = String(app.payload?.html ?? "");
        const hasCanvasOrSvg = /<\s*(canvas|svg)\b/i.test(html);
        const hasScript = /<\s*script\b/i.test(html);
        const hasWidget = /data-learnforge-widget/i.test(html);
        const isStaticInfographic =
          /信息图|infographic|海报|poster|对比图|流程图|学习卡片/i.test(app.title) && !hasCanvasOrSvg;
        if ((hasCanvasOrSvg && hasScript) || hasWidget) return true;
        if (isStaticInfographic) return false;
        return false;
      }
      return false;
    },
    iconType: "physics.work_energy_demo",
  },
  { key: "other", title: "其他资源", subtitle: "未归类但可打开的学习 App", iconType: "resource.folder" },
];

// Folder cards placed in right column (x≥1380) to avoid overlap with Zone A/B
const FOLDER_POSITIONS: Record<FolderKey, { x: number; y: number }> = {
  notes:      { x: 2180, y: 40  },
  quiz:       { x: 2180, y: 180 },
  mindmap:    { x: 2180, y: 320 },
  infographic:{ x: 2180, y: 460 },
  image:      { x: 2180, y: 600 },
  code:       { x: 2320, y: 40  },
  ppt:        { x: 2320, y: 180 },
  video:      { x: 2320, y: 320 },
  demo:       { x: 2320, y: 460 },
  other:      { x: 2320, y: 600 },
};

function isFolderApp(app: CanvasApp) {
  return (app.app_type as string) === "resource.folder";
}

// Keep app windows in one stacking context. A previous native layer for English
// workspaces sat below canvas-world when another window was focused, so clicks hit
// the canvas instead of the workspace. Rendering all windows in canvas-world keeps
// z-order, focus, and pointer hit-testing consistent.
const NATIVE_LAYER_APP_TYPES = new Set<string>();
function isNativeLayerAppType(appType: string): boolean {
  return NATIVE_LAYER_APP_TYPES.has(appType);
}

// Pinned monitoring apps are docked into the top "监控总览" frame at fixed slots.
const PINNED_ORDER = ["app-profile", "app-dashboard", "app-resource"];
const PINNED_TYPE_ORDER = ["profile.dashboard", "dashboard.learning", "resource.center"];
const PINNED_SLOTS = [
  { x: 40,  y: 70, width: 400, height: 300 },
  { x: 470, y: 70, width: 420, height: 300 },
  { x: 920, y: 70, width: 380, height: 300 },
];
function pinnedSlot(app: CanvasApp) {
  let idx = PINNED_ORDER.indexOf(app.app_id);
  if (idx === -1) idx = PINNED_TYPE_ORDER.indexOf(app.app_type as string);
  return PINNED_SLOTS[idx] ?? PINNED_SLOTS[0];
}

function folderForApp(app: CanvasApp): FolderDefinition | null {
  if (isPinnedApp(app)) return null;
  if (
    app.app_type === "image.explanation" &&
    (
      String(app.payload?.provider_alias ?? app.payload?.provider ?? "").toLowerCase().includes("banana") ||
      String(app.payload?.infographic_render_mode ?? "").toLowerCase() === "image" ||
      /信息图|海报/.test(app.title)
    )
  ) {
    return FOLDER_DEFS.find((folder) => folder.key === "infographic") ?? null;
  }
  return FOLDER_DEFS.find((folder) => folder.appTypes?.includes(app.app_type) || folder.matcher?.(app)) ?? FOLDER_DEFS.find((folder) => folder.key === "other") ?? null;
}

function byUpdatedDesc(a: CanvasApp, b: CanvasApp) {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

export function SpatialCanvas({ apps, dashboard, viewport, setViewport, setApps, openWindowIds, focusedId, fullscreenId, zOrder, openWindow, closeWindow, focusWindow, toggleFullscreen, deleteApp, onAppEvent, onDashboardUpdate, onResourceDrop, sessionContext }: Props) {
  const [drag, setDrag] = useState<DragState | null>(null);
  const [activeFolderApp, setActiveFolderApp] = useState<CanvasApp | null>(null);
  const [resourceDragOver, setResourceDragOver] = useState(false);
  const [pageFullscreenId, setPageFullscreenId] = useState<string | null>(null);
  // While true (during wheel-zoom), the world transform follows input instantly with no spring
  // transition, so panning/zooming feels 1:1 instead of lagging 0.9s behind the cursor.
  const [directManip, setDirectManip] = useState(false);
  const directManipTimer = useRef<number | undefined>(undefined);
  const autoArrangeTimer = useRef<number | undefined>(undefined);
  const windowInteractionRef = useRef<WindowInteraction | null>(null);
  const appsRef = useRef(apps);
  appsRef.current = apps;
  const flagDirectManip = () => {
    setDirectManip(true);
    window.clearTimeout(directManipTimer.current);
    directManipTimer.current = window.setTimeout(() => setDirectManip(false), 220);
  };
  const shellRef = useRef<HTMLDivElement | null>(null);
  // #10: ref mirror of the viewport so the wheel listener can read the latest value
  // without being rebound on every pan/zoom (which thrashed the listener registration).
  const viewportRef = useRef(viewport);
  viewportRef.current = viewport;
  const openedSet = useMemo(() => new Set(openWindowIds), [openWindowIds]);

  // #16: clear any pending timers on unmount so they don't fire setState on a dead node.
  useEffect(() => {
    return () => {
      window.clearTimeout(directManipTimer.current);
      window.clearTimeout(autoArrangeTimer.current);
      if (windowInteractionRef.current?.raf) window.cancelAnimationFrame(windowInteractionRef.current.raf);
    };
  }, []);
  // z-index from zOrder (most-recently-focused on top); fall back to insertion order
  const zIndexFor = (appId: string) => {
    const idx = zOrder.indexOf(appId);
    return idx === -1 ? 30 : 31 + idx;
  };
  const folderApps = useMemo(() => {
    const folders = new Map<FolderKey, CanvasApp[]>();
    apps.forEach((app) => {
      const folder = folderForApp(app);
      if (!folder) return;
      const list = folders.get(folder.key) ?? [];
      list.push(app);
      folders.set(folder.key, list);
    });
    return FOLDER_DEFS.flatMap((folder, index) => {
      const items = (folders.get(folder.key) ?? []).sort(byUpdatedDesc);
      if (!items.length) return [];
      const pos = FOLDER_POSITIONS[folder.key] ?? { x: 500 + (index % 3) * 370, y: 40 + Math.floor(index / 3) * 230 };
      const payload: FolderPayload = {
        folderKey: folder.key,
        subtitle: folder.subtitle,
        count: items.length,
        updatedAt: items[0]?.updated_at,
        items,
        recentTitles: items.slice(0, 3).map((item) => item.title),
      };
      return [{
        app_id: `folder-${folder.key}`,
        title: `${folder.title}文件夹`,
        // #7: use protocol-valid literals. Previously these were "native" / "agent" cast
        // through `as CanvasApp[...]`, which lied to the type checker — both values are
        // outside their declared unions (RenderMode / the source object shape).
        app_type: "resource.folder",
        status: "ready",
        state: "window",
        position: pos,
        size: { width: 120, height: 110 },
        z_index: 200 + index,  // above all app windows
        group_id: "resource-folders",
        payload,
        source_refs: [],
        render_mode: "native_react",
        source: {},
        actions: [{ label: "打开列表", action: "folder.open" }],
        created_at: items[items.length - 1]?.created_at ?? new Date().toISOString(),
        updated_at: items[0]?.updated_at ?? new Date().toISOString(),
      } as CanvasApp];
    });
  }, [apps]);
  const visibleApps = useMemo(() => {
    // Single source of truth: pinned apps always show; others show only if opened.
    // Fullscreen app is rendered separately as an overlay, so exclude it here.
    // Folder cards are intentionally NOT placed on the canvas surface (they cluttered it);
    // they remain reachable from the bottom dock, which still lists every folder.
    return apps.filter((app) => {
      if (app.app_id === fullscreenId || app.app_id === pageFullscreenId) return false;
      return isPinnedApp(app) || openedSet.has(app.app_id);
    });
  }, [apps, openedSet, fullscreenId, pageFullscreenId]);
  const fullscreenApp = useMemo(() => apps.find((app) => app.app_id === (pageFullscreenId ?? fullscreenId)), [apps, fullscreenId, pageFullscreenId]);
  const fullscreenMode = pageFullscreenId ? "page" : fullscreenId ? "canvas" : null;
  const focusedApp = visibleApps.find((app) => !isFolderApp(app) && app.app_id === focusedId);

  const clampScale = (scale: number) => Math.min(1.8, Math.max(0.42, scale));
  const viewportPixelSize = () => {
    const rect = shellRef.current?.getBoundingClientRect();
    return rect ? { width: rect.width, height: rect.height } : null;
  };
  const clampWindowPosition = (position: { x: number; y: number }, size: { width: number; height: number }) => {
    const pixels = viewportPixelSize();
    if (!pixels) return position;
    return clampWindowPositionToViewport(position, size, viewportRef.current, pixels);
  };
  const bringWindowIntoView = (appId: string) => {
    if (windowInteractionRef.current) return;
    const app = appsRef.current.find((item) => item.app_id === appId);
    if (!app || isPinnedApp(app) || isFolderApp(app)) return;
    const size = displaySizeForApp(app);
    const nextPosition = clampWindowPosition(app.position, size);
    if (samePoint(app.position, nextPosition)) return;
    const nextApp = { ...app, position: nextPosition, updated_at: new Date().toISOString() };
    setApps(appsRef.current.map((item) => (item.app_id === app.app_id ? nextApp : item)));
    void patchApp(app.app_id, { position: nextPosition, size: app.size, group_id: app.group_id }, sessionContext);
  };

  useEffect(() => {
    if (!focusedId) return;
    const raf = window.requestAnimationFrame(() => bringWindowIntoView(focusedId));
    return () => window.cancelAnimationFrame(raf);
  // Keep this tied to focus changes only; panning/zooming the canvas should not
  // constantly move the user's windows back into the viewport.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedId]);

  const zoomAt = (clientX: number, clientY: number, nextScale: number) => {
    const rect = shellRef.current?.getBoundingClientRect();
    if (!rect) return;
    const scale = clampScale(nextScale);
    const screenX = clientX - rect.left;
    const screenY = clientY - rect.top;
    const worldX = (screenX - viewport.x) / viewport.scale;
    const worldY = (screenY - viewport.y) / viewport.scale;
    setViewport({
      scale,
      x: screenX - worldX * scale,
      y: screenY - worldY * scale
    });
  };

  const zoomAtCenter = (factor: number) => {
    const rect = shellRef.current?.getBoundingClientRect();
    if (!rect) return setViewport({ ...viewport, scale: clampScale(viewport.scale * factor) });
    zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, viewport.scale * factor);
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!drag) return;
    event.preventDefault();
    if (drag.kind === "canvas") {
      setViewport({ ...drag.viewport, x: drag.viewport.x + event.clientX - drag.startX, y: drag.viewport.y + event.clientY - drag.startY });
    }
  };

  const onPointerUp = () => {
    setDrag(null);
  };

  const frameElementFor = (appId: string) => shellRef.current?.querySelector<HTMLElement>(`[data-window-frame="${appId}"]`) ?? null;

  const applyWindowInteractionPreview = (interaction: WindowInteraction) => {
    if (interaction.raf) return;
    interaction.raf = window.requestAnimationFrame(() => {
      interaction.raf = undefined;
      if (windowInteractionRef.current !== interaction) return;
      const frame = frameElementFor(interaction.appId);
      if (!frame) return;
      if (interaction.kind === "app") {
        frame.style.transform = `translate3d(${interaction.nextX - interaction.baseX}px, ${interaction.nextY - interaction.baseY}px, 0)`;
      } else {
        frame.style.width = `${interaction.nextWidth}px`;
        frame.style.height = `${interaction.nextHeight}px`;
      }
    });
  };

  const finishWindowInteraction = async () => {
    const interaction = windowInteractionRef.current;
    if (!interaction) return;
    windowInteractionRef.current = null;
    if (interaction.raf) window.cancelAnimationFrame(interaction.raf);
    window.removeEventListener("pointermove", onWindowInteractionMove);
    window.removeEventListener("pointerup", finishWindowInteraction);
    window.removeEventListener("pointercancel", finishWindowInteraction);
    document.removeEventListener("pointerup", finishWindowInteraction, true);
    document.removeEventListener("pointercancel", finishWindowInteraction, true);
    const app = appsRef.current.find((item) => item.app_id === interaction.appId);
    const frame = frameElementFor(interaction.appId);
    const rawPosition = interaction.kind === "app"
      ? { x: interaction.nextX, y: interaction.nextY }
      : app?.position ?? { x: interaction.baseX, y: interaction.baseY };
    const nextSize = interaction.kind === "resize"
      ? { width: interaction.nextWidth, height: interaction.nextHeight }
      : app?.size ?? { width: interaction.baseWidth, height: interaction.baseHeight };
    const clampSize = interaction.kind === "resize"
      ? nextSize
      : { width: interaction.baseWidth, height: interaction.baseHeight };
    const nextPosition = clampWindowPosition(rawPosition, clampSize);
    if (frame) {
      frame.style.left = `${nextPosition.x}px`;
      frame.style.top = `${nextPosition.y}px`;
      frame.style.width = `${nextSize.width}px`;
      frame.style.height = `${nextSize.height}px`;
      frame.style.transform = "";
    }
    setDrag(null);
    if (!app) return;
    const nextApp = { ...app, position: nextPosition, size: nextSize, updated_at: new Date().toISOString() };
    setApps(appsRef.current.map((item) => (item.app_id === app.app_id ? nextApp : item)));
    void patchApp(app.app_id, { position: nextPosition, size: nextSize, group_id: app.group_id }, sessionContext);
    void onAppEvent(app.app_id, interaction.kind === "resize" ? "layout.resize" : "layout.drag", { position: nextPosition, size: nextSize });
  };

  const onWindowInteractionMove = (event: globalThis.PointerEvent) => {
    const interaction = windowInteractionRef.current;
    if (!interaction || event.pointerId !== interaction.pointerId) return;
    event.preventDefault();
    const dx = (event.clientX - interaction.startX) / interaction.scale;
    const dy = (event.clientY - interaction.startY) / interaction.scale;
    if (interaction.kind === "app") {
      const nextPosition = clampWindowPosition(
        { x: interaction.baseX + dx, y: interaction.baseY + dy },
        { width: interaction.baseWidth, height: interaction.baseHeight },
      );
      interaction.nextX = nextPosition.x;
      interaction.nextY = nextPosition.y;
    } else {
      const app = appsRef.current.find((item) => item.app_id === interaction.appId);
      const min = app ? minResizeSizeForApp(app) : { width: 260, height: 190 };
      interaction.nextWidth = Math.max(min.width, interaction.baseWidth + dx);
      interaction.nextHeight = Math.max(min.height, interaction.baseHeight + dy);
    }
    applyWindowInteractionPreview(interaction);
  };

  const startWindowInteraction = (event: ReactPointerEvent<HTMLElement>, app: CanvasApp, kind: "app" | "resize") => {
    if (isPinnedApp(app)) return;
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const size = displaySizeForApp(app);
    const interaction: WindowInteraction = {
      kind,
      appId: app.app_id,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scale: viewport.scale,
      baseX: app.position.x,
      baseY: app.position.y,
      baseWidth: size.width,
      baseHeight: size.height,
      nextX: app.position.x,
      nextY: app.position.y,
      nextWidth: size.width,
      nextHeight: size.height,
    };
    windowInteractionRef.current = interaction;
    setDrag(kind === "app"
      ? { kind: "app", appId: app.app_id, startX: event.clientX, startY: event.clientY, x: app.position.x, y: app.position.y }
      : { kind: "resize", appId: app.app_id, startX: event.clientX, startY: event.clientY, width: size.width, height: size.height }
    );
    focusWindow(app.app_id);
    window.addEventListener("pointermove", onWindowInteractionMove, { passive: false });
    window.addEventListener("pointerup", finishWindowInteraction);
    window.addEventListener("pointercancel", finishWindowInteraction);
    document.addEventListener("pointerup", finishWindowInteraction, true);
    document.addEventListener("pointercancel", finishWindowInteraction, true);
  };

  useEffect(() => {
    if (!drag) return;
    const clearStaleDrag = () => {
      if (windowInteractionRef.current) {
        void finishWindowInteraction();
      } else {
        setDrag(null);
      }
    };
    document.addEventListener("pointerup", clearStaleDrag, true);
    document.addEventListener("pointercancel", clearStaleDrag, true);
    window.addEventListener("blur", clearStaleDrag);
    return () => {
      document.removeEventListener("pointerup", clearStaleDrag, true);
      document.removeEventListener("pointercancel", clearStaleDrag, true);
      window.removeEventListener("blur", clearStaleDrag);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drag]);

  const onViewportPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    if (target.closest(".canvas-app, .folder-card, .app-dock")) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDrag({ kind: "canvas", startX: event.clientX, startY: event.clientY, viewport });
  };

  // Register wheel listener as non-passive so we can call preventDefault for canvas zoom.
  // We skip zoom when the pointer is over an app card's scrollable body.
  // #10: bind once; read viewport from a ref so panning/zooming doesn't re-register the
  // listener (which previously happened on every viewport change).
  useEffect(() => {
    const el = shellRef.current;
    if (!el) return;
    const handleWheel = (event: globalThis.WheelEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest(".appwin-body, .native-app-body")) {
        // Inside a scrollable app card — let the browser scroll it naturally
        return;
      }
      event.preventDefault();
      flagDirectManip();
      const factor = event.deltaY < 0 ? 1.1 : 0.9;
      const current = viewportRef.current;
      const rect = el.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;
      const worldX = (screenX - current.x) / current.scale;
      const worldY = (screenY - current.y) / current.scale;
      const scale = clampScale(current.scale * factor);
      setViewport({
        scale,
        x: screenX - worldX * scale,
        y: screenY - worldY * scale,
      });
    };
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const el = shellRef.current;
    if (!el) return;
    el.scrollLeft = 0;
    el.scrollTop = 0;
  }, [activeFolderApp, openWindowIds, fullscreenId]);

  useEffect(() => {
    if (!fullscreenId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (pageFullscreenId) return;
      event.preventDefault();
      toggleFullscreen(fullscreenId);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [fullscreenId, pageFullscreenId, toggleFullscreen]);

  useEffect(() => {
    if (!pageFullscreenId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setPageFullscreenId(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pageFullscreenId]);

  const autoArrange = () => {
    // Zone B (top row): 3 monitoring apps — 学习画像 | 学习仪表盘 | 资源中心
    // Content (everything else): free grid below, no sub-zone distinction
    const LAYOUT: Record<string, { x: number; y: number; w: number; h: number; z: number }> = {
      // Zone B — monitoring, top row
      "app-profile":     { x: 40,   y: 40,  w: 380, h: 310, z: 13 },
      "app-dashboard":   { x: 450,  y: 40,  w: 420, h: 310, z: 13 },
      "app-resource":    { x: 900,  y: 40,  w: 380, h: 310, z: 13 },
      // Content — all other named apps, 4-col grid from y=400
      "app-path":        { x: 40,   y: 400, w: 400, h: 300, z: 10 },
      "app-knowledge":   { x: 470,  y: 400, w: 380, h: 300, z: 10 },
      "app-energy":      { x: 880,  y: 400, w: 420, h: 300, z: 10 },
      "app-gradient":    { x: 1330, y: 400, w: 420, h: 300, z: 10 },
      "app-quiz":        { x: 40,   y: 730, w: 390, h: 290, z: 10 },
      "app-notes":       { x: 460,  y: 730, w: 390, h: 290, z: 10 },
      "app-mindmap":     { x: 880,  y: 730, w: 380, h: 290, z: 10 },
      "app-ppt":         { x: 1290, y: 730, w: 360, h: 290, z: 9  },
      "app-code":        { x: 40,   y: 1050,w: 390, h: 280, z: 9  },
      "app-image":       { x: 460,  y: 1050,w: 360, h: 280, z: 9  },
      "app-video":       { x: 850,  y: 1050,w: 360, h: 280, z: 9  },
      "app-custom-html": { x: 1240, y: 1050,w: 980, h: 720, z: 9  },
    };

    let fallbackIndex = 0;
    const arranged = apps.map((app) => {
      const pos = LAYOUT[app.app_id];
      if (pos) {
        return {
          ...app,
          position: { x: pos.x, y: pos.y },
          size: { width: pos.w, height: pos.h },
          z_index: pos.z,
          group_id: pos.y < 740 && pos.x < 1400 ? "frame-core-loop" : app.group_id,
        };
      }
      // Unknown apps: stack in bottom-right overflow area
      const col = fallbackIndex % 3;
      const row = Math.floor(fallbackIndex / 3);
      fallbackIndex++;
      return { ...app, position: { x: 1880 + col * 420, y: 400 + row * 340 }, z_index: 9 };
    });

    setApps(arranged);
    // #11: persist all positions in parallel; a single failure shouldn't abort the rest.
    void Promise.allSettled(
      arranged.map((app) =>
        patchApp(app.app_id, { position: app.position, size: app.size, z_index: app.z_index, group_id: app.group_id }, sessionContext)
      )
    ).then((results) => {
      const rejected = results.filter((r) => r.status === "rejected");
      if (rejected.length) console.warn("[LearnForge] autoArrange: 部分位置保存失败", rejected.length);
    });

    // After layout, zoom to show Zone A + B together.
    // #16: track this timer so it's cleared on unmount (the unmount effect clears autoArrangeTimer).
    window.clearTimeout(autoArrangeTimer.current);
    autoArrangeTimer.current = window.setTimeout(() => {
      setViewport({ x: -10, y: -8, scale: 0.62 });
    }, 80);
  };

  const saveLayout = () => {
    saveJson("learnforge.canvas.layout", { apps, viewport });
    onAppEvent("app-path", "layout.save", { viewport, app_count: apps.length });
  };

  const resetView = () => setViewport({ x: 0, y: 0, scale: 1 });

  const worldPositionFromClient = (clientX: number, clientY: number) => {
    const rect = shellRef.current?.getBoundingClientRect();
    if (!rect) return { x: 260, y: 220 };
    return {
      x: Math.round((clientX - rect.left - viewport.x) / viewport.scale - 260),
      y: Math.round((clientY - rect.top - viewport.y) / viewport.scale - 180),
    };
  };

  const dropResource = async (event: DragEvent<HTMLDivElement>) => {
    const raw = event.dataTransfer.getData("application/x-learnforge-resource");
    if (!raw || !onResourceDrop) return;
    event.preventDefault();
    event.stopPropagation();
    setResourceDragOver(false);
    try {
      const resource = JSON.parse(raw) as LearningResource;
      await onResourceDrop(resource, worldPositionFromClient(event.clientX, event.clientY));
    } catch {
      setResourceDragOver(false);
    }
  };

  return (
    <section className="canvas-shell" data-testid="spatial-canvas">
      <div
        ref={shellRef}
        className={`canvas-viewport ${drag?.kind === "canvas" ? "panning" : ""} ${drag?.kind === "app" ? "window-dragging" : ""} ${drag?.kind === "resize" ? "window-resizing" : ""} ${resourceDragOver ? "resource-drop-active" : ""}`}
        onScroll={(event) => {
          event.currentTarget.scrollLeft = 0;
          event.currentTarget.scrollTop = 0;
        }}
        onPointerDown={onViewportPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onDragOver={(event) => {
          if (event.dataTransfer.types.includes("application/x-learnforge-resource")) {
            event.preventDefault();
            event.dataTransfer.dropEffect = "copy";
            setResourceDragOver(true);
          }
        }}
        onDragLeave={(event) => {
          if (event.currentTarget === event.target) setResourceDragOver(false);
        }}
        onDrop={dropResource}
      >
        <div className="canvas-drop-hint" aria-hidden="true">释放后加入左侧学习面板</div>
        <div
          className="canvas-world"
          style={{
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
            transition: drag?.kind === "canvas" || directManip ? "none" : undefined,
          }}
        >
          {/* Zone B — 3 monitoring apps, top row */}
          <div className="canvas-frame-b" style={{ position: "absolute", left: 25, top: 25, width: 1295, height: 360 }}>
            <span className="canvas-frame-label">监控总览</span>
          </div>
          {focusedApp && !(drag?.kind === "app" || drag?.kind === "resize") ? (
            <div
              className="focus-halo on"
              style={{
                left: focusedApp.position.x - 8,
                top: focusedApp.position.y - 8,
                width: focusedApp.size.width + 16,
                height: focusedApp.size.height + 16
              }}
            />
          ) : null}
          <AnimatePresence initial={false}>
          {visibleApps.filter((app) => !isNativeLayerAppType(app.app_type)).map((app) => isFolderApp(app) ? (
            /* Compact folder icon card — click opens FolderModal */
            <motion.div
              key={app.app_id}
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.7, opacity: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 28 }}
              style={{ position: "absolute", left: app.position.x, top: app.position.y, zIndex: app.z_index }}
            >
              <FolderCard app={app} onOpen={() => setActiveFolderApp(app)} />
            </motion.div>
          ) : (() => {
            const pinned = isPinnedApp(app);
            const slot = pinned ? pinnedSlot(app) : null;
            const pos = slot ? { x: slot.x, y: slot.y } : app.position;
            const size = slot ? { width: slot.width, height: slot.height } : displaySizeForApp(app);
            const isActiveFrame = (drag?.kind === "app" || drag?.kind === "resize") && drag.appId === app.app_id;
            return (
            <div
              key={app.app_id}
              data-window-frame={app.app_id}
              className={isActiveFrame ? "window-frame is-direct-manipulating" : "window-frame"}
              style={{ position: "absolute", left: pos.x, top: pos.y, width: size.width, height: size.height, zIndex: pinned ? 12 : zIndexFor(app.app_id) }}
            >
            <AppWindow
              app={app}
              dimmed={!pinned && !!(focusedApp && focusedApp.app_id !== app.app_id)}
              isFullscreen={false}
              fixed={pinned}
              dashboard={dashboard}
              onFocus={() => focusWindow(app.app_id)}
              onDragStart={(event) => startWindowInteraction(event, app, "app")}
              onResizeStart={(event) => startWindowInteraction(event, app, "resize")}
              onToggleFullscreen={() => toggleFullscreen(app.app_id)}
              onTogglePageFullscreen={() => setPageFullscreenId((current) => (current === app.app_id ? null : app.app_id))}
              onClose={!pinned ? () => closeWindow(app.app_id) : undefined}
              onDelete={!pinned ? () => deleteApp(app.app_id) : undefined}
              onAppEvent={onAppEvent}
              onFocusApp={openWindow}
              onDashboardUpdate={onDashboardUpdate}
              sessionContext={sessionContext}
            />
            </div>
            );
          })())}
          </AnimatePresence>
        </div>

        {/* Native App Layer — transform-sensitive workspace apps live here,
            outside canvas-world, so their canvas coordinate systems stay native. */}
        {(() => {
          const nativeAppIds = new Set(visibleApps.filter((a) => isNativeLayerAppType(a.app_type)).map((a) => a.app_id));
          const topMost = zOrder.length ? zOrder[zOrder.length - 1] : focusedId;
          const nativeOnTop = !!topMost && nativeAppIds.has(topMost);
          return (
        <div
          className="native-app-layer"
          style={{
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
            transition: drag?.kind === "canvas" || directManip ? "none" : undefined,
            zIndex: nativeOnTop ? 60 : 5,
          }}
        >
          <AnimatePresence initial={false}>
            {visibleApps.filter((app) => isNativeLayerAppType(app.app_type)).map((app) => {
              const pos = app.position;
              const size = displaySizeForApp(app);
              return (
                <div
                  key={app.app_id}
                  data-window-frame={app.app_id}
                  className="window-frame native-window-frame"
                  style={{ position: "absolute", left: pos.x, top: pos.y, width: size.width, height: size.height, zIndex: zIndexFor(app.app_id) }}
                >
                  <AppWindow
                    app={app}
                    dimmed={!!(focusedApp && focusedApp.app_id !== app.app_id)}
                    isFullscreen={false}
                    fixed={false}
                    dashboard={dashboard}
                    onFocus={() => focusWindow(app.app_id)}
                    onDragStart={(event) => startWindowInteraction(event, app, "app")}
                    onResizeStart={(event) => startWindowInteraction(event, app, "resize")}
                    onToggleFullscreen={() => toggleFullscreen(app.app_id)}
                    onTogglePageFullscreen={() => setPageFullscreenId((current) => (current === app.app_id ? null : app.app_id))}
                    onClose={() => closeWindow(app.app_id)}
                    onDelete={() => deleteApp(app.app_id)}
                    onAppEvent={onAppEvent}
                    onFocusApp={openWindow}
                    onDashboardUpdate={onDashboardUpdate}
                    sessionContext={sessionContext}
                  />
                </div>
              );
            })}
          </AnimatePresence>
        </div>
        );
        })()}


        <div className="canvas-minimap" data-testid="minimap" onPointerDown={(event) => event.stopPropagation()}>
          <button type="button" onClick={resetView} title="在小地图中复位视角" aria-label="在小地图中复位视角">
            <span className="minimap-viewport" />
          </button>
        </div>
      </div>
      <footer className="app-dock dock glass glass-hi" data-testid="app-dock">
        {(() => {
          // 3-zone dock: pinned | generated content (system modules + real-time) | folders
          const pinnedApps = apps.filter(isPinnedApp).slice(0, 3);
          // 系统模块固定显示（英语工作区、NotebookLM），即使 apps 中不存在。
          // humanities.notebook 仅作为旧类型 alias，不再单独出现在 Dock。
          const SYSTEM_MODULE_DEFS: Array<{ app_id: string; app_type: string; title: string; aliases?: string[] }> = [
            { app_id: "app-english", app_type: "english.workspace", title: "英语工作区" },
            { app_id: "app-notebooklm", app_type: "notebooklm.workspace", title: "NotebookLM", aliases: ["humanities.notebook"] },
          ];
          const makeSystemModuleApp = (def: (typeof SYSTEM_MODULE_DEFS)[0]): CanvasApp => ({
            app_id: def.app_id,
            title: def.title,
            app_type: def.app_type as CanvasApp["app_type"],
            status: "ready",
            state: "window",
            position: { x: 0, y: 0 },
            size: { width: 800, height: 600 },
            z_index: 10,
            group_id: "system-modules",
            payload: {},
            source_refs: [],
            render_mode: "native_react",
            source: {},
            actions: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
          const systemModules = SYSTEM_MODULE_DEFS.map(def => {
            const existing = apps.find(a => a.app_type === def.app_type || def.aliases?.includes(a.app_type as string));
            if (!existing) return makeSystemModuleApp(def);
            return {
              ...existing,
              title: def.title,
            };
          });
          // 实时资源区：不再显示在 Dock 上，只归类到文件夹中
          // const realTimeApps = apps
          //   .filter(a => isRealTimeResource(a) && !isPinnedApp(a) && !isSystemModule(a))
          //   .sort(byUpdatedDesc)
          //   .slice(0, 3);
          // 合并系统模块和实时资源为一个生成模块区域
          // const generatedApps = [...systemModules, ...realTimeApps];
          // 中区只保留系统模块（英语工作区、文科笔记本），实时资源归类到文件夹
          const generatedApps = [...systemModules];
          const contentApps = [...folderApps];
          const renderDockBtn = (app: CanvasApp) => {
            const isOpen = openedSet.has(app.app_id) || isPinnedApp(app);
            const iconSrc = isFolderApp(app) ? folderIconSrc(app) : undefined;
            const isVirtualSystemModule = app.app_id === "app-english" || app.app_id === "app-notebooklm";
            return (
            <button
              key={app.app_id}
              onClick={() => {
                if (isFolderApp(app)) {
                  setActiveFolderApp(activeFolderApp?.app_id === app.app_id ? null : app);
                } else if (isPinnedApp(app)) {
                  focusWindow(app.app_id);
                } else if (isVirtualSystemModule) {
                  onAppEvent(app.app_id, "system_module.create", { app_type: app.app_type });
                } else {
                  openWindow(app.app_id);
                  window.requestAnimationFrame(() => bringWindowIntoView(app.app_id));
                }
              }}
              title={app.title}
              className="dock-app"
              style={{ background: iconSrc || APP_ICON_FILES[app.app_type] ? undefined : appAccent(app) }}
            >
              <AppIcon appType={app.app_type} size={36} srcOverride={iconSrc} />
              {isFolderApp(app) ? <span className="dock-badge">{(app.payload as FolderPayload).count}</span> : null}
              {!isFolderApp(app) && isOpen ? <span className="dock-dot" /> : null}
              <span className="dock-tip">{app.title}</span>
            </button>
            );
          };
          return (
            <>
              {/* 左区：系统应用（pinned） */}
              {pinnedApps.map(renderDockBtn)}
              
              {/* 中区：生成模块（系统自带模块 + 实时生成资源） */}
              {generatedApps.length > 0 && pinnedApps.length > 0 && (
                <div className="dock-sep" aria-hidden="true" />
              )}
              {generatedApps.map(renderDockBtn)}
              
              {/* 右区：Folder Apps */}
              {contentApps.length > 0 && (pinnedApps.length > 0 || generatedApps.length > 0) && (
                <div className="dock-sep" aria-hidden="true" />
              )}
              {contentApps.map(renderDockBtn)}
            </>
          );
        })()}
      </footer>
      {/* Folder modal — macOS spring popup */}
      <AnimatePresence>
        {activeFolderApp && (
          <FolderModal
            app={activeFolderApp}
            onClose={() => setActiveFolderApp(null)}
            onOpenApp={(appId) => { openWindow(appId); setActiveFolderApp(null); }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
      {fullscreenApp ? (() => {
        const fullscreenExitLabel = fullscreenApp.app_type === "custom.html"
          ? "退出演示"
          : fullscreenMode === "page" ? "退出页面全屏" : "退出画布全屏";
        return (
        <motion.div
          key={`fs-${fullscreenApp.app_id}`}
          className={`fullscreen-app-layer ${fullscreenApp.app_type === "custom.html" ? "fullscreen-app-layer-custom" : ""}`}
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.25, ease: [0.22, 1.2, 0.36, 1] }}
          data-fullscreen-mode={fullscreenMode ?? undefined}
          style={fullscreenMode === "page"
            ? { position: "fixed", inset: 0, zIndex: 1200 }
            : { position: "fixed", top: "var(--topbar-h)", left: 0, bottom: 0, width: "var(--canvas-pane, 68%)", zIndex: 900 }}
        >
        <AppWindow
          key={fullscreenApp.app_id}
          app={fullscreenApp}
          dimmed={false}
          isFullscreen={true}
          dashboard={dashboard}
          onFocus={() => focusWindow(fullscreenApp.app_id)}
          onDragStart={() => undefined}
          onResizeStart={() => undefined}
          onToggleFullscreen={() => {
            if (fullscreenMode === "canvas") toggleFullscreen(fullscreenApp.app_id);
            else {
              setPageFullscreenId(null);
              toggleFullscreen(fullscreenApp.app_id);
            }
          }}
          onTogglePageFullscreen={() => {
            if (fullscreenMode === "page") setPageFullscreenId(null);
            else {
              if (fullscreenId === fullscreenApp.app_id) toggleFullscreen(fullscreenApp.app_id);
              setPageFullscreenId(fullscreenApp.app_id);
            }
          }}
          onClose={!isPinnedApp(fullscreenApp) ? () => closeWindow(fullscreenApp.app_id) : undefined}
          onAppEvent={onAppEvent}
          onFocusApp={openWindow}
          onDashboardUpdate={onDashboardUpdate}
          sessionContext={sessionContext}
        />
        <button
          type="button"
          className="fullscreen-exit-button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            if (fullscreenMode === "page") setPageFullscreenId(null);
            else toggleFullscreen(fullscreenApp.app_id);
          }}
          title={fullscreenExitLabel}
          aria-label={fullscreenExitLabel}
        >
          <Shrink size={16} />
          <span>{fullscreenExitLabel}</span>
        </button>
        </motion.div>
        );
      })() : null}
      </AnimatePresence>

      {/* Floating zoom controls — bottom-right corner */}
      <div className="canvas-zoom-controls">
        <button onClick={() => zoomAtCenter(1.12)} title="放大"><Plus size={16} /></button>
        <button onClick={() => zoomAtCenter(0.88)} title="缩小"><Minus size={16} /></button>
        <button onClick={resetView} title="复位"><LocateFixed size={16} /></button>
      </div>
    </section>
  );
}

// ---- AppWindow sub-component ----

type AppWindowProps = {
  app: CanvasApp;
  dimmed: boolean;
  isFullscreen: boolean;
  fixed?: boolean;
  dashboard?: DashboardSnapshot;
  onFocus: () => void;
  onDragStart: (event: ReactPointerEvent<HTMLElement>) => void;
  onResizeStart: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  onToggleFullscreen: () => void;
  onTogglePageFullscreen: () => void;
  onClose?: () => void;
  onDelete?: () => void;
  onAppEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void;
  onFocusApp: (appId: string) => void;
  onDashboardUpdate?: (dashboard: DashboardSnapshot) => void;
  sessionContext: SessionContext;
};

function AppWindow({ app, dimmed, isFullscreen, fixed, dashboard, onFocus, onDragStart, onResizeStart, onToggleFullscreen, onTogglePageFullscreen, onClose, onDelete, onAppEvent, onFocusApp, onDashboardUpdate, sessionContext }: AppWindowProps) {
  // Positioning is handled by the motion.div wrapper in canvas; fullscreen uses inset:0
  const isCustomHtml = app.app_type === "custom.html";
  // Workspace-class apps (English workspace, NotebookLM) are heavy multi-pane
  // tools, not lightweight cards. Treat them as "immersive": drop the redundant footer
  // ("已保存到学习画布" / "问老师") and the duplicate type strip, and use a compact
  // titlebar so the app content — not the chrome — fills the window.
  const isWorkspaceApp = app.app_type === "english.workspace" || app.app_type === "notebooklm.workspace" || app.app_type === "humanities.notebook";
  const appActions = Array.isArray(app.actions) ? app.actions : [];
  const posStyle = isFullscreen
    ? { position: "absolute" as const, inset: 0, width: "auto", height: "auto", zIndex: 500, borderRadius: 0 }
    : { width: "100%", height: "100%" };

  return (
    <article
      className={`canvas-app appwin ${isFullscreen ? "fullscreen" : app.state} ${dimmed ? "dimmed" : ""} ${isWorkspaceApp ? "is-workspace" : ""}`}
      data-app-id={app.app_id}
      data-app-type={app.app_type}
      data-testid={`canvas-app-${app.app_id}`}
      style={posStyle}
      onPointerDown={onFocus}
    >
      {isWorkspaceApp ? (
        // Workspace apps (English workspace, NotebookLM) render their own
        // full-bleed UI. They keep a slim, visible top bar — a macOS-style traffic
        // area that doubles as the drag handle — plus the standard window controls
        // (canvas fullscreen / page fullscreen / close) on the right. This bar is
        // intentionally short so it doesn't steal vertical space from the workspace.
        <div
          className="workspace-topbar"
          onPointerDown={(event) => {
            if (isFullscreen) return;
            // Don't start a window drag when the pointer lands on a control button.
            if ((event.target as HTMLElement).closest("button")) return;
            event.stopPropagation();
            onDragStart(event);
            onFocus();
          }}
        >
          <span className="workspace-topbar-grip" aria-hidden="true" />
          <span className="workspace-topbar-title">{app.title}</span>
          <div className="workspace-topbar-ctrls">
            <button
              onPointerDown={(event) => event.stopPropagation()}
              onClick={onToggleFullscreen}
              title={isFullscreen ? "退出画布全屏" : "画布内全屏"}
              aria-label={isFullscreen ? "退出画布全屏" : "画布内全屏"}
            >
              {isFullscreen ? <Shrink size={13} /> : <Maximize2 size={13} />}
            </button>
            <button
              onPointerDown={(event) => event.stopPropagation()}
              onClick={onTogglePageFullscreen}
              title="页面全屏"
              aria-label="页面全屏"
            >
              <Fullscreen size={13} />
            </button>
            {onClose && (
              <button
                onPointerDown={(event) => event.stopPropagation()}
                onClick={onClose}
                title="关闭窗口"
                aria-label="关闭窗口"
                className="win-btn-close"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </div>
      ) : (
      <header
        className="app-titlebar appwin-bar"
        onPointerDown={(event) => {
          if (isFullscreen) return;
          event.stopPropagation();
          onDragStart(event);
          onFocus();
        }}
        style={isFullscreen ? { cursor: "default" } : undefined}
      >
        {!isFullscreen && <Grip size={15} />}
        <div className="appwin-ico" style={{ background: APP_ICON_FILES[app.app_type] ? "transparent" : appAccent(app) }}>
          <AppIcon appType={app.app_type} size={28} />
        </div>
        <div className="appwin-title">
          <strong className="appwin-name">{app.title}</strong>
          <span className="appwin-kind">{appTypeLabel(app.app_type)}</span>
        </div>
        <span className={`status-tag ${appStatusClass(app)}`}><span className="d" />{appStatusLabel(app)}</span>
        <div className="appwin-ctrls">
          <button
            onPointerDown={(event) => event.stopPropagation()}
            onClick={onToggleFullscreen}
            title={isFullscreen ? "退出画布全屏" : "画布内全屏"}
            aria-label={isFullscreen ? "退出画布全屏" : "画布内全屏"}
          >
            {isFullscreen ? <Shrink size={14} /> : <Maximize2 size={14} />}
          </button>
          <button
            onPointerDown={(event) => event.stopPropagation()}
            onClick={onTogglePageFullscreen}
            title={isCustomHtml ? "页面全屏演示" : "页面全屏"}
            aria-label={isCustomHtml ? "页面全屏演示" : "页面全屏"}
          >
            <Fullscreen size={14} />
          </button>
          {onDelete && (
            <button onPointerDown={(event) => event.stopPropagation()} onClick={onDelete} title="删除" className="win-btn-delete">
              <Trash2 size={13} />
            </button>
          )}
          {onClose && (
            <button onPointerDown={(event) => event.stopPropagation()} onClick={onClose} title="关闭窗口" className="win-btn-close">
              <X size={14} />
            </button>
          )}
        </div>
      </header>
      )}
      <div
        className="appwin-body"
        onPointerDownCapture={(event) => {
          event.stopPropagation();
          onFocus();
        }}
      >
        <NativeAppRenderer app={app} dashboard={dashboard} isFullscreen={isFullscreen} onEvent={onAppEvent} onFocusApp={onFocusApp} onDashboardUpdate={onDashboardUpdate} sessionContext={sessionContext} />
      </div>
      {!isWorkspaceApp && (
        <footer className="appwin-foot">
          <span><Sparkles size={12} />已保存到学习画布</span>
          {appActions.length ? (
            <div className="app-action-row">
              {(isCustomHtml && !appActions.some((action) => String(action.action ?? "") === "custom.fullscreen")
                ? [{ label: "全屏演示", action: "custom.fullscreen" }, ...appActions]
                : appActions
              ).slice(0, 3).map((action, index) => (
                <button
                  key={`${String(action.action ?? action.label)}-${index}`}
                  className="app-action"
                  onClick={(event) => {
                    event.stopPropagation();
                    if (String(action.action ?? "") === "custom.fullscreen") {
                      onTogglePageFullscreen();
                      return;
                    }
                    onAppEvent(app.app_id, String(action.action ?? "app.action"), { app_id: app.app_id, title: app.title, action });
                  }}
                >
                  {String(action.label ?? action.action ?? "执行")}
                </button>
              ))}
            </div>
          ) : null}
          <button className="ask" onClick={(event) => { event.stopPropagation(); onAppEvent(app.app_id, "tutor.ask", { app_id: app.app_id, title: app.title }); }}>
            问老师
          </button>
        </footer>
      )}
      {!isFullscreen && !fixed && (
        <button
          className="resize-handle"
          title="调整大小"
          onPointerDown={(event) => {
            event.stopPropagation();
            onResizeStart(event);
          }}
        >
          <Maximize2 size={13} />
        </button>
      )}
    </article>
  );
}

// ---- FolderCard — compact canvas icon, click to open modal ----

function FolderCard({ app, onOpen }: { app: CanvasApp; onOpen: () => void }) {
  const payload = app.payload as FolderPayload;
  const previewIcons = payload.items.slice(0, 4);
  return (
    <button className="folder-card" onClick={onOpen} title={`打开 ${app.title}`}>
      <div className="folder-card-icon-grid">
        {previewIcons.map((item) => (
          <span key={item.app_id} className="folder-card-icon-cell">
            <AppIcon appType={item.app_type} size={20} />
          </span>
        ))}
        {previewIcons.length === 0 && (
          <AppIcon appType="resource.folder" size={32} srcOverride={folderIconSrc(app)} />
        )}
      </div>
      <div className="folder-card-meta">
        <strong>{app.title.replace("文件夹", "")}</strong>
        <span>{payload.count} 个</span>
      </div>
    </button>
  );
}

// ---- FolderModal — macOS-style spring modal ----

function FolderModal({
  app,
  onClose,
  onOpenApp,
}: {
  app: CanvasApp;
  onClose: () => void;
  onOpenApp: (appId: string) => void;
}) {
  const payload = app.payload as FolderPayload;
  const [folderQuery, setFolderQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [sortMode, setSortMode] = useState<"recent" | "title">("recent");

  const items = useMemo(() => {
    const q = folderQuery.trim().toLowerCase();
    const filtered = payload.items.filter((item) => !q || item.title.toLowerCase().includes(q));
    return [...filtered].sort((a, b) =>
      sortMode === "title" ? a.title.localeCompare(b.title, "zh-Hans-CN") : byUpdatedDesc(a, b)
    );
  }, [folderQuery, payload.items, sortMode]);

  return (
    <motion.div
      className="folder-modal-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      onClick={onClose}
    >
      <motion.div
        className="folder-modal"
        initial={{ scale: 0.78, opacity: 0, y: 24 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.82, opacity: 0, y: 16 }}
        transition={{ type: "spring", stiffness: 420, damping: 32 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="folder-modal-head">
          <div className="folder-modal-icon">
            <AppIcon appType="resource.folder" size={28} srcOverride={folderIconSrc(app)} />
          </div>
          <div className="folder-modal-title">
            <strong>{app.title.replace("文件夹", "")}</strong>
            <span>{payload.count} 个 App · {payload.subtitle}</span>
          </div>
          <div className="folder-modal-tools">
            <button className={`folder-view-btn ${viewMode === "grid" ? "active" : ""}`} onClick={() => setViewMode("grid")} title="网格">⊞</button>
            <button className={`folder-view-btn ${viewMode === "list" ? "active" : ""}`} onClick={() => setViewMode("list")} title="列表">☰</button>
            <select value={sortMode} onChange={(e) => setSortMode(e.target.value as "recent" | "title")} className="folder-sort-sel">
              <option value="recent">最近</option>
              <option value="title">名称</option>
            </select>
          </div>
          <button className="folder-modal-close" onClick={onClose} aria-label="关闭">✕</button>
        </div>

        {/* Search */}
        <div className="folder-modal-search">
          <Search size={13} />
          <input
            autoFocus
            value={folderQuery}
            onChange={(e) => setFolderQuery(e.target.value)}
            placeholder={`在"${app.title.replace("文件夹", "")}"中搜索`}
          />
        </div>

        {/* Items */}
        <div className={`folder-modal-items ${viewMode}`}>
          {items.length === 0 ? (
            <div className="folder-modal-empty">没有匹配的 App</div>
          ) : viewMode === "grid" ? (
            items.map((item) => (
              <button key={item.app_id} className="folder-grid-item" title={item.title} onClick={() => { onOpenApp(item.app_id); onClose(); }}>
                <span className="folder-grid-icon">
                  <AppIcon appType={item.app_type} size={32} />
                </span>
                <span className="folder-grid-label">{item.title}</span>
              </button>
            ))
          ) : (
            items.map((item) => (
              <button key={item.app_id} className="folder-list-row" title={item.title} onClick={() => { onOpenApp(item.app_id); onClose(); }}>
                <span className="folder-list-icon">
                  <AppIcon appType={item.app_type} size={18} />
                </span>
                <span className="folder-list-name">{item.title}</span>
                <span className={`folder-row-status ${appStatusClass(item)}`}>{appStatusLabel(item)}</span>
              </button>
            ))
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
