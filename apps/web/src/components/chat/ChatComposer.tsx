"use client";

import { useState, useRef, useEffect, type FC, type FormEvent, type RefObject } from "react";
import { Film, ImagePlus, Mic, NotebookPen, Paperclip, Plus, Presentation, Send, Sparkles, Square, X } from "lucide-react";

/* ── Types ── */

export type FileAttachment = { id: string; name: string; preview?: string };

export interface SkillInfo {
  key: string;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  prompt: string;
}

export type ChatComposerProps = {
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming: boolean;
  attachments: FileAttachment[];
  onAddFiles: (files: FileList | null) => void;
  onRemoveAttachment: (id: string) => void;
  listening: boolean;
  onToggleVoice: () => void;
  canStop?: boolean;
  onStop?: () => void;
  imageInputRef: RefObject<HTMLInputElement | null>;
  fileInputRef: RefObject<HTMLInputElement | null>;
  waveCanvasRef: RefObject<HTMLCanvasElement | null>;
  activeSkill?: SkillInfo | null;
  onActiveSkillChange?: (skill: SkillInfo | null) => void;
  onSummarize?: () => void | Promise<void>;
};

/* ── Skill definition (internal) ── */

interface SkillDef {
  key: string;
  icon: FC<{ size: number; className?: string }>;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  prompt?: string;
  action?: "summarize";
}

const SKILLS: SkillDef[] = [
  {
    key: "video",
    icon: Film,
    label: "搜索视频",
    color: "#60a5fa",
    bgColor: "rgba(59, 130, 246, 0.12)",
    borderColor: "rgba(59, 130, 246, 0.4)",
    prompt: "请搜索与当前主题相关的B站教学视频",
  },
  {
    key: "image",
    icon: ImagePlus,
    label: "生成图片",
    color: "#a78bfa",
    bgColor: "rgba(139, 92, 246, 0.12)",
    borderColor: "rgba(139, 92, 246, 0.4)",
    prompt: "请生成一张教学图解，包含关键概念和公式",
  },
  {
    key: "ppt",
    icon: Presentation,
    label: "生成PPT",
    color: "#fb923c",
    bgColor: "rgba(249, 115, 22, 0.12)",
    borderColor: "rgba(249, 115, 22, 0.4)",
    prompt: "请生成一份教学PPT，包含关键知识点和讲解大纲",
  },
  {
    key: "demo",
    icon: Sparkles,
    label: "可交互模型",
    color: "#34d399",
    bgColor: "rgba(16, 185, 129, 0.12)",
    borderColor: "rgba(16, 185, 129, 0.4)",
    prompt: "请生成一个可交互的演示模型，让我能动手操作理解",
  },
  {
    key: "notes",
    icon: NotebookPen,
    label: "整理到笔记",
    color: "#f472b6",
    bgColor: "rgba(236, 72, 153, 0.12)",
    borderColor: "rgba(236, 72, 153, 0.4)",
    action: "summarize",
  },
];

const SKILL_ICON_MAP: Record<string, FC<{ size: number; className?: string }>> = {
  video: Film,
  image: ImagePlus,
  ppt: Presentation,
  demo: Sparkles,
  notes: NotebookPen,
};

/* ── ChatComposer ── */

export function ChatComposer({
  input,
  onInputChange,
  onSubmit,
  isStreaming,
  attachments,
  onAddFiles,
  onRemoveAttachment,
  listening,
  onToggleVoice,
  canStop = false,
  onStop,
  imageInputRef,
  fileInputRef,
  waveCanvasRef,
  activeSkill,
  onActiveSkillChange,
  onSummarize,
}: ChatComposerProps) {
  const hasContent = input.trim().length > 0 || attachments.length > 0 || !!activeSkill;
  const [skillsOpen, setSkillsOpen] = useState(false);
  const skillsRef = useRef<HTMLDivElement>(null);

  /* Click outside to close dropdown */
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (skillsRef.current && !skillsRef.current.contains(event.target as Node)) {
        setSkillsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  const handleSkillClick = (skill: SkillDef) => {
    setSkillsOpen(false);
    if (skill.action === "summarize" && onSummarize) {
      void onSummarize();
      return;
    }
    if (skill.prompt) {
      onActiveSkillChange?.({
        key: skill.key,
        label: skill.label,
        color: skill.color,
        bgColor: skill.bgColor,
        borderColor: skill.borderColor,
        prompt: skill.prompt,
      });
    }
  };

  const clearActiveSkill = () => {
    onActiveSkillChange?.(null);
  };

  const SkillIcon = activeSkill ? SKILL_ICON_MAP[activeSkill.key] : null;

  return (
    <form className="composer" onSubmit={handleSubmit}>
      {/* Attachment previews */}
      {attachments.length > 0 && (
        <div className="composer-top-bar">
          <div className="composer-attachments">
            {attachments.map((item) => (
              <div key={item.id} className="composer-chip" title={item.name}>
                {item.preview ? (
                  <img src={item.preview} alt={item.name} />
                ) : (
                  <Paperclip size={13} />
                )}
                <span>{item.name}</span>
                <button
                  type="button"
                  onClick={() => onRemoveAttachment(item.id)}
                  aria-label="移除附件"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSkill && SkillIcon && (
        <div
          className="composer-skill-tag"
          style={{
            borderColor: activeSkill.borderColor,
            background: activeSkill.bgColor,
            color: activeSkill.color,
          }}
        >
          <SkillIcon size={12} />
          <span>{activeSkill.label}</span>
          <button
            type="button"
            className="composer-skill-tag-clear"
            onClick={clearActiveSkill}
            aria-label="取消技能"
            style={{ color: activeSkill.color }}
          >
            <X size={10} />
          </button>
        </div>
      )}

      {/* Voice listening UI */}
      {listening ? (
        <button
          type="button"
          className="composer-wave"
          onClick={onToggleVoice}
          title="点击停止语音输入"
        >
          <span className="composer-wave-dot" />
          <canvas ref={waveCanvasRef} className="composer-wave-canvas" />
          <span className="composer-wave-label">正在聆听…轻触停止</span>
        </button>
      ) : (
        <div className="composer-input-wrap">
          <textarea
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !(event.nativeEvent as { isComposing?: boolean }).isComposing
              ) {
                event.preventDefault();
                onSubmit();
              }
            }}
            aria-label="输入学习问题"
          />
        </div>
      )}

      {/* Toolbar */}
      <div className="composer-toolbar">
        <div className="composer-tools">
          {onActiveSkillChange && onSummarize && (
            <div className="composer-skill-wrap" ref={skillsRef}>
              <button
                type="button"
                className={`tool-btn ${activeSkill ? "has-active-skill" : ""}`}
                title="附加功能"
                onClick={() => setSkillsOpen((prev) => !prev)}
              >
                <Plus size={18} />
              </button>
              {skillsOpen && (
                <div className="composer-skill-dropdown">
                  {SKILLS.map((skill) => (
                    <button
                      key={skill.key}
                      type="button"
                      className="composer-skill-item"
                      data-testid={skill.action === "summarize" ? "chat-summarize" : undefined}
                      onClick={() => handleSkillClick(skill)}
                    >
                      <span
                        className="composer-skill-item-icon"
                        style={{ color: skill.color }}
                      >
                        <skill.icon size={16} />
                      </span>
                      <span className="composer-skill-item-label">{skill.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            className="tool-btn"
            title="上传图片"
            onClick={() => imageInputRef.current?.click()}
          >
            <ImagePlus size={18} />
          </button>
          <button
            type="button"
            className="tool-btn"
            title="上传文件"
            onClick={() => fileInputRef.current?.click()}
          >
            <Paperclip size={18} />
          </button>
          <button
            type="button"
            className={`tool-btn ${listening ? "is-recording" : ""}`}
            title={listening ? "停止语音输入" : "语音输入"}
            onClick={onToggleVoice}
          >
            <Mic size={18} />
          </button>
        </div>
        {canStop ? (
          <button
            type="button"
            data-testid="chat-stop"
            title="停止 Agent"
            className="composer-stop"
            onClick={onStop}
          >
            <Square size={12} fill="currentColor" />
            <span>停止</span>
          </button>
        ) : (
          <button
            type="submit"
            data-testid="chat-send"
            disabled={isStreaming || !hasContent}
            title="发送"
            className="composer-send"
          >
            <Send size={17} />
          </button>
        )}
      </div>

      {/* Hidden file inputs */}
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(event) => {
          onAddFiles(event.target.files);
          event.target.value = "";
        }}
      />
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        onChange={(event) => {
          onAddFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </form>
  );
}
