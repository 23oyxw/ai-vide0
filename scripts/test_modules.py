"""Quick module endpoint smoke test."""
from __future__ import annotations
import asyncio
import httpx
BASE = "http://127.0.0.1:8765"

async def main() -> int:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{BASE}/modules/l1-crawler/search", json={"keyword": "防晒", "vertical": "电商", "product_url": "https://example.com/p/demo"})
        r.raise_for_status()
        assert r.json()["ok"]
        script = await client.post(f"{BASE}/modules/l2-content/generate-script", json={"topic": "平价护肤", "product_url": "https://example.com/p/1"})
        script.raise_for_status()
        sid = script.json()["data"]["script"]["id"]
        assert len(script.json()["data"]["script"]["segments"]) == 4
        sb = await client.post(f"{BASE}/modules/l3-storyboard/build-from-script", json={"script_id": sid})
        sb.raise_for_status()
        sbid = sb.json()["data"]["storyboard"]["id"]
        render = await client.post(f"{BASE}/modules/l4-render/render", json={"storyboard_id": sbid})
        render.raise_for_status()
        pipeline = await client.post(f"{BASE}/pipeline/run", json={"product_url": "https://example.com/p/demo", "layers": ["L1","L2","L3","L4","L5","L6","L7","L8"]})
        pipeline.raise_for_status()
        assert len(pipeline.json()["data"]["layer_results"]) == 8
    print("all module smoke tests passed")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print("FAILED:", exc)
        raise SystemExit(1)