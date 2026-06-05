"""
双语数据库 BM25 索引构建脚本

功能：
    遍历指定目录下的所有 JSON 文件，提取每个 modern 字段并按句号分句，
    对每个句子进行中文分词（jieba）、去除停用词，
    使用 rank_bm25.BM25Okapi 构建索引，
    将 BM25 对象和文档列表保存到文件。

输入：
    - 数据目录: /root/autodl-tmp/毕业论文/数据库1-双语数据库
    - 停用词文件: /root/autodl-tmp/毕业论文/stopwords.txt（可选）

输出：
    - BM25 索引文件: /root/autodl-tmp/毕业论文/chromadb_bilingual/bm25_index.pkl
    - 文档列表文件: /root/autodl-tmp/毕业论文/chromadb_bilingual/bm25_docs.pkl

依赖：
    pip install jieba rank-bm25 tqdm
"""

import json
import os
import glob
import re
import pickle
import jieba
from tqdm import tqdm
from rank_bm25 import BM25Okapi

# -------------------- 配置 --------------------
DATA_DIR = "/root/autodl-tmp/毕业论文/数据库1-双语数据库"
STOPWORDS_PATH = "/root/autodl-tmp/毕业论文/stopwords.txt"
OUTPUT_DIR = "/root/autodl-tmp/毕业论文/chromadb_bilingual"
BM25_INDEX_FILE = os.path.join(OUTPUT_DIR, "bm25_index.pkl")
DOCS_FILE = os.path.join(OUTPUT_DIR, "bm25_docs.pkl")

# 分句正则（同向量生成脚本）
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

# -------------------- 分句 + 分词 --------------------
def tokenize_sentence(sentence, stopwords):
    # 使用 jieba 精确模式分词
    words = jieba.lcut(sentence)
    # 过滤停用词、去除非中文字符（可选，保留数字字母等）
    tokens = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if w in stopwords:
            continue
        # 可选：过滤纯标点符号
        tokens.append(w)
    return tokens

# -------------------- 主流程 --------------------
def main():
    print("加载停用词...")
    stopwords = load_stopwords(STOPWORDS_PATH)
    print(f"停用词数量: {len(stopwords)}")

    # 收集所有 JSON 文件
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    print(f"找到 {len(json_files)} 个 JSON 文件。")

    all_docs = []          # 存储每个句子的原始文本
    all_tokenized = []     # 存储每个句子的分词结果列表

    for file_path in tqdm(json_files, desc="处理文件"):
        file_name = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"读取失败 {file_path}: {e}")
            continue

        title = data.get("title", "")
        content_list = data.get("content", [])
        if not content_list:
            continue

        for para_idx, para_obj in enumerate(content_list):
            modern_text = para_obj.get("modern", "")
            if not modern_text:
                continue
            # 分句
            sentences = SENTENCE_SPLIT_PATTERN.split(modern_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            for sent_idx, sentence in enumerate(sentences):
                # 分词
                tokens = tokenize_sentence(sentence, stopwords)
                if not tokens:
                    continue
                all_docs.append({
                    "text": sentence,
                    "source_file": file_name,
                    "title": title,
                    "paragraph_index": para_idx,
                    "sentence_index": sent_idx
                })
                all_tokenized.append(tokens)

    print(f"共提取 {len(all_docs)} 个有效句子。")

    if not all_docs:
        print("没有提取到任何句子，退出。")
        return

    print("正在构建 BM25 索引...")
    bm25 = BM25Okapi(all_tokenized)

    # 保存索引和文档元信息
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(BM25_INDEX_FILE, 'wb') as f:
        pickle.dump(bm25, f)
    with open(DOCS_FILE, 'wb') as f:
        pickle.dump(all_docs, f)

    print(f"BM25 索引已保存至: {BM25_INDEX_FILE}")
    print(f"文档列表已保存至: {DOCS_FILE}")
    print("索引构建完成！")

if __name__ == "__main__":
    main()