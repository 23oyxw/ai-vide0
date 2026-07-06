import asyncio
from pathlib import Path
import shutil

import pytest

from orchestrator.modules.l4_render.models import RenderRequest
from orchestrator.modules.l4_render import service


@pytest.mark.integration
async def test_kenburns_smoke(tmp_path):
    # Simple smoke: request a motion_poster render without CogVideo, ensure output video or scenes are produced
    req = RenderRequest(job_id="kenburns-smoke-1", demo_name="motion_poster", enable_cogvideo=False)
    res = await service.start_render(req)
    assert res is not None
    out_dir = Path(res.job.output_dir)
    # Either a final video exists or at least scene files were generated
    video = out_dir / "output.mp4"
    scene_exists = any(out_dir.glob('s*.mp4'))
    assert video.exists() or scene_exists
