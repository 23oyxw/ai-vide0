"use client";

import { useChat } from "ai/react";
import { Loader2, MessageSquare, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export function AiAssistant() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } =
    useChat({
      api: "/api/chat",
      streamProtocol: "text",
    });

  return (
    <Card className="flex h-full flex-col border-border/60 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base font-medium">
          <MessageSquare className="size-4 text-primary" />
          AI 助手
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          选题与脚本建议 · 连接 Vercel AI Gateway
        </p>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3 pt-0">
        <div className="min-h-[200px] flex-1 space-y-3 overflow-y-auto rounded-lg border border-border/50 bg-muted/30 p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              输入产品卖点或目标人群，获取种草文案建议。
            </p>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "ml-4 rounded-lg bg-primary/10 px-3 py-2 text-sm"
                    : "mr-4 rounded-lg bg-background px-3 py-2 text-sm"
                }
              >
                <span className="mb-1 block text-xs font-medium text-muted-foreground">
                  {m.role === "user" ? "你" : "助手"}
                </span>
                {m.content}
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3 animate-spin" />
              生成中…
            </div>
          )}
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <Textarea
            value={input}
            onChange={handleInputChange}
            placeholder="描述产品、平台与风格…"
            rows={3}
            className="resize-none"
          />
          <Button type="submit" size="sm" disabled={isLoading || !input.trim()}>
            <Send className="size-3.5" />
            发送
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
