import { describe, expect, it } from "vitest";
import type { ChatAppLink } from "@learnforge/app-protocol";
import { attachLink, type ChatMessage } from "./agentEvents";

describe("attachLink", () => {
  it("binds AppLinks to the backend message_id instead of the previous assistant message", () => {
    const messages: ChatMessage[] = [
      { id: "welcome", role: "assistant", text: "欢迎语", links: [], resources: [] },
      { id: "user-1", role: "user", text: "生成图片", links: [], resources: [] },
    ];
    const link = {
      link_id: "link-1",
      message_id: "msg-current",
      app_id: "app-image",
      label: "打开教学图",
      action: "fullscreen",
    } as ChatAppLink;

    const next = attachLink(messages, link);

    expect(next.find((message) => message.id === "welcome")?.links).toHaveLength(0);
    expect(next.find((message) => message.id === "msg-current")?.links[0]).toEqual(link);
  });
});
