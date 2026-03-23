import { NextResponse } from "next/server";

import { demoJobSubmissionSchema, jobRequestSchema } from "@/lib/contracts";
import { env } from "@/lib/env";
import { generateId } from "@/lib/ids";
import { saveJob, saveProject, saveResult } from "@/lib/storage";
import { runWorkerJob } from "@/lib/worker-bridge";

export async function POST(request: Request) {
  try {
    const payload = demoJobSubmissionSchema.parse(await request.json());
    const projectId = payload.projectId ?? generateId("demo_project");
    const jobId = generateId("job");
    const submittedAt = new Date().toISOString();
    const requestedBy = `anonymous:${payload.sessionId}`;

    const jobRequest = jobRequestSchema.parse({
      job_id: jobId,
      app_id: env.appId,
      project_id: projectId,
      priority_class: "normal",
      job_class: "heavy",
      submitted_at: submittedAt,
      requested_capability: "followup_task_recommendation",
      input_payload: {
        context_type: payload.contextType,
        prompt: "Identify competitive signals and return exactly 3 actionable follow-up tasks.",
        artifacts: [{ type: "upload", ref: "inline_context_submission" }],
      },
      requested_by: requestedBy,
      policy_tags: ["public-demo", "no-auth", env.agentBridgeMode],
    });

    await saveProject({
      projectId,
      sessionId: payload.sessionId,
      summary: "managed_on_worker",
      createdAt: submittedAt,
    });
    await saveJob(jobRequest);

    const jobResult = await runWorkerJob({
      jobRequest,
      contextNotes: payload.contextNotes,
      sourceKind: payload.sourceKind,
    });

    await saveResult(jobResult);

    return NextResponse.json({
      scheduler_state: jobResult.status === "complete" ? "complete" : "blocked",
      project_id: projectId,
      job_id: jobId,
      job_request: jobRequest,
      result_url: `/api/jobs/${jobId}`,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "job_submission_failed",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 400 }
    );
  }
}
