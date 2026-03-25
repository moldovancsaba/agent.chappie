import { readFileSync } from "node:fs";
import path from "node:path";

import type { NextConfig } from "next";

const pkgPath = path.join(process.cwd(), "package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version: string };

const vercelSha = (process.env.VERCEL_GIT_COMMIT_SHA || "").trim();
const deploySha = vercelSha ? vercelSha.slice(0, 7) : "local";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_APP_VERSION: pkg.version,
    /** Proves which Git commit Vercel built (empty on misconfigured preview; "local" on dev). */
    NEXT_PUBLIC_DEPLOY_SHA: deploySha,
  },
};

export default nextConfig;
