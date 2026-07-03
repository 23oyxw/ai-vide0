export async function GET() {
  return Response.json({
    status: "ok",
    service: "ai-video-orchestrator-web",
    timestamp: new Date().toISOString(),
  });
}
