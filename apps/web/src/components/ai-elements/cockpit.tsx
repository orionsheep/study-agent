"use client";

import { memo, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { Shimmer } from "./shimmer";

/* ── Types ── */

export type SkillStatus = {
  id: string;
  label: string;
  status: "running" | "done" | "error" | "pending";
  detail?: string;
};

export type CockpitProps = {
  skills: SkillStatus[];
  isActive: boolean;
  capability?: string;
  // Hermes 实时状态:思考过程文本 + 当前状态文字
  reasoningText?: string;
  currentThinking?: string;
  defaultOpen?: boolean;
  className?: string;
};

/* ── Tiny spinner (no Tailwind dependency) ── */

function Spinner({ size = 12 }: { size?: number }) {
  return (
    <motion.span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: "2px solid rgba(245,158,11,0.3)",
        borderTopColor: "#f59e0b",
        borderRadius: "50%",
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
    />
  );
}

/* ── Cockpit ── */

export const Cockpit = memo(function Cockpit({
  skills,
  isActive,
  capability,
  reasoningText,
  currentThinking,
  defaultOpen = false,
  className,
}: CockpitProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  // Elapsed timer — reset on every new activity burst
  useEffect(() => {
    if (isActive) {
      if (!startRef.current) startRef.current = Date.now();
      const timer = setInterval(() => {
        setElapsed(Math.floor((Date.now() - (startRef.current ?? Date.now())) / 1000));
      }, 1000);
      return () => clearInterval(timer);
    }
    startRef.current = null;
    setElapsed(0);
  }, [isActive]);

  // Auto-close when agent finishes
  useEffect(() => {
    if (!isActive && skills.length > 0 && skills.every((s) => s.status === "done" || s.status === "error")) {
      const t = setTimeout(() => setOpen(false), 2000);
      return () => clearTimeout(t);
    }
  }, [isActive, skills]);

  const doneCount = skills.filter((s) => s.status === "done").length;

  return (
    <motion.div
      className={`cp-cockpit ${className ?? ""}`}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* ── Trigger bar ── */}
      <button
        type="button"
        className="cp-cockpit-trigger"
        onClick={() => setOpen(!open)}
      >
        {/* Pulsing dot */}
        <motion.span
          className="cp-cockpit-status-dot"
          animate={isActive ? { scale: [1, 1.5, 1], opacity: [1, 0.35, 1] } : { scale: 1, opacity: 0.6 }}
          transition={isActive ? { duration: 1.4, repeat: Infinity, ease: "easeInOut" } : {}}
        />

        {/* Label — shimmer while active, static when done */}
        <AnimatePresence mode="wait">
          <motion.span
            key={isActive ? "active" : "done"}
            initial={{ opacity: 0, y: 2 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -2 }}
            transition={{ duration: 0.15 }}
          >
            {isActive ? (
              <Shimmer duration={1.5}>
                {/* 优先显示 Hermes 实时 thinking 状态,其次显示 capability */}
                {currentThinking || capability || "Hermes 工作中…"}
              </Shimmer>
            ) : (
              <span style={{ color: "var(--text-2, #94a3b8)" }}>
                {capability ?? "已完成"} · {doneCount}/{skills.length} 步骤
              </span>
            )}
          </motion.span>
        </AnimatePresence>

        {/* Elapsed */}
        <span className="cp-cockpit-elapsed">
          {isActive && elapsed > 0 ? `${elapsed}s` : ""}
        </span>

        {/* Caret */}
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ display: "inline-flex" }}
        >
          <ChevronDown size={12} />
        </motion.span>
      </button>

      {/* ── Detail (animated expand) ── */}
      <AnimatePresence>
        {open && (
          <motion.div
            className="cp-cockpit-detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <div className="cp-skill-bar">
              <AnimatePresence>
                {skills.map((skill) => (
                  <motion.span
                    key={skill.id}
                    className={`cp-skill-tag cp-skill-tag--${skill.status}`}
                    title={skill.detail}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.2 }}
                  >
                    {skill.status === "running" && <Spinner size={12} />}
                    {skill.label}
                  </motion.span>
                ))}
              </AnimatePresence>
            </div>
            {/* Hermes 实时思考状态(来自 SDK thinking/status callback) */}
            {isActive && currentThinking ? (
              <div className="cp-thinking-line">
                <Shimmer duration={1.8}>{currentThinking}</Shimmer>
              </div>
            ) : null}
            {/* Hermes 推理过程文本(来自 SDK reasoning callback,流式累积) */}
            {reasoningText ? (
              <details className="cp-reasoning">
                <summary className="cp-reasoning-toggle">💭 思考过程</summary>
                <pre className="cp-reasoning-text">{reasoningText}</pre>
              </details>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
});
