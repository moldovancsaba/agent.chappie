import { readFileSync } from "node:fs";
import path from "node:path";

import type { NextConfig } from "next";

const pkgPath = path.join(process.cwd(), "package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version: string };

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_APP_VERSION: pkg.version,
  },
};

export default nextConfig;
