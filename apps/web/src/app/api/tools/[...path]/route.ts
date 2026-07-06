import { jsonResponse, type ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(req: Request, pathSegments: string[]) {
  const subPath = pathSegments.join("/");
  const url = new URL(req.url);
  const target = `${ORCHESTRATOR_URL}/tools/${subPath}${url.search}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  const res = await fetch(target, init);
  const data = (await res.json()) as ApiEnvelope;
  return jsonResponse(data, res.status);
}

export async function GET(req: Request, ctx: RouteContext) {
  try {
    const { path } = await ctx.params;
    return proxy(req, path);
  } catch (err) {
    const envelope: ApiEnvelope = {
      ok: false, data: null,
      error: { code: "proxy_error", message: "后端服务未响应，请确认 npm run dev:api 已启动", detail: String(err) },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 502);
  }
}

export async function POST(req: Request, ctx: RouteContext) {
  try {
    const { path } = await ctx.params;
    return proxy(req, path);
  } catch (err) {
    const envelope: ApiEnvelope = {
      ok: false, data: null,
      error: { code: "proxy_error", message: "后端服务未响应，请确认 npm run dev:api 已启动", detail: String(err) },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
    return jsonResponse(envelope, 502);
  }
}
