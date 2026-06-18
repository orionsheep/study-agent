"use client";

import type { ReactNode } from "react";
import { memo, useEffect, useState } from "react";
import { Shimmer } from "./shimmer";

/* ── StreamingMessage ── */

export type StreamingMessageProps = {
  /** The streaming text content so far */
  children: string;
  /** Whether the stream is still active */
  isStreaming?: boolean;
  /** Label to show while streaming (e.g. "Hermes 思考中…") */
  streamingLabel?: string;
  /** Elapsed seconds since streaming started */
  elapsedSeconds?: number;
  className?: string;
};

/** Displays streaming text with an animated thinking indicator.
 *  When streaming completes, the indicator auto-removes. */
export const StreamingMessage = memo(function StreamingMessage({
  children,
  isStreaming = false,
  streamingLabel = "AI 生成中…",
  elapsedSeconds,
  className,
}: StreamingMessageProps) {
  const [showComplete, setShowComplete] = useState(false);

  useEffect(() => {
    if (!isStreaming && children) {
      // Brief delay before showing "complete" state
      const t = setTimeout(() => setShowComplete(true), 300);
      return () => clearTimeout(t);
    }
    if (isStreaming) setShowComplete(false);
  }, [isStreaming, children]);

  return (
    <div className={`cp-message--assistant ${className ?? ""}`}>
      {/* Streaming indicator */}
      {isStreaming && !children && (
        <div className="cp-streaming-bar">
          <div className="cp-streaming-dots">
            <span />
            <span />
            <span />
          </div>
          <span className="cp-streaming-label">
            {streamingLabel}
            {elapsedSeconds != null ? ` (${elapsedSeconds}s)` : ""}
          </span>
        </div>
      )}

      {/* Content */}
      {children && (
        <div className="cp-message-content">
          <div className="cp-message-response">{children}</div>
          {isStreaming && (
            <div className="cp-streaming-bar">
              <div className="cp-streaming-dots">
                <span />
                <span />
                <span />
              </div>
              <Shimmer duration={1.5}>{streamingLabel}</Shimmer>
            </div>
          )}
        </div>
      )}
    </div>
  );
});
