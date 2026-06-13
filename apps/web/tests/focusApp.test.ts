import { describe, expect, it } from "vitest";
import type { CanvasApp } from "@learnforge/app-protocol";
import { focusApp } from "../src/features/app-canvas/focusApp";

function app(id: string, z: number): CanvasApp {
  return {
    app_id: id,
    app_type: "notes.session",
    title: id,
    status: "ready",
    render_mode: "native_react",
    state: "window",
    position: { x: 0, y: 0 },
    size: { width: 300, height: 220 },
    z_index: z,
    payload: {},
    source: {},
    source_refs: [],
    actions: [],
    created_at: "now",
    updated_at: "now"
  };
}

describe("app window state transitions", () => {
  it("focuses target app and raises z-index", () => {
    const result = focusApp([app("a", 1), app("b", 5)], "a");
    expect(result.find((item) => item.app_id === "a")?.state).toBe("focused");
    expect(result.find((item) => item.app_id === "a")?.z_index).toBe(6);
  });
});
