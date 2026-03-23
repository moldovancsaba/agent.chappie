import { NextResponse } from "next/server";

import { getLatestSessionState } from "@/lib/storage";

export async function GET(_: Request, context: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await context.params;
  const state = await getLatestSessionState(sessionId);

  return NextResponse.json({
    project: state.project,
    job_request: state.job,
    job_result: state.result,
  });
}
