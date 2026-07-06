from __future__ import annotations

import asyncio
import subprocess as _sp
import logging
from pathlib import Path
from typing import Tuple

from orchestrator.adapters.c4d import render_project
from orchestrator.adapters.c4d_scene2 import render_scene2_stub
from orchestrator.adapters.cogvideo_client2 import generate_clip as cogvideo_generate_clip
from orchestrator.adapters.video_factory import run_demo
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l3_storyboard.service import get_storyboard
from orchestrator.modules.l4_render.models import RenderJobRecord, RenderRequest, RenderResponse, RenderStatusResponse

logger = logging.getLogger(__name__)


def _run_cmd(cmd: list[str], timeout: int = 20) -> Tuple[bool, str, str]:
    """Run a subprocess command safely and return (success, stdout, stderr)."""
    try:
        r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.returncode == 0, r.stdout or "", r.stderr or "")
    except _sp.TimeoutExpired as e:
        return (False, "", f"timeout: {e}")
    except Exception as e:
        return (False, "", str(e))


async def _cogvideo_bg(prompt: str, output_dir: str, job_id: str) -> None:
    """Run CogVideo generation in background, update render job when done."""
    try:
        result = await cogvideo_generate_clip(prompt=prompt, output_dir=output_dir)
        if result.get("status") == "ok":
            from orchestrator.modules.common import save_json, utc_now_iso
            data = load_json(Path(output_dir).parent / f"{job_id}.json") or {}
            data["cogvideo_video_url"] = result.get("video_url", "")
            data["cogvideo_local_path"] = result.get("local_path", "")
            data["messages"] = data.get("messages", []) + ["CogVideo done: " + str(result.get("local_path", result.get("video_url", "")))]
            data["updated_at"] = utc_now_iso()
            save_json(Path(output_dir).parent / f"{job_id}.json", data)
    except Exception:
        pass  # best-effort background task

RENDERS_DIR = module_dir("l4", "renders")


def _render_path(job_id: str) -> Path:
    return RENDERS_DIR / f"{job_id}.json"


async def start_render(req: RenderRequest) -> RenderResponse:
    job_id = req.job_id or new_id("r")
    # Use pipeline job_id for output dir so /video/{pipeline_job} works
    output_key = req.job_id if req.job_id else job_id
    demo_name = req.demo_name
    if req.storyboard_id:
        sb = get_storyboard(req.storyboard_id)
        if sb:
            demo_name = sb.storyboard.demo_name

    messages: list[str] = []
    manifest_path = ""
    video_path = ""
    output_dir = str(RENDERS_DIR / output_key)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    import shutil, subprocess as sp

    ffmpeg = shutil.which("ffmpeg") or str(settings.ffmpeg_path)
    has_ffmpeg = bool(ffmpeg and Path(ffmpeg).exists())
    video_path = ""

    if has_ffmpeg:
        from orchestrator.modules.l4_render.templates import (
            generate_template_frame, get_template_config,
        )
        from orchestrator.modules.l2_content.models import GenerateProductImageRequest
        from orchestrator.modules.l2_content.service import generate_product_images

        # Auto-detect Chinese font for FFmpeg
        font_candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        # Default to a common Linux CJK font; fall back to first existing candidate
        font_file = font_candidates[0]
        for fc in font_candidates:
            p = Path(fc)
            if p.exists():
                font_file = str(p)
                break

        # ── Duration from selected template ──
        DURATION_MAP = {
            "motion_poster": 5, "post_production_15s_zhongcao": 15,
            "product_ad": 30, "short_drama": 60,
        }
        total_duration = DURATION_MAP.get(demo_name, 15)
        # Scale scene durations proportionally (base = 15s from SceneDef)
        duration_scale = total_duration / 15.0

        # ── Generate product images (AI > crawled > FFmpeg placeholder) ──
        product_images: list[str] = []
        product_title = (req.cogvideo_prompt or demo_name)[:50]

        import httpx
        # Scene definitions (needed early for count)
        from orchestrator.modules.l4_render.scene_defs import get_scenes
        scene_defs = get_scenes(req.video_style or "real")

        # Pre-download crawled + uploaded images as fallback
        crawled_urls: list[str] = getattr(req, "crawled_image_urls", []) or []
        all_fallback_imgs: list[str] = []
        # Crawled images
        for cu in crawled_urls[:len(scene_defs)]:
            try:
                # Try downloading crawled image with a few retries
                downloaded = False
                for attempt in range(3):
                    try:
                        async with httpx.AsyncClient(timeout=20) as client:
                            r = await client.get(cu)
                            if r.status_code == 200 and len(r.content) > 2000:
                                path = Path(output_dir) / f"crawled_{len(all_fallback_imgs)}.jpg"
                                path.write_bytes(r.content)
                                if path.stat().st_size > 2000:
                                    all_fallback_imgs.append(str(path))
                                    downloaded = True
                                    break
                    except Exception as e:
                        logger.debug("Attempt %s failed downloading %s: %s", attempt + 1, cu, e)
                    await asyncio.sleep(0.5)
                if not downloaded:
                    logger.debug("Failed to download crawled image after retries: %s", cu)
            except Exception:
                pass
        # Uploaded images (from frontend file input)
        for up in sorted(Path(output_dir).glob("uploaded_*.jpg")):
            if up.stat().st_size > 2000 and str(up) not in all_fallback_imgs:
                all_fallback_imgs.append(str(up))
        for up in sorted(Path(output_dir).glob("uploaded_*.png")):
            if up.stat().st_size > 2000 and str(up) not in all_fallback_imgs:
                all_fallback_imgs.append(str(up))
        if all_fallback_imgs:
            messages.append(f"{len(all_fallback_imgs)} fallback images (crawled+uploaded)")

        for idx in range(len(scene_defs)):
            img_file = Path(output_dir) / f"product_{idx}.jpg"
            img_type = ["白底主图", "场景氛围图", "卖点特写图", "场景氛围图"][idx % 4]
            got_img = False

            # 1. Try CogView (Zhipu paid API)
            try:
                img_req = GenerateProductImageRequest(
                    product_title=product_title, category="电商", image_types=[img_type],
                )
                img_result = await generate_product_images(img_req)
                if img_result.images:
                    img_url = img_result.images[0].url
                    if img_url and not img_url.startswith("data:") and len(img_url) > 20:
                        async with httpx.AsyncClient(timeout=60) as client:
                            resp = await client.get(img_url)
                            if resp.status_code == 200 and len(resp.content) > 2000:
                                img_file.write_bytes(resp.content)
                                product_images.append(str(img_file))
                                messages.append(f"CogView: {img_type}")
                                got_img = True
            except Exception:
                pass

            # 2. Try Pollinations.ai (free, no API key, unlimited)
            if not got_img:
                try:
                    from urllib.parse import quote
                    p_prompt = f"{product_title}, {img_type}, e-commerce product photo, clean background, professional studio lighting"
                    poll_url = f"https://image.pollinations.ai/prompt/{quote(p_prompt)}?width=512&height=512&nologo=true"
                    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
                        resp = await client.get(poll_url)
                        if resp.status_code == 200 and len(resp.content) > 2000:
                            img_file.write_bytes(resp.content)
                            product_images.append(str(img_file))
                            messages.append(f"FreeAI: {img_type}")
                            got_img = True
                except Exception:
                    pass

            # 2. Use fallback image (crawled or uploaded) if AI failed
            if not got_img and idx < len(all_fallback_imgs):
                import shutil
                shutil.copy(all_fallback_imgs[idx], img_file)
                product_images.append(str(img_file))
                messages.append(f"Crawled: {img_type}")
                got_img = True

            # 3. FFmpeg product card placeholder (last resort)
            if not got_img:
                label = product_title[:12] if product_title else f"场景{idx+1}"
                img_type_name = ["白底主图", "场景氛围图", "卖点特写图", "场景氛围图"][idx % 4]
                ok, out, err = _run_cmd([
                    ffmpeg, "-y",
                    "-f", "lavfi", "-i", "color=c=0xf5f5f0:s=512x512:d=0.1",
                    "-vf", (
                        f"drawtext=fontfile='{font_file}':text='{label}':"
                        f"fontsize=40:fontcolor=0x333333:"
                        f"x=(w-text_w)/2:y=(h-text_h)/2-30,"
                        f"drawtext=fontfile='{font_file}':text='{img_type_name}':"
                        f"fontsize=22:fontcolor=0x888888:"
                        f"x=(w-text_w)/2:y=(h-text_h)/2+30,"
                        f"drawbox=x=0:y=h-8:w=512:h=8:color=0x4477cc@0.8:t=fill"
                    ),
                    "-frames:v", "1", "-q:v", "3",
                    str(img_file),
                ], timeout=10)
                if ok and img_file.exists() and img_file.stat().st_size > 500:
                    product_images.append(str(img_file))
                    messages.append(f"Placeholder: {label}")
                else:
                    logger.warning("FFmpeg placeholder generation failed for %s: %s", str(img_file), err[:400])
                    messages.append(f"Placeholder failed: {label} - {err[:160]}")

        messages.append(f"{len(product_images)}/{len(scene_defs)} product images")

        # ── Generate template backgrounds ──
        for i in range(len(scene_defs)):
            generate_template_frame(req.video_style, i, Path(output_dir))
        bg_files = sorted(Path(output_dir).glob("bg_*.png"))
        if bg_files:
            messages.append(f"Generated {len(bg_files)} template backgrounds")

        # ── Scene definitions per style ──
        from orchestrator.modules.l4_render.scene_defs import get_scenes
        scene_defs = get_scenes(req.video_style or "real")
        total_duration = DURATION_MAP.get(demo_name, 15)
        scene_dur = total_duration / len(scene_defs)

        # ── Build each scene ──
        raw = req.cogvideo_prompt or demo_name
        lines = [s.strip() for s in raw.split("\n") if s.strip()]
        scene_files = []

        for sd in scene_defs:
            spath = Path(output_dir) / f"s{sd.index}.mp4"
            scene_actual_dur = round(sd.duration_sec * duration_scale, 1)
            scene_text = lines[sd.index] if sd.index < len(lines) else ""
            if not scene_text:
                scene_text = f"【{sd.label}】"
            else:
                scene_text = f"【{sd.label}】\n{scene_text}"
            scene_text = scene_text[:200]
            wrapped = "\n".join(scene_text[j:j+28] for j in range(0, len(scene_text), 28))
            tfile = Path(output_dir) / f"s{sd.index}.txt"
            tfile.write_text(wrapped, encoding="utf-8-sig")  # UTF-8 BOM for Windows FFmpeg
            text_path = str(tfile).replace("\\", "\\\\")

            # Product image for this scene
            prod_file = Path(product_images[sd.index]) if sd.index < len(product_images) else None
            has_prod = prod_file and prod_file.exists() if prod_file else False

            if has_prod:
                # Step 1: product image → video clip with padding (centered on bg color)
                tmp_path = Path(output_dir) / f"tmp_{sd.index}.mp4"
                frames = max(1, int(scene_actual_dur * 24))
                ok, out, err = _run_cmd([
                    ffmpeg, "-y",
                    "-loop", "1", "-i", str(prod_file),
                    "-vf", f"scale=720:-1,zoompan=z='min(zoom+0.001,1.15)':d={frames}:s=720x1280,setsar=1",
                    "-r", "24",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-t", str(scene_actual_dur),
                    str(tmp_path),
                ], timeout=20)
                if not ok:
                    logger.warning("FFmpeg step1 failed for tmp_path %s: %s", str(tmp_path), err[:400])
                    messages.append(f"S{sd.index} step1 ffmpeg error: {err[:160]}")
                # Step 2: add text overlay
                if tmp_path.exists() and tmp_path.stat().st_size > 1000:
                    ok2, out2, err2 = _run_cmd([
                        ffmpeg, "-y",
                        "-i", str(tmp_path),
                        "-vf", (
                            f"drawtext=fontfile='C\\:/Windows/Fonts/simhei.ttf':"
                            f"textfile='{text_path}':fontsize=22:fontcolor=white:"
                            f"x=(w-text_w)/2:y=h-text_h-60:"
                            f"box=1:boxcolor=black@0.5:boxborderw=8:line_spacing=6"
                        ),
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        str(spath),
                    ], timeout=15)
                    if not ok2:
                        logger.warning("FFmpeg drawtext failed for scene %s: %s", sd.index, err2[:400])
                        r = type("R", (), {"stderr": err2})()
                    else:
                        r = type("R", (), {"stderr": ""})()
                else:
                    r = None
                    messages.append(f"S{sd.index} step1 fail")
            else:
                ok3, out3, err3 = _run_cmd([
                    ffmpeg, "-y",
                    "-f", "lavfi", "-i", f"color=c={sd.bg_color}:s=720x1280:d={scene_actual_dur}:r=24",
                    "-vf", (
                        f"drawtext=fontfile='C\\:/Windows/Fonts/simhei.ttf':"
                        f"textfile='{text_path}':fontsize=22:fontcolor=white:"
                        f"x=(w-text_w)/2:y=(h-text_h)/2:"
                        f"box=1:boxcolor=black@0.5:boxborderw=8:line_spacing=6"
                    ),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    str(spath),
                ], timeout=20)
                if not ok3:
                    logger.warning("FFmpeg scene generation failed for scene %s: %s", sd.index, err3[:400])
                    r = type("R", (), {"stderr": err3})()

            if spath.exists() and spath.stat().st_size > 1000:
                scene_files.append(spath)
            else:
                messages.append(f"S{sd.index} fail: {r.stderr[:80] if r else 'no output'}")

        if len(scene_files) >= 2:
            ov = Path(output_dir) / "output.mp4"
            args = [ffmpeg, "-y"]
            for s in scene_files:
                args.extend(["-i", str(s)])
            filter_parts = "".join(f"[{i}:v]" for i in range(len(scene_files)))
            args.extend([
                "-filter_complex", f"{filter_parts}concat=n={len(scene_files)}:v=1:a=0[outv]",
                "-map", "[outv]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(ov),
            ])
            sp.run(args, capture_output=True, text=True, timeout=30)
            if ov.exists() and ov.stat().st_size > 5000:
                video_path = str(ov)
                manifest_path = str(Path(output_dir) / "manifest.json")
                messages.append(f"{len(scene_defs)}-scene video {len(scene_files)}x{scene_dur:.1f}s={total_duration}s")
            else:
                messages.append("Concat failed, using fallback")
        else:
            messages.append(f"Only {len(scene_files)} scenes generated, using fallback")

    # ── video-factory fallback ──
    if not video_path:
        vf_result = run_demo(demo_name)
        if vf_result["status"] == "ok":
            video_path = vf_result.get("final_video", "")
            output_dir = vf_result.get("output_dir", output_dir)
            manifest_path = vf_result.get("manifest_path", "")
            messages.append(vf_result["message"])
        else:
            messages.append(f"video-factory: {vf_result['message']}")

    # ── CogVideo (sync/async modes) ─────────────────────────
    if req.enable_cogvideo:
        prompt = req.cogvideo_prompt or f"电商产品种草视频：{demo_name}"
        mode = (getattr(req, "cogvideo_mode", "auto") or "auto").lower()
        cogvideo_task_id = ""
        cogvideo_video_url = ""
        cogvideo_local_path = ""
        if mode == "async":
            asyncio.create_task(_cogvideo_bg(prompt, output_dir, job_id))
            messages.append("CogVideo started in background (async mode)")
        else:
            # mode == 'sync' or 'auto' => try synchronous generation first
            try:
                result = await cogvideo_generate_clip(
                    prompt=prompt,
                    image_url=product_images[0] if product_images else None,
                    duration=total_duration,
                    output_dir=output_dir,
                )
                cogvideo_task_id = result.get("task_id", "")
                cogvideo_video_url = result.get("video_url", "")
                cogvideo_local_path = result.get("local_path", "")
                if result.get("status") == "ok" and (cogvideo_local_path or cogvideo_video_url):
                    video_path = cogvideo_local_path or cogvideo_video_url or video_path
                    messages.append("CogVideo produced video synchronously")
                else:
                    if mode == "auto":
                        asyncio.create_task(_cogvideo_bg(prompt, output_dir, job_id))
                        messages.append("CogVideo started in background (async fallback)")
                    else:
                        # sync mode requested but failed -> still spawn background task to attempt completion
                        asyncio.create_task(_cogvideo_bg(prompt, output_dir, job_id))
                        messages.append("CogVideo sync failed; started background retry")
            except Exception as e:
                logger.exception("CogVideo sync failed: %s", e)
                asyncio.create_task(_cogvideo_bg(prompt, output_dir, job_id))
                messages.append("CogVideo started in background after exception")

    now = utc_now_iso()
    job = RenderJobRecord(
        job_id=job_id,
        status="ok" if messages else status,
        demo_name=demo_name,
        manifest_path=manifest_path,
        video_path=video_path,
        output_dir=output_dir,
        c4d_scene2_output="",
        cogvideo_task_id="",
        cogvideo_video_url="",
        cogvideo_local_path="",
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
