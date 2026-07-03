from __future__ import annotations

import json
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


def find_latest_run(output_base: Path) -> Path | None:
    """Return newest run directory containing manifest.json."""
    if not output_base.exists():
        return None
    candidates = [
        p
        for p in output_base.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_manifest(run_dir: Path) -> dict | None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


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
    env["PIPELINE_MODE"] = settings.pipeline_mode
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(vf_root),
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
        output_base = vf_root / "output" / demo_name
        run_dir = find_latest_run(output_base)
        manifest_path = str(run_dir / "manifest.json") if run_dir else ""
        final_video = ""
        if run_dir and manifest_path and Path(manifest_path).exists():
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            final_name = manifest.get("final_video", "final.mp4")
            candidate = run_dir / str(final_name)
            if candidate.exists():
                final_video = str(candidate)

        if proc.returncode == 0:
            return {
                "status": "ok",
                "message": f"video-factory demo '{demo_name}' completed",
                "output_dir": str(run_dir or output_base),
                "manifest_path": manifest_path,
                "final_video": final_video,
                "pipeline_mode": settings.pipeline_mode,
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
