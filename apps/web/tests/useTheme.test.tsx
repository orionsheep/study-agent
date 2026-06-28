import React, { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { applyTheme, useTheme, type ThemeMode } from "../src/lib/state/useTheme";
import type { WallpaperId } from "../src/lib/assets/appearanceAssets";

type ThemeSnapshot = {
  theme: ThemeMode;
  glassEnabled: boolean;
  wallpaperId: WallpaperId;
};

function ThemeProbe({ onSnapshot }: { onSnapshot: (snapshot: ThemeSnapshot) => void }) {
  const themeState = useTheme();
  useEffect(() => {
    onSnapshot({
      theme: themeState.theme,
      glassEnabled: themeState.glassEnabled,
      wallpaperId: themeState.wallpaperId,
    });
  }, [onSnapshot, themeState.glassEnabled, themeState.theme, themeState.wallpaperId]);
  return null;
}

describe("useTheme appearance state", () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;

  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.className = "";
    document.documentElement.removeAttribute("data-wallpaper");
    document.documentElement.removeAttribute("style");
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    if (root) {
      act(() => root?.unmount());
      root = null;
    }
    container?.remove();
    container = null;
    window.localStorage.clear();
  });

  it("restores theme, glass, and wallpaper from localStorage", () => {
    window.localStorage.setItem("learnforge.settings.theme", JSON.stringify("dark"));
    window.localStorage.setItem("learnforge.settings.glass", JSON.stringify(true));
    window.localStorage.setItem("learnforge.settings.wallpaper", JSON.stringify("pure-white"));
    let snapshot: ThemeSnapshot | undefined;

    act(() => {
      root = createRoot(container!);
      root.render(<ThemeProbe onSnapshot={(next) => { snapshot = next; }} />);
    });

    expect(snapshot).toEqual({ theme: "dark", glassEnabled: true, wallpaperId: "pure-white" });
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("enable-glass")).toBe(true);
    expect(document.documentElement.dataset.wallpaper).toBe("pure-white");
  });

  it("writes wallpaper CSS variables to the document root", () => {
    applyTheme("light", false, "sonoma");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.dataset.wallpaper).toBe("sonoma");
    expect(document.documentElement.style.getPropertyValue("--lf-wallpaper-image")).toContain("sonoma.webp");

    applyTheme("dark", true, "pure-white");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("enable-glass")).toBe(true);
    expect(document.documentElement.style.getPropertyValue("--lf-wallpaper-image")).toBe("none");
  });
});
