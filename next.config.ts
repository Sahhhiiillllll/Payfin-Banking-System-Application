import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Suppress font fetch warnings in CI/sandboxed environments
  // Google Fonts are fetched at build time on Vercel — this is fine in production
  async rewrites() {
    // In production (Vercel), /api/* is handled by api/index.py serverless function.
    // In local dev, proxy to the Flask dev server.
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    const apiUrl = process.env.API_DEV_URL || "http://127.0.0.1:5001";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
