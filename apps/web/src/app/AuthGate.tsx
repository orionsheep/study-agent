import { useState } from "react";
import { loginAccount, registerAccount, type AuthPayload } from "../lib/api/client";
import { themedBrandAsset } from "../lib/assets/appearanceAssets";
import { useTheme } from "../lib/state/useTheme";

type Props = { onAuth: (auth: AuthPayload) => void };

export function AuthGate({ onAuth }: Props) {
  const { theme } = useTheme();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const normalizedEmail = email.trim();
  const canSubmit = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail) && password.length >= 6;

  const submit = async () => {
    setError("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError("请输入有效邮箱，例如 name@example.com。");
      return;
    }
    if (password.length < 6) {
      setError("密码至少需要 6 位。");
      return;
    }
    setBusy(true);
    try {
      const auth = mode === "register"
        ? await registerAccount({ email: normalizedEmail, password, display_name: displayName.trim() || undefined })
        : await loginAccount({ email: normalizedEmail, password });
      onAuth(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "认证失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-screen">
      <section className="auth-panel">
        <div className="auth-copy">
          <img className="auth-brand-mark" src={themedBrandAsset("learnforge-logo", theme)} alt="LearnForge" />
          <span>LearnForge V2</span>
          <h1>建立你的学习画像</h1>
          <p>登录后先通过资料上传和简短问答生成个人画像，再进入空间学习画布。</p>
        </div>
        <div className="auth-form">
          <div className="segmented">
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册</button>
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button>
          </div>
          {mode === "register" ? <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="昵称" /> : null}
          <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="邮箱" autoComplete="email" />
          <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="密码，至少 6 位" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} />
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-action" disabled={busy || !canSubmit} onClick={submit}>
            {busy ? "处理中" : mode === "register" ? "创建账号" : "登录"}
          </button>
        </div>
      </section>
    </div>
  );
}
