"use client";

import type { HTMLAttributes, ReactNode } from "react";
import { memo } from "react";

/* ── Message (container) ── */
export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant";
};

export function Message({ from, className, children, ...props }: MessageProps) {
  return (
    <div
      className={`cp-message cp-message--${from} ${className ?? ""}`}
      {...props}
    >
      {children}
    </div>
  );
}

/* ── MessageContent (bubble / body) ── */
export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export function MessageContent({
  children,
  className,
  ...props
}: MessageContentProps) {
  return (
    <div className={`cp-message-content ${className ?? ""}`} {...props}>
      {children}
    </div>
  );
}

/* ── MessageActions (row of action buttons) ── */
export type MessageActionsProps = HTMLAttributes<HTMLDivElement>;

export function MessageActions({
  className,
  children,
  ...props
}: MessageActionsProps) {
  return (
    <div className={`cp-message-actions ${className ?? ""}`} {...props}>
      {children}
    </div>
  );
}

/* ── MessageAction (icon button with optional tooltip) ── */
export type MessageActionProps = {
  label?: string;
  tooltip?: string;
  onClick?: () => void;
  children: ReactNode;
};

export function MessageAction({
  label,
  tooltip,
  onClick,
  children,
}: MessageActionProps) {
  return (
    <button
      type="button"
      className="cp-message-action"
      aria-label={label ?? tooltip}
      title={tooltip ?? label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

/* ── MessageResponse (markdown body — memo'd for perf) ── */
export type MessageResponseProps = {
  children: ReactNode;
  className?: string;
};

export const MessageResponse = memo(function MessageResponse({
  children,
  className,
}: MessageResponseProps) {
  return (
    <div className={`cp-message-response ${className ?? ""}`}>{children}</div>
  );
});

/* ── AIMessage (convenience: assistant message with content) ── */
export type AIMessageProps = {
  children: ReactNode;
  className?: string;
};

export function AIMessage({ children, className }: AIMessageProps) {
  return (
    <Message from="assistant" className={className}>
      <MessageContent>{children}</MessageContent>
    </Message>
  );
}
