# 文渊问史 API

`wenyuan-api` 是文渊问史项目的 FastAPI 后端，提供认证、会话、模型列表、SSE 流式问答、Agent 过程记录和检索证据保存能力。

## 当前能力

- 注册：`POST /api/auth/register`
- 登录：`POST /api/auth/login`
- 当前用户：`GET /api/auth/me`
- 模型列表：`GET /api/models`
- 文言名句：`GET /api/quotes`
- 健康检查：`GET /api/health`
- 会话列表：`GET /api/conversations`
- 创建会话：`POST /api/conversations`
- 删除会话：`DELETE /api/conversations/{id}`
- 会话消息：`GET /api/conversations/{id}/messages`
- 过程回放：`GET /api/conversations/{id}/agent-runs`
- 流式问答：`POST /api/chat/stream`

## 流式问答事件

`POST /api/chat/stream` 返回 `text/event-stream`，事件内容统一为 JSON：

- `conversation`：当前会话信息。
- `thinking`：面向用户的模型公开决策日志。
- `action`：模型行动与工具调度阶段。
- `tool_call`：模型选择的工具名和参数。
- `observation`：工具返回内容。
- `retrieval_chunk`：工具调用产生的预置模拟数据库检索块。
- `answer_start`：开始输出最终答案。
- `answer_delta`：答案增量文本。
- `done`：本轮问答完成。

## 本地运行

```powershell
cd I:\计设2026\claudecode
.\scripts\start_backend.ps1
```

本项目使用已有解释器：

```text
.\.venv\Scripts\python.exe
```

不要在 `wenyuan-api/` 内新建 `.venv`。若后续缺少依赖，使用上述解释器安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

接口文档地址：

```text
http://127.0.0.1:8000/docs
```

## 数据库

默认不配置 `DATABASE_URL` 时使用 SQLite：

```text
sqlite:///./wenyuan.db
```

如果要使用 MySQL，复制 `.env.example` 中的示例，并设置：

```text
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/wenyuan?charset=utf8mb4
```

当前代码不会把真实密钥写死在项目中。真实模型 API 使用 OpenAI-compatible `/chat/completions` 协议。

配置完整时，`POST /api/chat/stream` 会优先调用真实模型，由真实模型产生工具调用；未配置或调用失败时不会伪造 Agent 行进过程，也不会主动检索预置数据库。

```text
LLM_PROVIDER=
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

## 开发边界

当前仓库不包含：

- 真实 ChromaDB/BM25 索引和原始数据文件。
- 真实 API Key。
- 生产部署配置。
