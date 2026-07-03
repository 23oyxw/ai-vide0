#!/usr/bin/env bash
# OpenClaw MCP registration commands (run after: pip install fastmcp)
# Adjust python path if using venv

ORCH_ROOT="C:/Users/oyxw/Projects/ai-video-orchestrator"
C4D_ROOT="C:/BKC4D"

openclaw mcp add c4d-mcp \
  --command python \
  --args "${ORCH_ROOT}/mcp/c4d-mcp/server.py" \
  --env C4D_ROOT="${C4D_ROOT}"

# Optional: register orchestrator HTTP as a fetch target
# openclaw mcp add orchestrator-api --url http://127.0.0.1:8765/docs
