import { NextResponse } from "next/server";

import { getQueuedJob, getResult, normalizeStoredJobResult } from "@/lib/storage";

export async function GET(_: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const result = await getResult(jobId);

  if (result) {
    return NextResponse.json({
      scheduler_state: result.status === "complete" ? "complete" : "blocked",
      job_result: normalizeStoredJobResult(result),
    });
  }

  const queued = await getQueuedJob(jobId);
  if (!queued) {
    return NextResponse.json(
      {
        error: "result_not_found",
        detail: `No queued job or result was found for job '${jobId}'.`,
      },
      { status: 404 }
    );
  }

  return NextResponse.json({
    scheduler_state: queued.status,
    job_id: queued.job_id,
    project_id: queued.project_id,
    detail:
      queued.status === "failed"
        ? queued.error_detail ?? "Job failed on worker."
        : "Job is still processing.",
  }, { status: queued.status === "failed" ? 500 : 202 });
}
