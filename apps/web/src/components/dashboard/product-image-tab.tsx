"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, ImageIcon, Loader2, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  generateProductImage,
  type GenerateProductImageData,
  type PipelineProductContext,
} from "@/lib/orchestrator";

interface Props { context?: PipelineProductContext | null; }

/* ── Product Image Tab: single AI product photo generation ── */
export function ProductImageTab({ context }: Props) {
  const [productTitle, setProductTitle] = useState("");
  const [category, setCategory] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [refImageUrl, setRefImageUrl] = useState("");
  const [promptExtra, setPromptExtra] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GenerateProductImageData | null>(null);

  useEffect(() => {
    if (!context) return;
    setProductTitle(context.productTitle);
    setCategory(context.category);
    setProductUrl(context.productUrl);
    setError("");
  }, [context]);

  const handleGenerate = useCallback(async () => {
    if (!productTitle.trim()) {
      setError("请填写商品名称");
      return;
    }
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await generateProductImage({
        product_url: productUrl,
        product_title: productTitle.trim(),
        category: category.trim() || "电商",
        reference_image_url: refImageUrl.trim(),
        image_types: ["白底主图"],
      });
      if (!res.ok || !res.data) throw new Error(res.error?.message ?? "生成失败");
      setResult(res.data);
    } catch (err) { setError(err instanceof Error ? err.message : "生成失败"); }
    finally { setLoading(false); }
  }, [productTitle, category, productUrl, refImageUrl]);

  const image = result?.images?.[0];

  return (
    <div className="space-y-6">
      <Card className="rounded-3xl border-white/[0.06] bg-white/[0.01] shadow-none">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-white/70">
            <ImageIcon className="size-4" /> AI 商品图生成
          </CardTitle>
          <CardDescription className="text-white/25">
            根据商品信息生成一张专业产品主图。不同角度的图在「一键出片 → 完整模式」中自动生成。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Context hint */}
          {context ? (
            <div className="rounded-2xl border border-purple-500/10 bg-purple-500/[0.02] px-4 py-2.5 text-xs text-purple-300/60">
              已从出片流程导入：{context.productTitle}{context.category ? ` · ${context.category}` : ""}
            </div>
          ) : (
            <p className="text-xs text-white/15">在「出片」Tab 完成抓取后，商品信息会自动填到这里。</p>
          )}

          {/* Basic info */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-[10px] font-medium uppercase tracking-wider text-white/15">商品名称</label>
              <Input value={productTitle} onChange={(e) => setProductTitle(e.target.value)}
                placeholder="例：壁挂免打孔脏衣篮"
                className="h-11 rounded-xl border-white/[0.06] bg-white/[0.02] text-sm text-white/70 placeholder:text-white/10" />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium uppercase tracking-wider text-white/15">品类</label>
              <Input value={category} onChange={(e) => setCategory(e.target.value)}
                placeholder="家居 / 美妆 / 鞋服 / 日用"
                className="h-11 rounded-xl border-white/[0.06] bg-white/[0.02] text-sm text-white/70 placeholder:text-white/10" />
            </div>
          </div>

          {/* Reference image URL */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium uppercase tracking-wider text-white/15">
              参考图 URL <span className="font-normal text-white/08">· 可选，传了更精准</span>
            </label>
            <Input value={refImageUrl} onChange={(e) => setRefImageUrl(e.target.value)}
              placeholder="https://... 产品照片直链"
              className="h-11 rounded-xl border-white/[0.06] bg-white/[0.02] font-mono text-sm text-white/50 placeholder:text-white/10" />
          </div>

          {/* Prompt extra */}
          <div className="space-y-1">
            <label className="text-[10px] font-medium uppercase tracking-wider text-white/15">
              补充描述 <span className="font-normal text-white/08">· 背景、风格、氛围</span>
            </label>
            <Textarea value={promptExtra} onChange={(e) => setPromptExtra(e.target.value)}
              rows={2} placeholder="纯白背景、柔和灯光、专业产品摄影…"
              className="resize-none rounded-xl border-white/[0.06] bg-white/[0.02] text-sm text-white/70 placeholder:text-white/10" />
          </div>

          {/* Generate button */}
          <Button onClick={() => void handleGenerate()} disabled={loading || !productTitle.trim()}
            className="w-full rounded-2xl bg-white/[0.06] border border-white/[0.08] py-6 text-sm font-medium text-white/70 hover:bg-white/[0.1] hover:text-white/90 transition-all">
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            生成产品主图
          </Button>

          {error && <p className="rounded-xl border border-red-500/15 bg-red-500/[0.03] px-4 py-2.5 text-sm text-red-400/80">{error}</p>}

          {/* Result */}
          {image && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge className="rounded-full bg-white/[0.04] text-[10px] text-white/40 border-white/[0.05]">
                  {result!.provider}
                </Badge>
                <span className="text-xs text-white/30">{result!.product_title}</span>
              </div>
              <div className="overflow-hidden rounded-2xl border border-white/[0.06]">
                <img src={image.url} alt={image.type} className="w-full object-cover" loading="lazy" />
              </div>
              <p className="text-[10px] text-white/15 truncate">{image.prompt}</p>
              <Button variant="outline" size="sm" className="rounded-full border-white/[0.06] text-xs text-white/30"
                onClick={() => { const a = document.createElement("a"); a.href = image.url; a.download = `${productTitle}.png`; a.click(); }}>
                <Download className="size-3" /> 下载
              </Button>
            </div>
          )}

          {/* Empty placeholder */}
          {!image && !loading && (
            <div className="flex aspect-[4/3] flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.04] bg-white/[0.005]">
              <Sparkles className="mb-3 size-8 text-white/[0.06]" />
              <span className="text-xs text-white/10">输入商品信息，点击生成</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
