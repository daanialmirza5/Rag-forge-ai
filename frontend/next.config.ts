import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone output traces the minimal `node_modules` subset needed to
  // run `server.js` directly — lets the Docker image skip shipping the
  // full node_modules tree (see frontend/Dockerfile's runner stage).
  output: "standalone",
  async rewrites() {
    // In production, the browser talks to NEXT_PUBLIC_API_URL directly. This
    // rewrite is a dev-time convenience so relative `/api/*` fetches work
    // without CORS headaches when running `next dev` against a local backend.
    const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
