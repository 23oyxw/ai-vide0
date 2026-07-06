/**
 * Typed API client for the FastAPI orchestrator.
 *
 * When NEXT_PUBLIC_ORCHESTRATOR_URL is set (static export / Gitee Pages),
 * calls go directly to the orchestrator (CORS required).
 * Otherwise, calls go through Next.js API routes (proxy pattern).
 */

const DIRECT_ORCHESTRATOR = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "";

/** Map a Next.js API route path to a direct orchestrator endpoint. */
function orchestratorPath(apiPath: string): string {
  // /api/crawler          → /agent/crawler
  // /api/pipeline/run     → /pipeline/run
  // /api/prompt/optimize  → /modules/l2-content/optimize-prompts
  // /api/status           → /health
  // /api/data/click        → /data/click
  // /api/modules/:path     → /modules/:path
  // /api/rag/:path         → /rag/:path
  // /api/tools/:path       → /tools/:path
  // /api/report            → /report
  const ROUTE_MAP: Record<string, string> = {
    "/api/crawler": "/agent/crawler",
    "/api/pipeline/run": "/pipeline/run",
    "/api/prompt/optimize": "/modules/l2-content/optimize-prompts",
    "/api/status": "/health",
    "/api/data/click": "/data/click",
    "/api/data/conversion": "/data/conversion",
    "/api/data/order": "/data/order",
    "/api/data/analysis": "/data/analysis",
    "/api/report": "/report",
  };
  if (ROUTE_MAP[apiPath]) return ROUTE_MAP[apiPath];
  // Catch-all patterns
  if (apiPath.startsWith("/api/modules/")) return apiPath.replace("/api", "");
  if (apiPath.startsWith("/api/rag/")) return apiPath.replace("/api", "");
  if (apiPath.startsWith("/api/tools/")) return apiPath.replace("/api", "");
  return apiPath.replace("/api", "");
}

const BASE = DIRECT_ORCHESTRATOR
  ? DIRECT_ORCHESTRATOR.replace(/\/$/, "")
  : "";

export type { ApiEnvelope } from "@/lib/api-envelope";
import type { ApiEnvelope } from "@/lib/api-envelope";

export interface SelectionCard {
  title: string;
  pain_points: string[];
  category: string;
}

export interface CrawlerData {
  crawled_url: string;
  selection_card: SelectionCard;
  competitor_count: number;
  rag_candidates: string[];
}

export interface OptimizePromptsPayload {
  product_url: string;
  topic?: string;
  script?: string;
  product_title?: string;
  category?: string;
  pain_points?: string[];
  platform?: string;
}

export interface OptimizePromptsData {
  optimized_topic: string;
  optimized_script: string;
  hook_suggestions: string[];
  rag_snippets: string[];
  next_steps: string[];
  provider: string;
}

export interface LayerResultPayload {
  layer_id: string;
  status: string;
  message: string;
  artifacts: Record<string, string>;
}

export interface PipelineRunData {
  job_id: string;
  status: "ok" | "qa_failed" | "error";
  pipeline_state: string;
  layers: string[];
  layer_results: LayerResultPayload[];
  artifacts: Record<string, string>;
  errors: string[];
  retry_from: string | null;
  optimization_hints: string[];
}

export interface DataClickData {
  clicks: number;
  unique_clicks: number;
  ctr: number;
  records: Array<Record<string, unknown>>;
}

export interface DataConversionData {
  conversions: number;
  conversion_rate: number;
  records: Array<Record<string, unknown>>;
}

export interface DataOrderData {
  orders: number;
  gmv: number;
  records: Array<Record<string, unknown>>;
}

export interface DataAnalysisData {
  summary: string;
  optimization_hints: string[];
  feedback_targets: string[];
}

export interface DataSourceInfo {
  source: string;
  persistent: boolean;
  sqlite_path: string | null;
  postgres_configured: boolean;
}

export interface MetricsRecordPayload {
  job_id?: string;
  metric_date?: string;
  clicks: number;
  unique_clicks: number;
  conversions: number;
  orders: number;
  gmv: number;
}

export interface MetricsRecordResult {
  job_id: string;
  metric_date: string;
  backend: string;
  message: string;
}

export interface KgTriplet {
  subject: string;
  predicate: string;
  object: string;
}

export interface KgGraphData {
  triplets: KgTriplet[];
  entities: string[];
  count: number;
}

export interface KgQueryData {
  entity: string;
  triplets: KgTriplet[];
  count: number;
}

export interface ToolsCheckData {
  video_factory: Record<string, unknown>;
  ai_koubo: Record<string, unknown>;
  c4d: Record<string, unknown>;
  ffmpeg: Record<string, unknown>;
  openclaw: Record<string, unknown>;
}

export interface ProductImageVariant {
  type: string;
  url: string;
  prompt: string;
  width: number;
  height: number;
}

export interface GenerateProductImagePayload {
  product_url?: string;
  product_title?: string;
  category?: string;
  reference_image_url?: string;
  image_types?: string[];
}

export interface GenerateProductImageData {
  images: ProductImageVariant[];
  provider: string;
  product_title: string;
  category: string;
}

/** Shared pipeline context for cross-tab prefill (一键出片 → AI商品图). */
export interface PipelineProductContext {
  productUrl: string;
  productTitle: string;
  category: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  const url = DIRECT_ORCHESTRATOR
    ? `${BASE}${orchestratorPath(path)}`
    : path;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    return {
      ok: false,
      data: null,
      error: {
        code: "network_error",
        message: "网络中断，请确认 npm run dev:web 与 npm run dev:api 均在运行",
      },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
  }
  try {
    return (await res.json()) as ApiEnvelope<T>;
  } catch {
    return {
      ok: false,
      data: null,
      error: {
        code: "invalid_response",
        message: `接口返回异常 HTTP ${res.status}`,
      },
      meta: { layer: null, job_id: null, timestamp: new Date().toISOString() },
    };
  }
}

export async function runCrawler(
  productUrl: string,
  competitorUrls: string[] = [],
): Promise<ApiEnvelope<CrawlerData>> {
  return apiFetch<CrawlerData>("/api/crawler", {
    method: "POST",
    body: JSON.stringify({ product_url: productUrl, competitor_urls: competitorUrls }),
  });
}

export async function optimizePrompts(
  payload: OptimizePromptsPayload,
): Promise<ApiEnvelope<OptimizePromptsData>> {
  return apiFetch<OptimizePromptsData>("/api/prompt/optimize", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type PipelineMode = "quick" | "full";

const LAYER_PRESETS: Record<PipelineMode, string[]> = {
  quick: ["L1", "L2", "L3", "L8"],
  full: ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"],
};

export async function runPipeline(payload: {
  product_url: string;
  topic?: string;
  script?: string;
  demo_name?: string;
  video_style?: string;
  mode?: PipelineMode;
  layers?: string[];
  force_qa_fail?: boolean;
}): Promise<ApiEnvelope<PipelineRunData>> {
  const layers =
    payload.layers ??
    LAYER_PRESETS[payload.mode ?? "quick"];
  return apiFetch<PipelineRunData>("/api/pipeline/run", {
    method: "POST",
    body: JSON.stringify({
      product_url: payload.product_url,
      topic: payload.topic || "",
      script: payload.script || "",
      demo_name: payload.demo_name || "post_production_15s_zhongcao",
      layers,
      force_qa_fail: payload.force_qa_fail || false,
    }),
  });
}

export interface PipelineStatusData {
  job_id: string;
  status: string;
  pipeline_status?: string;
  layers?: string[];
  layer_results?: LayerResultPayload[];
  artifacts?: Record<string, string>;
  errors?: string[];
  retry_from?: string | null;
  optimization_hints?: string[];
  script_id?: string;
  storyboard_id?: string;
  render_job_id?: string;
}

export async function getPipelineStatus(jobId: string): Promise<ApiEnvelope<PipelineStatusData>> {
  return apiFetch<PipelineStatusData>(`/api/pipeline/status/${jobId}`);
}

export async function getClickData(jobId?: string): Promise<ApiEnvelope<DataClickData>> {
  const params = jobId ? `?job_id=${jobId}` : "";
  return apiFetch<DataClickData>(`/api/data/click${params}`);
}

export async function getConversionData(jobId?: string): Promise<ApiEnvelope<DataConversionData>> {
  const params = jobId ? `?job_id=${jobId}` : "";
  return apiFetch<DataConversionData>(`/api/data/conversion${params}`);
}

export async function getOrderData(jobId?: string): Promise<ApiEnvelope<DataOrderData>> {
  const params = jobId ? `?job_id=${jobId}` : "";
  return apiFetch<DataOrderData>(`/api/data/order${params}`);
}

export async function getAnalysisData(jobId?: string): Promise<ApiEnvelope<DataAnalysisData>> {
  const params = jobId ? `?job_id=${jobId}` : "";
  return apiFetch<DataAnalysisData>(`/api/data/analysis${params}`);
}

export async function getDataSource(): Promise<ApiEnvelope<DataSourceInfo>> {
  return apiFetch<DataSourceInfo>("/api/modules/l8-analytics/source");
}

export async function recordMetrics(
  payload: MetricsRecordPayload,
): Promise<ApiEnvelope<MetricsRecordResult>> {
  return apiFetch<MetricsRecordResult>("/api/modules/l8-analytics/metrics", {
    method: "POST",
    body: JSON.stringify({
      job_id: payload.job_id ?? "all",
      ...payload,
    }),
  });
}

export async function getKgGraph(): Promise<ApiEnvelope<KgGraphData>> {
  return apiFetch<KgGraphData>("/api/rag/kg/graph");
}

export async function queryKg(entity: string): Promise<ApiEnvelope<KgQueryData>> {
  return apiFetch<KgQueryData>("/api/rag/kg/query", {
    method: "POST",
    body: JSON.stringify({ entity }),
  });
}

export async function getToolsCheck(): Promise<ApiEnvelope<ToolsCheckData>> {
  return apiFetch<ToolsCheckData>("/api/tools/check");
}

export async function generateProductImage(
  payload: GenerateProductImagePayload,
): Promise<ApiEnvelope<GenerateProductImageData>> {
  return apiFetch<GenerateProductImageData>(
    "/api/modules/l2-content/generate-product-image",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
