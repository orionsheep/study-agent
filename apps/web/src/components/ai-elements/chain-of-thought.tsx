"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Brain, Dot } from "lucide-react";

/* ── Context ── */

const CoTContext = createContext<{
  isOpen: boolean;
  setIsOpen: (v: boolean) => void;
} | null>(null);

function useCoT() {
  const ctx = useContext(CoTContext);
  if (!ctx) throw new Error("ChainOfThought components must be used within <ChainOfThought>");
  return ctx;
}

/* ── ChainOfThought ── */

export type ChainOfThoughtProps = {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
  className?: string;
};

export function ChainOfThought({
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
  children,
  className,
}: ChainOfThoughtProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isOpen = controlledOpen ?? internalOpen;

  const ctx = useMemo(
    () => ({
      isOpen,
      setIsOpen: (v: boolean) => {
        setInternalOpen(v);
        onOpenChange?.(v);
      },
    }),
    [isOpen, onOpenChange],
  );

  return (
    <CoTContext.Provider value={ctx}>
      <motion.div
        className={`cp-cot ${className ?? ""}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>
    </CoTContext.Provider>
  );
}

/* ── ChainOfThoughtHeader ── */

export type ChainOfThoughtHeaderProps = {
  children?: ReactNode;
  className?: string;
};

export function ChainOfThoughtHeader({
  children,
  className,
}: ChainOfThoughtHeaderProps) {
  const { isOpen, setIsOpen } = useCoT();

  return (
    <button
      type="button"
      className={`cp-reasoning-trigger ${className ?? ""}`}
      onClick={() => setIsOpen(!isOpen)}
    >
      <Brain size={16} />
      <span>{children ?? "Agent 工作过程"}</span>
      <motion.span
        animate={{ rotate: isOpen ? 180 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ display: "inline-flex", marginLeft: "auto" }}
      >
        <ChevronDown size={14} />
      </motion.span>
    </button>
  );
}

/* ── ChainOfThoughtContent ── */

export type ChainOfThoughtContentProps = {
  children: ReactNode;
  className?: string;
};

export function ChainOfThoughtContent({
  children,
  className,
}: ChainOfThoughtContentProps) {
  const { isOpen } = useCoT();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={className ?? ""}
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
}

/* ── ChainOfThoughtStep ── */

export type ChainOfThoughtStepProps = {
  label: ReactNode;
  description?: ReactNode;
  status?: "complete" | "active" | "pending";
  children?: ReactNode;
  className?: string;
};

export function ChainOfThoughtStep({
  label,
  description,
  status = "complete",
  children,
  className,
}: ChainOfThoughtStepProps) {
  const statusClass =
    status === "active"
      ? "cp-cot-step--active"
      : status === "complete"
        ? "cp-cot-step--done"
        : "";

  return (
    <motion.div
      className={`cp-cot-step ${statusClass} ${className ?? ""}`}
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="cp-cot-rail">
        <Dot size={16} />
      </div>
      <div className="cp-cot-body">
        <div className="cp-cot-label">{label}</div>
        {description && <div className="cp-cot-desc">{description}</div>}
        {children}
      </div>
    </motion.div>
  );
}
