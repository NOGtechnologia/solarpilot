import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

// Produktion: statischer Export (wird von nginx oder direkt vom FastAPI-Backend ausgeliefert).
// Entwicklung: /api wird an das Backend weitergeleitet.
const nextConfig: NextConfig = {
  output: isProd ? "export" : undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
  reactStrictMode: true,
  ...(isProd
    ? {}
    : {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
        },
      }),
};

export default nextConfig;
