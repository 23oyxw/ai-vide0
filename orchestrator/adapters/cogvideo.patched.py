"""CogVideoX-3 video generation adapter for L4 rendering.

Async submit → poll → download flow, integrated into the orchestrator pipeline.

Usage::
    from orchestrator.adapters.cogvideo import submit_render, poll_render, generate_clip
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from orchestrator.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
POLL_MAX = 300  # hard cap on poll iterations


# ── Helpers ────────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return settings.zhipu_api_key.strip()


def _is_configured() -> bool:
    return bool(_api_key())


def _video_url() -> str:
    return f"{settings.zhipu_base_url.rstrip('/')}/videos/generations"


# ── Submit ─────────────────────────────────────────────────────────────────────


async def submit_render(
    prompt: str,
    *,
    image_url: str | None = None,
    duration: int | None = None,
    quality: str | None = None,
    size: str | None = None,
    with_audio: bool = False,
) -> dict[str, Any]:
    """Submit a video generation task to CogVideoX-3.

    Args:
        prompt: Text description (≤512 chars). The scene to generate.
        image_url: Optional first-frame image (URL or base64 data URI, ≤5MB).
        duration: 5 or 10 seconds (default from settings).
        quality: 'speed' (fast/cheap) or 'quality' (best results).
        size: e.g. '1920x1080', '1280x720'.  短边 >= 768.
        with_audio: Generate AI audio track (experimental).

    Returns:
        {"status": "ok"|"error", "task_id": str, "message": str}
    """
    if not _is_configured():
        return {
            "status": "skipped",
            "task_id": "",
            "message": "ZHIPU_API_KEY not configured — CogVideo unavailable",
        }

    payload: dict[str, Any] = {
        "model": settings.cogvideo_model,
        "prompt": prompt[:512],
        "quality": quality or settings.cogvideo_quality,
        "size": size or settings.cogvideo_size,
        "duration": duration or settings.cogvideo_duration,
        "with_audio": with_audio,
    }
    if image_url:
        payload["image_url"] = image_url

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _video_url(),
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            body: dict = resp.json()
            task_id = body.get("id", "")
            return {
                "status": "ok",
                "task_id": task_id,
                "model": settings.cogvideo_model,
                "message": f"CogVideo task submitted: {task_id}",
            }
    except httpx.HTTPStatusError as exc:
        logger.warning("CogVideo submit HTTP %s: %s", exc.response.status_code, exc)
        return {
            "status": "error",
            "task_id": "",
            "message": f"CogVideo HTTP {exc.response.status_code}",
        }
    except Exception as exc:
        logger.warning("CogVideo submit failed: %s", exc)
        return {
            "status": "error",
            "task_id": "",
            "message": str(exc),
        }


# ── Poll ───────────────────────────────────────────────────────────────────────


async def poll_render(task_id: str) -> dict[str, Any]:
    """Poll a CogVideo task until completion or timeout.

    Args:
        task_id: The task ID returned by submit_render.

    Returns:
        {"status": "ok"|"error"|"timeout", "video_url": str, "message": str,
         "duration_ms": int, "polls": int}
    """
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
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {_api_key()}"},
                )
                resp.raise_for_status()
                body: dict = resp.json()
                task_status: str = body.get("status", body.get("task_status", "unknown"))

                if task_status == "success" or task_status == "completed":
                    video_url = body.get("video_url", "")
                    if not video_url:
                        # Some versions return video_result as a list
                        video_result = body.get("video_result", [])
                        if isinstance(video_result, list) and video_result:
                            video_url = video_result[0].get("url", "")
                    return {
                        "status": "ok",
                        "video_url": video_url,
                        "message": f"CogVideo task completed after {polls} polls",
                        "duration_ms": int((time.monotonic() + settings.cogvideo_poll_max_seconds - deadline + settings.cogvideo_poll_max_seconds) * 1000),
                        "polls": polls,
                    }

                if task_status == "failed" or task_status == "error":
                    return {
                        "status": "error",
                        "video_url": "",
                        "message": f"CogVideo task failed: {body.get('error', body.get('message', ''))}",
                        "polls": polls,
                    }

                # Still processing → wait
                await asyncio.sleep(settings.cogvideo_poll_interval)

        except Exception as exc:
            logger.warning("CogVideo poll error (attempt %s): %s", polls, exc)
            await asyncio.sleep(settings.cogvideo_poll_interval * 2)

    return {
        "status": "timeout",
        "video_url": "",
        "message": f"CogVideo poll timeout after {polls} attempts ({settings.cogvideo_poll_max_seconds}s)",
        "polls": polls,
    }


# ── One-shot convenience ──────────────────────────────────────────────────────


async def generate_clip(
    prompt: str,
    *,
    image_url: str | None = None,
    duration: int | None = None,
    quality: str | None = None,
    size: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Submit + poll in one call.  Convenience wrapper around submit_render + poll_render.

    Args:
        prompt: Scene description (≤512 chars).
        image_url: Optional first frame.
        duration: 5 or 10 seconds.
        quality: 'speed' or 'quality'.
        size: e.g. '1920x1080'.
        output_dir: If provided, saves video_url as 'cogvideo_output.mp4' in this dir.

    Returns:
        {"status": "ok"|"error"|"timeout", "task_id": str, "video_url": str,
         "local_path": str, "message": str}
    """
    submit = await submit_render(
        prompt=prompt,
        image_url=image_url,
        duration=duration,
        quality=quality,
        size=size,
    )
    if submit["status"] != "ok":
        submit["local_path"] = ""
        return submit

    task_id: str = submit["task_id"]
    result = await poll_render(task_id)
    result["task_id"] = task_id
    result["prompt"] = prompt

    # Download video if output_dir provided
    local_path = ""
    if output_dir and result.get("video_url"):
        local_path = await _download_video(result["video_url"], output_dir, task_id)
    result["local_path"] = local_path

    return result


async def _download_video(video_url: str, output_dir: str, task_id: str) -> str:
    """Download generated video to output_dir.  Returns local path or empty string."""
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
        logger.warning("CogVideo download failed: %s", exc)
        return ""


# ── Health ─────────────────────────────────────────────────────────────────────

def check_cogvideo() -> dict[str, Any]:
    """Synchronous health probe for /tools/check integration."""
    return {
        "configured": _is_configured(),
        "model": settings.cogvideo_model,
        "quality": settings.cogvideo_quality,
        "duration": settings.cogvideo_duration,
        "size": settings.cogvideo_size,
        "poll_max_s": settings.cogvideo_poll_max_seconds,
    }

