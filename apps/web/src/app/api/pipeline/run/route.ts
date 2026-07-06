import type { ApiEnvelope } from "@/lib/api-envelope";
import { jsonResponse } from "@/lib/api-envelope";

// Local dev: 120s timeout for pipeline with image generation
export const maxDuration = 120;

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";
const UPSTREAM_TIMEOUT_MS = 110_000;

export async function POST(req: Request) {
  const body = await req.text();
  try {
    const upstream = await fetch(`${ORCHESTRATOR_URL}/pipeline/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: body || "{}",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
    const envelope = (await upstream.json()) as ApiEnvelope;
    return jsonResponse(envelope, upstream.status);
  } catch (err) {
    const isTimeout = err instanceof Error && err.name === "TimeoutError";
    const message = isTimeout
      ? "管线超时。完整模式（含视频）约需 30 秒，请重试或改用快速模式。"
      : "Orchestrator 未启动或连接中断 — 请运行 npm run dev:api";
    const envelope: ApiEnvelope = {
      ok: false,
      data: null,
      error: {
        code: isTimeout ? "pipeline_timeout" : "orchestrator_unreachable",
        message,
        detail: { orchestrator_url: ORCHESTRATOR_URL },
      },
      meta: { layer: "L5", timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 503);
  }
}
