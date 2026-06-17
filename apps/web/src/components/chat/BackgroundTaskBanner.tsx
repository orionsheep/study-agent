"use client";

import { motion, AnimatePresence } from "framer-motion";

export type BackgroundTaskInfo = {
  run_id: string;
  label: string;
  progress: number;
  detail: string;
  status: "running" | "completed";
};

export function BackgroundTaskBanner({ tasks }: { tasks: BackgroundTaskInfo[] }) {
  const runningTasks = tasks.filter((t) => t.status === "running");
  if (!runningTasks.length) return null;

  return (
    <>
      {runningTasks.map((task) => (
        <motion.div
          key={task.run_id}
          className="background-task-banner"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
        >
          <div className="bg-task-content">
            <span className="bg-task-spinner" />
            <div className="bg-task-info">
              <strong>{task.label}</strong>
              <small>{task.detail}</small>
              <div className="bg-task-bar">
                <div
                  className="bg-task-fill"
                  style={{ width: `${Math.round(task.progress * 100)}%` }}
                />
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </>
  );
}
