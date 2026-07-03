import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6">
      <Card className="w-full max-w-lg border-border/60 bg-card/80 shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
            <Sparkles className="size-7" />
          </div>
          <CardTitle className="text-2xl">AI 种草视频 SaaS</CardTitle>
          <CardDescription>
            多模态 AI 视频编排 · Next.js 控制面 + FastAPI 八层管线
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-center text-sm text-muted-foreground">
            选题创作、视频生成、数据看板与 AI 助手，统一在 SaaS 控制台操作。
          </p>
          <Button render={<Link href="/dashboard" />} nativeButton={false} size="lg" className="w-full">
            进入控制台
            <ArrowRight className="size-4" />
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            本地开发：npm run dev:web · 编排器 :8765
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
