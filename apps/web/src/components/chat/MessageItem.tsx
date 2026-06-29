"use client";

import type { ReactNode } from "react";
import { Paperclip } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { ChatMessage } from "../../lib/events/agentEvents";
import type { ChatAppLink, LearningResource } from "@learnforge/app-protocol";
import { RichMessageContent } from "../../features/tutor-chat/RichMessageContent";
import { AppLinkChip } from "../../features/applink-flight/AppLinkChip";
import { MessageActions } from "./MessageActions";
import { ResourceCard } from "./ResourceCard";

/* ── Types ── */

export type MessageItemProps = {
  message: ChatMessage;
  index: number;
  allMessages: ChatMessage[];
  isStreaming: boolean;
  agentActivity?: ReactNode;
  onSend: (message: string, attachments?: Array<{ name: string; preview?: string }>, skillLabel?: { key?: string; label: string; color: string; bgColor: string; borderColor: string }) => Promise<void>;
  onOpenLink: (link: ChatAppLink, rect: DOMRect) => void;
  onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void>;
};

const messageTransition = { type: "spring", stiffness: 440, damping: 36, mass: 0.72 } as const;

/* ── MessageItem ── */

export function MessageItem({
  message,
  index,
  allMessages,
  isStreaming,
  agentActivity,
  onSend,
  onOpenLink,
  onAddResourceToCanvas,
}: MessageItemProps) {
  const isAssistant = message.role === "assistant";
  const isWelcome = message.id === "welcome";

  // Find the preceding user message for retry
  const precedingUser = isAssistant
    ? [...allMessages.slice(0, index)].reverse().find((m) => m.role === "user")
    : undefined;

  return (
    <>
      <motion.article
        key={message.id}
        layout="position"
        initial={{ opacity: 0, y: 12, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.985, transition: { duration: 0.14 } }}
        transition={messageTransition}
        className={`message msg ${message.role} ${isAssistant ? "tutor" : ""}`}
      >
        <div className="message-content">
          <div className="message-text msg-bubble">
            {/* Skill label badge */}
            {message.skillLabel && (
              <div
                className="msg-skill-label"
                style={{
                  borderColor: message.skillLabel.borderColor,
                  background: message.skillLabel.bgColor,
                  color: message.skillLabel.color,
                }}
              >
                {message.skillLabel.label}
              </div>
            )}

            {/* Attachments */}
            {message.attachments?.length ? (
              <div className="msg-attachments">
                {message.attachments.map((attachment, i) =>
                  attachment.preview ? (
                    <img
                      // #23: prefer a stable value-based key over the array index so
                      // React can correctly reconcile attachments when the list changes.
                      key={attachment.name || `img-${i}`}
                      src={attachment.preview}
                      alt={attachment.name}
                      className="msg-attachment-img"
                    />
                  ) : (
                    <span key={attachment.name || `file-${i}`} className="msg-attachment-file">
                      <Paperclip size={13} />
                      {attachment.name}
                    </span>
                  )
                )}
              </div>
            ) : null}

            {/* Message text (markdown) */}
            {message.text ? (
              <RichMessageContent text={message.text} onGenerate={onSend} />
            ) : null}
          </div>

          {/* Resource cards */}
          {message.resources.length ? (
            <div
              className={`resource-cards ${
                message.resources.every((r) => r.type === "video")
                  ? "resource-cards-video-grid"
                  : ""
              }`}
              data-testid="resource-cards"
            >
              {message.resources.map((resource) => (
                <ResourceCard
                  key={resource.resource_id}
                  resource={resource}
                  onAddResourceToCanvas={onAddResourceToCanvas}
                />
              ))}
            </div>
          ) : null}

          {/* App links */}
          {message.links.length ? (
            <div className="link-row">
              {message.links.map((link) => (
                <AppLinkChip key={link.link_id} link={link} onOpen={onOpenLink} />
              ))}
            </div>
          ) : null}

          {/* Actions (copy / retry) */}
          {isAssistant && !isWelcome && message.text ? (
            <MessageActions
              text={message.text}
              canRetry={!!precedingUser && !isStreaming}
              onRetry={precedingUser ? () => onSend(precedingUser.text) : undefined}
            />
          ) : null}
        </div>
      </motion.article>

      {/* Agent activity — rendered inline after the message */}
      <AnimatePresence initial={false}>
        {agentActivity ? (
          <motion.div
            key={`${message.id}-activity`}
            layout="position"
            initial={{ opacity: 0, y: 8, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.99, transition: { duration: 0.12 } }}
            transition={messageTransition}
            className="message-motion-slot"
          >
            {agentActivity}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
