import { NextResponse } from "next/server";

import { fetchWorkerWorkspace } from "@/lib/worker-bridge";

export const dynamic = "force-dynamic";

export async function GET(_: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const workspace = await fetchWorkerWorkspace(projectId);
    return NextResponse.json(workspace);
  } catch (error) {
    return NextResponse.json(
      {
        error: "workspace_fetch_failed",
        detail: error instanceof Error ? error.message : "Unknown workspace error",
      },
      { status: 400 }
    );
  }
}
