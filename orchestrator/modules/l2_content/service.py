from __future__ import annotations

import os

import httpx

from orchestrator.adapters.ai_koubo import generate_script as koubo_generate
from orchestrator.modules.common import load_json, module_dir, new_id, save_json, utc_now_iso
from orchestrator.modules.l2_content.models import (
    GenerateScriptRequest,
    GenerateScriptResponse,
    ScriptGetResponse,
    ScriptRecord,
    ScriptSegment,
)

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
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
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
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def generate_script_record(req: GenerateScriptRequest) -> GenerateScriptResponse:
    provider = "stub"
    source = req.raw_text.strip() or req.topic.strip()

    koubo = await koubo_generate(
        product_url=req.product_url,
        raw_text=source,
        style=req.style,
    )
    full_text = koubo.get("artifacts", {}).get("script", "")
    provider = koubo.get("provider") or ("ai-koubo" if koubo["status"] == "ok" else "stub")

    if not full_text or "[stub]" in full_text:
        deepseek = await _deepseek_rewrite(source or req.product_url or "种草产品", req.style)
        if deepseek:
            full_text = deepseek
            provider = "deepseek"
        elif not full_text:
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
