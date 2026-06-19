import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatAppLink, LearningResource } from "@learnforge/app-protocol";
import type { ModelProvider, NotebookLMContext } from "../../lib/api/client";
import type { ChatMessage, TraceItem } from "../../lib/events/agentEvents";
import { AppLinkChip } from "../applink-flight/AppLinkChip";
import {
  MessageItem,
  AgentActivityItem,
  ChatHeader,
  ChatComposer,
  BackgroundTaskBanner,
  type SkillInfo,
} from "../../components/chat";
import { MessageList } from "../../components/ai-elements/message-list";
import type { BackgroundTaskInfo as BgTaskInfo } from "../../components/chat";

/* ── Types ── */

type BackgroundTaskInfo = BgTaskInfo;

type Props = {
  messages: ChatMessage[];
  generatedLinks: ChatAppLink[];
  activities: Array<{ anchorMessageId: string; trace: TraceItem[]; isActive: boolean }>;
  isStreaming: boolean;
  backgroundTasks: BackgroundTaskInfo[];
  // Hermes 实时状态
  reasoningText?: string;
  currentThinking?: string;
  modelProvider: ModelProvider;
  onModelProviderChange: (provider: ModelProvider) => void;
  onSend: (message: string, attachments?: Array<{ name: string; preview?: string }>, skillLabel?: { key?: string; label: string; color: string; bgColor: string; borderColor: string }) => Promise<void>;
  canStop?: boolean;
  onStop?: () => void;
  onSummarize: () => Promise<void>;
  onOpenLink: (link: ChatAppLink, rect: DOMRect) => void;
  onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void>;
  // English context: when set, a word from the English workspace is the active topic.
  // Shows a chip above the message list and changes the composer placeholder so the
  // user knows their next question will be answered in English-tutor mode.
  englishWord?: string | null;
  onClearEnglishWord?: () => void;
  notebookLMContext?: NotebookLMContext | null;
  onClearNotebookLMContext?: () => void;
  focusRequestId?: number;
};

/* ── TutorChat ── */

export function TutorChat({
  messages,
  generatedLinks,
  activities,
  isStreaming,
  backgroundTasks,
  reasoningText,
  currentThinking,
  modelProvider,
  onModelProviderChange,
  onSend,
  canStop = false,
  onStop,
  onSummarize,
  onOpenLink,
  onAddResourceToCanvas,
  englishWord,
  onClearEnglishWord,
  notebookLMContext,
  onClearNotebookLMContext,
  focusRequestId,
}: Props) {
  const [input, setInput] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [attachments, setAttachments] = useState<Array<{ id: string; name: string; preview?: string }>>([]);
  const [listening, setListening] = useState(false);
  const [activeSkill, setActiveSkill] = useState<SkillInfo | null>(null);

  const waveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recognitionRef = useRef<{ stop: () => void } | null>(null);

  /* ── Derived ── */

  const allGeneratedLinks = useMemo(
    () => {
      const lastUserIndex = messages.map((message) => message.role).lastIndexOf("user");
      const turnMessages = lastUserIndex >= 0 ? messages.slice(lastUserIndex + 1) : messages;
      return [...turnMessages.flatMap((m) => m.links), ...generatedLinks].filter(
        (link, i, arr) => arr.findIndex((item) => item.link_id === link.link_id) === i
      ).slice(-6);
    },
    [messages, generatedLinks],
  );

  const activitiesByAnchor = useMemo(
    () =>
      new Map(
        activities
          .filter((a) => a.anchorMessageId && (a.isActive || a.trace.length > 0))
          .map((a) => [a.anchorMessageId, a]),
      ),
    [activities],
  );

  /* ── Handlers ── */

  const addFiles = (fileList: FileList | null) => {
    if (!fileList?.length) return;
    Array.from(fileList).forEach((file) => {
      const id = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => {
          const preview = typeof reader.result === "string" ? reader.result : undefined;
          setAttachments((cur) => [...cur, { id, name: file.name, preview }].slice(0, 6));
        };
        reader.readAsDataURL(file);
      } else {
        setAttachments((cur) => [...cur, { id, name: file.name }].slice(0, 6));
      }
    });
  };

  const removeAttachment = (id: string) => {
    setAttachments((cur) => cur.filter((item) => item.id !== id));
  };

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: new () => unknown }).SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: new () => unknown }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      window.alert("当前浏览器不支持语音输入，请使用 Chrome 或 Edge。");
      return;
    }
    const recognition = new SpeechRecognition() as {
      lang: string;
      interimResults: boolean;
      continuous: boolean;
      onresult: (event: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
      onend: () => void;
      onerror: () => void;
      start: () => void;
      stop: () => void;
    };
    recognition.lang = "zh-CN";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) transcript += event.results[i][0].transcript;
      // #12: read the current input via a functional update rather than capturing `input`
      // at recognition-start. A stale snapshot would clobber any edits made while listening.
      setInput((current) => `${current ? `${current} ` : ""}${transcript}`);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  };

  const sendNow = async () => {
    const userText = input.trim();
    const fullText = userText || activeSkill?.prompt || "";
    if (!fullText && !attachments.length) return;
    const outgoing = attachments.map((item) => ({ name: item.name, preview: item.preview }));
    setInput("");
    setAttachments([]);
    const skillLabelData = activeSkill
      ? {
          label: activeSkill.label,
          key: activeSkill.key,
          color: activeSkill.color,
          bgColor: activeSkill.bgColor,
          borderColor: activeSkill.borderColor,
        }
      : undefined;
    setActiveSkill(null);
    await onSend(fullText, outgoing, skillLabelData);
  };

  /* ── Effects ── */

  // Live microphone waveform
  useEffect(() => {
    if (!listening) return;
    let audioCtx: AudioContext | null = null;
    let stream: MediaStream | null = null;
    let raf = 0;
    let cancelled = false;
    const AudioCtor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((mic) => {
        if (cancelled || !AudioCtor) {
          mic.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = mic;
        audioCtx = new AudioCtor();
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        audioCtx.createMediaStreamSource(mic).connect(analyser);
        const bins = analyser.frequencyBinCount;
        const data = new Uint8Array(bins);
        const draw = () => {
          // #13: bail out early if the effect was torn down between frames; otherwise we'd
          // schedule another raf after cancelAnimationFrame() already ran on cleanup.
          if (cancelled) return;
          const canvas = waveCanvasRef.current;
          if (canvas) {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const cw = canvas.clientWidth || 240;
            const ch = canvas.clientHeight || 32;
            if (canvas.width !== Math.round(cw * dpr)) {
              canvas.width = Math.round(cw * dpr);
              canvas.height = Math.round(ch * dpr);
            }
            const ctx = canvas.getContext("2d");
            if (ctx) {
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              analyser.getByteFrequencyData(data);
              const gap = 3 * dpr;
              const bw = (canvas.width - gap * (bins - 1)) / bins;
              for (let i = 0; i < bins; i += 1) {
                const v = data[i] / 255;
                const bh = Math.max(2 * dpr, v * canvas.height);
                const x = i * (bw + gap);
                const y = (canvas.height - bh) / 2;
                ctx.fillStyle = `rgba(122,162,255,${0.35 + 0.65 * v})`;
                ctx.fillRect(x, y, bw, bh);
              }
            }
          }
          raf = requestAnimationFrame(draw);
        };
        draw();
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((track) => track.stop());
      audioCtx?.close().catch(() => undefined);
    };
  }, [listening]);

  /* ── Render ── */

  return (
    <aside className="tutor-chat chat" data-testid="tutor-chat">
      <ChatHeader
        modelProvider={modelProvider}
        onModelProviderChange={onModelProviderChange}
        settingsOpen={settingsOpen}
        onToggleSettings={() => setSettingsOpen((o) => !o)}
        onRegeneratePath={() => {
          setInput("请重新规划我的学习路径，并生成左侧互动资源");
          setSettingsOpen(false);
        }}
      />

      {/* English context chip — a word selected in the English workspace is the active
          topic. The next question routes through the english_chat skill. Clearable. */}
      {englishWord ? (
        <div className="english-context-bar" data-testid="english-context-bar">
          <span className="english-context-chip">
            <span className="english-context-label">英语</span>
            <strong className="english-context-word">{englishWord}</strong>
            {onClearEnglishWord ? (
              <button
                type="button"
                className="english-context-clear"
                onClick={onClearEnglishWord}
                aria-label={`清除英语上下文：${englishWord}`}
                title="清除英语上下文"
              >
                ✕
              </button>
            ) : null}
          </span>
        </div>
      ) : null}

      {notebookLMContext ? (
        <div className="notebooklm-context-bar" data-testid="notebooklm-context-bar">
          <span className="notebooklm-context-chip">
            <span className="notebooklm-context-label">NotebookLM</span>
            <strong className="notebooklm-context-title">{notebookLMContext.sourceTitle || notebookLMContext.notebookTitle || notebookLMContext.notebookId || "当前来源"}</strong>
            {onClearNotebookLMContext ? (
              <button
                type="button"
                className="notebooklm-context-clear"
                onClick={onClearNotebookLMContext}
                aria-label="清除 NotebookLM 上下文"
                title="清除 NotebookLM 上下文"
              >
                x
              </button>
            ) : null}
          </span>
        </div>
      ) : null}

      <MessageList className="chat-body">
        {/* Generated links rail */}
        {allGeneratedLinks.length ? (
          <section className="generated-links-rail" aria-label="本轮生成物">
            <div>
              <strong>本轮生成物</strong>
              <small>点击后左侧画布会聚焦并全屏打开</small>
            </div>
            <div className="generated-links-row">
              {allGeneratedLinks.map((link) => (
                <AppLinkChip key={link.link_id} link={link} onOpen={onOpenLink} />
              ))}
            </div>
          </section>
        ) : null}

        {/* Background task progress */}
        <BackgroundTaskBanner tasks={backgroundTasks} />

        {/* Messages */}
        {messages.map((message, idx) => {
          const agentActivity = activitiesByAnchor.get(message.id);
          return (
            <MessageItem
              key={message.id}
              message={message}
              index={idx}
              allMessages={messages}
              isStreaming={isStreaming}
              agentActivity={
                agentActivity ? (
                  <AgentActivityItem
                    messageId={message.id}
                    trace={agentActivity.trace}
                    isActive={agentActivity.isActive}
                    reasoningText={reasoningText}
                    currentThinking={currentThinking}
                  />
                ) : null
              }
              onSend={onSend}
              onOpenLink={onOpenLink}
              onAddResourceToCanvas={onAddResourceToCanvas}
            />
          );
        })}
      </MessageList>

      <ChatComposer
        input={input}
        onInputChange={setInput}
        onSubmit={sendNow}
        isStreaming={isStreaming}
        attachments={attachments}
        onAddFiles={addFiles}
        onRemoveAttachment={removeAttachment}
        listening={listening}
        onToggleVoice={toggleVoice}
        canStop={canStop}
        onStop={onStop}
        imageInputRef={imageInputRef}
        fileInputRef={fileInputRef}
        waveCanvasRef={waveCanvasRef}
        activeSkill={activeSkill}
        onActiveSkillChange={setActiveSkill}
        onSummarize={onSummarize}
        focusRequestId={focusRequestId}
      />
    </aside>
  );
}
