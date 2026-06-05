"""
双语数据库混合检索模块（稠密向量 + BM25 稀疏检索）
修正版：修复 RRF 融合中 meta 为 None 的问题
"""

import json
import os
import re
import pickle
import jieba
from collections import defaultdict
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi

# -------------------- 配置 --------------------
DATA_DIR = "/root/autodl-tmp/毕业论文/数据库1-双语数据库"
STOPWORDS_PATH = "/root/autodl-tmp/毕业论文/stopwords.txt"
BM25_INDEX_DIR = "/root/autodl-tmp/毕业论文/chromadb_bilingual"
BM25_INDEX_FILE = os.path.join(BM25_INDEX_DIR, "bm25_index.pkl")
DOCS_FILE = os.path.join(BM25_INDEX_DIR, "bm25_docs.pkl")

# RRF 参数
K = 60
DENSE_WEIGHT = 0.5
SPARSE_WEIGHT = 0.5
TOP_K_SENTENCE = 20
FINAL_TOP_N = 10

# 分句正则
SENTENCE_SPLIT_PATTERN = re.compile(r'[。！？；]+')

# -------------------- 加载停用词 --------------------
def load_stopwords(path):
    stopwords = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                w = line.strip()
                if w:
                    stopwords.add(w)
    else:
        print(f"警告：停用词文件 {path} 不存在，将不使用停用词。")
    return stopwords

STOPWORDS = load_stopwords(STOPWORDS_PATH)

# -------------------- 分词 --------------------
def tokenize_query(query: str) -> List[str]:
    words = jieba.lcut(query)
    tokens = []
    for w in words:
        w = w.strip()
        if w and w not in STOPWORDS:
            tokens.append(w)
    return tokens

# -------------------- 加载 BM25 索引 --------------------
def load_bm25() -> Tuple[BM25Okapi, List[Dict]]:
    if not os.path.exists(BM25_INDEX_FILE) or not os.path.exists(DOCS_FILE):
        raise FileNotFoundError("BM25 索引文件不存在，请先运行 bilingual_bm25_index.py 构建索引。")
    with open(BM25_INDEX_FILE, 'rb') as f:
        bm25 = pickle.load(f)
    with open(DOCS_FILE, 'rb') as f:
        docs = pickle.load(f)
    return bm25, docs

BM25, BM25_DOCS = load_bm25()

# -------------------- 构建段落内容映射 --------------------
def build_paragraph_map():
    para_map = {}
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    for file_name in json_files:
        file_path = os.path.join(DATA_DIR, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"读取 {file_path} 失败: {e}")
            continue
        content_list = data.get("content", [])
        for para_idx, para_obj in enumerate(content_list):
            modern = para_obj.get("modern", "").strip()
            ancient = para_obj.get("ancient", "").strip()
            if modern or ancient:
                key = (file_name, para_idx)
                para_map[key] = (modern, ancient, data.get("title", ""))
    return para_map

PARAGRAPH_MAP = build_paragraph_map()

# -------------------- 稠密检索 --------------------
def dense_retrieve(model, collection, query: str, top_k: int = TOP_K_SENTENCE):
    try:
        query_emb = model.encode([query], convert_to_numpy=True)[0].tolist()
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        distances = results['distances'][0]
        ranked = []
        for rank, (doc, meta, dist) in enumerate(zip(docs, metas, distances), start=1):
            if meta is None:
                continue  # 跳过无效元数据
            ranked.append((doc, meta, rank))
        return ranked
    except Exception as e:
        print(f"稠密检索失败: {e}")
        return []

# -------------------- 稀疏检索 --------------------
def sparse_retrieve(query: str, top_k: int = TOP_K_SENTENCE):
    tokens = tokenize_query(query)
    if not tokens:
        return []
    try:
        scores = BM25.get_scores(tokens)
    except Exception as e:
        print(f"BM25 计算失败: {e}")
        return []
    indexed_scores = list(enumerate(scores))
    indexed_scores.sort(key=lambda x: x[1], reverse=True)
    top_indices = indexed_scores[:top_k]
    ranked = []
    for rank, (idx, score) in enumerate(top_indices, start=1):
        doc_info = BM25_DOCS[idx]
        sentence_text = doc_info["text"]
        meta = {
            "source_file": doc_info["source_file"],
            "title": doc_info["title"],
            "paragraph_index": doc_info["paragraph_index"],
            "sentence_index": doc_info["sentence_index"]
        }
        ranked.append((sentence_text, meta, rank))
    return ranked

# -------------------- RRF 融合（修正版）--------------------
def rrf_fusion(dense_results, sparse_results, k=K, dense_weight=DENSE_WEIGHT, sparse_weight=SPARSE_WEIGHT):
    sentence_scores = defaultdict(lambda: {
        "rrf": 0.0,
        "dense_rank": float('inf'),
        "sparse_rank": float('inf'),
        "meta": None,
        "sentence": None
    })

    # 稠密结果
    for sentence, meta, rank in dense_results:
        key = (meta["source_file"], meta["paragraph_index"], meta["sentence_index"])
        rrf = dense_weight / (k + rank)
        sentence_scores[key]["rrf"] += rrf
        sentence_scores[key]["dense_rank"] = min(sentence_scores[key]["dense_rank"], rank)
        sentence_scores[key]["meta"] = meta
        sentence_scores[key]["sentence"] = sentence

    # 稀疏结果
    for sentence, meta, rank in sparse_results:
        key = (meta["source_file"], meta["paragraph_index"], meta["sentence_index"])
        rrf = sparse_weight / (k + rank)
        sentence_scores[key]["rrf"] += rrf
        sentence_scores[key]["sparse_rank"] = min(sentence_scores[key]["sparse_rank"], rank)
        # 如果 meta 尚未设置（例如只出现在稀疏结果中），则设置
        if sentence_scores[key]["meta"] is None:
            sentence_scores[key]["meta"] = meta
            sentence_scores[key]["sentence"] = sentence

    # 按段落聚合：每个段落取 RRF 最高的句子，并保留其 dense_rank 和 sparse_rank
    para_best = defaultdict(lambda: {"rrf": -1.0, "dense_rank": float('inf'), "sparse_rank": float('inf'), "sentence_info": None})
    for key, data in sentence_scores.items():
        para_key = (data["meta"]["source_file"], data["meta"]["paragraph_index"])
        rrf = data["rrf"]
        if rrf > para_best[para_key]["rrf"]:
            para_best[para_key]["rrf"] = rrf
            para_best[para_key]["dense_rank"] = data["dense_rank"]
            para_best[para_key]["sparse_rank"] = data["sparse_rank"]
            para_best[para_key]["sentence_info"] = (data["meta"], data["sentence"])
        elif abs(rrf - para_best[para_key]["rrf"]) < 1e-6:
            if data["dense_rank"] < para_best[para_key]["dense_rank"]:
                para_best[para_key]["dense_rank"] = data["dense_rank"]
                para_best[para_key]["sparse_rank"] = data["sparse_rank"]
                para_best[para_key]["sentence_info"] = (data["meta"], data["sentence"])

    para_list = []
    for para_key, data in para_best.items():
        para_list.append({
            "para_key": para_key,
            "rrf": data["rrf"],
            "dense_rank": data["dense_rank"],
            "sparse_rank": data["sparse_rank"],
            "sentence_info": data["sentence_info"]
        })
    para_list.sort(key=lambda x: (-x["rrf"], x["dense_rank"]))
    return para_list

# -------------------- 获取段落完整内容 --------------------
def get_paragraph_content(source_file, para_idx):
    key = (source_file, para_idx)
    if key in PARAGRAPH_MAP:
        modern, ancient, title = PARAGRAPH_MAP[key]
        return modern, ancient, title
    return "", "", ""

# -------------------- 主检索函数 --------------------
def retrieve(model, collection, query_str: str) -> str:
    dense_res = dense_retrieve(model, collection, query_str)
    sparse_res = sparse_retrieve(query_str)
    fused = rrf_fusion(dense_res, sparse_res)
    top_paragraphs = fused[:FINAL_TOP_N] if len(fused) > FINAL_TOP_N else fused
    output_lines = []
    for idx, item in enumerate(top_paragraphs, start=1):
        meta, _ = item["sentence_info"]
        source_file = meta["source_file"]
        para_idx = meta["paragraph_index"]
        modern, ancient, title = get_paragraph_content(source_file, para_idx)
        if not modern and not ancient:
            continue
        output_lines.append(f"\n【结果 {idx}】")
        output_lines.append(f"文件：{source_file}")
        output_lines.append(f"标题：{title}")
        output_lines.append(f"现代文译文：{modern}")
        output_lines.append(f"古文原文：{ancient}")
    if not output_lines:
        return "未找到相关结果。"
    return "\n".join(output_lines)