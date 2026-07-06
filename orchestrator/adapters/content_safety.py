"""Content safety keyword checker for L6 QA - ad law compliance."""

import re
from typing import NamedTuple


class SafetyResult(NamedTuple):
    passed: bool
    score: float
    hits: list[str]
    message: str


# PRC Advertising Law prohibited / restricted keywords
PROHIBITED_WORDS = [
    "第一", "唯一", "首个", "首选", "顶级", "最高", "最佳", "最好", "最大", "最先",
    "国家级", "世界级", "宇宙级", "全球首发", "全国首发", "全网首发",
    "万能", "绝对", "100%", "百分百", "彻底", "完全",
    "最便宜", "最低价", "全网最低", "史上最低",
    "永不", "永久", "终身", "永远",
    "特效", "速效", "神效", "奇效",
    "纯天然", "无添加", "零添加", "无副作用",
    "第一品牌", "领导品牌", "王牌", "冠军",
    "销量第一", "排名第一", "市场占有率第一",
    "顶级", "极品", "至尊", "巅峰",
]

RISKY_WORDS = [
    "祛皱", "抗皱", "除皱", "淡斑", "祛斑", "美白", "祛痘",
    "减肥", "瘦身", "丰胸", "增高",
    "治愈", "根治", "治疗",
]


def check_content(text: str) -> SafetyResult:
    """Check script content for compliance with advertising regulations.

    Returns (passed, score, hits, message).
    """
    text_lower = text.lower()

    prohibited_hits: list[str] = []
    for word in PROHIBITED_WORDS:
        if word in text:
            prohibited_hits.append(word)

    risky_hits: list[str] = []
    for word in RISKY_WORDS:
        if word in text:
            risky_hits.append(word)

    score = 1.0
    score -= len(prohibited_hits) * 0.15
    score -= len(risky_hits) * 0.05
    score = max(0.0, score)

    if prohibited_hits:
        return SafetyResult(
            passed=False,
            score=score,
            hits=prohibited_hits + risky_hits,
            message=f"发现 {len(prohibited_hits)} 个违禁词: {', '.join(prohibited_hits[:5])}",
        )

    if risky_hits and score < 0.8:
        return SafetyResult(
            passed=False,
            score=score,
            hits=risky_hits,
            message=f"发现 {len(risky_hits)} 个高风险词: {', '.join(risky_hits[:5])}",
        )

    if risky_hits:
        return SafetyResult(
            passed=True,
            score=score,
            hits=risky_hits,
            message=f"高风险词: {', '.join(risky_hits[:5])} (建议替换)",
        )

    return SafetyResult(
        passed=True,
        score=1.0,
        hits=[],
        message="内容安全检测通过",
    )
