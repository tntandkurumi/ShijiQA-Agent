import importlib.util
import contextlib
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RETRIEVAL_CODE_DIR = PROJECT_ROOT / "research_code" / "retrieval"


PERSON_CBDB = {
    "陈霸先": {
        "biog_main": {
            "c_name_chn": "陈霸先",
            "dynasty": "南朝陈",
            "birth_year": "503",
            "death_year": "559",
        },
        "status": {"office": "相国、陈王、皇帝", "temple_name": "高祖", "posthumous_name": "武皇帝"},
        "events": [
            {"year": "557", "description": "受梁敬帝禅，建立陈朝。"},
            {"description": "平定侯景之乱后参与梁末政局整合。"},
        ],
    },
    "陈武帝": {
        "biog_main": {"c_name_chn": "陈武帝", "dynasty": "南朝陈"},
        "identity": {"personal_name": "陈霸先", "temple_name": "高祖", "posthumous_name": "武皇帝"},
    },
    "陈叔宝": {
        "biog_main": {"c_name_chn": "陈叔宝", "dynasty": "南朝陈", "death_year": "604"},
        "status": {"title": "陈后主", "posthumous_title": "长城炀公"},
        "events": [{"description": "陈朝末代皇帝，隋灭陈后入隋。"}],
    },
}

PERSON_CNG = {
    "陈霸先": {
        "person_name": "陈霸先",
        "aliases": ["陈武帝", "高祖"],
        "relations": {"father": "陈文赞", "dynasty": "陈"},
        "summary": "南朝陈开国君主，梁末起兵，后受禅称帝。",
    },
    "陈武帝": {
        "person_name": "陈武帝",
        "aliases": ["陈霸先", "高祖"],
        "summary": "陈霸先即陈武帝。",
    },
    "陈叔宝": {
        "person_name": "陈叔宝",
        "aliases": ["后主", "长城炀公"],
        "summary": "南朝陈后主，陈朝末帝。",
    },
}

POEMS = [
    {
        "author": "陈叔宝",
        "title": "玉树后庭花",
        "content": "丽宇芳林对高阁，新装艳质本倾城。",
        "note": "模拟诗文库预置记录，用于接口演示。",
        "dynasty": "陈",
    },
    {
        "author": "陈叔宝",
        "title": "三妇艳词十一首 其一",
        "content": "大妇上高楼，中妇荡莲舟。",
        "dynasty": "陈",
    },
    {
        "author": "陈霸先",
        "title": "宴群臣登高",
        "content": "预置诗文记录：用于验证作者精确检索流程。",
        "dynasty": "陈",
    },
]

OFFICIAL_DOCS = [
    ("丞相", {"品阶": "一品", "职责": "总理百官，辅佐君主处理政务。", "沿革": "秦汉以来为高级宰辅官称。"}),
    ("给事中", {"品阶": "从五品左右", "职责": "侍从顾问，掌封驳奏事。", "沿革": "魏晋南北朝多为近侍清要之职。"}),
    ("尚书令", {"品阶": "三品", "职责": "总领尚书台政务。", "沿革": "南朝中枢机构长官之一。"}),
]

GEOGRAPHY_DOCS = [
    ("建康", {"内容": "六朝都城，今南京一带，为南朝政治文化中心。"}),
    ("临川", {"内容": "江南郡县地名，南朝时期常见于军事与地方治理记载。"}),
    ("台城", {"内容": "建康宫城核心区域，常与梁陈政治事件相关。"}),
]

EVENT_DOCS = [
    ("侯景之乱", {"内容": "梁末重大叛乱，造成江南政局剧烈震荡。", "例子": "梁末侯景据建康，诸方起兵讨之。"}),
    ("受禅建陈", {"内容": "梁敬帝禅位于陈霸先，陈朝建立。", "例子": "陈霸先受禅后即皇帝位。"}),
    ("平定王僧辩", {"内容": "梁末政治军事事件，与陈霸先掌握朝局相关。", "例子": "陈霸先袭杀王僧辩，另立梁敬帝。"}),
]

TERM_DOCS = [
    ("践祚", {"解释": "帝王即位、登基。"}),
    ("受禅", {"解释": "接受前朝君主禅让而取得帝位。"}),
    ("丁忧", {"解释": "父母去世后按礼制离职守丧。"}),
]

KG_TRIPLES = {
    "高祖陈霸先": [
        {"subject": "高祖陈霸先", "predicate": "庙号", "object": "高祖"},
        {"subject": "高祖陈霸先", "predicate": "谥号", "object": "武皇帝"},
        {"subject": "高祖陈霸先", "predicate": "建立", "object": "陈朝"},
    ],
    "后主陈叔宝": [
        {"subject": "后主陈叔宝", "predicate": "身份", "object": "陈朝末代皇帝"},
        {"subject": "后主陈叔宝", "predicate": "父亲", "object": "宣帝陈顼"},
        {"subject": "后主陈叔宝", "predicate": "亡国事件", "object": "隋灭陈"},
    ],
    "建康": [
        {"subject": "建康", "predicate": "地理性质", "object": "六朝都城"},
        {"subject": "建康", "predicate": "相关政权", "object": "南朝陈"},
    ],
}

BILINGUAL_PARAGRAPHS = [
    {
        "source_file": "陈书_高祖纪.json",
        "title": "高祖纪",
        "modern": "陈霸先平定梁末乱局后，受梁敬帝禅让，建立陈朝。",
        "ancient": "梁敬帝禅位于高祖，高祖即皇帝位，国号陈。",
    },
    {
        "source_file": "陈书_后主纪.json",
        "title": "后主纪",
        "modern": "陈叔宝即位后，陈朝政治日趋衰弱，最终为隋所灭。",
        "ancient": "后主嗣位，政刑弛紊，隋师济江，遂亡陈。",
    },
    {
        "source_file": "陈书_地理志.json",
        "title": "地理志",
        "modern": "建康是南朝都城，是江南政治文化中心。",
        "ancient": "建康，江左都会，六代所都。",
    },
]


@dataclass(frozen=True)
class PreparedRetrievalResult:
    raw_text: str
    chunks: list[dict[str, Any]]


class _PreparedEmbedding:
    def __init__(self, text: str):
        self.text = text

    def tolist(self) -> dict[str, str]:
        return {"query": self.text}


class PreparedEmbeddingModel:
    def encode(self, texts: list[str], convert_to_numpy: bool = True) -> list[_PreparedEmbedding]:
        return [_PreparedEmbedding(text) for text in texts]


class PreparedCollection:
    def __init__(self, records: list[tuple[str, dict[str, Any]]], min_similarity: float = 0.12):
        self.records = records
        self.min_similarity = min_similarity

    def get(self, include: list[str] | None = None) -> dict[str, list[Any]]:
        return {
            "documents": [doc for doc, _ in self.records],
            "metadatas": [meta for _, meta in self.records],
        }

    def count(self) -> int:
        return len(self.records)

    def query(self, query_embeddings: list[Any], n_results: int, include: list[str] | None = None) -> dict[str, list[list[Any]]]:
        query = _extract_query_text(query_embeddings[0] if query_embeddings else "")
        scored = []
        for doc, meta in self.records:
            similarity = _text_similarity(query, doc + " " + " ".join(str(value) for value in meta.values()))
            if similarity >= self.min_similarity or query in doc or doc in query:
                distance = round(1.0 - similarity, 6)
                scored.append((distance, doc, meta))
        scored.sort(key=lambda item: item[0])
        selected = scored[:n_results]
        return {
            "documents": [[doc for _, doc, _ in selected]],
            "metadatas": [[meta for _, _, meta in selected]],
            "distances": [[dist for dist, _, _ in selected]],
        }


MODEL = PreparedEmbeddingModel()
COLLECTIONS = {
    "official": PreparedCollection(OFFICIAL_DOCS),
    "geography": PreparedCollection(GEOGRAPHY_DOCS),
    "event": PreparedCollection(EVENT_DOCS),
    "term": PreparedCollection(TERM_DOCS),
    "kg": PreparedCollection([(key, {"entity": key}) for key in KG_TRIPLES.keys()]),
}

_SCRIPT_CACHE: dict[str, Any] = {}


def execute_prepared_tool(tool_name: str, arguments: dict[str, Any], fallback_query: str) -> PreparedRetrievalResult:
    if tool_name == "search_bilingual":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_bilingual(query)
    if tool_name == "search_person":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_person(query)
    if tool_name == "search_poetry":
        author = str(arguments.get("author") or "")
        title = str(arguments.get("title") or "")
        return _retrieve_poetry(author, title)
    if tool_name == "search_official_positions":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_vector_script("官职数据库_检索.py", "official", query, "官职数据库")
    if tool_name == "search_geography":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_vector_script("地理数据库_检索.py", "geography", query, "地理数据库")
    if tool_name == "search_historical_events":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_vector_script("典故事件数据库_检索.py", "event", query, "典故事件数据库")
    if tool_name == "search_terminology":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_vector_script("术语句法数据库_检索.py", "term", query, "术语句法数据库")
    if tool_name == "search_knowledge_graph":
        query = str(arguments.get("query") or fallback_query)
        return _retrieve_kg(query)
    return PreparedRetrievalResult(raw_text=f"未知工具：{tool_name}", chunks=[])


def _retrieve_person(query: str) -> PreparedRetrievalResult:
    module = _load_script("人物数据库_检索.py")
    module.CBDB_DICT = PERSON_CBDB
    module.CNG_DICT = PERSON_CNG
    raw = module.retrieve(query)
    return PreparedRetrievalResult(raw_text=raw, chunks=_chunks_from_raw("人物数据库", query, raw, "人物别名映射 + JSON 精确匹配"))


def _retrieve_poetry(author: str, title: str) -> PreparedRetrievalResult:
    module = _load_script("诗文数据库_检索.py")
    module.POEMS = POEMS
    raw = module.retrieve(author, title)
    query = author or title or "诗文检索"
    return PreparedRetrievalResult(raw_text=raw, chunks=_chunks_from_raw("诗文数据库", query, raw, "作者精确匹配 + 标题包含匹配"))


def _retrieve_vector_script(script_name: str, collection_key: str, query: str, source_type: str) -> PreparedRetrievalResult:
    module = _load_script(script_name)
    raw = module.retrieve(MODEL, COLLECTIONS[collection_key], query)
    return PreparedRetrievalResult(raw_text=raw, chunks=_chunks_from_raw(source_type, query, raw, "精确匹配优先；未命中则模拟向量距离分组"))


def _retrieve_kg(query: str) -> PreparedRetrievalResult:
    module = _load_script("知识图谱数据_检索.py")
    module.ENTITY_MAPPING = None
    module.SUBJECT_TO_TRIPLES = KG_TRIPLES
    raw = module.retrieve(MODEL, COLLECTIONS["kg"], query)
    return PreparedRetrievalResult(raw_text=raw, chunks=_chunks_from_raw("知识图谱", query, raw, "实体映射优先；未命中则模拟向量近邻实体"))


def _retrieve_bilingual(query: str) -> PreparedRetrievalResult:
    dense_results = _dense_bilingual(query)
    sparse_results = _sparse_bilingual(query)
    fused = _rrf_fusion(dense_results, sparse_results)
    output_lines = []
    chunks = []
    for idx, item in enumerate(fused[:10], start=1):
        paragraph = BILINGUAL_PARAGRAPHS[item["paragraph_index"]]
        output_lines.append(f"\n【结果 {idx}】")
        output_lines.append(f"文件：{paragraph['source_file']}")
        output_lines.append(f"标题：{paragraph['title']}")
        output_lines.append(f"现代文译文：{paragraph['modern']}")
        output_lines.append(f"古文原文：{paragraph['ancient']}")
        chunks.append(
            {
                "source_type": "双语数据库",
                "title": paragraph["title"],
                "content": f"文件：{paragraph['source_file']}\n现代文译文：{paragraph['modern']}\n古文原文：{paragraph['ancient']}",
                "score": round(item["rrf"], 6),
                "rank": idx,
                "rationale": "稠密向量 + BM25 稀疏检索，经 RRF 融合后按段落聚合",
            }
        )
    if not output_lines:
        return PreparedRetrievalResult(raw_text="未找到相关结果。", chunks=[])
    return PreparedRetrievalResult(raw_text="\n".join(output_lines), chunks=chunks)


def _dense_bilingual(query: str) -> list[tuple[int, int]]:
    scored = []
    for idx, paragraph in enumerate(BILINGUAL_PARAGRAPHS):
        text = paragraph["modern"] + paragraph["ancient"] + paragraph["title"]
        similarity = _text_similarity(query, text)
        if similarity >= 0.12 or any(token and token in text for token in _tokens(query)):
            scored.append((idx, similarity))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [(idx, rank) for rank, (idx, _) in enumerate(scored[:20], start=1)]


def _sparse_bilingual(query: str) -> list[tuple[int, int]]:
    tokens = _tokens(query)
    if not tokens:
        return []
    scored = []
    for idx, paragraph in enumerate(BILINGUAL_PARAGRAPHS):
        text = paragraph["modern"] + paragraph["ancient"] + paragraph["title"]
        score = sum(1 for token in tokens if token in text)
        if score:
            scored.append((idx, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [(idx, rank) for rank, (idx, _) in enumerate(scored[:20], start=1)]


def _rrf_fusion(dense_results: list[tuple[int, int]], sparse_results: list[tuple[int, int]]) -> list[dict[str, Any]]:
    scores: dict[int, dict[str, Any]] = {}
    for paragraph_index, rank in dense_results:
        scores.setdefault(paragraph_index, {"rrf": 0.0, "dense_rank": math.inf, "sparse_rank": math.inf})
        scores[paragraph_index]["rrf"] += 0.5 / (60 + rank)
        scores[paragraph_index]["dense_rank"] = min(scores[paragraph_index]["dense_rank"], rank)
    for paragraph_index, rank in sparse_results:
        scores.setdefault(paragraph_index, {"rrf": 0.0, "dense_rank": math.inf, "sparse_rank": math.inf})
        scores[paragraph_index]["rrf"] += 0.5 / (60 + rank)
        scores[paragraph_index]["sparse_rank"] = min(scores[paragraph_index]["sparse_rank"], rank)
    fused = [{"paragraph_index": idx, **data} for idx, data in scores.items()]
    fused.sort(key=lambda item: (-item["rrf"], item["dense_rank"]))
    return fused


def _chunks_from_raw(source_type: str, title: str, raw: str, rationale: str) -> list[dict[str, Any]]:
    if _is_empty_result(raw):
        return []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw) if block.strip()]
    chunks = []
    for rank, block in enumerate(blocks, start=1):
        first_line = block.splitlines()[0] if block.splitlines() else title
        chunks.append(
            {
                "source_type": source_type,
                "title": first_line.replace("【", "").replace("】", "")[:120] or title,
                "content": block,
                "score": max(0.01, round(1.0 / rank, 4)),
                "rank": rank,
                "rationale": rationale,
            }
        )
    return chunks


def _is_empty_result(raw: str) -> bool:
    empty_markers = ("未找到", "错误：", "向量数据库未连接", "没有作为主体的三元组", "不在知识图谱中")
    return any(marker in raw for marker in empty_markers)


def _load_script(filename: str) -> Any:
    if filename in _SCRIPT_CACHE:
        return _SCRIPT_CACHE[filename]
    path = RETRIEVAL_CODE_DIR / filename
    module_name = "prepared_" + re.sub(r"\W+", "_", filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载检索脚本：{filename}")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    _SCRIPT_CACHE[filename] = module
    return module


def _extract_query_text(embedding: Any) -> str:
    if isinstance(embedding, dict):
        return str(embedding.get("query") or "")
    return str(embedding)


def _text_similarity(query: str, text: str) -> float:
    query_tokens = set(_tokens(query))
    text_tokens = set(_tokens(text))
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = len(query_tokens & text_tokens)
    char_overlap = len(set(query) & set(text)) / max(len(set(query)), 1)
    return round((overlap / len(query_tokens)) * 0.75 + char_overlap * 0.25, 6)


def _tokens(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text)
    words = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", compact)
    char_bigrams = [compact[index : index + 2] for index in range(max(len(compact) - 1, 0))]
    return [token for token in words + char_bigrams if token]
