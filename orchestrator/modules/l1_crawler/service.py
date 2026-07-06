from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from orchestrator.config import settings
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l1_crawler.models import (
    SearchRequest,
    SearchResponse,
    TopicRecord,
    TopicsListResponse,
    TrendingTopic,
)

TOPICS_FILE = module_dir("l1") / "topics.json"

CURATED_TRENDING: dict[str, list[tuple[str, int]]] = {
    "电商": [
        ("夏季防晒好物", 9200), ("平价护肤套装", 8800), ("厨房小家电种草", 7600),
        ("母婴湿巾测评", 7100), ("户外露营装备", 6900), ("零食大礼包", 6500),
        ("智能家居入门", 6200), ("宠物自动喂食器", 5800),
    ],
    "家居日用": [
        ("壁挂收纳神器", 9100), ("免打孔置物架", 8600), ("折叠脏衣篮", 7800),
        ("厨房转角收纳", 7200), ("卫生间壁挂架", 6800), ("衣柜分层板", 6300),
        ("门后挂钩", 5900), ("桌面理线器", 5500),
    ],
    "美妆个护": [
        ("平价粉底液实测", 9400), ("敏感肌护肤套装", 8900), ("持久口红试色", 8200),
        ("氨基酸洗面奶", 7700), ("防晒霜横评", 7300), ("面膜囤货季", 6700),
        ("眼影盘种草", 6100), ("身体乳推荐", 5600),
    ],
    "鞋服配饰": [
        ("通勤百搭小白鞋", 8800), ("夏季连衣裙", 8300), ("防晒衣选购指南", 7600),
        ("大码女装推荐", 7000), ("运动内衣测评", 6400), ("帆布包种草", 5800),
        ("墨镜搭配", 5200), ("袜子合集", 4800),
    ],
    "数码配件": [
        ("百元蓝牙耳机", 8600), ("手机壳推荐", 7900), ("快充头横评", 7200),
        ("iPad配件", 6600), ("无线鼠标测评", 6000), ("机械键盘种草", 5500),
        ("数据线选购", 4900), ("屏幕清洁套装", 4400),
    ],
    "母婴": [
        ("婴儿湿巾测评", 9000), ("学饮杯推荐", 8400), ("儿童防晒霜", 7700),
        ("辅食机种草", 7100), ("婴儿推车对比", 6500), ("早教玩具", 6000),
        ("哺乳内衣", 5400), ("宝宝爬行垫", 4900),
    ],
    "三农": [
        ("产地直发水果", 9500), ("有机蔬菜礼盒", 8700), ("乡村土鸡蛋", 8200),
        ("农家腊肉", 7800), ("助农直播带货", 7400), ("稻田蟹养殖", 6900),
        ("非遗手作", 6600), ("乡村民宿推广", 6100),
    ],
}


def _extract_meta(html: str, og_prop: str, fallback_tag: str) -> str:
    prop_match = re.search(
        rf'<meta\s[^>]*property=["\x27]{og_prop}["\x27][^>]*content=["\x27]([^"\x27]+)',
        html,
        re.IGNORECASE,
    )
    if prop_match:
        return prop_match.group(1)
    name_match = re.search(
        rf'<meta\s[^>]*name=["\x27]{og_prop}["\x27][^>]*content=["\x27]([^"\x27]+)',
        html,
        re.IGNORECASE,
    )
    if name_match:
        return name_match.group(1)
    if fallback_tag:
        tag_match = re.search(
            rf"<{fallback_tag}[^>]*>(.*?)</{fallback_tag}>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if tag_match:
            return re.sub(r"<[^>]+>", "", tag_match.group(1)).strip()[:500]
    return ""


async def _crawl_url(url: str) -> dict[str, str]:
    domain = urlparse(url).netloc or "unknown"
    title = ""
    desc = ""
    images: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        " AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "zh-CN,zh;q=0.9",
                },
            )
            html = resp.text[:50000]
            title = _extract_meta(html, "og:title", "title")
            desc = _extract_meta(html, "og:description", "description")
            # Extract image URLs (og:image first, then img tags)
            og_image = _extract_meta(html, "og:image", "")
            images = [og_image] if og_image else []
            # img tags
            imgs = re.findall(r'<img[^>]+src=["\x27]([^"\x27]+)["\x27]', html, re.IGNORECASE)
            imgs += re.findall(r'<img[^>]+data-src=["\x27]([^"\x27]+)["\x27]', html, re.IGNORECASE)
            # Filter to likely product images
            for img in imgs:
                if img.startswith("http") and img not in images:
                    if any(t in img.lower() for t in [".jpg", ".jpeg", ".png", ".webp", "img", "image", "n5", "n4", "n3", "400x400", "800x800"]):
                        images.append(img)
            # Add any remaining HTTP images as fallback
            for img in imgs:
                if img.startswith("http") and img not in images:
                    images.append(img)
            images = images[:8]
    except Exception as exc:
        return {"error": str(exc), "domain": domain, "title": "", "description": "", "images": []}
    return {"domain": domain, "title": title, "description": desc, "images": images, "error": ""}


def _load_topics_store() -> list[dict]:
    data = load_json(TOPICS_FILE)
    if not data:
        return []
    topics = data.get("topics", [])
    return topics if isinstance(topics, list) else []


def _save_topics_store(topics: list[dict]) -> None:
    save_json(TOPICS_FILE, {"topics": topics, "updated_at": utc_now_iso()})


def search_trending(keyword: str | None, vertical: str) -> list[TrendingTopic]:
    pool = CURATED_TRENDING.get(vertical, CURATED_TRENDING["电商"])
    topics = [
        TrendingTopic(keyword=kw, heat=heat, vertical=vertical, source="curated")
        for kw, heat in pool
    ]
    if keyword:
        needle = keyword.strip()
        filtered = [t for t in topics if needle in t.keyword or t.keyword in needle]
        topics = filtered if filtered else topics[:8]
    return sorted(topics, key=lambda t: t.heat, reverse=True)


async def search_topics(req: SearchRequest) -> SearchResponse:
    topics = search_trending(req.keyword, req.vertical)
    crawl_record: TopicRecord | None = None

    if req.product_url:
        crawl = await _crawl_url(req.product_url)
        record = TopicRecord(
            id=new_id("t"),
            keyword=req.keyword or (crawl.get("title") or "商品采集")[:40],
            vertical=req.vertical,
            heat=topics[0].heat if topics else 5000,
            crawled_url=req.product_url,
            title=crawl.get("title", ""),
            description=crawl.get("description", ""),
            category=crawl.get("domain", "unknown"),
            images=crawl.get("images", []),
            created_at=utc_now_iso(),
        )
        stored = _load_topics_store()
        stored.insert(0, record.model_dump())
        _save_topics_store(stored[:100])
        crawl_record = record

        if settings.rag_auto_ingest_crawl:
            from orchestrator.rag.service import rag_service

            body = "\n".join(
                filter(
                    None,
                    [
                        crawl.get("title"),
                        crawl.get("description"),
                        f"url: {req.product_url}",
                    ],
                )
            )
            if body.strip():
                rag_service.ingest_crawl_text(
                    body, req.product_url, crawl.get("title", "")
                )

    return SearchResponse(
        topics=topics,
        crawl=crawl_record,
        stored_count=len(_load_topics_store()),
    )


def list_topics(limit: int = 50) -> TopicsListResponse:
    raw = _load_topics_store()[:limit]
    topics = [TopicRecord.model_validate(item) for item in raw]
    return TopicsListResponse(topics=topics, total=len(raw))
