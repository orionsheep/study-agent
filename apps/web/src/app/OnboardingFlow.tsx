import { useEffect, useState } from "react";
import { TopBar } from "../features/app-canvas/TopBar";
import { TutorChat } from "../features/tutor-chat/TutorChat";
import {
  fetchOnboardingStatus,
  generateOnboardingProfile,
  postOnboardingMessage,
  startOnboarding,
  type AuthPayload,
  type ModelProvider,
  type OnboardingStatus,
  type SessionContext
} from "../lib/api/client";
import type { ChatMessage } from "../lib/events/agentEvents";
import { useTheme } from "../lib/state/useTheme";

type Props = {
  auth: AuthPayload;
  context: SessionContext;
  onComplete: () => void;
  onLogout: () => void;
};

export function OnboardingFlow({ auth, context, onComplete, onLogout }: Props) {
  const { theme, glassEnabled, wallpaperId, toggleTheme, toggleGlass, setTheme, setGlassEnabled, setWallpaperId } = useTheme();
  const name = auth.user.display_name || "同学";
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "onboarding-welcome",
      role: "assistant",
      text: `你好${name}！进入学习空间前，先用聊天的方式让我认识你。\n\n用几句话告诉我就好：\n1. **你在哪所学校、什么专业、几年级**\n2. **现在想学什么、哪里卡住**\n3. **喜欢怎么学**（图解 / 视频 / 代码 / 刷题…）、每周大概多少时间\n\n可以一次多说几点，我会边聊边帮你补全画像。`,
      links: [],
      resources: []
    }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [modelProvider, setModelProvider] = useState<ModelProvider>("gemini");

  useEffect(() => {
    startOnboarding(context).catch(() => undefined);
  }, [context]);

  const pushAssistant = (text: string) =>
    setMessages((items) => [...items, { id: `onb-a-${Date.now()}`, role: "assistant", text, links: [], resources: [] }]);

  const send = async (text: string) => {
    setMessages((items) => [...items, { id: `onb-u-${Date.now()}`, role: "user", text, links: [], resources: [] }]);
    setIsStreaming(true);
    try {
      const status = await postOnboardingMessage(text, context);
      const missing = status?.missing_fields ?? [];
      const coverage = Math.round((status?.coverage ?? 0) * 100);
      if (missing.length <= 7) {
        pushAssistant(`画像已经够用了（覆盖约 ${coverage}%）。我现在为你生成学习画像并进入空间学习画布，剩下的可以边学边补～`);
        await generateOnboardingProfile(context).catch(() => undefined);
        await onComplete();
        return;
      }
      const next = missing.slice(0, 3).join("、");
      pushAssistant(`收到～已记下来（画像覆盖约 ${coverage}%）。\n\n再补充几点就能进入学习空间：**${next}**。你可以接着告诉我。`);
    } catch (err) {
      pushAssistant(`这条没能记下来：${err instanceof Error ? err.message : "请求失败"}。可以再发一次。`);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="lf-root">
      <TopBar
        isStreaming={isStreaming}
        traceLatest={undefined}
        theme={theme}
        onToggleTheme={toggleTheme}
        onThemeChange={setTheme}
        glassEnabled={glassEnabled}
        onToggleGlass={toggleGlass}
        onGlassChange={setGlassEnabled}
        wallpaperId={wallpaperId}
        onWallpaperChange={setWallpaperId}
        onLogout={onLogout}
      />
      <main className="learnforge-shell canvas-hidden onboarding-chat-shell">
        <TutorChat
          messages={messages}
          generatedLinks={[]}
          activities={[]}
          isStreaming={isStreaming}
          backgroundTasks={[]}
          modelProvider={modelProvider}
          onModelProviderChange={setModelProvider}
          onSend={send}
          onSummarize={async () => { onLogout(); }}
          onOpenLink={() => undefined}
          onAddResourceToCanvas={() => undefined}
        />
      </main>
    </div>
  );
}
