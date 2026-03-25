import { NextResponse } from "next/server";

import { deleteWorkerIngestedSource, updateWorkerIngestedSource } from "@/lib/worker-bridge";

function decodeSourceRefParam(sourceRef: string): string {
  try {
    return decodeURIComponent(sourceRef);
  } catch {
    return sourceRef;
  }
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ projectId: string; sourceRef: string }> }
) {
  try {
    const { projectId, sourceRef: rawRef } = await context.params;
    const sourceRef = decodeSourceRefParam(rawRef);
    const payload = await request.json();
    const response = await updateWorkerIngestedSource(projectId, sourceRef, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "ingested_source_update_failed",
        detail: error instanceof Error ? error.message : "Unknown ingested source update error",
      },
      { status: 400 }
    );
  }
}

export async function DELETE(
  _: Request,
  context: { params: Promise<{ projectId: string; sourceRef: string }> }
) {
  try {
    const { projectId, sourceRef: rawRef } = await context.params;
    const sourceRef = decodeSourceRefParam(rawRef);
    const response = await deleteWorkerIngestedSource(projectId, sourceRef);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "ingested_source_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown ingested source delete error",
      },
      { status: 400 }
    );
  }
}
