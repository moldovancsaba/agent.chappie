import { NextResponse } from "next/server";

import { restoreWorkerHeldTask } from "@/lib/worker-bridge";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const body = await request.json();
    if (!body || typeof body.held_task_id !== "string") {
      return NextResponse.json({ error: "missing_held_task_id" }, { status: 400 });
    }
    const result = await restoreWorkerHeldTask(projectId, body.held_task_id);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      {
        error: "held_tasks_restore_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
