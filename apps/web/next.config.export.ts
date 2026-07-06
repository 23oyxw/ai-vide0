import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // Static export requires unoptimized images
  images: { unoptimized: true },
  // Gitee Pages compatibility
  trailingSlash: true,
};

export default nextConfig;
