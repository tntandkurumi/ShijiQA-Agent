"""
术语句法数据库向量化生成脚本

功能：
    读取术语 CSV 文件（包含“术语词”“解释”两列），
    使用 Qwen3-Embedding-8B 模型对“术语词”列进行嵌入，
    将嵌入向量、术语词（作为文档）以及解释（作为元数据）存入 ChromaDB 持久化集合。

数据文件：
    /root/autodl-tmp/毕业论文/数据库7-术语句法数据库/术语.csv

模型路径：
    /root/autodl-tmp/Qwen3-Embedding-8B

输出：
    持久化 ChromaDB 数据库，存储于 /root/autodl-tmp/毕业论文/chromadb_term
    集合名称：term_info

依赖库：
    pandas, sentence_transformers, chromadb, tqdm
"""

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import uuid
import os
from chromadb.errors import NotFoundError

# -------------------- 配置 --------------------
CSV_PATH = "/root/autodl-tmp/毕业论文/数据库7-术语句法数据库/术语.csv"
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"
DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_term"        # 向量数据库持久化路径
COLLECTION_NAME = "term_info"
BATCH_SIZE = 32                     # 每批处理条数，根据显存调整
PROMPT = "为古代汉语术语检索任务生成嵌入向量"
DROP_IF_EXISTS = True               # 是否删除已存在的同名集合（重新构建）

# -------------------- 1. 加载模型 --------------------
print("正在加载嵌入模型...")
model = SentenceTransformer(
    MODEL_PATH,
    tokenizer_kwargs={"padding_side": "left"},
    model_kwargs={"device_map": "auto"}  # 不启用 flash_attention_2
)
print("模型加载完成。")

# -------------------- 2. 读取CSV数据 --------------------
print(f"正在读取CSV文件: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, encoding='utf-8')  # 如果乱码可尝试 encoding='gbk'
print(f"数据总行数: {len(df)}")
print(f"数据列: {df.columns.tolist()}")

# 确保所需列存在
required_cols = ['术语词', '解释']
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"CSV文件中缺少'{col}'列")

# 处理空值：将NaN替换为空字符串
df['术语词'] = df['术语词'].fillna('').astype(str)
df['解释'] = df['解释'].fillna('').astype(str)

# -------------------- 3. 准备ChromaDB持久化存储 --------------------
print("初始化ChromaDB持久化客户端...")
os.makedirs(DB_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=DB_PATH)

# 如果集合已存在且允许删除，则删除重建
if DROP_IF_EXISTS:
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"已删除现有集合: {COLLECTION_NAME}")
    except NotFoundError:
        print(f"集合 {COLLECTION_NAME} 不存在，无需删除。")

# 创建或获取集合
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
)
print(f"ChromaDB集合 '{COLLECTION_NAME}' 已准备就绪，持久化路径: {DB_PATH}")

# -------------------- 4. 分批生成嵌入并存入数据库 --------------------
total_rows = len(df)
print("开始生成嵌入并存入ChromaDB...")

for i in tqdm(range(0, total_rows, BATCH_SIZE), desc="处理批次"):
    batch_df = df.iloc[i:i+BATCH_SIZE]
    
    # 获取术语词列表
    terms = batch_df['术语词'].tolist()
    
    # 生成嵌入向量
    batch_embeddings = model.encode(
        terms,
        convert_to_numpy=True,
        show_progress_bar=False
    )
    
    # 准备当前批次的数据
    batch_ids = []
    batch_documents = []
    batch_metadatas = []
    batch_embeddings_list = []
    
    for j, (idx, row) in enumerate(batch_df.iterrows()):
        doc_id = str(uuid.uuid4())
        batch_ids.append(doc_id)
        
        # 文档内容：术语词（用于精确匹配和文本检索）
        batch_documents.append(row['术语词'])
        
        # 元数据：解释字段
        meta = {
            '解释': row['解释']
        }
        # 如果希望保留术语词也在元数据中，可取消下一行注释
        # meta['术语词'] = row['术语词']
        batch_metadatas.append(meta)
        batch_embeddings_list.append(batch_embeddings[j])
    
    # 将当前批次数据添加到集合
    collection.add(
        embeddings=batch_embeddings_list,
        documents=batch_documents,
        metadatas=batch_metadatas,
        ids=batch_ids
    )

print(f"成功将 {total_rows} 条术语数据的嵌入向量存入ChromaDB集合 '{COLLECTION_NAME}'。")
print(f"向量数据库持久化位置: {DB_PATH}")