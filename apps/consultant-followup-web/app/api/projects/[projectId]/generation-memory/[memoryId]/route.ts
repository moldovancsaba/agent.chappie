import { NextResponse } from "next/server";

import { deleteWorkerGenerationMemoryRow } from "@/lib/worker-bridge";

export const dynamic = "force-dynamic";

export async function DELETE(
  _: Request,
  context: { params: Promise<{ projectId: string; memoryId: string }> }
) {
  try {
    const { projectId, memoryId } = await context.params;
    const result = await deleteWorkerGenerationMemoryRow(projectId, memoryId);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        error: "generation_memory_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
