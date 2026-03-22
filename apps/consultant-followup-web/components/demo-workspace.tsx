"use client";

import { FormEvent, useEffect, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult, type RecommendedTask } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

const SAMPLE_SUMMARY = "We run a soccer academy for talented boys and need practical decisions from regional competitor signals, not generic advice.";
const SAMPLE_NOTES =
  "FlowOps raised prices again, a nearby academy may close, and there is talk of a local equipment sell-off before the next intake cycle.";

type AppView = "checklist" | "know-more" | "sources-jobs";
type DecisionStatus = "done" | "edited" | "declined";
type TaskDecision = {
  status: DecisionStatus | null;
  adjustedText: string;
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

function humanizeRegion(region: string) {
  return region.replaceAll("_", " ");
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
  const [projectSummary, setProjectSummary] = useState(SAMPLE_SUMMARY);
  const [contextNotes, setContextNotes] = useState(SAMPLE_NOTES);
  const [competitor, setCompetitor] = useState("FlowOps");
  const [region, setRegion] = useState("north_cluster");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [submissionError, setSubmissionError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [taskDecisions, setTaskDecisions] = useState<Record<number, TaskDecision>>({});

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
          projectSummary,
          contextNotes,
          contextType: "meeting_notes",
          competitor: competitor || undefined,
          region: region || undefined,
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

  return (
    <section className="decision-shell">
      <header className="decision-header panel">
        <div className="decision-header-copy">
          <div className="eyebrow">Public test MVP · no login</div>
          <h1>Your next move, not more noise.</h1>
          <p>
            Agent.Chappie keeps the observation layer hidden, learns from competitive context in the background, and
            shows only the next three actions worth making.
          </p>
        </div>

        <div className="project-status">
          <div className="status-stack">
            <span className="status-label">Project</span>
            <strong>{projectId || "North Cluster Soccer Academy"}</strong>
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
                  <ul>
                    <li>{signalCounts.pricing} competitor pricing change detected</li>
                    <li>{signalCounts.closure} closure or distress signal detected</li>
                    <li>{signalCounts.offers + signalCounts.equipment} commercial offer or asset signal detected</li>
                  </ul>
                </article>

                <article className="intel-card">
                  <h3>Market Situation</h3>
                  <ul>
                    <li>{competitor || "Regional competitor"} is creating comparison pressure in {humanizeRegion(region)}.</li>
                    <li>Enrollment risk rises when parents see better offers, faster proof, or cheaper alternatives.</li>
                    <li>The current response window is measured in days, not quarters.</li>
                  </ul>
                </article>

                <article className="intel-card">
                  <h3>Recent Signals</h3>
                  {completeResult ? (
                    <ul>
                      {completeResult.result_payload.recommended_tasks.map((task) => (
                        <li key={task.rank}>{task.why_now}</li>
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
                  <h2>Ingestion layer for recurring, triggered, and ad hoc context</h2>
                </div>
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => {
                    setProjectSummary(SAMPLE_SUMMARY);
                    setContextNotes(SAMPLE_NOTES);
                    setCompetitor("FlowOps");
                    setRegion("north_cluster");
                  }}
                >
                  Load sample dataset
                </button>
              </div>

              <div className="operator-grid">
                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Recurring Monitoring</h3>
                    <button className="operator-add" type="button">
                      + Add Job
                    </button>
                  </div>
                  <div className="job-item">
                    <strong>Check competitor website</strong>
                    <span>Every Tuesday · 03:00</span>
                    <p>Last: 3 updates detected · last action: pricing adjustment triggered · impact: high</p>
                  </div>
                </article>

                <article className="operator-card">
                  <div className="operator-head">
                    <h3>Event-Based Jobs</h3>
                    <button className="operator-add" type="button">
                      + Add Job
                    </button>
                  </div>
                  <div className="job-item">
                    <strong>Google Sheet update</strong>
                    <span>Trigger: new row</span>
                    <p>Last: 2 signals extracted · last action: none</p>
                  </div>
                </article>
              </div>

              <div className="field-grid">
                <div className="field">
                  <label htmlFor="project-summary">Project summary</label>
                  <textarea
                    id="project-summary"
                    value={projectSummary}
                    onChange={(event) => setProjectSummary(event.target.value)}
                    placeholder="Describe the academy, the client, or the project pressure in one short paragraph."
                  />
                </div>

                <div className="field">
                  <label htmlFor="context-notes">Context package</label>
                  <textarea
                    id="context-notes"
                    value={contextNotes}
                    onChange={(event) => setContextNotes(event.target.value)}
                    placeholder="Paste one messy source package: notes, URL summary, file summary, or copied competitor copy."
                  />
                </div>
              </div>

              <div className="field-triple">
                <div className="field">
                  <label htmlFor="competitor">Competitor</label>
                  <input id="competitor" value={competitor} onChange={(event) => setCompetitor(event.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="region">Region</label>
                  <input id="region" value={region} onChange={(event) => setRegion(event.target.value)} />
                </div>
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
                  <h2>Source material used by the system</h2>
                </div>
              </div>

              <div className="library-list">
                <article className="library-item">
                  <strong>Long_Island_Soccer.pdf</strong>
                  <span>Extracted: pricing table</span>
                  <p>Last used: 2 tasks ago</p>
                </article>
                <article className="library-item">
                  <strong>Untitled.md</strong>
                  <span>Extracted: competitor list</span>
                  <p>Last used: 1 task ago</p>
                </article>
                <article className="library-item current">
                  <strong>Current inline context</strong>
                  <span>Competitor: {competitor || "not set"}</span>
                  <p>{contextNotes.slice(0, 130)}{contextNotes.length > 130 ? "..." : ""}</p>
                </article>
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
