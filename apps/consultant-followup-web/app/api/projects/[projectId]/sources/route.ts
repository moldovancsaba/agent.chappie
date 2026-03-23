import { NextResponse } from "next/server";

import { createWorkerSource } from "@/lib/worker-bridge";

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const payload = await request.json();
    const response = await createWorkerSource(projectId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "source_create_failed",
        detail: error instanceof Error ? error.message : "Unknown source create error",
      },
      { status: 400 }
    );
  }
}
