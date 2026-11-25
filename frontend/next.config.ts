import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    cpus: 1,
    staticGenerationMaxConcurrency: 1,
  },
  async rewrites() {
    return [{
      source: "/backend/:path*",
      destination: `${process.env.BACKEND_INTERNAL_URL || "http://localhost:8000"}/:path*`,
    }];
  },
};

export default nextConfig;
