import { NextResponse } from "next/server";

import { demoJobSubmissionSchema, jobRequestSchema, jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { env } from "@/lib/env";
import { generateId } from "@/lib/ids";
import { saveJob, saveProject, saveResult } from "@/lib/storage";

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
        prompt: "Recommend the next follow-up tasks for this client project.",
        artifacts: [{ type: "upload", ref: "inline_context_submission" }],
      },
      requested_by: requestedBy,
      policy_tags: ["public-demo", "no-auth"],
    });

    const recommendation = createDemoRecommendation({
      projectSummary: payload.projectSummary,
      contextNotes: payload.contextNotes,
    });

    const jobResult = jobResultSchema.parse({
      job_id: jobId,
      app_id: env.appId,
      project_id: projectId,
      status: "complete",
      completed_at: new Date().toISOString(),
      result_payload: {
        recommended_tasks: recommendation.tasks,
        summary: recommendation.summary,
      },
      decision_summary: {
        route: "proceed",
        confidence: 0.86,
      },
      trace_run_id: "demo-bridge-run",
      trace_refs: ["01_request.json", "05_outcome.json"],
    });

    await saveProject({
      projectId,
      sessionId: payload.sessionId,
      summary: payload.projectSummary,
      createdAt: submittedAt,
    });
    await saveJob(jobRequest);
    await saveResult(jobResult);

    return NextResponse.json({
      scheduler_state: "complete",
      project_id: projectId,
      job_id: jobId,
      job_request: jobRequest,
      result_url: `/api/demo/jobs/${jobId}`,
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
