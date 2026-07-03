export const maxDuration = 60;

import type { ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

/**
 * Control plane (Vercel) -> orchestration plane proxy — scaffolding only.
 *
 * Flow:
 *   Dashboard POST /api/pipeline/run
 *     -> this Route Handler (apps/web on Vercel or localhost:3000)
 *     -> FastAPI POST /pipeline/run (:8765) runs L1-L8 sequentially
 *     -> L4 adapters may invoke render-plane workers (video-factory, C4D) on the
 *        machine where orchestrator runs — never inside Vercel serverless.
 *
 * Production (see docs/ARCHITECTURE_LOGIC.md):
 *   - This route should enqueue Vercel Workflow, not block on 8 layers.
 *   - Render plane completes via Worker webhook; OpenClaw is dev tooling only.
 */
export async function POST(req: Request) {
  const body = await req.text();

  try {
    const upstream = await fetch(`${ORCHESTRATOR_URL}/pipeline/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body || "{}",
    });

    const envelope = (await upstream.json()) as ApiEnvelope;
    return Response.json(envelope, { status: upstream.status });
  } catch {
    const envelope: ApiEnvelope = {
      ok: false,
      data: null,
      error: {
        code: "orchestrator_unreachable",
        message:
          "Orchestrator unreachable. Start: uvicorn orchestrator.main:app --port 8765",
        detail: { orchestrator_url: ORCHESTRATOR_URL },
      },
      meta: { layer: "L5", timestamp: new Date().toISOString() },
    };
    return Response.json(envelope, { status: 503 });
  }
}
