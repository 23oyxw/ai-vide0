from __future__ import annotations

import base64

import httpx

from orchestrator.adapters.ai_koubo import generate_script as koubo_generate
from orchestrator.config import settings
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l2_content.models import (
    GenerateProductImageRequest,
    GenerateProductImageResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    OptimizePromptsRequest,
    OptimizePromptsResponse,
    ProductImageVariant,
    ScriptGetResponse,
    ScriptRecord,
    ScriptSegment,
)
from orchestrator.rag.context import fetch_rag_context

SCRIPTS_DIR = module_dir("l2", "scripts")

SEGMENT_TEMPLATE = [
    ("hook", "前3秒钩子", 0.0, 3.0),
    ("pain", "痛点展开", 3.0, 7.0),
    ("product", "产品特写", 7.0, 12.0),
    ("cta", "行动号召", 12.0, 15.0),
]


def _split_into_segments(full_text: str) -> list[ScriptSegment]:
    sentences = [s.strip() for s in full_text.replace("\n", "。").split("。") if s.strip()]
    if len(sentences) < 4:
        sentences.extend([""] * (4 - len(sentences)))
    segments: list[ScriptSegment] = []
    for idx, (code, role, start, end) in enumerate(SEGMENT_TEMPLATE):
        narration = sentences[idx] if idx < len(sentences) else f"[{role}]"
        segments.append(
            ScriptSegment(
                code=code,
                role=role,
                start_sec=start,
                end_sec=end,
                duration_sec=end - start,
                narration=narration[:120],
            )
        )
    return segments


async def _deepseek_rewrite(text: str, style: str) -> str | None:
    api_key = settings.deepseek_api_key
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"你是短视频种草文案师，输出15秒口播，4段结构，风格：{style}。",
                        },
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": 512,
                },
            )
            resp.raise_for_status()
            resp.encoding = "utf-8"
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content.strip()
    except Exception:
        return None


async def generate_script_record(req: GenerateScriptRequest) -> GenerateScriptResponse:
    provider = "stub"
    source = req.raw_text.strip() or req.topic.strip()

    # ── Provider chain: Zhipu (free) → DeepSeek → ai-koubo → local-template ──
    full_text = ""

    # 1. Zhipu GLM-4-Flash (free, best Chinese)
    from orchestrator.adapters.zhipu import generate_script as zhipu_generate
    zhipu = await zhipu_generate(
        product_url=req.product_url,
        raw_text=source,
        style=req.style,
    )
    if zhipu.get("status") == "ok" and zhipu.get("artifacts", {}).get("script"):
        full_text = zhipu["artifacts"]["script"]
        provider = "zhipu"

    # 2. ai-koubo (DeepSeek via existing adapter)
    if not full_text:
        koubo = await koubo_generate(
            product_url=req.product_url,
            raw_text=source,
            style=req.style,
        )
        full_text = koubo.get("artifacts", {}).get("script", "")
        provider = koubo.get("provider") or ("ai-koubo" if koubo["status"] == "ok" else "stub")

    # 3. DeepSeek direct
    if not full_text or "[stub]" in full_text:
        deepseek = await _deepseek_rewrite(source or req.product_url or "种草产品", req.style)
        if deepseek:
            full_text = deepseek
            provider = "deepseek"

    # 4. Local template (ultimate fallback)
    if not full_text:
        seed = req.topic or req.product_url or "好物推荐"
        full_text = (
            f"还在纠结选什么？{seed}真的值得入手。"
            f"痛点一目了然，性价比拉满。"
            f"实拍上手，质感在线。"
            f"链接在评论区，限时福利别错过。"
        )
        provider = "local-template"

    script_id = new_id("s")
    record = ScriptRecord(
        id=script_id,
        full_text=full_text,
        segments=_split_into_segments(full_text),
        duration_sec=15.0,
        provider=provider,
        product_url=req.product_url,
        created_at=utc_now_iso(),
    )
    save_json(SCRIPTS_DIR / f"{script_id}.json", record.model_dump())
    return GenerateScriptResponse(script=record)


def get_script(script_id: str) -> ScriptGetResponse | None:
    data = load_json(SCRIPTS_DIR / f"{script_id}.json")
    if not data:
        return None
    return ScriptGetResponse(script=ScriptRecord.model_validate(data))


async def optimize_prompts(req: OptimizePromptsRequest) -> OptimizePromptsResponse:
    """RAG + 模板生成选题/脚本大纲，供 L2 管线使用。"""
    title = req.product_title.strip() or req.topic.split("·")[0].strip() or "好物"
    category = req.category.strip() or "电商种草"
    pains = req.pain_points[:3] if req.pain_points else ["性价比", "是否适合肤质/场景", "和竞品差异"]
    platform = req.platform.strip() or "抖音/小红书"

    rag_q = f"{category} {title} 种草视频 开场钩子 痛点 CTA"
    rag_ctx = fetch_rag_context(rag_q, max_chars=600)
    rag_lines = [ln.strip() for ln in rag_ctx.split("\n") if ln.strip()][:4]

    hook_pool = [
        f"还在纠结{category}怎么选？先看这 3 点",
        f"为什么{title}最近刷屏？",
        f"同价位里，{title}到底值不值？",
        "别划走，15 秒讲清楚要不要下单",
    ]
    if rag_lines:
        hook_pool.insert(0, rag_lines[0][:48])

    optimized_topic = (
        f"【{platform}】{title} · {category}\n"
        f"目标人群：关注{pains[0]}的用户\n"
        f"核心卖点：{title} + {category}场景实测\n"
        f"内容形式：15 秒四段式种草（钩子→痛点→特写→CTA）"
    )

    optimized_script = (
        f"1. 钩子（0-3s）：{hook_pool[0]}\n"
        f"2. 痛点（3-7s）：{pains[0]}、{pains[1] if len(pains) > 1 else '使用门槛'}怎么解决\n"
        f"3. 产品特写（7-12s）：{title} 上手展示 + 关键参数/质地/对比\n"
        f"4. CTA（12-15s）：评论区链接 / 限时券 / 适合人群一句话"
    )
    if rag_ctx:
        optimized_script += f"\n\n[RAG 参考]\n{rag_ctx[:400]}"

    provider = "rag-template"
    if settings.deepseek_api_key:
        refine = await _deepseek_rewrite(
            f"商品：{title}\n类目：{category}\n痛点：{', '.join(pains)}\n"
            f"请输出：1行选题方向 + 4行15秒口播大纲（钩子/痛点/特写/CTA）",
            "种草短视频提示词优化",
        )
        if refine:
            parts = [p.strip() for p in refine.split("\n") if p.strip()]
            if parts:
                optimized_topic = parts[0][:500]
            if len(parts) > 1:
                optimized_script = "\n".join(parts[1:6])
            provider = "deepseek"

    next_steps = [
        "① 确认上方「选题方向」与「脚本大纲」",
        "② 点击「运行管线」执行 L1→L8（约 1–3 分钟）",
        "③ 完成后切到「后台 API」Tab 查看 L8 指标",
    ]
    if not req.product_url.strip():
        next_steps.insert(0, "⚠ 请先填写商品链接并点击「L1 抓取」")

    return OptimizePromptsResponse(
        optimized_topic=optimized_topic,
        optimized_script=optimized_script,
        hook_suggestions=hook_pool[:4],
        rag_snippets=rag_lines,
        next_steps=next_steps,
        provider=provider,
    )


async def generate_product_images(req: GenerateProductImageRequest) -> GenerateProductImageResponse:
    """Generate product images via Zhipu CogView-4, falling back to SVG placeholders."""
    title = req.product_title.strip() or "商品"
    category = req.category.strip() or "电商"
    types = req.image_types[:3] if req.image_types else ["白底主图", "场景氛围图", "卖点特写图"]

    palettes = {
        "白底主图": ("#E8F5E9", "#2E7D32", "📷"),
        "场景氛围图": ("#E3F2FD", "#1565C0", "🌟"),
        "卖点特写图": ("#FFF3E0", "#E65100", "✨"),
    }

    ref_url = req.reference_image_url.strip()

    async def _try_generate(prompt: str) -> str | None:
        from orchestrator.adapters.zhipu import generate_image
        result = await generate_image(prompt, reference_image_url=ref_url if ref_url else "")
        return result.get("url") if result.get("status") == "ok" else None

    product_id = f"单个{category}产品「{title}」，仅此一件"
    negatives = (
        "不要多件商品，不要拼图，不要模特露脸，"
        "不要文字水印，不要LOGO，不要包装盒，不要杂乱的背景"
    )
    style_prompts = {
        "白底主图": (
            f"{product_id}，纯白色背景#FFFFFF，正面平视角度，"
            f"均匀柔光无阴影，产品占画面80%，电商平台主图规范，"
            f"高清专业产品摄影，{negatives}"
        ),
        "场景氛围图": (
            f"{product_id}，简约北欧风格桌面场景，"
            f"自然窗光侧逆光，浅景深背景虚化，产品在画面中央，"
            f"搭配同色系道具点缀但不抢眼，生活方式商业摄影，{negatives}"
        ),
        "卖点特写图": (
            f"{product_id}，微距镜头拍摄产品局部核心材质与细节，"
            f"极浅景深f/1.8效果，展示纹理/质感/做工，"
            f"无手指无工具仅产品本身，高端商业细节摄影，{negatives}"
        ),
    }

    images: list[ProductImageVariant] = []
    provider = "stub"

    for idx, img_type in enumerate(types):
        prompt = style_prompts.get(img_type, f"{product_id}，{img_type}，专业产品摄影，{negatives}")

        # Generate with reference image if provided (image-guided for consistency)
        image_url = await _try_generate(prompt)
        if image_url:
            provider = "cogview-4"
            images.append(ProductImageVariant(type=img_type, url=image_url, prompt=prompt))
            continue

        # Fallback: vibrant SVG placeholder
        bg, accent, icon = palettes.get(img_type, ("#F3E5F5", "#7B1FA2", "🛍️"))
        name = title[:16]
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">'
            f'<rect width="512" height="512" fill="{bg}" rx="12"/>'
            f'<rect x="16" y="16" width="480" height="480" fill="none" stroke="{accent}" stroke-width="2" rx="8" stroke-dasharray="8,4"/>'
            f'<text x="256" y="180" text-anchor="middle" font-size="64" fill="{accent}" opacity="0.6">{icon}</text>'
            f'<text x="256" y="280" text-anchor="middle" font-size="28" fill="{accent}" font-weight="bold" font-family="sans-serif">'
            f'{name}</text>'
            f'<text x="256" y="330" text-anchor="middle" font-size="18" fill="{accent}" opacity="0.8" font-family="sans-serif">'
            f'{img_type}</text>'
            f'<text x="256" y="410" text-anchor="middle" font-size="14" fill="{accent}" opacity="0.5" font-family="sans-serif">'
            f'AI 预览 · {category}</text>'
            f'<rect x="156" y="430" width="200" height="32" rx="16" fill="{accent}" opacity="0.15"/>'
            f'<text x="256" y="452" text-anchor="middle" font-size="13" fill="{accent}" font-family="sans-serif">AI 生成中</text>'
            f'</svg>'
        )
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        images.append(ProductImageVariant(type=img_type, url=f"data:image/svg+xml;base64,{encoded}", prompt=prompt))

    return GenerateProductImageResponse(
        images=images,
        provider=provider,
        product_title=title,
        category=category,
    )
