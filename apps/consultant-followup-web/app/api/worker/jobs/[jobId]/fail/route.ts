import { NextResponse } from "next/server";
import { z } from "zod";

import { env } from "@/lib/env";
import { markQueuedJobFailed } from "@/lib/storage";

const payloadSchema = z.object({
  error_detail: z.string().min(1),
});

function isAuthorized(request: Request) {
  const expected = env.workerQueueSecret ?? "";
  const provided = request.headers.get("x-agent-worker-secret") ?? "";
  return Boolean(expected) && provided === expected;
}

/**
 * Worker callback: mark queue job failed.
 */
export async function POST(request: Request, context: { params: Promise<{ jobId: string }> }) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const { jobId } = await context.params;
    const body = payloadSchema.parse(await request.json());
    await markQueuedJobFailed(jobId, body.error_detail);
    return NextResponse.json({ status: "failed", job_id: jobId });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown fail error";
    const status = error instanceof z.ZodError ? 400 : 500;
    return NextResponse.json({ error: "fail_mark_failed", detail }, { status });
  }
}

