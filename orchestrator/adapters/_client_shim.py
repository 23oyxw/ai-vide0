from __future__ import annotations

"""Lightweight HTTPX AsyncClient shim that injects Authorization header when missing.
This avoids editing many adapter files here; prefer to permanently migrate adapters to use a shared client.
"""

import httpx
from orchestrator.config import settings


class _ShimAsyncClient(httpx.AsyncClient):
    async def request(self, method, url, *args, **kwargs):
        headers = kwargs.get("headers") or {}
        # ensure mutable dict
        headers = dict(headers)
        # If calling Zhipu / CogVideo endpoints and no Authorization provided, inject Bearer token
        try:
            api_key = (settings.zhipu_api_key or "").strip()
        except Exception:
            api_key = ""
        if api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {api_key}"
        kwargs["headers"] = headers
        return await super().request(method, url, *args, **kwargs)


# Monkeypatch httpx.AsyncClient globally in this process. Short-lived shim; prefer explicit headers in production code.
httpx.AsyncClient = _ShimAsyncClient
