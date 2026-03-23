"use client";

import { type ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult, type RecommendedTask } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

type AppView = "checklist" | "know-more" | "sources-jobs";
type InputMode = "url" | "text" | "file";
type DecisionStatus = "done" | "edited" | "declined";
type TaskDecision = {
  status: DecisionStatus | null;
  adjustedText: string;
};
type SourceFormState = {
  label: string;
  sourceKind: "url" | "manual_text" | "uploaded_file";
  contentText: string;
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
  const sourceLine = sourceLabels.length ? `Pull the linked source evidence from ${sourceLabels.join(", ")} and confirm the exact claim or trigger.` : "Pull the linked evidence and confirm the exact trigger before editing anything.";
  return [
    sourceLine,
    `Execute the dominant move now: ${task.title}.`,
    "Make the customer-facing or operator-facing change visible this week so the market can actually see the move.",
    "Check whether the move directly reduced the threat or captured the opportunity described in the expected impact.",
  ];
}

function buildDefaultDecisions(tasks: RecommendedTask[]) {
  return tasks.reduce<Record<number, TaskDecision>>((current, task) => {
    current[task.rank] = {
      status: null,
      adjustedText: task.title,
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
      } else {
        current.declined.push(task.title);
      }
      return current;
    },
    { done: [] as string[], edited: [] as string[], declined: [] as string[] }
  );
}

function allTasksDecided(tasks: RecommendedTask[], decisions: Record<number, TaskDecision>) {
  return tasks.every((task) => Boolean(decisions[task.rank]?.status));
}

function inferSourceLabel(sourceKind: SourceFormState["sourceKind"], contentText: string) {
  const trimmed = contentText.trim();
  if (!trimmed) {
    return "";
  }
  if (sourceKind === "url") {
    try {
      const host = new URL(trimmed).hostname.replace(/^www\./, "");
      return host || "Competitor page";
    } catch {
      return "Competitor page";
    }
  }
  if (sourceKind === "uploaded_file") {
    return "Document source";
  }
  return "Source note";
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
    sourceKind: "url",
    contentText: "",
  });
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
          setWorkspace(body);
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
    setWorkspace(body);
    return body as WorkspaceSnapshot;
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

      const resultResponse = await fetch(body.result_url);
      const resultBody = await resultResponse.json();
      if (!resultResponse.ok) {
        throw new Error(resultBody.detail ?? "The job result could not be retrieved.");
      }
      setJobResult(resultBody.job_result);
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

  async function handleSaveFeedback() {
    if (!isCompleteResultWithTasks(jobResult)) {
      return;
    }

    const feedbackPayload = buildFeedbackPayload(jobResult.result_payload.recommended_tasks, taskDecisions);
    const fallbackAction: DecisionStatus =
      feedbackPayload.done.length > 0 ? "done" : feedbackPayload.declined.length > 0 ? "declined" : "edited";

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

      setFeedbackStatus("Thanks. Your response has been captured so future recommendations can improve.");
    } catch (error) {
      setFeedbackStatus(error instanceof Error ? error.message : "Unknown feedback error.");
    } finally {
      setIsSavingFeedback(false);
    }
  }

  async function handleCreateSource() {
    const resolvedLabel = sourceForm.label.trim() || inferSourceLabel(sourceForm.sourceKind, sourceForm.contentText);
    if (!projectId || !sourceForm.contentText.trim()) {
      setManagementStatus({ tone: "error", message: "Add the source you want monitored first." });
      return;
    }
    const response = editingSourceId
      ? await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(editingSourceId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            label: resolvedLabel,
            source_kind: sourceForm.sourceKind,
            content_text: sourceForm.contentText.trim(),
          }),
        })
      : await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_id: generateId("source_cfg"),
            label: resolvedLabel,
            source_kind: sourceForm.sourceKind,
            content_text: sourceForm.contentText.trim(),
            status: "active",
          }),
        });
    const body = await response.json();
    if (!response.ok) {
      setManagementStatus({ tone: "error", message: body.detail ?? "The source could not be created." });
      return;
    }
    setWorkspace((current) => (current ? { ...current, managed_sources: body.sources ?? [] } : current));
    setSourceForm({ label: "", sourceKind: "url", contentText: "" });
    setEditingSourceId(null);
    setShowSourceComposer(false);
    setManagementStatus({ tone: "success", message: editingSourceId ? "Source updated." : "Source saved." });
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
      status: "confirmed" | "dismissed" | "edited";
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
    setManagementStatus({ tone: "success", message: "Ingested source deleted." });
  }

  function setDecision(rank: number, status: DecisionStatus, fallbackTitle: string) {
    setTaskDecisions((current) => ({
      ...current,
      [rank]: {
        status,
        adjustedText: current[rank]?.adjustedText ?? fallbackTitle,
      },
    }));
  }

  function setAdjustedText(rank: number, value: string) {
    setTaskDecisions((current) => ({
      ...current,
      [rank]: {
        status: "edited",
        adjustedText: value,
      },
    }));
  }

  const completeResult = isCompleteResultWithTasks(jobResult) ? jobResult : null;
  const blockedResult =
    jobResult && jobResult.status === "blocked" && !isCompleteResultWithTasks(jobResult) ? jobResult : null;
  const tasks = completeResult?.result_payload.recommended_tasks ?? [];
  const confidence = completeResult?.decision_summary?.confidence;
  const canSubmitFeedback = completeResult ? allTasksDecided(tasks, taskDecisions) : false;
  const topKnowledge = workspace?.knowledge_summary[0];
  const blockedReason =
    blockedResult && "reason" in blockedResult.result_payload && typeof blockedResult.result_payload.reason === "string"
      ? blockedResult.result_payload.reason === "insufficient_output_quality"
        ? "The current evidence builds useful knowledge, but not a strong enough advantage to recommend an immediate move."
        : blockedResult.result_payload.reason
      : "The worker ingested the source but could not derive three distinct, high-confidence actions from it.";
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
  const selectedTaskEvidence = selectedTask
    ? workspace?.recent_activity.filter((activity) => selectedTask.evidence_refs.includes(activity.signal_id)) ?? []
    : [];
  const selectedTaskSources = selectedTask
    ? workspace?.source_cards.filter((source) =>
        selectedTaskEvidence.some((activity) => activity.source_ref === source.source_ref)
      ) ?? []
    : [];
  const selectedTaskSteps = selectedTask
    ? buildExecutionSteps(
        selectedTask,
        selectedTaskSources.map((source) => source.label)
      )
    : [];

  return (
    <section className="decision-shell">
      <header className="decision-header panel">
        <div className="decision-header-copy">
          <div className="eyebrow">Competitive action engine</div>
          <h1>We analyze your competitive environment and recommend your next 3 moves.</h1>
          <p>
            Drop one source. Agent.Chappie extracts signals, builds market intelligence, and surfaces actions you can
            execute this week when a strong advantage appears.
          </p>
          <p className="system-status-line">{systemStatusLine}</p>
        </div>

          <div className="project-status">
            <div className="status-stack">
              <span className="status-label">Project</span>
              <strong>{projectLabel}</strong>
            </div>
            <div className="status-stack">
              <span className="status-label">Status</span>
              <strong>{currentStatus}</strong>
            </div>
            <div className="status-stack">
              <span className="status-label">Confidence</span>
              <strong>
                {confidenceLabel(confidence)}
                {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
              </strong>
            </div>
          </div>
      </header>

      <nav className="surface-nav" aria-label="Primary product sections">
        <button className={`surface-tab ${activeView === "checklist" ? "active" : ""}`} onClick={() => setActiveView("checklist")} type="button">
          Your Checklist
        </button>
        <button className={`surface-tab ${activeView === "know-more" ? "active" : ""}`} onClick={() => setActiveView("know-more")} type="button">
          Know More
        </button>
        <button className={`surface-tab ${activeView === "sources-jobs" ? "active" : ""}`} onClick={() => setActiveView("sources-jobs")} type="button">
          Sources &amp; Jobs
        </button>
      </nav>

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
                <span className="status-pill">{currentStatus}</span>
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
                            <div className="task-meta">When: this week</div>
                            <div className="task-meta">Confidence: {confidenceLabel(confidence)}{confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}</div>
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
                              onClick={() => setDecision(task.rank, "done", task.title)}
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
                              className={`decision-button reject ${decision?.status === "declined" ? "selected" : ""}`}
                              type="button"
                              onClick={() => setDecision(task.rank, "declined", task.title)}
                            >
                              ✕ Reject
                            </button>
                          </div>

                          {decision?.status === "edited" ? (
                            <div className="adjust-shell">
                              <label htmlFor={`adjust-${task.rank}`}>Adjusted action</label>
                              <textarea
                                id={`adjust-${task.rank}`}
                                value={decision.adjustedText}
                                onChange={(event) => setAdjustedText(task.rank, event.target.value)}
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
                  <p>{blockedReason}</p>
                  <p>
                    The source was still processed. We are monitoring pricing shifts, competitor positioning, and offer
                    changes from it. Open Know More to review the current intelligence, or add another source if you
                    want the worker to push toward a checklist move.
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
                      <span>Confidence</span>
                      <strong>
                        {confidenceLabel(confidence)}
                        {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
                      </strong>
                    </div>
                  </div>

                  <div className="task-block">
                    <span>Why this task</span>
                    <p>{selectedTask.why_now}</p>
                  </div>

                  <div className="task-block">
                    <span>What happens if you ignore it</span>
                    <p>{buildConsequenceOfInaction(selectedTask)}</p>
                  </div>

                  <div className="task-detail-list">
                    <h3>Execution steps</h3>
                    <ol className="compact-run-list">
                      {selectedTaskSteps.map((step, index) => (
                        <li key={`${selectedTask.rank}-step-${index}`}>{step}</li>
                      ))}
                    </ol>
                  </div>

                  <div className="task-evidence">
                    <span>Evidence</span>
                    <div className="evidence-chip-list">
                      {selectedTask.evidence_refs.map((ref) => (
                        <span className="evidence-chip" key={ref}>
                          {ref}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="task-detail-list">
                    <h3>Linked signals</h3>
                    {selectedTaskEvidence.length ? (
                      selectedTaskEvidence.map((activity) => (
                        <div className="job-item" key={activity.signal_id}>
                          <strong>{humanizeSignalType(activity.signal_type)}</strong>
                          <span>{formatTimestamp(activity.observed_at)}</span>
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
                            {sourceKindLabel(source.source_kind)} · {formatTimestamp(source.created_at)}
                          </span>
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

              <div className="feedback-panel">
                <h3>Help improve the next recommendation</h3>
                <p>Mark each card as Done, Adjust, or Reject so Agent.Chappie learns what was actually useful.</p>
                <div className="feedback-totals">
                  <span>{buildFeedbackPayload(tasks, taskDecisions).done.length} done</span>
                  <span>{buildFeedbackPayload(tasks, taskDecisions).edited.length} adjusted</span>
                  <span>{buildFeedbackPayload(tasks, taskDecisions).declined.length} rejected</span>
                </div>
                <button className="button-primary wide" disabled={!canSubmitFeedback || isSavingFeedback} onClick={handleSaveFeedback} type="button">
                  {isSavingFeedback ? "Saving decisions..." : "Submit decisions"}
                </button>
                {feedbackStatus ? <div className="notice success"><p>{feedbackStatus}</p></div> : null}
                {workspaceError ? <div className="notice error"><p>{workspaceError}</p></div> : null}
              </div>
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
              </div>
              {focusedSourceRef ? (
                <div className="notice success">
                  <p>
                    Filtering knowledge to source <strong>{focusedSourceRef}</strong>.
                  </p>
                  <button className="button-secondary" type="button" onClick={() => setFocusedSourceRef(null)}>
                    Show all knowledge
                  </button>
                </div>
              ) : null}

              <article className="intel-card snapshot-card">
                <div className="operator-head">
                  <h3>Competitive Position Snapshot</h3>
                  <span>{workspace?.competitive_snapshot.reference_competitor ?? "Comparison set still forming"}</span>
                </div>
                <div className="summary-stack">
                  <div className="summary-row">
                    <span>Pricing position</span>
                    <strong>{workspace?.competitive_snapshot.pricing_position ?? "Still forming"}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Acquisition comparison</span>
                    <strong>{workspace?.competitive_snapshot.acquisition_strategy_comparison ?? "Still forming"}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Current weakness</span>
                    <strong>{workspace?.competitive_snapshot.current_weakness ?? "Still forming"}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Risk level</span>
                    <strong>{titleCaseWords(workspace?.competitive_snapshot.risk_level ?? "medium")}</strong>
                  </div>
                </div>
                <div className="task-block">
                  <span>Active threats</span>
                  <ul>
                    {(workspace?.competitive_snapshot.active_threats ?? []).map((item, index) => (
                      <li key={`threat-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div className="task-block">
                  <span>Immediate opportunities</span>
                  <ul>
                    {(workspace?.competitive_snapshot.immediate_opportunities ?? []).map((item, index) => (
                      <li key={`opportunity-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              </article>

              {workspace?.fact_chips.length ? (
                <article className="intel-card">
                  <div className="operator-head">
                    <h3>Business Facts In Play</h3>
                    <span>{workspace.fact_chips.length} normalized facts</span>
                  </div>
                  <p>These chips are worker-normalized business facts derived from the current source set. They feed the knowledge cards and future checklist moves.</p>
                  <div className="evidence-chip-list">
                    {workspace.fact_chips.map((chip) => (
                      <button
                        className="evidence-chip"
                        key={chip.fact_id}
                        type="button"
                        onClick={() => setFocusedSourceRef(chip.source_refs[0] ?? null)}
                      >
                        {humanizeFactCategory(chip.category)}: {chip.label}
                      </button>
                    ))}
                  </div>
                </article>
              ) : null}

              <div className="intel-columns">
                {filteredKnowledgeCards.length ? (
                  filteredKnowledgeCards.map((card) => (
                    <article className="intel-card" key={card.knowledge_id}>
                      <div className="operator-head">
                        <h3>{card.title}</h3>
                        <span>
                          {confidenceLabel(card.confidence)} ({card.confidence.toFixed(2)}) · {card.annotation_status} · {confidenceSourceLabel(card.confidence_source)}
                        </span>
                      </div>
                      <p>{card.summary}</p>
                      <div className="task-block">
                        <span>Insight</span>
                        <p>{card.insight}</p>
                      </div>
                      <div className="task-block">
                        <span>Implication</span>
                        <p>{card.implication}</p>
                      </div>
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
                      <div className="evidence-chip-list">
                        {card.source_refs.map((sourceRef) => (
                          <button
                            className="evidence-chip"
                            key={sourceRef}
                            type="button"
                            onClick={() => setFocusedSourceRef(sourceRef)}
                          >
                            {sourceRef}
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
                            className="decision-button reject"
                            type="button"
                            onClick={() =>
                              void updateKnowledgeCard(card.knowledge_id, {
                                status: "dismissed",
                                confidence_source: "user_modified",
                                original_payload: card.audit.original_value,
                              })
                            }
                          >
                            Dismiss
                          </button>
                        </div>
                      )}

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
                    <p>Upload a real source and the worker will surface market knowledge here, even if no immediate task is strong enough yet.</p>
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
                  <span className="section-kicker">Sources &amp; Jobs</span>
                  <h2>Monitor your market and capture signals automatically.</h2>
                  <p className="section-subcopy">Add one source first. The worker will watch it, synthesize what changed, and surface actions when a strong move emerges.</p>
                </div>
              </div>

              <div className="monitoring-actions">
                <button
                  className="button-primary"
                  type="button"
                  onClick={() => {
                    setShowSourceComposer((current) => !current);
                    setShowJobComposer(false);
                  }}
                >
                  {showSourceComposer || editingSourceId ? "Hide source setup" : "Add source"}
                </button>
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => {
                    setShowJobComposer((current) => !current);
                    setShowSourceComposer(false);
                  }}
                >
                  {showJobComposer || editingJobId ? "Hide job setup" : "Add job"}
                </button>
              </div>

              {showSourceComposer || editingSourceId ? (
                <div className="operator-composer">
                  <div className="task-block">
                    <span>Step 1</span>
                    <p>What do you want to monitor?</p>
                  </div>
                  <div className="guided-actions">
                    <button className={`mode-chip ${sourceForm.sourceKind === "url" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "url" }))}>
                      Competitor page
                    </button>
                    <button className={`mode-chip ${sourceForm.sourceKind === "manual_text" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "manual_text" }))}>
                      Notes
                    </button>
                    <button className={`mode-chip ${sourceForm.sourceKind === "uploaded_file" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "uploaded_file" }))}>
                      Document
                    </button>
                  </div>

                  <div className="management-form compact-form">
                    <div className="task-block">
                      <span>Step 2</span>
                      <p>{sourceForm.sourceKind === "url" ? "Paste the page you want monitored." : sourceForm.sourceKind === "manual_text" ? "Paste the notes or copied source text." : "Paste the extracted document text or source reference."}</p>
                    </div>
                    <textarea
                      value={sourceForm.contentText}
                      onChange={(event) => setSourceForm((current) => ({ ...current, contentText: event.target.value }))}
                      placeholder={
                        sourceForm.sourceKind === "url"
                          ? "https://competitor.example/pricing"
                          : sourceForm.sourceKind === "manual_text"
                            ? "Paste the source text you want the worker to monitor"
                            : "Paste extracted document text or the source reference"
                      }
                    />
                    <details className="optional-fields">
                      <summary>Add a source label (optional)</summary>
                      <input
                        value={sourceForm.label}
                        onChange={(event) => setSourceForm((current) => ({ ...current, label: event.target.value }))}
                        placeholder="Short source label"
                      />
                    </details>
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
                          setSourceForm({ label: "", sourceKind: "url", contentText: "" });
                        }}
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              {showJobComposer || editingJobId ? (
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
                {workspace?.source_cards.length ? (
                  workspace.source_cards.map((source) => (
                    <article className={`source-asset ${focusedSourceRef === source.source_ref ? "current" : ""}`} key={source.source_ref}>
                      <div className="operator-head">
                        <div>
                          <strong>{source.label}</strong>
                          <span>
                            {sourceKindLabel(source.source_kind)} · Last update {formatTimestamp(source.created_at)}
                          </span>
                        </div>
                        <span className="asset-badge">{source.signal_count} signals</span>
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
                          Delete
                        </button>
                      </div>
                    </article>
                  ))
                ) : (
                  <article className="source-asset empty-asset">
                    <strong>No sources yet</strong>
                    <span>Add one competitor page or document.</span>
                    <p>We’ll monitor it and surface actions when something changes.</p>
                    <ul>
                      <li>pricing page</li>
                      <li>offer page</li>
                      <li>landing page</li>
                    </ul>
                  </article>
                )}
              </div>

              {workspace?.managed_jobs.length || workspace?.monitor_jobs.length ? (
                <div className="monitoring-secondary">
                  <div className="section-head compact">
                    <div>
                      <span className="section-kicker">Monitoring</span>
                      <h3>Jobs</h3>
                    </div>
                  </div>
                  <div className="secondary-assets">
                    {workspace?.managed_jobs.length ? (
                      workspace.managed_jobs.map((job) => (
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
                      workspace.monitor_jobs.map((job) => (
                        <article className="job-item" key={job.job_name}>
                          <strong>{job.job_name}</strong>
                          <span>Status: {job.status}</span>
                          <p>Last run: {formatTimestamp(job.last_run_at)} · last source: {job.last_source_ref ?? "none"}</p>
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
                  <p className="section-subcopy">This panel shows what the worker has seen recently and whether monitoring is active.</p>
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
                      <span>Add one source and the worker will start showing real signal changes here.</span>
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
                        <p>Last run: {formatTimestamp(job.last_run_at)} · last source: {job.last_source_ref ?? "none"}</p>
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
    </section>
  );
}
