from __future__ import annotations

from pathlib import Path

import yaml

from orchestrator.adapters.storyboard import load_storyboard
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l2_content.service import get_script
from orchestrator.modules.l3_storyboard.models import (
    BuildStoryboardRequest,
    StoryboardRecord,
    StoryboardResponse,
    StoryboardSegment,
)

STORYBOARDS_DIR = module_dir("l3", "storyboards")


def _segments_from_yaml(raw: dict, script_segments: list | None = None) -> list[StoryboardSegment]:
    scenes = raw.get("scenes") or raw.get("segments") or []
    segments: list[StoryboardSegment] = []
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        code = str(scene.get("code") or scene.get("id") or idx + 1)
        narration = ""
        if script_segments and idx < len(script_segments):
            narration = script_segments[idx].get("narration", "")
        segments.append(
            StoryboardSegment(
                code=code,
                title=str(scene.get("title") or scene.get("role") or f"segment_{code}"),
                start=float(scene.get("start") or 0),
                end=float(scene.get("end") or 0),
                duration=float(scene.get("duration") or 0),
                narration=narration or str(scene.get("narration") or ""),
                visual=str(scene.get("visual") or scene.get("shot") or ""),
            )
        )
    return segments


def build_from_script(req: BuildStoryboardRequest) -> StoryboardResponse:
    script_segments: list[dict] = []
    if req.script_id:
        script_data = get_script(req.script_id)
        if script_data:
            script_segments = [s.model_dump() for s in script_data.script.segments]

    yaml_result = load_storyboard(req.demo_name)
    yaml_path = yaml_result.get("yaml_path", "")
    raw: dict = {}
    if yaml_path and Path(yaml_path).exists():
        loaded = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded

    if req.segments_override:
        segments = req.segments_override
    elif script_segments:
        segments = [
            StoryboardSegment(
                code=s.get("code", f"s{i}"),
                title=s.get("role", "segment"),
                start=s.get("start_sec", 0),
                end=s.get("end_sec", 0),
                duration=s.get("duration_sec", 0),
                narration=s.get("narration", ""),
            )
            for i, s in enumerate(script_segments)
        ]
    else:
        segments = _segments_from_yaml(raw, script_segments)

    sb_id = new_id("sb")
    record = StoryboardRecord(
        id=sb_id,
        demo_name=req.demo_name,
        title=str(raw.get("title") or yaml_result.get("title") or req.demo_name),
        duration_target_sec=float(raw.get("duration_target_sec") or 15),
        width=int(raw.get("width") or 1080),
        height=int(raw.get("height") or 1920),
        fps=int(raw.get("fps") or 30),
        segments=segments,
        yaml_path=yaml_path,
        created_at=utc_now_iso(),
    )
    save_json(STORYBOARDS_DIR / f"{sb_id}.json", record.model_dump())
    return StoryboardResponse(storyboard=record)


def get_storyboard(storyboard_id: str) -> StoryboardResponse | None:
    data = load_json(STORYBOARDS_DIR / f"{storyboard_id}.json")
    if not data:
        return None
    return StoryboardResponse(storyboard=StoryboardRecord.model_validate(data))
