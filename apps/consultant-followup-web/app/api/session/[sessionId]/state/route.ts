import { NextResponse } from "next/server";

import { saveResult, getLatestSessionState, normalizeStoredJobResult, resultNeedsRefresh } from "@/lib/storage";
import { regenerateWorkerChecklist } from "@/lib/worker-bridge";

export async function GET(_: Request, context: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await context.params;
  const state = await getLatestSessionState(sessionId);

  if (state.project && state.result && resultNeedsRefresh(state.result)) {
    try {
      const regenerated = await regenerateWorkerChecklist({
        projectId: state.project.projectId,
        jobId: state.result.job_id,
        appId: state.result.app_id,
      });
      await saveResult(regenerated);
      state.result = normalizeStoredJobResult(regenerated);
    } catch {
      state.result = normalizeStoredJobResult(state.result);
    }
  }

  return NextResponse.json({
    project: state.project,
    job_request: state.job,
    job_result: state.result,
  });
}
