export const maxDuration = 60;

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

    const data = await upstream.json();
    return Response.json(data, { status: upstream.status });
  } catch {
    return Response.json(
      {
        stub: true,
        message:
          "Orchestrator unreachable. Start: uvicorn orchestrator.main:app --port 8765",
        orchestrator_url: ORCHESTRATOR_URL,
      },
      { status: 503 },
    );
  }
}
