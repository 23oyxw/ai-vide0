from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class CrawlerLayer(BaseLayer):
    layer_id = "L1"
    name = "crawler"
    description = "Product/competitor crawl - httpx + metadata extraction"

    async def run(self, ctx: LayerContext) -> LayerResult:
        url = ctx.product_url or "https://example.com/product"
        domain = urlparse(url).netloc or "unknown"

        title = ""
        desc = ""
        image = ""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                            " AppleWebKit/537.36 (KHTML, like Gecko)"
                            " Chrome/125.0.0.0 Safari/537.36"
                        ),
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    },
                )
                html = resp.text[:50000]
                title = _extract_meta(html, "og:title", "title")
                desc = _extract_meta(html, "og:description", "description")
                image = _extract_meta(html, "og:image", "")
        except Exception as exc:
            ctx.errors.append(f"crawl error: {exc}")

        ctx.artifacts["crawled_url"] = url
        ctx.artifacts["crawled_domain"] = domain
        ctx.artifacts["crawled_title"] = title
        ctx.artifacts["crawled_description"] = desc
        ctx.artifacts["crawled_image"] = image

        msg = f"crawled: {url} ({domain})"
        if title:
            msg += f" title={title[:60]}"
        else:
            msg += " no og metadata"

        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=msg,
            artifacts={
                "crawled_url": url,
                "crawled_domain": domain,
                "crawled_title": title,
                "crawled_description": desc,
                "crawled_image": image,
            },
        )


def _extract_meta(html: str, og_prop: str, fallback_tag: str) -> str:
    prop_match = re.search(
        rf'<meta\s[^>]*property=["\x27]{og_prop}["\x27][^>]*content=["\x27]([^"\x27]+)',
        html,
        re.IGNORECASE,
    )
    if prop_match:
        return prop_match.group(1)
    name_match = re.search(
        rf'<meta\s[^>]*name=["\x27]{og_prop}["\x27][^>]*content=["\x27]([^"\x27]+)',
        html,
        re.IGNORECASE,
    )
    if name_match:
        return name_match.group(1)
    if fallback_tag:
        tag_match = re.search(
            rf"<{fallback_tag}[^>]*>(.*?)</{fallback_tag}>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if tag_match:
            return re.sub(r"<[^>]+>", "", tag_match.group(1)).strip()[:500]
    return ""
