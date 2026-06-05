"""
知识图谱检索模块（修改版：接收外部传入的 model 和 collection）
"""
import json
import os

# 配置文件路径（与向量生成时一致）
KG_INDEX_PATH = "/root/autodl-tmp/毕业论文/chromadb_kg/kg_index.json"
MAPPING_JSON_PATH = "/root/autodl-tmp/毕业论文/数据库9-知识图谱/实体映射.json"
ENTITY_MAPPING = None

def load_entity_mapping():
    global ENTITY_MAPPING
    if ENTITY_MAPPING is not None:
        return ENTITY_MAPPING
    mapping = {}
    if os.path.exists(MAPPING_JSON_PATH):
        with open(MAPPING_JSON_PATH, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    extra_mapping = {
        "高祖": "高祖陈霸先", "武帝": "高祖陈霸先", "陈武帝": "高祖陈霸先",
        "陈霸先": "高祖陈霸先", "陈高祖武皇帝": "高祖陈霸先", "高祖武皇帝": "高祖陈霸先",
        "陈高祖": "高祖陈霸先", "世祖": "世祖陈蒨", "陈文帝": "世祖陈蒨",
        "陈蒨": "世祖陈蒨", "世祖文皇帝": "世祖陈蒨", "文帝": "世祖陈蒨",
        "陈世祖": "世祖陈蒨", "陈废帝": "陈伯宗", "废帝": "陈伯宗", "临海王": "陈伯宗",
        "陈宣帝": "宣帝陈顼", "高宗孝宣皇帝": "宣帝陈顼", "高宗": "宣帝陈顼",
        "宣帝": "宣帝陈顼", "高宗陈顼": "宣帝陈顼", "陈顼": "宣帝陈顼",
        "安成王": "宣帝陈顼", "安成王陈顼": "宣帝陈顼", "陈高宗": "宣帝陈顼",
        "长城炀公": "后主陈叔宝", "炀公": "后主陈叔宝", "南朝陈后主": "后主陈叔宝",
        "陈后主": "后主陈叔宝", "陈叔宝": "后主陈叔宝", "后主": "后主陈叔宝",
        "陈文赞": "景皇帝", "陈道谭": "始兴昭烈王"
    }
    mapping.update(extra_mapping)
    ENTITY_MAPPING = mapping
    return mapping

def load_triple_index():
    if not os.path.exists(KG_INDEX_PATH):
        return {}
    with open(KG_INDEX_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

SUBJECT_TO_TRIPLES = load_triple_index()

def _normalize_entity(entity):
    mapping = load_entity_mapping()
    return mapping.get(entity, entity)

def _format_triple(triple):
    return f"{triple.get('subject','')} -> {triple.get('predicate','')} -> {triple.get('object','')}"

def retrieve(model, collection, query_str: str) -> str:
    # 1. 规范名转换
    normalized = _normalize_entity(query_str)
    if normalized != query_str and normalized in SUBJECT_TO_TRIPLES:
        triples = SUBJECT_TO_TRIPLES[normalized]
        if triples:
            lines = [f"实体: {normalized}", "相关三元组:"]
            for t in triples:
                lines.append("  " + _format_triple(t))
            return "\n".join(lines)
    # 2. 向量检索
    if collection is None:
        return "向量数据库未连接。"
    try:
        emb = model.encode([query_str], convert_to_numpy=True)[0].tolist()
        results = collection.query(query_embeddings=[emb], n_results=1, include=["documents"])
        if results['documents'] and results['documents'][0]:
            similar = results['documents'][0][0]
        else:
            return f"未找到与 '{query_str}' 相似的实体。"
    except Exception as e:
        return f"向量检索失败：{e}"
    if similar in SUBJECT_TO_TRIPLES:
        triples = SUBJECT_TO_TRIPLES[similar]
        if triples:
            lines = [f"查询词: {query_str}", f"匹配实体: {similar}", "相关三元组:"]
            for t in triples:
                lines.append("  " + _format_triple(t))
            return "\n".join(lines)
        else:
            return f"实体 '{similar}' 没有作为主体的三元组。"
    else:
        return f"实体 '{similar}' 不在知识图谱中。"