from __future__ import annotations

from pathlib import Path

from orchestrator.adapters.c4d import render_project
from orchestrator.adapters.c4d_scene2 import render_scene2_stub
from orchestrator.adapters.video_factory import run_demo
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l3_storyboard.service import get_storyboard
from orchestrator.modules.l4_render.models import RenderJobRecord, RenderRequest, RenderResponse, RenderStatusResponse

RENDERS_DIR = module_dir("l4", "renders")


def _render_path(job_id: str) -> Path:
    return RENDERS_DIR / f"{job_id}.json"


async def start_render(req: RenderRequest) -> RenderResponse:
    job_id = req.job_id or new_id("r")
    demo_name = req.demo_name
    if req.storyboard_id:
        sb = get_storyboard(req.storyboard_id)
        if sb:
            demo_name = sb.storyboard.demo_name

    messages: list[str] = []
    manifest_path = ""
    video_path = ""
    output_dir = ""
    c4d_scene2_output = ""
    status = "ok"

    vf_result = run_demo(demo_name)
    if vf_result["status"] == "ok":
        output_dir = vf_result.get("output_dir", "")
        manifest_path = vf_result.get("manifest_path", "")
        video_path = vf_result.get("final_video", "")
        messages.append(vf_result["message"])
    elif vf_result["status"] == "skipped":
        messages.append(vf_result["message"])
        status = "skipped"
    else:
        messages.append(vf_result["message"])
        status = "error"

    if manifest_path and req.enable_c4d_scene2:
        c4d_s2 = render_scene2_stub(manifest_path, output_dir)
        if c4d_s2["status"] == "ok":
            c4d_scene2_output = c4d_s2.get("output", "")
        messages.append(c4d_s2["message"])

    if req.c4d_project:
        c4d_result = render_project(req.c4d_project)
        messages.append(c4d_result["message"])

    now = utc_now_iso()
    job = RenderJobRecord(
        job_id=job_id,
        status=status,
        demo_name=demo_name,
        manifest_path=manifest_path,
        video_path=video_path,
        output_dir=output_dir,
        c4d_scene2_output=c4d_scene2_output,
        messages=messages,
        created_at=now,
        updated_at=now,
    )
    save_json(_render_path(job_id), job.model_dump())
    return RenderResponse(job=job)


def get_render_status(job_id: str) -> RenderStatusResponse | None:
    data = load_json(_render_path(job_id))
    if not data:
        return None
    return RenderStatusResponse(job=RenderJobRecord.model_validate(data))
