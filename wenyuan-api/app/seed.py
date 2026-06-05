from sqlalchemy.orm import Session

from .config import settings
from .models import ModelConfig


DEFAULT_MODELS = [
    {
        "name": "wenyuan-sim",
        "provider": "mock",
        "display_name": "文渊模拟模型",
        "base_url": "",
        "enabled": True,
        "is_mock": True,
    },
    {
        "name": "kimi-k2.6",
        "provider": "moonshot",
        "display_name": "Kimi K2.6",
        "base_url": "https://api.moonshot.cn/v1",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "doubao-seed-2-0-pro-260215",
        "provider": "volcengine",
        "display_name": "豆包 Seed 2.0 Pro",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "mimo-v2.5-pro",
        "provider": "mimo",
        "display_name": "MiMo v2.5 Pro",
        "base_url": "https://api.xiaomimimo.com/v1",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "deepseek-v4-pro",
        "provider": "deepseek",
        "display_name": "DeepSeek V4 Pro",
        "base_url": "https://api.deepseek.com",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "deepseek-v4-flash",
        "provider": "deepseek",
        "display_name": "DeepSeek V4 Flash",
        "base_url": "https://api.deepseek.com",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "qwen3.6-plus",
        "provider": "dashscope",
        "display_name": "通义 Qwen 3.6 Plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "enabled": True,
        "is_mock": False,
    },
    {
        "name": "glm-5.1",
        "provider": "dashscope",
        "display_name": "GLM 5.1",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "enabled": True,
        "is_mock": False,
    },
]


CLASSIC_QUOTES = [
    {"text": "学而不思则罔，思而不学则殆。", "source": "论语"},
    {"text": "知不足而奋进，望远山而前行。", "source": "项目题辞"},
    {"text": "博学之，审问之，慎思之，明辨之，笃行之。", "source": "礼记"},
    {"text": "究天人之际，通古今之变。", "source": "报任安书"},
    {"text": "观今宜鉴古，无古不成今。", "source": "增广贤文"},
    {"text": "为学日益，为道日损。", "source": "道德经"},
]


def seed_model_configs(db: Session) -> None:
    existing_names = {row.name for row in db.query(ModelConfig).all()}
    for item in DEFAULT_MODELS:
        if item["name"] in existing_names:
            continue
        db.add(ModelConfig(**item))
    db.commit()
