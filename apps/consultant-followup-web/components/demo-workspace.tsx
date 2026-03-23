"use client";

import { FormEvent, useEffect, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult, type RecommendedTask } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

type AppView = "checklist" | "know-more" | "sources-jobs";
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

function deriveSignalCounts(notes: string) {
  const normalized = notes.toLowerCase();
  return {
    pricing: normalized.includes("price") || normalized.includes("pricing") || normalized.includes("fee") ? 1 : 0,
    closure: normalized.includes("close") || normalized.includes("closure") ? 1 : 0,
    offers:
      normalized.includes("discount") || normalized.includes("voucher") || normalized.includes("trial")
        ? 1
        : 0,
    equipment:
      normalized.includes("equipment") || normalized.includes("sell-off") || normalized.includes("asset sale")
        ? 1
        : 0,
  };
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
  const [sessionId, setSessionId] = useState("anonymous-loading");
  const [projectId, setProjectId] = useState("");
  const [contextNotes, setContextNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [submissionError, setSubmissionError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [taskDecisions, setTaskDecisions] = useState<Record<number, TaskDecision>>({});
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  const [workspaceError, setWorkspaceError] = useState("");

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setSubmissionError("");
    setFeedbackStatus("");

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          projectId: projectId || undefined,
          contextNotes,
          contextType: "meeting_notes",
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
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : "Unknown submission error.");
    } finally {
      setIsSubmitting(false);
    }
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

      const summary = [
        feedbackPayload.done.length > 0 ? `${feedbackPayload.done.length} done` : null,
        feedbackPayload.edited.length > 0 ? `${feedbackPayload.edited.length} adjusted` : null,
        feedbackPayload.declined.length > 0 ? `${feedbackPayload.declined.length} rejected` : null,
      ]
        .filter(Boolean)
        .join(" · ");

      setFeedbackStatus(`Feedback saved: ${summary || "no changes recorded"}.`);
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
  const signalCounts = deriveSignalCounts(contextNotes);
  const confidence = completeResult?.decision_summary?.confidence;
  const canSubmitFeedback = completeResult ? allTasksDecided(tasks, taskDecisions) : false;
  const topKnowledge = workspace?.knowledge_summary[0];

  return (
    <section className="decision-shell">
      <header className="decision-header panel">
        <div className="decision-header-copy">
          <div className="eyebrow">Worker-managed decision surface</div>
          <h1>Your next move, not more noise.</h1>
          <p>
            The frontend submits only raw source material. Agent.Chappie manages the general project context on the Mac
            mini and returns only the next three actions worth making.
          </p>
        </div>

        <div className="project-status">
          <div className="status-stack">
            <span className="status-label">Project</span>
            <strong>{projectId || "Assigned by worker"}</strong>
          </div>
          <div className="status-stack">
            <span className="status-label">Status</span>
            <strong>{completeResult ? "Monitoring active" : "Waiting for first signal set"}</strong>
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
        <button
          className={`surface-tab ${activeView === "checklist" ? "active" : ""}`}
          onClick={() => setActiveView("checklist")}
          type="button"
        >
          Your Checklist
        </button>
        <button
          className={`surface-tab ${activeView === "know-more" ? "active" : ""}`}
          onClick={() => setActiveView("know-more")}
          type="button"
        >
          Know More
        </button>
        <button
          className={`surface-tab ${activeView === "sources-jobs" ? "active" : ""}`}
          onClick={() => setActiveView("sources-jobs")}
          type="button"
        >
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
                <span className="status-pill">{completeResult ? "Monitoring active" : "Waiting for input"}</span>
              </div>

              {submissionError ? (
                <div className="notice error">
                  <strong>Submission error</strong>
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
                          <div className="task-meta">When: this week</div>
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
                <div className="empty-state">
                  <h3>No checklist yet</h3>
                  <p>Open Sources &amp; Jobs, submit one context package, and Agent.Chappie will return the top three actions.</p>
                </div>
              )}
            </section>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Decision Summary</span>
                  <h2>Confidence and response state</h2>
                </div>
              </div>

              <div className="summary-stack">
                <div className="summary-row">
                  <span>Confidence</span>
                  <strong>
                    {confidenceLabel(confidence)}
                    {confidence !== undefined ? ` (${confidence.toFixed(2)})` : ""}
                  </strong>
                </div>
                <div className="summary-row">
                  <span>Bridge mode</span>
                  <strong>Worker</strong>
                </div>
                <div className="summary-row">
                  <span>Storage</span>
                  <strong>Neon + local brain</strong>
                </div>
              </div>

              {completeResult ? <p className="surface-summary">{completeResult.result_payload.summary}</p> : null}

              <div className="feedback-panel">
                <h3>Decision capture</h3>
                <p>Mark each card as Done, Adjust, or Reject. The app stores only the final feedback object.</p>
                <div className="feedback-totals">
                  <span>{buildFeedbackPayload(tasks, taskDecisions).done.length} done</span>
                  <span>{buildFeedbackPayload(tasks, taskDecisions).edited.length} adjusted</span>
                  <span>{buildFeedbackPayload(tasks, taskDecisions).declined.length} rejected</span>
                </div>
                <button
                  className="button-primary wide"
                  disabled={!canSubmitFeedback || isSavingFeedback}
                  onClick={handleSaveFeedback}
                  type="button"
                >
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
                  <h2>Compressed intelligence behind the checklist</h2>
                </div>
              </div>

              <div className="intel-columns">
                <article className="intel-card">
                  <h3>Project Summary</h3>
                  {workspace ? (
                    <ul>
                      <li>{workspace.market_summary.pricing_changes} pricing changes detected</li>
                      <li>{workspace.market_summary.closure_signals} closure or distress signals detected</li>
                      <li>{workspace.market_summary.offer_signals} offer or asset signals detected</li>
                    </ul>
                  ) : (
                    <ul>
                      <li>{signalCounts.pricing} competitor pricing change detected from current input</li>
                      <li>{signalCounts.closure} closure or distress signal detected from current input</li>
                      <li>{signalCounts.offers + signalCounts.equipment} commercial offer or asset signal detected from current input</li>
                    </ul>
                  )}
                </article>

                <article className="intel-card">
                  <h3>Market Situation</h3>
                  <ul>
                    <li>
                      {topKnowledge
                        ? `${topKnowledge.competitor} is the strongest current competitor signal in ${topKnowledge.region.replaceAll("_", " ")}.`
                        : "The worker maintains the general project context and competitive scope outside the frontend."}
                    </li>
                    <li>
                      {workspace?.recent_activity.length
                        ? "The app is showing compressed reasoning derived from ingested source history."
                        : "The app only shows compressed reasoning after the worker ingests real source material."}
                    </li>
                    <li>The current response window is measured in days, not quarters.</li>
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
                      <li>Submit one context package to populate the signal summary.</li>
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
                  <span className="section-kicker">Sources &amp; Jobs</span>
                  <h2>Submit raw source material only</h2>
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
                      <strong>Managed on the Mac mini worker</strong>
                      <span>Recurring monitoring is not configured in the frontend.</span>
                      <p>The worker owns competitor scans, schedule rules, and continuous observation state.</p>
                    </div>
                  )}
                </article>

                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Event-Based Jobs</h3>
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
                      <strong>Triggered from submitted source packages</strong>
                      <span>Paste raw notes, a URL summary, or extracted file text.</span>
                      <p>The frontend no longer creates general project metadata or monitoring rules.</p>
                    </div>
                  )}
                </article>
              </div>

              <div className="field-grid single-column">
                <div className="field">
                  <label htmlFor="context-notes">Context package</label>
                  <textarea
                    id="context-notes"
                    value={contextNotes}
                    onChange={(event) => setContextNotes(event.target.value)}
                    placeholder="Paste one raw source package: notes, copied competitor copy, a URL summary, or extracted file text."
                  />
                </div>
              </div>

              <div className="field-triple single-readonly">
                <div className="field">
                  <label>Anonymous session</label>
                  <div className="read-only-field">{sessionId}</div>
                </div>
              </div>

              <div className="button-row">
                <button className="button-primary" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Submitting source package..." : "Run decision job"}
                </button>
              </div>
            </form>
          </div>

          <aside className="secondary-column">
            <section className="panel section-card">
              <div className="section-head compact">
                <div>
                  <span className="section-kicker">Context Library</span>
                  <h2>Worker-managed source handling</h2>
                </div>
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
                  <>
                    <article className="library-item">
                      <strong>Worker-managed source inventory</strong>
                      <span>Submitted raw input is forwarded to the worker.</span>
                      <p>General source snapshots and project knowledge are managed on the Mac mini only.</p>
                    </article>
                    <article className="library-item current">
                      <strong>Current inline context</strong>
                      <span>Raw source package sent from this browser</span>
                      <p>{contextNotes ? `${contextNotes.slice(0, 130)}${contextNotes.length > 130 ? "..." : ""}` : "No source package submitted yet."}</p>
                    </article>
                  </>
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
