# 文渊问史 Web

`wenyuan-web` 是文渊问史项目的 React + TypeScript + Vite 前端。

## 当前能力

- 网站介绍页。
- 登录页。
- 注册页。
- 完整问答页。
- 会话列表和新建会话。
- 删除会话。
- 历史消息读取。
- 历史过程块和检索知识块回放。
- 模型选择。
- SSE 流式问答。
- 助手消息内部展示过程块与检索知识块。
- 复制、重新生成、停止生成。
- token 本地保存。
- 模型列表读取。
- 底部文言名句轮滚。
- 古风纯文本视觉风格。

## 本地运行

先启动后端：

```powershell
cd I:\计设2026\claudecode\wenyuan-api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

再启动前端：

```powershell
cd I:\计设2026\claudecode
.\scripts\start_frontend.ps1
```

访问：

```text
http://127.0.0.1:5173
```

## 环境变量

默认后端地址：

```text
http://127.0.0.1:8000
```

如需修改，创建 `.env.local`：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 下一阶段

- 做浏览器人工验收。
- 优化移动端和宽屏细节。
- 补真实 LLM 配置说明和模拟/真实降级提示。
