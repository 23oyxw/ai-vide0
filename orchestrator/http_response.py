from __future__ import annotations

import json
from typing import Any

from starlette.responses import JSONResponse


class UTF8JSONResponse(JSONResponse):
    """JSON with UTF-8 body and ensure_ascii=False for Chinese text."""

    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")
