import { NextResponse } from "next/server";

import { deleteWorkerSource, updateWorkerSource } from "@/lib/worker-bridge";

export async function PATCH(request: Request, context: { params: Promise<{ projectId: string; sourceId: string }> }) {
  try {
    const { projectId, sourceId } = await context.params;
    const payload = await request.json();
    const response = await updateWorkerSource(projectId, sourceId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "source_update_failed",
        detail: error instanceof Error ? error.message : "Unknown source update error",
      },
      { status: 400 }
    );
  }
}

export async function DELETE(_: Request, context: { params: Promise<{ projectId: string; sourceId: string }> }) {
  try {
    const { projectId, sourceId } = await context.params;
    const response = await deleteWorkerSource(projectId, sourceId);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "source_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown source delete error",
      },
      { status: 400 }
    );
  }
}
