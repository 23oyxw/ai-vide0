import { jsonResponse, type ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

type RouteContext = { params: Promise<{ job_id: string }> };

export async function GET(_req: Request, ctx: RouteContext) {
  const { job_id } = await ctx.params;
  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/pipeline/status/${job_id}`);
    const data = (await res.json()) as ApiEnvelope;
    return jsonResponse(data, res.status);
  } catch (err) {
    const envelope: ApiEnvelope = {
      ok: false, data: null,
      error: { code: "proxy_error", message: "后端服务未响应，请确认 npm run dev:api 已启动", detail: String(err) },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 502);
  }
}
