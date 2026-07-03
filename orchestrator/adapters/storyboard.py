from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from orchestrator.config import settings


def load_storyboard(demo_name: str) -> dict[str, Any]:
    """Load video-factory demo YAML and extract storyboard metadata."""
    vf_root = settings.video_factory_path
    yaml_path = vf_root / "demos" / f"{demo_name}.yaml"

    if not yaml_path.exists():
        return {
            "status": "skipped",
            "message": f"storyboard YAML not found: {yaml_path}",
            "demo_name": demo_name,
            "yaml_path": str(yaml_path),
        }

    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {
            "status": "error",
            "message": f"invalid YAML structure in {yaml_path.name}",
            "demo_name": demo_name,
            "yaml_path": str(yaml_path),
        }

    scenes = raw.get("scenes") or raw.get("segments") or []
    if not isinstance(scenes, list):
        scenes = []

    segment_summaries: list[str] = []
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        code = scene.get("code") or scene.get("id") or (idx + 1)
        title = scene.get("title") or scene.get("role") or f"segment_{code}"
        start = scene.get("start", "")
        end = scene.get("end", "")
        duration = scene.get("duration", "")
        segment_summaries.append(
            f"{code}:{title}({start}-{end},{duration}s)"
            if start != "" or end != ""
            else f"{code}:{title}({duration}s)"
        )

    return {
        "status": "ok",
        "message": f"loaded storyboard {yaml_path.name} ({len(scenes)} segments)",
        "demo_name": demo_name,
        "yaml_path": str(yaml_path),
        "title": str(raw.get("title") or demo_name),
        "type": str(raw.get("type") or raw.get("slug") or "demo"),
        "duration_target_sec": str(
            raw.get("duration_target_sec") or raw.get("duration_target") or "15"
        ),
        "segment_count": str(len(scenes)),
        "segments": "|".join(segment_summaries),
        "tier": str(raw.get("tier") or "basic"),
        "width": str(raw.get("width") or ""),
        "height": str(raw.get("height") or ""),
        "fps": str(raw.get("fps") or ""),
    }


def resolve_demo_yaml_path(demo_name: str) -> Path:
    return settings.video_factory_path / "demos" / f"{demo_name}.yaml"
