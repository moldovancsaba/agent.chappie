import type { Feedback, JobRequest, JobResult, RecommendedTask } from "@/lib/contracts";
import { jobResultSchema } from "@/lib/contracts";
import { createDemoRecommendation } from "@/lib/demo-worker";
import { describeDirectWorkerBlock, env, isDirectWorkerEnabled } from "@/lib/env";
import type { PendingQueueJobRow } from "@/lib/storage";
import {
  canUseNeon,
  filterWorkspaceHiddenFactChips,
  getLatestJobResultForProject,
  getWorkspaceSnapshot,
  listPendingQueueJobsForProject,
  removeQueuedJobById,
  saveResult,
  saveWorkspaceSnapshot,
} from "@/lib/storage";

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

export type IntelligenceCardRow = {
  card_id: string;
  project_id: string;
  insight: string;
  implication: string;
  potential_moves: string[];
  fact_refs: string[];
  source_refs: string[];
  segment: string;
  competitor?: string | null;
  channel?: string | null;
  state: string;
  expires_at?: string | null;
  confidence: number;
  impact_score: number;
  freshness_score: number;
  evidence_strength: number;
  rank_score: number;
  quarantine_reason?: string | null;
  gate_flags?: string[];
};

export type FlashcardPipelineRunSummary = {
  run_id: string;
  job_id: string;
  project_id: string;
  pipeline_source: string;
  reason: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type WorkerWorkspacePayload = {
  project_id: string;
  intelligence_cards: IntelligenceCardRow[];
  visible_intelligence_cards: IntelligenceCardRow[];
  latest_flashcard_pipeline_run?: FlashcardPipelineRunSummary | null;
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
    repeat_interval: "never" | "daily" | "weekly" | "monthly" | "quarterly" | "yearly";
    repeat_anchor_at: string | null;
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

function workspaceSnapshotHasRenderableData(payload: WorkerWorkspacePayload): boolean {
  return (
    (payload.fact_chips?.length ?? 0) > 0 ||
    (payload.source_cards?.length ?? 0) > 0 ||
    (payload.visible_intelligence_cards?.length ?? 0) > 0 ||
    (payload.intelligence_cards?.length ?? 0) > 0 ||
    (payload.knowledge_cards?.length ?? 0) > 0 ||
    (payload.recent_sources?.length ?? 0) > 0 ||
    (payload.recent_activity?.length ?? 0) > 0 ||
    (payload.draft_segments?.length ?? 0) > 0
  );
}

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
    for (const ref of task.supporting_source_refs ?? []) {
      refs.add(ref);
    }
  }
  const recent_sources = [...refs].slice(0, 12).map((source_ref) => ({
    source_ref,
    source_kind: "manual_text",
    created_at: result.completed_at,
    preview: source_ref.length > 80 ? `${source_ref.slice(0, 77)}…` : source_ref,
  }));
  const linkedTaskTitles = tasks.map((t) => t.title);
  const source_cards = recent_sources.map((rs) => ({
    source_ref: rs.source_ref,
    label: rs.preview.length > 100 ? `${rs.preview.slice(0, 97)}…` : rs.preview,
    source_kind: rs.source_kind,
    status: "referenced",
    processing_summary: "Linked from the latest checklist as supporting evidence.",
    last_used_in_checklist: true,
    signal_count: 0,
    key_takeaway: "This source was cited when drafting the recommended moves.",
    business_impact: "It shaped the current checklist recommendations.",
    linked_tasks: linkedTaskTitles,
    confidence: 0.65,
    created_at: rs.created_at,
    preview: rs.preview,
  }));
  const recent_activity = tasks.slice(0, 6).map((task) => ({
    signal_id: `checklist_task_${task.rank}`,
    signal_type: "checklist_support",
    summary: task.title.length > 120 ? `${task.title.slice(0, 117)}…` : task.title,
    observed_at: result.completed_at,
    source_ref: (task.evidence_refs ?? [])[0] ?? (task.supporting_source_refs ?? [])[0] ?? "synthetic",
  }));
  return normalizeWorkerWorkspacePayload({
    project_id: projectId,
    fact_chips: factChips,
    recent_sources,
    source_cards,
    recent_activity,
  });
}

function synthesizeWorkspaceFromPendingQueueJobs(
  projectId: string,
  pending: PendingQueueJobRow[],
): WorkerWorkspacePayload {
  if (!pending.length) {
    return normalizeWorkerWorkspacePayload({ project_id: projectId });
  }
  const source_cards = pending.map((row) => {
    const pkg = row.source_package;
    const label =
      pkg.file_name?.trim() ||
      (pkg.raw_text?.trim().length
        ? pkg.raw_text.trim().length > 72
          ? `${pkg.raw_text.trim().slice(0, 69)}…`
          : pkg.raw_text.trim()
        : pkg.source_ref);
    const preview =
      pkg.source_kind === "uploaded_file" && pkg.file_name
        ? `Queued upload: ${pkg.file_name}`
        : (pkg.raw_text || "").slice(0, 220);
    const processing_summary =
      row.status === "processing"
        ? "The worker claimed this job. Full intelligence cards and three tasks appear when processing finishes."
        : "Waiting for the private Mac worker to claim this job from the cloud queue. On the Mac: run scripts/install_services.sh (launchd) or zsh scripts/run_queue_consumer.sh with APP_QUEUE_BASE_URL and WORKER_QUEUE_SHARED_SECRET in .env.queue.";
    return {
      source_ref: `queue_job:${row.job_id}`,
      label,
      source_kind: pkg.source_kind,
      status: row.status === "processing" ? "processing_on_worker" : "queued_for_worker",
      processing_summary,
      last_used_in_checklist: false,
      signal_count: 0,
      key_takeaway: `Job ${row.job_id.slice(0, 8)}… is ${row.status === "processing" ? "running on the worker" : "in the queue"}.`,
      business_impact: "No competitive tasks or Know More flashcards until the worker completes this job.",
      linked_tasks: [],
      confidence: 0.5,
      created_at: row.created_at,
      preview: preview || label,
    };
  });
  const recent_sources = pending.map((row) => {
    const pkg = row.source_package;
    const preview =
      pkg.source_kind === "uploaded_file" && pkg.file_name
        ? `Queued file: ${pkg.file_name}`
        : (pkg.raw_text || "").slice(0, 120);
    return {
      source_ref: `queue_job:${row.job_id}`,
      source_kind: pkg.source_kind,
      created_at: row.created_at,
      preview: preview || row.job_id,
    };
  });
  const recent_activity = pending.map((row) => ({
    signal_id: `queue_wait:${row.job_id}`,
    signal_type: row.status === "processing" ? "worker_processing" : "queue_waiting",
    summary:
      row.status === "processing"
        ? `Worker processing job ${row.job_id.slice(0, 8)}…`
        : `Source submitted; job ${row.job_id.slice(0, 8)}… waiting for worker to claim.`,
    observed_at: row.created_at,
    source_ref: `queue_job:${row.job_id}`,
  }));
  return normalizeWorkerWorkspacePayload({
    project_id: projectId,
    source_cards,
    recent_sources,
    recent_activity,
  });
}

type WorkspaceKnowledgeCard = WorkerWorkspacePayload["knowledge_cards"][number];

/** Neon / older worker snapshots sometimes persist debug-style key=value insight lines. */
function looksLikeLegacyKnowledgeKvCopy(text: string | undefined): boolean {
  if (!text?.trim()) {
    return false;
  }
  const s = text;
  if (s.includes("knowledge_id=")) {
    return true;
  }
  if (/\bprimary_kind=/.test(s)) {
    return true;
  }
  if (/\btop_unit_kind=/.test(s)) {
    return true;
  }
  if (/\bcluster_size=/.test(s)) {
    return true;
  }
  if (/\bn_units=/.test(s)) {
    return true;
  }
  if (/\bn_facts=/.test(s)) {
    return true;
  }
  if (/\bsample=/.test(s)) {
    return true;
  }
  if (/\bn=\d+/.test(s) && (s.includes(" · ") || s.includes("knowledge_id"))) {
    return true;
  }
  return false;
}

function firstIntMatch(text: string, pattern: RegExp): number | null {
  const m = text.match(pattern);
  if (!m) {
    return null;
  }
  const n = parseInt(m[1] ?? "", 10);
  return Number.isFinite(n) ? n : null;
}

function legacySanitizedInsightImplication(card: WorkspaceKnowledgeCard): { insight: string; implication: string } {
  const rawInsight = String(card.insight ?? "");
  const rawImpl = String(card.implication ?? "");
  const insightBad = looksLikeLegacyKnowledgeKvCopy(rawInsight);
  const implBad = looksLikeLegacyKnowledgeKvCopy(rawImpl);
  if (!insightBad && !implBad) {
    return { insight: rawInsight, implication: rawImpl };
  }

  const blob = `${rawInsight} ${rawImpl}`;
  const nUnits = firstIntMatch(blob, /\bn_units=(\d+)/);
  const nCompetitors = firstIntMatch(blob, /\bn=(\d+)/);
  const nFacts = firstIntMatch(blob, /\bn_facts=(\d+)/);
  const sampleMatch = blob.match(/\bsample=([^·]+)/);
  const sampleRaw = sampleMatch ? sampleMatch[1].trim() : "";
  const sample = sampleRaw.length > 120 ? `${sampleRaw.slice(0, 120)}…` : sampleRaw;

  let insight = rawInsight;
  let implication = rawImpl;
  const id = card.knowledge_id;

  if (id === "market_summary") {
    if (insightBad) {
      insight =
        nUnits != null
          ? `We're holding ${nUnits} related evidence line(s) from your sources under this market read. Open the strongest excerpt to sanity-check the framing.`
          : "Your sources contributed material to this market summary; the on-card narrative was saved in an older format. Re-sync from the latest worker for refreshed wording.";
    }
    if (implBad) {
      implication =
        "Use this as a working read of what the ingested text emphasizes—not a final judgment. Buyers compare what they can see; align your site and talk track with those comparisons.";
    }
  } else if (id === "competitors_detected") {
    if (insightBad) {
      if (nCompetitors != null && sample) {
        insight = `We picked up ${nCompetitors} named competitor candidate(s). Strongest surface signals include ${sample}.`;
      } else if (nCompetitors != null) {
        insight = `We picked up ${nCompetitors} named competitor candidate(s) from this material. Verify names against your own list before acting.`;
      } else {
        insight =
          "Named competitor candidates were detected from your sources; re-sync from the latest worker for a fuller narrative.";
      }
    }
    if (implBad) {
      implication = "Treat this as a draft list to verify; wrong names create wrong tasks downstream.";
    }
  } else if (id === "pricing_packaging") {
    if (insightBad) {
      insight =
        nUnits != null
          ? `Pricing and packaging language shows up in ${nUnits} evidence line(s) from this ingest.`
          : "Pricing or packaging signals were captured; the on-card narrative was saved in an older format. Re-sync from the latest worker for refreshed wording.";
    }
    if (implBad) {
      implication =
        nFacts != null
          ? `We surfaced ${nFacts} concrete pricing or packaging point(s)—buyers will compare numbers and packaging in the wild.`
          : "Buyers will compare numbers and packaging—make sure your story matches what they see in the wild.";
    }
  } else {
    if (insightBad) {
      insight =
        "This card was stored in an older debug format. Re-run processing or re-sync from an updated worker to restore operator-facing copy.";
    }
    if (implBad) {
      implication = "Verify against your sources before acting; refresh this workspace from the worker when convenient.";
    }
  }

  return { insight, implication };
}

function stripLegacyPotentialMoveRowPrefix(move: string): string {
  return move.replace(/^\s*row\[\d+\]\s*=\s*/i, "").trim();
}

const GENERIC_COMPETITOR_POTENTIAL_MOVES = [
  "Verify each extracted name against who you actually compete with.",
  "Map one rival to a page you control so comparisons stay fair.",
  "Decline or teach any name the system got wrong.",
];

const GENERIC_KNOWLEDGE_POTENTIAL_MOVES = [
  "Check this read against your live site and what prospects say on recent calls.",
  "If it is wrong, use Decline and teach so the system learns your market.",
  "Pick one concrete homepage or pricing tweak to test against this pattern.",
];

function looksLikeInternalPotentialMoveDebug(s: string): boolean {
  const t = s.toLowerCase();
  if (t.includes("unit_kind=")) {
    return true;
  }
  if (t.includes("source_ref=") || t.includes("auto_source_")) {
    return true;
  }
  if (t.includes("gap=") && t.includes("status=")) {
    return true;
  }
  if (/\b\w+_ref\s*=/.test(t)) {
    return true;
  }
  return false;
}

function sanitizePotentialMovesForDisplay(moves: string[], knowledgeId: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  let sawRowPrefix = false;
  for (const m of moves) {
    const raw = String(m).trim();
    if (/^\s*row\[\d+\]\s*=/i.test(raw)) {
      sawRowPrefix = true;
    }
    if (looksLikeInternalPotentialMoveDebug(raw)) {
      continue;
    }
    const s = stripLegacyPotentialMoveRowPrefix(raw);
    if (!s || looksLikeInternalPotentialMoveDebug(s)) {
      continue;
    }
    const k = s.toLowerCase();
    if (seen.has(k)) {
      continue;
    }
    seen.add(k);
    out.push(s);
    if (out.length >= 3) {
      break;
    }
  }
  if (out.length > 0) {
    return out;
  }
  if (sawRowPrefix && knowledgeId === "competitors_detected") {
    return GENERIC_COMPETITOR_POTENTIAL_MOVES.slice(0, 3);
  }
  if (moves.some((m) => looksLikeInternalPotentialMoveDebug(String(m)))) {
    return knowledgeId === "competitors_detected"
      ? GENERIC_COMPETITOR_POTENTIAL_MOVES.slice(0, 3)
      : GENERIC_KNOWLEDGE_POTENTIAL_MOVES.slice(0, 3);
  }
  return moves;
}

/** Competitor cards sometimes picked auto-research legal blogs; hide clearly wrong excerpts client-side. */
function sanitizeStrongestExcerptForDisplay(card: WorkspaceKnowledgeCard): string | null | undefined {
  const ex = card.strongest_excerpt;
  if (!ex || card.knowledge_id !== "competitors_detected") {
    return ex;
  }
  if (
    /\bhearsay\b/i.test(ex) ||
    /\bnontestimonial\b/i.test(ex) ||
    /\brule\s+80[12]\b/i.test(ex) ||
    /pumphreylawfirm\.com/i.test(ex)
  ) {
    return null;
  }
  return ex;
}

function sanitizeKnowledgeCardDisplay(card: WorkspaceKnowledgeCard): WorkspaceKnowledgeCard {
  const { insight, implication } = legacySanitizedInsightImplication(card);
  const pmIn = card.potential_moves ?? [];
  const potential_moves = sanitizePotentialMovesForDisplay(pmIn, card.knowledge_id);
  const strongest_excerpt = sanitizeStrongestExcerptForDisplay(card);

  const pmChanged = JSON.stringify(potential_moves) !== JSON.stringify(pmIn);
  const exChanged = strongest_excerpt !== card.strongest_excerpt;

  if (insight === card.insight && implication === card.implication && !pmChanged && !exChanged) {
    return card;
  }
  return { ...card, insight, implication, potential_moves, strongest_excerpt };
}

function sanitizeKnowledgeCardsForDisplay(cards: WorkspaceKnowledgeCard[]): WorkspaceKnowledgeCard[] {
  return cards.map((card) => sanitizeKnowledgeCardDisplay(card));
}

export function normalizeWorkerWorkspacePayload(payload: Partial<WorkerWorkspacePayload> & { project_id: string }): WorkerWorkspacePayload {
  return {
    project_id: payload.project_id,
    intelligence_cards: payload.intelligence_cards ?? [],
    visible_intelligence_cards: payload.visible_intelligence_cards ?? [],
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
      pricing_position: "",
      acquisition_strategy_comparison: "",
      active_threats: [],
      immediate_opportunities: [],
      reference_competitor: "",
    },
    knowledge_summary: payload.knowledge_summary ?? [],
    monitor_jobs: payload.monitor_jobs ?? [],
    source_cards: payload.source_cards ?? [],
    knowledge_cards: sanitizeKnowledgeCardsForDisplay(payload.knowledge_cards ?? []),
    managed_sources: payload.managed_sources ?? [],
    managed_jobs: payload.managed_jobs ?? [],
    latest_flashcard_pipeline_run: payload.latest_flashcard_pipeline_run ?? null,
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
    const applyHiddenFacts = async (payload: WorkerWorkspacePayload) =>
      filterWorkspaceHiddenFactChips(projectId, payload);
    const syncedWorkspace = await getWorkspaceSnapshot(projectId);
    if (syncedWorkspace && typeof syncedWorkspace === "object") {
      const raw = syncedWorkspace as Record<string, unknown>;
      const normalized = normalizeWorkerWorkspacePayload({
        ...(syncedWorkspace as Partial<WorkerWorkspacePayload>),
        project_id: String(raw.project_id ?? projectId),
      });
      if (workspaceSnapshotHasRenderableData(normalized)) {
        return applyHiddenFacts(normalized);
      }
    }
    const stored = await getLatestJobResultForProject(projectId);
    if (stored) {
      const fromJob = synthesizeWorkspaceFromJobResult(projectId, stored);
      if (workspaceSnapshotHasRenderableData(fromJob)) {
        return applyHiddenFacts(fromJob);
      }
    }
    const pending = await listPendingQueueJobsForProject(projectId);
    if (pending.length) {
      return applyHiddenFacts(synthesizeWorkspaceFromPendingQueueJobs(projectId, pending));
    }
    return applyHiddenFacts(
      normalizeWorkerWorkspacePayload({
        project_id: projectId,
      })
    );
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
  payload: {
    source_id: string;
    label: string;
    source_kind: string;
    content_text: string;
    repeat_interval?: "never" | "daily" | "weekly" | "monthly" | "quarterly" | "yearly";
    repeat_anchor_at?: string;
    status?: string;
  }
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

function pruneWorkspaceRowSourceRefs(row: unknown, sourceRef: string): unknown | null {
  if (!row || typeof row !== "object") {
    return row;
  }
  const o = row as Record<string, unknown>;
  const sr = o.source_refs;
  if (!Array.isArray(sr)) {
    return row;
  }
  const next = (sr as string[]).filter((r) => r !== sourceRef);
  if (
    next.length === 0 &&
    (Boolean(o.card_id) || Boolean(o.fact_id) || Boolean(o.knowledge_id) || Boolean(o.segment_id))
  ) {
    return null;
  }
  return { ...o, source_refs: next };
}

function applyIngestedSourceRemovalToSnapshot(payload: Record<string, unknown>, sourceRef: string): void {
  for (const key of ["source_cards", "recent_sources"] as const) {
    const arr = payload[key];
    if (!Array.isArray(arr)) {
      continue;
    }
    payload[key] = arr.filter((row) => {
      if (!row || typeof row !== "object") {
        return true;
      }
      return (row as { source_ref?: string }).source_ref !== sourceRef;
    });
  }
  const activity = payload.recent_activity;
  if (Array.isArray(activity)) {
    payload.recent_activity = activity.filter((row) => {
      if (!row || typeof row !== "object") {
        return true;
      }
      return (row as { source_ref?: string }).source_ref !== sourceRef;
    });
  }
  for (const key of [
    "fact_chips",
    "intelligence_cards",
    "visible_intelligence_cards",
    "knowledge_cards",
    "draft_segments",
  ] as const) {
    const arr = payload[key];
    if (!Array.isArray(arr)) {
      continue;
    }
    const out: unknown[] = [];
    for (const row of arr) {
      const pruned = pruneWorkspaceRowSourceRefs(row, sourceRef);
      if (pruned !== null) {
        out.push(pruned);
      }
    }
    payload[key] = out;
  }
}

const QUEUE_JOB_SOURCE_PREFIX = "queue_job:";

function taskReferencesIngestedSource(task: RecommendedTask, sourceRef: string): boolean {
  if ((task.supporting_source_refs ?? []).includes(sourceRef)) {
    return true;
  }
  if ((task.evidence_refs ?? []).includes(sourceRef)) {
    return true;
  }
  return (task.supporting_source_scores ?? []).some((row) => row.source_ref === sourceRef);
}

async function deleteIngestedSourceHosted(projectId: string, sourceRef: string): Promise<WorkerWorkspacePayload> {
  if (sourceRef.startsWith(QUEUE_JOB_SOURCE_PREFIX)) {
    const jobId = sourceRef.slice(QUEUE_JOB_SOURCE_PREFIX.length);
    await removeQueuedJobById(projectId, jobId);
    const snapQueued = await getWorkspaceSnapshot(projectId);
    if (snapQueued && typeof snapQueued === "object") {
      const copy = { ...(snapQueued as Record<string, unknown>) };
      applyIngestedSourceRemovalToSnapshot(copy, sourceRef);
      await saveWorkspaceSnapshot(projectId, copy);
    }
    return fetchWorkerWorkspace(projectId);
  }

  const latest = await getLatestJobResultForProject(projectId);
  if (
    latest &&
    latest.status === "complete" &&
    latest.result_payload &&
    typeof latest.result_payload === "object" &&
    "recommended_tasks" in latest.result_payload
  ) {
    const rp = latest.result_payload as Record<string, unknown> & { recommended_tasks: RecommendedTask[] };
    const tasks = rp.recommended_tasks;
    if (Array.isArray(tasks)) {
      const filtered = tasks.filter((t) => !taskReferencesIngestedSource(t, sourceRef));
      if (filtered.length !== tasks.length) {
        await saveResult({
          ...latest,
          result_payload: { ...rp, recommended_tasks: filtered },
        });
      }
    }
  }

  const snap = await getWorkspaceSnapshot(projectId);
  if (snap && typeof snap === "object") {
    const copy = { ...(snap as Record<string, unknown>) };
    applyIngestedSourceRemovalToSnapshot(copy, sourceRef);
    await saveWorkspaceSnapshot(projectId, copy);
  }

  return fetchWorkerWorkspace(projectId);
}

export async function deleteWorkerIngestedSource(
  projectId: string,
  sourceRef: string
): Promise<Record<string, unknown>> {
  if (!isDirectWorkerEnabled()) {
    if (!canUseNeon()) {
      throw new Error(
        "Removing a source in queue mode needs DATABASE_URL (Neon) with AGENT_BRIDGE_MODE=queue (or set DEMO_STORAGE_MODE=neon). Alternatively use AGENT_BRIDGE_MODE=worker with AGENT_API_BASE_URL so the Mac can delete from the brain database."
      );
    }
    return deleteIngestedSourceHosted(projectId, sourceRef) as unknown as Record<string, unknown>;
  }
  return sendWorkerManagementRequest(
    `/projects/${encodeURIComponent(projectId)}/sources/ingested/${encodeURIComponent(sourceRef)}`,
    "DELETE",
    {}
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
