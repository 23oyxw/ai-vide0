"use client";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-lg font-semibold">页面加载失败</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        {error.message || "构建缓存可能已损坏。请重启前端：删除 apps/web/.next 后运行 npm run dev:web"}
      </p>
      <button
        type="button"
        className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
        onClick={() => reset()}
      >
        重试
      </button>
    </div>
  );
}
