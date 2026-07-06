import { jsonResponse, type ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

export async function POST(req: Request) {
  try {
    const body = await req.text();
    const res = await fetch(`${ORCHESTRATOR_URL}/agent/crawler`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body,
    });
    const data = (await res.json()) as ApiEnvelope;
    return jsonResponse(data, res.status);
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        data: null,
        error: { code: "proxy_error", message: "后端服务未响应，请确认 npm run dev:api 已启动", detail: String(err) },
        meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
      },
      502,
    );
  }
}
