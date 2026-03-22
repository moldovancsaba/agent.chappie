"use client";

import { FormEvent, useEffect, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult, type RecommendedTask } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

const SAMPLE_SUMMARY = `We run a soccer academy for talented boys and need practical decisions from regional competitor signals, not generic advice.`;
const SAMPLE_NOTES = `Saw a competitor update their homepage and LinkedIn messaging this week. They now emphasize “Go live in 7 days”, “No engineering required”, and multiple customer logos and testimonials above the fold. Our current positioning talks about flexibility and customization, but not speed. Sales calls now include questions about onboarding time and complexity.`;

type FeedbackDraft = {
  done: string[];
  edited: string[];
  declined: string[];
};

function isCompleteResultWithTasks(
  result: JobResult | null
): result is JobResult & { result_payload: { recommended_tasks: RecommendedTask[]; summary: string } } {
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

function tasksToLines(tasks: RecommendedTask[]) {
  return tasks.map((task) => task.title);
}

function updateDraftBucket(text: string) {
  return text
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function DemoWorkspace() {
  const [sessionId, setSessionId] = useState("anonymous-loading");
  const [projectId, setProjectId] = useState("");
  const [projectSummary, setProjectSummary] = useState(SAMPLE_SUMMARY);
  const [contextNotes, setContextNotes] = useState(SAMPLE_NOTES);
  const [competitor, setCompetitor] = useState("FlowOps");
  const [region, setRegion] = useState("region_unknown");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);
  const [submissionError, setSubmissionError] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [feedbackDraft, setFeedbackDraft] = useState<FeedbackDraft>({ done: [], edited: [], declined: [] });

  useEffect(() => {
    setSessionId(readOrCreateSessionId());
  }, []);

  useEffect(() => {
    if (!isCompleteResultWithTasks(jobResult)) {
      return;
    }
    setFeedbackDraft({
      done: [],
      edited: tasksToLines(jobResult.result_payload.recommended_tasks),
      declined: [],
    });
    setFeedbackStatus("");
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
    if (!jobResult) {
      return;
    }

    setIsSavingFeedback(true);
    setFeedbackStatus("");

    try {
      const action = feedbackDraft.done.length > 0 ? "done" : feedbackDraft.declined.length > 0 ? "declined" : "edited";
      const feedback = feedbackSchema.parse({
        feedback_id: generateId("feedback"),
        job_id: jobResult.job_id,
        app_id: jobResult.app_id,
        project_id: jobResult.project_id,
        feedback_type: "task_response",
        submitted_at: new Date().toISOString(),
        user_action: action,
        feedback_payload: feedbackDraft,
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
      setFeedbackStatus(JSON.stringify(body, null, 2));
    } catch (error) {
      setFeedbackStatus(error instanceof Error ? error.message : "Unknown feedback error.");
    } finally {
      setIsSavingFeedback(false);
    }
  }

  function updateDraft(bucket: keyof FeedbackDraft, value: string) {
    setFeedbackDraft((current) => ({
      ...current,
      [bucket]: updateDraftBucket(value),
    }));
  }

  return (
    <section className="workspace-shell">
      <form className="panel section-card" onSubmit={handleSubmit}>
        <h2>Competitive action input</h2>
        <p className="lead">Paste one messy source package. The private worker learns from hidden observations and returns only the top external actions.</p>

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
          <label htmlFor="context-notes">Competitive context</label>
          <textarea
            id="context-notes"
            value={contextNotes}
            onChange={(event) => setContextNotes(event.target.value)}
            placeholder="Paste messy notes, competitor messaging, URL summary, or raw market context here."
          />
          <span className="hint">The worker stores internal observations, but the UI only shows the final 3 recommended actions.</span>
        </div>

        <div className="field">
          <label htmlFor="competitor">Competitor (optional)</label>
          <input id="competitor" value={competitor} onChange={(event) => setCompetitor(event.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="region">Region (optional)</label>
          <input id="region" value={region} onChange={(event) => setRegion(event.target.value)} />
        </div>

        <div className="button-row">
          <button className="button-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting job..." : "Submit competitive action job"}
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => {
              setProjectSummary(SAMPLE_SUMMARY);
              setContextNotes(SAMPLE_NOTES);
              setCompetitor("FlowOps");
              setRegion("region_unknown");
            }}
          >
            Load sample dataset
          </button>
        </div>

        <p className="footer-note">
          <strong>Anonymous session:</strong> {sessionId}
          <br />
          <strong>Project ID:</strong> {projectId || "Will be generated on first submit"}
        </p>
      </form>

      <div className="stack">
        <div className="panel section-card">
          <h2>Result path</h2>
          <p className="lead">The app submits one Job Request and only exposes the final decision-support output, not the hidden observation layer.</p>

          <div className="status-grid">
            <span className="status-pill">Auth deferred · public test MVP</span>
            <span className="status-pill">Observation layer hidden from UI</span>
          </div>

          {submissionError ? (
            <div className="data-card">
              <h3>Submission error</h3>
              <pre>{submissionError}</pre>
            </div>
          ) : null}

          {jobRequest ? (
            <div className="data-card">
              <h3>Job Request v1</h3>
              <pre>{JSON.stringify(jobRequest, null, 2)}</pre>
            </div>
          ) : null}

          {isCompleteResultWithTasks(jobResult) ? (
            <div className="data-card">
              <h3>Recommended tasks</h3>
              <div className="task-list">
                {jobResult.result_payload.recommended_tasks.map((task) => (
                  <div className="task-card" key={task.rank}>
                    <strong>
                      {task.rank}. {task.title}
                    </strong>
                    <p>{task.why_now}</p>
                    <p>
                      <em>{task.expected_advantage}</em>
                    </p>
                    <pre>{JSON.stringify({ evidence_refs: task.evidence_refs }, null, 2)}</pre>
                  </div>
                ))}
              </div>
              <pre>{jobResult.result_payload.summary}</pre>
            </div>
          ) : null}

          {jobResult ? (
            <div className="data-card">
              <h3>Job Result v1</h3>
              <pre>{JSON.stringify(jobResult, null, 2)}</pre>
            </div>
          ) : null}
        </div>

        <div className="panel section-card">
          <h2>Feedback path</h2>
          <p className="lead">Edit the 3 returned task titles into done, edited, or declined buckets and submit one feedback object.</p>

          {isCompleteResultWithTasks(jobResult) ? (
            <>
              <div className="task-list">
                <div className="task-card">
                  <strong>Done</strong>
                  <textarea value={feedbackDraft.done.join("\n")} onChange={(event) => updateDraft("done", event.target.value)} />
                </div>
                <div className="task-card">
                  <strong>Edited</strong>
                  <textarea value={feedbackDraft.edited.join("\n")} onChange={(event) => updateDraft("edited", event.target.value)} />
                </div>
                <div className="task-card">
                  <strong>Declined</strong>
                  <textarea value={feedbackDraft.declined.join("\n")} onChange={(event) => updateDraft("declined", event.target.value)} />
                </div>
              </div>

              <div className="button-row">
                <button className="button-primary" type="button" onClick={handleSaveFeedback} disabled={isSavingFeedback}>
                  {isSavingFeedback ? "Saving feedback..." : "Submit feedback"}
                </button>
              </div>

              {feedbackStatus ? (
                <div className="data-card">
                  <h3>Feedback status</h3>
                  <pre>{feedbackStatus}</pre>
                </div>
              ) : null}
            </>
          ) : (
            <div className="data-card">
              <h3>Waiting for a result</h3>
              <pre>Submit a job to populate the feedback flow.</pre>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
