"""
知识图谱实体向量化生成脚本

功能：
    从《陈书》知识图谱 JSON 文件中提取所有唯一实体（subject 和 object），
    使用 Qwen3-Embedding-8B 模型对实体名称进行嵌入，
    将实体名称作为文档，实体名称同时作为元数据，存入 ChromaDB 集合。
    同时构建实体到三元组的索引，以便快速检索。

数据文件：
    /root/autodl-tmp/毕业论文/数据库9-知识图谱/《陈书》知识图谱.json
    /root/autodl-tmp/毕业论文/数据库9-知识图谱/实体映射.json

模型路径：
    /root/autodl-tmp/Qwen3-Embedding-8B

输出：
    持久化 ChromaDB 数据库，存储于 /root/autodl-tmp/毕业论文/chromadb_kg
    集合名称：kg_entities
    并保存一个实体到三元组的索引文件（可选，也可以每次检索时加载）

依赖库：
    pandas, sentence_transformers, chromadb, tqdm (可选)
"""

import json
import os
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from chromadb.errors import NotFoundError

# -------------------- 配置 --------------------
KG_JSON_PATH = "/root/autodl-tmp/毕业论文/数据库9-知识图谱/《陈书》知识图谱.json"
MAPPING_JSON_PATH = "/root/autodl-tmp/毕业论文/数据库9-知识图谱/实体映射.json"
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"
DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_kg"
COLLECTION_NAME = "kg_entities"
BATCH_SIZE = 32
DROP_IF_EXISTS = True   # 是否重建集合

# -------------------- 加载数据 --------------------
print("加载知识图谱三元组...")
with open(KG_JSON_PATH, 'r', encoding='utf-8') as f:
    triples = json.load(f)   # 预期为列表，每个元素包含 subject, predicate, object
print(f"三元组数量: {len(triples)}")

# 提取所有唯一实体（subject 和 object）
entities = set()
for triple in triples:
    entities.add(triple.get("subject", ""))
    entities.add(triple.get("object", ""))
entities = [e for e in entities if e]   # 去除空字符串
print(f"唯一实体数量: {len(entities)}")

# 构建实体到三元组的映射（主体索引）
subject_to_triples = {}
for triple in triples:
    subj = triple.get("subject", "")
    if subj:
        subject_to_triples.setdefault(subj, []).append(triple)

# 可选：保存映射供检索使用
KG_INDEX_PATH = "/root/autodl-tmp/毕业论文/chromadb_kg/kg_index.json"
os.makedirs(os.path.dirname(KG_INDEX_PATH), exist_ok=True)
with open(KG_INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(subject_to_triples, f, ensure_ascii=False, indent=2)
print(f"实体索引已保存至 {KG_INDEX_PATH}")

# -------------------- 加载模型 --------------------
print("正在加载嵌入模型...")
model = SentenceTransformer(
    MODEL_PATH,
    tokenizer_kwargs={"padding_side": "left"},
    model_kwargs={"device_map": "auto"}
)
print("模型加载完成。")

# -------------------- 准备 ChromaDB --------------------
print("初始化 ChromaDB...")
os.makedirs(DB_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=DB_PATH)

if DROP_IF_EXISTS:
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"已删除旧集合 {COLLECTION_NAME}")
    except NotFoundError:
        pass

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)
print(f"集合 {COLLECTION_NAME} 已就绪")

# -------------------- 批量生成嵌入并存入 --------------------
total = len(entities)
print("开始生成嵌入并存入...")
for i in tqdm(range(0, total, BATCH_SIZE)):
    batch = entities[i:i+BATCH_SIZE]
    # 生成嵌入
    embeddings = model.encode(
        batch,
        convert_to_numpy=True,
        show_progress_bar=False
    )
    # 准备数据
    ids = [str(uuid.uuid4()) for _ in batch]
    documents = batch   # 实体名称作为文档
    metadatas = [{"entity": ent} for ent in batch]   # 元数据中也存储实体名
    # 添加到集合
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas
    )

print(f"成功将 {total} 个实体向量存入 {COLLECTION_NAME}")
print(f"向量数据库路径: {DB_PATH}")