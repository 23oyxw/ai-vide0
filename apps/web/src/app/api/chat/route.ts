import { createOpenAI } from "@ai-sdk/openai";
import { streamText, type CoreMessage } from "ai";

export const maxDuration = 30;

function stubTextStream(message: string) {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(message));
        controller.close();
      },
    }),
    {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    },
  );
}

/** AI_GATEWAY_API_KEY from Vercel AI Gateway; optional AI_GATEWAY_URL */
export async function POST(req: Request) {
  const { messages } = (await req.json()) as {
    messages?: CoreMessage[];
  };

  const apiKey = process.env.AI_GATEWAY_API_KEY;
  if (!apiKey) {
    return stubTextStream(
      "【演示模式】未配置 AI_GATEWAY_API_KEY。请在 Vercel 环境变量或 apps/web/.env.local 中设置后启用 AI 助手流式回复。",
    );
  }

  const gateway = createOpenAI({
    apiKey,
    baseURL:
      process.env.AI_GATEWAY_URL ?? "https://gateway.ai.vercel.ai/v1",
  });

  const result = streamText({
    model: gateway("openai/gpt-4o-mini"),
    messages: messages ?? [],
    system:
      "你是 AI 种草视频 SaaS 的文案助手，帮助用户撰写选题、脚本与带货话术。回答简洁、中文优先。",
  });

  return result.toTextStreamResponse();
}
