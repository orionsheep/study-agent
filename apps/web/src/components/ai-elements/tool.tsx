"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wrench, ChevronDown, CheckCircle, XCircle } from "lucide-react";

/* ── Collapsible context ── */

const CollapsibleCtx = createContext<{
  open: boolean;
  toggle: () => void;
} | null>(null);

function useCollapsible() {
  const ctx = useContext(CollapsibleCtx);
  if (!ctx) throw new Error("Tool sub-components must be used inside <Tool>");
  return ctx;
}

/* ── Tool ── */

export type ToolProps = {
  defaultOpen?: boolean;
  children: ReactNode;
  className?: string;
};

export function Tool({ defaultOpen = false, className, children }: ToolProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [everOpened, setEverOpened] = useState(defaultOpen);

  const toggle = () => {
    if (!open && !everOpened) setEverOpened(true);
    setOpen(!open);
  };

  return (
    <CollapsibleCtx.Provider value={{ open, toggle }}>
      <motion.div
        className={`cp-tool ${className ?? ""}`}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {/* Only render children after first open (lazy) */}
        <ToolLazyCtx.Provider value={everOpened || open}>
          {children}
        </ToolLazyCtx.Provider>
      </motion.div>
    </CollapsibleCtx.Provider>
  );
}

/* separate context for lazy rendering */
const ToolLazyCtx = createContext<boolean>(false);

/* ── ToolHeader ── */

export type ToolHeaderProps = {
  title?: string;
  state?: "running" | "done" | "error" | "pending";
  toolName?: string;
  className?: string;
};

const statusLabels: Record<string, string> = {
  running: "运行中",
  done: "已完成",
  error: "出错",
  pending: "等待中",
};

function Spinner({ size = 14 }: { size?: number }) {
  return (
    <motion.span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: "2px solid rgba(245,158,11,0.25)",
        borderTopColor: "#f59e0b",
        borderRadius: "50%",
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
    />
  );
}

function StatusIcon({ state }: { state?: string }) {
  switch (state) {
    case "running":
      return <Spinner size={14} />;
    case "done":
      return <CheckCircle size={14} />;
    case "error":
      return <XCircle size={14} />;
    default:
      return <Spinner size={14} />;
  }
}

export function ToolHeader({
  title,
  state = "pending",
  toolName,
  className,
}: ToolHeaderProps) {
  const { open, toggle } = useCollapsible();
  const label = title ?? toolName ?? "Tool";

  return (
    <button
      type="button"
      className={`cp-tool-header ${className ?? ""}`}
      onClick={toggle}
    >
      <Wrench size={16} className="cp-tool-icon" />
      <span>{label}</span>
      <span className={`cp-tool-status cp-tool-status--${state}`}>
        <StatusIcon state={state} />
        {statusLabels[state] ?? state}
      </span>
      <motion.span
        animate={{ rotate: open ? 180 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ display: "inline-flex", marginLeft: "auto" }}
      >
        <ChevronDown size={14} />
      </motion.span>
    </button>
  );
}

/* ── ToolContent ── */

export type ToolContentProps = {
  children: ReactNode;
  className?: string;
};

export function ToolContent({ children, className }: ToolContentProps) {
  const { open } = useCollapsible();
  const everOpened = useContext(ToolLazyCtx);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={`cp-tool-content ${className ?? ""}`}
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
        >
          {everOpened ? children : null}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── ToolInput ── */

export type ToolInputProps = {
  input: unknown;
  className?: string;
};

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ToolInput({ input, className }: ToolInputProps) {
  return (
    <div className={className ?? ""}>
      <h4>参数</h4>
      <pre><code>{safeStringify(input)}</code></pre>
    </div>
  );
}

/* ── ToolOutput ── */

export type ToolOutputProps = {
  output?: unknown;
  errorText?: string;
  className?: string;
};

export function ToolOutput({ output, errorText, className }: ToolOutputProps) {
  if (!output && !errorText) return null;

  const text = errorText ?? (typeof output === "string" ? output : safeStringify(output));

  return (
    <div className={className ?? ""}>
      <h4>{errorText ? "错误" : "结果"}</h4>
      <pre><code>{text}</code></pre>
    </div>
  );
}
