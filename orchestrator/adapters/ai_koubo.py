from __future__ import annotations

import json

import httpx

from orchestrator.config import settings

DEFAULT_TIMEOUT = 30.0
SCRIPT_STYLE = "种草口播"


def _base_url() -> str:
    return settings.ai_koubo_url.rstrip("/")


async def _reachable() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{_base_url()}/api/health")
            return response.status_code == 200
    except Exception:
        return False


async def check_health() -> dict:
    """Probe ai-koubo GET /api/health."""
    url = _base_url()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/api/health")
            response.raise_for_status()
            return {
                "status": "ok",
                "reachable": True,
                "url": url,
                "health": response.json(),
            }
    except Exception as exc:
        return {
            "status": "skipped",
            "reachable": False,
            "url": url,
            "message": str(exc),
        }


async def generate_script(
    *,
    product_url: str | None = None,
    raw_text: str = "",
    style: str = SCRIPT_STYLE,
) -> dict:
    """L2: POST /api/pipeline/extract + /api/pipeline/rewrite, stub if offline."""
    if not await _reachable():
        return _generate_script_stub(product_url, raw_text)

    base = _base_url()
    source_text = raw_text.strip()

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            if not source_text and product_url:
                extract_resp = await client.post(
                    f"{base}/api/pipeline/extract",
                    json={
                        "source_url": product_url,
                        "raw_text": "",
                        "provider_mode": "auto",
                    },
                )
                if extract_resp.status_code == 200:
                    extract_data = extract_resp.json()
                    source_text = extract_data.get("text", "").strip()

            if not source_text:
                seed = product_url or "种草产品"
                source_text = f"【对标参考】{seed} — 15秒种草口播参考文案。"

            rewrite_resp = await client.post(
                f"{base}/api/pipeline/rewrite",
                json={
                    "text": source_text,
                    "style": style,
                    "provider_mode": "auto",
                },
            )
            rewrite_resp.raise_for_status()
            rewrite_data = rewrite_resp.json()
            script = rewrite_data.get("text", source_text)
            return {
                "status": "ok",
                "message": (
                    f"script via ai-koubo ({rewrite_data.get('provider', 'unknown')})"
                ),
                "artifacts": {"script": script},
                "provider": rewrite_data.get("provider"),
            }
    except Exception as exc:
        stub = _generate_script_stub(product_url, raw_text)
        stub["message"] = f"ai-koubo unreachable, stub fallback: {exc}"
        return stub


def _generate_script_stub(product_url: str | None, raw_text: str) -> dict:
    script = raw_text.strip() or "[stub] product seeding script"
    if product_url and not raw_text:
        script = f"[stub] 种草脚本 — {product_url}"
    return {
        "status": "ok",
        "message": "stub script generated (ai-koubo offline)",
        "artifacts": {"script": script},
    }


async def publish_video(
    *,
    job_id: str,
    video_path: str = "",
    title: str = "",
    cover_path: str = "",
) -> dict:
    """L7: POST /api/pipeline/publish, stub if offline."""
    if not await _reachable():
        return _publish_stub(job_id, video_path=video_path)

    payload = {
        "video_path": video_path or str(
            settings.ai_koubo_path / "stub" / f"{job_id}.mp4"
        ),
        "title": title or f"种草视频 {job_id}",
        "cover_path": cover_path,
        "platforms": ["douyin"],
        "provider_mode": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{_base_url()}/api/pipeline/publish",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "status": "ok",
                "message": (
                    f"publish queued via ai-koubo ({data.get('provider', 'unknown')})"
                ),
                "artifacts": {
                    "publish_target": "ai-koubo",
                    "video_path": video_path,
                    "publish_provider": str(data.get("provider", "")),
                    "publish_results": json.dumps(
                        data.get("results", []), ensure_ascii=False
                    ),
                },
            }
    except Exception as exc:
        stub = _publish_stub(job_id, video_path=video_path)
        stub["message"] = f"ai-koubo publish failed, stub fallback: {exc}"
        return stub


def _publish_stub(job_id: str, *, video_path: str = "") -> dict:
    koubo = settings.ai_koubo_path
    artifacts: dict[str, str] = {"publish_target": "ai-koubo-stub"}
    if video_path:
        artifacts["video_path"] = video_path
    if not koubo.exists():
        return {
            "status": "skipped",
            "message": f"AI_KOUBO unreachable and path not found: {koubo}",
            "artifacts": artifacts,
        }
    msg = f"publish stub for job {job_id} (ai-koubo offline at {koubo})"
    if video_path:
        msg += f"; video={video_path}"
    return {
        "status": "ok",
        "message": msg,
        "artifacts": artifacts,
    }


def publish_stub(job_id: str) -> dict:
    """Sync stub kept for backward compatibility."""
    return _publish_stub(job_id)
