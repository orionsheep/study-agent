"use client";

import type { TraceItem } from "../../lib/events/agentEvents";
import { AgentCockpit } from "./AgentCockpit";

export type AgentActivityItemProps = {
  messageId: string;
  trace: Array<TraceItem | string>;
  isActive: boolean;
  reasoningText?: string;
  currentThinking?: string;
};

/**
 * Wraps AgentCockpit in a message-shaped article so it renders inline
 * alongside the assistant message that triggered the agent work.
 */
export function AgentActivityItem({ messageId, trace, isActive, reasoningText, currentThinking }: AgentActivityItemProps) {
  if (!isActive && trace.length === 0) return null;

  return (
    <article
      key={`${messageId}-agent-activity`}
      className="message msg assistant tutor agent-activity-message agent-activity-inline"
      data-testid="agent-activity-turn"
    >
      <div className="message-content">
        <AgentCockpit trace={trace} isStreaming={isActive} reasoningText={reasoningText} currentThinking={currentThinking} />
      </div>
    </article>
  );
}
