from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from orchestrator.config import settings


def _video_factory_python(vf_root: Path) -> str:
    for rel in (".venv/Scripts/python.exe", "venv/Scripts/python.exe"):
        candidate = vf_root / rel
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run_demo(demo_name: str) -> dict:
    """Run video-factory demo as subprocess if path exists."""
    vf_root = settings.video_factory_path
    run_py = vf_root / "run.py"

    if not vf_root.exists():
        return {
            "status": "skipped",
            "message": f"VIDEO_FACTORY_PATH not found: {vf_root}",
        }
    if not run_py.exists():
        return {
            "status": "skipped",
            "message": f"run.py missing in {vf_root}",
        }

    cmd = [_video_factory_python(vf_root), str(run_py), "run", demo_name]
    env = os.environ.copy()
    env.setdefault("PIPELINE_MODE", "mock")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(vf_root),
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        output_dir = str(vf_root / "output" / demo_name)
        if proc.returncode == 0:
            return {
                "status": "ok",
                "message": f"video-factory demo '{demo_name}' completed",
                "output_dir": output_dir,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
            }
        return {
            "status": "error",
            "message": proc.stderr[-1000:] if proc.stderr else f"exit code {proc.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "video-factory timed out (600s)"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def list_demos() -> dict:
    vf_root = settings.video_factory_path
    demos_dir = vf_root / "demos"
    if not demos_dir.exists():
        return {"status": "skipped", "demos": []}
    demos = sorted(p.stem for p in demos_dir.glob("*.yaml"))
    return {"status": "ok", "demos": demos}
