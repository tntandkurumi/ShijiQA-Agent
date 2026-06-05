"""
主程序：统一加载模型和数据库，调用各检索模块

支持类型：
    - 官职（向量数据库）
    - 地理（向量数据库）
    - 典故事件（向量数据库）
    - 术语（向量数据库）
    - 知识图谱（向量数据库 + 三元组索引）
    - 人物（JSON 精确匹配，无向量）
    - 诗文（JSON 模糊/精确匹配，无向量）
    - 双语（稠密向量 + BM25 混合检索）

使用方法：
    1. 修改变量 `db_type` 和对应查询参数。
    2. 运行脚本。
"""

import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.errors import NotFoundError

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = RESEARCH_ROOT / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

# -------------------- 公共配置 --------------------
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"

# 向量数据库路径及集合名
OFFICIAL_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_official"
OFFICIAL_COLLECTION = "official_positions"

GEO_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_geo"
GEO_COLLECTION = "geography_info"

EVENT_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_event"
EVENT_COLLECTION = "event_info"

TERM_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_term"
TERM_COLLECTION = "term_info"

KG_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_kg"
KG_COLLECTION = "kg_entities"

BILINGUAL_DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_bilingual"
BILINGUAL_COLLECTION = "bilingual_sentences"

# -------------------- 用户输入 --------------------
db_type = "双语"      # 可选：官职,地理,典故事件,术语,知识图谱,人物,诗文,双语

# 对于官职、地理、典故事件、术语、知识图谱、人物、双语，使用 query_str
query_str = "周迪占据临起兵，陈详从州的其他路袭击旦迪于的别营，捕获了他的妻儿。"

# 对于诗文，使用 author_str 和 title_str（至少一个非空）
author_str = "陈叔宝"
title_str = "祓禊"

# -------------------- 1. 加载模型（需要向量的类型） --------------------
need_model = db_type in ["官职", "地理", "典故事件", "术语", "知识图谱", "双语"]
if need_model:
    print("正在加载嵌入模型...")
    try:
        model = SentenceTransformer(
            MODEL_PATH,
            tokenizer_kwargs={"padding_side": "left"},
            model_kwargs={"device_map": "auto"}
        )
        print("模型加载完成。")
    except Exception as e:
        print(f"模型加载失败：{e}")
        exit(1)
else:
    model = None

# -------------------- 2. 连接向量数据库或导入检索模块 --------------------
print("连接数据库/加载模块...")

if db_type == "官职":
    from 官职数据库_检索 import retrieve
    client = chromadb.PersistentClient(path=OFFICIAL_DB_PATH)
    try:
        collection = client.get_collection(OFFICIAL_COLLECTION)
        print(f"成功加载集合 {OFFICIAL_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {OFFICIAL_COLLECTION} 不存在，请先运行建库脚本。")
        exit(1)

elif db_type == "地理":
    from 地理数据库_检索 import retrieve
    client = chromadb.PersistentClient(path=GEO_DB_PATH)
    try:
        collection = client.get_collection(GEO_COLLECTION)
        print(f"成功加载集合 {GEO_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {GEO_COLLECTION} 不存在，请先运行建库脚本。")
        exit(1)

elif db_type == "典故事件":
    from 典故事件数据库_检索 import retrieve
    client = chromadb.PersistentClient(path=EVENT_DB_PATH)
    try:
        collection = client.get_collection(EVENT_COLLECTION)
        print(f"成功加载集合 {EVENT_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {EVENT_COLLECTION} 不存在，请先运行建库脚本。")
        exit(1)

elif db_type == "术语":
    from 术语句法数据库_检索 import retrieve
    client = chromadb.PersistentClient(path=TERM_DB_PATH)
    try:
        collection = client.get_collection(TERM_COLLECTION)
        print(f"成功加载集合 {TERM_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {TERM_COLLECTION} 不存在，请先运行建库脚本。")
        exit(1)

elif db_type == "知识图谱":
    from 知识图谱数据_检索 import retrieve
    client = chromadb.PersistentClient(path=KG_DB_PATH)
    try:
        collection = client.get_collection(KG_COLLECTION)
        print(f"成功加载集合 {KG_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {KG_COLLECTION} 不存在，请先运行建库脚本。")
        exit(1)

elif db_type == "双语":
    from 双语数据库_检索 import retrieve
    client = chromadb.PersistentClient(path=BILINGUAL_DB_PATH)
    try:
        collection = client.get_collection(BILINGUAL_COLLECTION)
        print(f"成功加载集合 {BILINGUAL_COLLECTION}")
    except NotFoundError:
        print(f"错误：集合 {BILINGUAL_COLLECTION} 不存在，请先运行向量生成脚本。")
        exit(1)

elif db_type == "人物":
    from 人物数据库_检索 import retrieve
    collection = None
    print("人物数据库已准备就绪。")

elif db_type == "诗文":
    from 诗文数据库_检索 import retrieve
    collection = None
    print("诗文数据库已准备就绪。")

else:
    print("错误：数据库类型必须是 '官职','地理','典故事件','术语','知识图谱','人物','诗文','双语'")
    exit(1)

# -------------------- 3. 调用检索 --------------------
if db_type in ["官职", "地理", "典故事件", "术语"]:
    result = retrieve(model, collection, query_str)
elif db_type == "知识图谱":
    result = retrieve(model, collection, query_str)
elif db_type == "双语":
    result = retrieve(model, collection, query_str)
elif db_type == "人物":
    result = retrieve(query_str)
elif db_type == "诗文":
    result = retrieve(author_str, title_str)

print("\n检索结果：\n")
print(result)
