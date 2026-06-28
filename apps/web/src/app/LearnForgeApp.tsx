import { useCallback, useEffect, useState } from "react";
import type { LearningResource } from "@learnforge/app-protocol";
import { AuthGate } from "./AuthGate";
import { OnboardingFlow } from "./OnboardingFlow";
import { LearnForgeShell } from "./LearnForgeShell";
import {
  DEFAULT_SESSION_CONTEXT,
  fetchAuthMe,
  logoutAccount,
  setAuthToken,
  type AuthPayload,
  type SessionContext
} from "../lib/api/client";
import { themedBrandAsset } from "../lib/assets/appearanceAssets";
import { loadJson, saveJson } from "../lib/state/localStorage";
import { useTheme } from "../lib/state/useTheme";
import { DEFAULT_BILIBILI_EMBED_OPTIONS, bilibiliEmbedUrl, extractBvidFromResource } from "../lib/video/bilibili";

export function buildResourceCanvasAppRequest(resource: LearningResource) {
  const isVideo = resource.type === "video";
  const topic = String(resource.target_topic || resource.content?.target_topic || resource.title || (isVideo ? "B站视频推荐" : "学习资源"));
  const selectedBvid = isVideo ? extractBvidFromResource(resource) : "";
  return {
    app_type: isVideo ? "video.player" : "resource.center",
    title: isVideo ? `${topic} B站视频播放器` : `${resource.title} 资源卡`,
    payload: isVideo
      ? {
        topic,
        status: "B站视频可播放",
        videos: [resource],
        selected_resource_id: resource.resource_id,
        selected_bvid: selectedBvid,
        embed_url: bilibiliEmbedUrl(selectedBvid),
        embed_options: DEFAULT_BILIBILI_EMBED_OPTIONS
      }
      : {
        topic,
        status: "已加入画布",
        resource_kind: "resource",
        resources: [resource]
      },
    source_refs: resource.source_refs
  };
}

function sessionFromAuth(auth: AuthPayload): SessionContext {
  const params = new URLSearchParams(window.location.search);
  return {
    studentId: params.get("student_id") || auth.student.student_id,
    courseId: params.get("course_id") || auth.student.course_id,
    conversationId: params.get("conversation_id") || `conv-${auth.student.student_id}`
  };
}

export function LearnForgeApp() {
  const { theme } = useTheme();
  const [auth, setAuth] = useState<AuthPayload | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [sessionContext, setSessionContext] = useState<SessionContext>(() => loadJson("learnforge.session.context", DEFAULT_SESSION_CONTEXT));

  const applyAuth = useCallback((nextAuth: AuthPayload) => {
    setAuth(nextAuth);
    const nextSession = sessionFromAuth(nextAuth);
    saveJson("learnforge.session.context", nextSession);
    setSessionContext(nextSession);
  }, []);

  useEffect(() => {
    fetchAuthMe()
      .then(applyAuth)
      .catch(() => undefined)
      .finally(() => setCheckingAuth(false));
  }, [applyAuth]);

  const handleLogout = useCallback(() => {
    logoutAccount();
    setAuth(null);
  }, []);

  if (checkingAuth) {
    return <div className="auth-screen"><section className="auth-panel"><div className="auth-copy"><img className="auth-brand-mark" src={themedBrandAsset("learnforge-logo", theme)} alt="LearnForge" /><span>LearnForge V2</span><h1>正在检查登录状态</h1></div></section></div>;
  }

  if (!auth) {
    return <AuthGate onAuth={applyAuth} />;
  }

  if (auth.student.profile_status !== "completed") {
    return (
      <OnboardingFlow
        auth={auth}
        context={sessionContext}
        onLogout={handleLogout}
        onComplete={() => fetchAuthMe().then(applyAuth).catch(() => setAuth({ ...auth, student: { ...auth.student, profile_status: "completed" } }))}
      />
    );
  }

  return <LearnForgeShell sessionContext={sessionContext} onLogout={handleLogout} />;
}
