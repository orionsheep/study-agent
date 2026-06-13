import { describe, expect, it } from "vitest";
import { applyAgentEvent, applyTraceEvent, type ChatMessage, type EventApplyResult } from "../src/lib/events/agentEvents";

const baseMessage: ChatMessage = { id: "m1", role: "assistant", text: "", links: [], resources: [] };

describe("agent stream event reducer", () => {
  it("applies text, app links, resources, and dashboard evidence", () => {
    let state: EventApplyResult = { apps: [], messages: [baseMessage], trace: [], backgroundTasks: [] };
    state = applyAgentEvent(state, { type: "assistant.delta", message_id: "m1", text: "你好" });
    expect(state.messages[0].text).toBe("你好");
    state = applyAgentEvent(state, {
      type: "app.link.create",
      link: { link_id: "l1", message_id: "m1", app_id: "app-gradient", label: "打开实验台", action: "focus", created_at: "now" }
    });
    expect(state.messages[0].links).toHaveLength(1);
    state = applyAgentEvent(state, {
      type: "app.link.create",
      link: { link_id: "l1", message_id: "m1", app_id: "app-gradient", label: "打开实验台", action: "focus", created_at: "now" }
    });
    expect(state.messages[0].links).toHaveLength(1);
    state = applyAgentEvent(state, {
      type: "run.step",
      run_id: "r1",
      step_name: "planner_agent",
      status: "completed"
    });
    expect(state.trace.at(-1)?.name).toBe("planner_agent");
    expect(state.trace.at(-1)?.raw).toContain("planner_agent");
    expect(applyTraceEvent(state.trace, { type: "assistant.done", message_id: "m1" })).toEqual(state.trace);
  });

  it("attaches resources to the explicit assistant message id", () => {
    let state: EventApplyResult = { apps: [], messages: [], trace: [], backgroundTasks: [] };
    state = applyAgentEvent(state, {
      type: "resource.create",
      message_id: "msg-video",
      resource: {
        resource_id: "res-video-1",
        type: "video",
        title: "数据结构 B站课",
        target_topic: "数据结构",
        difficulty: "中级",
        content: { url: "https://www.bilibili.com/video/BV1xx", author: "UP主" },
        source_refs: [],
        personalized_reason: "匹配当前搜索",
        tags: ["#B站视频"]
      }
    });
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].id).toBe("msg-video");
    expect(state.messages[0].resources[0].type).toBe("video");
    state = applyAgentEvent(state, { type: "assistant.delta", message_id: "msg-video", text: "找到视频。" });
    expect(state.messages[0].text).toBe("找到视频。");
  });
});
