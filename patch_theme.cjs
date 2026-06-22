const fs = require('fs');

const useThemePath = '/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/lib/state/useTheme.ts';
let content = fs.readFileSync(useThemePath, 'utf8');

if (!content.includes('glassEnabled')) {
    content = `import { useCallback, useEffect, useState } from "react";
import { loadJson, saveJson } from "./localStorage";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY = "learnforge.settings.theme";
const GLASS_KEY = "learnforge.settings.glass";

function getInitialTheme(): ThemeMode {
  const stored = loadJson<ThemeMode | null>(STORAGE_KEY, null);
  if (stored === "light" || stored === "dark") return stored;
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

function getInitialGlass(): boolean {
  return loadJson<boolean>(GLASS_KEY, true); // 默认开启毛玻璃
}

function applyTheme(theme: ThemeMode, glassEnabled: boolean): void {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  
  if (!glassEnabled) {
    root.classList.add("disable-glass");
  } else {
    root.classList.remove("disable-glass");
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(getInitialTheme);
  const [glassEnabled, setGlassState] = useState<boolean>(getInitialGlass);

  useEffect(() => {
    applyTheme(theme, glassEnabled);
    saveJson(STORAGE_KEY, theme);
    saveJson(GLASS_KEY, glassEnabled);
  }, [theme, glassEnabled]);

  const setTheme = useCallback((next: ThemeMode) => setThemeState(next), []);
  const toggleTheme = useCallback(() => setThemeState((prev) => (prev === "dark" ? "light" : "dark")), []);
  const toggleGlass = useCallback(() => setGlassState((prev) => !prev), []);

  return { theme, glassEnabled, toggleTheme, toggleGlass, setTheme };
}
`;
    fs.writeFileSync(useThemePath, content);
}
console.log('useTheme patched');
