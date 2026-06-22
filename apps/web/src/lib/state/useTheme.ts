import { useCallback, useEffect, useState } from "react";
import { loadJson, saveJson } from "./localStorage";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY_THEME = "learnforge.settings.theme";
const STORAGE_KEY_GLASS = "learnforge.settings.glass";

function getInitialTheme(): ThemeMode {
  const stored = loadJson<ThemeMode | null>(STORAGE_KEY_THEME, null);
  if (stored === "light" || stored === "dark") return stored;
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function getInitialGlass(): boolean {
  return loadJson<boolean>(STORAGE_KEY_GLASS, false); // 默认关闭透明度，保持纯净背景
}

function applyTheme(theme: ThemeMode, isGlassEnabled: boolean): void {
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
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(getInitialTheme);
  const [glassEnabled, setGlassState] = useState<boolean>(getInitialGlass);

  useEffect(() => {
    applyTheme(theme, glassEnabled);
    saveJson(STORAGE_KEY_THEME, theme);
    saveJson(STORAGE_KEY_GLASS, glassEnabled);
  }, [theme, glassEnabled]);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleGlass = useCallback(() => {
    setGlassState((prev) => !prev);
  }, []);

  return { theme, glassEnabled, toggleTheme, toggleGlass };
}
