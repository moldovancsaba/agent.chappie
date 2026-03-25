import { NextResponse } from "next/server";
import { z } from "zod";

import { env } from "@/lib/env";
import { saveWorkspaceSnapshot } from "@/lib/storage";

const payloadSchema = z.object({
  workspace: z.record(z.string(), z.unknown()),
});

function isAuthorized(request: Request) {
  const expected = env.workerQueueSecret ?? "";
  const provided = request.headers.get("x-agent-worker-secret") ?? "";
  return Boolean(expected) && provided === expected;
}

/**
 * Worker callback: push the latest project workspace snapshot
 * so hosted queue mode can render Know More / Sources views.
 */
export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const { projectId } = await context.params;
    const body = payloadSchema.parse(await request.json());
    const payloadProjectId = String(body.workspace.project_id ?? "");
    if (payloadProjectId && payloadProjectId !== projectId) {
      return NextResponse.json(
        { error: "project_id_mismatch", detail: "workspace.project_id must match URL projectId." },
        { status: 400 }
      );
    }
    await saveWorkspaceSnapshot(projectId, body.workspace);
    return NextResponse.json({ status: "saved", project_id: projectId });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown workspace sync error";
    const status = error instanceof z.ZodError ? 400 : 500;
    return NextResponse.json({ error: "workspace_sync_failed", detail }, { status });
  }
}
