import { NextResponse } from "next/server";

import { feedbackSchema } from "@/lib/contracts";
import { saveFeedback } from "@/lib/storage";

export async function POST(request: Request) {
  try {
    const payload = feedbackSchema.parse(await request.json());
    await saveFeedback(payload);

    return NextResponse.json({
      status: "saved",
      feedback_id: payload.feedback_id,
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
