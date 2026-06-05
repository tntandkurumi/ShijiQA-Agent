"""
官职数据库检索模块

功能：
    基于已加载的模型和 ChromaDB 集合，对输入的官职名称进行检索。
    优先精确匹配（官职名称完全一致），返回所有匹配记录；
    若无精确匹配，则向量检索，按相似度距离分组，返回前三个不同距离值组的所有记录。

输入参数：
    model (SentenceTransformer) : 已加载的嵌入模型
    collection (chromadb.Collection) : 已连接的官职数据库集合
    query_str (str) : 待检索的官职名称

输出参数：
    str : 格式化后的检索结果。精确匹配时每条记录之间空行分隔；
          向量检索时每组包含组标题和组内多条记录（记录间空行分隔），组间空行分隔；
          错误时返回错误信息字符串。
"""

def _format_record(metadata: dict, office_name: str = None) -> str:
    """
    格式化单条记录（排除空字段）
    :param metadata: 元数据字典，包含除官职名称外的其他字段
    :param office_name: 官职名称，若提供则作为第一行输出
    """
    lines = []
    if office_name is not None:
        lines.append(f"官职名称：{office_name}")
    for key, value in metadata.items():
        if value != "" and value is not None:
            lines.append(f"{key}：{value}")
    return "\n".join(lines)

def retrieve(model, collection, query_str: str) -> str:
    # 1. 精确匹配检测：找出所有 document == query_str 的记录
    all_data = collection.get(include=["documents", "metadatas"])
    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    matched_indices = [i for i, doc in enumerate(all_docs) if doc == query_str]
    if matched_indices:
        # 精确匹配，返回所有匹配记录，每条记录之间空行分隔
        results = []
        for idx in matched_indices:
            results.append(_format_record(all_metas[idx], office_name=all_docs[idx]))
        return "\n\n".join(results)

    # 2. 向量相似度检索：获取全部结果并按距离分组
    try:
        query_embedding = model.encode(
            [query_str],
            convert_to_numpy=True
        )[0].tolist()
    except Exception as e:
        return f"向量编码失败：{e}"

    # 获取所有记录
    total_count = collection.count()
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=total_count,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        return f"向量查询失败：{e}"

    top_docs = results["documents"][0]
    top_metas = results["metadatas"][0]
    top_distances = results["distances"][0]

    if not top_docs:
        return "未找到任何匹配记录。"

    # 按距离分组
    distance_groups = {}
    for doc, meta, dist in zip(top_docs, top_metas, top_distances):
        dist_key = round(dist, 6)
        if dist_key not in distance_groups:
            distance_groups[dist_key] = []
        distance_groups[dist_key].append((doc, meta))

    sorted_distances = sorted(distance_groups.keys())
    top_groups = sorted_distances[:5]  # 保留用户修改的5组

    if not top_groups:
        return "未找到任何匹配记录。"

    output_parts = []
    group_index = 1
    for dist in top_groups:
        group_records = distance_groups[dist]
        header = f"【第 {group_index} 组】（相似度距离：{dist:.6f}）"
        group_output = [header]
        for doc, meta in group_records:
            group_output.append(_format_record(meta, office_name=doc))
        output_parts.append("\n".join(group_output))
        group_index += 1

    return "\n\n".join(output_parts)