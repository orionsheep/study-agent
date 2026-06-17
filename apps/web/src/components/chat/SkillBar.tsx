"use client";

import { useState, useRef, useEffect } from "react";
import type { FC } from "react";
import { FileText, Film, ImagePlus, NotebookPen, Plus, Sparkles } from "lucide-react";

/* ── Types ── */

export type SkillItem =
  | { key: string; icon: FC<{ size: number; className?: string }>; label: string; prompt: string }
  | { key: string; icon: FC<{ size: number; className?: string }>; label: string; action: "summarize" };

const SKILLS: SkillItem[] = [
  { key: "video", icon: Film, label: "搜索视频", prompt: "请搜索与当前主题相关的B站教学视频" },
  { key: "image", icon: ImagePlus, label: "生成图片", prompt: "请生成一张教学图解，包含关键概念和公式" },
  { key: "demo", icon: Sparkles, label: "可交互模型", prompt: "请生成一个可交互的演示模型，让我能动手操作理解" },
  { key: "explain", icon: FileText, label: "生成详细讲解", prompt: "请生成详细讲解，做成可在画布打开的 HTML 讲解报告" },
  { key: "notes", icon: NotebookPen, label: "整理到笔记 App", action: "summarize" },
];

export type SkillBarProps = {
  onSkill: (prompt: string) => void;
  onSummarize: () => void | Promise<void>;
};

export function SkillBar({ onSkill, onSummarize }: SkillBarProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="skill-bar" ref={wrapperRef}>
      <div className="skill-options-inner">
        <button
          type="button"
          className="skill-trigger"
          aria-label="附加功能"
          onClick={() => setOpen((prev) => !prev)}
        >
          <Plus size={16} />
        </button>

        {open && (
          <div className="skill-dropdown">
            {SKILLS.map((skill) => (
              <button
                key={skill.key}
                type="button"
                className="skill-dropdown-item"
                data-testid={"action" in skill && skill.action === "summarize" ? "chat-summarize" : undefined}
                onClick={() => {
                  setOpen(false);
                  if ("prompt" in skill) {
                    onSkill(skill.prompt);
                  } else if (skill.action === "summarize") {
                    void onSummarize();
                  }
                }}
              >
                <skill.icon size={15} />
                <span>{skill.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
