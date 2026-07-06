"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  getClickData,
  getConversionData,
  getDataSource,
  getOrderData,
  type ApiEnvelope,
  type DataClickData,
  type DataConversionData,
  type DataOrderData,
} from "@/lib/orchestrator";

interface Props {
  jobId?: string | null;
}

type MetricStatus = "ok" | "pending" | "error";

interface MetricRow {
  label: string;
  value: string;
  status: MetricStatus;
}

const POLL_INTERVAL_MS = 10_000;

function formatMetric(
  label: string,
  res: ApiEnvelope<DataClickData | DataConversionData | DataOrderData>,
  formatter: (data: NonNullable<typeof res.data>) => string,
): MetricRow {
  if (res.ok && res.data) {
    return { label, value: formatter(res.data), status: "ok" };
  }
  const code = res.error?.code ?? "";
  const msg = res.error?.message ?? "";
  if (code === "not_found" || msg.includes("404") || msg.includes("Not Found")) {
    return { label, value: "待接入", status: "pending" };
  }
  return { label, value: msg || "暂无数据", status: "error" };
}

export function BackendTab({ jobId }: Props) {
  const [question, setQuestion] = useState("种草视频开场钩子怎么写？");
  const [kgEntity, setKgEntity] = useState("美妆");
  const [output, setOutput] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>("—");
  const [metrics, setMetrics] = useState<MetricRow[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inflightRef = useRef(false); // prevents concurrent polls

  const loadL8 = useCallback(async () => {
    if (inflightRef.current) return; // skip if previous poll still in flight
    inflightRef.current = true;
    setLoading("l8");
    try {
      const [source, click, conv, order] = await Promise.all([
        getDataSource(),
        getClickData(jobId ?? undefined),
        getConversionData(jobId ?? undefined),
        getOrderData(jobId ?? undefined),
      ]);
      setDataSource(source.data?.source ?? "demo");

      const rows: MetricRow[] = [
        formatMetric("点击量", click, (d) => {
          const c = d as DataClickData;
          return `${c.clicks} 次 · CTR ${(c.ctr * 100).toFixed(1)}%`;
        }),
        formatMetric("转化", conv, (d) => {
          const c = d as DataConversionData;
          return `${c.conversions} 次 · 转化率 ${(c.conversion_rate * 100).toFixed(1)}%`;
        }),
        formatMetric("订单 / GMV", order, (d) => {
          const o = d as DataOrderData;
          return `${o.orders} 单 · ¥${o.gmv.toLocaleString()}`;
        }),
      ];
      setMetrics(rows);
      setLastUpdated(new Date());
    } finally {
      inflightRef.current = false;
      setLoading(null);
    }
  }, [jobId]);

  useEffect(() => {
    void loadL8();
  }, [loadL8]);

  useEffect(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
    if (!jobId) return;

    // Recursive setTimeout: next poll scheduled only after previous completes
    const schedule = () => {
      pollRef.current = setTimeout(() => {
        void loadL8().finally(() => schedule());
      }, POLL_INTERVAL_MS);
    };
    schedule();

    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [jobId, loadL8]);

  const callRag = useCallback(
    async (path: string, method: "GET" | "POST", body?: object) => {
      setLoading(path);
      setOutput(null);
      try {
        const res = await fetch(`/api/rag/${path}`, {
          method,
          headers: body ? { "Content-Type": "application/json" } : undefined,
          body: body ? JSON.stringify(body) : undefined,
        });
        const json = await res.json();
        setOutput(JSON.stringify(json, null, 2));
      } finally {
        setLoading(null);
      }
    },
    [],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">知识库 · RAG</CardTitle>
          <CardDescription>ingest / query / check / kg</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!!loading} onClick={() => void callRag("status", "GET")}>
              status
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={!!loading}
              onClick={() => void callRag("ingest", "POST", { source: "directory" })}
            >
              ingest
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={!!loading}
              onClick={() => void callRag("kg/graph", "GET")}
            >
              kg/graph
            </Button>
          </div>
          <div className="flex gap-2">
            <Textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} className="text-sm" />
            <Button size="sm" disabled={!!loading} onClick={() => void callRag("query", "POST", { question, mode: "auto" })}>
              query
            </Button>
          </div>
          <div className="flex gap-2">
            <Input value={kgEntity} onChange={(e) => setKgEntity(e.target.value)} placeholder="KG 实体" className="max-w-xs text-sm" />
            <Button size="sm" variant="secondary" disabled={!!loading} onClick={() => void callRag("kg/query", "POST", { entity: kgEntity })}>
              kg/query
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">效果数据</CardTitle>
          <CardDescription>
            {jobId
              ? `任务 ${jobId} 的点击与转化指标（每 10s 自动刷新）`
              : "完成一键出片后，此处将自动绑定最近一次任务 ID"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {jobId ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default" className="font-mono text-xs">
                {jobId}
              </Badge>
              <Badge variant="secondary">数据源: {dataSource}</Badge>
              {lastUpdated && (
                <span className="text-[10px] text-muted-foreground">
                  更新于 {lastUpdated.toLocaleTimeString()}
                </span>
              )}
              <Button size="sm" variant="outline" onClick={() => void loadL8()} disabled={loading === "l8"}>
                {loading === "l8" && <Loader2 className="size-3 animate-spin" />}
                刷新
              </Button>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed bg-muted/20 p-4 space-y-2">
              <p className="text-sm font-medium">暂无任务数据</p>
              <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                <li>切到「一键出片」Tab，粘贴商品链接或选行业模板</li>
                <li>依次完成：抓取商品 → 智能写脚本 → 生成视频（快速模式约 10s）</li>
                <li>出片成功后任务 ID 会自动出现在此处，并每 10 秒刷新点击/转化指标</li>
              </ol>
              <p className="text-[10px] text-muted-foreground">
                若指标显示「待接入」，说明 L8 真实数据源尚未配置；快速模式仍会写入 demo/sqlite 种子数据。
              </p>
            </div>
          )}

          {jobId && (
            <div className="grid gap-2 sm:grid-cols-3">
              {metrics.length === 0 ? (
                <p className="text-sm text-muted-foreground col-span-3">加载中…</p>
              ) : (
                metrics.map((m) => (
                  <div key={m.label} className="rounded-lg border bg-muted/10 p-3">
                    <p className="text-xs text-muted-foreground">{m.label}</p>
                    <p
                      className={
                        m.status === "pending"
                          ? "text-sm text-muted-foreground italic"
                          : m.status === "error"
                            ? "text-sm text-destructive"
                            : "text-sm font-medium"
                      }
                    >
                      {m.value}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {output && (
        <pre className="max-h-64 overflow-auto rounded-lg border bg-muted/30 p-3 text-xs whitespace-pre-wrap">
          {output}
        </pre>
      )}
    </div>
  );
}
