from __future__ import annotations

import json
import subprocess
from pathlib import Path

from orchestrator.config import settings


def render_scene2_stub(manifest_path: str, output_dir: str | None = None) -> dict:
    """
    Optional C4D S2 render via video-factory c4d_render.ps1.
    Skips when no .c4d project template is configured or found.
    """
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return {
            "status": "skipped",
            "message": f"manifest not found for C4D S2: {manifest_path}",
        }

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    c4d_handoff = manifest.get("c4d_handoff") or {}
    project_template = c4d_handoff.get("c4d_project_template") or c4d_handoff.get(
        "project_template"
    )

    vf_root = settings.video_factory_path
    candidates: list[Path] = []
    if project_template:
        candidates.append(Path(str(project_template)))
    candidates.extend(
        [
            vf_root / "templates" / "product_hero.c4d",
            settings.c4d_root / "templates" / "product_hero.c4d",
        ]
    )
    if settings.c4d_project_template:
        candidates.append(settings.c4d_project_template)

    project_path: Path | None = None
    for candidate in candidates:
        if candidate.exists() and candidate.suffix.lower() == ".c4d":
            project_path = candidate
            break

    if project_path is None:
        return {
            "status": "skipped",
            "message": "C4D S2 skipped: no .c4d project template found",
        }

    run_dir = Path(output_dir) if output_dir else manifest_file.parent
    assets_dir = run_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_mp4 = assets_dir / "scene_02_c4d.mp4"

    script = vf_root / "scripts" / "c4d_render.ps1"
    if not script.exists():
        return {
            "status": "skipped",
            "message": f"c4d_render.ps1 not found: {script}",
        }

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Project",
        str(project_path.resolve()),
        "-Output",
        str(output_mp4.resolve()),
        "-Frame",
        "0-120",
        "-Width",
        "1080",
        "-Height",
        "1920",
        "-C4DExe",
        str(settings.c4d_commandline),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,
            cwd=str(vf_root),
        )
        if proc.returncode == 0 and output_mp4.exists():
            return {
                "status": "ok",
                "message": f"C4D S2 rendered: {output_mp4.name}",
                "output": str(output_mp4),
                "project": str(project_path),
            }
        return {
            "status": "error",
            "message": proc.stderr[-1000] if proc.stderr else f"exit {proc.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "C4D S2 render timed out (1800s)"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
