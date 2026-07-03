from __future__ import annotations

from orchestrator.adapters.ai_koubo import publish_video
from orchestrator.adapters.multi_platform import publish_to_platforms
from orchestrator.modules.common import list_json_records, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l7_publish.models import (
    PublishRequest,
    PublishedListResponse,
    PublishedRecord,
    PublishResponse,
)

PUBLISHED_DIR = module_dir("l7", "published")


def _utm_ids(job_id: str) -> tuple[str, str]:
    return f"seed_{job_id}", f"video_{job_id}"


async def publish(req: PublishRequest) -> PublishResponse:
    utm_campaign, utm_content = _utm_ids(req.job_id)
    platform_results = publish_to_platforms(
        job_id=req.job_id,
        video_path=req.video_path,
        title=req.title,
        platforms=req.platforms,
    )
    koubo = await publish_video(
        job_id=req.job_id,
        video_path=req.video_path,
        title=req.title,
        cover_path=req.cover_path,
    )

    targets = [r.get("platform", "") for r in platform_results if r.get("ok")]
    publish_target = ", ".join(targets) or koubo.get("artifacts", {}).get("publish_target", "ai-koubo")
    blob_path = req.blob_path or f"blob://published/{req.job_id}/final.mp4"
    status = koubo.get("status", "ok")

    record = PublishedRecord(
        id=new_id("pub"),
        job_id=req.job_id,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        video_path=req.video_path,
        blob_path=blob_path,
        publish_target=publish_target,
        platforms=req.platforms,
        status=status,
        created_at=utc_now_iso(),
    )
    save_json(PUBLISHED_DIR / f"{record.id}.json", record.model_dump())
    return PublishResponse(published=record)


def list_published(limit: int = 50) -> PublishedListResponse:
    items = [PublishedRecord.model_validate(r) for r in list_json_records(PUBLISHED_DIR)[:limit]]
    return PublishedListResponse(items=items, total=len(items))
