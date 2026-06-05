# Research Code

本目录归档论文阶段的数据预处理、检索和实验脚本。它们不是 Web 应用启动入口，而是用于说明系统背后的 Agentic RAG 研究流程。

## 目录

- `retrieval/`：8 类检索工具脚本，对应 Web 后端工具调用接口。
- `preprocessing/`：向量生成、ChromaDB 构建、BM25 构建等数据预处理脚本。
- `experiments/`：原始 Agent 与多模型评测脚本，已移除真实 API Key。

## 与 Web 系统的关系

`wenyuan-api/app/services/prepared_retrieval.py` 会在没有真实数据目录时，通过预置数据和模拟向量集合适配 `retrieval/` 中的检索接口。后续接入真实数据时，可以保留 Agent 工具协议，只替换检索数据源和向量集合。

## 安全说明

实验脚本中的模型配置只保留结构，不包含真实 API Key。运行前请通过环境变量或本机 `.env.local` 配置密钥。
