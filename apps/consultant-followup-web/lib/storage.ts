import { neon } from "@neondatabase/serverless";

import type { Feedback, JobRequest, JobResult } from "@/lib/contracts";
import { env } from "@/lib/env";

type ProjectRecord = {
  projectId: string;
  sessionId: string;
  summary: string;
  createdAt: string;
};

type MemoryState = {
  projects: Map<string, ProjectRecord>;
  jobs: Map<string, JobRequest>;
  results: Map<string, JobResult>;
  feedback: Map<string, Feedback>;
};

declare global {
  var __agentChappieDemoState__: MemoryState | undefined;
}

function memoryState(): MemoryState {
  if (!globalThis.__agentChappieDemoState__) {
    globalThis.__agentChappieDemoState__ = {
      projects: new Map(),
      jobs: new Map(),
      results: new Map(),
      feedback: new Map(),
    };
  }
  return globalThis.__agentChappieDemoState__;
}

function canUseNeon() {
  return env.demoStorageMode === "neon" && Boolean(env.databaseUrl);
}

function sqlClient() {
  if (!env.databaseUrl) {
    throw new Error("DATABASE_URL is required for Neon storage mode.");
  }
  return neon(env.databaseUrl);
}

export async function saveProject(project: ProjectRecord) {
  if (!canUseNeon()) {
    memoryState().projects.set(project.projectId, project);
    return;
  }
  const sql = sqlClient();
  await sql`
    insert into demo_projects (project_id, session_id, summary, created_at)
    values (${project.projectId}, ${project.sessionId}, ${project.summary}, ${project.createdAt})
    on conflict (project_id) do update
      set summary = excluded.summary,
          session_id = excluded.session_id
  `;
}

export async function saveJob(job: JobRequest) {
  if (!canUseNeon()) {
    memoryState().jobs.set(job.job_id, job);
    return;
  }
  const sql = sqlClient();
  await sql`
    insert into demo_jobs (
      job_id,
      app_id,
      project_id,
      priority_class,
      job_class,
      submitted_at,
      requested_capability,
      requested_by,
      payload
    )
    values (
      ${job.job_id},
      ${job.app_id},
      ${job.project_id},
      ${job.priority_class},
      ${job.job_class},
      ${job.submitted_at},
      ${job.requested_capability},
      ${job.requested_by ?? null},
      ${JSON.stringify(job)}
    )
  `;
}

export async function saveResult(result: JobResult) {
  if (!canUseNeon()) {
    memoryState().results.set(result.job_id, result);
    return;
  }
  const sql = sqlClient();
  await sql`
    insert into demo_job_results (job_id, project_id, status, completed_at, payload)
    values (
      ${result.job_id},
      ${result.project_id},
      ${result.status},
      ${result.completed_at},
      ${JSON.stringify(result)}
    )
    on conflict (job_id) do update
      set status = excluded.status,
          completed_at = excluded.completed_at,
          payload = excluded.payload
  `;
}

export async function getResult(jobId: string): Promise<JobResult | null> {
  if (!canUseNeon()) {
    return memoryState().results.get(jobId) ?? null;
  }
  const sql = sqlClient();
  const rows = (await sql`
    select payload
    from demo_job_results
    where job_id = ${jobId}
    limit 1
  `) as Array<{ payload: JobResult }>;
  return rows[0]?.payload ?? null;
}

export async function saveFeedback(feedback: Feedback) {
  if (!canUseNeon()) {
    memoryState().feedback.set(feedback.feedback_id, feedback);
    return;
  }
  const sql = sqlClient();
  await sql`
    insert into demo_feedback (
      feedback_id,
      job_id,
      project_id,
      feedback_type,
      user_action,
      submitted_at,
      payload
    )
    values (
      ${feedback.feedback_id},
      ${feedback.job_id},
      ${feedback.project_id},
      ${feedback.feedback_type},
      ${feedback.user_action},
      ${feedback.submitted_at},
      ${JSON.stringify(feedback)}
    )
  `;
}
