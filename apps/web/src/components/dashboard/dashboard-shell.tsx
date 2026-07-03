"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  Calendar,
  Clapperboard,
  Film,
  Loader2,
  Megaphone,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

import { AiAssistant } from "@/components/dashboard/ai-assistant";
import { ModulePanel } from "@/components/dashboard/module-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type StatusPayload = {
  ok: boolean;
  data: {
    aiGatewayConfigured: boolean;
    orchestratorUrl: string;
    orchestrator: { reachable: boolean; status?: string; error?: string };
  } | null;
};

const MODULE_TABS = [
  { value: "m1", label: "M1 热点", icon: Search },
  { value: "m2", label: "M2 文案", icon: Sparkles },
  { value: "m3", label: "M3 分镜", icon: Clapperboard },
  { value: "m4", label: "M4 渲染", icon: Film },
  { value: "m5", label: "M5 调度", icon: Workflow },
  { value: "m6", label: "M6 质检", icon: ShieldCheck },
  { value: "m7", label: "M7 发布", icon: Megaphone },
  { value: "m8", label: "M8 数据", icon: BarChart3 },
  { value: "settings", label: "设置", icon: Settings2 },
] as const;

export function DashboardShell() {
  const [activeTab, setActiveTab] = useState("m1");
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const res = await fetch("/api/status");
      setStatus((await res.json()) as StatusPayload);
    } catch {
      setStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/60 bg-card/50 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Calendar className="size-4" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">AI 种草视频控制台</h1>
              <p className="text-xs text-muted-foreground">8 独立功能模块 · 可单独调用或串联管线</p>
            </div>
          </div>
          <Badge variant="secondary">Modules v2</Badge>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[1fr_320px]">
        <main>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="mb-4 w-full justify-start overflow-x-auto flex-wrap h-auto gap-1">
              {MODULE_TABS.map(({ value, label, icon: Icon }) => (
                <TabsTrigger key={value} value={value} className="text-xs">
                  <Icon className="size-3.5" />
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="m1">
              <ModulePanel
                moduleId="M1"
                title="热点检索"
                description="POST /modules/l1-crawler/search — 电商/三农热点 + 商品抓取"
                endpoint="l1-crawler/search"
                fields={[
                  { key: "keyword", label: "关键词", placeholder: "夏季防晒" },
                  { key: "vertical", label: "垂直", placeholder: "电商" },
                  { key: "product_url", label: "商品链接", placeholder: "https://..." },
                ]}
                buildBody={(v) => ({
                  keyword: v.keyword || null,
                  vertical: v.vertical || "电商",
                  product_url: v.product_url || null,
                })}
              />
            </TabsContent>

            <TabsContent value="m2">
              <ModulePanel
                moduleId="M2"
                title="内容创作"
                description="POST /modules/l2-content/generate-script — 15秒四段口播"
                endpoint="l2-content/generate-script"
                fields={[
                  { key: "product_url", label: "商品链接", placeholder: "https://..." },
                  { key: "topic", label: "选题", placeholder: "平价护肤", multiline: true },
                  { key: "raw_text", label: "脚本大纲", placeholder: "hook → 痛点 → 产品 → CTA", multiline: true },
                ]}
                buildBody={(v) => ({
                  product_url: v.product_url || null,
                  topic: v.topic || "",
                  raw_text: v.raw_text || "",
                })}
              />
            </TabsContent>

            <TabsContent value="m3">
              <ModulePanel
                moduleId="M3"
                title="镜头重构"
                description="POST /modules/l3-storyboard/build-from-script"
                endpoint="l3-storyboard/build-from-script"
                fields={[
                  { key: "script_id", label: "脚本 ID", placeholder: "sxxxxxxxx" },
                  { key: "demo_name", label: "Demo", placeholder: "post_production_15s_zhongcao" },
                ]}
                buildBody={(v) => ({
                  script_id: v.script_id || null,
                  demo_name: v.demo_name || "post_production_15s_zhongcao",
                })}
              />
            </TabsContent>

            <TabsContent value="m4">
              <ModulePanel
                moduleId="M4"
                title="渲染合成"
                description="POST /modules/l4-render/render — video-factory + C4D scene2"
                endpoint="l4-render/render"
                fields={[
                  { key: "storyboard_id", label: "分镜 ID", placeholder: "sbxxxxxxx" },
                  { key: "demo_name", label: "Demo", placeholder: "post_production_15s_zhongcao" },
                ]}
                buildBody={(v) => ({
                  storyboard_id: v.storyboard_id || null,
                  demo_name: v.demo_name || "post_production_15s_zhongcao",
                })}
              />
            </TabsContent>

            <TabsContent value="m5">
              <div className="space-y-4">
                <ModulePanel
                  moduleId="M5"
                  title="创建调度任务"
                  description="POST /modules/l5-scheduler/jobs"
                  endpoint="l5-scheduler/jobs"
                  fields={[
                    { key: "product_url", label: "商品链接", placeholder: "https://..." },
                    { key: "demo_name", label: "Demo", placeholder: "post_production_15s_zhongcao" },
                  ]}
                  buildBody={(v) => ({
                    product_url: v.product_url || null,
                    demo_name: v.demo_name || "post_production_15s_zhongcao",
                  })}
                />
                <ModulePanel
                  moduleId="M5"
                  title="查询任务"
                  description="GET /modules/l5-scheduler/jobs"
                  endpoint="l5-scheduler/jobs"
                  method="GET"
                  fields={[]}
                />
              </div>
            </TabsContent>

            <TabsContent value="m6">
              <div className="space-y-4">
                <ModulePanel
                  moduleId="M6"
                  title="质检校验"
                  description="POST /modules/l6-qa/validate"
                  endpoint="l6-qa/validate"
                  fields={[
                    { key: "manifest_path", label: "Manifest", placeholder: "C:\\...\\manifest.json" },
                    { key: "script_text", label: "脚本文本", placeholder: "口播内容", multiline: true },
                  ]}
                  buildBody={(v) => ({
                    manifest_path: v.manifest_path || "",
                    script_text: v.script_text || "",
                  })}
                />
                <ModulePanel
                  moduleId="M6"
                  title="违禁词规则"
                  description="GET /modules/l6-qa/rules"
                  endpoint="l6-qa/rules"
                  method="GET"
                />
              </div>
            </TabsContent>

            <TabsContent value="m7">
              <div className="space-y-4">
                <ModulePanel
                  moduleId="M7"
                  title="发布输出"
                  description="POST /modules/l7-publish/publish — UTM + 多平台"
                  endpoint="l7-publish/publish"
                  fields={[
                    { key: "job_id", label: "Job ID", placeholder: "jxxxxxxx" },
                    { key: "video_path", label: "视频路径", placeholder: "C:\\...\\final.mp4" },
                    { key: "title", label: "标题", placeholder: "种草视频标题" },
                  ]}
                  buildBody={(v) => ({
                    job_id: v.job_id || "demo",
                    video_path: v.video_path || "",
                    title: v.title || "",
                  })}
                />
                <ModulePanel
                  moduleId="M7"
                  title="已发布列表"
                  description="GET /modules/l7-publish/published"
                  endpoint="l7-publish/published"
                  method="GET"
                />
              </div>
            </TabsContent>

            <TabsContent value="m8">
              <div className="space-y-4">
                <ModulePanel
                  moduleId="M8"
                  title="运营看板"
                  description="GET /modules/l8-analytics/dashboard"
                  endpoint="l8-analytics/dashboard"
                  method="GET"
                />
                <ModulePanel
                  moduleId="M8"
                  title="点击 / 转化 / 订单 / 分析"
                  description="GET /modules/l8-analytics/analysis"
                  endpoint="l8-analytics/analysis"
                  method="GET"
                  fields={[{ key: "job_id", label: "Job ID (query)", placeholder: "可选" }]}
                />
              </div>
            </TabsContent>

            <TabsContent value="settings">
              <div className="rounded-lg border bg-card p-6 space-y-4">
                <h3 className="text-lg font-semibold">环境状态</h3>
                <Button variant="outline" size="sm" onClick={() => void loadStatus()} disabled={statusLoading}>
                  {statusLoading && <Loader2 className="size-3.5 animate-spin" />}
                  刷新
                </Button>
                <p className="text-sm text-muted-foreground">
                  Orchestrator:{" "}
                  {status?.data?.orchestrator.reachable ? "在线" : "离线"} ·{" "}
                  {status?.data?.orchestratorUrl}
                </p>
              </div>
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
