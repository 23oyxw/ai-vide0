import type { ApiEnvelope } from "@/lib/api-envelope";

const ORCHESTRATOR_URL =
  process.env.ORCHESTRATOR_URL ?? "http://127.0.0.1:8765";

type HealthData = { status?: string };

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
      const envelope = (await res.json()) as ApiEnvelope<HealthData>;
      const status = envelope.ok ? (envelope.data?.status ?? "ok") : "error";
      orchestrator = { reachable: envelope.ok, status };
      if (!envelope.ok) {
        orchestrator.error = envelope.error?.message ?? "health check failed";
      }
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

  const envelope: ApiEnvelope<{
    aiGatewayConfigured: boolean;
    orchestratorUrl: string;
    orchestrator: typeof orchestrator;
  }> = {
    ok: true,
    data: {
      aiGatewayConfigured,
      orchestratorUrl: ORCHESTRATOR_URL,
      orchestrator,
    },
    error: null,
    meta: { layer: "L0", timestamp: new Date().toISOString() },
  };

  return Response.json(envelope);
}
