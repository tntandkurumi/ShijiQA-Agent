# 技术架构规范

## 技术栈

- 前端：React + TypeScript + Vite。
- 后端：FastAPI + SQLAlchemy。
- 数据库：优先 MySQL，缺少 MySQL 配置时降级 SQLite。
- 通信：REST API + SSE 流式问答。
- 模型：OpenAI-compatible API，支持多供应商配置。

## 目录边界

- `wenyuan-web/`：前端工程，只负责界面、交互、状态管理和 API 调用。
- `wenyuan-api/`：后端工程，只负责认证、数据持久化、Agent 编排和 SSE 输出。
- 根目录既有中文检索脚本：作为未来真实检索模块参考，第一阶段不强依赖。
- `docs/`：规范文档。
- `dev-logs/`：每日开发日志。
- `scripts/`：开发辅助脚本。

## 后端模块建议

- `app/main.py`：FastAPI 应用入口。
- `app/config.py`：环境变量和配置读取。
- `app/database.py`：数据库连接、Session 管理。
- `app/models.py`：SQLAlchemy 表模型。
- `app/schemas.py`：Pydantic 请求/响应模型。
- `app/auth.py`：密码哈希、JWT、当前用户依赖。
- `app/services/agent_service.py`：真实 LLM 与模拟 Agent 编排。
- `app/services/mock_knowledge.py`：模拟八类知识库与检索。

## 数据库表

- `users`：用户账号、密码哈希、创建时间。
- `conversations`：用户会话、标题、所选模型、更新时间。
- `messages`：用户消息、助手回答、角色、时间。
- `agent_runs`：每次问答过程日志。
- `retrieval_chunks`：检索知识块、来源库、内容、分数、排序。
- `model_configs`：模型名称、供应商、base_url、是否启用。

## API 基线

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/models`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{id}/messages`
- `POST /api/chat/stream`
- `GET /api/quotes`

## 降级策略

1. 有 LLM API Key：优先调用真实 OpenAI-compatible 模型。
2. 无 API Key 或调用失败：自动使用模拟 Agent。
3. 有 MySQL 配置：使用 MySQL。
4. 无 MySQL 配置：使用 SQLite，保证演示原型可启动。
