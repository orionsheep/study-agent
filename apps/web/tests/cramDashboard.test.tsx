import React from "react";
import { act } from "react-dom/test-utils";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import type { CanvasApp, DashboardSnapshot } from "@learnforge/app-protocol";
import { NativeAppRenderer } from "../src/features/learning-apps/NativeAppRenderer";
import { DEFAULT_SESSION_CONTEXT } from "../src/lib/api/client";

function render(node: React.ReactNode) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(node));
  return {
    host,
    cleanup: () => act(() => root.unmount()),
  };
}

const dashboardWithCram: DashboardSnapshot = {
  student_id: "demo-student",
  profile: { major: "软件工程" },
  mastery: { "cram-kp-expectancy": 0.48 },
  weak_points: ["期望理论"],
  recommendations: [],
  memory_evidence: [],
  recent_runs: [{ run_id: "run-cram", task_type: "exam_cram", status: "completed" }],
  path_progress: 0.2,
  cram: {
    active_session: {
      session_id: "cram-demo",
      course_title: "管理学期末冲刺",
      stage: "teach",
      progress: {
        total_points: 9,
        taught_points: 3,
        generated_questions: 0,
        wrong_points: 0,
        stubborn_points: 0,
        must_know_total: 6,
        key_point_total: 3,
      },
      next_actions: ["继续讲授下一批知识点"],
    },
    kpis: {
      openstax_books: 24,
      active_sessions: 1,
      must_know_coverage: 0.5,
      stubborn_points: 0,
    },
    recommended_books: [
      {
        slug: "principles-management",
        title: "Principles of Management",
        subject: "Business",
        exam_mode: "conceptual_cram",
      },
    ],
    stubborn_points: [],
    root_cause_distribution: {},
  },
};

const cramApp: CanvasApp = {
  app_id: "app-cram",
  app_type: "exam.cram",
  title: "期末速成",
  status: "ready",
  render_mode: "native_react",
  state: "window",
  position: { x: 0, y: 0 },
  size: { width: 420, height: 360 },
  z_index: 1,
  payload: {
    session_id: "cram-demo",
    course_title: "管理学期末冲刺",
  },
  source: {},
  source_refs: [],
  actions: [],
  created_at: "now",
  updated_at: "now",
};

describe("Cram dashboard integration", () => {
  it("renders cram metrics inside the learning dashboard overview", () => {
    const dashboardApp: CanvasApp = {
      ...cramApp,
      app_id: "app-dashboard",
      app_type: "dashboard.learning",
      title: "学习仪表盘",
      payload: { active_tab: "overview" },
    };
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={dashboardApp}
        dashboard={dashboardWithCram}
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );

    expect(host.textContent).toContain("期末冲刺");
    expect(host.textContent).toContain("管理学期末冲刺");
    expect(host.textContent).toContain("OpenStax");
    expect(host.textContent).toContain("24");
    cleanup();
  });

  it("renders a dedicated cram app with stage, progress, and next action", () => {
    const { host, cleanup } = render(
      <NativeAppRenderer
        app={cramApp}
        dashboard={dashboardWithCram}
        onEvent={() => undefined}
        onFocusApp={() => undefined}
        sessionContext={DEFAULT_SESSION_CONTEXT}
      />
    );

    expect(host.textContent).toContain("期末速成");
    expect(host.textContent).toContain("讲授");
    expect(host.textContent).toContain("3/9");
    expect(host.textContent).toContain("继续讲授下一批知识点");
    cleanup();
  });
});
