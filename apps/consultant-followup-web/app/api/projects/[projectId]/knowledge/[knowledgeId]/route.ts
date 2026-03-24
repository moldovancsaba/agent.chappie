import { NextResponse } from "next/server";

import { deleteWorkerKnowledgeCard, updateWorkerKnowledgeCard } from "@/lib/worker-bridge";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ projectId: string; knowledgeId: string }> }
) {
  try {
    const { projectId, knowledgeId } = await context.params;
    const payload = await request.json();
    const response = await updateWorkerKnowledgeCard(projectId, knowledgeId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "knowledge_update_failed",
        detail: error instanceof Error ? error.message : "Unknown knowledge update error",
      },
      { status: 400 }
    );
  }
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ projectId: string; knowledgeId: string }> }
) {
  try {
    const { projectId, knowledgeId } = await context.params;
    const payload = await request.json().catch(() => ({}));
    const response = await deleteWorkerKnowledgeCard(projectId, knowledgeId, payload);
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json(
      {
        error: "knowledge_delete_failed",
        detail: error instanceof Error ? error.message : "Unknown knowledge delete error",
      },
      { status: 400 }
    );
  }
}
