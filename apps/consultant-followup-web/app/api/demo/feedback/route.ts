import { NextResponse } from "next/server";

import { feedbackSchema } from "@/lib/contracts";
import { env } from "@/lib/env";
import { saveFeedback } from "@/lib/storage";
import { saveResult } from "@/lib/storage";
import { submitWorkerTaskFeedback } from "@/lib/worker-bridge";

export async function POST(request: Request) {
  try {
    const payload = feedbackSchema.parse(await request.json());
    await saveFeedback(payload);

    let regenerated: unknown = null;
    if (env.agentBridgeMode === "worker" && payload.project_id) {
      regenerated = await submitWorkerTaskFeedback(payload.project_id, payload);
      if (
        regenerated &&
        typeof regenerated === "object" &&
        "job_result" in regenerated &&
        regenerated.job_result &&
        typeof regenerated.job_result === "object"
      ) {
        await saveResult(regenerated.job_result as never);
      }
    }

    return NextResponse.json({
      status: "saved",
      feedback_id: payload.feedback_id,
      regenerated,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "feedback_submission_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
