import { jsonResponse, type ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const jobId = url.searchParams.get("job_id") || "";
    const params = jobId ? `?job_id=${jobId}` : "";
    const res = await fetch(`${ORCHESTRATOR_URL}/data/conversion${params}`);
    const data = (await res.json()) as ApiEnvelope;
    return jsonResponse(data, res.ok ? 200 : res.status);
  } catch (err) {
    const envelope: ApiEnvelope = {
      ok: false, data: null,
      error: { code: "proxy_error", message: "后端服务未响应，请确认 npm run dev:api 已启动", detail: String(err) },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 502);
  }
}
