const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

type RouteContext = { params: Promise<{ job_id: string; filename: string }> };

export async function GET(_req: Request, ctx: RouteContext) {
  const { job_id, filename } = await ctx.params;
  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/image/${job_id}/${filename}`);
    if (!res.ok) return new Response(null, { status: res.status });
    const blob = await res.blob();
    return new Response(blob, {
      headers: { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=3600" },
    });
  } catch { return new Response(null, { status: 502 }); }
}
