import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { CanvasApp, DashboardSnapshot } from "@learnforge/app-protocol";
import { Activity, BookOpen, Boxes, Brain, CheckCircle2, Code2, ExternalLink, FileImage, Film, Gauge, GitBranch, Image, Maximize2, NotebookPen, Presentation, RotateCcw, Route, Search, Tags, UserRound, ZoomIn, ZoomOut } from "lucide-react";
import { fetchResources, postAppEvent, postResourceFeedback, submitQuiz, type SessionContext } from "../../lib/api/client";
import { gradientDescent, isLearningRateUnstable, workEnergy, type WorkEnergyInput } from "./calculations";
import { CustomHtmlAppRenderer } from "../custom-html-app/CustomHtmlAppRenderer";
import { bilibiliEmbedUrl, extractBvidFromResource, type BilibiliEmbedOptions } from "../../lib/video/bilibili";

type Props = {
  app: CanvasApp;
  dashboard?: DashboardSnapshot;
  isFullscreen?: boolean;
  onEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void | Promise<void>;
  onFocusApp: (appId: string) => void;
  onDashboardUpdate?: (dashboard: DashboardSnapshot) => void;
  sessionContext: SessionContext;
};

const iconMap: Partial<Record<CanvasApp["app_type"], typeof Boxes>> = {
  "profile.dashboard": UserRound,
  "learning.path": Route,
  "knowledge.graph": GitBranch,
  "mindmap.concept": Brain,
  "quiz.practice": CheckCircle2,
  "physics.work_energy_demo": Activity,
  "math.gradient_descent_demo": Gauge,
  "code.lab": Code2,
  "notes.session": NotebookPen,
  "dashboard.learning": Boxes,
  "ppt.preview": Presentation,
  "image.explanation": FileImage,
  "video.script": Film,
  "video.player": Film,
  "resource.center": BookOpen,
  "resource.folder": Boxes,
  "custom.html": Image
};

const appTypeLabels: Partial<Record<CanvasApp["app_type"], string>> = {
  "profile.dashboard": "学习画像",
  "learning.path": "学习路径",
  "knowledge.graph": "知识图谱",
  "mindmap.concept": "概念图",
  "quiz.practice": "练习题",
  "physics.work_energy_demo": "物理演示",
  "math.gradient_descent_demo": "数学演示",
  "code.lab": "代码实验",
  "notes.session": "学习笔记",
  "dashboard.learning": "学习仪表盘",
  "ppt.preview": "课件预览",
  "image.explanation": "教学图解",
  "video.script": "视频脚本",
  "video.player": "教学视频",
  "resource.center": "学习资源",
  "resource.folder": "资源文件夹",
  "custom.html": "互动演示"
};

function customHtmlIsPptDeck(app: CanvasApp): boolean {
  if (app.app_type !== "custom.html") return false;
  const cap = String((app.source as Record<string, unknown>)?.capability ?? app.group_id ?? "").toLowerCase();
  const deckKind = String(app.payload?.deck_kind ?? app.payload?.deckKind ?? app.payload?.layout ?? "").toLowerCase();
  const html = String(app.payload?.html ?? "");
  return cap.includes("ppt") || deckKind.includes("ppt") || deckKind.includes("deck") || /guizang|web ppt|horizontal[- ]swipe|slide deck/i.test(html);
}

export function NativeAppRenderer({ app, dashboard, isFullscreen, onEvent, onFocusApp, onDashboardUpdate, sessionContext }: Props) {
  const isPptDeck = customHtmlIsPptDeck(app);
  const Icon = isPptDeck ? Presentation : iconMap[app.app_type] ?? Boxes;
  const appTypeLabel = isPptDeck ? "网页 PPT" : appTypeLabels[app.app_type] ?? "学习应用";
  const bodyClassName = [
    "native-app-body",
    app.app_type === "custom.html" ? "native-app-body-custom" : "",
    app.app_type === "image.explanation" ? "native-app-body-image" : ""
  ].filter(Boolean).join(" ");
  return (
    <div className={bodyClassName}>
      <div className={`app-type-strip ${app.app_type === "custom.html" ? "app-type-strip-custom" : ""}`}>
        <Icon size={15} />
        <span>{appTypeLabel}</span>
      </div>
      {app.app_type === "profile.dashboard" ? <ProfileDashboard dashboard={dashboard} isFullscreen={isFullscreen} /> : null}
      {app.app_type === "learning.path" ? <LearningPathApp dashboard={dashboard} onFocusApp={onFocusApp} /> : null}
      {app.app_type === "knowledge.graph" || app.app_type === "mindmap.concept" ? <KnowledgeGraphApp app={app} /> : null}
      {app.app_type === "physics.work_energy_demo" ? <WorkEnergyDemoApp app={app} onEvent={onEvent} /> : null}
      {app.app_type === "math.gradient_descent_demo" ? <GradientDescentDemoApp app={app} onEvent={onEvent} sessionContext={sessionContext} /> : null}
      {app.app_type === "quiz.practice" ? <QuizPracticeApp app={app} onEvent={onEvent} sessionContext={sessionContext} /> : null}
      {app.app_type === "code.lab" ? <CodeLabApp app={app} /> : null}
      {app.app_type === "notes.session" ? <NotesApp app={app} onEvent={onEvent} /> : null}
      {app.app_type === "dashboard.learning" ? <LearningDashboardApp dashboard={dashboard} isFullscreen={isFullscreen} /> : null}
      {app.app_type === "ppt.preview" ? <PPTPreviewApp app={app} /> : null}
      {app.app_type === "image.explanation" ? <ImageExplanationApp app={app} onEvent={onEvent} /> : null}
      {app.app_type === "video.script" ? <VideoScriptApp app={app} /> : null}
      {app.app_type === "video.player" ? <VideoPlayerApp app={app} isFullscreen={isFullscreen} /> : null}
      {app.app_type === "resource.center" ? <ResourceCenterApp app={app} isFullscreen={isFullscreen} onDashboardUpdate={onDashboardUpdate} sessionContext={sessionContext} /> : null}
      {app.app_type === "custom.html" ? <CustomHtmlAppRenderer code={String(app.payload.html ?? "")} theme="dark" mode="canvas" forceDeckBridge={isPptDeck} /> : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CoverageRing({ percent, size = 64 }: { percent: number; size?: number }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const dash = (percent / 100) * c;
  return (
    <div className="coverage-ring" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} className="ring-track" />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          className="ring-fill"
          strokeDasharray={`${dash} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="ring-label">{percent}%</span>
    </div>
  );
}

function ProfileDashboard({ dashboard, isFullscreen }: { dashboard?: DashboardSnapshot; isFullscreen?: boolean }) {
  const profile = dashboard?.profile ?? {};
  const evidence = dashboard?.memory_evidence ?? [];
  const summaryKeys = ["major", "grade", "knowledge_foundation", "learning_goal", "cognitive_style", "learning_pace"];
  const tagKeys = ["preferred_resources", "interests", "weak_points"];
  const allKeys = [...summaryKeys, ...tagKeys, "mastery_map", "subjects", "subject_confidence"];
  const filled = allKeys.filter((key) => hasProfileValue(profile[key])).length;
  const coverage = Math.round((filled / allKeys.length) * 100);
  const profileEvidence = evidence.filter((item) => item.memory_type === "profile");
  const missing = allKeys.filter((key) => !hasProfileValue(profile[key])).slice(0, 4);
  const subjectConfidence = profile.subject_confidence && typeof profile.subject_confidence === "object" ? (profile.subject_confidence as Record<string, unknown>) : {};
  const subjects = Object.entries(subjectConfidence).sort((a, b) => Number(b[1]) - Number(a[1]));

  return (
    <div className={`profile-panel ${isFullscreen ? "is-fullscreen" : ""}`} data-testid="profile-dashboard">
      {/* Hero header: avatar + identity + coverage ring */}
      <div className="profile-hero">
        <div className="profile-avatar"><UserRound size={isFullscreen ? 30 : 24} /></div>
        <div className="profile-id">
          <strong>{formatProfileValue(profile.major) === "待补充" ? "学习者画像" : String(formatProfileValue(profile.major))}</strong>
          <span>{[profile.grade, profile.learning_goal].filter(hasProfileValue).map((v) => formatProfileValue(v)).join(" · ") || "画像构建中"}</span>
        </div>
        <CoverageRing percent={coverage} size={isFullscreen ? 76 : 58} />
      </div>

      {/* Quick stat chips */}
      <div className="profile-stats">
        <div className="pstat"><span>画像覆盖</span><strong>{coverage}%</strong></div>
        <div className="pstat"><span>记忆证据链</span><strong>{profileEvidence.length}</strong></div>
        <div className="pstat"><span>薄弱点</span><strong>{(dashboard?.weak_points?.length ?? 0)}</strong></div>
      </div>

      {/* Subject confidence bars */}
      {subjects.length ? (
        <div className="profile-section">
          <h4>科目掌握置信度</h4>
          <div className="subject-map" data-testid="subject-map">
            {subjects.slice(0, isFullscreen ? 12 : 4).map(([subject, score]) => (
              <label key={subject}>
                <span>{subject}</span>
                <i style={{ width: `${Math.max(8, Number(score) * 100)}%` }} />
                <small>{Math.round(Number(score) * 100)}%</small>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {/* Tag groups: preferences / interests / weak points */}
      <div className="profile-section">
        <h4>偏好与特征</h4>
        <div className="profile-tags">
          {tagKeys.map((key) => {
            const arr = Array.isArray(profile[key]) ? (profile[key] as unknown[]) : [];
            if (!arr.length) return null;
            return (
              <div className="tag-group" key={key}>
                <em>{fieldLabel(key)}</em>
                <div className="chip-row">
                  {arr.slice(0, isFullscreen ? 12 : 4).map((v, i) => (
                    <span key={i} className={`profile-chip ${key === "weak_points" ? "weak" : ""}`}>{String(v)}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dimension cards */}
      <div className="profile-section">
        <h4>画像维度</h4>
        <div className="profile-grid">
          {summaryKeys.map((key) => (
            <div className="profile-field" key={key}>
              <span>{fieldLabel(key)}</span>
              <strong>{formatProfileValue(profile[key])}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* Coldstart hint */}
      <div className="profile-coldstart" data-testid="profile-missing-fields">
        <span>待补齐</span>
        <strong>{missing.length ? missing.map(fieldLabel).join(" / ") : "当前画像足够用于个性化建议"}</strong>
      </div>

      {/* Fullscreen-only: profile memory evidence chain */}
      {isFullscreen && profileEvidence.length ? (
        <div className="profile-section">
          <h4>画像记忆证据链 · EduMem0</h4>
          <div className="evidence-chain">
            {profileEvidence.slice(0, 6).map((item) => (
              <article key={item.id}>
                <header className="evidence-card-head">
                  <strong>{memoryTypeLabel(item.memory_type)}</strong>
                  <span className="confidence-pill">{Math.round((item.effective_confidence ?? item.confidence) * 100)}%</span>
                </header>
                <p>{cleanEvidenceContent(item.content)}</p>
                <footer className="evidence-meta">
                  <span>{evidenceTypeLabel(item.evidence_type)}</span>
                  <span>{sourceAgentLabel(item)}</span>
                </footer>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function hasProfileValue(value: unknown) {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === "object") return Object.keys(value).length > 0;
  return value !== undefined && value !== null && String(value).trim().length > 0;
}

function formatProfileValue(value: unknown) {
  if (Array.isArray(value)) return value.length ? value.join(" / ") : "待补充";
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key} ${typeof item === "number" ? Math.round(item * 100) + "%" : String(item)}`)
      .join(" / ");
  }
  return String(value ?? "待补充");
}

function fieldLabel(key: string) {
  return (
    {
      major: "专业",
      grade: "年级",
      knowledge_foundation: "基础",
      learning_goal: "目标",
      cognitive_style: "认知风格",
      learning_pace: "节奏",
      preferred_resources: "资源偏好",
      weak_points: "薄弱点",
      interests: "兴趣",
      mastery_map: "掌握图谱",
      subjects: "科目范围",
      subject_confidence: "科目置信"
    }[key] ?? key
  );
}

function LearningPathApp({ dashboard, onFocusApp }: { dashboard?: DashboardSnapshot; onFocusApp: (appId: string) => void }) {
  const stages = [
    { id: "stage-math", title: "补齐数学推导基础", appId: "app-gradient", progress: 38, status: "进行中" },
    { id: "stage-opt", title: "梯度下降与学习率", appId: "app-quiz", progress: 42, status: "推荐" },
    { id: "stage-nn", title: "神经网络训练闭环", appId: "app-knowledge", progress: 25, status: "锁定" }
  ];
  return (
    <div className="path-list" data-testid="learning-path-app">
      <div className="path-progress">
        <span>总进度</span>
        <strong>{Math.round((dashboard?.path_progress ?? 0.32) * 100)}%</strong>
      </div>
      {stages.map((stage) => (
        <button
          className="path-stage"
          key={stage.id}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => onFocusApp(stage.appId)}
          data-testid={`path-stage-${stage.id}`}
        >
          <span>{stage.title}</span>
          <small>{stage.status} · {stage.progress}%</small>
        </button>
      ))}
    </div>
  );
}

function KnowledgeGraphApp({ app }: { app: CanvasApp }) {
  const payloadNodes = Array.isArray(app.payload.nodes) ? app.payload.nodes as Array<Record<string, unknown>> : [];
  const nodes = payloadNodes.length ? payloadNodes.map((node, index) => ({
    id: String(node.id ?? `node-${index}`),
    label: String(node.label ?? node.title ?? node.name ?? `节点 ${index + 1}`),
    x: Number(node.x ?? 16 + (index % 3) * 34),
    y: Number(node.y ?? 24 + Math.floor(index / 3) * 30)
  })) : [
    { id: "math", label: "数学推导", x: 12, y: 52 },
    { id: "opt", label: "梯度下降", x: 42, y: 24 },
    { id: "nn", label: "神经网络", x: 72, y: 48 },
    { id: "safe", label: "验证安全", x: 54, y: 76 }
  ];
  const payloadEdges = Array.isArray(app.payload.edges) ? app.payload.edges as unknown[] : [];
  const edges = payloadEdges.length ? payloadEdges : [["math", "opt"], ["opt", "nn"], ["opt", "safe"]];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  return (
    <div className="knowledge-map" data-testid="knowledge-graph-app">
      <svg viewBox="0 0 100 100" role="img" aria-label="知识图谱">
        {edges.map((edge, index) => {
          const pair = Array.isArray(edge) ? edge : [String((edge as Record<string, unknown>).source ?? ""), String((edge as Record<string, unknown>).target ?? "")];
          const source = byId.get(String(pair[0]));
          const target = byId.get(String(pair[1]));
          return source && target ? <path key={index} d={`M${source.x} ${source.y} L${target.x} ${target.y}`} /> : null;
        })}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="8" />
            <text x={node.x} y={node.y + 17} textAnchor="middle">{node.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function WorkEnergyDemoApp({ app, onEvent }: { app: CanvasApp; onEvent: Props["onEvent"] }) {
  const [values, setValues] = useState<WorkEnergyInput>({
    mass: Number(app.payload.mass ?? 2),
    initialVelocity: Number(app.payload.initialVelocity ?? 3),
    finalVelocity: Number(app.payload.finalVelocity ?? 7),
    force: Number(app.payload.force ?? 8),
    displacement: Number(app.payload.displacement ?? 5)
  });
  const result = useMemo(() => workEnergy(values), [values]);
  const update = (key: keyof WorkEnergyInput, value: number) => {
    const next = { ...values, [key]: value };
    setValues(next);
    onEvent(app.app_id, "parameter_change", next);
  };
  const cartX = Math.min(86, 12 + values.finalVelocity * 8);
  return (
    <div className="work-energy" data-testid="work-energy-demo">
      <div className="cart-track">
        <div className="cart" style={{ left: `${cartX}%` }} />
        <span>W = F · s，ΔK = 1/2mv₂² - 1/2mv₁²</span>
      </div>
      <div className="control-grid">
        <Slider label="质量 m" min={1} max={8} step={0.5} value={values.mass} onChange={(value) => update("mass", value)} />
        <Slider label="初速度 v₁" min={0} max={10} step={0.5} value={values.initialVelocity} onChange={(value) => update("initialVelocity", value)} />
        <Slider label="末速度 v₂" min={0} max={12} step={0.5} value={values.finalVelocity} onChange={(value) => update("finalVelocity", value)} />
        <Slider label="力 F" min={1} max={20} step={1} value={values.force} onChange={(value) => update("force", value)} />
        <Slider label="位移 s" min={1} max={12} step={1} value={values.displacement} onChange={(value) => update("displacement", value)} />
      </div>
      <div className="metric-row">
        <Metric label="做功 W" value={result.work.toFixed(1)} />
        <Metric label="初动能" value={result.initialKinetic.toFixed(1)} />
        <Metric label="末动能" value={result.finalKinetic.toFixed(1)} />
        <Metric label="ΔK" value={result.deltaKinetic.toFixed(1)} />
      </div>
      <button className="secondary-action" onClick={() => onEvent(app.app_id, "tutor.explain", { values, result })}>让导师解释当前数值</button>
    </div>
  );
}

function Slider({ label, min, max, step, value, onChange }: { label: string; min: number; max: number; step: number; value: number; onChange: (value: number) => void }) {
  return (
    <label className="slider-row">
      <span>{label}</span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
      <strong>{value}</strong>
    </label>
  );
}

function GradientDescentDemoApp({ app, onEvent, sessionContext }: { app: CanvasApp; onEvent: Props["onEvent"]; sessionContext: SessionContext }) {
  const [learningRate, setLearningRate] = useState(Number(app.payload.learningRate ?? 0.18));
  const [initialPoint, setInitialPoint] = useState(Number(app.payload.initialPoint ?? 4));
  const [iterations, setIterations] = useState(Number(app.payload.iterations ?? 12));
  const points = useMemo(() => gradientDescent(learningRate, initialPoint, iterations), [learningRate, initialPoint, iterations]);
  useEffect(() => {
    postAppEvent(app.app_id, "parameter_change", { learningRate, initialPoint, iterations, knowledge_point_id: "kp-optimization" }, sessionContext).catch(() => undefined);
  }, [app.app_id, learningRate, initialPoint, iterations, sessionContext]);
  const maxLoss = Math.max(...points.map((point) => point.loss), 1);
  return (
    <div className="gradient-demo" data-testid="gradient-demo">
      <div className="control-grid">
        <Slider label="学习率" min={0.05} max={1.4} step={0.05} value={learningRate} onChange={setLearningRate} />
        <Slider label="初始点" min={-6} max={6} step={0.5} value={initialPoint} onChange={setInitialPoint} />
        <Slider label="迭代数" min={4} max={24} step={1} value={iterations} onChange={setIterations} />
      </div>
      <div className="loss-chart" aria-label="损失曲线">
        {points.map((point) => (
          <i key={point.iteration} style={{ height: `${Math.max(4, (point.loss / maxLoss) * 96)}%` }} title={`step ${point.iteration}: ${point.loss.toFixed(2)}`} />
        ))}
      </div>
      <p className={isLearningRateUnstable(learningRate) ? "warning-text" : "ok-text"}>
        {isLearningRateUnstable(learningRate) ? "学习率过大：轨迹可能震荡或发散。" : "当前学习率较稳定，点会逐步靠近低谷。"}
      </p>
      <table className="mini-table">
        <tbody>
          {points.slice(0, 5).map((point) => (
            <tr key={point.iteration}>
              <td>{point.iteration}</td>
              <td>x={point.x.toFixed(3)}</td>
              <td>L={point.loss.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="secondary-action" onClick={() => onEvent(app.app_id, "tutor.explain", { learningRate, points: points.slice(0, 5) })}>解释学习率行为</button>
    </div>
  );
}

function QuizPracticeApp({ app, onEvent, sessionContext }: { app: CanvasApp; onEvent: Props["onEvent"]; sessionContext: SessionContext }) {
  const questions = Array.isArray(app.payload.questions) ? app.payload.questions as Array<Record<string, unknown>> : [];
  const question = questions[0];
  const options = Array.isArray(question?.options) ? question.options.map(String) : ["稳定加速", "震荡或发散", "自动停止", "无需损失函数"];
  const [answer, setAnswer] = useState(options[0] ?? "");
  const [feedback, setFeedback] = useState<string>("");
  const [scoreState, setScoreState] = useState<"idle" | "correct" | "wrong">("idle");
  const questionId = String(question?.question_id ?? app.payload.question_id ?? "quiz-q-gradient-lr");
  const submit = async () => {
    if (question?.answer !== undefined) {
      const isCorrect = String(answer) === String(question.answer);
      setScoreState(isCorrect ? "correct" : "wrong");
      setFeedback(String(question.explanation ?? (isCorrect ? "回答正确。" : "请回到相关资源复习。")));
      onEvent(app.app_id, "quiz.submit", { questionId, answer, isCorrect });
      return;
    }
    const data = await submitQuiz(questionId, answer, sessionContext);
    const evaluation = data as { evaluation: { summary: string; payload: { submission: { is_correct: boolean; evaluation: { explanation: string } } } } };
    const isCorrect = evaluation.evaluation.payload.submission.is_correct;
    setScoreState(isCorrect ? "correct" : "wrong");
    setFeedback(evaluation.evaluation.payload.submission.evaluation.explanation);
    onEvent(app.app_id, "quiz.submit", { questionId, answer, isCorrect });
  };
  return (
    <div className="quiz-app" data-testid="quiz-practice-app">
      <p className="question">{String(question?.prompt ?? "当梯度下降的学习率过大时，最可能出现什么现象？")}</p>
      <div className="option-list">
        {options.map((option) => (
          <label key={option} className={answer === option ? "selected-option" : ""}>
            <input type="radio" name={`quiz-${app.app_id}`} checked={answer === option} onChange={() => setAnswer(option)} />
            {option}
          </label>
        ))}
      </div>
      <button className="primary-action" data-testid="quiz-submit" onClick={submit}>提交并更新仪表盘</button>
      {feedback ? <div className={`quiz-feedback ${scoreState}`} data-testid="quiz-feedback">{scoreState === "correct" ? "答对了" : "需要复习"}：{feedback}</div> : null}
    </div>
  );
}

function CodeLabApp({ app }: { app: CanvasApp }) {
  const starterCode = String(app.payload.starter_code ?? app.payload.starterCode ?? "lr = 0.18\nx = 4.0\nfor step in range(8):\n    grad = 2 * x\n    x = x - lr * grad\n    print(step, round(x, 3))");
  const goal = String(app.payload.goal ?? "用 Python 循环理解梯度下降。");
  const expected = String(app.payload.expected_output ?? app.payload.expectedOutput ?? "后端不执行任意代码；这里展示 starter code、预期输出和测试点。");
  return (
    <div className="code-lab" data-testid="code-lab-app">
      <p>目标：{goal}</p>
      <pre>{starterCode}</pre>
      <small>{expected}</small>
    </div>
  );
}

function renderMarkdown(text: string): string {
  // Simple but effective markdown to HTML renderer
  let html = text
    // Escape HTML entities
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // Code blocks (```...```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang, code) =>
    `<pre><code class="language-${lang || 'plain'}">${code.trim()}</code></pre>`
  );
  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  html = html.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
  // Strikethrough
  html = html.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
  // Headers
  html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // Unordered lists
  html = html.replace(/^[-\*] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  // Horizontal rules
  html = html.replace(/^---$/gm, "<hr>");
  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");
  // Paragraphs (double newlines)
  html = html.replace(/\n\n/g, "</p><p>");
  // Remaining single newlines → <br>
  html = html.replace(/\n/g, "<br>");
  // Wrap in paragraph if not already
  if (!html.startsWith("<")) html = `<p>${html}</p>`;
  return html;
}

function NotesApp({ app, onEvent }: { app: CanvasApp; onEvent: Props["onEvent"] }) {
  const notePayload = app.payload.content ?? app.payload.summary ?? app.payload;
  const initial = typeof notePayload === "string" ? notePayload : JSON.stringify(notePayload, null, 2);
  const [content, setContent] = useState(initial);
  const [editing, setEditing] = useState(false);
  const hasMarkdown = /^#|\[.+\]\(.+\)|\*\*|```|^- |^\d+\. /m.test(initial);
  const [viewMode, setViewMode] = useState(hasMarkdown);

  return (
    <div className="notes-app" data-testid="notes-app">
      {app.payload.topic ? <strong className="note-topic">主题：{String(app.payload.topic)}</strong> : null}
      <div className="notes-toolbar">
        <button
          className={`notes-mode-btn ${!editing && viewMode ? "active" : ""}`}
          onClick={() => { setEditing(false); setViewMode(true); }}
        >
          预览
        </button>
        <button
          className={`notes-mode-btn ${editing ? "active" : ""}`}
          onClick={() => setEditing(true)}
        >
          编辑
        </button>
      </div>
      {editing ? (
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          data-testid="notes-textarea"
        />
      ) : (
        <div
          className="notes-rendered markdown-body"
          data-testid="notes-rendered"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
      )}
      <button className="secondary-action" onClick={() => { onEvent(app.app_id, "notes.save", { content }); setEditing(false); setViewMode(true); }}>保存笔记</button>
    </div>
  );
}

const RUN_LABELS: Record<string, string> = {
  tutor_turn: "导师对话",
  hermes_custom_infographic: "信息图生成",
  hermes_interactive_demo: "交互演示生成",
  resource_bundle: "资源包生成",
  notes_summary: "笔记总结",
  work_energy_demo: "动能演示",
  quiz_evaluation: "测验评估",
};

function LearningDashboardApp({ dashboard, isFullscreen }: { dashboard?: DashboardSnapshot; isFullscreen?: boolean }) {
  const evidence = dashboard?.memory_evidence ?? [];
  const mastery = dashboard?.mastery ?? {};
  const masteryEntries = Object.entries(mastery);
  const avgMastery = masteryEntries.length ? Math.round((masteryEntries.reduce((s, [, v]) => s + Number(v), 0) / masteryEntries.length) * 100) : 0;
  const recommendations = dashboard?.recommendations ?? [];
  const recentRuns = dashboard?.recent_runs ?? [];
  const weakPoints = dashboard?.weak_points ?? [];

  const masteryColor = (v: number) => (v >= 0.7 ? "var(--st-done)" : v >= 0.4 ? "var(--accent-blue)" : "var(--st-weak)");

  return (
    <div className={`learning-dashboard ${isFullscreen ? "is-fullscreen" : ""}`} data-testid="learning-dashboard-app">
      {/* KPI cards */}
      <div className="dash-kpis">
        <div className="kpi"><span>路径进度</span><strong>{Math.round((dashboard?.path_progress ?? 0) * 100)}%</strong><i className="kpi-bar"><b style={{ width: `${Math.round((dashboard?.path_progress ?? 0) * 100)}%` }} /></i></div>
        <div className="kpi"><span>平均掌握</span><strong>{avgMastery}%</strong><i className="kpi-bar"><b style={{ width: `${avgMastery}%`, background: masteryColor(avgMastery / 100) }} /></i></div>
        <div className="kpi"><span>记忆证据</span><strong>{evidence.length}</strong></div>
        <div className="kpi"><span>薄弱点</span><strong>{weakPoints.length}</strong></div>
      </div>

      {/* Mastery map */}
      {masteryEntries.length ? (
        <div className="dash-section">
          <h4>知识点掌握度</h4>
          <div className="mastery-bars">
            {masteryEntries.slice(0, isFullscreen ? 12 : 4).map(([key, value]) => (
              <label key={key}>
                <span>{key}</span>
                <i><b style={{ width: `${Number(value) * 100}%`, background: masteryColor(Number(value)) }} /></i>
                <small>{Math.round(Number(value) * 100)}%</small>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {/* Weak points chips */}
      {weakPoints.length ? (
        <div className="dash-section">
          <h4>当前薄弱点</h4>
          <div className="chip-row">
            {weakPoints.map((w, i) => <span key={i} className="profile-chip weak">{w}</span>)}
          </div>
        </div>
      ) : null}

      {/* Recommendations from Recommender Agent */}
      {recommendations.length ? (
        <div className="dash-section">
          <h4>智能推荐 · Recommender</h4>
          <div className="rec-list">
            {recommendations.slice(0, isFullscreen ? 6 : 2).map((rec, i) => (
              <article key={i} className="rec-card">
                <div className="rec-top">
                  <strong>{String(rec.title ?? "推荐资源")}</strong>
                  {typeof rec.score === "number" ? <span className="rec-score">{Math.round(Number(rec.score) * 100)}</span> : null}
                </div>
                <p>{String(rec.reason ?? "")}</p>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {/* Recent Agent runs — Hermes orchestration trace */}
      {recentRuns.length ? (
        <div className="dash-section">
          <h4>最近 Agent 运行 · Hermes</h4>
          <div className="run-timeline">
            {recentRuns.slice(0, isFullscreen ? 8 : 3).map((run, i) => {
              const status = String(run.status ?? "");
              const taskType = String(run.task_type ?? "");
              return (
                <div className={`run-item run-${status}`} key={String(run.run_id ?? i)}>
                  <span className="run-dot" />
                  <span className="run-name">{RUN_LABELS[taskType] ?? taskType}</span>
                  <span className="run-status">{status === "completed" ? "完成" : status === "failed" ? "失败" : status === "running" ? "运行中" : status}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Memory evidence chain — EduMem0 */}
      <div className="dash-section">
        <h4>记忆证据链 · EduMem0</h4>
        <div className="evidence-chain" data-testid="memory-evidence">
          {evidence.slice(0, isFullscreen ? 10 : 3).map((item) => (
            <article key={item.id} data-testid={`memory-evidence-${item.memory_type}`}>
              <header className="evidence-card-head">
                <strong>{memoryTypeLabel(item.memory_type)}</strong>
                <span className="confidence-pill">{Math.round((item.effective_confidence ?? item.confidence) * 100)}%</span>
              </header>
              <p>{item.content}</p>
              <footer className="evidence-meta">
                <span>{evidenceTypeLabel(item.evidence_type)}</span>
                <span>{sourceAgentLabel(item)}</span>
                {isFullscreen ? <span>{item.decayed ? "已淡化" : "较新"}</span> : null}
              </footer>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

const MEMORY_TYPE_LABELS: Record<string, string> = {
  profile: "学习画像",
  spatial_layout: "画布布局",
  app_interaction: "App 互动",
  session_notes: "学习笔记",
  mastery: "知识掌握",
  preference: "学习偏好",
  resource_preference: "资源偏好",
  misconception: "易错点",
  learning_path: "学习路径",
  learning_event: "学习事件",
  agent_state: "Agent 状态",
  resource_feedback: "资源反馈",
  session_summary: "会话总结",
  tutor_pedagogy: "教学策略",
};

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  spatial_layout: "画布操作",
  app_interaction: "App 操作",
  notes_app: "笔记",
  conversation: "对话",
  quiz: "练习",
  chat: "聊天记录",
  resource_feedback: "资源反馈",
  teacher_confirmed: "教师确认",
  system_inferred: "系统推断",
  verifier_result: "验证结果",
};

const SOURCE_AGENT_LABELS: Record<string, string> = {
  memory_agent: "记忆代理",
  notes_skill: "笔记技能",
  profile_agent: "画像代理",
  orchestrator_agent: "编排代理",
  tutor_agent: "导师代理",
  verifier_agent: "校验代理",
  system: "系统",
  backend: "后端",
};

function cleanEvidenceContent(raw: string): string {
  // Trim excessively long content and strip JSON artifact tails
  let text = raw.trim();
  // Remove trailing JSON fragments (e.g., '{"knowledge_point_id": ...')
  text = text.replace(/\s*\{[\"'][\w_]+[\"']:\s*[\"'][^\"']*[\"'].*$/g, "");
  // Translate common internal identifiers to Chinese
  text = text.replace(/\bknowledge_point_id\b/g, "知识点");
  text = text.replace(/\bmental_model\b/g, "心智模型");
  text = text.replace(/\bconversation_summary\b/g, "对话摘要");
  text = text.replace(/\bconfidence_policy\b/g, "置信度策略");
  text = text.replace(/\bmastery_level\b/g, "掌握程度");
  // Truncate at reasonable length
  if (text.length > 280) text = text.slice(0, 280) + "…";
  return text || "证据记录";
}

function memoryTypeLabel(type: string) {
  return MEMORY_TYPE_LABELS[type] ?? type;
}

function evidenceTypeLabel(type: string) {
  return EVIDENCE_TYPE_LABELS[type] ?? type;
}

function sourceAgentLabel(item: { source_agent?: string; source_event_id?: string }) {
  const raw = sourceAgent(item);
  return SOURCE_AGENT_LABELS[raw] ?? "系统";
}

function sourceAgent(item: { source_agent?: string; source_event_id?: string }) {
  return item.source_agent ?? item.source_event_id ?? "system";
}

function PPTPreviewApp({ app }: { app: CanvasApp }) {
  const slides = Array.isArray(app.payload.slides) ? app.payload.slides as Array<Record<string, unknown>> : [];
  const titles = slides.length ? slides.map((slide) => String(slide.title ?? "未命名页")) : ["问题引入", "核心概念", "互动任务"];
  return (
    <div className="preview-stack" data-testid="ppt-preview-app">
      {titles.map((title, index) => (
        <article key={`${title}-${index}`}><span>{index + 1}</span><strong>{title}</strong><small>{String(slides[index]?.speaker_notes ?? "含讲稿与来源引用")}</small></article>
      ))}
      <button className="secondary-action" title="本地未配置导出服务，预览可用" disabled>导出待连接</button>
    </div>
  );
}

function ImageExplanationApp({ app, onEvent }: { app: CanvasApp; onEvent: Props["onEvent"] }) {
  const [status, setStatus] = useState("");
  const [scale, setScale] = useState(1);
  const [showLabels, setShowLabels] = useState(false);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ pointerId: number; startX: number; startY: number; scrollLeft: number; scrollTop: number } | null>(null);
  const imageUrl = typeof app.payload.image_url === "string" ? app.payload.image_url : "";
  const imageError = typeof app.payload.image_error === "string" ? app.payload.image_error : "";
  const provider = String(app.payload.provider_alias ?? app.payload.provider ?? "gemini").toLowerCase();
  const providerLabel = provider.includes("banana") ? "信息图" : "教学图解";
  const visualBrief = String(app.payload.visual_brief ?? app.payload.teaching_goal ?? app.title);
  const labels = Array.isArray(app.payload.overlay_labels) ? app.payload.overlay_labels as Array<Record<string, unknown>> : [
    { text: "概念入口", x: 0.18, y: 0.22 },
    { text: "关键公式", x: 0.58, y: 0.42 },
    { text: "错误提醒", x: 0.72, y: 0.76 }
  ];
  const generate = async () => {
    setStatus(`${providerLabel}生成中...`);
    await onEvent(app.app_id, "image.generate", {
      topic: app.payload.topic ?? app.title,
      teaching_goal: visualBrief,
      provider_alias: provider
    });
    setStatus("图片生成请求已完成");
  };
  const centerScroller = () => {
    window.requestAnimationFrame(() => {
      const scroller = scrollerRef.current;
      if (!scroller) return;
      scroller.scrollLeft = Math.max(0, (scroller.scrollWidth - scroller.clientWidth) / 2);
      scroller.scrollTop = Math.max(0, (scroller.scrollHeight - scroller.clientHeight) / 2);
    });
  };
  const resetView = () => {
    setScale(1);
    centerScroller();
  };
  const zoom = (delta: number) => {
    const scroller = scrollerRef.current;
    const centerX = scroller ? (scroller.scrollLeft + scroller.clientWidth / 2) / Math.max(1, scroller.scrollWidth) : 0.5;
    const centerY = scroller ? (scroller.scrollTop + scroller.clientHeight / 2) / Math.max(1, scroller.scrollHeight) : 0.5;
    setScale((value) => Math.max(1, Math.min(4, Number((value + delta).toFixed(2)))));
    window.requestAnimationFrame(() => {
      const nextScroller = scrollerRef.current;
      if (!nextScroller) return;
      nextScroller.scrollLeft = nextScroller.scrollWidth * centerX - nextScroller.clientWidth / 2;
      nextScroller.scrollTop = nextScroller.scrollHeight * centerY - nextScroller.clientHeight / 2;
    });
  };
  return (
    <div className={`image-explainer ${imageUrl ? "has-generated-image" : ""}`} data-testid="image-explanation-app">
      <div
        className={`diagram-panel image-viewer ${imageUrl ? "has-image" : ""}`}
        data-testid="image-viewer"
        onPointerDown={(event) => {
          if (!imageUrl) return;
          const target = event.target as HTMLElement;
          if (target.closest("button")) return;
          const scroller = scrollerRef.current;
          if (!scroller) return;
          dragRef.current = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, scrollLeft: scroller.scrollLeft, scrollTop: scroller.scrollTop };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const drag = dragRef.current;
          if (!drag || drag.pointerId !== event.pointerId) return;
          const scroller = scrollerRef.current;
          if (!scroller) return;
          scroller.scrollLeft = drag.scrollLeft - (event.clientX - drag.startX);
          scroller.scrollTop = drag.scrollTop - (event.clientY - drag.startY);
        }}
        onPointerUp={(event) => {
          if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
        }}
        onPointerCancel={() => {
          dragRef.current = null;
        }}
      >
        {imageUrl ? (
          <div className="image-viewer-scroll" ref={scrollerRef}>
            <div
              className="image-viewer-canvas"
              style={{ width: `${scale * 100}%`, height: `${scale * 100}%` } as CSSProperties}
            >
              <img src={imageUrl} alt={visualBrief} onLoad={centerScroller} />
              {showLabels && labels.map((label, index) => {
                const rawX = Number(label.x ?? 0.18);
                const rawY = Number(label.y ?? 0.22);
                const x = rawX > 1 ? rawX : rawX * 100;
                const y = rawY > 1 ? rawY : rawY * 100;
                return (
                  <span className="image-viewer-label" key={String(label.id ?? index)} style={{ left: `${Math.max(8, Math.min(92, x))}%`, top: `${Math.max(8, Math.min(92, y))}%` }}>
                    {String(label.text ?? `标签 ${index + 1}`)}
                  </span>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="diagram-placeholder"><FileImage size={28} /><strong>等待 {providerLabel}</strong><small>{visualBrief}</small></div>
        )}
        {imageUrl ? (
          <div className="image-viewer-tools" aria-label="图片查看器工具">
            <button type="button" onClick={() => zoom(-0.2)} title="缩小"><ZoomOut size={14} /></button>
            <span>{Math.round(scale * 100)}%</span>
            <button type="button" onClick={() => zoom(0.2)} title="放大"><ZoomIn size={14} /></button>
            <button type="button" onClick={resetView} title="适配窗口"><Maximize2 size={14} /></button>
            <button type="button" onClick={() => setShowLabels((value) => !value)} title="显示热点"><Tags size={14} /></button>
          </div>
        ) : null}
      </div>
      <div className="image-action-row">
        <button className="secondary-action" onClick={generate}>{imageUrl ? `重新生成 ${providerLabel}` : `生成 ${providerLabel}`}</button>
        {imageUrl ? <button className="secondary-action" onClick={resetView}><RotateCcw size={14} />重置视图</button> : null}
      </div>
      {status ? <p className="feedback-status">{status}</p> : null}
      {imageError ? <p className="feedback-status error">{providerLabel}生成失败：{imageError}</p> : null}
    </div>
  );
}

function VideoScriptApp({ app }: { app: CanvasApp }) {
  const storyboard = Array.isArray(app.payload.storyboard)
    ? app.payload.storyboard.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        return [record.scene, record.visual, record.narration].filter(Boolean).map(String).join(" · ");
      }
      return String(item);
    })
    : ["山谷视角引入损失函数", "点沿负梯度移动", "学习率过大时越过谷底"];
  return (
    <div className="script-list" data-testid="video-script-app">
      {storyboard.map((item, index) => (
        <article key={item}><strong>{String(index + 1).padStart(2, "0")}</strong><span>{item}</span></article>
      ))}
    </div>
  );
}

type VideoItem = {
  id: string;
  title: string;
  author: string;
  description: string;
  bvid: string;
  url: string;
  embedUrl: string;
  play: string;
  topic: string;
};

function formatPlayCount(value: unknown) {
  const count = Number(value ?? 0);
  if (!Number.isFinite(count) || count <= 0) return "";
  if (count >= 10000) return `${(count / 10000).toFixed(count >= 100000 ? 0 : 1)}万播放`;
  return `${Math.round(count)}播放`;
}

function normalizeVideoResource(resource: Record<string, unknown>, index: number, embedOptions: BilibiliEmbedOptions, payloadEmbedUrl = "", payloadSelectedId = ""): VideoItem {
  const content = typeof resource.content === "object" && resource.content ? resource.content as Record<string, unknown> : {};
  const id = String(resource.resource_id ?? resource.id ?? `video-${index}`);
  const bvid = extractBvidFromResource(resource);
  const rawUrl = String(content.url ?? content.href ?? "");
  const url = /^https?:\/\//.test(rawUrl) ? rawUrl : bvid ? `https://www.bilibili.com/video/${bvid}` : "";
  const embedUrl = payloadEmbedUrl && id === payloadSelectedId ? payloadEmbedUrl : bilibiliEmbedUrl(bvid, embedOptions);
  return {
    id,
    title: String(resource.title ?? content.title ?? `B站视频 ${index + 1}`),
    author: String(content.author ?? "B站"),
    description: String(content.description ?? resource.personalized_reason ?? ""),
    bvid,
    url,
    embedUrl,
    play: formatPlayCount(content.play),
    topic: String(resource.target_topic ?? content.target_topic ?? content.chapter ?? "视频推荐"),
  };
}

function VideoPlayerApp({ app, isFullscreen }: { app: CanvasApp; isFullscreen?: boolean }) {
  const [query, setQuery] = useState("");
  const payloadSelectedId = String(app.payload.selected_resource_id ?? "");
  const [selectedId, setSelectedId] = useState(payloadSelectedId);
  const embedOptions = useMemo(
    () => (typeof app.payload.embed_options === "object" && app.payload.embed_options ? app.payload.embed_options : {}) as BilibiliEmbedOptions,
    [app.payload.embed_options]
  );
  const payloadEmbedUrl = typeof app.payload.embed_url === "string" ? app.payload.embed_url : "";
  const rawVideos = useMemo(
    () => Array.isArray(app.payload.videos)
      ? app.payload.videos as Array<Record<string, unknown>>
      : Array.isArray(app.payload.resources)
        ? app.payload.resources as Array<Record<string, unknown>>
        : [],
    [app.payload.resources, app.payload.videos]
  );
  const videos = useMemo(() => rawVideos.map((resource, index) => normalizeVideoResource(resource, index, embedOptions, payloadEmbedUrl, payloadSelectedId)), [rawVideos, embedOptions, payloadEmbedUrl, payloadSelectedId]);
  useEffect(() => {
    if (videos.length && !videos.some((video) => video.id === selectedId)) {
      setSelectedId(videos[0].id);
    }
  }, [selectedId, videos]);
  const visibleVideos = videos.filter((video) => {
    const haystack = `${video.title} ${video.author} ${video.description} ${video.topic} ${video.bvid}`.toLowerCase();
    return !query.trim() || haystack.includes(query.trim().toLowerCase());
  });
  const selected = videos.find((video) => video.id === selectedId) ?? visibleVideos[0] ?? videos[0];
  const selectedEmbedUrl = selected?.embedUrl || bilibiliEmbedUrl(selected?.bvid ?? "", embedOptions);
  return (
    <div className={`video-player-app ${isFullscreen ? "fullscreen" : "compact"}`} data-testid="video-player-app">
      <header className="video-player-head">
        <div>
          <strong>{String(app.payload.topic ?? app.title ?? "B站视频播放器")}</strong>
          <small>{videos.length} 个视频 · {selected?.author ?? "B站"} {selected?.play ? `· ${selected.play}` : ""}</small>
        </div>
        {selected?.url ? (
          <a href={selected.url} target="_blank" rel="noreferrer">
            打开B站
            <ExternalLink size={13} />
          </a>
        ) : null}
      </header>
      <div className="video-player-layout">
        <section className="bilibili-player-panel">
          <div className="bilibili-player-frame">
            {selectedEmbedUrl ? (
              <iframe
                title={`${selected?.title ?? "B站视频"} 播放器`}
                src={selectedEmbedUrl}
                loading="lazy"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation"
                allow="fullscreen; picture-in-picture; autoplay"
                allowFullScreen
                data-testid="bilibili-player-iframe"
              />
            ) : (
              <div className="bilibili-player-fallback">
                <Film size={32} />
                <strong>没有可内嵌的 BV 号</strong>
                <span>可以从列表打开 B站原站查看。</span>
              </div>
            )}
          </div>
          {selected ? (
            <article className="video-now-playing">
              <strong>{selected.title}</strong>
              <small>{[selected.bvid, selected.author, selected.play, selected.topic].filter(Boolean).join(" · ")}</small>
              {selected.description ? <p>{selected.description}</p> : null}
            </article>
          ) : null}
        </section>
        <aside className="video-playlist-panel">
          <label className="resource-search"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索视频、UP、BV号" /></label>
          <div className="video-playlist">
            {visibleVideos.map((video) => (
              <button
                key={video.id}
                type="button"
                className={selected?.id === video.id ? "active" : ""}
                onClick={() => setSelectedId(video.id)}
                data-testid={`video-player-row-${video.id}`}
              >
                <span><Film size={14} /></span>
                <strong>{video.title}</strong>
                <small>{[video.author, video.play, video.bvid].filter(Boolean).join(" · ")}</small>
              </button>
            ))}
            {!visibleVideos.length ? <p className="feedback-status">没有匹配的视频。</p> : null}
          </div>
        </aside>
      </div>
    </div>
  );
}

function ResourceCenterApp({ app, isFullscreen, onDashboardUpdate, sessionContext }: { app: CanvasApp; isFullscreen?: boolean; onDashboardUpdate?: (dashboard: DashboardSnapshot) => void; sessionContext: SessionContext }) {
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [activeModule, setActiveModule] = useState("全部");
  const [activeTag, setActiveTag] = useState("全部标签");
  const [selectedId, setSelectedId] = useState("");
  const [remoteResources, setRemoteResources] = useState<Array<Record<string, unknown>>>([]);
  const [resourceStatus, setResourceStatus] = useState("快照");
  const toStringArray = (value: unknown) => Array.isArray(value) ? value.map(String).filter(Boolean) : [];
  const resourceKind = String(app.payload.resource_kind ?? "");
  const payloadResources = Array.isArray(app.payload.filtered_resources)
    ? app.payload.filtered_resources as Array<Record<string, unknown>>
    : Array.isArray(app.payload.resources)
      ? app.payload.resources as Array<Record<string, unknown>>
      : [
        { resource_id: "res-doc-gradient", title: "梯度下降图解讲义", type: "document" },
        { resource_id: "res-quiz-gradient", title: "诊断练习", type: "quiz" },
        { resource_id: "res-code-lab", title: "NumPy 实验", type: "code_practice" },
        { resource_id: "res-mindmap", title: "知识导图", type: "mindmap" },
        { resource_id: "res-reading", title: "延伸阅读", type: "reading" }
      ];
  useEffect(() => {
    let cancelled = false;
    setResourceStatus("同步中");
    fetchResources({ limit: 320, resource_type: resourceKind === "video" ? "video" : undefined }, sessionContext)
      .then((items) => {
        if (cancelled) return;
        setRemoteResources(items as unknown as Array<Record<string, unknown>>);
        setResourceStatus(`${items.length} 条已同步`);
      })
      .catch(() => {
        if (cancelled) return;
        setResourceStatus("离线快照");
      });
    return () => {
      cancelled = true;
    };
  }, [resourceKind, sessionContext.studentId, sessionContext.courseId]);
  const resourceMap = new Map<string, Record<string, unknown>>();
  [...payloadResources, ...remoteResources].forEach((resource, index) => {
    const id = String(resource.resource_id ?? resource.id ?? `resource-${index}`);
    const previous = resourceMap.get(id) ?? {};
    resourceMap.set(id, {
      ...previous,
      ...resource,
      content: {
        ...(typeof previous.content === "object" && previous.content ? previous.content as Record<string, unknown> : {}),
        ...(typeof resource.content === "object" && resource.content ? resource.content as Record<string, unknown> : {})
      }
    });
  });
  const mergedResources = Array.from(resourceMap.values());
  const roadmap = Array.isArray(app.payload.roadmap)
    ? (app.payload.roadmap as Array<unknown>).map((item, index) => {
      if (typeof item === "string") {
        return { title: item, order: index + 1 };
      }
      const record = typeof item === "object" && item ? item as Record<string, unknown> : {};
      return {
        title: String(record.title ?? record.resource_name ?? record.module_name ?? `阶段 ${index + 1}`),
        module: String(record.module_name ?? record.module ?? ""),
        order: Number(record.order ?? index + 1),
      };
    })
    : [];
  const resources = mergedResources.map((resource, index) => {
    const content = typeof resource.content === "object" && resource.content ? resource.content as Record<string, unknown> : {};
    const sourceRefs = Array.isArray(resource.source_refs) ? resource.source_refs : [];
    const sourceRefItems = sourceRefs
      .map((ref, refIndex) => {
        const record = typeof ref === "object" && ref ? ref as Record<string, unknown> : {};
        const page = record.page ? `p.${String(record.page)}` : "";
        const section = String(record.section ?? record.title ?? record.document_id ?? `来源 ${refIndex + 1}`);
        const confidence = typeof record.confidence === "number" ? `${Math.round(record.confidence * 100)}%` : "";
        return {
          id: String(record.chunk_id ?? `${section}-${refIndex}`),
          label: [section, page].filter(Boolean).join(" · "),
          meta: [record.source_type ? String(record.source_type) : "", confidence].filter(Boolean).join(" · "),
        };
      })
      .filter((ref) => ref.label);
    const tags = toStringArray(resource.tags).length ? toStringArray(resource.tags) : toStringArray(content.tags);
    const linksSource = Array.isArray(resource.links) ? resource.links : Array.isArray(content.links) ? content.links : [];
    const links = linksSource
      .map((link) => {
        if (typeof link === "string") {
          return { label: "打开链接", url: link };
        }
        const record = typeof link === "object" && link ? link as Record<string, unknown> : {};
        return { label: String(record.label ?? record.type ?? "打开链接"), url: String(record.url ?? record.href ?? "") };
      })
      .filter((link) => link.url.startsWith("http://") || link.url.startsWith("https://"));
    const contentUrl = typeof content.url === "string" && /^https?:\/\//.test(content.url) ? content.url : "";
    if (contentUrl && !links.some((link) => link.url === contentUrl)) {
      links.unshift({ label: String(resource.type ?? "") === "video" ? "打开B站" : "打开链接", url: contentUrl });
    }
    const corePoints = toStringArray(content.core_knowledge_points ?? content.core_points ?? resource.core_knowledge_points);
    const playCount = Number(content.play ?? 0);
    const play = Number.isFinite(playCount) && playCount > 0
      ? playCount >= 10000 ? `${(playCount / 10000).toFixed(playCount >= 100000 ? 0 : 1)}万播放` : `${Math.round(playCount)}播放`
      : "";
    return {
      id: String(resource.resource_id ?? resource.id ?? `resource-${index}`),
      title: String(resource.title ?? `资源 ${index + 1}`),
      preference: String(resource.type ?? resource.preference ?? "学习资源"),
      module: String(resource.module_name ?? content.module_name ?? resource.target_topic ?? content.topic ?? "通用资源"),
      level: String(resource.recommended_level ?? content.recommended_level ?? "核心"),
      difficulty: String(resource.difficulty ?? content.difficulty ?? "中级"),
      reason: String(resource.personalized_reason ?? content.summary ?? content.description ?? ""),
      summary: String(content.summary ?? content.description ?? ""),
      objective: String(content.learning_goal ?? content.objective ?? resource.learning_goal ?? ""),
      relation: String(content.relation ?? content.module_relation ?? ""),
      author: String(content.author ?? ""),
      bvid: String(content.bvid ?? ""),
      play,
      sourceRefs: sourceRefs.length,
      sourceRefItems,
      tags,
      links,
      corePoints,
    };
  });
  const modules = ["全部", ...Array.from(new Set(resources.map((resource) => resource.module))).slice(0, 8)];
  const payloadTags = toStringArray(app.payload.tag_system);
  const tagCatalog = ["全部标签", ...Array.from(new Set((payloadTags.length ? payloadTags : resources.flatMap((resource) => resource.tags)).filter(Boolean))).slice(0, 14)];
  const visibleResources = resources.filter((resource) => {
    const haystack = `${resource.title} ${resource.preference} ${resource.module} ${resource.reason} ${resource.tags.join(" ")}`.toLowerCase();
    const matchesQuery = !query.trim() || haystack.includes(query.trim().toLowerCase());
    const matchesModule = activeModule === "全部" || resource.module === activeModule;
    const matchesTag = activeTag === "全部标签" || resource.tags.includes(activeTag) || resource.module === activeTag;
    return matchesQuery && matchesModule && matchesTag;
  });
  const selected = visibleResources.find((resource) => resource.id === selectedId) ?? visibleResources[0] ?? resources[0];
  const coverage = resources.length ? Math.round((resources.filter((resource) => resource.sourceRefs > 0).length / resources.length) * 100) : 0;
  const record = async (resource: (typeof resources)[number], sentiment: "positive" | "negative") => {
    setStatus("写入反馈中");
    const result = await postResourceFeedback({
      resource_id: resource.id,
      app_id: app.app_id,
      preference: resource.preference,
      sentiment,
      rating: sentiment === "positive" ? 5 : 2,
      comment: sentiment === "positive" ? "适合当前学习节奏" : "需要换一种资源形态"
    }, sessionContext);
    onDashboardUpdate?.(result.dashboard);
    setStatus(`${resource.preference} 反馈已进入记忆`);
  };
  return (
    <div className={`resource-center ${isFullscreen ? "fullscreen" : "compact"}`} data-testid="resource-center-app">
      <header className="resource-center-head">
        <div>
          <strong>{String(app.payload.topic ?? app.title ?? "学习资源库")}</strong>
          <small>{resources.length} 个资源 · {modules.length - 1} 个模块 · 引用覆盖 {coverage}% · {resourceStatus}</small>
        </div>
        <span>{String(app.payload.status ?? "已索引")}</span>
      </header>
      <label className="resource-search"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索资源、模块、标签" /></label>
      <div className="resource-module-tabs" role="tablist" aria-label="资源模块">
        {modules.map((module) => (
          <button key={module} type="button" className={module === activeModule ? "active" : ""} onClick={() => setActiveModule(module)}>
            {module}
          </button>
        ))}
      </div>
      <div className="resource-tag-tabs" aria-label="资源标签筛选">
        {tagCatalog.map((tag) => (
          <button key={tag} type="button" className={tag === activeTag ? "active" : ""} onClick={() => setActiveTag(tag)}>
            {tag}
          </button>
        ))}
      </div>
      {roadmap.length ? (
        <div className="resource-roadmap" aria-label="学习路线图">
          {roadmap.slice(0, isFullscreen ? 10 : 5).map((item) => (
            <span key={`${item.order}-${item.title}`}>
              <strong>{String(item.order).padStart(2, "0")}</strong>
              {item.title}
            </span>
          ))}
        </div>
      ) : null}
      <div className="resource-center-grid">
        <div className="resource-list">
          {visibleResources.map((resource) => (
            <button key={resource.id} type="button" className={selected?.id === resource.id ? "active" : ""} onClick={() => setSelectedId(resource.id)}>
              <strong>{resource.title}</strong>
              <small>{resource.module} · {resource.preference} · {resource.level}</small>
              {resource.reason ? <span>{resource.reason}</span> : null}
            </button>
          ))}
        </div>
        {selected ? (
          <article className="resource-detail">
            <div className="resource-detail-title">
              <div>
                <strong>{selected.title}</strong>
                <small>{[selected.author, selected.play, selected.difficulty].filter(Boolean).join(" · ")}</small>
              </div>
              <span>{selected.level}</span>
            </div>
            {selected.preference === "video" && selected.links[0] ? (
              <a className="video-primary-link" href={selected.links[0].url} target="_blank" rel="noreferrer">
                <Film size={15} />
                打开B站视频
                <ExternalLink size={13} />
              </a>
            ) : null}
            {selected.objective ? <p>{selected.objective}</p> : selected.reason ? <p>{selected.reason}</p> : <p>该资源已进入当前课程知识库，可用于后续问答、引用和学习路线推荐。</p>}
            {selected.summary && selected.summary !== selected.objective ? <p className="resource-summary">{selected.summary}</p> : null}
            {selected.corePoints.length ? (
              <ul className="resource-points">
                {selected.corePoints.slice(0, 8).map((point) => <li key={point}>{point}</li>)}
              </ul>
            ) : null}
            <div className="resource-tags">
              {[selected.module, ...selected.tags].slice(0, 6).map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            {selected.sourceRefItems.length ? (
              <div className="resource-citations" aria-label="引用来源">
                {selected.sourceRefItems.slice(0, isFullscreen ? 8 : 4).map((ref) => (
                  <span key={ref.id} title={ref.meta || ref.label}>
                    {ref.label}
                    {ref.meta ? <small>{ref.meta}</small> : null}
                  </span>
                ))}
              </div>
            ) : null}
            {isFullscreen && selected.relation ? <p className="resource-relation">{selected.relation}</p> : null}
            {selected.links.length ? (
              <div className="resource-links">
                {selected.links.slice(0, 3).map((link) => <a key={link.url} href={link.url} target="_blank" rel="noreferrer">{link.label}</a>)}
              </div>
            ) : null}
            <div className="feedback-actions">
              <button onClick={() => record(selected, "positive")} data-testid={`resource-feedback-like-${selected.id}`}>适合</button>
              <button onClick={() => record(selected, "negative")} data-testid={`resource-feedback-swap-${selected.id}`}>换一种</button>
            </div>
          </article>
        ) : <p className="feedback-status">没有匹配资源。</p>}
      </div>
      {status ? <p className="feedback-status" data-testid="resource-feedback-status">{status}</p> : null}
    </div>
  );
}
