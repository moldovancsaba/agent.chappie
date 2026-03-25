import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { claimNextQueuedJob } from "@/lib/storage";

function isAuthorized(request: Request) {
  const expected = env.workerQueueSecret ?? "";
  const provided = request.headers.get("x-agent-worker-secret") ?? "";
  return Boolean(expected) && provided === expected;
}

/**
 * Worker pull API: claim one queued job.
 * Returns 204 when no queued job exists.
 */
export async function POST(request: Request) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const next = await claimNextQueuedJob();
    if (!next) {
      return new NextResponse(null, { status: 204 });
    }
    return NextResponse.json(next);
  } catch (error) {
    return NextResponse.json(
      {
        error: "claim_failed",
        detail: error instanceof Error ? error.message : "Unknown claim error",
      },
      { status: 500 }
    );
  }
}

