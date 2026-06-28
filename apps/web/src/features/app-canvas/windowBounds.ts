import type { CanvasViewport } from "@learnforge/app-protocol";

type Point = { x: number; y: number };
type Size = { width: number; height: number };

type ClampOptions = {
  minVisibleXPx?: number;
  minVisibleYPx?: number;
  topInsetPx?: number;
};

function clamp(value: number, min: number, max: number) {
  if (min > max) return min;
  return Math.min(max, Math.max(min, value));
}

export function clampWindowPositionToViewport(
  position: Point,
  size: Size,
  viewport: CanvasViewport,
  viewportSize: Size,
  options: ClampOptions = {},
): Point {
  if (viewportSize.width <= 0 || viewportSize.height <= 0) return position;

  const scale = Math.max(0.05, viewport.scale || 1);
  const width = Math.max(1, size.width);
  const height = Math.max(1, size.height);

  const visibleLeft = -viewport.x / scale;
  const visibleTop = -viewport.y / scale;
  const visibleRight = (viewportSize.width - viewport.x) / scale;
  const visibleBottom = (viewportSize.height - viewport.y) / scale;

  const minVisibleXPx = options.minVisibleXPx ?? 180;
  const minVisibleYPx = options.minVisibleYPx ?? 56;
  const topInsetPx = options.topInsetPx ?? 8;

  const requiredXVisible = Math.min(
    width,
    Math.max(48, Math.min(minVisibleXPx, viewportSize.width * 0.4)) / scale,
  );
  const requiredYVisible = Math.min(
    height,
    Math.max(40, Math.min(minVisibleYPx, viewportSize.height * 0.35)) / scale,
  );

  const minX = visibleLeft - width + requiredXVisible;
  const maxX = visibleRight - requiredXVisible;
  const minY = visibleTop + topInsetPx / scale;
  const maxY = visibleBottom - requiredYVisible;

  return {
    x: Math.round(clamp(position.x, minX, maxX)),
    y: Math.round(clamp(position.y, minY, maxY)),
  };
}

export function samePoint(a: Point, b: Point) {
  return Math.round(a.x) === Math.round(b.x) && Math.round(a.y) === Math.round(b.y);
}
