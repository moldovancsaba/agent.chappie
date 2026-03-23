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
type ManagementStatus = {
  tone: "success" | "error";
  message: string;
} | null;
type WorkspaceSnapshot = {
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
  const [managementStatus, setManagementStatus] = useState<ManagementStatus>(null);
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
    if (!projectId || !sourceForm.label.trim() || !sourceForm.contentText.trim()) {
      setManagementStatus({ tone: "error", message: "Add a source label and source content first." });
      return;
    }
    const response = editingSourceId
      ? await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(editingSourceId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            label: sourceForm.label.trim(),
            source_kind: sourceForm.sourceKind,
            content_text: sourceForm.contentText.trim(),
          }),
        })
      : await fetch(`/api/projects/${encodeURIComponent(projectId)}/sources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_id: generateId("source_cfg"),
            label: sourceForm.label.trim(),
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
      setManagementStatus({ tone: "error", message: "Add a job name first." });
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
      ? blockedResult.result_payload.reason
      : "The worker ingested the source but could not derive three distinct, high-confidence actions from it.";
  const currentStatus = isSubmitting
    ? "Processing"
    : completeResult
      ? "Ready"
      : blockedResult
        ? "Needs stronger source"
      : workspace?.recent_sources.length
        ? "Monitoring active"
        : "Waiting for input";
  const projectLabel = topKnowledge ? titleCaseWords(humanizeRegion(topKnowledge.region)) : "Current project";
  const latestSourceLabel = workspace?.recent_sources[0]
    ? `${sourceKindLabel(workspace.recent_sources[0].source_kind)} received`
    : "No source yet";

  return (
    <section className="decision-shell">
      <header className="decision-header panel">
        <div className="decision-header-copy">
          <div className="eyebrow">Competitive action engine</div>
          <h1>Your next move, not more noise.</h1>
          <p>
            Submit one source and Agent.Chappie turns it into the three highest-value actions to make next. You only
            see what to do, why it matters, and what evidence triggered it.
          </p>
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
                          <div className="task-block">
                            <span>Why now</span>
                            <p>{task.why_now}</p>
                          </div>
                          <div className="task-block impact">
                            <span>Expected impact</span>
                            <p>{task.expected_advantage}</p>
                          </div>
                          <div className="task-evidence">
                            <span>Evidence</span>
                            <div className="evidence-chip-list">
                              {task.evidence_refs.map((ref) => (
                                <span className="evidence-chip" key={ref}>
                                  {ref}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="task-actions">
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
                  <strong>No strong action yet</strong>
                  <p>{blockedReason}</p>
                  <p>
                    The source was received. Try a denser source with clearer competitor, pricing, offer, closure, or
                    timing signals.
                  </p>
                  <div className="guided-actions">
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => {
                        setInputMode("url");
                        setActiveView("sources-jobs");
                      }}
                    >
                      Try URL
                    </button>
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => {
                        setInputMode("text");
                        setActiveView("sources-jobs");
                      }}
                    >
                      Try Text
                    </button>
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => {
                        setInputMode("file");
                        setActiveView("sources-jobs");
                        fileInputRef.current?.click();
                      }}
                    >
                      Try Document
                    </button>
                  </div>
                </div>
              ) : (
                <div className="empty-state guided-empty-state">
                  <h3>No checklist yet</h3>
                  <p>
                    Submit one real source. The checklist will appear only after the worker has enough evidence to
                    return three distinct actions.
                  </p>
                  <div className="guided-actions">
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("url"); setActiveView("sources-jobs"); }}>
                      Try URL
                    </button>
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("text"); setActiveView("sources-jobs"); }}>
                      Try Text
                    </button>
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("file"); setActiveView("sources-jobs"); fileInputRef.current?.click(); }}>
                      Try Document
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
                  <span className="section-kicker">Decision Summary</span>
                  <h2>What happened and what to do next</h2>
                  <p className="section-subcopy">This summary stays aligned with the checklist, not a separate dashboard.</p>
                </div>
              </div>

              <div className="summary-stack">
                <div className="summary-row">
                  <span>Status</span>
                  <strong>{currentStatus}</strong>
                </div>
                <div className="summary-row">
                  <span>Confidence</span>
                  <strong>
                    {confidenceLabel(confidence)}
                    {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
                  </strong>
                </div>
                <div className="summary-row">
                  <span>Latest source</span>
                  <strong>{latestSourceLabel}</strong>
                </div>
              </div>

              {completeResult ? <p className="surface-summary">{completeResult.result_payload.summary}</p> : null}

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
                  <h2>Why these three actions were chosen</h2>
                  <p className="section-subcopy">This view explains the decision context behind the checklist.</p>
                </div>
              </div>

              <div className="intel-columns">
                <article className="intel-card">
                  <h3>Market Summary</h3>
                  {workspace ? (
                    <ul>
                      <li>{workspace.market_summary.pricing_changes} competitors changed pricing</li>
                      <li>{workspace.market_summary.closure_signals} closure or distress signals detected</li>
                      <li>{workspace.market_summary.offer_signals} offer or asset signals detected</li>
                    </ul>
                  ) : (
                    <ul>
                      <li>No market summary yet.</li>
                      <li>This panel fills after the worker ingests a real source.</li>
                    </ul>
                  )}
                </article>

                <article className="intel-card">
                  <h3>Current Context</h3>
                  <ul>
                    <li>
                      {topKnowledge
                        ? `${topKnowledge.competitor} is the strongest current signal in ${humanizeRegion(topKnowledge.region)}.`
                        : "No strong competitor or region has been inferred yet."}
                    </li>
                    <li>
                      {workspace?.recent_activity.length
                        ? "The checklist is grounded in ingested source history."
                        : "Submit one source to generate the first market summary."}
                    </li>
                    <li>The system prefers actions that can be executed inside a 7-day window.</li>
                  </ul>
                </article>

                <article className="intel-card">
                  <h3>Recent Signals</h3>
                  {workspace?.recent_activity.length ? (
                    <ul>
                      {workspace.recent_activity.slice(0, 3).map((activity) => (
                        <li key={activity.signal_id}>{activity.summary}</li>
                      ))}
                    </ul>
                  ) : (
                    <ul>
                      <li>No recent signals yet.</li>
                    </ul>
                  )}
                </article>
              </div>
            </section>
          </div>
        </section>
      ) : null}

      {activeView === "sources-jobs" ? (
        <section className="content-grid">
          <div className="primary-column">
            <form className="panel section-card" onSubmit={handleSubmit}>
              <div className="section-head">
                <div>
                  <span className="section-kicker">Submit Context</span>
                  <h2>Tell the system exactly what to read</h2>
                  <p className="section-subcopy">Submit one source at a time. The worker ingests it and updates the checklist if the evidence is strong enough.</p>
                </div>
              </div>

              <div className="input-mode-row">
                <button className={`mode-chip ${inputMode === "url" ? "active" : ""}`} type="button" onClick={() => setInputMode("url")}>
                  URL
                </button>
                <button className={`mode-chip ${inputMode === "text" ? "active" : ""}`} type="button" onClick={() => setInputMode("text")}>
                  Text
                </button>
                <button className={`mode-chip ${inputMode === "file" ? "active" : ""}`} type="button" onClick={() => { setInputMode("file"); fileInputRef.current?.click(); }}>
                  Document
                </button>
              </div>

              {inputMode === "file" ? (
                <div className="field-grid single-column">
                  <div className="field">
                    <div className="file-upload-row">
                      <button className="button-secondary" type="button" onClick={() => fileInputRef.current?.click()}>
                        Choose document
                      </button>
                      <span className="file-upload-label">{fileName || "No file selected yet"}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="field-grid single-column">
                  <div className="field">
                    <textarea
                      id="context-notes"
                      value={contextNotes}
                      onChange={(event) => setContextNotes(event.target.value)}
                      placeholder={inputMode === "url" ? "https://..." : "Paste source text"}
                    />
                  </div>
                </div>
              )}

              <input ref={fileInputRef} hidden type="file" accept=".txt,.md,.csv,.pdf,.docx" onChange={handleFileSelection} />

              <div className="button-row">
                <button className="button-primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Analyzing source..." : "Analyze source"}
                </button>
              </div>
            </form>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Sources &amp; Jobs</span>
                  <h2>What the system has taken in</h2>
                  <p className="section-subcopy">These cards show real worker activity, not placeholder inventory.</p>
                </div>
              </div>

              <div className="operator-grid">
                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Sources</h3>
                  </div>
                  <div className="management-form">
                    <input
                      value={sourceForm.label}
                      onChange={(event) => setSourceForm((current) => ({ ...current, label: event.target.value }))}
                      placeholder="Source label"
                    />
                    <div className="guided-actions">
                      <button className={`mode-chip ${sourceForm.sourceKind === "url" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "url" }))}>
                        URL
                      </button>
                      <button className={`mode-chip ${sourceForm.sourceKind === "manual_text" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "manual_text" }))}>
                        Text
                      </button>
                      <button className={`mode-chip ${sourceForm.sourceKind === "uploaded_file" ? "active" : ""}`} type="button" onClick={() => setSourceForm((current) => ({ ...current, sourceKind: "uploaded_file" }))}>
                        Document
                      </button>
                    </div>
                    <textarea
                      value={sourceForm.contentText}
                      onChange={(event) => setSourceForm((current) => ({ ...current, contentText: event.target.value }))}
                      placeholder="Source content or source address"
                    />
                    <div className="task-actions compact-actions">
                      <button className="button-primary" type="button" onClick={() => void handleCreateSource()}>
                        {editingSourceId ? "Save Source" : "Add Source"}
                      </button>
                      {editingSourceId ? (
                        <button
                          className="button-secondary"
                          type="button"
                          onClick={() => {
                            setEditingSourceId(null);
                            setSourceForm({ label: "", sourceKind: "url", contentText: "" });
                          }}
                        >
                          Cancel
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {workspace?.managed_sources.length ? (
                    workspace.managed_sources.map((source) => (
                      <div className="job-item" key={source.source_id}>
                        <strong>{source.label}</strong>
                        <span>
                          {sourceKindLabel(source.source_kind)} · {source.status}
                        </span>
                        <p>Last run: {formatTimestamp(source.last_run_at)} · last result: {source.last_result_summary ?? "Not yet"}</p>
                        <div className="task-actions compact-actions">
                          <button className="decision-button adjust" type="button" onClick={() => {
                            setEditingSourceId(source.source_id);
                            setSourceForm({ label: source.label, sourceKind: source.source_kind as SourceFormState["sourceKind"], contentText: source.content_text });
                          }}>
                            Edit
                          </button>
                          <button className="decision-button" type="button" onClick={() => void updateSource(source.source_id, { status: source.status === "active" ? "paused" : "active" })}>
                            {source.status === "active" ? "Pause" : "Resume"}
                          </button>
                          <button className="decision-button reject" type="button" onClick={() => void deleteSource(source.source_id)}>
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="job-item">
                      <strong>No saved sources yet</strong>
                      <span>Add one source to make this a real management surface.</span>
                      <p>Saved sources keep their status and latest result summary here.</p>
                    </div>
                  )}
                </article>

                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Jobs</h3>
                  </div>
                  <div className="management-form">
                    <input
                      value={jobForm.name}
                      onChange={(event) => setJobForm((current) => ({ ...current, name: event.target.value }))}
                      placeholder="Job name"
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
                        {editingJobId ? "Save Job" : "Add Job"}
                      </button>
                      {editingJobId ? (
                        <button
                          className="button-secondary"
                          type="button"
                          onClick={() => {
                            setEditingJobId(null);
                            setJobForm({ name: "", triggerType: "manual", scheduleText: "", sourceId: "" });
                          }}
                        >
                          Cancel
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {workspace?.managed_jobs.length ? (
                    workspace.managed_jobs.map((job) => (
                      <div className="job-item" key={job.managed_job_id}>
                        <strong>{job.name}</strong>
                        <span>
                          {titleCaseWords(job.trigger_type)} · {job.status}
                          {job.schedule_text ? ` · ${job.schedule_text}` : ""}
                        </span>
                        <p>
                          Last run: {formatTimestamp(job.last_run_at)} · last action: {job.last_action_summary ?? "Not yet"} · expected impact: {job.last_expected_impact ?? "Not yet"}
                        </p>
                        {job.last_runs.length ? (
                          <ul className="compact-run-list">
                            {job.last_runs.slice(0, 3).map((run, index) => (
                              <li key={`${job.managed_job_id}-${index}`}>{formatTimestamp(run.at)} · {run.status} · {run.summary}</li>
                            ))}
                          </ul>
                        ) : null}
                        <div className="task-actions compact-actions">
                          <button className="decision-button adjust" type="button" onClick={() => {
                            setEditingJobId(job.managed_job_id);
                            setJobForm({ name: job.name, triggerType: job.trigger_type as JobFormState["triggerType"], scheduleText: job.schedule_text ?? "", sourceId: job.source_id ?? "" });
                          }}>
                            Edit
                          </button>
                          <button className="decision-button" type="button" onClick={() => void updateJob(job.managed_job_id, { status: job.status === "active" ? "paused" : "active" })}>
                            {job.status === "active" ? "Pause" : "Resume"}
                          </button>
                          <button className="decision-button reject" type="button" onClick={() => void deleteJob(job.managed_job_id)}>
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="job-item">
                      <strong>No saved jobs yet</strong>
                      <span>Add one job to control how monitoring should run.</span>
                      <p>Jobs keep trigger type, schedule, status, and recent execution history here.</p>
                    </div>
                  )}
                </article>
              </div>

              {managementStatus ? (
                <div className={`notice ${managementStatus.tone}`}>
                  <p>{managementStatus.message}</p>
                </div>
              ) : null}

              <div className="library-list">
                {workspace?.recent_sources.length ? (
                  workspace.recent_sources.map((source) => (
                    <article className={`library-item ${source.source_ref.startsWith("source_") ? "current" : ""}`} key={source.source_ref}>
                      <strong>{sourceKindLabel(source.source_kind)}</strong>
                      <span>Received {formatTimestamp(source.created_at)}</span>
                      <p>{source.preview}</p>
                    </article>
                  ))
                ) : (
                  <article className="library-item">
                    <strong>No sources recorded yet</strong>
                    <span>Recent URLs, notes, or extracted file text appear here after ingestion.</span>
                    <p>Nothing is shown until the worker has processed a real source.</p>
                  </article>
                )}
              </div>

              <div className="operator-grid">
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
                      <span>Submit one URL, one text block, or one file to create the first activity trace.</span>
                      <p>The system will show what it actually ingested, not a fabricated source list.</p>
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
                      <span>This panel fills from real worker state.</span>
                      <p>It will show recurring observation activity after the first ingested source is processed.</p>
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
