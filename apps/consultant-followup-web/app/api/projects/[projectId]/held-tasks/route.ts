import { NextResponse } from "next/server";

import { getWorkerHeldTasks } from "@/lib/worker-bridge";

export const dynamic = "force-dynamic";

export async function GET(_: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const result = await getWorkerHeldTasks(projectId);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        error: "held_tasks_fetch_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
