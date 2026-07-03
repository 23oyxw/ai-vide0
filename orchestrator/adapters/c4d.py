from __future__ import annotations

import subprocess
from pathlib import Path

from orchestrator.config import settings


def render_project(
    project_path: str,
    output_path: str | None = None,
    width: int = 1920,
    height: int = 1080,
    timeout: int = 1800,
) -> dict:
    """Wrap C4D Commandline.exe for headless render."""
    exe = settings.c4d_commandline
    if not exe.exists():
        return {
            "status": "skipped",
            "message": f"C4D Commandline not found: {exe}",
        }

    project = Path(project_path)
    if not project.exists():
        return {
            "status": "error",
            "message": f"C4D project not found: {project_path}",
        }

    out = Path(output_path) if output_path else project.with_suffix(".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    # C4D R23 commandline: load project, render to output
    cmd = [
        str(exe),
        "-load", str(project.resolve()),
        "-oimage", str(out.resolve()),
        "-ow", str(width),
        "-oh", str(height),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(settings.c4d_root),
        )
        if proc.returncode == 0 and out.exists():
            return {
                "status": "ok",
                "message": f"rendered to {out}",
                "output": str(out),
            }
        return {
            "status": "error",
            "message": proc.stderr[-1000] if proc.stderr else f"exit {proc.returncode}",
            "stdout": proc.stdout[-500:] if proc.stdout else "",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"C4D render timed out ({timeout}s)"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def check_c4d() -> dict:
    exe = settings.c4d_commandline
    c4dpy = settings.c4d_root / "c4dpy.exe"
    return {
        "commandline": str(exe),
        "commandline_exists": exe.exists(),
        "c4dpy": str(c4dpy),
        "c4dpy_exists": c4dpy.exists(),
    }
