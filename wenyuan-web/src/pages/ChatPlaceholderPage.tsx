import { useEffect, useState } from "react";
import { Bot, MessageSquareText } from "lucide-react";
import { api, type ModelInfo } from "../lib/api";
import { useAuth } from "../lib/auth";

export function ChatPlaceholderPage() {
  const { token } = useAuth();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.models(token).then(setModels).catch((err) => setError(err instanceof Error ? err.message : "模型列表读取失败。"));
  }, [token]);

  return (
    <section className="chatPlaceholder">
      <div className="chatNotice">
        <MessageSquareText size={32} aria-hidden="true" />
        <p className="eyebrow">阶段 3 基础页</p>
        <h1>问答台已立，细节待铺</h1>
        <p>
          当前前端已完成认证、路由与基础页面。下一阶段会接入会话列表、消息历史、
          SSE 流式回答和过程块折叠展示。
        </p>
      </div>

      <aside className="modelPreview">
        <Bot size={24} aria-hidden="true" />
        <h2>后端模型配置</h2>
        {error ? <p className="formError">{error}</p> : null}
        <div className="modelList">
          {models.map((model) => (
            <div className="modelItem" key={model.name}>
              <span>{model.display_name}</span>
              <small>{model.provider}{model.is_mock ? " · 模拟" : " · 真实预留"}</small>
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
