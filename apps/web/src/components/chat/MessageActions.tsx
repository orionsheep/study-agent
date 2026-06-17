"use client";

import { useState } from "react";
import { Check, Copy, RotateCcw } from "lucide-react";

export type MessageActionsProps = {
  text: string;
  canRetry: boolean;
  onRetry?: () => void;
};

export function MessageActions({ text, canRetry, onRetry }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="msg-actions">
      <button type="button" className="msg-action-btn" onClick={copy} title="复制">
        {copied ? <Check size={13} /> : <Copy size={13} />}
        <span>{copied ? "已复制" : "复制"}</span>
      </button>
      {canRetry && onRetry ? (
        <button type="button" className="msg-action-btn" onClick={onRetry} title="重新生成">
          <RotateCcw size={13} />
          <span>重试</span>
        </button>
      ) : null}
    </div>
  );
}
