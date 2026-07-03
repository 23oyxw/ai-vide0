"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  Film,
  Lightbulb,
  Loader2,
  Play,
  Settings2,
  Sparkles,
} from "lucide-react";

import { AiAssistant } from "@/components/dashboard/ai-assistant";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

type StatusPayload = {
  ok: boolean;
  data: {
    aiGatewayConfigured: boolean;
    orchestratorUrl: string;
    orchestrator: { reachable: boolean; status?: string; error?: string };
  } | null;
};

export function DashboardShell() {
  const [topic, setTopic] = useState("");
  const [product, setProduct] = useState("");
  const [script, setScript] = useState("");
  const [pipelineResult, setPipelineResult] = useState<string | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const res = await fetch("/api/status");
      const envelope = (await res.json()) as StatusPayload;
      setStatus(envelope);
    } catch {
      setStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  async function runPipeline() {
    setPipelineLoading(true);
    setPipelineResult(null);
    try {
      const res = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          product,
          script,
          demo_name: "post_production_15s_zhongcao",
          layers: ["L3", "L4"],
        }),
      });
      const data = await res.json();
      setPipelineResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setPipelineResult(
        err instanceof Error ? err.message : "Pipeline request failed",
      );
    } finally {
      setPipelineLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/60 bg-card/50 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                AI 种草视频控制台
              </h1>
              <p className="text-xs text-muted-foreground">
                L1–L8 八层编排 · 控制面
              </p>
            </div>
          </div>
          <Badge variant="secondary">Beta</Badge>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[1fr_320px]">
        <main>
          <Tabs defaultValue="topic" className="w-full">
            <TabsList className="mb-4 w-full justify-start overflow-x-auto">
              <TabsTrigger value="topic">
                <Lightbulb className="size-3.5" />
                选题创作
              </TabsTrigger>
              <TabsTrigger value="video">
                <Film className="size-3.5" />
                视频生成
              </TabsTrigger>
              <TabsTrigger value="analytics">
                <BarChart3 className="size-3.5" />
                数据看板
              </TabsTrigger>
              <TabsTrigger value="settings">
                <Settings2 className="size-3.5" />
                设置
              </TabsTrigger>
            </TabsList>

            <TabsContent value="topic">
              <Card>
                <CardHeader>
                  <CardTitle>选题创作 · L1–L2</CardTitle>
                  <CardDescription>
                    输入产品与平台，生成选题方向与脚本大纲（演示表单）
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">产品名称</label>
                    <Input
                      placeholder="例：夏季防晒喷雾"
                      value={product}
                      onChange={(e) => setProduct(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">选题方向</label>
                    <Textarea
                      placeholder="目标人群、卖点、平台（抖音/小红书）…"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      rows={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">脚本大纲</label>
                    <Textarea
                      placeholder="开场钩子 → 痛点 → 产品展示 → CTA"
                      value={script}
                      onChange={(e) => setScript(e.target.value)}
                      rows={5}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    保存与 AI 润色将在 L2 接入 ai-koubo-platform。
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="video">
              <Card>
                <CardHeader>
                  <CardTitle>视频生成 · L3–L4</CardTitle>
                  <CardDescription>
                    触发八层管线，代理至 FastAPI orchestrator (:8765)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    将当前选题表单一并提交至{" "}
                    <code className="rounded bg-muted px-1 py-0.5 text-xs">
                      POST /api/pipeline/run
                    </code>
                  </p>
                  <Button onClick={runPipeline} disabled={pipelineLoading}>
                    {pipelineLoading ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Play className="size-4" />
                    )}
                    启动管线
                  </Button>
                  {pipelineResult && (
                    <pre className="max-h-64 overflow-auto rounded-lg border bg-muted/40 p-3 text-xs">
                      {pipelineResult}
                    </pre>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analytics">
              <Card>
                <CardHeader>
                  <CardTitle>数据看板 · L8</CardTitle>
                  <CardDescription>
                    播放量、转化与 A/B 指标（占位）
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-3">
                    {[
                      { label: "今日播放", value: "—", hint: "Postgres 接入后展示" },
                      { label: "种草转化", value: "—", hint: "Webhook 回传" },
                      { label: "在制任务", value: "—", hint: "KV 队列" },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded-xl border border-dashed border-border/80 bg-muted/20 p-4"
                      >
                        <p className="text-xs text-muted-foreground">
                          {item.label}
                        </p>
                        <p className="mt-2 text-2xl font-semibold tabular-nums">
                          {item.value}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {item.hint}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6 h-40 rounded-xl border border-dashed border-border/80 bg-muted/10 flex items-center justify-center text-sm text-muted-foreground">
                    图表区域 · ECharts / Tremor 待 L8 集成
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="settings">
              <Card>
                <CardHeader>
                  <CardTitle>环境状态</CardTitle>
                  <CardDescription>
                    控制面依赖与健康检查（只读）
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void loadStatus()}
                    disabled={statusLoading}
                  >
                    {statusLoading && (
                      <Loader2 className="size-3.5 animate-spin" />
                    )}
                    刷新状态
                  </Button>
                  <dl className="space-y-3 text-sm">
                    <div className="flex items-center justify-between rounded-lg border p-3">
                      <dt className="text-muted-foreground">AI Gateway</dt>
                      <dd>
                        {statusLoading ? (
                          <Badge variant="secondary">检测中</Badge>
                        ) : status?.data?.aiGatewayConfigured ? (
                          <Badge>已配置</Badge>
                        ) : (
                          <Badge variant="outline">未配置</Badge>
                        )}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border p-3">
                      <dt className="text-muted-foreground">Orchestrator</dt>
                      <dd>
                        {statusLoading ? (
                          <Badge variant="secondary">检测中</Badge>
                        ) : status?.data?.orchestrator.reachable ? (
                          <Badge>在线 · {status.data.orchestrator.status}</Badge>
                        ) : (
                          <Badge variant="destructive">离线</Badge>
                        )}
                      </dd>
                    </div>
                    {status?.data && (
                      <p className="text-xs text-muted-foreground">
                        目标：{status.data.orchestratorUrl}
                        {status.data.orchestrator.error
                          ? ` · ${status.data.orchestrator.error}`
                          : ""}
                      </p>
                    )}
                  </dl>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>

        <aside className="hidden lg:block">
          <div className="sticky top-6 h-[calc(100vh-7rem)]">
            <AiAssistant />
          </div>
        </aside>
      </div>
    </div>
  );
}
