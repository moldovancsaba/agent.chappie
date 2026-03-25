import { NextResponse } from "next/server";
import { z } from "zod";

import { jobRequestSchema } from "@/lib/contracts";
import { env, isDirectWorkerEnabled } from "@/lib/env";
import { generateId } from "@/lib/ids";
import { enqueueJobForWorker, saveJob, saveProject } from "@/lib/storage";
import { createWorkerSource } from "@/lib/worker-bridge";

const sourceRequestSchema = z
  .object({
    label: z.string().min(1),
    source_kind: z.enum(["url", "manual_text", "uploaded_file"]),
    repeat_interval: z.enum(["never", "daily", "weekly", "monthly", "quarterly", "yearly"]).default("never"),
    repeat_anchor_at: z.string().min(1).optional(),
    content_text: z.string().min(1),
    file_name: z.string().min(1).optional(),
    content_type: z.string().min(1).optional(),
    content_base64: z.string().min(1).optional(),
  })
  .superRefine((row, ctx) => {
    if (row.source_kind === "uploaded_file" && !row.content_base64?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Document source requires file bytes. Use multipart upload (field \"file\") or send content_base64.",
        path: ["content_base64"],
      });
    }
  });

async function enqueueQueuedSource(
  projectId: string,
  parsed: z.infer<typeof sourceRequestSchema>
) {
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
    file_name: parsed.file_name,
    content_type: parsed.content_type,
    content_base64: parsed.content_base64,
  });
  return { jobId, submittedAt };
}

export async function POST(request: Request, context: { params: Promise<{ projectId: string }> }) {
  try {
    const { projectId } = await context.params;
    const contentType = request.headers.get("content-type") ?? "";
    if (!isDirectWorkerEnabled()) {
      if (contentType.includes("multipart/form-data")) {
        const form = await request.formData();
        const sourceKind = z.enum(["url", "manual_text", "uploaded_file"]).parse(String(form.get("source_kind") ?? ""));
        const repeatInterval = z
          .enum(["never", "daily", "weekly", "monthly", "quarterly", "yearly"])
          .catch("never")
          .parse(String(form.get("repeat_interval") ?? "never"));
        const labelRaw = String(form.get("label") ?? "").trim();
        const contentTextRaw = String(form.get("content_text") ?? "").trim();
        const file = form.get("file");

        let contentBase64: string | undefined;
        let fileName: string | undefined;
        let mimeType: string | undefined;
        let contentText = contentTextRaw;

        if (sourceKind === "uploaded_file") {
          if (!(file instanceof File)) {
            throw new Error("Choose a file for document source, or use Notes / URL mode.");
          }
          const buffer = Buffer.from(await file.arrayBuffer());
          if (buffer.length === 0) {
            throw new Error("Uploaded file is empty.");
          }
          contentBase64 = buffer.toString("base64");
          fileName = file.name;
          mimeType = file.type || "application/octet-stream";
          if (!contentText) {
            contentText = fileName;
          }
        }

        const label = labelRaw || (sourceKind === "uploaded_file" ? "Document source" : contentText.slice(0, 80) || "Source");
        const parsed = sourceRequestSchema.parse({
          label,
          source_kind: sourceKind,
          repeat_interval: repeatInterval,
          repeat_anchor_at: String(form.get("repeat_anchor_at") ?? "").trim() || undefined,
          content_text: contentText || label,
          file_name: fileName,
          content_type: mimeType,
          content_base64: contentBase64,
        });
        const { jobId } = await enqueueQueuedSource(projectId, parsed);
        return NextResponse.json({
          status: "queued",
          detail: "Source received and queued for local worker processing.",
          job_id: jobId,
          project_id: projectId,
        });
      }

      const payload = await request.json();
      const parsed = sourceRequestSchema.parse(payload);
      const { jobId } = await enqueueQueuedSource(projectId, parsed);
      return NextResponse.json({
        status: "queued",
        detail: "Source received and queued for local worker processing.",
        job_id: jobId,
        project_id: projectId,
      });
    }
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
