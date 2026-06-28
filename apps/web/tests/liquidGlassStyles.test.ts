import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(__dirname, "../src/app/styles.css"), "utf8");

describe("liquid glass style contract", () => {
  it("defines semantic liquid glass tokens and a non-glass fallback mode", () => {
    expect(css).toContain("--lf-glass-surface:");
    expect(css).toContain("--lf-glass-surface-strong:");
    expect(css).toContain("--lf-glass-blur:");
    expect(css).toContain("html:not(.enable-glass)");
    expect(css).toContain("--lf-glass-filter: none");
  });

  it("applies the liquid glass surface contract across every primary surface", () => {
    [
      ".topbar",
      ".appwin",
      ".canvas-app",
      ".native-window-frame",
      ".tutor-chat",
      ".auth-panel",
      ".onboarding-top",
      ".source-panel",
      ".onboarding-chat",
      ".appearance-panel",
      ".folder-modal",
      ".notebooklm-workspace",
      ".nblm-source-rail",
      ".english-workspace",
      ".learning-dashboard",
      ".profile-panel",
      ".resource-center",
      ".video-player-app",
      ".composer",
    ].forEach((selector) => {
      const blockPattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{[^}]*var\\(--lf-glass`, "s");
      expect(css, `${selector} should use --lf-glass tokens`).toMatch(blockPattern);
    });
  });

  it("keeps nested cards and controls on readable glass planes", () => {
    [
      ".ew-checkin-panel",
      ".ew-filter-panel",
      ".ew-mastery-panel",
      ".ew-history-list",
      ".ew-quiz-settings",
      ".resource-detail",
      ".nblm-source-card",
      ".message.tutor .message-text",
    ].forEach((selector) => {
      const blockPattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{[^}]*var\\(--lf-glass`, "s");
      expect(css, `${selector} should sit on a readable glass plane`).toMatch(blockPattern);
    });
  });
});
