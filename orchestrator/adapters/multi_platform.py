"""Multi-platform publishing adapter for douyin, xiaohongshu, kuaishou, wechat."""

from typing import Any

PLATFORM_CONFIGS = {
    "douyin": {
        "name": "抖音",
        "max_duration_sec": 300,
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "max_title_len": 55,
        "supports_cover": True,
        "recommended_tags": ["种草", "好物推荐"],
    },
    "xiaohongshu": {
        "name": "小红书",
        "max_duration_sec": 300,
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "max_title_len": 20,
        "supports_cover": True,
        "recommended_tags": ["好物分享", "种草"],
    },
    "kuaishou": {
        "name": "快手",
        "max_duration_sec": 600,
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "max_title_len": 80,
        "supports_cover": True,
        "recommended_tags": ["好物", "实惠"],
    },
    "wechat": {
        "name": "视频号",
        "max_duration_sec": 1800,
        "aspect_ratio": "16:9",
        "resolution": "1920x1080",
        "max_title_len": 60,
        "supports_cover": False,
        "recommended_tags": ["好物推荐"],
    },
}


def get_platforms() -> dict[str, str]:
    return {k: v["name"] for k, v in PLATFORM_CONFIGS.items()}


def publish_to_platforms(
    job_id: str,
    video_path: str,
    title: str = "",
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Stub multi-platform publish. Returns results per platform.

    In production, each platform would have an OAuth-integrated adapter
    that calls the platform's content API.
    """
    targets = platforms or list(PLATFORM_CONFIGS.keys())
    results: list[dict[str, Any]] = []

    for platform_id in targets:
        config = PLATFORM_CONFIGS.get(platform_id)
        if not config:
            results.append({
                "platform": platform_id,
                "ok": False,
                "error": f"Unknown platform: {platform_id}",
            })
            continue

        # Stub: skip platforms where video path is empty
        if not video_path:
            results.append({
                "platform": platform_id,
                "ok": True,
                "status": "skipped",
                "url": "",
                "message": f"[{config['name']}] skipped: no video path",
            })
            continue

        results.append({
            "platform": platform_id,
            "ok": True,
            "status": "published",
            "url": f"https://{platform_id}.example.com/video/{job_id}",
            "title": (title or "种草视频")[: config["max_title_len"]],
            "tags": config["recommended_tags"],
            "message": f"[{config['name']}] queued for publish (stub)",
        })

    return results
