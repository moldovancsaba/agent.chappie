import type { JobRequest, JobResult } from "@/lib/contracts";
import { jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { env } from "@/lib/env";

type SourcePackage = {
  source_kind: "manual_text" | "url" | "uploaded_file";
  project_summary: string;
  raw_text: string;
  source_ref: string;
  file_name?: string;
  content_type?: string;
  content_base64?: string;
};

export type WorkerWorkspacePayload = {
  project_id: string;
  draft_segments: Array<{
    segment_id: string;
    project_id: string;
    segment_kind: string;
    title: string;
    segment_text: string;
    source_refs: string[];
    evidence_refs: string[];
    importance: number;
    confidence: number;
    created_at: string;
    updated_at: string;
  }>;
  fact_chips: Array<{
    fact_id: string;
    category: string;
    label: string;
    confidence: number;
    source_refs: string[];
    evidence_refs: string[];
  }>;
  source_cards: Array<{
    source_ref: string;
    label: string;
    source_kind: string;
    status: string;
    processing_summary: string;
    last_used_in_checklist: boolean;
    signal_count: number;
    key_takeaway: string;
    business_impact: string;
    linked_tasks: string[];
    confidence: number;
    created_at: string;
    preview: string;
  }>;
  knowledge_cards: Array<{
    knowledge_id: string;
    title: string;
    summary: string;
    items: string[];
    insight: string;
    implication: string;
    potential_moves: string[];
    source_refs: string[];
    evidence_refs: string[];
    confidence: number;
    annotation_status: string;
    confidence_source: string;
    audit: {
      original_value: {
        title: string;
        summary: string;
        items: string[];
        insight: string;
        implication: string;
        potential_moves: string[];
      };
      user_modification: {
        title?: string | null;
        summary?: string | null;
        items?: string[] | null;
        implication?: string | null;
        potential_moves?: string[] | null;
      } | null;
      timestamp: string | null;
    };
  }>;
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
  competitive_snapshot: {
    pricing_position: string;
    acquisition_strategy_comparison: string;
    current_weakness?: string;
    active_threats: string[];
    immediate_opportunities: string[];
    reference_competitor: string;
    risk_level?: string;
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
  managed_sources: Array<{
    source_id: string;
    project_id: string;
    label: string;
    source_kind: string;
    content_text: string;
    status: string;
    last_run_at: string | null;
    last_result_status: string | null;
    last_result_summary: string | null;
    created_at: string;
    updated_at: string;
  }>;
  managed_jobs: Array<{
    managed_job_id: string;
    project_id: string;
    name: string;
    trigger_type: string;
    schedule_text: string | null;
    status: string;
    source_id: string | null;
    last_run_at: string | null;
    last_result_status: string | null;
    last_action_summary: string | null;
    last_expected_impact: string | null;
    last_runs: Array<{ at: string; status: string; summary: string }>;
    created_at: string;
    updated_at: string;
  }>;
};

export async function runWorkerJob(input: {
  jobRequest: JobRequest;
  contextNotes: string;
  sourceKind: "manual_text" | "url" | "uploaded_file";
  uploadedFile?: {
    fileName: string;
    contentType: string;
    contentBase64: string;
  };
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
        file_name: input.uploadedFile?.fileName,
        content_type: input.uploadedFile?.contentType,
        content_base64: input.uploadedFile?.contentBase64,
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
      fact_chips: [],
      draft_segments: [],
      competitive_snapshot: {
        pricing_position: "Still forming",
        acquisition_strategy_comparison: "Still forming",
        active_threats: [],
        immediate_opportunities: [],
        reference_competitor: "Comparison set still forming",
      },
      knowledge_summary: [],
      monitor_jobs: [],
      source_cards: [],
      knowledge_cards: [],
      managed_sources: [],
      managed_jobs: [],
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

async function sendWorkerManagementRequest(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  payload: Record<string, unknown>
) {
  if (env.agentBridgeMode === "demo" || !env.agentApiBaseUrl) {
    throw new Error("Worker management is unavailable in demo mode.");
  }

  const response = await fetch(`${env.agentApiBaseUrl.replace(/\/$/, "")}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "x-agent-shared-secret": env.agentSharedSecret ?? "",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail ?? "Worker management request failed.");
  }
  return body;
}

export async function createWorkerSource(
  projectId: string,
  payload: { source_id: string; label: string; source_kind: string; content_text: string; status?: string }
) {
  return sendWorkerManagementRequest(`/projects/${encodeURIComponent(projectId)}/sources`, "POST", payload);
}

export async function updateWorkerSource(projectId: string, sourceId: string, payload: Record<string, unknown>) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}`,
    "PATCH",
    payload
  );
}

export async function deleteWorkerSource(projectId: string, sourceId: string) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}`,
    "DELETE",
    {}
  );
}

export async function createWorkerJob(
  projectId: string,
  payload: {
    managed_job_id: string;
    name: string;
    trigger_type: string;
    schedule_text?: string;
    status?: string;
    source_id?: string;
  }
) {
  return sendWorkerManagementRequest(`/projects/${encodeURIComponent(projectId)}/jobs`, "POST", payload);
}

export async function updateWorkerJob(projectId: string, jobId: string, payload: Record<string, unknown>) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`,
    "PATCH",
    payload
  );
}

export async function deleteWorkerJob(projectId: string, jobId: string) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`,
    "DELETE",
    {}
  );
}

export async function updateWorkerIngestedSource(
  projectId: string,
  sourceRef: string,
  payload: Record<string, unknown>
) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/sources/ingested/${encodeURIComponent(sourceRef)}`,
    "PATCH",
    payload
  );
}

export async function deleteWorkerIngestedSource(projectId: string, sourceRef: string) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/sources/ingested/${encodeURIComponent(sourceRef)}`,
    "DELETE",
    {}
  );
}

export async function updateWorkerKnowledgeCard(
  projectId: string,
  knowledgeId: string,
  payload: Record<string, unknown>
) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(knowledgeId)}`,
    "PATCH",
    payload
  );
}
