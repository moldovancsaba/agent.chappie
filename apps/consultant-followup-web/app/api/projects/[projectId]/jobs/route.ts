import { NextResponse } from "next/server";

import { createWorkerJob } from "@/lib/worker-bridge";

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const payload = await request.json();
    const response = await createWorkerJob(projectId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "job_create_failed",
        detail: error instanceof Error ? error.message : "Unknown job create error",
      },
      { status: 400 }
    );
  }
}
