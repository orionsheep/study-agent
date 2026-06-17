"use client";

import { useMemo } from "react";
import type { TraceItem } from "../../lib/events/agentEvents";
import { Cockpit } from "../ai-elements/cockpit";
import type { SkillStatus } from "../ai-elements/cockpit";

/* ── Trace normalization ── */

type StepState = "idle" | "running" | "completed" | "failed";

export function normalizeTrace(
  raw: TraceItem | string,
  index: number,
  streaming: boolean,
  isLatest: boolean
) {
  const rawText = typeof raw === "string" ? raw : raw.raw;
  const [fallbackName, fallbackStatus = "", ...fallbackDetailParts] = rawText.split(":");
  const name = typeof raw === "string" ? fallbackName : raw.name;
  const statusText = typeof raw === "string" ? fallbackStatus : raw.status;
  const detailText = typeof raw === "string" ? fallbackDetailParts.join(":") : raw.detail;
  const lowered = statusText.toLowerCase();
  let state: StepState = "idle";
  if (lowered.includes("running") || (streaming && isLatest && !lowered)) state = "running";
  if (lowered.includes("completed") || lowered.includes("done") || lowered.includes("已完成"))
    state = "completed";
  if (lowered.includes("failed") || lowered.includes("error") || lowered.includes("失败"))
    state = "failed";
  return {
    id: `${name}-${index}-${statusText}-${detailText}`,
    raw: rawText,
    name,
    detail: detailText || statusText || "",
    state,
  };
}

/* ── Labels ── */

export function agentStepLabel(name: string) {
  const labels: Record<string, string> = {
    backend: "发送请求",
    intent_detect: "识别意图",
    capability_contract: "Hermes 判定",
    context: "更新学习焦点",
    video_context: "锁定搜索主题",
    bilibili_live_search: "实时搜索 B站",
    video_relevance_filter: "筛选相关视频",
    video_retriever: "整理视频候选",
    video_canvas: "准备视频播放器",
    artifact_verifier: "校验生成结果",
    model_gateway: "生成回答",
    hermes_runtime: "Hermes 执行",
    hermes_native_trace: "Hermes 反馈",
    skill_call: "Hermes 技能调用",
    ppt_style: "确定 PPT 风格",
    ppt_outline: "规划 PPT 大纲",
    ppt_slide_html: "生成网页 PPT",
    ppt_deck_verify: "校验 PPT 翻页",
    resource_bundle_skill: "生成资源包",
    canvas_materializer: "写入学习画布",
    image_generation_skill: "生成图片",
    custom_html_app_skill: "校验互动组件",
    infographic_router: "选择图解形式",
    app_create: "创建画布 App",
    app_link: "创建打开入口",
    resource_create: "创建资源卡片",
    memory: "更新记忆",
    knowledge_agent: "检索课程知识",
    planner_agent: "规划学习路径",
    recommender_agent: "推荐学习材料",
  };
  return labels[name] ?? name.replace(/_/g, " ");
}

export function agentStepDetail(step: ReturnType<typeof normalizeTrace>) {
  const detail = step.detail.trim();
  if (!detail) return "";
  const raw = `${step.name}:${detail}`;
  if (step.name === "hermes_native_trace" && /provider_fallback|HTTP|api[_-]?key|token|quota/i.test(raw)) {
    return "模型通道已自动处理";
  }
  if (step.name === "backend" && /api|token|authorization|401|403/i.test(raw)) {
    return "请求已发送";
  }
  return detail;
}

export function shouldShowAgentStep(name: string) {
  return !["backend", "resource_create", "app_create", "app_link", "memory"].includes(name);
}

/* ── Trace → Skills mapping ── */

export function traceToSkills(
  trace: Array<TraceItem | string>,
  isActive: boolean
): { skills: SkillStatus[]; capability: string } {
  const rawSteps = trace.map((item, index, arr) =>
    normalizeTrace(item, index, isActive, index === arr.length - 1)
  );
  const visible = rawSteps.filter((step) => shouldShowAgentStep(step.name)).slice(-7);

  const capabilityStep = visible.find((s) => s.name === "capability_contract");
  const capability =
    capabilityStep?.detail ||
    (capabilityStep ? agentStepLabel(capabilityStep.name) : "") ||
    "Hermes 工作";

  const skills: SkillStatus[] = visible.map((step) => ({
    id: step.id,
    label: agentStepLabel(step.name),
    status:
      step.state === "running"
        ? "running"
        : step.state === "completed"
          ? "done"
          : "pending",
    detail: agentStepDetail(step),
  }));

  return { skills, capability };
}

/* ── AgentCockpit Component ── */

export function AgentCockpit({
  trace,
  isStreaming,
  reasoningText,
  currentThinking,
}: {
  trace: Array<TraceItem | string>;
  isStreaming: boolean;
  reasoningText?: string;
  currentThinking?: string;
}) {
  const { skills, capability } = useMemo(
    () => traceToSkills(trace, isStreaming),
    [trace, isStreaming]
  );

  if (!isStreaming && skills.length === 0) return null;

  return (
    <section data-testid="agent-activity" aria-label="AI 学习导师工作过程">
      <Cockpit
        skills={skills}
        isActive={isStreaming}
        capability={capability}
        reasoningText={reasoningText}
        currentThinking={currentThinking}
      />
    </section>
  );
}
