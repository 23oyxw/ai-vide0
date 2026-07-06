from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from orchestrator.config import settings

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 30.0
POLL_MAX = 300


def _api_key() -> str:
    return settings.zhipu_api_key.strip()


def _is_configured() -> bool:
    return bool(_api_key())


def _video_url() -> str:
    return f"{settings.zhipu_base_url.rstrip('/')}/videos/generations"


async def submit_render(prompt: str, *, image_url: str | None = None, duration: int | None = None, quality: str | None = None, size: str | None = None, with_audio: bool = False) -> dict[str, Any]:
    if not _is_configured():
        return {"status": "skipped", "task_id": "", "message": "ZHIPU_API_KEY not configured — CogVideo unavailable"}
    payload: dict[str, Any] = {"model": settings.cogvideo_model, "prompt": prompt[:512], "quality": quality or settings.cogvideo_quality, "size": size or settings.cogvideo_size, "duration": duration or settings.cogvideo_duration, "with_audio": with_audio}
    if image_url:
        payload["image_url"] = image_url
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(_video_url(), headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}, json=payload)
            if resp.status_code != 200:
                logger.warning("CogVideo submit HTTP %s: %s", resp.status_code, (resp.text or '')[:400])
                return {"status": "error", "task_id": "", "message": f"CogVideo HTTP {resp.status_code}: {(resp.text or '')[:200]}"}
            body: dict = resp.json()
            task_id = body.get("id", "")
            return {"status": "ok", "task_id": task_id, "model": settings.cogvideo_model, "message": f"CogVideo task submitted: {task_id}"}
    except Exception as exc:
        logger.exception("CogVideo submit failed: %s", exc)
        return {"status": "error", "task_id": "", "message": str(exc)}


async def poll_render(task_id: str) -> dict[str, Any]:
    if not task_id:
        return {"status": "error", "video_url": "", "message": "No task_id provided"}
    if not _is_configured():
        return {"status": "error", "video_url": "", "message": "ZHIPU_API_KEY not configured"}
    url = f"{_video_url()}/{task_id}"
    deadline = time.monotonic() + settings.cogvideo_poll_max_seconds
    polls = 0
    while time.monotonic() < deadline and polls < POLL_MAX:
        polls += 1
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {_api_key()}"})
                if resp.status_code != 200:
                    logger.warning("CogVideo poll HTTP %s: %s", resp.status_code, (resp.text or '')[:400])
                    await asyncio.sleep(settings.cogvideo_poll_interval)
                    continue
                body: dict = resp.json()
                task_status: str = body.get("status", body.get("task_status", "unknown"))
                if task_status in ("success", "completed"):
                    video_url = body.get("video_url", "")
                    if not video_url:
                        video_result = body.get("video_result", [])
                        if isinstance(video_result, list) and video_result:
                            video_url = video_result[0].get("url", "")
                    return {"status": "ok", "video_url": video_url, "message": f"CogVideo task completed after {polls} polls", "duration_ms": int((time.monotonic() + settings.cogvideo_poll_max_seconds - deadline + settings.cogvideo_poll_max_seconds) * 1000), "polls": polls}
                if task_status in ("failed", "error"):
                    return {"status": "error", "video_url": "", "message": f"CogVideo task failed: {body.get("error", body.get("message", ""))}", "polls": polls}
                await asyncio.sleep(settings.cogvideo_poll_interval)
        except Exception as exc:
            logger.warning("CogVideo poll error (attempt %s): %s", polls, exc)
            await asyncio.sleep(settings.cogvideo_poll_interval * 2)
    return {"status": "timeout", "video_url": "", "message": f"CogVideo poll timeout after {polls} attempts ({settings.cogvideo_poll_max_seconds}s)", "polls": polls}


async def generate_clip(prompt: str, *, image_url: str | None = None, duration: int | None = None, quality: str | None = None, size: str | None = None, output_dir: str | None = None) -> dict[str, Any]:
    submit = await submit_render(prompt=prompt, image_url=image_url, duration=duration, quality=quality, size=size)
    if submit["status"] != "ok":
        submit["local_path"] = ""
        return submit
    task_id: str = submit["task_id"]
    result = await poll_render(task_id)
    result["task_id"] = task_id
    result["prompt"] = prompt
    local_path = ""
    if output_dir and result.get("video_url"):
        local_path = await _download_video(result["video_url"], output_dir, task_id)
    result["local_path"] = local_path
    return result


async def _download_video(video_url: str, output_dir: str, task_id: str) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"cogvideo_{task_id}.mp4"
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(video_url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            logger.info("CogVideo downloaded: %s", dest)
            return str(dest)
    except Exception as exc:
        logger.exception("CogVideo download failed: %s", exc)
        return ""


def check_cogvideo() -> dict[str, Any]:
    return {"configured": _is_configured(), "model": settings.cogvideo_model, "quality": settings.cogvideo_quality, "duration": settings.cogvideo_duration, "size": settings.cogvideo_size, "poll_max_s": settings.cogvideo_poll_max_seconds}

