import { NextResponse } from "next/server";

import { getResult } from "@/lib/storage";

export async function GET(_: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const result = await getResult(jobId);

  if (!result) {
    return NextResponse.json(
      {
        error: "result_not_found",
        detail: `No result was found for job '${jobId}'.`,
      },
      { status: 404 }
    );
  }

  return NextResponse.json({
    scheduler_state: "complete",
    job_result: result,
  });
}
