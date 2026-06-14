import { Fragment, FormEvent, useEffect, useRef, useState, type DragEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ChatAppLink, LearningResource } from "@learnforge/app-protocol";
import { BrainCircuit, Check, CheckCircle2, Copy, ExternalLink, Film, ImagePlus, Mic, NotebookPen, Paperclip, PlayCircle, PlusCircle, RotateCcw, Route, Send, Settings2, Sparkles, X } from "lucide-react";
import { AppLinkChip } from "../applink-flight/AppLinkChip";
import { RichMessageContent } from "./RichMessageContent";
import type { ModelProvider } from "../../lib/api/client";
import type { ChatMessage, TraceItem } from "../../lib/events/agentEvents";
import { bilibiliEmbedUrl, extractBvidFromResource } from "../../lib/video/bilibili";

type BackgroundTaskInfo = {
  run_id: string;
  label: string;
  progress: number;
  detail: string;
  status: 'running' | 'completed';
};

type Props = {
  messages: ChatMessage[];
  generatedLinks: ChatAppLink[];
  activities: Array<{ anchorMessageId: string; trace: TraceItem[]; isActive: boolean }>;
  isStreaming: boolean;
  backgroundTasks: BackgroundTaskInfo[];
  modelProvider: ModelProvider;
  onModelProviderChange: (provider: ModelProvider) => void;
  onSend: (message: string, attachments?: Array<{ name: string; preview?: string }>) => Promise<void>;
  onSummarize: () => Promise<void>;
  onOpenLink: (link: ChatAppLink, rect: DOMRect) => void;
  onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void>;
};

type StepState = "idle" | "running" | "completed" | "failed";
const MODEL_OPTIONS: { provider: ModelProvider; label: string; caption: string }[] = [
  { provider: "gemini", label: "Gemini 3.1 Pro", caption: "Google Gemini" },
  { provider: "mimo", label: "MiMo 2.5 Pro", caption: "小米 MiMo" }
];

function normalizeTrace(raw: TraceItem | string, index: number, streaming: boolean, isLatest: boolean) {
  const rawText = typeof raw === "string" ? raw : raw.raw;
  const [fallbackName, fallbackStatus = "", ...fallbackDetailParts] = rawText.split(":");
  const name = typeof raw === "string" ? fallbackName : raw.name;
  const statusText = typeof raw === "string" ? fallbackStatus : raw.status;
  const detailText = typeof raw === "string" ? fallbackDetailParts.join(":") : raw.detail;
  const lowered = statusText.toLowerCase();
  let state: StepState = "idle";
  if (lowered.includes("running") || (streaming && isLatest && !lowered)) state = "running";
  if (lowered.includes("completed") || lowered.includes("done") || lowered.includes("已完成")) state = "completed";
  if (lowered.includes("failed") || lowered.includes("error") || lowered.includes("失败")) state = "failed";
  return { id: `${name}-${index}-${statusText}-${detailText}`, raw: rawText, name, detail: detailText || statusText || "", state };
}

function agentStepLabel(name: string) {
  const labels: Record<string, string> = {
    backend: "发送请求",
    intent_detect: "识别意图",
    capability_contract: "Hermes 判定",
    context: "更新学习焦点",
    video_context: "锁定搜索主题",
    bilibili_live_search: "实时搜索 B站",
    video_relevance_filter: "筛选相关视频",
    video_retriever: "整理视频候选",
    video_canvas: "准备视频播放器",
    artifact_verifier: "校验生成结果",
    model_gateway: "生成回答",
    hermes_runtime: "Hermes 执行",
    hermes_native_trace: "Hermes 反馈",
    ppt_style: "确定 PPT 风格",
    ppt_outline: "规划 PPT 大纲",
    ppt_slide_html: "生成网页 PPT",
    ppt_deck_verify: "校验 PPT 翻页",
    resource_bundle_skill: "生成资源包",
    canvas_materializer: "写入学习画布",
    image_generation_skill: "生成图片",
    custom_html_app_skill: "校验互动组件",
    infographic_router: "选择图解形式",
    app_create: "创建画布 App",
    app_link: "创建打开入口",
    resource_create: "创建资源卡片",
    memory: "更新记忆",
    knowledge_agent: "检索课程知识",
    planner_agent: "规划学习路径",
    recommender_agent: "推荐学习材料",
  };
  return labels[name] ?? name.replace(/_/g, " ");
}

function agentStepDetail(step: ReturnType<typeof normalizeTrace>) {
  const detail = step.detail.trim();
  if (!detail) return "";
  const raw = `${step.name}:${detail}`;
  if (step.name === "hermes_native_trace" && /provider_fallback|HTTP|api[_-]?key|token|quota/i.test(raw)) {
    return "模型通道已自动处理";
  }
  if (step.name === "backend" && /api|token|authorization|401|403/i.test(raw)) {
    return "请求已发送";
  }
  return detail;
}

function shouldShowAgentStep(name: string) {
  return ![
    "backend",
    "skill_call",
    "resource_create",
    "app_create",
    "app_link",
    "memory",
  ].includes(name);
}

function AgentActivity({ trace, isStreaming }: { trace: Array<TraceItem | string>; isStreaming: boolean }) {
  const rawSteps = trace.map((item, index, arr) =>
    normalizeTrace(item, index, isStreaming, index === arr.length - 1)
  );

  if (!isStreaming && rawSteps.length === 0) return null;

  const visibleSteps = rawSteps
    .filter((step) => shouldShowAgentStep(step.name))
    .slice(-7)
    .map((step) => {
      const label = agentStepLabel(step.name);
      const detail = agentStepDetail(step);
      // ── capability_contract 携带有 Hermes 判定的具体能力，直接展示 ──
      if (step.name === "capability_contract" && detail) {
        return { ...step, label: detail, detail: "" };
      }
      return { ...step, label, detail };
    });
  const headStep = visibleSteps.find((step) => step.state === "running") ?? visibleSteps.at(-1);
  const completedSteps = visibleSteps.filter((step) => step.state === "completed").slice(-3);
  const statusText = isStreaming ? (headStep?.label ?? "正在思考") : "已完成";

  return (
    <section className="ag-group" data-testid="agent-activity" aria-label="AI 学习导师工作过程">
      <div className="ag-current">
        <span className={`ag-status-dot ${isStreaming ? "is-running" : "is-done"}`} aria-hidden="true">
          {isStreaming ? <Sparkles size={12} /> : <Check size={12} />}
        </span>
        <AnimatePresence mode="wait">
          <motion.div
            key={`${headStep?.id ?? "idle"}-${headStep?.state ?? "idle"}`}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -3 }}
            transition={{ duration: 0.14 }}
            className="ag-current-copy"
            data-testid="run-trace"
          >
            <span className={isStreaming ? "ag-shimmer" : "ag-head-label-done"}>{statusText}</span>
          </motion.div>
        </AnimatePresence>
        <span className="machine-trace" aria-hidden="true">
          {visibleSteps.map((step) => `${step.name}:${step.state}:${step.detail}`).join(" | ")}
        </span>
      </div>
      {completedSteps.length ? (
        <div className="ag-timeline">
          {completedSteps.map((step) => {
          return (
            <div key={step.id} className={`ag-tl-row ag-tl-${step.state}`}>
              <span className="ag-tl-node">
                <CheckCircle2 size={10} />
              </span>
              <span className="ag-tl-copy">
                <span className="ag-tl-label">{step.label}</span>
              </span>
            </div>
          );
          })}
        </div>
      ) : null}
    </section>
  );
}

function MessageActions({ text, onRetry, canRetry }: { text: string; onRetry?: () => void; canRetry: boolean }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };
  return (
    <div className="msg-actions">
      <button type="button" className="msg-action-btn" onClick={copy} title="复制">
        {copied ? <Check size={13} /> : <Copy size={13} />}
        <span>{copied ? "已复制" : "复制"}</span>
      </button>
      {canRetry && onRetry ? (
        <button type="button" className="msg-action-btn" onClick={onRetry} title="重新生成">
          <RotateCcw size={13} />
          <span>重试</span>
        </button>
      ) : null}
    </div>
  );
}

function resourceUrl(resource: LearningResource) {
  const content = resource.content ?? {};
  const url = content.url ?? content.href;
  return typeof url === "string" && /^https?:\/\//.test(url) ? url : "";
}

function playLabel(value: unknown) {
  const count = Number(value ?? 0);
  if (!Number.isFinite(count) || count <= 0) return "";
  if (count >= 10000) return `${(count / 10000).toFixed(count >= 100000 ? 0 : 1)}万播放`;
  return `${Math.round(count)}播放`;
}

function startResourceDrag(event: DragEvent<HTMLElement>, resource: LearningResource) {
  event.dataTransfer.effectAllowed = "copy";
  event.dataTransfer.setData("application/x-learnforge-resource", JSON.stringify(resource));
  event.dataTransfer.setData("text/plain", resource.title);
}

function VideoResourceCard({ resource, onAddResourceToCanvas }: { resource: LearningResource; onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void> }) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const content = resource.content ?? {};
  const url = resourceUrl(resource);
  const bvid = extractBvidFromResource(resource);
  const embedUrl = bilibiliEmbedUrl(bvid);
  const author = String(content.author ?? "B站视频");
  const cover = String(content.cover ?? content.pic ?? content.thumbnail ?? "");
  const duration = String(content.duration ?? "");
  const play = playLabel(content.play);
  const togglePreview = () => { if (embedUrl) setPreviewOpen((open) => !open); };
  return (
    <section
      className="resource-card video-resource-card"
      draggable
      onDragStart={(event) => startResourceDrag(event, resource)}
      data-testid={`video-resource-card-${resource.resource_id}`}
      title="拖到左侧画布生成视频播放器"
    >
      <button type="button" className="video-card-cover" onClick={togglePreview} aria-label="预览视频">
        {cover ? (
          <img src={cover} alt={resource.title} loading="lazy" referrerPolicy="no-referrer" />
        ) : (
          <span className="video-card-cover-fallback"><Film size={26} /></span>
        )}
        {embedUrl ? <span className="video-card-play"><PlayCircle size={34} /></span> : null}
        {duration ? <span className="video-card-duration">{duration}</span> : null}
      </button>
      <div className="video-card-body">
        <strong>{resource.title}</strong>
        <small>{[author, play].filter(Boolean).join(" · ")}</small>
        <div className="video-card-actions">
          {embedUrl ? (
            <button type="button" onClick={togglePreview} title={previewOpen ? "收起" : "预览"}>
              <PlayCircle size={13} />
              <span className="video-action-label">{previewOpen ? "收起" : "预览"}</span>
            </button>
          ) : null}
          {url ? (
            <a href={url} target="_blank" rel="noreferrer" title="打开B站">
              <ExternalLink size={13} />
              <span className="video-action-label">打开B站</span>
            </a>
          ) : null}
          <button type="button" onClick={() => onAddResourceToCanvas(resource)} title="加入画布">
            <PlusCircle size={13} />
            <span className="video-action-label">加入画布</span>
          </button>
        </div>
      </div>
      {previewOpen && embedUrl ? (
        <div className="video-card-embed" data-testid={`video-resource-embed-${resource.resource_id}`}>
          <iframe
            title={`${resource.title} B站预览`}
            src={embedUrl}
            loading="lazy"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation"
            allow="fullscreen; picture-in-picture; autoplay"
            allowFullScreen
          />
        </div>
      ) : null}
    </section>
  );
}

function ResourceCard({ resource, onAddResourceToCanvas }: { resource: LearningResource; onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void> }) {
  if (resource.type === "video") {
    return <VideoResourceCard resource={resource} onAddResourceToCanvas={onAddResourceToCanvas} />;
  }
  return (
    <section
      className="resource-card"
      draggable
      onDragStart={(event) => startResourceDrag(event, resource)}
      title="拖到左侧画布生成资源中心"
    >
      <strong>{resource.title}</strong>
      <small>学习资料</small>
      <p>{resource.personalized_reason}</p>
    </section>
  );
}

type SkillItem =
  | { key: string; icon: React.FC<{ size: number; className?: string }>; label: string; prompt: string }
  | { key: string; icon: React.FC<{ size: number; className?: string }>; label: string; action: "summarize" };

const SKILLS: SkillItem[] = [
  { key: "video", icon: Film, label: "搜索视频", prompt: "请搜索与当前主题相关的B站教学视频" },
  { key: "image", icon: ImagePlus, label: "生成图片", prompt: "请生成一张教学图解，包含关键概念和公式" },
  { key: "demo", icon: Sparkles, label: "可交互模型", prompt: "请生成一个可交互的演示模型，让我能动手操作理解" },
  { key: "notes", icon: NotebookPen, label: "整理到笔记 App", action: "summarize" },
];

function SkillBar({ onSkill, onSummarize }: { onSkill: (prompt: string) => void; onSummarize: () => void | Promise<void> }) {
  return (
    <div className="skill-bar">
      <div className="skill-options-inner">
        {SKILLS.map((skill) => (
          <button
            key={skill.key}
            type="button"
            className="skill-chip"
            data-testid={"action" in skill && skill.action === "summarize" ? "chat-summarize" : undefined}
            onClick={() => {
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
    </div>
  );
}

export function TutorChat({ messages, generatedLinks, activities, isStreaming, backgroundTasks, modelProvider, onModelProviderChange, onSend, onSummarize, onOpenLink, onAddResourceToCanvas }: Props) {
  const [input, setInput] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const activeProvider = MODEL_OPTIONS.find((option) => option.provider === modelProvider) ?? MODEL_OPTIONS[0];
  const providerLabel = activeProvider.label;
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recognitionRef = useRef<{ stop: () => void } | null>(null);
  const waveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [attachments, setAttachments] = useState<Array<{ id: string; name: string; preview?: string }>>([]);
  const [listening, setListening] = useState(false);
  const allGeneratedLinks = [...messages.flatMap((message) => message.links), ...generatedLinks]
    .filter((link, index, links) => links.findIndex((item) => item.link_id === link.link_id) === index)
    .slice(-6);
  const activitiesByAnchor = new Map(
    activities
      .filter((activity) => activity.anchorMessageId && (activity.isActive || activity.trace.length > 0))
      .map((activity) => [activity.anchorMessageId, activity])
  );

  // Auto-scroll to bottom on mount and when messages change
  useEffect(() => {
    const el = messageListRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, activities]);


  // Live microphone waveform while listening — gives real-time "I'm recording" feedback.
  useEffect(() => {
    if (!listening) return;
    let audioCtx: AudioContext | null = null;
    let stream: MediaStream | null = null;
    let raf = 0;
    let cancelled = false;
    const AudioCtor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    navigator.mediaDevices?.getUserMedia({ audio: true })
      .then((mic) => {
        if (cancelled || !AudioCtor) { mic.getTracks().forEach((track) => track.stop()); return; }
        stream = mic;
        audioCtx = new AudioCtor();
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        audioCtx.createMediaStreamSource(mic).connect(analyser);
        const bins = analyser.frequencyBinCount;
        const data = new Uint8Array(bins);
        const draw = () => {
          const canvas = waveCanvasRef.current;
          if (canvas) {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const cw = canvas.clientWidth || 240;
            const ch = canvas.clientHeight || 32;
            if (canvas.width !== Math.round(cw * dpr)) { canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr); }
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

  const addFiles = (fileList: FileList | null) => {
    if (!fileList?.length) return;
    Array.from(fileList).forEach((file) => {
      const id = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
      if (file.type.startsWith("image/")) {
        // Data URL persists in the sent message (object URLs would be revoked).
        const reader = new FileReader();
        reader.onload = () => {
          const preview = typeof reader.result === "string" ? reader.result : undefined;
          setAttachments((current) => [...current, { id, name: file.name, preview }].slice(0, 6));
        };
        reader.readAsDataURL(file);
      } else {
        setAttachments((current) => [...current, { id, name: file.name }].slice(0, 6));
      }
    });
  };

  const removeAttachment = (id: string) => {
    setAttachments((current) => current.filter((item) => item.id !== id));
  };

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SpeechRecognition = (window as unknown as { SpeechRecognition?: new () => unknown; webkitSpeechRecognition?: new () => unknown }).SpeechRecognition
      ?? (window as unknown as { webkitSpeechRecognition?: new () => unknown }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      window.alert("当前浏览器不支持语音输入，请使用 Chrome 或 Edge。");
      return;
    }
    const recognition = new SpeechRecognition() as {
      lang: string; interimResults: boolean; continuous: boolean;
      onresult: (event: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void;
      onend: () => void; onerror: () => void; start: () => void; stop: () => void;
    };
    recognition.lang = "zh-CN";
    recognition.interimResults = true;
    recognition.continuous = false;
    const base = input;
    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) transcript += event.results[i][0].transcript;
      setInput((base ? `${base} ` : "") + transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  };

  const sendNow = async () => {
    const text = input.trim();
    if (!text && !attachments.length) return;
    const outgoing = attachments.map((item) => ({ name: item.name, preview: item.preview }));
    setInput("");
    setAttachments([]);
    await onSend(text, outgoing);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await sendNow();
  };
  return (
    <aside className="tutor-chat chat" data-testid="tutor-chat">
      <header className="chat-header chat-head">
        <div className="tutor-id">
          <div className="tutor-av"><img src="/brand/ai-tutor-avatar.png" alt="AI 学习导师" /></div>
          <div className="tutor-meta">
            <span className="eyebrow">Tutor Chat</span>
            <h1 className="nm">AI 学习导师</h1>
            <div className="role">Tutor Agent · Hermes 调度 · {providerLabel} 生成</div>
          </div>
        </div>
        <div className="tutor-header-actions">
          <button type="button" className="model-settings-btn" title="模型设置" aria-label="模型设置" onClick={() => setSettingsOpen((open) => !open)}>
            <Settings2 size={15} />
          </button>
          <div className="tutor-status"><span />在线</div>
        </div>
      </header>
      {settingsOpen ? (
        <section className="model-settings-panel" aria-label="模型设置">
          <div>
            <span>回答模型</span>
            <strong>{providerLabel}</strong>
          </div>
          <div className="provider-toggle" role="radiogroup" aria-label="回答模型">
            {MODEL_OPTIONS.map((option) => (
              <button
                key={option.provider}
                type="button"
                role="radio"
                aria-checked={option.provider === modelProvider}
                className={option.provider === modelProvider ? "active" : ""}
                onClick={() => onModelProviderChange(option.provider)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <small>{activeProvider.caption}</small>
          <div className="settings-actions" aria-label="更多操作">
            <button
              type="button"
              className="settings-action-btn"
              onClick={() => {
                setInput("请重新规划我的学习路径，并生成左侧互动资源");
                setSettingsOpen(false);
              }}
            >
              <Route size={15} />
              <span>重新规划路径</span>
            </button>
          </div>
        </section>
      ) : null}
      <div className="message-list chat-body" ref={messageListRef}>
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
        {/* Background Task Indicator — 后台任务进度条，不阻塞聊天 */}
        {backgroundTasks.filter(t => t.status === 'running').map(task => (
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
                  <div className="bg-task-fill" style={{ width: `${Math.round(task.progress * 100)}%` }} />
                </div>
              </div>
            </div>
          </motion.div>
        ))}
        {messages.map((message, idx) => {
          const isAssistant = message.role === "assistant";
          // retry resends the user message that preceded this assistant turn
          const precedingUser = isAssistant
            ? [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")
            : undefined;
          const isWelcome = message.id === "welcome";
          const agentActivity = activitiesByAnchor.get(message.id);
          return (
            <Fragment key={message.id}>
              <article key={message.id} className={`message msg ${message.role} ${isAssistant ? "tutor" : ""}`}>
                <div className="message-content">
                  <div className="message-text msg-bubble">
                    {message.attachments?.length ? (
                      <div className="msg-attachments">
                        {message.attachments.map((attachment, attachmentIndex) =>
                          attachment.preview ? (
                            <img key={attachmentIndex} src={attachment.preview} alt={attachment.name} className="msg-attachment-img" />
                          ) : (
                            <span key={attachmentIndex} className="msg-attachment-file"><Paperclip size={13} />{attachment.name}</span>
                          )
                        )}
                      </div>
                    ) : null}
                    {message.text ? <RichMessageContent text={message.text} onGenerate={onSend} /> : null}
                  </div>
                  {message.resources.length ? (
                    <div
                      className={`resource-cards ${message.resources.every((resource) => resource.type === "video") ? "resource-cards-video-grid" : ""}`}
                      data-testid="resource-cards"
                    >
                      {message.resources.map((resource) => (
                        <ResourceCard key={resource.resource_id} resource={resource} onAddResourceToCanvas={onAddResourceToCanvas} />
                      ))}
                    </div>
                  ) : null}
                  {message.links.length ? (
                    <div className="link-row">
                      {message.links.map((link) => (
                        <AppLinkChip key={link.link_id} link={link} onOpen={onOpenLink} />
                      ))}
                    </div>
                  ) : null}
                  {isAssistant && !isWelcome && message.text ? (
                    <MessageActions
                      text={message.text}
                      canRetry={!!precedingUser && !isStreaming}
                      onRetry={precedingUser ? () => onSend(precedingUser.text) : undefined}
                    />
                  ) : null}
                </div>
              </article>
              {agentActivity ? (
                <article key={`${message.id}-agent-activity`} className="message msg assistant tutor agent-activity-message agent-activity-inline" data-testid="agent-activity-turn">
                  <div className="message-content">
                    <AgentActivity trace={agentActivity.trace} isStreaming={agentActivity.isActive} />
                  </div>
                </article>
              ) : null}
            </Fragment>
          );
        })}
      </div>
      <SkillBar onSkill={(prompt) => setInput(prompt)} onSummarize={onSummarize} />
      <form className="composer" onSubmit={submit}>
        {attachments.length ? (
          <div className="composer-attachments">
            {attachments.map((item) => (
              <div key={item.id} className="composer-chip" title={item.name}>
                {item.preview ? <img src={item.preview} alt={item.name} /> : <Paperclip size={13} />}
                <span>{item.name}</span>
                <button type="button" onClick={() => removeAttachment(item.id)} aria-label="移除附件"><X size={12} /></button>
              </div>
            ))}
          </div>
        ) : null}
        {listening ? (
          <button type="button" className="composer-wave" onClick={toggleVoice} title="点击停止语音输入">
            <span className="composer-wave-dot" />
            <canvas ref={waveCanvasRef} className="composer-wave-canvas" />
            <span className="composer-wave-label">正在聆听…轻触停止</span>
          </button>
        ) : (
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                void sendNow();
              }
            }}
            aria-label="输入学习问题"
          />
        )}
        <div className="composer-toolbar">
          <div className="composer-tools">
            <button type="button" className="tool-btn" title="上传图片" onClick={() => imageInputRef.current?.click()}>
              <ImagePlus size={18} />
            </button>
            <button type="button" className="tool-btn" title="上传文件" onClick={() => fileInputRef.current?.click()}>
              <Paperclip size={18} />
            </button>
            <button
              type="button"
              className={`tool-btn ${listening ? "is-recording" : ""}`}
              title={listening ? "停止语音输入" : "语音输入"}
              onClick={toggleVoice}
            >
              <Mic size={18} />
            </button>
          </div>
          <button
            type="submit"
            data-testid="chat-send"
            disabled={isStreaming || (!input.trim() && !attachments.length)}
            title="发送"
            className="composer-send"
          >
            <Send size={17} />
          </button>
        </div>
        <input ref={imageInputRef} type="file" accept="image/*" multiple hidden onChange={(event) => { addFiles(event.target.files); event.target.value = ""; }} />
        <input ref={fileInputRef} type="file" multiple hidden onChange={(event) => { addFiles(event.target.files); event.target.value = ""; }} />
      </form>
    </aside>
  );
}
