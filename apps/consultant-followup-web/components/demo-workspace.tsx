"use client";

import { FormEvent, useEffect, useState } from "react";

import { feedbackSchema, type JobRequest, type JobResult } from "@/lib/contracts";
import { generateId } from "@/lib/ids";

const SAMPLE_SUMMARY = `ACME is reviewing a milestone plan that slipped after a vendor dependency changed. The consultant needs a short, prioritized follow-up list after the review meeting.`;
const SAMPLE_NOTES = `The client reviewed the current milestone plan and called out a likely delay caused by a vendor dependency. The consultant agreed to send a recap, revise the milestone plan, and clarify ownership for three open actions before the next checkpoint.`;

type FeedbackDraft = {
  done: string[];
  edited: string[];
  declined: string[];
};

function isCompleteResultWithTasks(
  result: JobResult | null
): result is JobResult & { result_payload: { recommended_tasks: string[]; summary: string } } {
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

export function DemoWorkspace() {
  const [sessionId, setSessionId] = useState("anonymous-loading");
  const [projectId, setProjectId] = useState("");
  const [projectSummary, setProjectSummary] = useState(SAMPLE_SUMMARY);
  const [contextNotes, setContextNotes] = useState(SAMPLE_NOTES);
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
      edited: [...jobResult.result_payload.recommended_tasks],
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
      const response = await fetch("/api/demo/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          projectId: projectId || undefined,
          projectSummary,
          contextNotes,
          contextType: "meeting_notes",
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "The demo job submission failed.");
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

      const response = await fetch("/api/demo/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "The feedback payload could not be saved.");
      }

      setFeedbackStatus(`Feedback saved as ${body.feedback_id}.`);
    } catch (error) {
      setFeedbackStatus(error instanceof Error ? error.message : "Unknown feedback error.");
    } finally {
      setIsSavingFeedback(false);
    }
  }

  function updateDraft(bucket: keyof FeedbackDraft, value: string) {
    const lines = value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    setFeedbackDraft((current) => ({ ...current, [bucket]: lines }));
  }

  return (
    <section className="workspace">
      <form className="panel section-card" onSubmit={handleSubmit}>
        <h2>Submit one public demo job</h2>
        <p className="lead">
          This page uses anonymous demo identifiers only. It validates the contract shape, stores the payload through a
          demo-safe boundary, and returns a contract-shaped result without adding auth or scheduler code.
        </p>

        <div className="field">
          <label htmlFor="project-summary">Project summary</label>
          <textarea
            id="project-summary"
            value={projectSummary}
            onChange={(event) => setProjectSummary(event.target.value)}
            placeholder="Describe the client project in one short paragraph."
          />
        </div>

        <div className="field">
          <label htmlFor="context-notes">Meeting notes or context</label>
          <textarea
            id="context-notes"
            value={contextNotes}
            onChange={(event) => setContextNotes(event.target.value)}
            placeholder="Paste demo-safe client context here."
          />
          <span className="hint">
            Use only demo-safe material here. This public test version intentionally has no login, no access control,
            and no trusted user ownership.
          </span>
        </div>

        <div className="button-row">
          <button className="button-primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting job..." : "Submit follow-up recommendation job"}
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => {
              setProjectSummary(SAMPLE_SUMMARY);
              setContextNotes(SAMPLE_NOTES);
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
          <p className="lead">The app submits a Job Request, retrieves a Job Result, and then lets the public tester submit Feedback.</p>

          <div className="status-grid">
            <span className="status-pill">Auth deferred · demo only</span>
            <span className="status-pill">Scheduler state handled as UI metadata</span>
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

          {jobResult ? (
            <div className="data-card">
              <h3>Job Result v1</h3>
              <pre>{JSON.stringify(jobResult, null, 2)}</pre>
            </div>
          ) : null}
        </div>

        <div className="panel section-card">
          <h2>Feedback path</h2>
          <p className="lead">Edit the returned tasks into demo feedback buckets, then save one contract-shaped Feedback payload.</p>

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
              <pre>Submit a demo job to populate the feedback flow.</pre>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
