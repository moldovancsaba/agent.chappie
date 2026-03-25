import { NextResponse } from "next/server";
import { z } from "zod";

import { jobResultSchema } from "@/lib/contracts";
import { env } from "@/lib/env";
import { saveResult } from "@/lib/storage";

/** Large job_result JSON + Neon write; avoid Vercel default short limit cutting off the worker upload. */
export const maxDuration = 300;

const payloadSchema = z.object({
  job_result: jobResultSchema,
});

function isAuthorized(request: Request) {
  const expected = env.workerQueueSecret ?? "";
  const provided = request.headers.get("x-agent-worker-secret") ?? "";
  return Boolean(expected) && provided === expected;
}

/**
 * Worker callback: complete a claimed queue job by saving JobResult.
 */
export async function POST(request: Request, context: { params: Promise<{ jobId: string }> }) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const { jobId } = await context.params;
    const body = payloadSchema.parse(await request.json());
    if (body.job_result.job_id !== jobId) {
      return NextResponse.json(
        { error: "job_id_mismatch", detail: "URL jobId and payload job_result.job_id must match." },
        { status: 400 }
      );
    }
    await saveResult(body.job_result);
    return NextResponse.json({ status: "saved", job_id: jobId });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown complete error";
    const status = error instanceof z.ZodError ? 400 : 500;
    return NextResponse.json({ error: "complete_failed", detail }, { status });
  }
}

