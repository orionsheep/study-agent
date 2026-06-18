"use client";

import type { ReactNode } from "react";
import { createContext, memo, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Brain } from "lucide-react";
import { Shimmer } from "./shimmer";

/* ── Context ── */

interface ReasoningContextValue {
  isStreaming: boolean;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  duration: number | undefined;
}

const ReasoningContext = createContext<ReasoningContextValue | null>(null);

function useReasoning() {
  const ctx = useContext(ReasoningContext);
  if (!ctx) throw new Error("Reasoning components must be used within <Reasoning>");
  return ctx;
}

/* ── Reasoning ── */

const AUTO_CLOSE_DELAY = 1000;

export type ReasoningProps = {
  isStreaming?: boolean;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  duration?: number;
  children: ReactNode;
  className?: string;
};

export const Reasoning = memo(function Reasoning({
  isStreaming = false,
  open: controlledOpen,
  defaultOpen,
  onOpenChange,
  duration: durationProp,
  children,
  className,
}: ReasoningProps) {
  const resolvedDefault = defaultOpen ?? isStreaming;
  const isExplicitlyClosed = defaultOpen === false;

  const [internalOpen, setInternalOpen] = useState(resolvedDefault);
  const isOpen = controlledOpen ?? internalOpen;

  const setOpen = useCallback(
    (v: boolean) => {
      setInternalOpen(v);
      onOpenChange?.(v);
    },
    [onOpenChange],
  );

  const [duration, setDuration] = useState<number | undefined>(durationProp);
  const hasEverStreamed = useRef(isStreaming);
  const [hasAutoClosed, setHasAutoClosed] = useState(false);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (isStreaming) {
      hasEverStreamed.current = true;
      if (startTimeRef.current === null) startTimeRef.current = Date.now();
    } else if (startTimeRef.current !== null) {
      setDuration(Math.ceil((Date.now() - startTimeRef.current) / 1000));
      startTimeRef.current = null;
    }
  }, [isStreaming]);

  useEffect(() => {
    if (isStreaming && !isOpen && !isExplicitlyClosed) setOpen(true);
  }, [isStreaming]);

  useEffect(() => {
    if (hasEverStreamed.current && !isStreaming && isOpen && !hasAutoClosed) {
      const timer = setTimeout(() => {
        setOpen(false);
        setHasAutoClosed(true);
      }, AUTO_CLOSE_DELAY);
      return () => clearTimeout(timer);
    }
  }, [isStreaming, isOpen, hasAutoClosed, setOpen]);

  const ctx = useMemo<ReasoningContextValue>(
    () => ({ isStreaming, isOpen, setIsOpen: setOpen, duration }),
    [isStreaming, isOpen, setOpen, duration],
  );

  return (
    <ReasoningContext.Provider value={ctx}>
      <motion.div
        className={`cp-reasoning ${className ?? ""}`}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>
    </ReasoningContext.Provider>
  );
});

/* ── ReasoningTrigger ── */

export type ReasoningTriggerProps = {
  getThinkingMessage?: (isStreaming: boolean, duration?: number) => ReactNode;
  className?: string;
};

const defaultThinkingMsg = (streaming: boolean, dur?: number): ReactNode => {
  if (streaming || dur === 0) return <Shimmer duration={1.5}>思考中…</Shimmer>;
  if (dur === undefined) return "思考了几秒";
  return `思考了 ${dur} 秒`;
};

export const ReasoningTrigger = memo(function ReasoningTrigger({
  getThinkingMessage = defaultThinkingMsg,
  className,
}: ReasoningTriggerProps) {
  const { isStreaming, isOpen, setIsOpen, duration } = useReasoning();

  return (
    <button
      type="button"
      className={`cp-reasoning-trigger ${className ?? ""}`}
      onClick={() => setIsOpen(!isOpen)}
    >
      <Brain size={16} />
      <AnimatePresence mode="wait">
        <motion.span
          key={isStreaming ? "streaming" : "done"}
          initial={{ opacity: 0, y: 2 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -2 }}
          transition={{ duration: 0.15 }}
        >
          {getThinkingMessage(isStreaming, duration)}
        </motion.span>
      </AnimatePresence>
      <motion.span
        animate={{ rotate: isOpen ? 180 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ display: "inline-flex", marginLeft: "auto" }}
      >
        <ChevronDown size={14} />
      </motion.span>
    </button>
  );
});

/* ── ReasoningContent ── */

export type ReasoningContentProps = {
  children: string;
  className?: string;
};

export const ReasoningContent = memo(function ReasoningContent({
  children,
  className,
}: ReasoningContentProps) {
  const { isOpen } = useReasoning();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={`cp-reasoning-content ${className ?? ""}`}
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
});
