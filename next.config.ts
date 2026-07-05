import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingExcludes: {
    "/*": ["./next.config.ts", "./storage/**/*"],
  },
};

export default nextConfig;
