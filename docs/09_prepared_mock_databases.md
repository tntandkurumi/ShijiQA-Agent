# 预置模拟数据库与检索接口说明

当前阶段没有真实数据文件夹和真实向量库，因此后端使用“预置数据 + 原检索脚本接口形状 + 模拟 Embedding/Collection”的方式模拟数据库存在。

## 核心约束

- 不在用户问题下临时编造检索数据。
- 只有真实模型通过 tool calling 明确调用工具时，后端才执行对应检索器。
- 未配置真实模型时，不主动检索预置数据库。
- 每个工具只访问自己的预置数据库，不再混用一个临时知识条目表。

## 对应关系

| 工具名 | 对应脚本 | 模拟方式 |
| --- | --- | --- |
| `search_bilingual` | `research_code/retrieval/双语数据库_检索.py` | 预置双语段落，模拟稠密检索、BM25 稀疏检索和 RRF 融合 |
| `search_person` | `research_code/retrieval/人物数据库_检索.py` | 注入预置 `CBDB_DICT`、`CNG_DICT`，沿用别名映射和 JSON 精确匹配 |
| `search_poetry` | `research_code/retrieval/诗文数据库_检索.py` | 注入预置 `POEMS`，沿用作者精确匹配和标题包含匹配 |
| `search_official_positions` | `research_code/retrieval/官职数据库_检索.py` | 预置官职 Collection，沿用精确匹配优先、否则向量距离分组 |
| `search_geography` | `research_code/retrieval/地理数据库_检索.py` | 预置地理 Collection，沿用精确匹配优先、否则向量距离分组 |
| `search_historical_events` | `research_code/retrieval/典故事件数据库_检索.py` | 预置事件 Collection，沿用精确匹配优先、否则向量距离分组 |
| `search_terminology` | `research_code/retrieval/术语句法数据库_检索.py` | 预置术语 Collection，沿用精确匹配优先、否则向量距离分组 |
| `search_knowledge_graph` | `research_code/retrieval/知识图谱数据_检索.py` | 注入预置实体三元组，沿用实体映射优先、否则向量近邻实体 |

## 后端文件

- 预置数据和检索适配器：`wenyuan-api/app/services/prepared_retrieval.py`
- Agent 工具调用入口：`wenyuan-api/app/services/agent_service.py`

## 后续替换真实数据

后续接入真实数据时，应保留 `agent_service.py` 的工具调用协议，只替换 `prepared_retrieval.py`：

- 将预置数据替换为真实 JSON 文件。
- 将 `PreparedEmbeddingModel` 替换为真实 `SentenceTransformer`。
- 将 `PreparedCollection` 替换为真实 ChromaDB collection。
- 双语检索恢复真实 BM25 索引和段落映射。
