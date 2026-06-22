import { useEffect, useRef, useState } from "react";
import { Brain, ChevronDown, Cpu, Download, LogOut, Moon, PanelLeftClose, PanelLeftOpen, Sun, User } from "lucide-react";
import type { TraceItem } from "../../lib/events/agentEvents";
import { logoutAccount } from "../../lib/api/client";
import type { ThemeMode } from "../../lib/state/useTheme";

type Props = {
  isStreaming: boolean;
  traceLatest?: TraceItem;
  memoryActive?: boolean;
  canvasHidden?: boolean;
  currentTopic?: string;
  courseLabel?: string;
  learningObjective?: string;
  theme: ThemeMode;
  onToggleTheme: () => void;
  onToggleCanvas?: () => void;
  onLogout?: () => void;
};

export function TopBar({ isStreaming, traceLatest, memoryActive, canvasHidden, currentTopic, courseLabel, learningObjective, theme, onToggleTheme, onToggleCanvas, onLogout }: Props) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!userMenuOpen) return;
    const onPointerDown = (event: MouseEvent | PointerEvent) => {
      if (!userMenuRef.current?.contains(event.target as Node)) setUserMenuOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setUserMenuOpen(false);
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [userMenuOpen]);

  // 直接处理退出：清 token + 回调，即使后端 /api/auth/logout 报错也强制登出
  const handleLogout = () => {
    setUserMenuOpen(false);
    console.log("[TopBar] 退出按钮被点击");
    try { logoutAccount(); } catch (e) { console.warn("[TopBar] logoutAccount error", e); }
    try { onLogout?.(); } catch (e) { console.warn("[TopBar] onLogout error", e); }
    // 兜底：强制刷新页面回到登录页
    setTimeout(() => { window.location.href = window.location.pathname; }, 300);
  };

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

      {/* spacer */}
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

      <button
        className="theme-toggle"
        title={theme === "dark" ? "切换到亮色模式" : "切换到暗色模式"}
        aria-label={theme === "dark" ? "切换到亮色模式" : "切换到暗色模式"}
        onClick={onToggleTheme}
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      <button className="btn btn-icon" title="导出">
        <Download size={16} />
      </button>

      <div className="topbar-user-menu" ref={userMenuRef}>
        <button
          type="button"
          className={`topbar-avatar-button ${userMenuOpen ? "is-open" : ""}`}
          onClick={() => setUserMenuOpen((open) => !open)}
          aria-haspopup="menu"
          aria-expanded={userMenuOpen}
          title="账户菜单"
        >
          <span className="topbar-avatar-icon">
            <User size={14} color="#fff" />
          </span>
          <ChevronDown size={12} />
        </button>
        {userMenuOpen ? (
          <div className="topbar-user-dropdown" role="menu">
            <button type="button" role="menuitem" className="topbar-user-menu-item danger" onClick={handleLogout}>
              <LogOut size={14} />
              <span>退出登录</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
