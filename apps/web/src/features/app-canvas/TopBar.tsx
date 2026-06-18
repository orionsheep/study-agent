import { Brain, Cpu, Download, LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import type { TraceItem } from "../../lib/events/agentEvents";

type Props = {
  isStreaming: boolean;
  traceLatest?: TraceItem;
  memoryActive?: boolean;
  canvasHidden?: boolean;
  currentTopic?: string;
  courseLabel?: string;
  learningObjective?: string;
  onToggleCanvas?: () => void;
  onLogout?: () => void;
};

export function TopBar({ isStreaming, traceLatest, memoryActive, canvasHidden, currentTopic, courseLabel, learningObjective, onToggleCanvas, onLogout }: Props) {
  return (
    <div className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <img src="/brand/learnforge-logo.png" alt="LearnForge" />
        </div>
        <div>
          <div className="brand-name">
            学境 <span style={{ color: "var(--text-3)", fontWeight: 500, fontSize: 13 }}>LearnForge</span>
          </div>
          <div className="brand-sub">V2 · SPATIAL LEARNING OS</div>
        </div>
      </div>

      <div className="topdiv" />

      <div className="crumb">
        <span className="crumb-label">当前课程</span>
        <span className="crumb-val">
          {courseLabel || "学习空间"}{currentTopic ? <> · <span className="accent">{currentTopic}</span></> : null}
        </span>
      </div>

      <div className="topdiv" />

      <div className="crumb" style={{ maxWidth: 280 }}>
        <span className="crumb-label">学习目标</span>
        <span className="crumb-val">{learningObjective || "与导师对话以设定学习目标"}</span>
      </div>

      <div style={{ flex: 1 }} />

      {isStreaming ? (
        <div className="agent-now">
          <div className="agent-orb">
            <Cpu size={12} style={{ color: "#fff", position: "absolute", inset: 0, margin: "auto" }} />
          </div>
          <span className="agent-now-text">
            <b>Hermes 总控</b> {traceLatest ? `· ${traceLatest.name} · ${traceLatest.detail || traceLatest.status}` : "· Agent 协同生成中"}
          </span>
        </div>
      ) : (
        <div className="save-chip">
          <span className="save-dot" />
          已自动保存
        </div>
      )}

      {memoryActive ? (
        <div className="memory-chip" title="LearnForge 正在根据你的学习记录个性化内容">
          <Brain size={13} />
          记忆已就绪
        </div>
      ) : null}

      {onToggleCanvas ? (
        <button
          className="btn btn-icon"
          title={canvasHidden ? "显示学习画板" : "隐藏学习画板"}
          aria-label={canvasHidden ? "显示学习画板" : "隐藏学习画板"}
          onClick={onToggleCanvas}
        >
          {canvasHidden ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      ) : null}

      <button className="btn btn-icon" title="导出">
        <Download size={16} />
      </button>

      {onLogout ? (
        <button
          className="btn btn-icon"
          title="退出登录"
          aria-label="退出登录"
          onClick={onLogout}
          style={{ marginLeft: 4 }}
        >
          <LogOut size={16} />
        </button>
      ) : null}
    </div>
  );
}
