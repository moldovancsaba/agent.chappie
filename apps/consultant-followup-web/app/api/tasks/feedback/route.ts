import { NextResponse } from "next/server";
import { z } from "zod";

import { env } from "@/lib/env";
import { submitWorkerTaskFeedbackV2 } from "@/lib/worker-bridge";

const taskFeedbackV2Schema = z.object({
  project_id: z.string().min(1),
  task_id: z.string().min(1),
  action_type: z.enum([
    "done",
    "edit",
    "decline_and_replace",
    "delete_only",
    "delete_and_teach",
    "hold_for_later",
  ]),
  comment: z.string().optional(),
  edited_title: z.string().optional(),
});

/**
 * POST /api/tasks/feedback — Phase 8 app boundary for feedback_v2.
 * Forwards to the private worker; returns exactly 3 tasks from the worker response.
 */
export async function POST(request: Request) {
  if (env.agentBridgeMode !== "worker") {
    return NextResponse.json(
      { error: "worker_bridge_required", detail: "Set AGENT_BRIDGE_MODE=worker for task feedback v2." },
      { status: 501 }
    );
  }
  try {
    const body = taskFeedbackV2Schema.parse(await request.json());
    const workerResult = await submitWorkerTaskFeedbackV2(body);
    const tasks = workerResult.tasks;
    if (!Array.isArray(tasks) || tasks.length !== 3) {
      return NextResponse.json(
        { error: "invalid_worker_tasks", detail: "Worker must return exactly 3 tasks." },
        { status: 502 }
      );
    }
    return NextResponse.json({ tasks });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    const status = error instanceof z.ZodError ? 400 : 502;
    return NextResponse.json({ error: "task_feedback_failed", detail: message }, { status });
  }
}
