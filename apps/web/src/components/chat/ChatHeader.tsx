"use client";

import { Settings2, Route } from "lucide-react";
import { MODEL_OPTIONS, type ModelProvider } from "../../lib/api/client";

/* ── Types ── */

export type ChatHeaderProps = {
  modelProvider: ModelProvider;
  onModelProviderChange: (provider: ModelProvider) => void;
  settingsOpen: boolean;
  onToggleSettings: () => void;
  onRegeneratePath?: () => void;
};

export function ChatHeader({
  modelProvider,
  onModelProviderChange,
  settingsOpen,
  onToggleSettings,
  onRegeneratePath,
}: ChatHeaderProps) {
  const activeProvider = MODEL_OPTIONS.find((o) => o.provider === modelProvider) ?? MODEL_OPTIONS[0];
  const providerLabel = activeProvider.label;

  return (
    <>
      <header className="chat-header chat-head">
        <div className="tutor-id">
          <div className="tutor-av">
            <img src="/brand/ai-tutor-avatar.png" alt="AI 学习导师" />
          </div>
          <div className="tutor-meta">
            <span className="eyebrow">Tutor Chat</span>
            <h1 className="nm">AI 学习导师</h1>
            <div className="role">Tutor Agent · Hermes 调度 · {providerLabel} 生成</div>
          </div>
        </div>
        <div className="tutor-header-actions">
          <button
            type="button"
            className="model-settings-btn"
            title="模型设置"
            aria-label="模型设置"
            onClick={onToggleSettings}
          >
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
          {onRegeneratePath ? (
            <div className="settings-actions" aria-label="更多操作">
              <button
                type="button"
                className="settings-action-btn"
                onClick={onRegeneratePath}
              >
                <Route size={15} />
                <span>重新规划路径</span>
              </button>
            </div>
          ) : null}
        </section>
      ) : null}
    </>
  );
}
