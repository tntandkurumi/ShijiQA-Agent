# 真实大模型配置说明

后端支持 OpenAI-compatible `/chat/completions` 协议。真实 Agent 行进过程必须由真实模型 API 产生；未配置密钥时，系统只展示模拟检索数据，不伪装真实 Agent 过程。

## 环境变量

在启动后端前设置：

```powershell
$env:LLM_PROVIDER="deepseek"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_API_KEY="你的真实密钥"
$env:LLM_MODEL="deepseek-chat"
```

然后启动后端：

```powershell
.\scripts\start_backend.ps1
```

也可以在本机创建 `wenyuan-api/.env.local`：

```text
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的真实密钥
LLM_MODEL=deepseek-chat
```

后端启动时会自动读取 `.env.local`。该文件只用于本机，不要提交到仓库。

如果同一套系统要支持多个真实模型，推荐使用本机多模型配置文件：

```text
# wenyuan-api/.env.local
LLM_MODEL_CONFIG_FILE=.llm.models.local.json
```

然后在 `wenyuan-api/.llm.models.local.json` 中按模型名保存配置：

```json
{
  "deepseek-v4-pro": {
    "provider": "deepseek",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-pro",
    "api_key": "你的真实密钥"
  },
  "qwen3.6-plus": {
    "provider": "dashscope",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.6-plus",
    "api_key": "你的真实密钥"
  }
}
```

问答时后端会优先按前端选择的模型名查找对应配置；找不到时才回退到旧的全局 `LLM_API_KEY` 配置。

## 兼容供应商

只要供应商兼容 OpenAI Chat Completions 协议，理论上都可以配置：

```text
POST {LLM_BASE_URL}/chat/completions
Authorization: Bearer {LLM_API_KEY}
```

常见配置示例：

```powershell
# DeepSeek
$env:LLM_PROVIDER="deepseek"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-chat"

# 通义千问兼容模式
$env:LLM_PROVIDER="dashscope"
$env:LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_MODEL="qwen-plus"
```

`test3.ipynb` 中出现过的 Kimi、豆包、MiMo、DeepSeek、通义/百炼等模型，可以作为本机多模型配置来源。不要把 notebook 中的 API Key 写入源码、README、docs 或前端。

## 降级策略

- 配置完整：优先调用真实模型。
- 缺少任一配置：不执行真实 Agent 行进过程，只展示模拟检索数据和配置提示。
- 真实模型请求失败：自动降级为配置提示与模拟检索数据，不伪装模型思考。
- 前端消息内部会显示 `真实模型状态`，说明当前使用真实模型、未配置或失败降级。

## Agent 调用流程

真实模型问答流程参考 `test3.ipynb`：

- 使用《陈书》与南朝历史研究助手系统提示词。
- 使用 OpenAI-compatible `tools` 与 `tool_choice=auto`。
- 最多进行 5 轮工具调用。
- 工具调用由真实模型自主决定，后端只负责执行对应模拟检索工具。
- 若 5 轮后仍没有最终答案，后端会追加“现在，请根据以上所有信息，直接给出最终答案。”并强制生成。
- 页面按顺序展示公开过程块：`thinking`、`action`、`tool_call`、`observation`，然后展示最终答案。
- `thinking` 是面向用户的公开决策日志，用于说明模型为什么进入检索或直接回答；不展示底层隐藏推理链。
- 多轮会话会把最近 8 条用户/助手消息带入模型上下文。

## 安全要求

- 不要把真实 API Key 写入代码。
- 不要提交 `.env.local`、`.llm.models.local.json` 或包含密钥的脚本；后端 `.gitignore` 已忽略这些本机文件。
- 演示时可以先不配置密钥，系统仍能完整跑通。
