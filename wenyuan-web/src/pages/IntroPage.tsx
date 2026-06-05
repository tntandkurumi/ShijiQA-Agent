import { ArrowRight, DatabaseZap, Network, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";

const capabilities = [
  { icon: DatabaseZap, title: "八类知识源", text: "人物、官职、地理、典故事件、术语、知识图谱、诗文、双语对照。" },
  { icon: Network, title: "Agentic RAG", text: "先识别意图，再选择检索工具，最后以证据块组织答案。" },
  { icon: ShieldCheck, title: "过程可视化", text: "思考摘要、决策过程、工具调用和检索依据分块展示。" },
];

export function IntroPage() {
  const { isAuthed } = useAuth();

  return (
    <section className="introPage">
      <div className="introHero">
        <div>
          <p className="eyebrow">史籍知识问答 · 多源异构检索</p>
          <h1>文渊问史</h1>
          <p className="heroText">
            面向《陈书》等南朝史料的浏览器端问答系统。以模拟知识库先跑通完整流程，
            后续可替换为真实 ChromaDB、BM25、知识图谱与大模型服务。
          </p>
          <div className="heroActions">
            <Link className="primaryButton buttonLink" to={isAuthed ? "/chat" : "/login"}>
              {isAuthed ? "进入问答" : "登录体验"}
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
            {!isAuthed && (
              <Link className="secondaryButton buttonLink" to="/register">
                创建账号
              </Link>
            )}
          </div>
        </div>
        <div className="processPanel" aria-label="系统流程">
          <Sparkles size={22} aria-hidden="true" />
          <ol>
            <li>用户提出史籍问题</li>
            <li>Agent 判断意图与数据源</li>
            <li>多源知识块检索与排序</li>
            <li>流式生成答案并保存历史</li>
          </ol>
        </div>
      </div>

      <div className="capabilityGrid">
        {capabilities.map((item) => {
          const Icon = item.icon;
          return (
            <article className="capability" key={item.title}>
              <Icon size={24} aria-hidden="true" />
              <h2>{item.title}</h2>
              <p>{item.text}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
