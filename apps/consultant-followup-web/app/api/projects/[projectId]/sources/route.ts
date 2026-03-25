import { NextResponse } from "next/server";
import { z } from "zod";

import { jobRequestSchema } from "@/lib/contracts";
import { env, isDirectWorkerEnabled } from "@/lib/env";
import { generateId } from "@/lib/ids";
import { enqueueJobForWorker, saveJob, saveProject } from "@/lib/storage";
import { createWorkerSource } from "@/lib/worker-bridge";

const sourceRequestSchema = z.object({
  label: z.string().min(1),
  source_kind: z.enum(["url", "manual_text", "uploaded_file"]),
  content_text: z.string().min(1),
});

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const payload = await request.json();
    if (!isDirectWorkerEnabled()) {
      const parsed = sourceRequestSchema.parse(payload);
      const submittedAt = new Date().toISOString();
      const jobId = generateId("job");
      const jobRequest = jobRequestSchema.parse({
        job_id: jobId,
        app_id: env.appId,
        project_id: projectId,
        priority_class: "normal",
        job_class: "heavy",
        submitted_at: submittedAt,
        requested_capability: "followup_task_recommendation",
        input_payload: {
          context_type: "working_document",
          prompt: `Analyze this new source (${parsed.label}) and update checklist and workspace cards.`,
          artifacts: [{ type: "upload", ref: "queue_source_submission" }],
        },
        requested_by: "anonymous:queue_sources",
        policy_tags: ["public-demo", "no-auth", env.agentBridgeMode, "source_management_queue"],
      });
      await saveProject({
        projectId,
        sessionId: "queue_sources",
        summary: "managed_on_worker",
        createdAt: submittedAt,
      });
      await saveJob(jobRequest);
      await enqueueJobForWorker(jobRequest, {
        source_kind: parsed.source_kind,
        project_summary: "managed_on_worker",
        raw_text: parsed.content_text,
        source_ref: `managed_source_${generateId("src")}`,
      });
      return NextResponse.json({
        status: "queued",
        detail: "Source received and queued for local worker processing.",
        job_id: jobId,
        project_id: projectId,
      });
    }
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
