import { useCallback, useEffect, useState } from "react";
import { loadJson, saveJson } from "./localStorage";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY = "learnforge.settings.theme";

function getInitialTheme(): ThemeMode {
  const stored = loadJson<ThemeMode | null>(STORAGE_KEY, null);
  if (stored === "light" || stored === "dark") return stored;
  // Follow system preference by default
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function applyTheme(theme: ThemeMode): void {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export function useTheme(): {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (theme: ThemeMode) => void;
} {
  const [theme, setThemeState] = useState<ThemeMode>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    saveJson(STORAGE_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme, setTheme };
}
