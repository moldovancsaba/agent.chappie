import { NextResponse } from "next/server";

import { getResult, normalizeStoredJobResult, resultNeedsRefresh, saveResult } from "@/lib/storage";
import { regenerateWorkerChecklist } from "@/lib/worker-bridge";

export async function GET(_: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  let result = await getResult(jobId);

  if (!result) {
    return NextResponse.json(
      {
        error: "result_not_found",
        detail: `No result was found for job '${jobId}'.`,
      },
      { status: 404 }
    );
  }

  if (resultNeedsRefresh(result)) {
    try {
      const regenerated = await regenerateWorkerChecklist({
        projectId: result.project_id,
        jobId: result.job_id,
        appId: result.app_id,
      });
      await saveResult(regenerated);
      result = normalizeStoredJobResult(regenerated);
    } catch {
      result = normalizeStoredJobResult(result);
    }
  }

  return NextResponse.json({
    scheduler_state: result.status === "complete" ? "complete" : "blocked",
    job_result: result,
  });
}
