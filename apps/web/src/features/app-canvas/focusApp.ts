import type { CanvasApp } from "@learnforge/app-protocol";

export function focusApp(apps: CanvasApp[], appId: string, nextState: CanvasApp["state"] = "focused"): CanvasApp[] {
  const top = Math.max(...apps.map((app) => app.z_index), 1) + 1;
  return apps.map((app) => {
    if (app.app_id !== appId) {
      return app.state === "focused" ? { ...app, state: "window" } : app;
    }
    return {
      ...app,
      state: nextState,
      z_index: top,
      updated_at: new Date().toISOString()
    };
  });
}
