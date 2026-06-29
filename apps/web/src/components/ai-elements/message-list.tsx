"use client";

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

/* ── MessageList (scrollable container with auto-scroll) ── */

export type MessageListProps = {
  children: ReactNode;
  className?: string;
  /** Whether to auto-scroll to bottom on new content */
  autoScroll?: boolean;
};

export function MessageList({
  children,
  className,
  autoScroll = true,
}: MessageListProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!autoScroll) return;
    const el = ref.current;
    if (!el) return;
    const raf = window.requestAnimationFrame(() => {
      const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollTo({ top: el.scrollHeight, behavior: prefersReducedMotion ? "auto" : "smooth" });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [children, autoScroll]);

  return (
    <div ref={ref} className={`message-list ${className ?? ""}`}>
      {children}
    </div>
  );
}
