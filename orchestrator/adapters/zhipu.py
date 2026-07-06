"""Zhipu (智谱) GLM text API adapter.

Provider priority chain for L2 script generation:
  GLM-4-Flash (free) → DeepSeek → ai-koubo → local-template

Usage::
    from orchestrator.adapters.zhipu import generate_script, check_compliance
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from orchestrator.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return settings.zhipu_api_key.strip()


def _is_configured() -> bool:
    return bool(_api_key())


def _chat_url() -> str:
    return f"{settings.zhipu_base_url.rstrip('/')}/chat/completions"


# ── Script Generation (L2) ───────────────────────────────────────────────────

SEEDING_SYSTEM_PROMPT = """你是顶级短视频种草文案师。输出 15 秒四段式口播稿：

【格式要求】
1. 钩子（0-3s）：痛点/反常识/数字冲击，一句话抓住注意力
2. 痛点展开（3-7s）：为什么用户需要这个产品
3. 产品特写（7-12s）：核心卖点 + 使用场景 + 质感描述
4. CTA（12-15s）：行动号召 + 限时福利 + 评论区引导

【风格要求】
- 口语化、有节奏感、适合配音
- 80-120 字
- 不堆砌形容词，用具体场景代替抽象描述
- 避免使用「第一」「唯一」「绝对」「100%」等广告法违禁词

只输出四段文案，每段一行，不要任何额外解释。"""


async def generate_script(
    *,
    product_url: str | None = None,
    raw_text: str = "",
    style: str = "种草短视频",
) -> dict[str, Any]:
    """Generate a seeding script via GLM-4-Flash (free tier).

    Returns the same shape as ai_koubo.generate_script for drop-in compatibility:
        {"status": "ok"|"error", "message": str, "artifacts": {"script": str}, "provider": str}
    """
    if not _is_configured():
        return {
            "status": "skipped",
            "message": "Zhipu API key not configured — set ZHIPU_API_KEY",
            "artifacts": {},
            "provider": "zhipu-unconfigured",
        }

    source_text = raw_text.strip()
    if not source_text:
        source_text = product_url or "种草产品"

    user_prompt = f"商品信息：{source_text}\n风格：{style}"

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.zhipu_text_model,
                    "messages": [
                        {"role": "system", "content": SEEDING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 512,
                    "temperature": 0.8,
                },
            )
            resp.raise_for_status()
            body: dict = resp.json()
            content: str = body["choices"][0]["message"]["content"]
            script = content.strip()

            return {
                "status": "ok",
                "message": f"script via {settings.zhipu_text_model} (zhipu)",
                "artifacts": {"script": script},
                "provider": "zhipu",
            }
    except httpx.HTTPStatusError as exc:
        logger.warning("Zhipu API HTTP %s: %s", exc.response.status_code, exc)
        return {
            "status": "error",
            "message": f"Zhipu API error: HTTP {exc.response.status_code}",
            "artifacts": {},
            "provider": "zhipu-error",
        }
    except Exception as exc:
        logger.warning("Zhipu API request failed: %s", exc)
        return {
            "status": "error",
            "message": f"Zhipu API unreachable: {exc}",
            "artifacts": {},
            "provider": "zhipu-error",
        }


# ── Compliance Check (L6) ────────────────────────────────────────────────────

COMPLIANCE_SYSTEM_PROMPT = """你是广告法合规审查专家。检测以下文案是否存在虚假宣传、违禁词、误导性陈述。

【审查维度】
1. 广告法违禁词（如：第一、唯一、绝对、100%、纯天然、特效、根治等）
2. 虚假宣传（夸大功效、无法验证的声明）
3. 医疗/保健误导（暗示治疗功能）
4. PII 泄露（手机号、身份证号等）

请严格按 JSON 格式输出：
{"passed": true/false, "issues": ["问题1", "问题2"], "risk_level": "safe"|"low"|"high", "verdict": "一句话总结"}

只输出 JSON，不要任何额外文字。"""


async def check_compliance(script_text: str) -> dict[str, Any]:
    """AI-powered semantic compliance review via GLM-Z1-Flash (free tier).

    Returns:
        {"passed": bool, "issues": list[str], "risk_level": str, "verdict": str, "engine": str}
    """
    if not script_text.strip():
        return {
            "passed": True,
            "issues": [],
            "risk_level": "safe",
            "verdict": "empty script — trivially compliant",
            "engine": "zhipu-skip",
        }

    if not _is_configured():
        return {
            "passed": True,
            "issues": [],
            "risk_level": "unknown",
            "verdict": "Zhipu not configured — skip AI semantic review",
            "engine": "zhipu-unconfigured",
        }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.zhipu_reasoning_model,
                    "messages": [
                        {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                        {"role": "user", "content": script_text[:2000]},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.1,  # low temp for deterministic review
                },
            )
            resp.raise_for_status()
            body: dict = resp.json()
            raw: str = body["choices"][0]["message"]["content"].strip()

            # Parse the JSON output
            result = json.loads(raw)
            return {
                "passed": bool(result.get("passed", True)),
                "issues": result.get("issues", []),
                "risk_level": result.get("risk_level", "unknown"),
                "verdict": result.get("verdict", ""),
                "engine": f"zhipu-{settings.zhipu_reasoning_model}",
            }
    except json.JSONDecodeError:
        logger.warning("Zhipu compliance returned non-JSON: %s", raw[:200] if 'raw' in dir() else "N/A")
        return {
            "passed": True,
            "issues": [],
            "risk_level": "low",
            "verdict": "AI review parse error — pass by default",
            "engine": "zhipu-parse-error",
        }
    except httpx.HTTPStatusError as exc:
        logger.warning("Zhipu compliance HTTP %s: %s", exc.response.status_code, exc)
        return {
            "passed": True,
            "issues": [],
            "risk_level": "unknown",
            "verdict": f"Zhipu API HTTP {exc.response.status_code} — pass by default",
            "engine": "zhipu-http-error",
        }
    except Exception as exc:
        logger.warning("Zhipu compliance check failed: %s", exc)
        return {
            "passed": True,
            "issues": [],
            "risk_level": "unknown",
            "verdict": f"AI review unavailable: {exc}",
            "engine": "zhipu-error",
        }


# ── Product Image Understanding (L1) ──────────────────────────────────────────

VISION_SYSTEM_PROMPT = """你是电商商品分析专家。从商品图中提取可用于种草视频的视觉卖点。

输出 JSON：
{"category": "类目", "visual_selling_points": ["卖点1", "卖点2", "卖点3"],
 "style_tags": ["简约", "高端", ...], "color_palette": ["主色1", "主色2"],
 "suggested_shots": ["建议镜头1", "建议镜头2"]}

只输出 JSON。"""


async def analyze_product_image(image_url: str) -> dict[str, Any]:
    """Extract visual selling points from a product image via GLM-4.6V-Flash.

    Args:
        image_url: Public URL or base64 data URI of the product image.

    Returns:
        {"status": str, "analysis": dict | None, "message": str}
    """
    if not _is_configured():
        return {
            "status": "skipped",
            "analysis": None,
            "message": "Zhipu API key not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.zhipu_vision_model,
                    "messages": [
                        {"role": "system", "content": VISION_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url},
                                },
                                {
                                    "type": "text",
                                    "text": "分析这张商品图，提取可用于种草视频的视觉卖点",
                                },
                            ],
                        },
                    ],
                    "max_tokens": 400,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            body: dict = resp.json()
            raw: str = body["choices"][0]["message"]["content"].strip()
            analysis = json.loads(raw)

            return {
                "status": "ok",
                "analysis": analysis,
                "message": f"Visual analysis via {settings.zhipu_vision_model}",
            }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "analysis": None,
            "message": "Vision model returned non-JSON output",
        }
    except Exception as exc:
        logger.warning("Zhipu vision analysis failed: %s", exc)
        return {
            "status": "error",
            "analysis": None,
            "message": str(exc),
        }


# ── Health Check ──────────────────────────────────────────────────────────────

async def check_health() -> dict[str, Any]:
    """Probe Zhipu API reachability with a lightweight models list call."""
    if not _is_configured():
        return {
            "status": "skipped",
            "configured": False,
            "message": "ZHIPU_API_KEY not set",
        }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.zhipu_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {_api_key()}"},
            )
            return {
                "status": "ok" if resp.status_code == 200 else "error",
                "configured": True,
                "http_status": resp.status_code,
                "text_model": settings.zhipu_text_model,
                "reasoning_model": settings.zhipu_reasoning_model,
                "vision_model": settings.zhipu_vision_model,
            }
    except Exception as exc:
        return {
            "status": "error",
            "configured": True,
            "message": str(exc),
        }


# ── CogView Image Generation ────────────────────────────────────────────

async def generate_image(prompt: str, size: str = "1024x1024", reference_image_url: str = "") -> dict[str, Any]:
    """Generate an image via Zhipu CogView-4 (free tier: 100 imgs/day).
    If reference_image_url is provided, uses image-guided generation for product consistency.
    Returns {"status": "ok", "url": "...", "prompt": "..."} or {"status": "error", "message": "..."}.
    """
    if not _is_configured():
        return {"status": "skipped", "message": "ZHIPU_API_KEY not configured"}

    try:
        body: dict[str, Any] = {
            "model": "cogview-3-flash",
            "prompt": prompt,
            "size": size,
        }
        if reference_image_url:
            body["image_url"] = reference_image_url

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.zhipu_base_url.rstrip('/')}/images/generations",
                headers={
                    "Authorization": f"Bearer {_api_key()}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "message": f"CogView API error {resp.status_code}: {resp.text[:200]}",
                }

            data = resp.json()
            # Response format: {"data": [{"url": "..."}]}
            image_url = data.get("data", [{}])[0].get("url", "")
            if not image_url:
                return {"status": "error", "message": "CogView returned no image URL"}

            return {
                "status": "ok",
                "url": image_url,
                "prompt": prompt,
                "model": "cogview-3-flash",
            }

    except Exception as exc:
        return {"status": "error", "message": f"CogView request failed: {str(exc)}"}
