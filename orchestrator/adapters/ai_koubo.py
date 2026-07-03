from __future__ import annotations

import subprocess

from orchestrator.config import settings


def publish_stub(job_id: str) -> dict:
    """Stub publish via ai-koubo when backend is available."""
    koubo = settings.ai_koubo_path
    if not koubo.exists():
        return {
            "status": "skipped",
            "message": f"AI_KOUBO_PATH not found: {koubo}",
            "artifacts": {},
        }
    return {
        "status": "ok",
        "message": f"publish stub for job {job_id} (ai-koubo at {koubo})",
        "artifacts": {"publish_target": "ai-koubo-stub"},
    }


def openclaw_video_generate(prompt: str, timeout: int = 300) -> dict:
    """Call OpenClaw video_generate if CLI is available."""
    cmd = [settings.openclaw_bin, "video", "generate", "--prompt", prompt]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return {"status": "ok", "message": "openclaw video generated", "stdout": proc.stdout}
        return {
            "status": "skipped",
            "message": f"openclaw not available or failed: {proc.stderr[:500]}",
        }
    except FileNotFoundError:
        return {"status": "skipped", "message": "openclaw CLI not in PATH"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
