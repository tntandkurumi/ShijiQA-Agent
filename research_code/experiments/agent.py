# -*- coding: utf-8 -*-
"""
《陈书》多源异构知识问答 Agent —— 基于 DeepSeek V4 Pro + ReAct 范式
（优化工具描述与迭代限制，防止无限循环）
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI
import chromadb
from sentence_transformers import SentenceTransformer

# ================== 配置区域 ==================
RESEARCH_ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = RESEARCH_ROOT / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-v4-pro"

MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"

CHROMA_PATHS = {
    "bilingual": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_bilingual",
        "collection": "bilingual_sentences"
    },
    "official": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_official",
        "collection": "official_positions"
    },
    "geography": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_geo",
        "collection": "geography_info"
    },
    "event": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_event",
        "collection": "event_info"
    },
    "term": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_term",
        "collection": "term_info"
    },
    "kg": {
        "path": "/root/autodl-tmp/毕业论文/chromadb_kg",
        "collection": "kg_entities"
    }
}

# ================== 工具定义（已优化） ==================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_bilingual",
            "description": (
                "检索古籍现代汉语与古文对照的段落。融合稠密语义检索与稀疏关键词匹配（RRF），"
                "返回现代文译文及对应的古文原文。适用于将现代文表述映射回《陈书》等史籍的具体段落。"
                "输入应为现代汉语文本片段（也可使用《陈书》古文原文，但建议使用现代文以获得最佳匹配），"
                "不能填入零散关键词，推荐使用完整句子或段落。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "现代汉语句子或完整的文本片段，例如'周迪占据临川起兵，陈详从别路袭击其营地，俘获其妻儿'。不建议使用单个关键词。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_person",
            "description": (
                "检索历史人物详细档案，含生平、官职、家族、著述等。"
                "宜使用规范完整的姓名（如‘陈霸先’、‘陈叔宝’），尽量避免别称或庙号，"
                "但系统仍会对常用别名进行自动映射。当需要某位人物的权威传记信息时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "人物规范姓名，如‘陈霸先’、‘姚察’。也可以使用常见别名（如‘陈武帝’），但建议优先使用完整姓名。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_poetry",
            "description": (
                "检索古诗文作品。作者请务必使用规范完整姓名（如‘陈叔宝’，不要用‘后主’），"
                "标题支持部分字词匹配（如‘祓禊’）。当需查找某位文人的诗作或特定篇目时使用，"
                "至少须提供作者或标题之一。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author": {
                        "type": "string",
                        "description": "作者规范姓名，如‘陈叔宝’。建议使用完整姓名，勿用别名（如‘后主’）。可留空，但此时必须提供title。"
                    },
                    "title": {
                        "type": "string",
                        "description": "诗题中的关键词，如'祓禊'，支持部分匹配。可留空，但此时必须提供author。"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_positions",
            "description": (
                "检索古代官职信息。仅接受官职名称作为输入（如‘丞相’、‘给事中’），"
                "不支持职责描述或模糊概念（例如不能输入‘负责刑狱的官职’）。"
                "返回该官职的品阶、隶属、沿革等详细记载。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "准确的官职名称，例如‘丞相’、‘给事中’。不能是职责说明或相关描述。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_geography",
            "description": (
                "检索古代地理信息，包含地名沿革、地理位置、山川城池等。"
                "输入为古代地名或地理关键词（如‘建康’、‘秦淮河’），可返回该地的详细历史记载。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "古代地名或地理关键词，如‘建康’、‘淮南道’。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_historical_events",
            "description": (
                "检索历史典故事件、战役、政变等。输入事件名称或典故关键词"
                "（如‘侯景之乱’、‘淝水之战’），返回事件背景、经过、相关人物及后世引用例句。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "事件名称或典故关键词，如‘侯景之乱’、‘萧墙之祸’。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_terminology",
            "description": (
                "检索古代汉语术语、专有名词、制度用语的精准释义。"
                "输入待解释的术语或古汉语词汇（如‘祓禊’、‘丁忧’），返回简明解释，适用于文言文训诂。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "待解释的术语或古汉语词汇，如‘祓禊’、‘践祚’。"
                    }
                },
                "required": ["query"]
            }
        }
    },  # ← 此处必须有逗号
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_graph",
            "description": (
                "查询知识图谱中人物、官职、地名等实体之间的结构化关系。"
                "输入任意实体名称（如‘陈霸先’、‘丞相’、‘台城’），可返回与之相关的所有关系三元组，"
                "包括但不限于：亲属关系、官职隶属、地理归属、战役胜负、政权更迭等。"
                "凡是需要厘清\"谁与谁有什么关系\"\"某地属于谁\"\"某人担任何职\"等逻辑关系的问题，都应优先使用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "实体名称，如‘陈霸先’、‘吴明彻’、‘台城’。"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# ================== Agent 类 ==================
class ChenShuAgent:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.messages = [{"role": "system", "content": self.system_prompt}]

        self.model_embed = None
        self.chroma_clients = {}
        self._load_resources()

    def _build_system_prompt(self) -> str:
        return (
            "你是一个精通《陈书》及相关南朝历史的高级研究助手，背后接入了多源异构古籍数据库。\n"
            "你的知识库覆盖《陈书》的现代文对照、人物传记、诗文作品、官职制度、地理沿革、\n"
            "典故战争、术语解释以及知识图谱（人物、官职、地名间的关系网络）。\n\n"
            "## 核心原则（ReAct 范式）\n"
            "1. **所有回答必须基于工具返回的真实数据**，严禁凭空编造史实。\n"
            "2. **若问题明确涉及《陈书》的人物、事件、地理、制度等，你必须至少调用一次工具进行检索**，\n"
            "   即使你自认为知道答案，也必须通过工具验证或补充细节。\n"
            "3. **你可以一次性并行调用多个工具**，例如同时查人物传记和知识图谱关系，以提高效率。\n"
            "4. **完成第一轮工具调用后，仔细分析返回结果。如果信息仍不充分，或需要进一步追问细节，\n"
            "   必须继续调用工具**，但**最多进行 5 轮工具调用**。请高效规划查询，避免冗长反复。\n"
            "5. **只有当所有必要信息均已获取，且无需更多工具时，你才能生成最终答案**。\n"
            "6. 最终答案应条理清晰，尽量引用原文依据（如古文原文或现代文出处），并注明信息来源。\n\n"
            "## 工具使用要点\n"
            "- 查询人物关系、隶属、血缘时，优先使用 `search_knowledge_graph`。\n"
            "- 将现代文描述映射回《陈书》段落，请使用 `search_bilingual`，输入完整的现代文句子。\n"
            "- 官职必须输入准确名称，诗文作者必须用规范完整姓名。\n"
            "- 如果工具返回空结果或报错，可尝试更换同义词、更规范的名称或组合其他工具。\n\n"
            "## 输出规范\n"
            "- 你的思考过程会与最终答案分开显示，请专注于推理和决策。\n"
            "- 最终答案使用流畅的中文，适当引用古文或现代文段落。"
        )

    def _load_resources(self):
        """加载嵌入模型和 ChromaDB 集合"""
        print("正在加载嵌入模型...")
        try:
            self.model_embed = SentenceTransformer(
                MODEL_PATH,
                tokenizer_kwargs={"padding_side": "left"},
                model_kwargs={"device_map": "auto"}
            )
            print("模型加载完成。")
        except Exception as e:
            print(f"模型加载失败：{e}")
            sys.exit(1)

        for key, cfg in CHROMA_PATHS.items():
            try:
                client = chromadb.PersistentClient(path=cfg["path"])
                coll = client.get_collection(cfg["collection"])
                self.chroma_clients[key] = (client, coll)
                print(f"已连接 ChromaDB: {cfg['collection']}")
            except Exception as e:
                print(f"连接 {cfg['collection']} 失败：{e}，工具 {key} 可能不可用。")
                self.chroma_clients[key] = None

    def _call_tool(self, tool_name: str, arguments: dict) -> str:
        """执行实际的工具调用，返回格式化字符串"""
        try:
            if tool_name == "search_bilingual":
                from 双语数据库_检索 import retrieve
                coll = self.chroma_clients.get("bilingual")
                if coll is None:
                    return "错误：未连接双语数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            elif tool_name == "search_person":
                from 人物数据库_检索 import retrieve
                return retrieve(arguments["query"])

            elif tool_name == "search_poetry":
                from 诗文数据库_检索 import retrieve
                author = arguments.get("author", "")
                title = arguments.get("title", "")
                if not author and not title:
                    return "错误：至少需要提供作者或标题。"
                return retrieve(author, title)

            elif tool_name == "search_official_positions":
                from 官职数据库_检索 import retrieve
                coll = self.chroma_clients.get("official")
                if coll is None:
                    return "错误：未连接官职数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            elif tool_name == "search_geography":
                from 地理数据库_检索 import retrieve
                coll = self.chroma_clients.get("geography")
                if coll is None:
                    return "错误：未连接地理数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            elif tool_name == "search_historical_events":
                from 典故事件数据库_检索 import retrieve
                coll = self.chroma_clients.get("event")
                if coll is None:
                    return "错误：未连接典故事件数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            elif tool_name == "search_terminology":
                from 术语句法数据库_检索 import retrieve
                coll = self.chroma_clients.get("term")
                if coll is None:
                    return "错误：未连接术语数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            elif tool_name == "search_knowledge_graph":
                from 知识图谱数据_检索 import retrieve
                coll = self.chroma_clients.get("kg")
                if coll is None:
                    return "错误：未连接知识图谱数据库。"
                _, collection = coll
                return retrieve(self.model_embed, collection, arguments["query"])

            else:
                return f"未知工具：{tool_name}"

        except Exception as e:
            return f"工具执行错误：{str(e)}"

    def run(self, user_query: str, max_rounds: int = 5) -> str:
        """ReAct 主循环，限制最大轮次"""
        self.messages.append({"role": "user", "content": user_query})
        final_output = []

        for round_num in range(1, max_rounds + 1):
            print(f"\n{'='*40} 第 {round_num} 轮 {'='*40}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}}
            )

            msg = response.choices[0].message
            finish = response.choices[0].finish_reason

            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                think = msg.reasoning_content
                print(f"[思考]\n{think}")
                final_output.append(f"[思考]\n{think}")

            if finish == "tool_calls":
                self.messages.append(msg)

                tool_results = []
                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    print(f"→ 调用工具：{name}, 参数：{args}")
                    result_str = self._call_tool(name, args)
                    display = result_str[:300] + ("..." if len(result_str) > 300 else "")
                    print(f"← 返回结果（前300字符）：\n{display}")
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str
                    })

                self.messages.extend(tool_results)
                continue

            elif finish == "stop":
                answer = msg.content
                print(f"[最终回答]\n{answer}")
                final_output.append(f"[最终回答]\n{answer}")
                self.messages.append(msg)
                return "\n\n".join(final_output)

            else:
                print(f"未知 finish_reason：{finish}")
                break

        return "\n\n".join(final_output) + "\n（已达到最大 5 轮工具调用，过程结束。）"


# ================== 主程序 ==================
def main():
    if not API_KEY or API_KEY == "your-api-key-here":
        print("请设置环境变量 DEEPSEEK_API_KEY 或修改代码中的 API_KEY。")
        sys.exit(1)

    agent = ChenShuAgent(api_key=API_KEY, base_url=BASE_URL, model=MODEL_NAME)

    print("=" * 60)
    print("《陈书》知识问答 Agent (ReAct + 关系图谱增强)")
    print("输入 'exit' 或 'quit' 退出")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n请输入问题：").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input:
            continue

        result = agent.run(user_input)


if __name__ == "__main__":
    main()
