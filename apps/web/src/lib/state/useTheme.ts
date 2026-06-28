import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_WALLPAPER_ID,
  normalizeWallpaperId,
  type WallpaperId,
  wallpaperCssValue,
  wallpaperOverlayCssValue,
} from "../assets/appearanceAssets";
import { loadJson, saveJson } from "./localStorage";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY_THEME = "learnforge.settings.theme";
const STORAGE_KEY_GLASS = "learnforge.settings.glass";
const STORAGE_KEY_WALLPAPER = "learnforge.settings.wallpaper";
const THEME_CHANGE_EVENT = "learnforge:theme-change";

type ThemeChangeDetail = {
  theme: ThemeMode;
  glassEnabled: boolean;
  wallpaperId: WallpaperId;
};

function getInitialTheme(): ThemeMode {
  const stored = loadJson<ThemeMode | null>(STORAGE_KEY_THEME, null);
  if (stored === "light" || stored === "dark") return stored;
  if (typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function getInitialGlass(): boolean {
  return loadJson<boolean>(STORAGE_KEY_GLASS, true);
}

function getInitialWallpaper(): WallpaperId {
  return normalizeWallpaperId(loadJson<string | null>(STORAGE_KEY_WALLPAPER, DEFAULT_WALLPAPER_ID));
}

export function applyTheme(theme: ThemeMode, isGlassEnabled: boolean, wallpaperId: WallpaperId): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }

  if (isGlassEnabled) {
    root.classList.add("enable-glass");
  } else {
    root.classList.remove("enable-glass");
  }

  root.dataset.wallpaper = wallpaperId;
  root.style.setProperty("--lf-wallpaper-image", wallpaperCssValue(wallpaperId));
  root.style.setProperty("--lf-wallpaper-overlay", wallpaperOverlayCssValue(wallpaperId, theme));
}

function notifyThemeChange(theme: ThemeMode, glassEnabled: boolean, wallpaperId: WallpaperId): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<ThemeChangeDetail>(THEME_CHANGE_EVENT, {
    detail: { theme, glassEnabled, wallpaperId },
  }));
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(getInitialTheme);
  const [glassEnabled, setGlassState] = useState<boolean>(getInitialGlass);
  const [wallpaperId, setWallpaperState] = useState<WallpaperId>(getInitialWallpaper);

  useEffect(() => {
    applyTheme(theme, glassEnabled, wallpaperId);
    saveJson(STORAGE_KEY_THEME, theme);
    saveJson(STORAGE_KEY_GLASS, glassEnabled);
    saveJson(STORAGE_KEY_WALLPAPER, wallpaperId);
    notifyThemeChange(theme, glassEnabled, wallpaperId);
  }, [theme, glassEnabled, wallpaperId]);

  useEffect(() => {
    const syncTheme = (nextTheme: ThemeMode, nextGlass: boolean, nextWallpaper: WallpaperId) => {
      setThemeState((prev) => (prev === nextTheme ? prev : nextTheme));
      setGlassState((prev) => (prev === nextGlass ? prev : nextGlass));
      setWallpaperState((prev) => (prev === nextWallpaper ? prev : nextWallpaper));
    };

    const handleThemeEvent = (event: Event) => {
      const detail = (event as CustomEvent<Partial<ThemeChangeDetail>>).detail;
      if (!detail) return;
      const nextTheme = detail.theme === "dark" || detail.theme === "light" ? detail.theme : theme;
      const nextGlass = typeof detail.glassEnabled === "boolean" ? detail.glassEnabled : glassEnabled;
      const nextWallpaper = detail.wallpaperId ? normalizeWallpaperId(detail.wallpaperId) : wallpaperId;
      syncTheme(nextTheme, nextGlass, nextWallpaper);
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY_THEME && event.key !== STORAGE_KEY_GLASS && event.key !== STORAGE_KEY_WALLPAPER) return;
      syncTheme(getInitialTheme(), getInitialGlass(), getInitialWallpaper());
    };

    window.addEventListener(THEME_CHANGE_EVENT, handleThemeEvent);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(THEME_CHANGE_EVENT, handleThemeEvent);
      window.removeEventListener("storage", handleStorage);
    };
  }, [glassEnabled, theme, wallpaperId]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleGlass = useCallback(() => {
    setGlassState((prev) => !prev);
  }, []);

  const setTheme = useCallback((nextTheme: ThemeMode) => {
    setThemeState(nextTheme);
  }, []);

  const setGlassEnabled = useCallback((enabled: boolean) => {
    setGlassState(enabled);
  }, []);

  const setWallpaperId = useCallback((nextWallpaperId: WallpaperId) => {
    setWallpaperState(normalizeWallpaperId(nextWallpaperId));
  }, []);

  return { theme, glassEnabled, wallpaperId, toggleTheme, toggleGlass, setTheme, setGlassEnabled, setWallpaperId };
}
