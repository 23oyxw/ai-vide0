/** Unified orchestrator response envelope (matches FastAPI ApiEnvelope). */
export type ApiEnvelope<T = unknown> = {
  ok: boolean;
  data: T | null;
  error: { code: string; message: string; detail?: unknown } | null;
  meta: { layer?: string | null; job_id?: string | null; timestamp: string };
};

export function unwrapEnvelope<T>(body: ApiEnvelope<T>): T {
  if (!body.ok || body.data == null) {
    const msg = body.error?.message ?? "Upstream request failed";
    throw new Error(msg);
  }
  return body.data;
}

/** UTF-8 JSON for Chinese text in API responses. */
export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
