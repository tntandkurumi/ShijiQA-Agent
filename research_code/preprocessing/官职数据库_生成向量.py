import subprocess
import os

result = subprocess.run('bash -c "source /etc/network_turbo && env | grep proxy"', shell=True, capture_output=True, text=True)
output = result.stdout
for line in output.splitlines():
    if '=' in line:
        var, value = line.split('=', 1)
        os.environ[var] = value

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import uuid
import os
from chromadb.errors import NotFoundError  # 导入 NotFoundError

# -------------------- 配置 --------------------
CSV_PATH = "/root/autodl-tmp/毕业论文/数据库4-官职数据库/历代职官查询结果_增强.csv"
MODEL_PATH = "/root/autodl-tmp/Qwen3-Embedding-8B"
DB_PATH = "/root/autodl-tmp/毕业论文/chromadb_official"  # 向量数据库持久化存储路径
COLLECTION_NAME = "official_positions"
BATCH_SIZE = 32                     # 每批处理的条数，根据显存调整
PROMPT = "为古代官职检索任务生成嵌入向量"
DROP_IF_EXISTS = True                # 是否删除已存在的同名集合（重新构建）

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
df = pd.read_csv(CSV_PATH, encoding='utf-8')  # 如果乱码尝试 encoding='gbk'
# 丢弃"序号"列（如果存在）
if '序号' in df.columns:
    df = df.drop(columns=['序号'])
print(f"数据总行数: {len(df)}")

# 确保官职名称列存在
if '官职名称' not in df.columns:
    raise ValueError("CSV文件中缺少'官职名称'列")

# 处理空值：将NaN替换为空字符串，确保所有官职名称都是字符串类型
df['官职名称'] = df['官职名称'].fillna('').astype(str)

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
        # 集合不存在，忽略
        print(f"集合 {COLLECTION_NAME} 不存在，无需删除。")
        pass

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
    
    # 获取官职名称列表
    office_names = batch_df['官职名称'].tolist()
    
    # 生成嵌入向量
    batch_embeddings = model.encode(
        office_names,
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
        batch_documents.append(row['官职名称'])
        
        meta = {}
        for col in df.columns:
            if col != '官职名称' and pd.notna(row[col]):
                meta[col] = str(row[col])
            elif col != '官职名称' and pd.isna(row[col]):
                meta[col] = ""
        batch_metadatas.append(meta)
        batch_embeddings_list.append(batch_embeddings[j])
    
    # 将当前批次数据添加到集合
    collection.add(
        embeddings=batch_embeddings_list,
        documents=batch_documents,
        metadatas=batch_metadatas,
        ids=batch_ids
    )

print(f"成功将 {total_rows} 条官职数据的嵌入向量存入ChromaDB集合 '{COLLECTION_NAME}'。")
print(f"向量数据库持久化位置: {DB_PATH}")