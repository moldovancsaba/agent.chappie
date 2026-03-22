import type { JobRequest, JobResult } from "@/lib/contracts";
import { jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { env } from "@/lib/env";

type SourcePackage = {
  source_kind: "manual_text";
  project_summary: string;
  raw_text: string;
  source_ref: string;
  competitor?: string;
  region?: string;
};

export async function runWorkerJob(input: {
  jobRequest: JobRequest;
  projectSummary: string;
  contextNotes: string;
  competitor?: string;
  region?: string;
}): Promise<JobResult> {
  if (env.agentBridgeMode === "demo" || !env.agentApiBaseUrl) {
    const recommendation = createDemoRecommendation({
      projectSummary: input.projectSummary,
      contextNotes: input.contextNotes,
    });
    return jobResultSchema.parse({
      job_id: input.jobRequest.job_id,
      app_id: input.jobRequest.app_id,
      project_id: input.jobRequest.project_id,
      status: "complete",
      completed_at: new Date().toISOString(),
      result_payload: {
        recommended_tasks: recommendation.tasks,
        summary: recommendation.summary,
      },
      decision_summary: {
        route: "proceed",
        confidence: 0.51,
      },
      trace_run_id: "demo-worker-bridge",
      trace_refs: recommendation.tasks.flatMap((task) => task.evidence_refs),
    });
  }

  const response = await fetch(`${env.agentApiBaseUrl.replace(/\/$/, "")}/jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-agent-shared-secret": env.agentSharedSecret ?? "",
    },
    body: JSON.stringify({
      job_request: input.jobRequest,
      source_package: {
        source_kind: "manual_text",
        project_summary: input.projectSummary,
        raw_text: input.contextNotes,
        source_ref: `source_${input.jobRequest.job_id}`,
        competitor: input.competitor,
        region: input.region,
      } satisfies SourcePackage,
    }),
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Worker bridge failed to return a result.");
  }
  return jobResultSchema.parse(payload.job_result);
}
