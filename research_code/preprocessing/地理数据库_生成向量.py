import subprocess
import os

result = subprocess.run('bash -c "source /etc/network_turbo && env | grep proxy"', shell=True, capture_output=True, text=True)
output = result.stdout
for line in output.splitlines():
    if '=' in line:
        var, value = line.split('=', 1)
        os.environ[var] = value
"""
地理数据库向量化生成脚本

功能：
    读取地理数据库 CSV 文件（包含“标题”和“内容”两列），
    使用 Qwen3-Embedding-8B 模型对“标题”列进行嵌入，
    将嵌入向量、标题（作为文档）以及内容（作为元数据）存入 ChromaDB 持久化集合。

数据文件：
    /root/autodl-tmp/毕业论文/数据库5-地理数据库/地理筛选结果.csv

模型路径：
    /root/autodl-tmp/Qwen3-Embedding-8B

输出：
    持久化 ChromaDB 数据库，存储于 /root/autodl-tmp/毕业论文/chromadb_geo
    集合名称：geography_info

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
CSV_PATH = "/root/autodl-tmp/毕业论文/数据库5-地理数据库/地理筛选结果.csv"
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"
DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_geo"        # 向量数据库持久化路径
COLLECTION_NAME = "geography_info"
BATCH_SIZE = 32                     # 每批处理条数，根据显存调整
PROMPT = "为古代地理检索任务生成嵌入向量"
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
if '标题' not in df.columns:
    raise ValueError("CSV文件中缺少'标题'列")
if '内容' not in df.columns:
    raise ValueError("CSV文件中缺少'内容'列")

# 处理空值：将NaN替换为空字符串，确保标题和内容都是字符串类型
df['标题'] = df['标题'].fillna('').astype(str)
df['内容'] = df['内容'].fillna('').astype(str)

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
    
    # 获取标题列表
    titles = batch_df['标题'].tolist()
    
    # 生成嵌入向量
    batch_embeddings = model.encode(
        titles,
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
        
        # 文档内容：标题（用于精确匹配和文本检索）
        batch_documents.append(row['标题'])
        
        # 元数据：包含内容字段（也可以包含标题，但文档已是标题，可选）
        meta = {
            '内容': row['内容']   # 存储内容作为元数据，便于后续直接展示
        }
        # 如果希望保留标题也在元数据中，可取消下一行注释
        # meta['标题'] = row['标题']
        batch_metadatas.append(meta)
        batch_embeddings_list.append(batch_embeddings[j])
    
    # 将当前批次数据添加到集合
    collection.add(
        embeddings=batch_embeddings_list,
        documents=batch_documents,
        metadatas=batch_metadatas,
        ids=batch_ids
    )

print(f"成功将 {total_rows} 条地理数据的嵌入向量存入ChromaDB集合 '{COLLECTION_NAME}'。")
print(f"向量数据库持久化位置: {DB_PATH}")