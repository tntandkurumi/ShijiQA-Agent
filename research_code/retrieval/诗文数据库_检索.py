"""
诗文数据库检索模块

功能：
    基于 JSON 文件进行诗文检索，支持作者和标题双重条件。
    输入两个参数：作者（author）和标题（title），至少提供一个。
    作者名支持别名映射（与人物数据库相同），精确匹配。
    标题支持包含匹配（查询词作为子串）。
    两个条件取并集，返回所有匹配的诗文记录。

输入参数：
    author_str (str) : 作者名称（可选，可为空字符串）
    title_str (str)  : 标题关键词（可选，可为空字符串）
    至少有一个非空。

输出参数：
    str : 格式化后的检索结果，每条记录按字段输出，空字段不输出。
          若未找到记录，返回相应提示。

依赖：
    - JSON 文件位于：
        /root/autodl-tmp/毕业论文/数据库3-诗文数据库/merged_poems.json
"""

import json
import os
from typing import List, Dict, Any

# -------------------- 配置 --------------------
POEM_PATH = "/root/autodl-tmp/毕业论文/数据库3-诗文数据库/merged_poems.json"

# -------------------- 作者别名映射表（同人物数据库） --------------------
AUTHOR_ALIAS_MAP = {
    "高祖": ["陈武帝", "陈霸先"],
    "武帝": ["陈武帝", "陈霸先"],
    "陈武帝": ["陈武帝", "陈霸先"],
    "陈霸先": ["陈武帝", "陈霸先"],
    "陈高祖武皇帝": ["陈武帝", "陈霸先"],
    "高祖武皇帝": ["陈武帝", "陈霸先"],
    "高祖陈霸先": ["陈武帝", "陈霸先"],
    "陈高祖": ["陈武帝", "陈霸先"],
    "世祖": ["陈文帝", "陈蒨"],
    "世祖文皇帝": ["陈文帝", "陈蒨"],
    "文帝": ["陈文帝", "陈蒨"],
    "世祖陈蒨": ["陈文帝", "陈蒨"],
    "陈蒨": ["陈文帝", "陈蒨"],
    "陈世祖": ["陈文帝", "陈蒨"],
    "陈伯宗": ["陈废帝", "陈伯宗"],
    "陈废帝": ["陈废帝", "陈伯宗"],
    "临海王": ["陈废帝", "陈伯宗"],
    "废帝": ["陈废帝", "陈伯宗"],
    "陈顼": ["陈宣帝", "陈顼"],
    "高宗孝宣皇帝": ["陈宣帝", "陈顼"],
    "高宗": ["陈宣帝", "陈顼"],
    "安成王": ["陈宣帝", "陈顼"],
    "安成王陈顼": ["陈宣帝", "陈顼"],
    "高宗陈顼": ["陈宣帝", "陈顼"],
    "宣帝陈顼": ["陈宣帝", "陈顼"],
    "宣帝": ["陈宣帝", "陈顼"],
    "陈高宗": ["陈宣帝", "陈顼"],
    "景皇帝": ["陈文赞"],
    "始兴昭烈王": ["陈道谭"],
    "陈叔宝": ["陈叔宝"],
    "后主": ["陈叔宝"],
    "陈后主": ["陈叔宝"],
    "南朝陈后主": ["陈叔宝"],
    "炀公": ["陈叔宝"],
    "长城炀公": ["陈叔宝"],
    "元帝": ["梁元帝"],
    "敬帝": ["梁敬帝", "萧方智"],
    "梁帝": ["梁敬帝"],
    "炀帝": ["隋炀帝"],
    "悯王": ["陈昙朗"],
    "献王": ["陈昌"],
    "康简王": ["陈叔献"],
}

# -------------------- 加载 JSON 数据 --------------------
def load_poems() -> List[Dict[str, Any]]:
    """加载诗文数据，返回列表"""
    if not os.path.exists(POEM_PATH):
        print(f"警告：文件 {POEM_PATH} 不存在")
        return []
    with open(POEM_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 假设 data 是一个列表，每个元素是一首诗
    return data

POEMS = load_poems()

# -------------------- 辅助函数 --------------------
def _format_poem(poem: Dict[str, Any]) -> str:
    """
    格式化单条诗文记录，输出所有非空字段
    """
    lines = []
    # 按常见字段顺序输出
    for key in ["author", "title", "content", "note", "dynasty"]:
        value = poem.get(key)
        if value and value != "":
            lines.append(f"{key}：{value}")
    # 输出其他未列出的字段
    for key, value in poem.items():
        if key not in ["author", "title", "content", "note", "dynasty"]:
            if value and value != "":
                lines.append(f"{key}：{value}")
    return "\n".join(lines)

def _get_author_names(alias: str) -> List[str]:
    """根据作者别名获取标准作者名列表"""
    if alias in AUTHOR_ALIAS_MAP:
        return AUTHOR_ALIAS_MAP[alias]
    return [alias]

# -------------------- 主检索函数 --------------------
def retrieve(author_str: str = "", title_str: str = "") -> str:
    """
    检索诗文信息
    :param author_str: 作者名称（可为空）
    :param title_str: 标题关键词（可为空）
    :return: 格式化结果字符串，每条记录用空行分隔
    """
    if not author_str and not title_str:
        return "错误：至少需要提供一个检索条件（作者或标题）。"

    # 1. 处理作者条件
    author_targets = set()
    if author_str:
        for name in _get_author_names(author_str):
            author_targets.add(name)

    # 2. 遍历诗文列表，收集匹配项
    matched_poems = []
    for poem in POEMS:
        # 作者匹配（精确）
        match_author = False
        if author_targets:
            poem_author = poem.get("author", "")
            if poem_author in author_targets:
                match_author = True

        # 标题匹配（包含）
        match_title = False
        if title_str:
            poem_title = poem.get("title", "")
            if title_str in poem_title:  # 包含匹配
                match_title = True

        # 若匹配任一条件，则收录
        if (author_str and match_author) or (title_str and match_title):
            matched_poems.append(poem)

    # 3. 格式化输出
    if not matched_poems:
        return "未找到匹配的诗文记录。"

    formatted = []
    for idx, poem in enumerate(matched_poems):
        formatted.append(_format_poem(poem))
    return "\n\n".join(formatted)