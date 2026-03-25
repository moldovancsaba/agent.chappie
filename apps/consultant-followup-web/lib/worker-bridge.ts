import type { Feedback, JobRequest, JobResult, RecommendedTask } from "@/lib/contracts";
import { jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { describeDirectWorkerBlock, env, isDirectWorkerEnabled } from "@/lib/env";
import { getLatestJobResultForProject } from "@/lib/storage";

export class DirectWorkerUnavailableError extends Error {
  override readonly name = "DirectWorkerUnavailableError";

  constructor() {
    super(describeDirectWorkerBlock());
  }
}

function buildWorkerBaseUrl(): string {
  const base = env.agentApiBaseUrl?.replace(/\/$/, "") ?? "";
  if (!base) {
    throw new Error(
      "AGENT_API_BASE_URL is not set. Copy apps/consultant-followup-web/.env.example to .env.local and set the worker URL (e.g. http://127.0.0.1:8787)."
    );
  }
  return base;
}

function explainWorkerConnectionFailure(err: unknown): Error {
  const base = env.agentApiBaseUrl ?? "(AGENT_API_BASE_URL unset)";
  const parts: string[] = [];
  if (err instanceof Error) {
    parts.push(err.message);
    if (err.cause instanceof Error) {
      parts.push(err.cause.message);
    }
  } else {
    parts.push(String(err));
  }
  const blob = parts.join(" ").toLowerCase();
  const looksDns =
    blob.includes("enotfound") ||
    blob.includes("getaddrinfo") ||
    blob.includes("name not resolved");
  const looksNetwork =
    blob.includes("fetch failed") ||
    blob.includes("failed to fetch") ||
    blob.includes("econnrefused") ||
    blob.includes("connection refused") ||
    blob.includes("enotfound") ||
    blob.includes("networkerror") ||
    blob.includes("socket") ||
    blob.includes("aborted");
  if (!looksNetwork) {
    return err instanceof Error ? err : new Error(String(err));
  }
  if (looksDns) {
    const tunnelHint =
      base.includes("trycloudflare.com") || base.includes("cfargotunnel.com")
        ? "Cloudflare quick-tunnel hostnames stop resolving when the tunnel process exits; restart cloudflared and set AGENT_API_BASE_URL (e.g. on Vercel) to the new URL."
        : "Confirm the hostname is spelled correctly and still exists (DNS / tunnel still running).";
    return new Error(
      [
        `DNS could not resolve the worker host in ${base}.`,
        tunnelHint,
        "Job enqueue may still work via the DB queue if configured; routes that load workspace or call the worker API directly need a reachable AGENT_API_BASE_URL.",
        `Technical detail: ${parts.join(" — ")}`,
      ].join(" ")
    );
  }
  return new Error(
    [
      `The app cannot reach the private worker at ${base}.`,
      "Start the worker from the Agent.Chappie repo root:",
      "  source .venv/bin/activate && python scripts/worker_bridge.py",
      "Ensure AGENT_SHARED_SECRET matches in the worker process and in apps/consultant-followup-web/.env.local.",
      `Technical detail: ${parts.join(" — ")}`,
    ].join(" ")
  );
}

async function workerFetch(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, { ...init, cache: "no-store" });
  } catch (err) {
    throw explainWorkerConnectionFailure(err);
  }
}

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
    support_count?: number;
    strongest_excerpt?: string | null;
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

function synthesizeWorkspaceFromJobResult(projectId: string, result: JobResult): WorkerWorkspacePayload {
  const base = normalizeWorkerWorkspacePayload({ project_id: projectId });
  if (
    result.status !== "complete" ||
    typeof result.result_payload !== "object" ||
    result.result_payload === null ||
    !("recommended_tasks" in result.result_payload) ||
    !Array.isArray(result.result_payload.recommended_tasks)
  ) {
    return base;
  }
  const tasks = result.result_payload.recommended_tasks as RecommendedTask[];
  const summary =
    "summary" in result.result_payload && typeof result.result_payload.summary === "string"
      ? result.result_payload.summary
      : "";
  const factChips = tasks.slice(0, 6).map((task) => ({
    fact_id: `from_task_${task.rank}`,
    category: "checklist",
    label: task.title.length > 160 ? `${task.title.slice(0, 157)}…` : task.title,
    confidence: 0.72,
    source_refs: task.evidence_refs ?? [],
    evidence_refs: task.evidence_refs ?? [],
  }));
  const refs = new Set<string>();
  for (const task of tasks) {
    for (const ref of task.evidence_refs ?? []) {
      refs.add(ref);
    }
  }
  const recent_sources = [...refs].slice(0, 12).map((source_ref) => ({
    source_ref,
    source_kind: "manual_text",
    created_at: result.completed_at,
    preview: source_ref.length > 80 ? `${source_ref.slice(0, 77)}…` : source_ref,
  }));
  return normalizeWorkerWorkspacePayload({
    project_id: projectId,
    fact_chips: factChips,
    recent_sources,
    competitive_snapshot: {
      ...base.competitive_snapshot,
      pricing_position: summary.slice(0, 280) || base.competitive_snapshot.pricing_position,
    },
  });
}

export function normalizeWorkerWorkspacePayload(payload: Partial<WorkerWorkspacePayload> & { project_id: string }): WorkerWorkspacePayload {
  return {
    project_id: payload.project_id,
    recent_sources: payload.recent_sources ?? [],
    recent_activity: payload.recent_activity ?? [],
    market_summary: payload.market_summary ?? {
      pricing_changes: 0,
      closure_signals: 0,
      offer_signals: 0,
    },
    fact_chips: payload.fact_chips ?? [],
    draft_segments: payload.draft_segments ?? [],
    competitive_snapshot: payload.competitive_snapshot ?? {
      pricing_position: "Still forming",
      acquisition_strategy_comparison: "Still forming",
      active_threats: [],
      immediate_opportunities: [],
      reference_competitor: "Comparison set still forming",
    },
    knowledge_summary: payload.knowledge_summary ?? [],
    monitor_jobs: payload.monitor_jobs ?? [],
    source_cards: payload.source_cards ?? [],
    knowledge_cards: payload.knowledge_cards ?? [],
    managed_sources: payload.managed_sources ?? [],
    managed_jobs: payload.managed_jobs ?? [],
  };
}

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
  if (!isDirectWorkerEnabled()) {
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

  const response = await workerFetch(`${buildWorkerBaseUrl()}/jobs`, {
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
  });
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.detail ?? payload.error ?? "Worker bridge failed to return a result.";
    if (response.status === 401) {
      throw new Error(
        `Worker returned 401 (unauthorized). Set AGENT_SHARED_SECRET in apps/consultant-followup-web/.env.local to match the worker (same value as when starting worker_bridge.py). ${detail}`
      );
    }
    throw new Error(detail);
  }
  return jobResultSchema.parse(payload.job_result);
}

export async function fetchWorkerWorkspace(projectId: string): Promise<WorkerWorkspacePayload> {
  if (!isDirectWorkerEnabled()) {
    const stored = await getLatestJobResultForProject(projectId);
    if (stored) {
      return synthesizeWorkspaceFromJobResult(projectId, stored);
    }
    return normalizeWorkerWorkspacePayload({
      project_id: projectId,
    });
  }

  const response = await workerFetch(
    `${buildWorkerBaseUrl()}/projects/${encodeURIComponent(projectId)}/workspace`,
    {
      method: "GET",
      headers: {
        "x-agent-shared-secret": env.agentSharedSecret ?? "",
      },
    }
  );
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Worker bridge failed to return workspace data.");
  }
  return normalizeWorkerWorkspacePayload(payload as Partial<WorkerWorkspacePayload> & { project_id: string });
}

export async function regenerateWorkerChecklist(input: {
  projectId: string;
  jobId: string;
  appId: string;
}): Promise<JobResult> {
  if (!isDirectWorkerEnabled()) {
    throw new Error("Checklist regeneration needs a direct Mac worker (AGENT_BRIDGE_MODE=worker and AGENT_API_BASE_URL).");
  }

  const response = await workerFetch(
    `${buildWorkerBaseUrl()}/projects/${encodeURIComponent(input.projectId)}/checklist`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-agent-shared-secret": env.agentSharedSecret ?? "",
      },
      body: JSON.stringify({
        job_id: input.jobId,
        app_id: input.appId,
      }),
    }
  );
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "Worker checklist regeneration failed.");
  }
  return jobResultSchema.parse(payload.job_result);
}

async function sendWorkerManagementRequest(
  path: string,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  payload: Record<string, unknown> = {}
) {
  if (!isDirectWorkerEnabled()) {
    throw new DirectWorkerUnavailableError();
  }

  const headers: Record<string, string> = {
    "x-agent-shared-secret": env.agentSharedSecret ?? "",
  };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
  }
  const response = await workerFetch(`${buildWorkerBaseUrl()}${path}`, {
    method,
    headers,
    body: method === "GET" ? undefined : JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const detail = body.detail ?? body.error ?? "Worker management request failed.";
    if (response.status === 401) {
      throw new Error(
        `Worker returned 401. AGENT_SHARED_SECRET in .env.local must match the running worker. ${detail}`
      );
    }
    throw new Error(detail);
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

export async function deleteWorkerKnowledgeCard(
  projectId: string,
  knowledgeId: string,
  payload: Record<string, unknown>
) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(knowledgeId)}`,
    "DELETE",
    payload
  );
}

export async function deleteWorkerDraftSegment(
  projectId: string,
  segmentId: string,
  payload: Record<string, unknown>
) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/draft-segments/${encodeURIComponent(segmentId)}`,
    "DELETE",
    payload
  );
}

export async function submitWorkerTaskFeedback(projectId: string, payload: Feedback) {
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/task-feedback`,
    "POST",
    payload as unknown as Record<string, unknown>
  );
}

/** Phase 8 / feedback_v2 — same shape as `docs/09_contracts/feedback_v2.md` task payload. */
export type TaskFeedbackV2Payload = {
  project_id: string;
  task_id: string;
  action_type:
    | "done"
    | "edit"
    | "decline_and_replace"
    | "delete_only"
    | "delete_and_teach"
    | "hold_for_later";
  comment?: string;
  edited_title?: string;
};

export type TaskFeedbackV2Response = {
  tasks: unknown[];
  job_id?: string;
  job_result?: unknown;
  workspace?: unknown;
};

export async function submitWorkerTaskFeedbackV2(
  payload: TaskFeedbackV2Payload
): Promise<TaskFeedbackV2Response> {
  const projectId = payload.project_id;
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/tasks/feedback`,
    "POST",
    payload as unknown as Record<string, unknown>
  ) as Promise<TaskFeedbackV2Response>;
}

// ── Generation Memory Management ────────────────────────────────────────────

export type GenerationMemoryRow = {
  memory_id: string;
  project_id: string;
  memory_kind: string;
  pattern_key: string;
  signal_value: string | null;
  weight: number;
  source_feedback_id: string | null;
  created_at: string;
  updated_at: string;
};

export async function getWorkerGenerationMemory(
  projectId: string
): Promise<{ generation_memory: GenerationMemoryRow[]; count: number }> {
  const result = await sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/generation-memory`,
    "GET"
  );
  return result as { generation_memory: GenerationMemoryRow[]; count: number };
}

export async function deleteWorkerGenerationMemoryRow(
  projectId: string,
  memoryId: string
): Promise<{ deleted: boolean; memory_id: string }> {
  const result = await sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/generation-memory/${encodeURIComponent(memoryId)}`,
    "DELETE"
  );
  return result as { deleted: boolean; memory_id: string };
}

export async function clearWorkerGenerationMemory(
  projectId: string
): Promise<{ cleared: boolean; rows_removed: number }> {
  const result = await sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/generation-memory`,
    "DELETE"
  );
  return result as { cleared: boolean; rows_removed: number };
}

// ── Held Tasks Management ────────────────────────────────────────────────────

export type HeldTask = {
  held_task_id: string;
  project_id: string;
  original_title: string;
  original_rank: number | null;
  held_at: string;
  status: string;
};

export async function getWorkerHeldTasks(
  projectId: string
): Promise<{ held_tasks: HeldTask[]; count: number }> {
  const result = await sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/held-tasks`,
    "GET"
  );
  return result as { held_tasks: HeldTask[]; count: number };
}

export async function restoreWorkerHeldTask(
  projectId: string,
  heldTaskId: string
): Promise<{ restored: boolean }> {
  const result = await sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/held-tasks/restore`,
    "POST",
    { held_task_id: heldTaskId }
  );
  return result as { restored: boolean };
}
