import { describe, expect, it } from "vitest";
import {
  DEFAULT_WALLPAPER_ID,
  ICON_FILES,
  normalizeWallpaperId,
  themedAppIcon,
  themedBrandAsset,
  wallpaperCssValue,
} from "../src/lib/assets/appearanceAssets";

describe("appearance assets", () => {
  it("resolves themed brand and app icon paths", () => {
    expect(themedBrandAsset("learnforge-logo", "light")).toBe("/brand/light/learnforge-logo.png");
    expect(themedBrandAsset("ai-tutor-avatar", "dark")).toBe("/brand/dark/ai-tutor-avatar.png");
    expect(themedAppIcon("notes.session", "light")).toBe("/icons/light/session_notes_app.png");
    expect(themedAppIcon("knowledge.graph", "dark")).toBe("/icons/dark/knowledge_graph_app.png");
    expect(themedAppIcon("video.player", "dark")).toBe("/icons/dark/folder_video_app.png");
  });

  it("lists every generated icon file", () => {
    expect(ICON_FILES).toHaveLength(20);
    expect(ICON_FILES).toContain("tutor_chat_app.png");
    expect(new Set(ICON_FILES).size).toBe(ICON_FILES.length);
  });

  it("resolves wallpaper defaults and solid color wallpapers", () => {
    expect(normalizeWallpaperId("not-real")).toBe(DEFAULT_WALLPAPER_ID);
    expect(normalizeWallpaperId("pure-white")).toBe("pure-white");
    expect(normalizeWallpaperId("pure-black")).toBe("pure-black");
    expect(wallpaperCssValue("sonoma")).toContain("/wallpapers/apple/sonoma.webp");
    expect(wallpaperCssValue("pure-white")).toBe("none");
    expect(wallpaperCssValue("pure-black")).toBe("none");
  });
});
