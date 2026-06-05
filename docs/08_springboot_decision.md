# Spring Boot 架构决策

## 当前结论

当前不建议把 Spring Boot 加入主流程。

## 原因

- 现有核心能力在 Python：Agent 编排、模拟检索、未来真实 ChromaDB/BM25/知识图谱检索都更贴近 Python 生态。
- 加入 Spring Boot 会变成 React -> Spring Boot -> FastAPI -> Agent/检索 的双后端链路，调试和部署复杂度上升。
- 当前论文/演示重点是 Agentic RAG 与多源异构知识问答，不是 Java 企业系统。
- 已有 FastAPI 后端足够表达 B/S、REST、SSE、鉴权、数据库和模型服务。

## 可选加入方式

若老师或论文要求必须体现 Spring Boot，可作为后续可选网关层：

- Spring Boot 负责用户、权限、统一网关、审计日志。
- FastAPI 保留为 Agent 服务。
- React 只调用 Spring Boot，Spring Boot 再转发 Agent 请求给 FastAPI。

该方案只建议在明确需要 Java 后端时采用，不建议现在实现。
