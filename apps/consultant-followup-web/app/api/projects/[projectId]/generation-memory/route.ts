import { NextResponse } from "next/server";

import { clearWorkerGenerationMemory, getWorkerGenerationMemory } from "@/lib/worker-bridge";

export const dynamic = "force-dynamic";

export async function GET(_: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const result = await getWorkerGenerationMemory(projectId);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        error: "generation_memory_fetch_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}

export async function DELETE(_: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const result = await clearWorkerGenerationMemory(projectId);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        error: "generation_memory_clear_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
