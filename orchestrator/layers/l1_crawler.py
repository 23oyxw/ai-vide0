from __future__ import annotations

from orchestrator.layers.base import BaseLayer, LayerContext, LayerResult


class CrawlerLayer(BaseLayer):
    layer_id = "L1"
    name = "crawler"
    description = "Product/competitor crawl - Python + fetch MCP"

    async def run(self, ctx: LayerContext) -> LayerResult:
        url = ctx.product_url or "https://example.com/product"
        ctx.artifacts["crawled_url"] = url
        return LayerResult(
            layer_id=self.layer_id,
            status="ok",
            message=f"stub crawl: {url}",
            artifacts={"crawled_url": url},
        )
