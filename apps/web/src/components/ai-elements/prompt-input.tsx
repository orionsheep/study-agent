"use client";

import type { ChangeEvent, ClipboardEvent, FormEvent, KeyboardEvent, ReactNode, RefObject } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ImagePlus, Mic, Paperclip, Send, X } from "lucide-react";

/* ====================================================================
   Types
   ==================================================================== */

export type FileAttachment = {
  id: string;
  name: string;
  preview?: string; // data URL for images
};

export interface PromptInputContextValue {
  input: string;
  setInput: (value: string) => void;
  attachments: FileAttachment[];
  addFiles: (files: FileList | null) => void;
  removeAttachment: (id: string) => void;
  isStreaming: boolean;
  listening: boolean;
  toggleVoice: () => void;
  onSubmit: () => void;
}

/* ====================================================================
   Context
   ==================================================================== */

const PromptInputCtx = createContext<PromptInputContextValue | null>(null);

export function usePromptInput() {
  const ctx = useContext(PromptInputCtx);
  if (!ctx) throw new Error("PromptInput components must be used within <PromptInput>");
  return ctx;
}

/* ====================================================================
   PromptInput (root)
   ==================================================================== */

export type PromptInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming?: boolean;
  attachments?: FileAttachment[];
  onAttachmentsChange?: (attachments: FileAttachment[]) => void;
  listening?: boolean;
  onToggleVoice?: () => void;
  children: ReactNode;
  className?: string;
};

export function PromptInput({
  value,
  onChange,
  onSubmit,
  isStreaming = false,
  attachments: externalAttachments,
  onAttachmentsChange,
  listening = false,
  onToggleVoice,
  children,
  className,
}: PromptInputProps) {
  const [internalAttachments, setInternalAttachments] = useState<FileAttachment[]>([]);
  const attachments = externalAttachments ?? internalAttachments;
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const addFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList?.length) return;
      const newItems: FileAttachment[] = [];
      Array.from(fileList).forEach((file) => {
        const id = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = () => {
            const preview = typeof reader.result === "string" ? reader.result : undefined;
            const updated = [...(onAttachmentsChange ? externalAttachments ?? [] : internalAttachments), { id, name: file.name, preview }].slice(0, 6);
            if (onAttachmentsChange) onAttachmentsChange(updated);
            else setInternalAttachments(updated);
          };
          reader.readAsDataURL(file);
        } else {
          newItems.push({ id, name: file.name });
        }
      });
      if (newItems.length) {
        const updated = [...(onAttachmentsChange ? externalAttachments ?? [] : internalAttachments), ...newItems].slice(0, 6);
        if (onAttachmentsChange) onAttachmentsChange(updated);
        else setInternalAttachments(updated);
      }
    },
    [internalAttachments, externalAttachments, onAttachmentsChange],
  );

  const removeAttachment = useCallback(
    (id: string) => {
      const updated = attachments.filter((a) => a.id !== id);
      if (onAttachmentsChange) onAttachmentsChange(updated);
      else setInternalAttachments(updated);
    },
    [attachments, onAttachmentsChange],
  );

  const ctx: PromptInputContextValue = {
    input: value,
    setInput: onChange,
    attachments,
    addFiles,
    removeAttachment,
    isStreaming,
    listening,
    toggleVoice: onToggleVoice ?? (() => {}),
    onSubmit,
  };

  return (
    <PromptInputCtx.Provider value={ctx}>
      <form
        className={`cp-composer ${className ?? ""}`}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e: ChangeEvent<HTMLInputElement>) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(e: ChangeEvent<HTMLInputElement>) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
        {children}
      </form>
    </PromptInputCtx.Provider>
  );
}

/* ====================================================================
   PromptInputAttachments
   ==================================================================== */

export type PromptInputAttachmentsProps = {
  className?: string;
};

export function PromptInputAttachments({ className }: PromptInputAttachmentsProps) {
  const { attachments, removeAttachment } = usePromptInput();

  if (!attachments.length) return null;

  return (
    <div className={`composer-attachments ${className ?? ""}`}>
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
            onClick={() => removeAttachment(item.id)}
            aria-label="移除附件"
          >
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}

/* ====================================================================
   PromptInputBody (textarea)
   ==================================================================== */

export type PromptInputBodyProps = {
  placeholder?: string;
  className?: string;
};

export function PromptInputBody({
  placeholder = "输入学习问题…",
  className,
}: PromptInputBodyProps) {
  const { input, setInput, listening, onSubmit } = usePromptInput();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-resize
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Refocus after submit
  useEffect(() => {
    if (!listening) textareaRef.current?.focus();
  }, [listening]);

  if (listening) {
    return (
      <button
        type="button"
        className="composer-wave"
        onClick={() => usePromptInput().toggleVoice()}
        title="点击停止语音输入"
      >
        <span className="composer-wave-dot" />
        <span className="composer-wave-label">正在聆听…轻触停止</span>
      </button>
    );
  }

  return (
    <textarea
      ref={textareaRef}
      className={`cp-composer-textarea ${className ?? ""}`}
      value={input}
      onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
      onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey && !(e.nativeEvent as { isComposing?: boolean }).isComposing) {
          e.preventDefault();
          onSubmit();
        }
      }}
      onPaste={(e: ClipboardEvent<HTMLTextAreaElement>) => {
        const items = e.clipboardData?.files;
        if (items?.length) {
          const { addFiles } = usePromptInput();
          addFiles(items);
        }
      }}
      placeholder={placeholder}
      aria-label="输入学习问题"
      rows={1}
    />
  );
}

/* ====================================================================
   PromptInputFooter (toolbar + send)
   ==================================================================== */

export type PromptInputFooterProps = {
  extraActions?: ReactNode;
  className?: string;
};

export function PromptInputFooter({ extraActions, className }: PromptInputFooterProps) {
  const { input, attachments, isStreaming, onSubmit } = usePromptInput();
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const hasContent = input.trim().length > 0 || attachments.length > 0;

  return (
    <div className={`cp-composer-footer ${className ?? ""}`}>
      <div className="cp-composer-actions">
        <button
          type="button"
          className="cp-composer-btn"
          title="上传图片"
          onClick={() => {
            // Find hidden file inputs in parent form
            const form = document.querySelector(".cp-composer");
            const imgInput = form?.querySelector<HTMLInputElement>('input[type="file"][accept*="image"]');
            imgInput?.click();
          }}
        >
          <ImagePlus size={18} />
        </button>
        <button
          type="button"
          className="cp-composer-btn"
          title="上传文件"
          onClick={() => {
            const form = document.querySelector(".cp-composer");
            const fInput = form?.querySelector<HTMLInputElement>('input[type="file"]:not([accept*="image"])');
            fInput?.click();
          }}
        >
          <Paperclip size={18} />
        </button>
        <button
          type="button"
          className="cp-composer-btn"
          title="语音输入"
          onClick={() => {
            const ctx = usePromptInput();
            ctx.toggleVoice();
          }}
        >
          <Mic size={18} />
        </button>
        {extraActions}
      </div>
      <button
        type="submit"
        className="cp-composer-btn cp-composer-btn--send"
        disabled={isStreaming || !hasContent}
        title="发送"
      >
        <Send size={17} />
      </button>
    </div>
  );
}

/* ====================================================================
   Composed convenience export
   ==================================================================== */

export type PromptInputComposedProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming?: boolean;
  attachments?: FileAttachment[];
  onAttachmentsChange?: (attachments: FileAttachment[]) => void;
  listening?: boolean;
  onToggleVoice?: () => void;
  placeholder?: string;
  className?: string;
};

/** All-in-one PromptInput with attachments, body, and footer pre-wired */
export function PromptInputComposed({
  value,
  onChange,
  onSubmit,
  isStreaming,
  attachments,
  onAttachmentsChange,
  listening,
  onToggleVoice,
  placeholder,
  className,
}: PromptInputComposedProps) {
  return (
    <PromptInput
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
      isStreaming={isStreaming}
      attachments={attachments}
      onAttachmentsChange={onAttachmentsChange}
      listening={listening}
      onToggleVoice={onToggleVoice}
      className={className}
    >
      <PromptInputAttachments />
      <PromptInputBody placeholder={placeholder} />
      <PromptInputFooter />
    </PromptInput>
  );
}
