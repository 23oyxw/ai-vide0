const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

type RouteContext = { params: Promise<{ job_id: string }> };

export async function GET(_req: Request, ctx: RouteContext) {
  const { job_id } = await ctx.params;
  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/video/${job_id}`, {
      signal: AbortSignal.timeout(30_000),
    });
    if (!res.ok) return new Response(null, { status: res.status });
    // Stream-through — don't buffer the entire video
    return new Response(res.body, {
      status: 200,
      headers: {
        "Content-Type": res.headers.get("Content-Type") ?? "video/mp4",
        "Content-Length": res.headers.get("Content-Length") ?? "",
        "Cache-Control": "public, max-age=3600",
        "Accept-Ranges": "bytes",
      },
    });
  } catch {
    return new Response(null, { status: 502 });
  }
}
