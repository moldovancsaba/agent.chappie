"use client";

import { type ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult, type RecommendedTask } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

type AppView = "checklist" | "know-more" | "sources-jobs";
type InputMode = "url" | "text" | "file";
type DecisionStatus = "done" | "edited" | "declined" | "commented" | "deleted_silent" | "deleted_with_annotation" | "held_for_later";
type TaskDecision = {
  status: DecisionStatus | null;
  adjustedText: string;
  commentText: string;
};
type SourceFormState = {
  label: string;
  relation: "general" | "industry" | "competitors" | "my_business";
  repeatInterval: "never" | "daily" | "weekly" | "monthly" | "quarterly" | "yearly";
  url: string;
  contentNotes: string;
  description: string;
  hashtags: string;
};
type JobFormState = {
  name: string;
  triggerType: "manual" | "recurring" | "event";
  scheduleText: string;
  sourceId: string;
};
type KnowledgeCard = {
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
  confidence_source: "extracted" | "user_confirmed" | "user_modified" | string;
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
};
type SourceCard = {
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
};
type ManagementStatus = {
  tone: "success" | "error";
  message: string;
} | null;
type WorkspaceSnapshot = {
  project_id: string;
  intelligence_cards: Array<{
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
  }>;
  visible_intelligence_cards: Array<{
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
  }>;
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
  source_cards: SourceCard[];
  knowledge_cards: KnowledgeCard[];
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

function isCompleteResultWithTasks(
  result: JobResult | null
): result is JobResult & {
  result_payload: { recommended_tasks: RecommendedTask[]; summary: string };
  decision_summary?: { confidence: number };
} {
  return Boolean(
    result &&
      result.status === "complete" &&
      typeof result.result_payload === "object" &&
      result.result_payload !== null &&
      "recommended_tasks" in result.result_payload &&
      Array.isArray(result.result_payload.recommended_tasks)
  );
}

function readOrCreateSessionId() {
  if (typeof window === "undefined") {
    return "anonymous-server";
  }
  const existing = window.localStorage.getItem("agent-chappie-demo-session");
  if (existing) {
    return existing;
  }
  const created = generateId("demo_session");
  window.localStorage.setItem("agent-chappie-demo-session", created);
  return created;
}

function confidenceLabel(confidence: number | undefined) {
  if (confidence === undefined) {
    return "Pending";
  }
  if (confidence >= 0.85) {
    return "High";
  }
  if (confidence >= 0.65) {
    return "Medium";
  }
  return "Low";
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not yet";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function humanizeRegion(value: string) {
  return value.replaceAll("_", " ");
}

function titleCaseWords(value: string) {
  return value
    .split(" ")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ");
}

function humanizeSignalType(value: string) {
  return titleCaseWords(value.replaceAll("_", " "));
}

function humanizeFactCategory(value: string) {
  if (value === "pricing") {
    return "Pricing";
  }
  if (value === "offer") {
    return "Offer";
  }
  if (value === "positioning") {
    return "Positioning";
  }
  if (value === "proof") {
    return "Proof";
  }
  if (value === "segment") {
    return "Segment";
  }
  if (value === "timing") {
    return "Timing";
  }
  if (value === "opportunity") {
    return "Opportunity";
  }
  if (value === "competitor") {
    return "Competitor";
  }
  return titleCaseWords(value.replaceAll("_", " "));
}

function sourceKindLabel(value: string) {
  if (value === "auto_research_url") {
    return "Auto research";
  }
  if (value === "manual_text") {
    return "Text";
  }
  if (value === "uploaded_file") {
    return "Document";
  }
  if (value === "url") {
    return "URL";
  }
  return titleCaseWords(value.replaceAll("_", " "));
}

function confidenceSourceLabel(value: string) {
  if (value === "user_confirmed") {
    return "User confirmed";
  }
  if (value === "user_modified") {
    return "User modified";
  }
  return "Extracted";
}

function priorityLabel(value: RecommendedTask["priority_label"] | undefined) {
  if (value === "critical") {
    return "Critical";
  }
  if (value === "high") {
    return "High";
  }
  return "Normal";
}

function supportStrengthLabel(score: number | undefined) {
  if (score === undefined) {
    return "Supporting evidence";
  }
  if (score >= 2.6) {
    return "Primary evidence";
  }
  if (score >= 1.5) {
    return "Strong support";
  }
  return "Secondary support";
}

function buildConsequenceOfInaction(task: RecommendedTask) {
  const impact = task.expected_advantage.replace(/\.$/, "");
  const title = task.title.toLowerCase();
  if (title.includes("comparison offer") || title.includes("switch campaign")) {
    return `If you do nothing, price-sensitive buyers stay inside the competitor's comparison frame and the next buying window closes before you intercept them. ${impact}.`;
  }
  if (title.includes("owner") || title.includes("bundled offer") || title.includes("first access")) {
    return `If you do nothing, another operator can secure the distressed assets first and close the expansion window before you act. ${impact}.`;
  }
  if (title.includes("testimonial") || title.includes("proof") || title.includes("hero")) {
    return `If you do nothing, the competitor keeps the trust advantage in active comparisons and hesitant buyers are more likely to choose the lower-friction option. ${impact}.`;
  }
  return `If you do nothing, the competitor keeps the initiative and the business effect described here becomes harder to capture in the current window. ${impact}.`;
}

function buildExecutionSteps(task: RecommendedTask, sourceLabels: string[]) {
  if (task.execution_steps?.length) {
    return task.execution_steps;
  }
  const sourceSummary = sourceLabels.length ? sourceLabels.join(", ") : "the linked source set";
  const targetChannel = task.target_channel ?? "named channel";
  const targetSegment = task.target_segment ?? "buyers";
  const competitor = task.competitor_name ?? "the strongest competitor";
  const mechanism = task.mechanism ?? "the exact change described in the task";
  const lowerTitle = task.title.toLowerCase();
  const bucket = task.move_bucket ?? "";

  if (task.task_type === "information_request") {
    return [
      `Review ${sourceSummary} and isolate the one missing proprietary fact we still cannot collect automatically.`,
      "Request that specific missing input in one message, not a broad research ask.",
      "Add the new evidence to the same workspace this week so the checklist can regenerate from it.",
      "Check that the next regeneration replaces the exploratory task with a stronger action move.",
    ];
  }

  if (bucket === "pricing_or_offer_move" || lowerTitle.includes("pricing") || lowerTitle.includes("onboarding")) {
    return [
      `Pull the exact pricing, onboarding, and proof claims from ${sourceSummary}, especially anything tied to ${competitor}.`,
      `Turn those claims into the exact asset described by the task using this mechanism: ${mechanism}.`,
      `Place that asset on the ${targetChannel}.`,
      `Publish the ${targetChannel} update before the best-before date so active ${targetSegment} see the lower-friction comparison immediately.`,
      "Send the updated asset to live prospects or active deals and check whether pricing or onboarding objections drop.",
    ];
  }

  if (bucket === "messaging_or_positioning_move" || lowerTitle.includes("homepage") || lowerTitle.includes("hero") || lowerTitle.includes("enrollment")) {
    return [
      `Identify the strongest competitor claim in ${sourceSummary}, especially the angle ${competitor} is using against ${targetSegment}.`,
      `Rewrite the ${targetChannel} using this mechanism: ${mechanism}.`,
      `Publish the update in the ${targetChannel} this week and keep the change in the first comparison section buyers will see.`,
      "Check whether the updated page now answers the objection or offer pressure named in the task.",
    ];
  }

  if (bucket === "proof_or_trust_move" || lowerTitle.includes("proof") || lowerTitle.includes("testimonial")) {
    return [
      `Pull the strongest proof patterns from ${sourceSummary}, especially anything that makes ${competitor} more trustworthy to ${targetSegment}.`,
      `Add the proof assets described by the task using this mechanism: ${mechanism}.`,
      "Publish or ship the updated proof asset this week where hesitant buyers see it first.",
      "Check whether trust objections drop in live conversations or comparison-stage pages.",
    ];
  }

  if (bucket === "intercept_or_capture_move" || lowerTitle.includes("owner") || lowerTitle.includes("first access") || lowerTitle.includes("assets") || lowerTitle.includes("distribution")) {
    return [
      `Pull the exact distress or transition evidence from ${sourceSummary}.`,
      `Contact ${competitor} with one specific ask using this mechanism: ${mechanism}.`,
      "Secure the next meeting, inventory list, or first-right-of-access this week before another operator moves.",
      "Check whether the opportunity is now advancing on your terms instead of staying theoretical.",
    ];
  }

  return [
    `Use the strongest evidence from ${sourceSummary} to define the exact asset or channel change required against ${competitor}.`,
    `Create the exact move described by the task using this mechanism: ${mechanism}.`,
    `Publish the change in the ${targetChannel} this week so ${targetSegment} can actually experience the move.`,
    "Check whether the result reduced the threat or captured the opportunity described in the expected impact.",
  ];
}

function buildHumanEvidenceChips(
  task: RecommendedTask,
  evidence: WorkspaceSnapshot["recent_activity"],
  facts: WorkspaceSnapshot["fact_chips"],
  sources: SourceCard[]
) {
  const chips: string[] = [];
  const seen = new Set<string>();

  const push = (value: string) => {
    const normalized = value.trim();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    chips.push(normalized);
  };

  if (task.strongest_evidence_excerpt) {
    push(task.strongest_evidence_excerpt);
  }
  for (const activity of evidence) {
    push(activity.summary);
  }
  for (const chip of facts) {
    push(`${humanizeFactCategory(chip.category)}: ${chip.label}`);
  }
  for (const source of sources) {
    push(source.label);
  }

  return chips.slice(0, 6);
}

function isAutoCollectedSourceKind(value: string) {
  return value === "auto_research_url";
}

function classifyOriginFromSourceRefs(sourceRefs: string[], autoCollectedSourceRefs: Set<string>) {
  const refs = sourceRefs.filter(Boolean);
  if (!refs.length) {
    return "user-provided";
  }
  const autoCount = refs.filter((sourceRef) => autoCollectedSourceRefs.has(sourceRef)).length;
  if (autoCount === 0) {
    return "user-provided";
  }
  if (autoCount === refs.length) {
    return "auto-collected";
  }
  return "mixed-origin";
}

function originLabel(origin: string) {
  if (origin === "auto-collected") {
    return "We researched";
  }
  if (origin === "mixed-origin") {
    return "Mixed";
  }
  return "You provided";
}

function buildDefaultDecisions(tasks: RecommendedTask[]) {
  return tasks.reduce<Record<number, TaskDecision>>((current, task) => {
    current[task.rank] = {
      status: null,
      adjustedText: task.title,
      commentText: "",
    };
    return current;
  }, {});
}

function buildFeedbackPayload(tasks: RecommendedTask[], decisions: Record<number, TaskDecision>) {
  return tasks.reduce(
    (current, task) => {
      const decision = decisions[task.rank];
      if (!decision?.status) {
        return current;
      }
      if (decision.status === "done") {
        current.done.push(task.title);
      } else if (decision.status === "edited") {
        current.edited.push(decision.adjustedText.trim() || task.title);
      } else if (decision.status === "commented") {
        current.commented.push(task.title);
      } else if (decision.status === "deleted_silent") {
        current.deleted_silent.push(task.title);
      } else if (decision.status === "deleted_with_annotation") {
        current.deleted_with_annotation.push(task.title);
      } else if (decision.status === "held_for_later") {
        current.held_for_later.push(task.title);
      } else {
        current.declined.push(task.title);
      }
      return current;
    },
    {
      done: [] as string[],
      edited: [] as string[],
      declined: [] as string[],
      commented: [] as string[],
      deleted_silent: [] as string[],
      deleted_with_annotation: [] as string[],
      held_for_later: [] as string[],
    }
  );
}

function buildTaskFeedbackItems(tasks: RecommendedTask[], decisions: Record<number, TaskDecision>) {
  return tasks.flatMap((task) => {
    const decision = decisions[task.rank];
    if (!decision?.status) {
      return [];
    }
    return [
      {
        feedback_id: generateId("task_feedback"),
        rank: task.rank,
        original_title: task.title,
        original_expected_advantage: task.expected_advantage,
        feedback_type: decision.status === "edited" ? "edited" : decision.status,
        adjusted_text: decision.status === "edited" ? decision.adjustedText.trim() || task.title : undefined,
        feedback_comment: decision.commentText.trim() || undefined,
      },
    ];
  });
}

function findTaskSourceRef(task: RecommendedTask) {
  return task.supporting_source_refs?.find((sourceRef) => sourceRef && !sourceRef.startsWith("feedback::")) ?? null;
}

function inferSourceLabel(source: SourceFormState, uploadFile: File | null) {
  if (uploadFile?.name?.trim()) {
    return uploadFile.name.trim();
  }
  if (source.url.trim()) {
    try {
      const host = new URL(source.url.trim()).hostname.replace(/^www\./, "");
      return host || "Source";
    } catch {
      return "Source";
    }
  }
  if (source.description.trim()) {
    return source.description.trim().slice(0, 80);
  }
  if (source.contentNotes.trim()) {
    return source.contentNotes.trim().slice(0, 80);
  }
  return "Source";
}

function fallbackSourceLabel(sourceRef: string) {
  if (!sourceRef) {
    return "No linked source";
  }
  if (sourceRef.startsWith("feedback::")) {
    return "Operator feedback";
  }
  if (sourceRef.startsWith("source_job_")) {
    return "Uploaded source";
  }
  if (sourceRef.startsWith("source_")) {
    return "Source";
  }
  return titleCaseWords(sourceRef.replaceAll("_", " "));
}

function hasPlaceholderTaskText(value: string) {
  const lowered = value.toLowerCase();
  return (
    lowered.includes("uploaded file") ||
    lowered.includes("document source") ||
    lowered.includes("placeholder") ||
    lowered.includes("dummy")
  );
}

function normalizeWorkspaceSnapshot(payload: Partial<WorkspaceSnapshot> & { project_id: string }) {
  return {
    project_id: payload.project_id,
    intelligence_cards: payload.intelligence_cards ?? [],
    visible_intelligence_cards: payload.visible_intelligence_cards ?? [],
    fact_chips: payload.fact_chips ?? [],
    draft_segments: payload.draft_segments ?? [],
    source_cards: payload.source_cards ?? [],
    knowledge_cards: payload.knowledge_cards ?? [],
    recent_sources: payload.recent_sources ?? [],
    recent_activity: payload.recent_activity ?? [],
    market_summary: payload.market_summary ?? {
      pricing_changes: 0,
      closure_signals: 0,
      offer_signals: 0,
    },
    competitive_snapshot: payload.competitive_snapshot ?? {
      pricing_position: "",
      acquisition_strategy_comparison: "",
      active_threats: [],
      immediate_opportunities: [],
      reference_competitor: "",
    },
    knowledge_summary: payload.knowledge_summary ?? [],
    monitor_jobs: payload.monitor_jobs ?? [],
    managed_sources: payload.managed_sources ?? [],
    managed_jobs: payload.managed_jobs ?? [],
  };
}

export function DemoWorkspace() {
  const [activeView, setActiveView] = useState<AppView>("checklist");
  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [sessionId, setSessionId] = useState("anonymous-loading");
  const [projectId, setProjectId] = useState("");
  const [contextNotes, setContextNotes] = useState("");
  const [fileName, setFileName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [submissionError, setSubmissionError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [taskDecisions, setTaskDecisions] = useState<Record<number, TaskDecision>>({});
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");
  const [sourceForm, setSourceForm] = useState<SourceFormState>({
    label: "",
    relation: "general",
    repeatInterval: "never",
    url: "",
    contentNotes: "",
    description: "",
    hashtags: "",
  });
  const [sourceUploadFile, setSourceUploadFile] = useState<File | null>(null);
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
  const [jobForm, setJobForm] = useState<JobFormState>({
    name: "",
    triggerType: "manual",
    scheduleText: "",
    sourceId: "",
  });
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [showSourceComposer, setShowSourceComposer] = useState(false);
  const [showJobComposer, setShowJobComposer] = useState(false);
  const [managementStatus, setManagementStatus] = useState<ManagementStatus>(null);
  const [selectedTask, setSelectedTask] = useState<RecommendedTask | null>(null);
  const [focusedSourceRef, setFocusedSourceRef] = useState<string | null>(null);
  const [editingIngestedSourceRef, setEditingIngestedSourceRef] = useState<string | null>(null);
  const [ingestedSourceLabel, setIngestedSourceLabel] = useState("");
  const [editingKnowledgeId, setEditingKnowledgeId] = useState<string | null>(null);
  const [knowledgeDraft, setKnowledgeDraft] = useState({ title: "", summary: "", implication: "", potentialMoves: "", items: "" });
  const [knowledgeDeleteReason, setKnowledgeDeleteReason] = useState<Record<string, string>>({});
  const [flashcardTeachNote, setFlashcardTeachNote] = useState<Record<string, string>>({});
  const [flashcardTeachOpen, setFlashcardTeachOpen] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setSessionId(readOrCreateSessionId());
  }, []);

  useEffect(() => {
    if (!sessionId || sessionId === "anonymous-loading") {
      return;
    }

    let cancelled = false;
    async function loadLatestSessionState() {
      try {
        const response = await fetch(`/api/session/${encodeURIComponent(sessionId)}/state`, {
          cache: "no-store",
        });
        if (!response.ok) {
          return;
        }
        const body = await response.json();
        if (cancelled) {
          return;
        }
        if (body.project?.projectId) {
          setProjectId(body.project.projectId);
        }
        if (body.job_request) {
          setJobRequest(body.job_request);
        }
        if (body.job_result) {
          setJobResult(body.job_result);
        }
      } catch {
        return;
      }
    }

    void loadLatestSessionState();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!isCompleteResultWithTasks(jobResult)) {
      return;
    }
    setTaskDecisions(buildDefaultDecisions(jobResult.result_payload.recommended_tasks));
    setFeedbackStatus("");
    setActiveView("checklist");
  }, [jobResult]);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    let cancelled = false;
    async function loadWorkspace() {
      try {
        setWorkspaceError("");
        const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/workspace`, {
          cache: "no-store",
        });
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.detail ?? "The workspace could not be loaded.");
        }
        if (!cancelled) {
          setWorkspace(normalizeWorkspaceSnapshot(body));
        }
      } catch (error) {
        if (!cancelled) {
          setWorkspaceError(error instanceof Error ? error.message : "Unknown workspace error.");
        }
      }
    }

    void loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [projectId, jobResult]);

  async function reloadWorkspace(currentProjectId: string) {
    const response = await fetch(`/api/projects/${encodeURIComponent(currentProjectId)}/workspace`, {
      cache: "no-store",
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail ?? "The workspace could not be loaded.");
    }
    const normalized = normalizeWorkspaceSnapshot(body);
    setWorkspace(normalized);
    return normalized as WorkspaceSnapshot;
  }

  async function submitContext(notes: string) {
    const trimmed = notes.trim();
    if (inputMode !== "file" && !trimmed) {
      setSubmissionError("Paste one URL, one text block, or upload one file before running the job.");
      return;
    }
    if (inputMode === "file" && !selectedFile) {
      setSubmissionError("Choose one file before running the job.");
      return;
    }

    setIsSubmitting(true);
    setSubmissionError("");
    setFeedbackStatus("");

    try {
      const contextType = inputMode === "file" ? "working_document" : "meeting_notes";
      const sourceKind =
        inputMode === "url" ? "url" : inputMode === "file" ? "uploaded_file" : "manual_text";
      const response =
        inputMode === "file" && selectedFile
          ? await (async () => {
              const form = new FormData();
              form.set("sessionId", sessionId);
              form.set("contextType", contextType);
              form.set("sourceKind", sourceKind);
              if (projectId) {
                form.set("projectId", projectId);
              }
              form.set("file", selectedFile);
              return fetch("/api/jobs", {
                method: "POST",
                body: form,
              });
            })()
          : await fetch("/api/jobs", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                sessionId,
                projectId: projectId || undefined,
                contextNotes: trimmed,
                contextType,
                sourceKind,
              }),
            });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "The job submission failed.");
      }

      setProjectId(body.project_id);
      setJobRequest(body.job_request);

      const fetchResultWithPolling = async () => {
        const maxAttempts = 30;
        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
          const resultResponse = await fetch(body.result_url, { cache: "no-store" });
          const resultBody = await resultResponse.json();
          if (resultResponse.ok && resultBody.job_result) {
            return resultBody.job_result;
          }
          if (resultResponse.status === 202) {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            continue;
          }
          throw new Error(resultBody.detail ?? "The job result could not be retrieved.");
        }
        throw new Error("The job is still queued. Please wait a moment and refresh.");
      };

      const resolvedResult = await fetchResultWithPolling();
      setJobResult(resolvedResult);
      setActiveView("checklist");
      if (inputMode === "file") {
        setSelectedFile(null);
        setFileName("");
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      } else {
        setContextNotes("");
      }
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : "Unknown submission error.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitContext(contextNotes);
  }

  async function handleFileSelection(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setInputMode("file");
    setFileName(file.name);
    setSelectedFile(file);
    setContextNotes("");
    setSubmissionError("");
  }

  async function submitSingleDecision(
    task: RecommendedTask,
    status: DecisionStatus,
    overrides?: { adjustedText?: string; commentText?: string }
  ) {
    if (!jobResult || !isCompleteResultWithTasks(jobResult)) {
      return;
    }

    const decision: TaskDecision = {
      status,
      adjustedText: overrides?.adjustedText ?? taskDecisions[task.rank]?.adjustedText ?? task.title,
      commentText: overrides?.commentText ?? taskDecisions[task.rank]?.commentText ?? "",
    };
    const removeFromUiNow =
      status === "done" || status === "deleted_with_annotation" || status === "deleted_silent";

    setTaskDecisions((current) => ({
      ...current,
      [task.rank]: decision,
    }));

    const feedbackPayload = buildFeedbackPayload(jobResult.result_payload.recommended_tasks, {
      [task.rank]: decision,
    });
    const fallbackAction: DecisionStatus =
      feedbackPayload.done.length > 0
        ? "done"
        : feedbackPayload.deleted_with_annotation.length > 0
          ? "deleted_with_annotation"
          : feedbackPayload.deleted_silent.length > 0
            ? "deleted_silent"
            : feedbackPayload.held_for_later.length > 0
              ? "held_for_later"
              : feedbackPayload.declined.length > 0
                ? "declined"
                : feedbackPayload.edited.length > 0
                  ? "edited"
                  : "commented";

    setIsSavingFeedback(true);
    setFeedbackStatus("");

    try {
      const feedback = feedbackSchema.parse({
        feedback_id: generateId("feedback"),
        job_id: jobResult.job_id,
        app_id: jobResult.app_id,
        project_id: jobResult.project_id,
        feedback_type: "task_response",
        submitted_at: new Date().toISOString(),
        user_action: fallbackAction,
        feedback_payload: feedbackPayload,
        task_feedback_items: buildTaskFeedbackItems([task], { [task.rank]: decision }),
        current_tasks: isCompleteResultWithTasks(jobResult) ? jobResult.result_payload.recommended_tasks : undefined,
        actor_id: `anonymous:${sessionId}`,
        linked_result_status: jobResult.status,
      });

      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "The feedback payload could not be saved.");
      }

      if (
        body.regenerated &&
        typeof body.regenerated === "object" &&
        "job_result" in body.regenerated &&
        body.regenerated.job_result
      ) {
        const regeneratedJobResult = body.regenerated.job_result as JobResult;
        setJobResult(regeneratedJobResult);
        setTaskDecisions(
          isCompleteResultWithTasks(regeneratedJobResult)
            ? buildDefaultDecisions(regeneratedJobResult.result_payload.recommended_tasks)
            : {}
        );
        setSelectedTask(null);
        if (projectId) {
          await reloadWorkspace(projectId);
        }
      } else if (removeFromUiNow) {
        setJobResult((current) => {
          if (!current || !isCompleteResultWithTasks(current)) {
            return current;
          }
          const remaining = current.result_payload.recommended_tasks.filter((item) => item.rank !== task.rank);
          return {
            ...current,
            result_payload: {
              ...current.result_payload,
              recommended_tasks: remaining,
            },
          };
        });
        setTaskDecisions((current) => {
          const next = { ...current };
          delete next[task.rank];
          return next;
        });
        setSelectedTask((current) => (current?.rank === task.rank ? null : current));
      }

      setFeedbackStatus("Saved automatically. We regenerated the checklist from your action.");
    } catch (error) {
      setFeedbackStatus(error instanceof Error ? error.message : "Unknown feedback error.");
    } finally {
      setIsSavingFeedback(false);
    }
  }

  async function handleCreateSource() {
    const resolvedLabel = sourceForm.label.trim() || inferSourceLabel(sourceForm, sourceUploadFile);
    if (!projectId) {
      setManagementStatus({ tone: "error", message: "Add the source you want monitored first." });
      return;
    }
    const hasAnyInput =
      Boolean(sourceUploadFile) ||
      Boolean(sourceForm.url.trim()) ||
      Boolean(sourceForm.contentNotes.trim()) ||
      Boolean(sourceForm.description.trim()) ||
      Boolean(sourceForm.hashtags.trim());
    if (!hasAnyInput) {
      setManagementStatus({ tone: "error", message: "Add the source you want monitored first." });
      return;
    }
    const sourceKind: "url" | "manual_text" | "uploaded_file" = sourceUploadFile
      ? "uploaded_file"
      : sourceForm.url.trim()
        ? "url"
        : "manual_text";
    const contentParts = [
      sourceForm.url.trim() ? `URL: ${sourceForm.url.trim()}` : "",
      sourceForm.description.trim() ? `Description: ${sourceForm.description.trim()}` : "",
      sourceForm.hashtags.trim() ? `Hashtags: ${sourceForm.hashtags.trim()}` : "",
      sourceForm.contentNotes.trim() ? `Content / Notes: ${sourceForm.contentNotes.trim()}` : "",
      `Relation: ${sourceForm.relation}`,
    ].filter(Boolean);
    const contentText = sourceKind === "uploaded_file" ? sourceUploadFile?.name ?? resolvedLabel : contentParts.join("\n");
    let contentBase64: string | undefined;
    let contentType: string | undefined;
    let fileName: string | undefined;
    if (sourceKind === "uploaded_file" && sourceUploadFile) {
      const bytes = new Uint8Array(await sourceUploadFile.arrayBuffer());
      let binary = "";
      const chunkSize = 0x8000;
      for (let index = 0; index < bytes.length; index += chunkSize) {
        const chunk = bytes.subarray(index, index + chunkSize);
        binary += String.fromCharCode(...chunk);
      }
      contentBase64 = btoa(binary);
      contentType = sourceUploadFile.type || "application/octet-stream";
      fileName = sourceUploadFile.name;
    }
    const response = editingSourceId
      ? await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(editingSourceId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            label: resolvedLabel,
            source_kind: sourceKind,
            relation: sourceForm.relation,
            description: sourceForm.description.trim() || undefined,
            hashtags: sourceForm.hashtags.trim() || undefined,
            url: sourceForm.url.trim() || undefined,
            repeat_interval: sourceForm.repeatInterval,
            content_text: contentText,
          }),
        })
      : sourceKind === "uploaded_file" && sourceUploadFile
        ? await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
            method: "POST",
            body: (() => {
              const form = new FormData();
              form.set("source_kind", sourceKind);
              form.set("relation", sourceForm.relation);
              form.set("description", sourceForm.description.trim());
              form.set("hashtags", sourceForm.hashtags.trim());
              form.set("url", sourceForm.url.trim());
              form.set("repeat_interval", sourceForm.repeatInterval);
              form.set("label", resolvedLabel);
              form.set("content_text", contentText);
              form.set("repeat_anchor_at", new Date().toISOString());
              form.set("file", sourceUploadFile);
              return form;
            })(),
          })
        : await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_id: generateId("source_cfg"),
              label: resolvedLabel,
              source_kind: sourceKind,
              relation: sourceForm.relation,
              description: sourceForm.description.trim() || undefined,
              hashtags: sourceForm.hashtags.trim() || undefined,
              url: sourceForm.url.trim() || undefined,
              repeat_interval: sourceForm.repeatInterval,
              repeat_anchor_at: new Date().toISOString(),
              content_text: contentText,
              file_name: fileName,
              content_type: contentType,
              content_base64: contentBase64,
              status: "active",
            }),
          });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The source could not be created." });
      return;
    }
    setWorkspace((current) =>
      current && Array.isArray(body.sources) ? { ...current, managed_sources: body.sources } : current
    );
    setSourceForm({
      label: "",
      relation: "general",
      repeatInterval: "never",
      url: "",
      contentNotes: "",
      description: "",
      hashtags: "",
    });
    setSourceUploadFile(null);
    setEditingSourceId(null);
    setShowSourceComposer(false);
    const queuedOk = body.status === "queued";
    setManagementStatus({
      tone: "success",
      message: editingSourceId
        ? "Source updated."
        : queuedOk
          ? `Queued (job ${body.job_id ?? ""}). Local worker will process and sync Know More.`
          : "Source saved.",
    });
  }

  async function updateSource(sourceId: string, payload: Record<string, unknown>) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The source could not be updated." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_sources: body.sources ?? [] } : current));
    setManagementStatus({ tone: "success", message: "Source updated." });
  }

  async function deleteSource(sourceId: string) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}`, {
      method: "DELETE",
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The source could not be deleted." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_sources: body.sources ?? [] } : current));
    setManagementStatus({ tone: "success", message: "Source deleted." });
  }

  async function handleCreateJob() {
    if (!projectId || !jobForm.name.trim()) {
      setManagementStatus({ tone: "error", message: "Add a job name before saving this monitoring rule." });
      return;
    }
    const response = editingJobId
      ? await fetch(`/api/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(editingJobId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: jobForm.name.trim(),
            trigger_type: jobForm.triggerType,
            schedule_text: jobForm.scheduleText.trim() || null,
            source_id: jobForm.sourceId || null,
          }),
        })
      : await fetch(`/api/projects/${encodeURIComponent(projectId)}/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            managed_job_id: generateId("managed_job"),
            name: jobForm.name.trim(),
            trigger_type: jobForm.triggerType,
            schedule_text: jobForm.scheduleText.trim() || undefined,
            source_id: jobForm.sourceId || undefined,
            status: "active",
          }),
        });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The job could not be created." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_jobs: body.jobs ?? [] } : current));
    setJobForm({ name: "", triggerType: "manual", scheduleText: "", sourceId: "" });
    setEditingJobId(null);
    setShowJobComposer(false);
    setManagementStatus({ tone: "success", message: editingJobId ? "Job updated." : "Job saved." });
  }

  async function updateJob(jobId: string, payload: Record<string, unknown>) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The job could not be updated." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_jobs: body.jobs ?? [] } : current));
    setManagementStatus({ tone: "success", message: "Job updated." });
  }

  async function deleteJob(jobId: string) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`, {
      method: "DELETE",
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The job could not be deleted." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_jobs: body.jobs ?? [] } : current));
    setManagementStatus({ tone: "success", message: "Job deleted." });
  }

  async function updateKnowledgeCard(
    knowledgeId: string,
    payload: {
      status: "confirmed" | "dismissed" | "edited" | "held" | "held_for_later" | "deleted_with_annotation";
      confidence_source?: string;
      original_payload?: Record<string, unknown>;
      corrected_title?: string;
      corrected_summary?: string;
      corrected_implication?: string;
      corrected_potential_moves?: string[];
      corrected_items?: string[];
    }
  ) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(knowledgeId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The knowledge card could not be updated." });
      return;
    }
    setWorkspace(body);
    setEditingKnowledgeId(null);
    setKnowledgeDraft({ title: "", summary: "", implication: "", potentialMoves: "", items: "" });
    setManagementStatus({ tone: "success", message: "Knowledge updated." });
  }

  async function deleteKnowledgeCard(
    knowledgeId: string,
    payload: {
      status: "deleted_silent" | "deleted_with_annotation";
      original_payload?: Record<string, unknown>;
      reason?: string;
    }
  ) {
    if (!projectId) {
      return;
    }
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge/${encodeURIComponent(knowledgeId)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The knowledge card could not be deleted." });
      return;
    }
    setWorkspace(body);
    setKnowledgeDeleteReason((current) => ({ ...current, [knowledgeId]: "" }));
    setManagementStatus({
      tone: "success",
      message: payload.status === "deleted_with_annotation" ? "Knowledge card deleted and recorded as guidance for future generations." : "Knowledge card deleted.",
    });
  }

  async function actOnFactFlashcard(factId: string, action: "forget" | "teach") {
    if (!projectId) {
      return;
    }
    const teachNote = action === "teach" ? flashcardTeachNote[factId]?.trim() : "";
    if (action === "teach" && !teachNote) {
      setManagementStatus({
        tone: "error",
        message: "Add a short note for Delete and teach so we know what to avoid next time.",
      });
      return;
    }
    const response = await fetch(
      `/api/projects/${encodeURIComponent(projectId)}/fact-chips/${encodeURIComponent(factId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          teach_note: action === "teach" ? teachNote : undefined,
        }),
      }
    );
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "Flashcard action failed." });
      return;
    }
    setWorkspace((current) =>
      current
        ? {
            ...current,
            fact_chips: current.fact_chips.filter((c) => c.fact_id !== factId),
            intelligence_cards: current.intelligence_cards.filter((c) => c.card_id !== factId),
            visible_intelligence_cards: current.visible_intelligence_cards.filter((c) => c.card_id !== factId),
          }
        : current
    );
    setFlashcardTeachNote((current) => {
      const next = { ...current };
      delete next[factId];
      return next;
    });
    setFlashcardTeachOpen((current) => {
      const next = { ...current };
      delete next[factId];
      return next;
    });
    setManagementStatus({
      tone: "success",
      message:
        action === "teach"
          ? "Recorded. We will steer away from this pattern when generating recommendations."
          : "Removed from your view.",
    });
  }

  async function updateIngestedSource(sourceRef: string, payload: Record<string, unknown>) {
    if (!projectId) {
      return;
    }
    const response = await fetch(
      `/api/projects/${encodeURIComponent(projectId)}/sources/ingested/${encodeURIComponent(sourceRef)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The ingested source could not be updated." });
      return;
    }
    setWorkspace(body);
    setEditingIngestedSourceRef(null);
    setIngestedSourceLabel("");
    setManagementStatus({
      tone: "success",
      message: payload.action === "reprocess" ? "Source reprocessed." : "Source metadata updated.",
    });
  }

  async function deleteIngestedSource(sourceRef: string) {
    if (!projectId) {
      return;
    }
    const response = await fetch(
      `/api/projects/${encodeURIComponent(projectId)}/sources/ingested/${encodeURIComponent(sourceRef)}`,
      {
        method: "DELETE",
      }
    );
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The ingested source could not be deleted." });
      return;
    }
    setWorkspace(body);
    setJobResult((current) => {
      if (!current || !isCompleteResultWithTasks(current)) {
        return current;
      }
      const remaining = current.result_payload.recommended_tasks.filter(
        (task) => !(task.supporting_source_refs ?? []).includes(sourceRef)
      );
      return {
        ...current,
        result_payload: {
          ...current.result_payload,
          recommended_tasks: remaining,
        },
      };
    });
    setSelectedTask((current) => (current && (current.supporting_source_refs ?? []).includes(sourceRef) ? null : current));
    setManagementStatus({ tone: "success", message: "Ingested source deleted." });
  }

  function setDecision(rank: number, status: DecisionStatus, fallbackTitle: string) {
    setTaskDecisions((current) => ({
      ...current,
      [rank]: {
        status,
        adjustedText: current[rank]?.adjustedText ?? fallbackTitle,
        commentText: current[rank]?.commentText ?? "",
      },
    }));
  }

  function setAdjustedText(rank: number, value: string) {
    setTaskDecisions((current) => ({
      ...current,
      [rank]: {
        status: "edited",
        adjustedText: value,
        commentText: current[rank]?.commentText ?? "",
      },
    }));
  }

  function setCommentText(rank: number, value: string) {
    setTaskDecisions((current) => ({
      ...current,
      [rank]: {
        status: current[rank]?.status ?? "commented",
        adjustedText: current[rank]?.adjustedText ?? "",
        commentText: value,
      },
    }));
  }

  const completeResult = isCompleteResultWithTasks(jobResult) ? jobResult : null;
  const blockedResult =
    jobResult && jobResult.status === "blocked" && !isCompleteResultWithTasks(jobResult) ? jobResult : null;
  const tasks = (completeResult?.result_payload.recommended_tasks ?? []).filter(
    (task) =>
      !hasPlaceholderTaskText(task.title) &&
      !hasPlaceholderTaskText(task.why_now) &&
      !hasPlaceholderTaskText(task.expected_advantage)
  );
  const hasCompetitiveSnapshotData = Boolean(
    workspace?.competitive_snapshot.reference_competitor ||
      workspace?.competitive_snapshot.pricing_position ||
      workspace?.competitive_snapshot.acquisition_strategy_comparison ||
      workspace?.competitive_snapshot.current_weakness ||
      workspace?.competitive_snapshot.risk_level ||
      (workspace?.competitive_snapshot.active_threats?.length ?? 0) > 0 ||
      (workspace?.competitive_snapshot.immediate_opportunities?.length ?? 0) > 0
  );
  const sourceLabelByRef = new Map<string, string>();
  for (const source of workspace?.source_cards ?? []) {
    sourceLabelByRef.set(source.source_ref, source.label);
  }
  for (const source of workspace?.recent_sources ?? []) {
    if (!sourceLabelByRef.has(source.source_ref)) {
      sourceLabelByRef.set(source.source_ref, `${sourceKindLabel(source.source_kind)} source`);
    }
  }
  for (const job of workspace?.monitor_jobs ?? []) {
    if (job.last_source_ref && !sourceLabelByRef.has(job.last_source_ref)) {
      sourceLabelByRef.set(job.last_source_ref, fallbackSourceLabel(job.last_source_ref));
    }
  }
  const humanSourceLabel = (sourceRef: string | null | undefined) => {
    if (!sourceRef) {
      return "No linked source";
    }
    return sourceLabelByRef.get(sourceRef) ?? fallbackSourceLabel(sourceRef);
  };
  const autoCollectedSourceRefs = new Set(
    (workspace?.source_cards ?? []).filter((source) => isAutoCollectedSourceKind(source.source_kind)).map((source) => source.source_ref)
  );
  const confidence = completeResult?.decision_summary?.confidence;
  const topKnowledge = workspace?.knowledge_summary[0];
  const blockedReason =
    blockedResult && "reason" in blockedResult.result_payload && typeof blockedResult.result_payload.reason === "string"
      ? blockedResult.result_payload.reason === "insufficient_output_quality"
        ? "The current evidence builds useful knowledge, but not a strong enough advantage to recommend an immediate move."
        : blockedResult.result_payload.reason
      : "We processed your source but could not derive three distinct, high-confidence actions from it.";
  const currentStatus = isSubmitting
    ? "Processing"
    : completeResult
      ? "Ready"
      : blockedResult
        ? "Monitoring active"
      : workspace?.recent_sources.length
        ? "Monitoring active"
        : "Ready to process";
  const projectLabel = topKnowledge ? titleCaseWords(humanizeRegion(topKnowledge.region)) : "Competitive environment";
  const latestSourceLabel = workspace?.recent_sources[0]
    ? `${sourceKindLabel(workspace.recent_sources[0].source_kind)} received`
    : "No source yet";
  const systemStatusLine = workspace?.recent_sources.length
    ? `${workspace.recent_sources.length} source${workspace.recent_sources.length === 1 ? "" : "s"} ingested • last update ${formatTimestamp(workspace.recent_sources[0]?.created_at)}`
    : "System ready — no sources ingested yet";
  const filteredKnowledgeCards = focusedSourceRef
    ? (workspace?.knowledge_cards ?? []).filter((card) => card.source_refs.includes(focusedSourceRef))
    : (workspace?.knowledge_cards ?? []);
  const visibleFlashcards =
    workspace && workspace.visible_intelligence_cards.length
      ? workspace.visible_intelligence_cards
      : [];
  const taskScopedSourceRefs = selectedTask?.supporting_source_refs ?? [];
  const selectedTaskEvidence = selectedTask
    ? workspace?.recent_activity.filter(
        (activity) =>
          selectedTask.supporting_signal_refs?.includes(activity.signal_id) ||
          selectedTask.evidence_refs.includes(activity.signal_id) ||
          (!!taskScopedSourceRefs.length && taskScopedSourceRefs.includes(activity.source_ref))
      ) ?? []
    : [];
  const selectedTaskSignalScoreMap = new Map(
    (selectedTask?.supporting_signal_scores ?? []).map((item) => [item.signal_id, item])
  );
  const selectedTaskFactChips = selectedTask
    ? (workspace?.fact_chips ?? []).filter(
        (chip) =>
          !taskScopedSourceRefs.length || chip.source_refs.some((ref) => taskScopedSourceRefs.includes(ref))
      )
    : [];
  const selectedTaskSourceRefs = Array.from(
    new Set([
      ...((selectedTask?.supporting_source_refs ?? []) as string[]),
      ...selectedTaskEvidence.map((activity) => activity.source_ref),
      ...selectedTaskFactChips.flatMap((chip) => chip.source_refs),
    ])
  );
  const selectedTaskSourceScoreMap = new Map(
    (selectedTask?.supporting_source_scores ?? []).map((item) => [item.source_ref, item])
  );
  const selectedTaskSources = selectedTask
    ? (workspace?.source_cards.filter((source) => selectedTaskSourceRefs.includes(source.source_ref)) ?? []).sort((left, right) => {
        const leftScore = selectedTaskSourceScoreMap.get(left.source_ref)?.relevance_score ?? 0;
        const rightScore = selectedTaskSourceScoreMap.get(right.source_ref)?.relevance_score ?? 0;
        return rightScore - leftScore;
      })
    : [];
  const orderedTaskEvidence = [...selectedTaskEvidence].sort((left, right) => {
    const leftScore = selectedTaskSignalScoreMap.get(left.signal_id)?.relevance_score ?? 0;
    const rightScore = selectedTaskSignalScoreMap.get(right.signal_id)?.relevance_score ?? 0;
    return rightScore - leftScore;
  });
  const orderedTaskFactChips = [...selectedTaskFactChips].sort((left, right) => right.confidence - left.confidence);
  const selectedTaskSteps = selectedTask
    ? buildExecutionSteps(
        selectedTask,
        selectedTaskSources.map((source) => source.label)
      )
    : [];
  const selectedTaskHumanEvidence = selectedTask
    ? buildHumanEvidenceChips(selectedTask, orderedTaskEvidence, orderedTaskFactChips, selectedTaskSources)
    : [];
  const navigationItems: Array<{ view: AppView; label: string; description: string }> = [
    { view: "checklist", label: "Checklist", description: "Your next three moves" },
    { view: "know-more", label: "Know More", description: "What we learned and why" },
    { view: "sources-jobs", label: "Sources", description: "What we monitor for you" },
  ];
  const activeNavigationItem = navigationItems.find((item) => item.view === activeView) ?? navigationItems[0];
  const topbarSummary =
    activeView === "checklist"
      ? `${tasks.length} ranked moves`
      : activeView === "know-more"
        ? `${visibleFlashcards.length} flashcards · ${filteredKnowledgeCards.length} cards`
        : `${workspace?.source_cards.length ?? 0} monitored sources`;

  return (
    <section className="decision-shell">
      <aside className="workspace-sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">AC</div>
          <div>
            <strong>Agent.Chappie</strong>
            <span>Operator intelligence workspace</span>
          </div>
        </div>

        <div className="sidebar-panel">
          <span className="sidebar-label">Live system</span>
          <strong>{currentStatus}</strong>
          <p>{systemStatusLine}</p>
        </div>

        <nav className="surface-nav sidebar-nav" aria-label="Primary product sections">
          {navigationItems.map((item) => (
            <button
              key={item.view}
              className={`surface-tab sidebar-tab ${activeView === item.view ? "active" : ""}`}
              onClick={() => setActiveView(item.view)}
              type="button"
            >
              <span>{item.label}</span>
              <small>{item.description}</small>
            </button>
          ))}
        </nav>

        <div className="sidebar-metrics">
          <div className="status-stack">
            <span className="status-label">Project</span>
            <strong>{projectLabel}</strong>
            <small>{activeView === "checklist" ? "Decision mode" : activeView === "know-more" ? "Intelligence mode" : "Monitoring mode"}</small>
            <small>{tasks.find((task) => task.is_next_best_action)?.title ?? "Waiting for the next strong move"}</small>
          </div>
          <div className="status-stack">
            <span className="status-label">Confidence</span>
            <strong>
              {confidenceLabel(confidence)}
              {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
            </strong>
          </div>
          <div className="status-stack">
            <span className="status-label">Evidence</span>
            <strong>
              {workspace?.source_cards.length ?? 0} sources · {workspace?.recent_activity.length ?? 0} signals
            </strong>
          </div>
        </div>
      </aside>

      <div className="workspace-main">
        <header className="decision-header panel">
          <div className="decision-header-copy">
            <div className="eyebrow">Competitive action engine</div>
            <h1>We analyze your competitive environment and recommend your next 3 moves.</h1>
            <p>
              Drop one source. Agent.Chappie extracts signals, builds market intelligence, and surfaces actions you can
              execute this week when a strong advantage appears.
            </p>
          </div>
        </header>

        <section className="workspace-toolbar panel" aria-label="Workspace context">
          <div className="workspace-toolbar-copy">
            <span className="section-kicker">Workspace view</span>
            <strong>{activeNavigationItem.label}</strong>
            <p>{activeNavigationItem.description}</p>
          </div>
          <div className="workspace-toolbar-metrics">
            <div className="toolbar-chip">
              <span>Focus</span>
              <strong>{topbarSummary}</strong>
            </div>
            <div className="toolbar-chip">
              <span>Sources</span>
              <strong>{workspace?.source_cards.length ?? 0}</strong>
            </div>
            <div className="toolbar-chip">
              <span>Signals</span>
              <strong>{workspace?.recent_activity.length ?? 0}</strong>
            </div>
            <div className="toolbar-chip">
              <span>Tasks</span>
              <strong>{tasks.length}</strong>
            </div>
          </div>
        </section>

        {activeView === "checklist" ? (
        <section className="content-grid">
          <div className="primary-column">
            <section className="panel section-card">
              <div className="section-head">
                <div>
                  <span className="section-kicker">Your Checklist</span>
                  <h2>Exactly three actions. No dashboard clutter.</h2>
                  <p className="section-subcopy">The checklist stays focused on the next moves that matter most right now.</p>
                </div>
                <div className="section-head-badges">
                  <span className="status-pill">{currentStatus}</span>
                  <span className="section-count-badge">{tasks.length} tasks live</span>
                </div>
              </div>

              {submissionError ? (
                <div className="notice error">
                  <strong>Input problem</strong>
                  <p>{submissionError}</p>
                </div>
              ) : null}

              {completeResult ? (
                <div className="task-card-list">
                  {tasks.map((task) => {
                    const decision = taskDecisions[task.rank];
                    return (
                      <article className="checklist-card" key={task.rank}>
                        <div className="task-rank">{task.rank}</div>
                        <div className="task-content">
                          <h3>{task.title}</h3>
                          <div className="task-meta-row">
                            <div className="task-meta">Priority: {priorityLabel(task.priority_label)}</div>
                            <div className="task-meta">Best before: {task.best_before ?? "This week"}</div>
                            <div className="task-meta">Confidence: {confidenceLabel(confidence)}{confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}</div>
                            {task.is_next_best_action ? <div className="task-meta nba">Next best action</div> : null}
                          </div>
                          <div className="task-block impact">
                            <span>Expected impact</span>
                            <p>{task.expected_advantage}</p>
                          </div>
                          <p className="task-preview">{task.why_now}</p>

                          <div className="task-actions">
                            <button
                              className={`decision-button detail ${selectedTask?.rank === task.rank ? "selected" : ""}`}
                              type="button"
                              onClick={() => setSelectedTask(task)}
                            >
                              View detail
                            </button>
                            <button
                              className={`decision-button done ${decision?.status === "done" ? "selected" : ""}`}
                              type="button"
                              onClick={() => void submitSingleDecision(task, "done")}
                            >
                              ✓ Done
                            </button>
                            <button
                              className={`decision-button adjust ${decision?.status === "edited" ? "selected" : ""}`}
                              type="button"
                              onClick={() => setDecision(task.rank, "edited", task.title)}
                            >
                              ✎ Adjust
                            </button>
                            <button
                              className={`decision-button reject ${decision?.status === "deleted_silent" ? "selected" : ""}`}
                              type="button"
                              onClick={() => void submitSingleDecision(task, "deleted_silent")}
                            >
                              Delete
                            </button>
                            <button
                              className={`decision-button reject ${decision?.status === "deleted_with_annotation" ? "selected" : ""}`}
                              type="button"
                              onClick={() => setDecision(task.rank, "deleted_with_annotation", task.title)}
                            >
                              Delete and teach
                            </button>
                            <button
                              className={`decision-button adjust ${decision?.status === "held_for_later" ? "selected" : ""}`}
                              type="button"
                              onClick={() => setDecision(task.rank, "held_for_later", task.title)}
                            >
                              Hold for later
                            </button>
                            <button
                              className={`decision-button adjust ${decision?.status === "commented" ? "selected" : ""}`}
                              type="button"
                              onClick={() => setDecision(task.rank, "commented", task.title)}
                            >
                              Comment
                            </button>
                            {findTaskSourceRef(task) ? (
                              <button
                                className="decision-button reject"
                                type="button"
                                onClick={() => {
                                  const sourceRef = findTaskSourceRef(task);
                                  if (sourceRef) {
                                    void deleteIngestedSource(sourceRef);
                                  }
                                }}
                              >
                                Remove source and rebuild
                              </button>
                            ) : null}
                          </div>

                          {decision?.status === "edited" ? (
                            <div className="adjust-shell">
                              <label htmlFor={`adjust-${task.rank}`}>Adjusted action</label>
                              <textarea
                                id={`adjust-${task.rank}`}
                                value={decision.adjustedText}
                                onChange={(event) => setAdjustedText(task.rank, event.target.value)}
                                onBlur={(event) => void submitSingleDecision(task, "edited", { adjustedText: event.target.value })}
                              />
                            </div>
                          ) : null}
                          {decision?.status === "edited" ||
                          decision?.status === "declined" ||
                          decision?.status === "commented" ||
                          decision?.status === "deleted_with_annotation" ||
                          decision?.status === "held_for_later" ? (
                            <div className="adjust-shell">
                              <label htmlFor={`comment-${task.rank}`}>Why?</label>
                              <textarea
                                id={`comment-${task.rank}`}
                                value={decision.commentText}
                                onChange={(event) => setCommentText(task.rank, event.target.value)}
                                onBlur={(event) =>
                                  void submitSingleDecision(task, decision?.status ?? "commented", {
                                    adjustedText: taskDecisions[task.rank]?.adjustedText,
                                    commentText: event.target.value,
                                  })
                                }
                                placeholder="Tell us what was wrong, what We should avoid, or why this should wait."
                              />
                            </div>
                          ) : null}
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : blockedResult ? (
                <div className="notice error">
                  <strong>No immediate move detected</strong>
                  <p>
                    We processed the source and drafted knowledge from it, but no pricing, offer, closure, or timing
                    signal was strong enough yet to justify three high-confidence moves this week.
                  </p>
                  <p>{blockedReason}</p>
                  {workspace?.fact_chips.length ? (
                    <div className="task-block">
                      <span>Atomic facts we still hold from this source</span>
                      <ul>
                        {workspace.fact_chips.slice(0, 6).map((chip) => (
                          <li key={chip.fact_id}>
                            {humanizeFactCategory(chip.category)}: {chip.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <p>
                    We still processed the source. We are monitoring pricing shifts, competitor positioning, and offer
                    changes from it. Open Know More to review the current intelligence, or add another source if you
                    want us to push toward a checklist move.
                  </p>
                  <div className="guided-actions">
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => setActiveView("know-more")}
                    >
                      Open Know More
                    </button>
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => {
                        setActiveView("sources-jobs");
                      }}
                    >
                      Add another source
                    </button>
                  </div>
                </div>
              ) : (
                <div className="empty-state guided-empty-state">
                  <h3>No actions recommended yet</h3>
                  <p>
                    We need at least one strong signal before the checklist appears:
                    pricing change, competitor move, offer shift, or closure / expansion signal.
                  </p>
                  <div className="guided-grid">
                    <article className="guided-card">
                      <strong>Competitor website</strong>
                      <p>Detect pricing moves, offers, positioning claims, and proof signals.</p>
                    </article>
                    <article className="guided-card">
                      <strong>Internal notes</strong>
                      <p>Extract risks, opportunities, objections, and timing pressure from messy updates.</p>
                    </article>
                    <article className="guided-card">
                      <strong>Market documents</strong>
                      <p>Map competitors, packaging pressure, proof patterns, and strategy shifts.</p>
                    </article>
                  </div>
                  <div className="panel-lite">
                    <strong>Example output</strong>
                    <ul>
                      <li>Launch a 7-day trial response this week before Essex captures price-sensitive leads.</li>
                      <li>Call Westover owner now and secure first access to players and assets before closure finalizes.</li>
                      <li>Launch a U14 comparison offer before the next intake cycle resets buyer expectations.</li>
                    </ul>
                  </div>
                  <div className="guided-actions">
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => {
                        setInputMode("text");
                        setActiveView("sources-jobs");
                      }}
                    >
                      Add a source
                    </button>
                  </div>
                </div>
              )}
            </section>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Task Detail</span>
                  <h2>{selectedTask ? `Why task ${selectedTask.rank} exists` : "Open a task to inspect the reasoning"}</h2>
                  <p className="section-subcopy">Task detail is a one-to-one explanation surface for a single action, not the global knowledge view.</p>
                </div>
              </div>

              {selectedTask ? (
                <div className="task-detail-shell">
                  <div className="summary-stack">
                    <div className="summary-row">
                      <span>Action</span>
                      <strong>{selectedTask.title}</strong>
                    </div>
                    <div className="summary-row">
                      <span>Expected impact</span>
                      <strong>{selectedTask.expected_advantage}</strong>
                    </div>
                    <div className="summary-row">
                      <span>Priority</span>
                      <strong>{priorityLabel(selectedTask.priority_label)}</strong>
                    </div>
                    <div className="summary-row">
                      <span>Best before</span>
                      <strong>{selectedTask.best_before ?? "This week"}</strong>
                    </div>
                    <div className="summary-row">
                      <span>Confidence</span>
                      <strong>
                        {confidenceLabel(confidence)}
                        {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
                      </strong>
                    </div>
                    {selectedTask.target_channel ? (
                      <div className="summary-row">
                        <span>Target channel</span>
                        <strong>{selectedTask.target_channel}</strong>
                      </div>
                    ) : null}
                    {selectedTask.target_segment ? (
                      <div className="summary-row">
                        <span>Target segment</span>
                        <strong>{selectedTask.target_segment}</strong>
                      </div>
                    ) : null}
                    {selectedTask.competitor_name ? (
                      <div className="summary-row">
                        <span>Competitor</span>
                        <strong>{selectedTask.competitor_name}</strong>
                      </div>
                    ) : null}
                  </div>

                  <div className="task-block">
                    <span>Why this task</span>
                    <p>{selectedTask.why_now}</p>
                  </div>

                  <div className="task-block">
                    <span>What happens if you ignore it</span>
                    <p>{buildConsequenceOfInaction(selectedTask)}</p>
                  </div>

                  {selectedTask.strongest_evidence_excerpt ? (
                    <div className="task-block">
                      <span>Strongest evidence</span>
                      <p>{selectedTask.strongest_evidence_excerpt}</p>
                    </div>
                  ) : null}

                  <div className="task-detail-list">
                    <h3>Execution steps</h3>
                    <ol className="compact-run-list">
                      {selectedTaskSteps.map((step, index) => (
                        <li key={`${selectedTask.rank}-step-${index}`}>{step}</li>
                      ))}
                    </ol>
                  </div>

                  {selectedTask.done_definition ? (
                    <div className="task-block">
                      <span>Done looks like</span>
                      <p>{selectedTask.done_definition}</p>
                    </div>
                  ) : null}

                  <div className="task-evidence">
                    <span>Evidence</span>
                    <div className="evidence-chip-list">
                      {selectedTaskHumanEvidence.map((item, index) => (
                        <span className="evidence-chip" key={`${selectedTask.rank}-evidence-${index}`}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="task-detail-list">
                    <h3>Linked signals</h3>
                    {orderedTaskEvidence.length ? (
                      orderedTaskEvidence.map((activity) => (
                        <div className="job-item" key={activity.signal_id}>
                          <strong>{humanizeSignalType(activity.signal_type)}</strong>
                          <span>
                            {supportStrengthLabel(selectedTaskSignalScoreMap.get(activity.signal_id)?.relevance_score)} ·{" "}
                            {formatTimestamp(activity.observed_at)}
                          </span>
                          <p>{activity.summary}</p>
                        </div>
                      ))
                    ) : (
                      <p className="surface-summary">No linked signals are available for this task yet.</p>
                    )}
                  </div>

                  <div className="task-detail-list">
                    <h3>Linked sources</h3>
                    {selectedTaskSources.length ? (
                      selectedTaskSources.map((source) => (
                        <div className="job-item" key={source.source_ref}>
                          <strong>{source.label}</strong>
                          <span>
                            {supportStrengthLabel(selectedTaskSourceScoreMap.get(source.source_ref)?.relevance_score)} ·{" "}
                            {sourceKindLabel(source.source_kind)} · {formatTimestamp(source.created_at)}
                          </span>
                          {selectedTaskSourceScoreMap.get(source.source_ref)?.strongest_excerpt ? (
                            <p>{selectedTaskSourceScoreMap.get(source.source_ref)?.strongest_excerpt}</p>
                          ) : null}
                          <p>{source.processing_summary}</p>
                        </div>
                      ))
                    ) : (
                      <p className="surface-summary">No linked source cards are available for this task yet.</p>
                    )}
                  </div>

                </div>
              ) : (
                <div className="empty-state">
                  <h3>No task selected</h3>
                  <p>Open one checklist card to inspect why it was chosen, what evidence supports it, and which sources shaped it.</p>
                </div>
              )}
            </section>
          </aside>
        </section>
        ) : null}

        {activeView === "know-more" ? (
        <section className="content-grid single">
          <div className="primary-column">
            <section className="panel section-card intelligence-layout">
              <div className="section-head">
                <div>
                  <span className="section-kicker">Know More</span>
                  <h2>Structured knowledge from the source set</h2>
                  <p className="section-subcopy">Know More is the knowledge surface. It stays useful even when the checklist is blocked.</p>
                </div>
                <span className="section-count-badge">
                  {workspace?.fact_chips.length ?? 0} flashcards · {filteredKnowledgeCards.length} cards
                </span>
              </div>
              {focusedSourceRef ? (
                <div className="notice success">
                  <p>
                    Filtering knowledge to source <strong>{humanSourceLabel(focusedSourceRef)}</strong>.
                  </p>
                  <button className="button-secondary" type="button" onClick={() => setFocusedSourceRef(null)}>
                    Show all knowledge
                  </button>
                </div>
              ) : null}

              {hasCompetitiveSnapshotData ? (
              <article className="intel-card snapshot-card">
                <div className="operator-head">
                  <h3>Competitive Position Snapshot</h3>
                  <span>{workspace?.competitive_snapshot.reference_competitor ?? ""}</span>
                </div>
                <div className="summary-stack">
                  {workspace?.competitive_snapshot.pricing_position ? (
                  <div className="summary-row">
                    <span>Pricing position</span>
                    <strong>{workspace?.competitive_snapshot.pricing_position}</strong>
                  </div>
                  ) : null}
                  {workspace?.competitive_snapshot.acquisition_strategy_comparison ? (
                  <div className="summary-row">
                    <span>Acquisition comparison</span>
                    <strong>{workspace?.competitive_snapshot.acquisition_strategy_comparison}</strong>
                  </div>
                  ) : null}
                  {workspace?.competitive_snapshot.current_weakness ? (
                  <div className="summary-row">
                    <span>Current weakness</span>
                    <strong>{workspace?.competitive_snapshot.current_weakness}</strong>
                  </div>
                  ) : null}
                  {workspace?.competitive_snapshot.risk_level ? (
                  <div className="summary-row">
                    <span>Risk level</span>
                    <strong>{titleCaseWords(workspace?.competitive_snapshot.risk_level)}</strong>
                  </div>
                  ) : null}
                </div>
                {(workspace?.competitive_snapshot.active_threats ?? []).length ? (
                <div className="task-block">
                  <span>Active threats</span>
                  <ul>
                    {(workspace?.competitive_snapshot.active_threats ?? []).map((item, index) => (
                      <li key={`threat-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
                ) : null}
                {(workspace?.competitive_snapshot.immediate_opportunities ?? []).length ? (
                <div className="task-block">
                  <span>Immediate opportunities</span>
                  <ul>
                    {(workspace?.competitive_snapshot.immediate_opportunities ?? []).map((item, index) => (
                      <li key={`opportunity-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
                ) : null}
              </article>
              ) : null}

              {visibleFlashcards.length ? (
                <article className="intel-card">
                  <div className="operator-head">
                    <h3>Knowledge flashcards</h3>
                    <span>{visibleFlashcards.length} visible cards (top 20%)</span>
                  </div>
                  <p className="section-subcopy" style={{ marginTop: 0 }}>
                    Each flashcard is the smallest unit of knowledge we store and use when recommending your next best
                    actions. Only two operations are supported here, as agreed.
                  </p>
                  <div className="flashcard-deck">
                    {visibleFlashcards.map((card) => (
                      <article
                        className={`intel-card mini flashcard ${classifyOriginFromSourceRefs(card.source_refs, autoCollectedSourceRefs)}`}
                        key={card.card_id}
                      >
                        <div className="operator-head">
                          <h3>{titleCaseWords(card.segment || "card")}</h3>
                          <span>
                            {confidenceLabel(card.confidence)} ({card.confidence.toFixed(2)}) · impact{" "}
                            {Math.round(card.impact_score)}
                          </span>
                        </div>
                        <p className="surface-summary">{originLabel(classifyOriginFromSourceRefs(card.source_refs, autoCollectedSourceRefs))}</p>
                        <p className="flashcard-body">{card.insight}</p>
                        <p className="surface-summary">{card.implication}</p>
                        {card.potential_moves.length ? (
                          <ul>
                            {card.potential_moves.slice(0, 2).map((move, index) => (
                              <li key={`${card.card_id}-move-${index}`}>{move}</li>
                            ))}
                          </ul>
                        ) : null}
                        {card.expires_at ? <p className="surface-summary">Expires {formatTimestamp(card.expires_at)}</p> : null}
                        {card.source_refs[0] ? (
                          <button
                            className="button-secondary flashcard-source-link"
                            type="button"
                            onClick={() => setFocusedSourceRef(card.source_refs[0] ?? null)}
                          >
                            View linked source
                          </button>
                        ) : null}
                        <div className="task-actions compact-actions flashcard-actions">
                          <button
                            className="decision-button"
                            type="button"
                            onClick={() => void actOnFactFlashcard(card.card_id, "forget")}
                          >
                            Delete and forget
                          </button>
                          <button
                            className="decision-button reject"
                            type="button"
                            onClick={() =>
                              setFlashcardTeachOpen((current) => ({
                                ...current,
                                [card.card_id]: !current[card.card_id],
                              }))
                            }
                          >
                            Delete and teach
                          </button>
                        </div>
                        {flashcardTeachOpen[card.card_id] ? (
                          <div className="adjust-shell">
                            <label htmlFor={`flashcard-teach-${card.card_id}`}>What should we avoid next time?</label>
                            <textarea
                              id={`flashcard-teach-${card.card_id}`}
                              value={flashcardTeachNote[card.card_id] ?? ""}
                              onChange={(event) =>
                                setFlashcardTeachNote((current) => ({
                                  ...current,
                                  [card.card_id]: event.target.value,
                                }))
                              }
                              placeholder="Tell us what pattern should be avoided in the future."
                            />
                            <div className="task-actions compact-actions">
                              <button
                                className="decision-button reject"
                                type="button"
                                onClick={() => void actOnFactFlashcard(card.card_id, "teach")}
                              >
                                Confirm teach
                              </button>
                              <button
                                className="decision-button"
                                type="button"
                                onClick={() =>
                                  setFlashcardTeachOpen((current) => ({
                                    ...current,
                                    [card.card_id]: false,
                                  }))
                                }
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </article>
              ) : null}

              <div className="intel-columns">
                {filteredKnowledgeCards.length ? (
                  filteredKnowledgeCards.map((card) => (
                    <article
                      className={`intel-card ${classifyOriginFromSourceRefs(card.source_refs, autoCollectedSourceRefs)}`}
                      key={card.knowledge_id}
                    >
                      <div className="operator-head">
                        <h3>{card.title}</h3>
                        <span>
                          {confidenceLabel(card.confidence)} ({card.confidence.toFixed(2)}) · {card.annotation_status} · {confidenceSourceLabel(card.confidence_source)}
                        </span>
                      </div>
                      <p className="surface-summary">
                        {classifyOriginFromSourceRefs(card.source_refs, autoCollectedSourceRefs) === "auto-collected"
                          ? "We researched this from public web sources and merged it into the local brain."
                          : classifyOriginFromSourceRefs(card.source_refs, autoCollectedSourceRefs) === "mixed-origin"
                            ? "This card combines your source with our public web research."
                            : "This card comes directly from the sources you provided."}
                      </p>
                      <p>{card.summary}</p>
                      <div className="task-block">
                        <span>Insight</span>
                        <p>{card.insight}</p>
                      </div>
                      <div className="task-block">
                        <span>Implication</span>
                        <p>{card.implication}</p>
                      </div>
                      {card.strongest_excerpt ? (
                        <div className="task-block">
                          <span>Strongest excerpt</span>
                          <p>{card.strongest_excerpt}</p>
                        </div>
                      ) : null}
                      <div className="task-block">
                        <span>Potential moves</span>
                        <ul>
                          {card.potential_moves.map((move, index) => (
                            <li key={`${card.knowledge_id}-move-${index}`}>{move}</li>
                          ))}
                        </ul>
                      </div>
                      <ul>
                        {card.items.map((item, index) => (
                          <li key={`${card.knowledge_id}-${index}`}>{item}</li>
                        ))}
                      </ul>
                      <div className="summary-stack">
                        <div className="summary-row">
                          <span>Supporting units</span>
                          <strong>{card.support_count ?? card.items.length}</strong>
                        </div>
                        <div className="summary-row">
                          <span>Supporting sources</span>
                          <strong>{card.source_refs.length}</strong>
                        </div>
                      </div>
                      <div className="evidence-chip-list">
                        {card.source_refs.map((sourceRef) => (
                          <button
                            className="evidence-chip"
                            key={sourceRef}
                            type="button"
                            onClick={() => setFocusedSourceRef(sourceRef)}
                          >
                            {humanSourceLabel(sourceRef)}
                          </button>
                        ))}
                      </div>
                      {editingKnowledgeId === card.knowledge_id ? (
                        <div className="management-form">
                          <input
                            value={knowledgeDraft.title}
                            onChange={(event) =>
                              setKnowledgeDraft((current) => ({ ...current, title: event.target.value }))
                            }
                            placeholder="Card title"
                          />
                          <textarea
                            value={knowledgeDraft.summary}
                            onChange={(event) =>
                              setKnowledgeDraft((current) => ({ ...current, summary: event.target.value }))
                            }
                            placeholder="Corrected summary"
                          />
                          <textarea
                            value={knowledgeDraft.implication}
                            onChange={(event) =>
                              setKnowledgeDraft((current) => ({ ...current, implication: event.target.value }))
                            }
                            placeholder="Corrected implication"
                          />
                          <textarea
                            value={knowledgeDraft.potentialMoves}
                            onChange={(event) =>
                              setKnowledgeDraft((current) => ({ ...current, potentialMoves: event.target.value }))
                            }
                            placeholder="One potential move per line"
                          />
                          <textarea
                            value={knowledgeDraft.items}
                            onChange={(event) =>
                              setKnowledgeDraft((current) => ({ ...current, items: event.target.value }))
                            }
                            placeholder="One corrected item per line"
                          />
                          <div className="task-actions compact-actions">
                            <button
                              className="button-primary"
                              type="button"
                              onClick={() =>
                                void updateKnowledgeCard(card.knowledge_id, {
                                  status: "edited",
                                  confidence_source: "user_modified",
                                  original_payload: card.audit.original_value,
                                  corrected_title: knowledgeDraft.title.trim() || card.title,
                                  corrected_summary: knowledgeDraft.summary.trim() || card.summary,
                                  corrected_implication: knowledgeDraft.implication.trim() || card.implication,
                                  corrected_potential_moves: knowledgeDraft.potentialMoves
                                    .split("\n")
                                    .map((item) => item.trim())
                                    .filter(Boolean),
                                  corrected_items: knowledgeDraft.items
                                    .split("\n")
                                    .map((item) => item.trim())
                                    .filter(Boolean),
                                })
                              }
                            >
                              Save correction
                            </button>
                            <button
                              className="button-secondary"
                              type="button"
                              onClick={() => {
                                setEditingKnowledgeId(null);
                                setKnowledgeDraft({ title: "", summary: "", implication: "", potentialMoves: "", items: "" });
                              }}
                            >
                              Close
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="task-actions compact-actions">
                          <button
                            className="decision-button done"
                            type="button"
                            onClick={() =>
                              void updateKnowledgeCard(card.knowledge_id, {
                                status: "confirmed",
                                confidence_source: "user_confirmed",
                                original_payload: card.audit.original_value,
                              })
                            }
                          >
                            Confirm
                          </button>
                          <button
                            className="decision-button adjust"
                            type="button"
                            onClick={() => {
                              setEditingKnowledgeId(card.knowledge_id);
                              setKnowledgeDraft({
                                title: card.title,
                                summary: card.summary,
                                implication: card.implication,
                                potentialMoves: card.potential_moves.join("\n"),
                                items: card.items.join("\n"),
                              });
                            }}
                          >
                            Edit
                          </button>
                          <button
                            className="decision-button"
                            type="button"
                            onClick={() =>
                              void updateKnowledgeCard(card.knowledge_id, {
                                status: "held_for_later",
                                confidence_source: "user_modified",
                                original_payload: card.audit.original_value,
                              })
                            }
                          >
                            Hold for later
                          </button>
                          <button
                            className="decision-button reject"
                            type="button"
                            onClick={() =>
                              void deleteKnowledgeCard(card.knowledge_id, {
                                status: "deleted_silent",
                                original_payload: card.audit.original_value,
                              })
                            }
                          >
                            Delete
                          </button>
                          <button
                            className="decision-button reject"
                            type="button"
                            onClick={() =>
                              void deleteKnowledgeCard(card.knowledge_id, {
                                status: "deleted_with_annotation",
                                original_payload: card.audit.original_value,
                                reason:
                                  knowledgeDeleteReason[card.knowledge_id]?.trim() ||
                                  "Avoid this card pattern in future generations.",
                              })
                            }
                          >
                            Delete and teach
                          </button>
                        </div>
                      )}

                      {editingKnowledgeId !== card.knowledge_id ? (
                        <div className="adjust-shell">
                          <label htmlFor={`knowledge-delete-reason-${card.knowledge_id}`}>What should we avoid?</label>
                          <textarea
                            id={`knowledge-delete-reason-${card.knowledge_id}`}
                            value={knowledgeDeleteReason[card.knowledge_id] ?? ""}
                            onChange={(event) =>
                              setKnowledgeDeleteReason((current) => ({
                                ...current,
                                [card.knowledge_id]: event.target.value,
                              }))
                            }
                            placeholder="Optional for Delete. Use this if you want Delete and teach to record what we should avoid."
                          />
                        </div>
                      ) : null}

                      {card.audit.timestamp ? (
                        <div className="task-block">
                          <span>Knowledge edit audit</span>
                          <p>
                            Last updated {formatTimestamp(card.audit.timestamp)} from {confidenceSourceLabel(card.confidence_source)}.
                          </p>
                        </div>
                      ) : null}
                    </article>
                  ))
                ) : (
                  <article className="intel-card">
                    <h3>No knowledge cards yet</h3>
                    <p>Upload a real source and we will surface market knowledge here, even if no immediate task is strong enough yet.</p>
                  </article>
                )}
              </div>
            </section>
          </div>
        </section>
        ) : null}

        {activeView === "sources-jobs" ? (
        <section className="content-grid">
          <div className="primary-column">
            <section className="panel section-card">
              <div className="section-head">
                <div>
                  <span className="section-kicker">Sources</span>
                  <h2>Monitor your market and capture signals automatically.</h2>
                  <p className="section-subcopy">Add one source with its repeat cadence. We will watch it, synthesize what changed, and surface actions when a strong move emerges.</p>
                </div>
                <span className="section-count-badge">{workspace?.source_cards.length ?? 0} sources</span>
              </div>

              <div className="monitoring-actions">
                <button
                  className="button-primary"
                  type="button"
                  onClick={() => {
                    setShowSourceComposer((current) => !current);
                  }}
                >
                  {showSourceComposer || editingSourceId ? "Hide source setup" : "Add source"}
                </button>
              </div>

              {workspace ? (
                <div className="compact-meta">
                  <div className="summary-row">
                    <span>Ingested sources in this workspace</span>
                    <strong>{workspace.source_cards.length}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Recent signals available</span>
                    <strong>{workspace.recent_activity.length}</strong>
                  </div>
                </div>
              ) : projectId ? (
                <div className="notice">
                  <p>Loading the current workspace…</p>
                </div>
              ) : (
                <div className="notice">
                  <p>No project is loaded in this browser session yet. Add one source here to start a workspace, or return to the session that created the earlier sources.</p>
                </div>
              )}

              {showSourceComposer || editingSourceId ? (
                <div className="operator-composer">
                  <div className="management-form compact-form">
                    <label>
                      Relation
                      <select
                        value={sourceForm.relation}
                        onChange={(event) =>
                          setSourceForm((current) => ({
                            ...current,
                            relation: event.target.value as SourceFormState["relation"],
                          }))
                        }
                      >
                        <option value="general">General</option>
                        <option value="industry">Industry</option>
                        <option value="competitors">Competitors</option>
                        <option value="my_business">My business</option>
                      </select>
                    </label>
                    <label>
                      Upload a document
                      <input
                        type="file"
                        accept=".txt,.md,.rtf,.pdf,.doc,.docx,application/pdf,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        onChange={(event) => setSourceUploadFile(event.target.files?.[0] ?? null)}
                      />
                    </label>
                    <label>
                      Description
                      <input
                        value={sourceForm.description}
                        onChange={(event) => setSourceForm((current) => ({ ...current, description: event.target.value }))}
                        placeholder="Optional context for this source"
                      />
                    </label>
                    <label>
                      Hashtags
                      <input
                        value={sourceForm.hashtags}
                        onChange={(event) => setSourceForm((current) => ({ ...current, hashtags: event.target.value }))}
                        placeholder="#pricing #offer #churn"
                      />
                    </label>
                    <details className="optional-fields">
                      <summary>Add a source label (optional)</summary>
                      <input
                        value={sourceForm.label}
                        onChange={(event) => setSourceForm((current) => ({ ...current, label: event.target.value }))}
                        placeholder="Short source label"
                      />
                    </details>
                    <label>
                      Repeat
                      <select
                        value={sourceForm.repeatInterval}
                        onChange={(event) =>
                          setSourceForm((current) => ({
                            ...current,
                            repeatInterval: event.target.value as SourceFormState["repeatInterval"],
                          }))
                        }
                      >
                        <option value="never">Never</option>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                        <option value="quarterly">Quarterly</option>
                        <option value="yearly">Yearly</option>
                      </select>
                    </label>
                    <label>
                      Content / Notes
                      <textarea
                        value={sourceForm.contentNotes}
                        onChange={(event) => setSourceForm((current) => ({ ...current, contentNotes: event.target.value }))}
                        placeholder="Paste context notes or copied source text"
                      />
                    </label>
                    <label>
                      URL
                      <input
                        value={sourceForm.url}
                        onChange={(event) => setSourceForm((current) => ({ ...current, url: event.target.value }))}
                        placeholder="https://example.com/page"
                      />
                    </label>
                    <div className="task-actions compact-actions">
                      <button className="button-primary" type="button" onClick={() => void handleCreateSource()}>
                        {editingSourceId ? "Save source" : "Add source"}
                      </button>
                      <button
                        className="button-secondary"
                        type="button"
                        onClick={() => {
                          setEditingSourceId(null);
                          setShowSourceComposer(false);
                          setSourceForm({
                            label: "",
                            relation: "general",
                            repeatInterval: "never",
                            url: "",
                            contentNotes: "",
                            description: "",
                            hashtags: "",
                          });
                          setSourceUploadFile(null);
                        }}
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              {false ? (
                <div className="operator-composer secondary-composer">
                  <div className="task-block">
                    <span>Monitoring job</span>
                    <p>Use jobs when a source should run again on a schedule or on a trigger.</p>
                  </div>
                  <div className="management-form compact-form">
                    <input
                      value={jobForm.name}
                      onChange={(event) => setJobForm((current) => ({ ...current, name: event.target.value }))}
                      placeholder="Monitoring job name"
                    />
                    <div className="guided-actions">
                      <button className={`mode-chip ${jobForm.triggerType === "manual" ? "active" : ""}`} type="button" onClick={() => setJobForm((current) => ({ ...current, triggerType: "manual" }))}>
                        Manual
                      </button>
                      <button className={`mode-chip ${jobForm.triggerType === "recurring" ? "active" : ""}`} type="button" onClick={() => setJobForm((current) => ({ ...current, triggerType: "recurring" }))}>
                        Recurring
                      </button>
                      <button className={`mode-chip ${jobForm.triggerType === "event" ? "active" : ""}`} type="button" onClick={() => setJobForm((current) => ({ ...current, triggerType: "event" }))}>
                        Event
                      </button>
                    </div>
                    <input
                      value={jobForm.scheduleText}
                      onChange={(event) => setJobForm((current) => ({ ...current, scheduleText: event.target.value }))}
                      placeholder="Schedule or trigger description"
                    />
                    <input
                      value={jobForm.sourceId}
                      onChange={(event) => setJobForm((current) => ({ ...current, sourceId: event.target.value }))}
                      placeholder="Linked source id (optional)"
                    />
                    <div className="task-actions compact-actions">
                      <button className="button-primary" type="button" onClick={() => void handleCreateJob()}>
                        {editingJobId ? "Save job" : "Add job"}
                      </button>
                      <button
                        className="button-secondary"
                        type="button"
                        onClick={() => {
                          setEditingJobId(null);
                          setShowJobComposer(false);
                          setJobForm({ name: "", triggerType: "manual", scheduleText: "", sourceId: "" });
                        }}
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              {managementStatus ? (
                <div className={`notice ${managementStatus.tone}`}>
                  <p>{managementStatus.message}</p>
                </div>
              ) : null}

              <div className="sources-workspace">
                {workspace?.managed_sources.length ? (
                  <div className="monitoring-secondary">
                    <div className="section-head compact">
                      <div>
                        <span className="section-kicker">Monitoring</span>
                        <h3>Source rules</h3>
                      </div>
                    </div>
                    <div className="secondary-assets">
                      {workspace.managed_sources.map((source) => (
                        <article className="job-item" key={source.source_id}>
                          <strong>{source.label}</strong>
                          <span>
                            {titleCaseWords(source.source_kind)} · {source.status}
                          </span>
                          <span>Repeat: {titleCaseWords(source.repeat_interval ?? "never")}</span>
                          <p>{source.content_text}</p>
                          <div className="task-actions compact-actions">
                            <button
                              className="decision-button adjust"
                              type="button"
                              onClick={() => {
                                setEditingSourceId(source.source_id);
                                setShowSourceComposer(true);
                                setSourceForm({
                                  label: source.label,
                                  relation: "general",
                                  repeatInterval: source.repeat_interval ?? "never",
                                  url: source.source_kind === "url" ? source.content_text : "",
                                  contentNotes: source.source_kind === "manual_text" ? source.content_text : "",
                                  description: "",
                                  hashtags: "",
                                });
                              }}
                            >
                              Edit
                            </button>
                            <button className="decision-button" type="button" onClick={() => void updateSource(source.source_id, { status: source.status === "active" ? "paused" : "active" })}>
                              {source.status === "active" ? "Pause" : "Resume"}
                            </button>
                            <button className="decision-button reject" type="button" onClick={() => void deleteSource(source.source_id)}>
                              Delete rule
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                ) : null}

                {workspace?.source_cards.length ? (
                  workspace.source_cards.map((source) => (
                    <article
                      className={`source-asset ${focusedSourceRef === source.source_ref ? "current" : ""} ${isAutoCollectedSourceKind(source.source_kind) ? "auto-collected" : "user-provided"}`}
                      key={source.source_ref}
                    >
                      <div className="operator-head">
                        <div>
                          <strong>{source.label}</strong>
                          <span>
                            {sourceKindLabel(source.source_kind)} · Last update {formatTimestamp(source.created_at)}
                          </span>
                        </div>
                        <span className="asset-badge">
                          {originLabel(isAutoCollectedSourceKind(source.source_kind) ? "auto-collected" : "user-provided")} · {source.signal_count} signals
                        </span>
                      </div>
                      <div className="task-block">
                        <span>Key change</span>
                        <p>{source.key_takeaway}</p>
                      </div>
                      <div className="task-block">
                        <span>Impact</span>
                        <p>{source.business_impact}</p>
                      </div>
                      <div className="summary-stack">
                        <div className="summary-row">
                          <span>Confidence</span>
                          <strong>{confidenceLabel(source.confidence)} ({source.confidence.toFixed(2)})</strong>
                        </div>
                        <div className="summary-row">
                          <span>Used in</span>
                          <strong>{source.linked_tasks.length ? `Task #${Math.min(source.linked_tasks.length, 3)}` : "Knowledge only"}</strong>
                        </div>
                      </div>
                      <div className="task-block">
                        <span>Linked tasks</span>
                        {source.linked_tasks.length ? (
                          <ul>
                            {source.linked_tasks.map((taskTitle, index) => (
                              <li key={`${source.source_ref}-task-${index}`}>{taskTitle}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>This source is improving the market brief even though no checklist task depends on it yet.</p>
                        )}
                      </div>
                      <div className="task-actions compact-actions">
                        <button
                          className="decision-button detail"
                          type="button"
                          onClick={() => {
                            setFocusedSourceRef(source.source_ref);
                            setActiveView("know-more");
                          }}
                        >
                          View extracted knowledge
                        </button>
                        <button className="decision-button" type="button" onClick={() => void updateIngestedSource(source.source_ref, { action: "reprocess" })}>
                          Reprocess
                        </button>
                        {editingIngestedSourceRef === source.source_ref ? (
                          <>
                            <input
                              value={ingestedSourceLabel}
                              onChange={(event) => setIngestedSourceLabel(event.target.value)}
                              placeholder="Source label"
                            />
                            <button
                              className="decision-button adjust"
                              type="button"
                              onClick={() =>
                                void updateIngestedSource(source.source_ref, {
                                  display_label: ingestedSourceLabel.trim() || source.label,
                                })
                              }
                            >
                              Save
                            </button>
                            <button
                              className="decision-button"
                              type="button"
                              onClick={() => {
                                setEditingIngestedSourceRef(null);
                                setIngestedSourceLabel("");
                              }}
                            >
                              Close
                            </button>
                          </>
                        ) : (
                          <button
                            className="decision-button adjust"
                            type="button"
                            onClick={() => {
                              setEditingIngestedSourceRef(source.source_ref);
                              setIngestedSourceLabel(source.label);
                            }}
                          >
                            Edit
                          </button>
                        )}
                        <button className="decision-button reject" type="button" onClick={() => void deleteIngestedSource(source.source_ref)}>
                          Remove source and rebuild
                        </button>
                      </div>
                    </article>
                  ))
                ) : (
                  <article className="source-asset empty-asset">
                    <strong>No sources in this workspace yet</strong>
                    <span>This view only shows sources linked to the active project.</span>
                    <p>Add a source to start analysis for this project.</p>
                  </article>
                )}
              </div>

              {false ? (
                <div className="monitoring-secondary">
                  <div className="section-head compact">
                    <div>
                      <span className="section-kicker">Monitoring</span>
                      <h3>Jobs</h3>
                    </div>
                  </div>
                  <div className="secondary-assets">
                    {workspace?.managed_jobs.length ? (
                      workspace?.managed_jobs.map((job) => (
                        <article className="job-item" key={job.managed_job_id}>
                          <strong>{job.name}</strong>
                          <span>
                            {titleCaseWords(job.trigger_type)} · {job.status}
                            {job.schedule_text ? ` · ${job.schedule_text}` : ""}
                          </span>
                          <p>{job.last_action_summary ?? "No action generated yet."}</p>
                          <div className="task-actions compact-actions">
                            <button
                              className="decision-button adjust"
                              type="button"
                              onClick={() => {
                                setEditingJobId(job.managed_job_id);
                                setShowJobComposer(true);
                                setJobForm({ name: job.name, triggerType: job.trigger_type as JobFormState["triggerType"], scheduleText: job.schedule_text ?? "", sourceId: job.source_id ?? "" });
                              }}
                            >
                              Edit
                            </button>
                            <button className="decision-button" type="button" onClick={() => void updateJob(job.managed_job_id, { status: job.status === "active" ? "paused" : "active" })}>
                              {job.status === "active" ? "Pause" : "Resume"}
                            </button>
                            <button className="decision-button reject" type="button" onClick={() => void deleteJob(job.managed_job_id)}>
                              Delete
                            </button>
                          </div>
                        </article>
                      ))
                    ) : (
                      workspace?.monitor_jobs.map((job) => (
                        <article className="job-item" key={job.job_name}>
                          <strong>{job.job_name}</strong>
                          <span>Status: {job.status}</span>
                          <p>Last run: {formatTimestamp(job.last_run_at)} · last source: {humanSourceLabel(job.last_source_ref)}</p>
                        </article>
                      ))
                    )}
                  </div>
                </div>
              ) : null}
            </section>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Monitoring brief</span>
                  <h2>What your monitoring workspace is tracking</h2>
                  <p className="section-subcopy">This panel shows what we have seen recently and whether monitoring is active.</p>
                </div>
              </div>
              <div className="secondary-assets">
                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Recent Signals</h3>
                  </div>
                  {workspace?.recent_activity.length ? (
                    workspace.recent_activity.slice(0, 3).map((activity) => (
                      <div className="job-item" key={activity.signal_id}>
                        <strong>{humanizeSignalType(activity.signal_type)}</strong>
                        <span>Observed: {formatTimestamp(activity.observed_at)}</span>
                        <p>{activity.summary}</p>
                      </div>
                    ))
                  ) : (
                    <div className="job-item">
                      <strong>No source activity yet</strong>
                      <span>Add one source and we will start showing real signal changes here.</span>
                      <p>This panel stays grounded in actual monitoring activity, not placeholders.</p>
                    </div>
                  )}
                </article>

                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Monitoring</h3>
                  </div>
                  {workspace?.monitor_jobs.length ? (
                    workspace.monitor_jobs.map((job) => (
                      <div className="job-item" key={job.job_name}>
                        <strong>{job.job_name}</strong>
                        <span>Status: {job.status}</span>
                        <p>Last run: {formatTimestamp(job.last_run_at)} · last source: {humanSourceLabel(job.last_source_ref)}</p>
                      </div>
                    ))
                  ) : (
                    <div className="job-item">
                      <strong>No monitoring activity yet</strong>
                      <span>Monitoring becomes visible after the first source is ingested.</span>
                      <p>You’ll see recurring observation activity here once a saved source or job runs again.</p>
                    </div>
                  )}
                </article>
              </div>

              {workspaceError ? <div className="notice error"><p>{workspaceError}</p></div> : null}
            </section>
          </aside>
        </section>
        ) : null}
      </div>
    </section>
  );
}
