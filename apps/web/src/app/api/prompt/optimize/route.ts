import type { ApiEnvelope } from "@/lib/api-envelope";
import { jsonResponse } from "@/lib/api-envelope";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

export async function POST(req: Request) {
  const body = await req.text();
  try {
    const upstream = await fetch(
      `${ORCHESTRATOR_URL}/modules/l2-content/optimize-prompts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: body || "{}",
      },
    );
    if (upstream.status === 404) {
      const envelope: ApiEnvelope = {
        ok: false,
        data: null,
        error: {
          code: "stale_orchestrator",
          message:
            "L2 优化接口 404 — :8765 上可能是旧版后台。请关闭所有 python 进程后重新 npm run dev:api",
          detail: { orchestrator_url: ORCHESTRATOR_URL },
        },
        meta: { layer: "L2", timestamp: new Date().toISOString() },
      };
      return jsonResponse(envelope, 503);
    }
    const envelope = (await upstream.json()) as ApiEnvelope;
    return jsonResponse(envelope, upstream.status);
  } catch {
    const envelope: ApiEnvelope = {
      ok: false,
      data: null,
      error: {
        code: "orchestrator_unreachable",
        message: "Orchestrator 未启动 — npm run dev:api",
      },
      meta: { layer: "L2", timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 503);
  }
}
