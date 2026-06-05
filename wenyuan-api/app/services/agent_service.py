import json
import urllib.error
import urllib.request

from ..config import settings
from .prepared_retrieval import execute_prepared_tool


AVAILABLE_TOOLS = [
    "search_person",
    "search_official_positions",
    "search_geography",
    "search_historical_events",
    "search_terminology",
    "search_knowledge_graph",
    "search_poetry",
    "search_bilingual",
]

MAX_TOOL_ROUNDS = 5
MAX_TOKENS = 4096

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_bilingual",
            "description": "检索《陈书》古文与现代文对照段落，适合把现代文描述映射回原文或查找原文出处。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "完整问题、现代文句子或关键词。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_person",
            "description": "检索《陈书》相关人物传记、身份、事迹和称谓。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "人物姓名、称号或相关事迹关键词。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_poetry",
            "description": "按作者或题名检索诗文作品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "author": {"type": "string", "description": "作者规范姓名，可为空。"},
                    "title": {"type": "string", "description": "诗文标题，可为空。"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_positions",
            "description": "检索官职制度、品阶、职责和沿革。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "官职名称或制度问题关键词。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_geography",
            "description": "检索地理沿革、地名、都城、州郡和地域关系。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "地名或地理问题关键词。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_historical_events",
            "description": "检索典故、战争、叛乱、政治事件和关联人物。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "事件名称或相关关键词。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_terminology",
            "description": "检索古籍术语、礼制词、句法和文言表达解释。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "术语、短语或句法问题。"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_graph",
            "description": "检索人物、官职、地名之间的关系网络，适合查询隶属、血缘、任职和关联。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "关系查询关键词。"}},
                "required": ["query"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "你是一个精通《陈书》及相关南朝历史的高级研究助手，背后接入了多源异构古籍数据库。\n"
    "你的知识库覆盖《陈书》的现代文对照、人物传记、诗文作品、官职制度、地理沿革、\n"
    "典故战争、术语解释以及知识图谱（人物、官职、地名间的关系网络）。\n\n"
    "## 核心原则（ReAct 范式）\n"
    "1. 所有回答必须基于工具返回的真实数据，严禁凭空编造史实。\n"
    "2. 若问题明确涉及《陈书》的人物、事件、地理、制度等，你必须至少调用一次工具进行检索，\n"
    "   即使你自认为知道答案，也必须通过工具验证或补充细节。\n"
    "3. 你可以一次性并行调用多个工具，例如同时查人物传记和知识图谱关系，以提高效率。\n"
    "4. 完成第一轮工具调用后，仔细分析返回结果。如果信息仍不充分，或需要进一步追问细节，\n"
    "   必须继续调用工具，但最多进行 5 轮工具调用。请高效规划查询，找到需要的数据后就停止。\n"
    "5. 只有当所有必要信息均已获取，且无需更多工具时，你才能生成最终答案。\n"
    "6. 最终答案应条理清晰，尽量引用原文依据或现代文出处，并注明信息来源。\n\n"
    "## 非检索问题\n"
    "- 用户询问你是谁、能做什么、如何使用、寒暄或页面操作时，不要调用工具。\n"
    "- 这类问题直接说明你是“文渊问史”的史籍知识问答助手即可，不要声称已经检索数据库。\n"
    "- 只有问题需要史籍事实、原文、人物、官职、地理、事件、术语或关系依据时，才调用工具。\n\n"
    "## 工具使用要点\n"
    "- 查询人物关系、隶属、血缘时，优先使用 search_knowledge_graph。\n"
    "- 将现代文描述映射回《陈书》段落，请使用 search_bilingual，输入完整的现代文句子。\n"
    "- 官职必须输入准确名称，诗文作者必须用规范完整姓名。\n"
    "- 如果工具返回空结果或报错，可尝试更换同义词、更规范的名称或组合其他工具。\n\n"
    "## 输出规范\n"
    "- 最终答案使用流畅的中文，适当引用古文或现代文段落。"
)


def split_answer(text: str, size: int = 18) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]


def build_agent_result(
    query: str,
    model_name: str,
    history_count: int = 0,
    model_config: dict | None = None,
    history_messages: list[dict] | None = None,
) -> dict:
    runtime = _resolve_runtime_config(model_name, model_config)
    if not runtime["enabled"]:
        return build_unconfigured_result(query=query, model_name=model_name, history_count=history_count)

    try:
        return build_real_agent_result(
            query=query,
            model_name=model_name,
            history_count=history_count,
            runtime=runtime,
            history_messages=history_messages,
        )
    except Exception as exc:
        fallback = build_unconfigured_result(query=query, model_name=model_name, history_count=history_count)
        fallback["process_blocks"][0]["content"] = f"真实模型调用失败，未伪装真实 Agent 行进过程。失败原因：{exc}"
        fallback["process_blocks"][0]["metadata"] = {"mode": "fallback", "reason": str(exc)}
        fallback["fallback_reason"] = str(exc)
        return fallback


def build_unconfigured_result(query: str, model_name: str, history_count: int = 0) -> dict:
    answer = (
        "当前未配置完整真实大模型 API，因此不能执行真实 Agent 行进过程。\n\n"
        "模拟数据库不会自行检索；只有真实模型明确调用工具后，后端才会按预置 8 个数据库接口返回模拟检索结果。\n"
        "请配置该模型对应的 API Key、base_url、model 后，再进行真实 Agent 问答。"
    )
    return {
        "process_blocks": [
            {
                "type": "llm_status",
                "title": "真实模型状态",
                "content": "未检测到当前所选模型的完整 API 配置。系统不会伪装真实 Agent 行进过程，也不会主动检索预置数据库。",
                "metadata": {"mode": "unconfigured", "model": model_name, "history_count": history_count},
            }
        ],
        "retrieval_chunks": [],
        "answer": answer,
        "used_real_llm": False,
        "fallback_reason": "missing_llm_configuration",
    }


def build_real_agent_result(
    query: str,
    model_name: str,
    history_count: int = 0,
    runtime: dict | None = None,
    history_messages: list[dict] | None = None,
) -> dict:
    runtime = runtime or _resolve_runtime_config(model_name, None)
    actual_model = runtime["model"]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_normalize_history_messages(history_messages or []))
    messages.append({"role": "user", "content": query})
    process_blocks = []
    all_chunks = []
    final_answer = ""

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        choice = _call_openai_choice(
            model_name=actual_model,
            runtime=runtime,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_tokens=MAX_TOKENS,
        )
        finish_reason = choice.get("finish_reason", "")
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            messages.append(_assistant_message_for_history(message))
            process_blocks.append(_thinking_block(round_num, actual_model, finish_reason, tool_calls))
            process_blocks.append(
                {
                    "type": "action",
                    "title": f"模型行动 第 {round_num} 轮",
                    "content": f"模型决定调用 {len(tool_calls)} 个检索工具。finish_reason={finish_reason or 'tool_calls'}。",
                    "metadata": {"mode": "real", "model": actual_model, "round": round_num, "history_count": history_count},
                }
            )
            for call_index, tool_call in enumerate(tool_calls, start=1):
                tool_name, arguments = _parse_tool_call(tool_call)
                result = execute_prepared_tool(tool_name, arguments, query)
                process_blocks.append(
                    {
                        "type": "tool_call",
                        "title": f"工具调用 {round_num}.{call_index}",
                        "content": f"{tool_name}({json.dumps(arguments, ensure_ascii=False)})",
                        "metadata": {"tool": tool_name, "arguments": arguments, "round": round_num},
                    }
                )
                for chunk in result.chunks:
                    normalized = dict(chunk)
                    normalized["rank"] = len(all_chunks) + 1
                    all_chunks.append(normalized)
                process_blocks.append(
                    {
                        "type": "observation",
                        "title": f"工具返回 {round_num}.{call_index}",
                        "content": result.raw_text,
                        "metadata": {"tool": tool_name, "count": len(result.chunks), "round": round_num},
                    }
                )
                messages.append({"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": result.raw_text})
            continue

        if finish_reason == "stop":
            if not process_blocks:
                process_blocks.append(_thinking_block(round_num, actual_model, finish_reason, tool_calls))
            final_answer = str(message.get("content") or "").strip()
            messages.append({"role": "assistant", "content": final_answer})
            break

        process_blocks.append(_thinking_block(round_num, actual_model, finish_reason, tool_calls))
        process_blocks.append(
            {
                "type": "action",
                "title": f"模型行动 第 {round_num} 轮",
                "content": f"模型返回了暂不支持的 finish_reason：{finish_reason or 'unknown'}，将尝试强制生成最终答案。",
                "metadata": {"mode": "real", "model": actual_model, "round": round_num},
            }
        )
        break

    if not final_answer:
        messages.append({"role": "user", "content": "现在，请根据以上所有信息，直接给出最终答案。"})
        choice = _call_openai_choice(
            model_name=actual_model,
            runtime=runtime,
            messages=messages,
            tools=None,
            tool_choice=None,
            max_tokens=MAX_TOKENS,
        )
        message = choice.get("message") or {}
        final_answer = str(message.get("content") or "").strip()
        process_blocks.append(
            {
                "type": "action",
                "title": "强制生成最终答案",
                "content": "工具调用轮次结束或模型未直接停止，已参考 notebook 逻辑要求模型基于现有信息直接回答。",
                "metadata": {"mode": "real", "model": actual_model},
            }
        )

    if not final_answer:
        final_answer = "模型未返回可展示的最终答案。"
    return {
        "process_blocks": process_blocks,
        "retrieval_chunks": all_chunks,
        "answer": final_answer,
        "used_real_llm": True,
        "fallback_reason": "",
    }


def _assistant_message_for_history(message: dict) -> dict:
    return {
        "role": "assistant",
        "content": message.get("content") or "",
        "tool_calls": message.get("tool_calls") or [],
    }


def _normalize_history_messages(history_messages: list[dict]) -> list[dict]:
    normalized = []
    for item in history_messages[-8:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def _thinking_block(round_num: int, model_name: str, finish_reason: str, tool_calls: list[dict]) -> dict:
    if tool_calls:
        tool_names = []
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            tool_names.append(str(function.get("name") or "unknown"))
        content = (
            "模型判断当前问题需要外部知识库支撑，进入 ReAct 检索流程。\n"
            f"本轮准备调用工具：{', '.join(tool_names)}。"
        )
    elif finish_reason == "stop":
        content = "模型判断当前上下文已经足够，未继续调用检索工具，进入最终回答阶段。"
    else:
        content = f"模型返回 finish_reason={finish_reason or 'unknown'}，后端将根据已有上下文推进到最终回答。"
    return {
        "type": "thinking",
        "title": f"模型思考过程 第 {round_num} 轮",
        "content": content,
        "metadata": {
            "mode": "public_decision_log",
            "model": model_name,
            "round": round_num,
            "finish_reason": finish_reason or "",
            "tool_count": len(tool_calls),
        },
    }


def _parse_tool_call(tool_call: dict) -> tuple[str, dict]:
    function = tool_call.get("function") or {}
    tool_name = str(function.get("name") or "search_bilingual")
    if tool_name not in AVAILABLE_TOOLS:
        tool_name = "search_bilingual"
    raw_arguments = function.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
    except json.JSONDecodeError:
        arguments = {"query": str(raw_arguments)}
    if not isinstance(arguments, dict):
        arguments = {"query": str(arguments)}
    return tool_name, arguments


def _call_openai_choice(
    model_name: str,
    runtime: dict,
    messages: list[dict],
    tools: list[dict] | None,
    tool_choice: str | None,
    max_tokens: int,
) -> dict:
    base_url = runtime["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
    if tool_choice:
        payload["tool_choice"] = tool_choice
    extra_body = runtime.get("extra_body") or {}
    if isinstance(extra_body, dict):
        payload.update(extra_body)
    if runtime.get("reasoning_effort"):
        payload["reasoning_effort"] = runtime["reasoning_effort"]
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {runtime['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("模型响应中没有 choices。")
    return choices[0]


def _resolve_runtime_config(model_name: str, model_config: dict | None) -> dict:
    local_config = _find_local_model_config(model_name)
    if local_config:
        base_url = local_config.get("base_url", "")
        model = local_config.get("model") or local_config.get("model_id") or model_name
        api_key = local_config.get("api_key", "")
        provider = local_config.get("provider") or (model_config or {}).get("provider", "")
        extra_body = local_config.get("extra_body") or _default_extra_body(model, provider)
        reasoning_effort = local_config.get("reasoning_effort") or _default_reasoning_effort(model)
    else:
        base_url = settings.llm_base_url or (model_config or {}).get("base_url", "")
        model = settings.llm_model or model_name
        api_key = settings.llm_api_key
        provider = settings.llm_provider or (model_config or {}).get("provider", "")
        extra_body = _default_extra_body(model, provider)
        reasoning_effort = _default_reasoning_effort(model)
    return {
        "enabled": bool(api_key and base_url and model and not (model_config or {}).get("is_mock", False)),
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "provider": provider,
        "extra_body": extra_body,
        "reasoning_effort": reasoning_effort,
    }


def _find_local_model_config(model_name: str) -> dict[str, str] | None:
    normalized_name = model_name.lower()
    direct = settings.llm_model_configs.get(normalized_name)
    if direct:
        return direct
    for config in settings.llm_model_configs.values():
        model = (config.get("model") or config.get("model_id") or "").lower()
        alias = (config.get("name") or "").lower()
        if normalized_name in {model, alias}:
            return config
    return None


def _default_extra_body(model: str, provider: str) -> dict:
    normalized = f"{provider} {model}".lower()
    if "mimo" in normalized:
        return {}
    if "deepseek" in normalized or "doubao" in normalized:
        return {"thinking": {"type": "enabled"}}
    if "kimi" in normalized or "qwen" in normalized or "glm" in normalized:
        return {"enable_thinking": True}
    return {}


def _default_reasoning_effort(model: str) -> str:
    if "deepseek-v4" in model.lower():
        return "high"
    return ""
