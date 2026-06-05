import { FormEvent, useState } from "react";
import { BookMarked, LockKeyhole, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isLogin = mode === "login";
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isLogin) {
        await login(username, password);
      } else {
        await register(username, password);
      }
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="authPanel">
      <div className="authIntro">
        <BookMarked size={42} aria-hidden="true" />
        <p>多源异构史籍知识问答</p>
        <h1>{isLogin ? "归案启问" : "开卷入渊"}</h1>
        <span>以人物、地理、官职、术语、诗文与图谱为证，循检索而答。</span>
      </div>

      <form className="authForm" onSubmit={handleSubmit}>
        <label>
          <span>账号</span>
          <div className="inputWrap">
            <UserRound size={18} aria-hidden="true" />
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              minLength={3}
              maxLength={64}
              required
              autoComplete="username"
              placeholder="请输入账号"
            />
          </div>
        </label>

        <label>
          <span>密码</span>
          <div className="inputWrap">
            <LockKeyhole size={18} aria-hidden="true" />
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={6}
              maxLength={128}
              required
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              placeholder="至少 6 位"
            />
          </div>
        </label>

        {error && <div className="formError">{error}</div>}

        <button className="primaryButton" type="submit" disabled={loading}>
          {loading ? "处理中..." : isLogin ? "登录" : "注册"}
        </button>

        <p className="switchAuth">
          {isLogin ? "尚无账号？" : "已有账号？"}
          <Link to={isLogin ? "/register" : "/login"}>{isLogin ? "立即注册" : "返回登录"}</Link>
        </p>
      </form>
    </section>
  );
}
