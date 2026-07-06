"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Download, ImageIcon, Loader2, Play, Sparkles, Wand2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { INDUSTRY_TEMPLATES, VIDEO_STYLES, VIDEO_TEMPLATES } from "@/lib/industry-templates";
import { optimizePrompts, runCrawler, runPipeline, type ApiEnvelope, type CrawlerData, type OptimizePromptsData, type PipelineMode, type PipelineProductContext, type PipelineRunData } from "@/lib/orchestrator";

interface Props {
  onJobComplete?: (id: string) => void;
  onContextChange?: (ctx: PipelineProductContext | null) => void;
  onViewBackend?: () => void;
  onViewProductImage?: () => void;
}

export function PipelineTab({ onJobComplete, onContextChange, onViewBackend, onViewProductImage }: Props) {
  const [product, setProduct] = useState("");
  const [topic, setTopic] = useState("");
  const [script, setScript] = useState("");
  const [template, setTemplate] = useState("home");
  const [videoStyle, setVideoStyle] = useState("real");
  const [videoTemplate, setVideoTemplate] = useState("post_production_15s_zhongcao");
  const [crawlData, setCrawlData] = useState<CrawlerData | null>(null);
  const [optMeta, setOptMeta] = useState<OptimizePromptsData | null>(null);
  const [result, setResult] = useState<ApiEnvelope<PipelineRunData> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const syncCtx = useCallback((d: CrawlerData | null) => {
    onContextChange?.(d ? { productUrl: d.crawled_url, productTitle: d.selection_card.title, category: d.selection_card.category } : null);
  }, [onContextChange]);

  const applyTpl = (id: string) => {
    const t = INDUSTRY_TEMPLATES.find(x => x.id === id);
    if (t) { setTemplate(id); setProduct(t.productUrl); setTopic(t.topicHint); setScript(t.scriptHints); reset(); }
  };

  const reset = () => { setCrawlData(null); setOptMeta(null); setResult(null); setError(""); };

  /* ── Step 1: Crawl + Script ── */
  const doPrepare = async () => {
    if (!product.trim()) return;
    setLoading(true); setError(""); reset();
    try {
      const cr = await runCrawler(product.trim());
      if (!cr.ok || !cr.data) throw new Error(cr.error?.message ?? "抓取失败");
      setCrawlData(cr.data); setProduct(cr.data.crawled_url); syncCtx(cr.data);
      const card = cr.data.selection_card;
      const tpl = INDUSTRY_TEMPLATES.find(x => x.id === template);
      const or = await optimizePrompts({
        product_url: cr.data.crawled_url,
        topic: topic || [card.title, card.category].filter(Boolean).join(" · "),
        script: script || undefined,
        product_title: card.title, category: card.category || tpl?.category || "",
        pain_points: card.pain_points.length > 0 ? card.pain_points : tpl?.painPoints ?? [],
      });
      if (!or.ok || !or.data) throw new Error(or.error?.message ?? "脚本生成失败");
      setOptMeta(or.data); setTopic(or.data.optimized_topic); setScript(or.data.optimized_script);
    } catch (err) { setError(err instanceof Error ? err.message : "准备失败"); }
    finally { setLoading(false); }
  };

  /* ── Step 2: Generate Video ── */
  const doRender = async () => {
    if (!crawlData || !optMeta) return;
    setLoading(true); setError(""); setResult(null); setElapsed(0);
    const start = Date.now();
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    try {
      const res = await runPipeline({
        product_url: crawlData.crawled_url, topic, script,
        mode: "full", demo_name: videoTemplate,
      });
      if (!res.ok || !res.data) throw new Error(res.error?.message ?? "生成失败");
      setResult(res);
      onJobComplete?.(res.data.job_id);
    } catch (err) { setError(err instanceof Error ? err.message : "生成失败"); }
    finally { setLoading(false); if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } }
  };

  const canPrepare = product.trim() && !loading;
  const canRender = optMeta && !loading;
  const jobId = result?.data?.job_id;

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* ── Industry templates ── */}
      <div className="flex flex-wrap justify-center gap-1.5">
        {INDUSTRY_TEMPLATES.map(t => (
          <button key={t.id} onClick={() => applyTpl(t.id)}
            className={`rounded-full px-3 py-1 text-[10px] font-medium transition-all ${
              template === t.id ? "bg-white/[0.08] text-white/70 border border-white/[0.1]" : "bg-white/[0.02] text-white/25 border border-white/[0.03] hover:text-white/40"
            }`}>{t.name}</button>
        ))}
      </div>

      {/* ── URL + Prepare ── */}
      <div className="flex gap-2">
        <Input value={product} onChange={e => { setProduct(e.target.value); reset(); }}
          placeholder="粘贴商品链接…" disabled={loading}
          className="h-12 rounded-2xl border-white/[0.06] bg-white/[0.02] font-mono text-sm text-white/70 placeholder:text-white/15"
          onKeyDown={e => e.key === "Enter" && canPrepare && doPrepare()}
        />
        <Button onClick={() => void doPrepare()} disabled={!canPrepare}
          className="h-12 shrink-0 rounded-2xl bg-white/[0.08] border border-white/[0.1] px-6 text-sm font-medium text-white/80 hover:bg-white/[0.12] transition-all">
          {loading && !optMeta ? <Loader2 className="size-4 animate-spin" /> : <Zap className="size-4" />}
          准备
        </Button>
      </div>

      {/* ── Style + Duration ── */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="text-[10px] text-white/15">风格</span>
        {VIDEO_STYLES.map(s => (
          <button key={s.id} onClick={() => setVideoStyle(s.id)}
            className={`rounded-full px-2.5 py-0.5 text-[10px] transition-all ${
              videoStyle === s.id ? "bg-white/[0.06] text-white/60 border border-white/[0.08]" : "bg-white/[0.02] text-white/20 border border-white/[0.03]"
            }`}>{s.icon} {s.name}</button>
        ))}
        <span className="text-[10px] text-white/15 ml-2">时长</span>
        {VIDEO_TEMPLATES.map(t => (
          <button key={t.id} onClick={() => setVideoTemplate(t.id)}
            className={`rounded-full px-2 py-0.5 text-[10px] transition-all ${
              videoTemplate === t.id ? "bg-white/[0.06] text-white/60 border border-white/[0.08]" : "bg-white/[0.02] text-white/20 border border-white/[0.03]"
            }`}>{t.seconds}s</button>
        ))}
      </div>

      {loading && !optMeta && <p className="text-center text-xs text-white/20">正在抓取+写脚本…</p>}

      {/* ── Crawl result + Upload product images ── */}
      {crawlData && (
        <div className="rounded-2xl border border-amber-500/10 bg-amber-500/[0.02] p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1 min-w-0">
              <p className="text-sm font-medium text-white/70 truncate">{crawlData.selection_card.title}</p>
              <p className="text-xs text-white/25">{crawlData.selection_card.category} · {crawlData.rag_candidates.length} 条匹配</p>
            </div>
          </div>
          {/* Upload — REQUIRED for real product images */}
          <div className="rounded-xl border border-dashed border-amber-500/20 bg-amber-500/[0.03] p-3">
            <p className="text-[10px] text-amber-400/50 mb-2">CogView 免费额度今日用完，请上传产品图用于视频合成（JPEG/PNG，建议 4 张不同角度）</p>
            <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 px-4 py-2 text-xs text-amber-400/70 hover:bg-amber-500/20 transition-colors">
              <ImageIcon className="size-3.5" />选择图片上传
              <input type="file" accept="image/*" multiple className="hidden"
                onChange={async e => {
                  const files = e.target.files; if (!files) return;
                  for (const f of Array.from(files)) {
                    const fd = new FormData(); fd.append("file", f); fd.append("job_id", "preview");
                    await fetch("http://127.0.0.1:8765/upload/product-image", { method: "POST", body: fd }).catch(()=>{});
                  }
                  // Refresh to show uploaded
                  alert(`已上传 ${files.length} 张图`);
                }}
              />
            </label>
          </div>
          {/* Script editor */}
          {optMeta && (
            <details>
              <summary className="cursor-pointer text-[10px] text-white/15 hover:text-white/30">编辑脚本</summary>
              <div className="mt-2 space-y-2">
                <Textarea value={topic} onChange={e => setTopic(e.target.value)} rows={2} className="resize-none rounded-xl border-white/[0.06] bg-white/[0.02] text-sm text-white/60" />
                <Textarea value={script} onChange={e => setScript(e.target.value)} rows={5} className="resize-none rounded-xl border-white/[0.06] bg-white/[0.02] font-mono text-sm text-white/60" />
              </div>
            </details>
          )}
        </div>
      )}

      {/* ── Generate button ── */}
      {optMeta && (
        <div className="flex flex-col items-center gap-3">
          <Button onClick={() => void doRender()} disabled={!canRender}
            className="rounded-2xl bg-white/[0.08] border border-white/[0.1] px-10 py-3 text-sm font-medium text-white/80 hover:bg-white/[0.12] hover:text-white transition-all disabled:opacity-20">
            {loading && !result ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            生成视频
            <ArrowRight className="size-4" />
          </Button>
          {loading && !result && <p className="text-xs text-white/20">生成中 {elapsed}s…（L1-L4 含生图约 60s）</p>}
        </div>
      )}
      {error && <div className="rounded-2xl border border-red-500/15 bg-red-500/5 px-4 py-3 text-sm text-red-400">{error}</div>}

      {/* ── Results ── */}
      {result?.data && (
        <div className="rounded-3xl border border-white/[0.06] bg-card-gradient p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-white/50">#{jobId}</span>
            <span className={`rounded-full px-3 py-0.5 text-[10px] font-medium ${
              result.data.status === "ok" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400"
            }`}>{result.data.status}</span>
          </div>
          {result.data.layer_results.map(lr => (
            <div key={lr.layer_id} className="flex items-center gap-2 text-xs">
              <span className={`size-1.5 rounded-full ${lr.status === "ok" ? "bg-emerald-400" : "bg-red-400"}`} />
              <span className="w-8 text-white/25">{lr.layer_id}</span>
              <span className="text-white/40">{lr.message}</span>
            </div>
          ))}
          {/* Product images — only show when job is done */}
          {jobId && (
            <div className="border-t border-white/[0.04] pt-3 grid grid-cols-4 gap-2">
              {[0,1,2,3].map(i => (
                <img key={i} src={`/api/image/${jobId}/product_${i}.jpg`}
                  className="aspect-square rounded-xl border border-white/[0.06] object-cover bg-white/[0.02]"
                  onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
                  alt={`Scene ${i+1}`}
                />
              ))}
            </div>
          )}
          {/* Video player */}
          {result.data.layers?.includes("L4") && result.data.status === "ok" && (
            <div className="border-t border-white/[0.04] pt-3 space-y-2">
              <p className="text-[10px] uppercase tracking-wider text-white/15">视频</p>
              <video controls className="w-full rounded-2xl border border-white/[0.06] bg-black/50" preload="metadata">
                <source src={`/api/video/${jobId}`} type="video/mp4" />
              </video>
              <a href={`/api/video/${jobId}`} download className="inline-flex items-center gap-1 rounded-full border border-white/[0.08] px-3 py-1 text-[10px] text-white/30 hover:text-white/50">
                <Download className="size-3" />下载 MP4
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
