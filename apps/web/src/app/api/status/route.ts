const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

export async function GET() {
  const aiGatewayConfigured = Boolean(process.env.AI_GATEWAY_API_KEY);

  let orchestrator: {
    reachable: boolean;
    status?: string;
    error?: string;
  } = { reachable: false };

  try {
    const res = await fetch(`${ORCHESTRATOR_URL}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = (await res.json()) as { status?: string };
      orchestrator = { reachable: true, status: data.status ?? "ok" };
    } else {
      orchestrator = {
        reachable: false,
        error: `HTTP ${res.status}`,
      };
    }
  } catch (err) {
    orchestrator = {
      reachable: false,
      error: err instanceof Error ? err.message : "unreachable",
    };
  }

  return Response.json({
    aiGatewayConfigured,
    orchestratorUrl: ORCHESTRATOR_URL,
    orchestrator,
    timestamp: new Date().toISOString(),
  });
}
