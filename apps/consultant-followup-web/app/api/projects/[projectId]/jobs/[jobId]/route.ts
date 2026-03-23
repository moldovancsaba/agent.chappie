import { NextResponse } from "next/server";

import { deleteWorkerJob, updateWorkerJob } from "@/lib/worker-bridge";

export async function PATCH(request: Request, context: { params: Promise<{ projectId: string; jobId: string }> }) {
  try {
    const { projectId, jobId } = await context.params;
    const payload = await request.json();
    const response = await updateWorkerJob(projectId, jobId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "job_update_failed",
        detail: error instanceof Error ? error.message : "Unknown job update error",
      },
      { status: 400 }
    );
  }
}

export async function DELETE(_: Request, context: { params: Promise<{ projectId: string; jobId: string }> }) {
  try {
    const { projectId, jobId } = await context.params;
    const response = await deleteWorkerJob(projectId, jobId);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "job_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown job delete error",
      },
      { status: 400 }
    );
  }
}
