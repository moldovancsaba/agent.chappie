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
};

const EXAMPLE_INPUT = {
  mode: "text" as const,
  value:
    "FlowOps increased U14 pricing by 12%, Essex County Club launched a free-trial campaign, and one nearby academy may close with equipment likely headed to a sell-off before the next intake cycle.",
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

function inputHelper(mode: InputMode) {
  if (mode === "url") {
    return {
      label: "Paste URL",
      placeholder: "https://competitor-site.example/pricing",
      good: [
        "One competitor website or pricing page",
        "One announcement, launch page, or social post",
        "One page with clear claims, pricing, or offers",
      ],
      bad: ["Generic homepage with no useful content", "Unrelated directory or map links", "Multiple links pasted together"],
    };
  }
  if (mode === "file") {
    return {
      label: "Upload File",
      placeholder: "Upload one PDF, notes file, or report.",
      good: ["Pricing PDF", "Meeting notes", "Competitor report"],
      bad: ["Screenshot with no text extraction", "Multiple files", "Completely unrelated document"],
    };
  }
  return {
    label: "Paste Text",
    placeholder: 'Example: "FlowOps increased prices by 15%, Essex launched a discount campaign, and one academy may close."',
    good: ["One raw notes block", "One copied pricing table or announcement", "One source bundle from a call or report"],
    bad: ["One-word summary", "Vague request with no evidence", "Multiple unrelated topics mixed together"],
  };
}

export function DemoWorkspace() {
  const [activeView, setActiveView] = useState<AppView>("checklist");
  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [sessionId, setSessionId] = useState("anonymous-loading");
  const [projectId, setProjectId] = useState("");
  const [contextNotes, setContextNotes] = useState("");
  const [fileName, setFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [submissionError, setSubmissionError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [taskDecisions, setTaskDecisions] = useState<Record<number, TaskDecision>>({});
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setSessionId(readOrCreateSessionId());
  }, []);

  useEffect(() => {
    if (!isCompleteResultWithTasks(jobResult)) {
      return;
    }
    setTaskDecisions(buildDefaultDecisions(jobResult.result_payload.recommended_tasks));
    setFeedbackStatus("");
    setActiveView("checklist");
  }, [jobResult]);

  useEffect(() => {
    if (!projectId || !jobResult) {
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

  async function submitContext(notes: string) {
    const trimmed = notes.trim();
    if (!trimmed) {
      setSubmissionError("Paste one URL, one text block, or upload one file before running the job.");
      return;
    }

    setIsSubmitting(true);
    setSubmissionError("");
    setFeedbackStatus("");

    try {
      const contextType = inputMode === "file" ? "working_document" : "meeting_notes";
      const sourceKind =
        inputMode === "url" ? "url" : inputMode === "file" ? "uploaded_file" : "manual_text";
      const response = await fetch("/api/jobs", {
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

  async function handleUseExample() {
    setInputMode(EXAMPLE_INPUT.mode);
    setFileName("");
    setContextNotes(EXAMPLE_INPUT.value);
    await submitContext(EXAMPLE_INPUT.value);
  }

  async function handleFileSelection(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setInputMode("file");
    setFileName(file.name);
    const rawText = await file.text();
    setContextNotes(rawText.slice(0, 20000));
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
  const tasks = completeResult?.result_payload.recommended_tasks ?? [];
  const confidence = completeResult?.decision_summary?.confidence;
  const canSubmitFeedback = completeResult ? allTasksDecided(tasks, taskDecisions) : false;
  const topKnowledge = workspace?.knowledge_summary[0];
  const currentHelper = inputHelper(inputMode);
  const currentStatus = isSubmitting
    ? "Processing"
    : completeResult
      ? "Ready"
      : workspace?.recent_sources.length
        ? "Monitoring active"
        : "Waiting for input";

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
            <strong>{projectId || "Start with one source"}</strong>
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
              ) : (
                <div className="empty-state guided-empty-state">
                  <h3>Start with one source</h3>
                  <p>
                    Paste one competitor URL, one block of raw notes, or upload one file. Agent.Chappie will turn it
                    into three ranked actions or tell you honestly when the source is too weak.
                  </p>
                  <div className="guided-actions">
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("url"); setActiveView("sources-jobs"); }}>
                      Paste URL
                    </button>
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("text"); setActiveView("sources-jobs"); }}>
                      Paste Text
                    </button>
                    <button className="button-secondary" type="button" onClick={() => { setInputMode("file"); setActiveView("sources-jobs"); fileInputRef.current?.click(); }}>
                      Upload File
                    </button>
                    <button className="button-primary" type="button" onClick={() => void handleUseExample()} disabled={isSubmitting}>
                      {isSubmitting ? "Running example..." : "Use Example"}
                    </button>
                  </div>
                  <div className="guided-grid">
                    <article className="guided-card">
                      <strong>Good URL input</strong>
                      <p>One pricing page, announcement, or competitor post with claims, offers, or positioning.</p>
                    </article>
                    <article className="guided-card">
                      <strong>Good text input</strong>
                      <p>One raw note bundle like: “FlowOps raised prices, Essex launched free trials, one academy may close.”</p>
                    </article>
                    <article className="guided-card">
                      <strong>Good file input</strong>
                      <p>One pricing PDF, notes file, or report with text the worker can actually parse.</p>
                    </article>
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
                  <strong>{workspace?.recent_sources[0]?.source_kind ?? "Not yet"}</strong>
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
                      <li>Waiting for the first source package.</li>
                      <li>Once a source arrives, this view explains why the checklist changed.</li>
                    </ul>
                  )}
                </article>

                <article className="intel-card">
                  <h3>Current Context</h3>
                  <ul>
                    <li>
                      {topKnowledge
                        ? `${topKnowledge.competitor} is the strongest current competitor signal in ${humanizeRegion(topKnowledge.region)}.`
                        : "No strong competitor or region has been inferred yet."}
                    </li>
                    <li>
                      {workspace?.recent_activity.length
                        ? "The checklist is grounded in ingested source history, not generic AI filler."
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
                      <li>Paste one pricing page, one raw text block, or one notes file to populate this panel.</li>
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
                </div>
                <button className="button-secondary" type="button" onClick={() => void handleUseExample()} disabled={isSubmitting}>
                  Use Example
                </button>
              </div>

              <div className="input-mode-row">
                <button className={`mode-chip ${inputMode === "url" ? "active" : ""}`} type="button" onClick={() => setInputMode("url")}>
                  Paste URL
                </button>
                <button className={`mode-chip ${inputMode === "text" ? "active" : ""}`} type="button" onClick={() => setInputMode("text")}>
                  Paste Text
                </button>
                <button className={`mode-chip ${inputMode === "file" ? "active" : ""}`} type="button" onClick={() => { setInputMode("file"); fileInputRef.current?.click(); }}>
                  Upload File
                </button>
              </div>

              <div className="input-guidance panel-lite">
                <div>
                  <strong>{currentHelper.label}</strong>
                  <p>{currentHelper.placeholder}</p>
                </div>
                <div className="guidance-columns">
                  <div>
                    <span>Good input</span>
                    <ul>
                      {currentHelper.good.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span>Bad input</span>
                    <ul>
                      {currentHelper.bad.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {inputMode === "file" ? (
                <div className="field-grid single-column">
                  <div className="field">
                    <label>Upload one file</label>
                    <div className="file-upload-row">
                      <button className="button-secondary" type="button" onClick={() => fileInputRef.current?.click()}>
                        Choose file
                      </button>
                      <span className="file-upload-label">{fileName || "No file selected yet"}</span>
                    </div>
                    <p className="field-help">
                      Max one file per submission. Text extraction must happen in the browser or a worker-supported format.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="field-grid single-column">
                  <div className="field">
                    <label htmlFor="context-notes">{inputMode === "url" ? "URL" : "Text block"}</label>
                    <textarea
                      id="context-notes"
                      value={contextNotes}
                      onChange={(event) => setContextNotes(event.target.value)}
                      placeholder={currentHelper.placeholder}
                    />
                  </div>
                </div>
              )}

              <input ref={fileInputRef} hidden type="file" accept=".txt,.md,.pdf,.csv" onChange={handleFileSelection} />

              <div className="field-triple single-readonly">
                <div className="field">
                  <label>Anonymous session</label>
                  <div className="read-only-field">{sessionId}</div>
                </div>
              </div>

              <div className="button-row">
                <button className="button-primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Submitting source..." : "Run decision job"}
                </button>
              </div>
            </form>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Sources &amp; Jobs</span>
                  <h2>Recent source handling</h2>
                </div>
              </div>

              <div className="operator-grid">
                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Recurring Monitoring</h3>
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
                      <strong>Monitoring starts after the first useful source</strong>
                      <span>This panel fills from the worker, not from manual frontend setup.</span>
                      <p>It will show recurring observation activity once the worker has real project context.</p>
                    </div>
                  )}
                </article>

                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Recent Activity</h3>
                  </div>
                  {workspace?.recent_activity.length ? (
                    workspace.recent_activity.slice(0, 2).map((activity) => (
                      <div className="job-item" key={activity.signal_id}>
                        <strong>{activity.signal_type.replaceAll("_", " ")}</strong>
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
              </div>

              <div className="library-list">
                {workspace?.recent_sources.length ? (
                  workspace.recent_sources.map((source) => (
                    <article className={`library-item ${source.source_ref.startsWith("source_") ? "current" : ""}`} key={source.source_ref}>
                      <strong>{source.source_ref}</strong>
                      <span>{source.source_kind} · received {formatTimestamp(source.created_at)}</span>
                      <p>{source.preview}</p>
                    </article>
                  ))
                ) : (
                  <article className="library-item">
                    <strong>What appears here</strong>
                    <span>Recent URLs, notes, or file text that the worker actually ingested.</span>
                    <p>Nothing is shown until the system has real source material to work with.</p>
                  </article>
                )}
              </div>

              {jobRequest ? (
                <div className="compact-meta">
                  <h3>Latest Job</h3>
                  <p>
                    <strong>Job ID:</strong> {jobRequest.job_id}
                  </p>
                  <p>
                    <strong>Project ID:</strong> {jobRequest.project_id}
                  </p>
                  <p>
                    <strong>Capability:</strong> {jobRequest.requested_capability}
                  </p>
                </div>
              ) : null}
            </section>
          </aside>
        </section>
      ) : null}
    </section>
  );
}
