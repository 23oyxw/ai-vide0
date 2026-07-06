"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ImageIcon, Layers, Loader2, Play } from "lucide-react";

import { BackendTab } from "@/components/dashboard/backend-tab";
import { ModuleStatusBar } from "@/components/dashboard/module-status-bar";
import { PipelineTab } from "@/components/dashboard/pipeline-tab";
import { ProductImageTab } from "@/components/dashboard/product-image-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PipelineProductContext } from "@/lib/orchestrator";

type StatusPayload = {
  ok: boolean;
  data: {
    orchestratorUrl: string;
    orchestrator: { reachable: boolean; status?: string; error?: string; optimizePrompts?: boolean };
  } | null;
};

/* ── Distinctive logo mark: layered rings evoking video/orchestration ── */
function LogoMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="shrink-0">
      {/* Outer ring */}
      <circle cx="16" cy="16" r="14" stroke="url(#logo-outer)" strokeWidth="1.2" opacity="0.5" />
      {/* Middle ring */}
      <circle cx="16" cy="16" r="9" stroke="url(#logo-mid)" strokeWidth="1.5" opacity="0.7" />
      {/* Inner dot */}
      <circle cx="16" cy="16" r="3.5" fill="url(#logo-inner)" />
      {/* Orbit accent */}
      <path d="M16 2a14 14 0 0 1 9.9 23.9" stroke="url(#logo-accent)" strokeWidth="1.8" strokeLinecap="round" opacity="0.9" />
      <defs>
        <linearGradient id="logo-outer" x1="0" y1="0" x2="32" y2="32">
          <stop stopColor="#7c3aed" stopOpacity="0.6" /><stop offset="1" stopColor="#4f46e5" stopOpacity="0.3" />
        </linearGradient>
        <linearGradient id="logo-mid" x1="32" y1="0" x2="0" y2="32">
          <stop stopColor="#a78bfa" stopOpacity="0.8" /><stop offset="1" stopColor="#6366f1" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="logo-inner" x1="0" y1="0" x2="32" y2="32">
          <stop stopColor="#c4b5fd" /><stop offset="1" stopColor="#818cf8" />
        </linearGradient>
        <linearGradient id="logo-accent" x1="0" y1="0" x2="32" y2="32">
          <stop stopColor="#f59e0b" stopOpacity="0.9" /><stop offset="1" stopColor="#d97706" stopOpacity="0.6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function DashboardShell() {
  const [activeTab, setActiveTab] = useState("pipeline");
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [pipelineContext, setPipelineContext] = useState<PipelineProductContext | null>(null);
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    setStatusLoading(true);
    try { const res = await fetch("/api/status"); setStatus((await res.json()) as StatusPayload); }
    catch { setStatus(null); }
    finally { setStatusLoading(false); }
  }, []);

  useEffect(() => { void loadStatus(); }, [loadStatus]);

  const orchOk = status?.data?.orchestrator?.reachable && status?.data?.orchestrator?.optimizePrompts !== false;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#08080d] bg-mesh">
      {/* Noise texture overlay */}
      <div className="bg-noise" />

      {/* Ambient glows — very subtle */}
      <div className="pointer-events-none fixed -top-32 right-0 size-[28rem] animate-glow-shift" style={{ background: "radial-gradient(circle at 70% 30%, oklch(0.45 0.18 280 / 0.18), transparent 65%)" }} />
      <div className="pointer-events-none fixed bottom-0 -left-32 size-[24rem] animate-glow-shift" style={{ background: "radial-gradient(circle at 30% 70%, oklch(0.40 0.15 260 / 0.12), transparent 65%)", animationDelay: "4s" }} />

      {/* Header */}
      <header className="relative z-30 border-b border-white/[0.04] bg-[#08080d]/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-8 py-4">
          <div className="flex items-center gap-3.5">
            <LogoMark />
            <div>
              <h1 className="text-[13px] font-medium tracking-[0.02em] text-white/75">Orchestrator</h1>
              <p className="text-[10px] tracking-[0.05em] text-white/20">AI VIDEO STUDIO</p>
            </div>
          </div>
          <div className="flex items-center gap-5">
            {lastJobId && (
              <span className="rounded-full border border-white/[0.05] bg-white/[0.02] px-3 py-0.5 font-mono text-[10px] tracking-wider text-white/30">
                {lastJobId.slice(0, 8)}
              </span>
            )}
            <div className="flex items-center gap-1.5">
              <span className={`size-1.5 rounded-full transition-colors duration-1000 ${orchOk ? "bg-emerald-400/80 shadow-[0_0_6px_rgba(52,211,153,0.3)]" : "bg-red-400/60"}`} />
              <span className="text-[10px] text-white/20">{orchOk ? "ON" : "OFF"}</span>
            </div>
            <button
              onClick={() => void loadStatus()}
              disabled={statusLoading}
              className="flex size-6 items-center justify-center rounded-md text-white/10 hover:text-white/30 transition-colors"
            >
              {statusLoading ? <Loader2 className="size-2.5 animate-spin" /> : null}
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 mx-auto max-w-4xl px-8 py-20 stagger">
        <ModuleStatusBar />

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
          <div className="mb-14 flex justify-center">
            <TabsList className="inline-flex gap-0.5 rounded-full border border-white/[0.04] bg-white/[0.01] p-1">
              <TabsTrigger value="pipeline" className="gap-1.5 rounded-full px-5 py-2 text-[12px] font-medium text-white/25 data-[active]:bg-white/[0.06] data-[active]:text-white/70 transition-all duration-300">
                <Play className="size-3" /> 出片
              </TabsTrigger>
              <TabsTrigger value="product-image" className="gap-1.5 rounded-full px-5 py-2 text-[12px] font-medium text-white/25 data-[active]:bg-white/[0.06] data-[active]:text-white/70 transition-all duration-300">
                <ImageIcon className="size-3" /> 商品图
              </TabsTrigger>
              <TabsTrigger value="backend" className="gap-1.5 rounded-full px-5 py-2 text-[12px] font-medium text-white/25 data-[active]:bg-white/[0.06] data-[active]:text-white/70 transition-all duration-300">
                <Layers className="size-3" /> 数据
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="pipeline">
            <PipelineTab
              onJobComplete={(id) => setLastJobId(id)}
              onContextChange={setPipelineContext}
              onViewBackend={() => setActiveTab("backend")}
              onViewProductImage={() => setActiveTab("product-image")}
            />
          </TabsContent>
          <TabsContent value="product-image">
            <ProductImageTab context={pipelineContext} />
          </TabsContent>
          <TabsContent value="backend">
            <BackendTab jobId={lastJobId} />
          </TabsContent>
        </Tabs>

        <p className="mt-16 text-center text-[10px] tracking-[0.08em] text-white/[0.06] font-mono uppercase">
          {status?.data?.orchestratorUrl ?? "localhost:8765"}
        </p>
      </main>
    </div>
  );
}
