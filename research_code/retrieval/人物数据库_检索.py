"""
人物数据库检索模块

功能：
    基于 JSON 文件进行精确人名匹配，支持别名映射。
    输入一个查询词（可能是别名），根据映射表转换为多个标准人名，
    然后在两个 JSON 文件中分别精确匹配，每个文件返回第一条匹配记录（按映射顺序优先）。
    输出格式会递归展开所有嵌套字段，确保不遗漏任何信息。

输入参数：
    query_str (str) : 待检索的人名或别名

输出参数：
    str : 格式化后的检索结果。包含两个文件的检索结果（如果有），
          每条记录递归输出所有字段（嵌套字段以缩进或点号显示），
          字段为空则不输出。

依赖：
    - 两个 JSON 文件位于固定路径：
        /root/autodl-tmp/毕业论文/数据库2-人物数据库/cbdb人物数据.json
        /root/autodl-tmp/毕业论文/数据库2-人物数据库/cng人物.json
"""

import json
import os

# -------------------- 配置 --------------------
CBDB_PATH = "/root/autodl-tmp/毕业论文/数据库2-人物数据库/cbdb人物数据.json"
CNG_PATH = "/root/autodl-tmp/毕业论文/数据库2-人物数据库/cng人物.json"

# -------------------- 别名映射表 --------------------
ALIAS_MAP = {
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
def load_json_data():
    """加载两个 JSON 文件，返回两个字典，键为人名，值为完整记录"""
    cbdb_dict = {}
    cng_dict = {}

    # 加载 cbdb 数据
    if os.path.exists(CBDB_PATH):
        with open(CBDB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            # 假设数据格式为列表，每个元素包含 "biog_main" 字段，其中 "c_name_chn" 为人名
            c_name = item.get("biog_main", {}).get("c_name_chn", "")
            if c_name and c_name not in cbdb_dict:
                cbdb_dict[c_name] = item   # 只存储第一条匹配的记录
    else:
        print(f"警告：文件 {CBDB_PATH} 不存在")

    # 加载 cng 数据
    if os.path.exists(CNG_PATH):
        with open(CNG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            # 假设数据格式为列表，每个元素包含 "person_name" 字段
            person_name = item.get("person_name", "")
            if person_name and person_name not in cng_dict:
                cng_dict[person_name] = item
    else:
        print(f"警告：文件 {CNG_PATH} 不存在")

    return cbdb_dict, cng_dict

CBDB_DICT, CNG_DICT = load_json_data()

# -------------------- 递归展平字典 --------------------
def _flatten_dict(obj, parent_key='', sep='.'):
    """
    递归展平嵌套字典，返回 (key, value) 列表
    :param obj: 待展平的对象（字典、列表或其他）
    :param parent_key: 父键前缀
    :param sep: 键分隔符
    :return: 列表，元素为 (键, 值)
    """
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(_flatten_dict(v, new_key, sep))
    elif isinstance(obj, list):
        # 列表按索引展开，如 "field.0"
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.extend(_flatten_dict(v, new_key, sep))
    else:
        # 基本类型（字符串、数字等）
        if obj is not None and obj != "":
            items.append((parent_key, obj))
    return items

def _format_record(record: dict, source: str) -> str:
    """
    格式化单条记录，递归输出所有非空字段
    :param record: 记录字典
    :param source: 数据来源（"cbdb" 或 "cng"）
    :return: 格式化字符串
    """
    if not record:
        return f"【{source}】\n未找到匹配记录。"

    # 展平嵌套结构
    flat_items = _flatten_dict(record)

    # 过滤掉空值和None
    flat_items = [(k, v) for k, v in flat_items if v is not None and v != ""]

    if not flat_items:
        return f"【{source}】\n（无有效字段）"

    # 按键排序（可选）
    flat_items.sort(key=lambda x: x[0])

    lines = [f"【{source}】"]
    for key, value in flat_items:
        # 适当处理值中的换行符，保持可读性
        value_str = str(value).replace('\n', ' ')
        lines.append(f"{key}: {value_str}")
    return "\n".join(lines)

# -------------------- 主检索函数 --------------------
def retrieve(query_str: str) -> str:
    """
    检索人物信息
    :param query_str: 用户输入的查询词（可能为别名）
    :return: 格式化结果字符串，每个文件最多一条记录
    """
    # 1. 根据映射表获取标准人名列表
    if query_str in ALIAS_MAP:
        target_names = ALIAS_MAP[query_str]
    else:
        target_names = [query_str]   # 直接使用输入

    # 2. 分别查找两个文件，每个文件只取第一条匹配记录
    cbdb_result = None
    cng_result = None

    for name in target_names:
        # 如果已经找到 cbdb 记录，跳过后续人名
        if cbdb_result is None and name in CBDB_DICT:
            cbdb_result = CBDB_DICT[name]
        # 如果已经找到 cng 记录，跳过后续人名
        if cng_result is None and name in CNG_DICT:
            cng_result = CNG_DICT[name]
        # 如果两个都已找到，提前终止
        if cbdb_result is not None and cng_result is not None:
            break

    # 3. 格式化输出
    cbdb_output = _format_record(cbdb_result, "cbdb人物数据")
    cng_output = _format_record(cng_result, "cng人物")

    # 4. 合并结果，用空行分隔
    return "\n\n".join([cbdb_output, cng_output])