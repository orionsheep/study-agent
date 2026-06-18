"use client";

import { motion } from "framer-motion";
import { memo, useMemo } from "react";

export interface TextShimmerProps {
  children: string;
  className?: string;
  duration?: number;
}

/** Animated text shimmer — gradient wipe across the text.
 *  ALL styles are inline so no Tailwind / CSS-class dependency. */
export const Shimmer = memo(function Shimmer({
  children,
  className,
  duration = 1.8,
}: TextShimmerProps) {
  const spread = useMemo(() => Math.max(50, children.length * 4), [children]);

  return (
    <motion.span
      className={className}
      animate={{ backgroundPosition: ["200% center", "0% center"] }}
      transition={{ duration, repeat: Infinity, ease: "linear" }}
      style={{
        display: "inline-block",
        backgroundImage: `linear-gradient(
          90deg,
          var(--text-3, #94a3b8) 0%,
          var(--text-3, #94a3b8) 40%,
          var(--text-1, #e2e8f0) 50%,
          var(--text-3, #94a3b8) 60%,
          var(--text-3, #94a3b8) 100%
        )`,
        backgroundSize: "200% 100%",
        backgroundClip: "text",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </motion.span>
  );
});
