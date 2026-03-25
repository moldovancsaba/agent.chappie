import { NextResponse } from "next/server";
import { z } from "zod";

import { recordFactFlashcardAction } from "@/lib/storage";

const bodySchema = z
  .object({
    action: z.enum(["forget", "teach"]),
    teach_note: z.string().optional(),
  })
  .superRefine((row, ctx) => {
    if (row.action === "teach" && !row.teach_note?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Delete and teach requires a short note about what to avoid in the future.",
        path: ["teach_note"],
      });
    }
  });

export async function POST(request: Request, context: { params: Promise<{ projectId: string; factId: string }> }) {
  try {
    const { projectId, factId } = await context.params;
    const body = bodySchema.parse(await request.json());
    await recordFactFlashcardAction(
      projectId,
      factId,
      body.action,
      body.action === "teach" ? body.teach_note : null
    );
    return NextResponse.json({
      status: "recorded",
      project_id: projectId,
      fact_id: factId,
      action: body.action,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown flashcard action error";
    const status = error instanceof z.ZodError ? 400 : 500;
    return NextResponse.json({ error: "fact_flashcard_action_failed", detail }, { status });
  }
}
