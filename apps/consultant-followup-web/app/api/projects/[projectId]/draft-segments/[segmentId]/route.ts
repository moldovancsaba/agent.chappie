import { NextResponse } from "next/server";

import { deleteWorkerDraftSegment } from "@/lib/worker-bridge";

export async function DELETE(
  request: Request,
  context: { params: Promise<{ projectId: string; segmentId: string }> }
) {
  try {
    const { projectId, segmentId } = await context.params;
    const payload = await request.json().catch(() => ({}));
    const response = await deleteWorkerDraftSegment(projectId, segmentId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "draft_segment_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
