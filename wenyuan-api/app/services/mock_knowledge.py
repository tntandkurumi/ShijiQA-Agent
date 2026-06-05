from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeItem:
    source_type: str
    title: str
    content: str
    keywords: tuple[str, ...]


MOCK_KNOWLEDGE = [
    KnowledgeItem(
        source_type="人物数据库",
        title="陈霸先",
        content="陈霸先，南朝陈开国君主，庙号高祖，谥号武皇帝。系统模拟记录显示，其政治活动常与梁末局势、平定叛乱、受禅建陈相关。",
        keywords=("陈霸先", "高祖", "武帝", "受禅", "建陈", "南朝陈"),
    ),
    KnowledgeItem(
        source_type="官职数据库",
        title="丞相",
        content="丞相为古代高级官职，常总理政务，位望极重。模拟官职库记录其品阶、隶属与沿革字段，可用于制度类问答。",
        keywords=("丞相", "官职", "政务", "品阶", "制度"),
    ),
    KnowledgeItem(
        source_type="地理数据库",
        title="建康",
        content="建康为六朝都城核心地名，地处江南政治文化中心。模拟地理库用于回答都城、地名沿革、地域关系等问题。",
        keywords=("建康", "都城", "江南", "地理", "六朝"),
    ),
    KnowledgeItem(
        source_type="典故事件数据库",
        title="侯景之乱",
        content="侯景之乱是南朝梁末重大变局，深刻影响江南政局。模拟事件库记录事件背景、经过、关联人物和后续影响。",
        keywords=("侯景之乱", "梁末", "事件", "叛乱", "政局"),
    ),
    KnowledgeItem(
        source_type="术语句法数据库",
        title="践祚",
        content="践祚指帝王即位、登基。模拟术语库用于解释古籍中常见制度词、礼制词和文言表达。",
        keywords=("践祚", "即位", "登基", "术语", "礼制"),
    ),
    KnowledgeItem(
        source_type="知识图谱",
        title="高祖陈霸先 -> 谥号 -> 武皇帝",
        content="模拟知识图谱三元组：高祖陈霸先 -> 谥号 -> 武皇帝；高祖陈霸先 -> 庙号 -> 高祖；高祖陈霸先 -> 建立 -> 陈。",
        keywords=("陈霸先", "谥号", "武皇帝", "庙号", "高祖", "知识图谱", "关系"),
    ),
    KnowledgeItem(
        source_type="诗文数据库",
        title="陈叔宝诗文",
        content="模拟诗文库记录陈叔宝相关篇目，支持按作者、标题关键词检索，并返回作者、题名、正文、朝代等字段。",
        keywords=("陈叔宝", "后主", "诗文", "作者", "题名"),
    ),
    KnowledgeItem(
        source_type="双语数据库",
        title="《陈书》现代文与古文对照",
        content="模拟双语库返回完整段落：现代文译文用于理解事件经过，古文原文用于引用依据。检索策略模拟稠密向量与 BM25 融合。",
        keywords=("陈书", "古文", "现代文", "译文", "双语", "RRF", "检索"),
    ),
]


def _score(query: str, item: KnowledgeItem) -> float:
    compact_query = query.replace(" ", "")
    keyword_score = 0.0
    for keyword in item.keywords:
        if keyword in compact_query:
            keyword_score += 2.0
        else:
            overlap = len(set(keyword) & set(compact_query))
            if overlap:
                keyword_score += min(overlap / max(len(set(keyword)), 1), 1.0)
    title_score = 1.5 if item.title in compact_query else 0.0
    return round(keyword_score + title_score, 4)


def retrieve_mock_chunks(query: str, limit: int = 5, min_score: float = 0.5) -> list[dict]:
    ranked = []
    for item in MOCK_KNOWLEDGE:
        score = _score(query, item)
        if score >= min_score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    chunks = []
    for rank, (score, item) in enumerate(ranked[:limit], start=1):
        chunks.append(
            {
                "source_type": item.source_type,
                "title": item.title,
                "content": item.content,
                "score": score,
                "rank": rank,
                "rationale": "模拟向量检索得分 = 关键词命中 + 字符重叠 + 标题命中；低于阈值不返回",
            }
        )
    return chunks


def search_mock_tool(tool_name: str, query: str, limit: int = 3) -> list[dict]:
    source_map = {
        "search_person": "人物数据库",
        "search_official": "官职数据库",
        "search_geography": "地理数据库",
        "search_event": "典故事件数据库",
        "search_term": "术语句法数据库",
        "search_kg": "知识图谱",
        "search_poetry": "诗文数据库",
        "search_bilingual": "双语数据库",
    }
    source_type = source_map.get(tool_name)
    ranked = retrieve_mock_chunks(query, limit=len(MOCK_KNOWLEDGE), min_score=0.5)
    if source_type:
        filtered = [chunk for chunk in ranked if chunk["source_type"] == source_type]
        return filtered[:limit]
    return ranked[:limit]


def detect_intent(query: str) -> str:
    checks = [
        ("人物", ("谁", "人物", "陈霸先", "陈叔宝", "高祖", "后主")),
        ("官职制度", ("官职", "丞相", "品阶", "职责")),
        ("地理沿革", ("哪里", "建康", "地名", "都城", "地理")),
        ("事件典故", ("事件", "侯景", "叛乱", "战争", "起兵")),
        ("术语解释", ("是什么意思", "解释", "践祚", "术语")),
        ("关系推理", ("关系", "谥号", "庙号", "属于", "担任")),
        ("诗文检索", ("诗", "文", "作者", "题名", "陈叔宝")),
        ("双语对照", ("原文", "译文", "陈书", "古文", "现代文")),
    ]
    matched = [name for name, words in checks if any(word in query for word in words)]
    return "、".join(matched) if matched else "综合史籍问答"
