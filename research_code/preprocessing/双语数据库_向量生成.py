"""
双语数据库向量化生成脚本

功能：
    遍历指定目录下的所有 JSON 文件，提取每个 JSON 中的 content 列表，
    对每个对象的 "modern" 字段文本按句号（。！？）切分为句子，
    使用 Qwen3-Embedding-8B 模型对每个句子进行嵌入，
    将嵌入向量、句子内容（作为文档）以及元数据（文件名、标题、段落索引、句子索引）
    存入 ChromaDB 持久化集合。

数据目录：
    /root/autodl-tmp/毕业论文/数据库1-双语数据库

模型路径：
    /root/autodl-tmp/Qwen3-Embedding-8B

输出：
    持久化 ChromaDB 数据库，存储于 /root/autodl-tmp/毕业论文/chromadb_bilingual
    集合名称：bilingual_sentences

依赖库：
    sentence_transformers, chromadb, tqdm, glob, json, re
"""

import json
import os
import re
import glob
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from chromadb.errors import NotFoundError

# -------------------- 配置 --------------------
DATA_DIR = "/root/autodl-tmp/毕业论文/数据库1-双语数据库"
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"
DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_bilingual"
COLLECTION_NAME = "bilingual_sentences"
BATCH_SIZE = 32                     # 每批处理的句子数
PROMPT = "为古籍白话文检索任务生成嵌入向量"
DROP_IF_EXISTS = True               # 是否删除已存在的同名集合（重新构建）

# 分句正则：匹配句号、感叹号、问号、分号等常见句子结束符
SENTENCE_SPLIT_PATTERN = re.compile(r'[。！？；]+')

# -------------------- 1. 加载模型 --------------------
print("正在加载嵌入模型...")
model = SentenceTransformer(
    MODEL_PATH,
    tokenizer_kwargs={"padding_side": "left"},
    model_kwargs={"device_map": "auto"}  # 不启用 flash_attention_2
)
print("模型加载完成。")

# -------------------- 2. 准备 ChromaDB --------------------
print("初始化 ChromaDB 持久化客户端...")
os.makedirs(DB_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=DB_PATH)

if DROP_IF_EXISTS:
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"已删除现有集合: {COLLECTION_NAME}")
    except NotFoundError:
        print(f"集合 {COLLECTION_NAME} 不存在，无需删除。")

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)
print(f"ChromaDB 集合 '{COLLECTION_NAME}' 已就绪，持久化路径: {DB_PATH}")

# -------------------- 3. 遍历 JSON 文件，提取句子 --------------------
json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
print(f"找到 {len(json_files)} 个 JSON 文件。")

all_sentences = []          # 存储每个句子的文本
all_metadata = []           # 存储每个句子的元数据
all_doc_ids = []            # 存储每个句子的唯一 ID

for file_path in tqdm(json_files, desc="处理文件"):
    file_name = os.path.basename(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        continue

    title = data.get("title", "")
    content_list = data.get("content", [])
    if not content_list:
        continue

    for para_idx, para_obj in enumerate(content_list):
        modern_text = para_obj.get("modern", "")
        if not modern_text:
            continue
        # 按标点切分句子
        sentences = SENTENCE_SPLIT_PATTERN.split(modern_text)
        # 去除空串、首尾空格
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            continue
        for sent_idx, sentence in enumerate(sentences):
            # 生成唯一 ID
            doc_id = str(uuid.uuid4())
            all_doc_ids.append(doc_id)
            all_sentences.append(sentence)
            all_metadata.append({
                "source_file": file_name,
                "title": title,
                "paragraph_index": para_idx,
                "sentence_index": sent_idx,
                # 可选：保留原始段落中的位置信息（如字符起始位置），这里不实现
            })

print(f"共提取 {len(all_sentences)} 个句子。")

# -------------------- 4. 分批生成嵌入并存入数据库 --------------------
total = len(all_sentences)
print("开始分批生成向量并存入 ChromaDB...")

for i in tqdm(range(0, total, BATCH_SIZE), desc="生成嵌入"):
    batch_sentences = all_sentences[i:i+BATCH_SIZE]
    batch_metas = all_metadata[i:i+BATCH_SIZE]
    batch_ids = all_doc_ids[i:i+BATCH_SIZE]

    # 生成嵌入
    try:
        batch_embeddings = model.encode(
            batch_sentences,
            prompt=PROMPT,
            convert_to_numpy=True,
            show_progress_bar=False
        )
    except Exception as e:
        print(f"嵌入生成失败: {e}")
        continue

    # 添加到集合
    collection.add(
        embeddings=batch_embeddings.tolist(),
        documents=batch_sentences,
        metadatas=batch_metas,
        ids=batch_ids
    )

print(f"成功将 {total} 个句子存入 ChromaDB 集合 '{COLLECTION_NAME}'。")
print(f"向量数据库持久化位置: {DB_PATH}")