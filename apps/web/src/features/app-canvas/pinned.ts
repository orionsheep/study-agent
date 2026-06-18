import type { CanvasApp } from "@learnforge/app-protocol";

// The 3 always-visible monitoring apps, fixed at the top of the canvas.
// They can never be closed; everything else is a free, openable/closable window.
export const PINNED_APP_IDS = new Set(["app-profile", "app-dashboard", "app-resource"]);
export const PINNED_APP_TYPES = new Set(["profile.dashboard", "dashboard.learning", "resource.center"]);

export const SYSTEM_MODULE_TYPES = new Set(["english.workspace", "notebooklm.workspace", "humanities.notebook"]);
export const REALTIME_TYPES = new Set(["ppt.preview", "image.explanation", "video.script", "video.player", "custom.html"]);

export function isPinnedApp(app: Pick<CanvasApp, "app_id" | "app_type">): boolean {
  return PINNED_APP_IDS.has(app.app_id) || PINNED_APP_TYPES.has(app.app_type as string);
}

export function isSystemModule(app: Pick<CanvasApp, "app_type">): boolean {
  return SYSTEM_MODULE_TYPES.has(app.app_type as string);
}

export function isRealTimeResource(app: Pick<CanvasApp, "app_type">): boolean {
  return REALTIME_TYPES.has(app.app_type as string);
}
