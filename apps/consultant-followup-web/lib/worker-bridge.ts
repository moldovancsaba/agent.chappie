import type { JobRequest, JobResult } from "@/lib/contracts";
import { jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { env } from "@/lib/env";

type SourcePackage = {
  source_kind: "manual_text" | "url" | "uploaded_file";
  project_summary: string;
  raw_text: string;
  source_ref: string;
};

export type WorkerWorkspacePayload = {
  project_id: string;
  recent_sources: Array<{
    source_ref: string;
    source_kind: string;
    created_at: string;
    preview: string;
  }>;
  recent_activity: Array<{
    signal_id: string;
    signal_type: string;
    summary: string;
    observed_at: string;
    source_ref: string;
  }>;
  market_summary: {
    pricing_changes: number;
    closure_signals: number;
    offer_signals: number;
  };
  knowledge_summary: Array<{
    competitor: string;
    region: string;
    latest_observed_at: string;
  }>;
  monitor_jobs: Array<{
    job_name: string;
    status: string;
    last_run_at: string | null;
    last_source_ref: string | null;
  }>;
};

export async function runWorkerJob(input: {
  jobRequest: JobRequest;
  contextNotes: string;
  sourceKind: "manual_text" | "url" | "uploaded_file";
}): Promise<JobResult> {
  if (env.agentBridgeMode === "demo" || !env.agentApiBaseUrl) {
    const recommendation = createDemoRecommendation({
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
        source_kind: input.sourceKind,
        project_summary: "managed_on_worker",
        raw_text: input.contextNotes,
        source_ref: `source_${input.jobRequest.job_id}`,
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

export async function fetchWorkerWorkspace(projectId: string): Promise<WorkerWorkspacePayload> {
  if (env.agentBridgeMode === "demo" || !env.agentApiBaseUrl) {
    return {
      project_id: projectId,
      recent_sources: [],
      recent_activity: [],
      market_summary: {
        pricing_changes: 0,
        closure_signals: 0,
        offer_signals: 0,
      },
      knowledge_summary: [],
      monitor_jobs: [],
    };
  }

  const response = await fetch(
    `${env.agentApiBaseUrl.replace(/\/$/, "")}/projects/${encodeURIComponent(projectId)}/workspace`,
    {
      method: "GET",
      headers: {
        "x-agent-shared-secret": env.agentSharedSecret ?? "",
      },
      cache: "no-store",
    }
  );
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Worker bridge failed to return workspace data.");
  }
  return payload as WorkerWorkspacePayload;
}
