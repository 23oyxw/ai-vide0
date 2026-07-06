from __future__ import annotations

import json
from typing import Any

from orchestrator.modules.l1_crawler.models import SearchRequest
from orchestrator.modules.l1_crawler import service as l1
from orchestrator.modules.l2_content.models import GenerateScriptRequest
from orchestrator.modules.l2_content import service as l2
from orchestrator.modules.l3_storyboard.models import BuildStoryboardRequest
from orchestrator.modules.l3_storyboard import service as l3
from orchestrator.modules.l4_render.models import RenderRequest
from orchestrator.modules.l4_render import service as l4
from orchestrator.modules.l5_scheduler.models import JobCreateRequest
from orchestrator.modules.l5_scheduler import service as l5
from orchestrator.modules.l6_qa.models import ValidateRequest
from orchestrator.modules.l6_qa import service as l6
from orchestrator.modules.l7_publish.models import PublishRequest
from orchestrator.modules.l7_publish import service as l7
from orchestrator.modules.l8_analytics import service as l8
from orchestrator.pipeline_state import QA_PASS_THRESHOLD, QA_RETRY_FROM, PipelineState
from orchestrator.rag.context import fetch_rag_context
from orchestrator.schemas import LayerResultPayload, PipelineRunData, PipelineRunRequest


async def run_pipeline(req: PipelineRunRequest) -> PipelineRunData:
    job_resp = l5.create_job(
        JobCreateRequest(
            product_url=req.product_url,
            demo_name=req.demo_name,
            layers=req.layers,
            metadata={"topic": req.topic or "", "script": req.script or ""},
        )
    )
    job_id = job_resp.job.job_id

    artifacts: dict[str, str] = {}
    errors: list[str] = []
    results: list[LayerResultPayload] = []
    pipeline_state = PipelineState.RUNNING
    retry_from: str | None = None
    optimization_hints: list[str] = []
    script_id = ""
    storyboard_id = ""
    render_job_id = ""

    def record(layer_id: str, status: str, message: str, layer_artifacts: dict[str, str]) -> None:
        results.append(
            LayerResultPayload(
                layer_id=layer_id,
                status=status,
                message=message,
                artifacts=layer_artifacts,
            )
        )

    # Progress tracking: update job store after each layer
    total_layers = len(req.layers)
    for idx, lid in enumerate(req.layers):
        from orchestrator.main import _emit_event
        l5.update_job(job_id, {
            "status": "running",
            "pipeline_status": f"layer_{lid}",
            "progress": f"{idx}/{total_layers}",
        })
        _emit_event(job_id, "layer_start", {"layer": lid, "progress": f"{idx}/{total_layers}"})

        if lid == "L1":
            search = await l1.search_topics(
                SearchRequest(
                    keyword=req.topic,
                    product_url=req.product_url,
                    vertical="电商",
                )
            )
            crawl = search.crawl
            # Save crawled image URLs for L4 fallback
            crawled_images = getattr(crawl, "images", []) if crawl else []
            layer_art = {
                "crawled_url": crawl.crawled_url if crawl else (req.product_url or ""),
                "crawled_title": crawl.title if crawl else "",
                "crawled_domain": crawl.category if crawl else "",
                "topics_count": str(len(search.topics)),
                "crawled_images": json.dumps(crawled_images[:4]),
            }
            artifacts.update(layer_art)
            record("L1", "ok", f"L1: {len(search.topics)} trending topics", layer_art)

        elif lid == "L2":
            rag_question = req.topic or req.script or req.product_url or ""
            rag_ctx = fetch_rag_context(rag_question)
            raw_text = req.script or ""
            # Pass RAG context as style/background hint, not as source text to rewrite
            style_hint = ""
            if rag_ctx:
                style_hint = f"知识参考: {rag_ctx[:300]}"
            gen = await l2.generate_script_record(
                GenerateScriptRequest(
                    product_url=req.product_url,
                    topic=req.topic or "",
                    raw_text=raw_text,
                    style=style_hint,
                )
            )
            script_id = gen.script.id
            layer_art = {
                "script": gen.script.full_text,
                "script_id": script_id,
                "segment_count": str(len(gen.script.segments)),
                "script_provider": gen.script.provider,
            }
            if rag_ctx:
                layer_art["rag_context_chars"] = str(len(rag_ctx))
            artifacts.update(layer_art)
            record(
                "L2",
                "ok",
                f"L2: script {script_id} ({gen.script.provider})"
                + (f" +RAG({len(rag_ctx)}ch)" if rag_ctx else ""),
                layer_art,
            )

        elif lid == "L3":
            sb = l3.build_from_script(
                BuildStoryboardRequest(
                    script_id=script_id or None,
                    demo_name=req.demo_name,
                    video_style=getattr(req, "video_style", None) or "real",
                )
            )
            storyboard_id = sb.storyboard.id
            # Emit per-scene details for frontend preview
            scene_descriptions = [
                {"index": s.code, "label": s.title, "duration": s.duration, "narration": s.narration[:60]}
                for s in sb.storyboard.segments
            ]
            layer_art = {
                "storyboard_id": storyboard_id,
                "storyboard_yaml": sb.storyboard.yaml_path,
                "storyboard_title": sb.storyboard.title,
                "segment_count": str(len(sb.storyboard.segments)),
                "demo_name": sb.storyboard.demo_name,
                "scenes": json.dumps(scene_descriptions, ensure_ascii=False),
            }
            artifacts.update(layer_art)
            record("L3", "ok", f"L3: storyboard {storyboard_id}", layer_art)

        elif lid == "L4":
            pipeline_state = PipelineState.L4_RENDER
            script_text = artifacts.get("script", req.script or "")
            crawled_urls = json.loads(artifacts.get("crawled_images", "[]"))
            render = await l4.start_render(
                RenderRequest(
                    storyboard_id=storyboard_id or None,
                    demo_name=req.demo_name,
                    video_style=getattr(req, "video_style", None) or "real",
                    c4d_project=req.c4d_project,
                    job_id=job_id,
                    enable_cogvideo=True,
                    cogvideo_prompt=script_text[:500] if script_text else None,
                    crawled_image_urls=crawled_urls,
                )
            )
            render_job_id = render.job.job_id
            layer_art = {
                "render_job_id": render_job_id,
                "manifest_path": render.job.manifest_path,
                "video_path": render.job.video_path,
                "video_factory_output": render.job.output_dir,
                "pipeline_mode": "module",
            }
            artifacts.update(layer_art)
            status = "error" if render.job.status == "error" else "ok"
            if status == "error":
                errors.extend(render.job.messages)
            record("L4", status, "; ".join(render.job.messages) or "L4 render", layer_art)
            if status == "error":
                pipeline_state = PipelineState.ERROR
                break
            pipeline_state = PipelineState.RUNNING

        elif lid == "L5":
            patch = {
                "status": PipelineState.RUNNING.value,
                "script_id": script_id,
                "storyboard_id": storyboard_id,
                "render_job_id": render_job_id,
                **artifacts,
            }
            l5.update_job(job_id, patch)
            layer_art = {"scheduled_job": job_id}
            artifacts.update(layer_art)
            record("L5", "ok", f"L5: job {job_id} scheduled", layer_art)

        elif lid == "L6":
            script_for_qa = artifacts.get("script", req.script or "")
            qa = await l6.validate(
                ValidateRequest(
                    manifest_path=artifacts.get("manifest_path", ""),
                    output_dir=artifacts.get("video_factory_output", ""),
                    script_text=script_for_qa,
                    force_fail=req.force_qa_fail,
                )
            )
            layer_art = {
                "qa_score": str(qa.score),
                "qa_checks_failed": ",".join(c.name for c in qa.checks if not c.passed),
            }
            rag_hits = [c.name for c in qa.checks if c.name.startswith("rag_")]
            if rag_hits:
                layer_art["rag_qa_checks"] = ",".join(rag_hits)
            artifacts.update(layer_art)
            if not qa.passed:
                errors.append(qa.message)
                retry_from = QA_RETRY_FROM
                pipeline_state = PipelineState.QA_FAILED
                record("L6", "error", qa.message, layer_art)
                break
            record("L6", "ok", qa.message, layer_art)

        elif lid == "L7":
            pub = await l7.publish(
                PublishRequest(
                    job_id=job_id,
                    video_path=artifacts.get("video_path", ""),
                    title=artifacts.get("script", "")[:40],
                    script_id=script_id or None,
                )
            )
            layer_art = {
                "publish_target": pub.published.publish_target,
                "utm_campaign": pub.published.utm_campaign,
                "blob_path": pub.published.blob_path,
            }
            artifacts.update(layer_art)
            record("L7", pub.published.status, f"L7 publish {pub.published.id}", layer_art)

        elif lid == "L8":
            from orchestrator.rag.service import rag_service
            from orchestrator.rag.models import L8SyncRequest

            rag_service.sync_l8(L8SyncRequest(job_id=job_id))
            l8.record_pipeline_metrics(job_id)
            analysis = l8.get_analysis(job_id)
            optimization_hints = analysis.optimization_hints
            layer_art = {
                "optimization_hints": "|".join(analysis.optimization_hints[:6]),
                "metrics_json": analysis.summary,
            }
            artifacts.update(layer_art)
            record("L8", "ok", analysis.summary, layer_art)

    if pipeline_state == PipelineState.QA_FAILED:
        status = "qa_failed"
    elif errors or pipeline_state == PipelineState.ERROR:
        status = "error"
        if pipeline_state not in (PipelineState.QA_FAILED, PipelineState.ERROR):
            pipeline_state = PipelineState.ERROR
    else:
        status = "ok"
        if "L7" in req.layers and artifacts.get("publish_target"):
            pipeline_state = PipelineState.PUBLISHED
        if "L8" in req.layers and results and results[-1].layer_id == "L8":
            pipeline_state = PipelineState.ANALYZED

    l5.update_job(
        job_id,
        {
            "status": pipeline_state.value,
            "pipeline_status": status,
            "script_id": script_id,
            "storyboard_id": storyboard_id,
            "render_job_id": render_job_id,
            "retry_from": retry_from or "",
            "errors": errors,
            **{k: v for k, v in artifacts.items() if isinstance(v, str)},
        },
    )

    return PipelineRunData(
        job_id=job_id,
        status=status,
        pipeline_state=pipeline_state.value,
        layers=list(req.layers),
        layer_results=results,
        artifacts=artifacts,
        errors=errors,
        retry_from=retry_from,
        optimization_hints=optimization_hints,
    )
