import { describe, expect, it } from "vitest";
import { clampWindowPositionToViewport } from "../src/features/app-canvas/windowBounds";

describe("canvas window bounds", () => {
  it("keeps a dragged window reachable inside the visible viewport", () => {
    const position = clampWindowPositionToViewport(
      { x: 980, y: -240 },
      { width: 420, height: 300 },
      { x: 0, y: 0, scale: 1 },
      { width: 1000, height: 700 },
    );

    expect(position.x).toBeLessThanOrEqual(820);
    expect(position.y).toBeGreaterThanOrEqual(8);
  });

  it("clamps against the current pan and zoom transform", () => {
    const position = clampWindowPositionToViewport(
      { x: 2600, y: 10 },
      { width: 500, height: 340 },
      { x: -200, y: -100, scale: 0.5 },
      { width: 1000, height: 700 },
    );

    expect(position.x).toBe(2040);
    expect(position.y).toBe(216);
  });
});
