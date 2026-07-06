"use client";

import { useEffect, useState } from "react";

type ModuleCheck = { name: string; ok: boolean; detail: string };

export function ModuleStatusBar() {
  const [checks, setChecks] = useState<ModuleCheck[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const items: ModuleCheck[] = [];
      let optimizePromptsOk: boolean | undefined;
      try {
        const health = await fetch("/api/status");
        const h = (await health.json()) as { data?: { orchestrator?: { reachable?: boolean; optimizePrompts?: boolean } } };
        const orch = h.data?.orchestrator;
        optimizePromptsOk = orch?.optimizePrompts !== false;
        items.push({ name: "后台", ok: Boolean(orch?.reachable && optimizePromptsOk), detail: orch?.reachable ? "在线" : "离线" });
      } catch { items.push({ name: "后台", ok: false, detail: "离线" }); }
      try {
        const topics = await fetch("/api/modules/l1-crawler/topics");
        const t = await topics.json();
        items.push({ name: "抓取", ok: Boolean(t.ok), detail: t.ok ? `${t.data?.total ?? 0}条` : "失败" });
      } catch { items.push({ name: "抓取", ok: false, detail: "失败" }); }
      items.push({ name: "脚本", ok: optimizePromptsOk ?? false, detail: optimizePromptsOk ? "就绪" : "待重启" });
      if (!cancelled) setChecks(items);
    }
    void run();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="mb-10 flex items-center justify-center gap-4">
      {checks.map((c) => (
        <div key={c.name} className="flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1">
          <span className={`size-1.5 rounded-full ${c.ok ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]" : "bg-red-400"}`} />
          <span className="text-[11px] text-white/50">{c.name}</span>
          <span className="text-[10px] text-white/25">{c.detail}</span>
        </div>
      ))}
    </div>
  );
}
