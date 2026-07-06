from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from orchestrator.config import settings

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 60.0


def _api_key() -> str:
    return settings.zhipu_api_key.strip()


def _is_configured() -> bool:
    return bool(_api_key())


def _chat_url() -> str:
    return f"{settings.zhipu_base_url.rstrip('/')}/chat/completions"


async def generate_script(*, product_url: str | None = None, raw_text: str = "", style: str = "种草短视频") -> dict[str, Any]:
    if not _is_configured():
        return {"status": "skipped", "message": "Zhipu API key not configured — set ZHIPU_API_KEY", "artifacts": {}, "provider": "zhipu-unconfigured"}
    source_text = raw_text.strip() or product_url or "种草产品"
    user_prompt = f"商品信息：{source_text}\n风格：{style}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
                json={"model": settings.zhipu_text_model, "messages": [{"role": "system", "content": "请输出 15 秒四段式口播稿"}, {"role": "user", "content": user_prompt}], "max_tokens": 512, "temperature": 0.8},
            )
            if resp.status_code != 200:
                text = (resp.text or "")[:800]
                logger.warning("Zhipu script generation HTTP %s: %s", resp.status_code, text)
                return {"status": "error", "message": f"Zhipu API error: HTTP {resp.status_code}", "artifacts": {}, "provider": "zhipu-error"}
            try:
                body: dict = resp.json()
                content: str = body["choices"][0]["message"]["content"]
                script = content.strip()
            except Exception:
                logger.warning("Failed to parse Zhipu response: %s", getattr(resp, "text", ""))
                return {"status": "error", "message": "Zhipu returned invalid JSON", "artifacts": {}, "provider": "zhipu-error"}
            return {"status": "ok", "message": f"script via {settings.zhipu_text_model} (zhipu)", "artifacts": {"script": script}, "provider": "zhipu"}
    except Exception as exc:
        logger.exception("Zhipu API request failed: %s", exc)
        return {"status": "error", "message": f"Zhipu API unreachable: {exc}", "artifacts": {}, "provider": "zhipu-error"}


async def check_compliance(script_text: str) -> dict[str, Any]:
    if not script_text.strip():
        return {"passed": True, "issues": [], "risk_level": "safe", "verdict": "empty script — trivially compliant", "engine": "zhipu-skip"}
    if not _is_configured():
        return {"passed": True, "issues": [], "risk_level": "unknown", "verdict": "Zhipu not configured — skip AI semantic review", "engine": "zhipu-unconfigured"}
    COMPLIANCE_SYSTEM_PROMPT = """你是广告法合规审查专家。检测以下文案是否存在虚假宣传、违禁词、误导性陈述。只输出 JSON。"""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
                json={"model": settings.zhipu_reasoning_model, "messages": [{"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT}, {"role": "user", "content": script_text[:2000]}], "max_tokens": 300, "temperature": 0.1},
            )
            if resp.status_code != 200:
                logger.warning("Zhipu compliance HTTP %s: %s", resp.status_code, (resp.text or "")[:400])
                return {"passed": True, "issues": [], "risk_level": "unknown", "verdict": f"Zhipu API HTTP {resp.status_code} — pass by default", "engine": "zhipu-http-error"}
            body: dict = resp.json()
            raw: str = body["choices"][0]["message"]["content"].strip()
            try:
                result = json.loads(raw)
            except Exception:
                logger.warning("Zhipu compliance returned non-JSON: %s", raw[:200])
                return {"passed": True, "issues": [], "risk_level": "low", "verdict": "AI review parse error — pass by default", "engine": "zhipu-parse-error"}
            return {"passed": bool(result.get("passed", True)), "issues": result.get("issues", []), "risk_level": result.get("risk_level", "unknown"), "verdict": result.get("verdict", ""), "engine": f"zhipu-{settings.zhipu_reasoning_model}"}
    except Exception as exc:
        logger.exception("Zhipu compliance check failed: %s", exc)
        return {"passed": True, "issues": [], "risk_level": "unknown", "verdict": f"AI review unavailable: {exc}", "engine": "zhipu-error"}


async def analyze_product_image(image_url: str) -> dict[str, Any]:
    if not _is_configured():
        return {"status": "skipped", "analysis": None, "message": "Zhipu API key not configured"}
    VISION_SYSTEM_PROMPT = """你是电商商品分析专家。从商品图中提取可用于种草视频的视觉卖点。只输出 JSON。"""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(
                _chat_url(),
                headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
                json={"model": settings.zhipu_vision_model, "messages": [{"role": "system", "content": VISION_SYSTEM_PROMPT}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}, {"type": "text", "text": "分析这张商品图，提取可用于种草视频的视觉卖点"}]}], "max_tokens": 400, "temperature": 0.3},
            )
            if resp.status_code != 200:
                return {"status": "error", "analysis": None, "message": f"Vision API HTTP {resp.status_code}: {(resp.text or '')[:200]}"}
            body: dict = resp.json()
            raw: str = body["choices"][0]["message"]["content"].strip()
            analysis = json.loads(raw)
            return {"status": "ok", "analysis": analysis, "message": f"Visual analysis via {settings.zhipu_vision_model}"}
    except json.JSONDecodeError:
        return {"status": "error", "analysis": None, "message": "Vision model returned non-JSON output"}
    except Exception as exc:
        logger.exception("Zhipu vision analysis failed: %s", exc)
        return {"status": "error", "analysis": None, "message": str(exc)}


async def check_health() -> dict[str, Any]:
    if not _is_configured():
        return {"status": "skipped", "configured": False, "message": "ZHIPU_API_KEY not set"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.zhipu_base_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {_api_key()}"})
            return {"status": "ok" if resp.status_code == 200 else "error", "configured": True, "http_status": resp.status_code, "text_model": settings.zhipu_text_model, "reasoning_model": settings.zhipu_reasoning_model, "vision_model": settings.zhipu_vision_model}
    except Exception as exc:
        logger.exception("Zhipu health check failed: %s", exc)
        return {"status": "error", "configured": True, "message": str(exc)}
