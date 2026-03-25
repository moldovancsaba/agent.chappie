import { neon } from "@neondatabase/serverless";

import type { Feedback, JobRequest, JobResult } from "@/lib/contracts";
import { env } from "@/lib/env";

type ProjectRecord = {
  projectId: string;
  sessionId: string;
  summary: string;
  createdAt: string;
};

type SessionState = {
  project: ProjectRecord | null;
  job: JobRequest | null;
  result: JobResult | null;
};

export type QueuedSourcePackage = {
  source_kind: "manual_text" | "url" | "uploaded_file";
  project_summary: string;
  raw_text: string;
  source_ref: string;
  file_name?: string;
  content_type?: string;
  content_base64?: string;
};

export type QueuedJobRecord = {
  job_id: string;
  project_id: string;
  status: "queued" | "processing" | "complete" | "failed";
  job_request: JobRequest;
  source_package: QueuedSourcePackage;
  claimed_at?: string | null;
  completed_at?: string | null;
  error_detail?: string | null;
};

type MemoryState = {
  projects: Map<string, ProjectRecord>;
  jobs: Map<string, JobRequest>;
  results: Map<string, JobResult>;
  feedback: Map<string, Feedback>;
  queue: Map<string, QueuedJobRecord>;
  workspaces: Map<string, Record<string, unknown>>;
  /** projectId -> factId -> dismiss/teach record (both remove chip from UI) */
  factFlashcardActions: Map<string, Map<string, { action: "forget" | "teach"; teach_note?: string | null }>>;
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
      queue: new Map(),
      workspaces: new Map(),
      factFlashcardActions: new Map(),
    };
  } else if (!globalThis.__agentChappieDemoState__.factFlashcardActions) {
    globalThis.__agentChappieDemoState__.factFlashcardActions = new Map();
  }
  return globalThis.__agentChappieDemoState__;
}

/** True when job queue, results, and workspace snapshots should use Neon (not in-process memory). */
export function canUseNeon() {
  if (!env.databaseUrl?.trim()) {
    return false;
  }
  if (env.demoStorageMode === "neon") {
    return true;
  }
  // Hosted queue mode is expected to persist with DATABASE_URL even if DEMO_STORAGE_MODE was left unset.
  if (env.agentBridgeMode === "queue") {
    return true;
  }
  return false;
}

function sqlClient() {
  if (!env.databaseUrl) {
    throw new Error("DATABASE_URL is required for Neon storage mode.");
  }
  return neon(env.databaseUrl);
}

let queueSchemaEnsured = false;

async function ensureQueueSchema() {
  if (!canUseNeon() || queueSchemaEnsured) {
    return;
  }
  const sql = sqlClient();
  await sql`
    create table if not exists demo_job_queue (
      job_id text primary key references demo_jobs(job_id) on delete cascade,
      project_id text not null references demo_projects(project_id) on delete cascade,
      status text not null,
      job_request jsonb not null,
      source_package jsonb not null,
      claimed_at timestamptz,
      completed_at timestamptz,
      error_detail text,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    )
  `;
  await sql`
    create index if not exists idx_demo_job_queue_status_created
    on demo_job_queue(status, created_at)
  `;
  await sql`
    create table if not exists demo_workspace_snapshots (
      project_id text primary key references demo_projects(project_id) on delete cascade,
      payload jsonb not null,
      updated_at timestamptz not null default now()
    )
  `;
  await sql`
    create table if not exists demo_fact_flashcard_actions (
      project_id text not null references demo_projects(project_id) on delete cascade,
      fact_id text not null,
      action text not null check (action in ('forget', 'teach')),
      teach_note text,
      created_at timestamptz not null default now(),
      primary key (project_id, fact_id)
    )
  `;
  queueSchemaEnsured = true;
}

function newestProjectRecord(records: ProjectRecord[]) {
  return [...records].sort((left, right) => right.createdAt.localeCompare(left.createdAt))[0] ?? null;
}

async function loadProjectState(project: ProjectRecord | null): Promise<SessionState> {
  if (!project) {
    return { project: null, job: null, result: null };
  }

  if (!canUseNeon()) {
    const results = [...memoryState().results.values()]
      .filter((result) => result.project_id === project.projectId)
      .sort((left, right) => right.completed_at.localeCompare(left.completed_at));
    const result = results[0] ?? null;
    const job = result ? (memoryState().jobs.get(result.job_id) ?? null) : null;
    return { project, job, result };
  }

  const sql = sqlClient();
  const resultRows = (await sql`
    select payload
    from demo_job_results
    where project_id = ${project.projectId}
    order by completed_at desc
    limit 1
  `) as Array<{ payload: JobResult }>;
  const result = resultRows[0]?.payload ?? null;

  const jobRows =
    result === null
      ? []
      : ((await sql`
          select payload
          from demo_jobs
          where job_id = ${result.job_id}
          limit 1
        `) as Array<{ payload: JobRequest }>);

  return {
    project,
    job: jobRows[0]?.payload ?? null,
    result,
  };
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

export async function enqueueJobForWorker(job: JobRequest, sourcePackage: QueuedSourcePackage) {
  if (!canUseNeon()) {
    memoryState().queue.set(job.job_id, {
      job_id: job.job_id,
      project_id: job.project_id,
      status: "queued",
      job_request: job,
      source_package: sourcePackage,
      claimed_at: null,
      completed_at: null,
      error_detail: null,
    });
    return;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  await sql`
    insert into demo_job_queue (
      job_id,
      project_id,
      status,
      job_request,
      source_package
    )
    values (
      ${job.job_id},
      ${job.project_id},
      ${"queued"},
      ${JSON.stringify(job)},
      ${JSON.stringify(sourcePackage)}
    )
    on conflict (job_id) do update
      set project_id = excluded.project_id,
          status = excluded.status,
          job_request = excluded.job_request,
          source_package = excluded.source_package,
          error_detail = null,
          claimed_at = null,
          completed_at = null,
          updated_at = now()
  `;
}

export async function saveResult(result: JobResult) {
  if (!canUseNeon()) {
    memoryState().results.set(result.job_id, result);
    // "Move" semantics: once consumed and completed, keep durable result only.
    memoryState().queue.delete(result.job_id);
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
  await ensureQueueSchema();
  // "Move" semantics: remove completed payload from online queue table.
  await sql`
    delete from demo_job_queue
    where job_id = ${result.job_id}
  `;
}

export async function getLatestJobResultForProject(projectId: string): Promise<JobResult | null> {
  if (!canUseNeon()) {
    const results = [...memoryState().results.values()]
      .filter((row) => row.project_id === projectId)
      .sort((left, right) => right.completed_at.localeCompare(left.completed_at));
    const raw = results[0] ?? null;
    return raw ? normalizeStoredJobResult(raw) : null;
  }
  const sql = sqlClient();
  const rows = (await sql`
    select payload
    from demo_job_results
    where project_id = ${projectId}
    order by completed_at desc
    limit 1
  `) as Array<{ payload: JobResult }>;
  const result = rows[0]?.payload ?? null;
  return result ? normalizeStoredJobResult(result) : null;
}

export async function getResult(jobId: string): Promise<JobResult | null> {
  if (!canUseNeon()) {
    const result = memoryState().results.get(jobId) ?? null;
    return result ? normalizeStoredJobResult(result) : null;
  }
  const sql = sqlClient();
  const rows = (await sql`
    select payload
    from demo_job_results
    where job_id = ${jobId}
    limit 1
  `) as Array<{ payload: JobResult }>;
  const result = rows[0]?.payload ?? null;
  return result ? normalizeStoredJobResult(result) : null;
}

export async function getQueuedJob(jobId: string): Promise<QueuedJobRecord | null> {
  if (!canUseNeon()) {
    return memoryState().queue.get(jobId) ?? null;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  const rows = (await sql`
    select
      job_id,
      project_id,
      status,
      job_request,
      source_package,
      claimed_at,
      completed_at,
      error_detail
    from demo_job_queue
    where job_id = ${jobId}
    limit 1
  `) as Array<QueuedJobRecord>;
  return rows[0] ?? null;
}

export type PendingQueueJobRow = {
  job_id: string;
  status: "queued" | "processing";
  source_package: QueuedSourcePackage;
  created_at: string;
};

/** Jobs waiting on the private worker (for workspace synthesis when snapshots/results are empty). */
/**
 * Remove a pending queue job (`queue_job:*` in the UI) and its demo_jobs row when no result exists yet.
 * Does not delete completed jobs (those have demo_job_results and no longer appear as pending sources).
 */
export async function removeQueuedJobById(projectId: string, jobId: string): Promise<void> {
  if (!canUseNeon()) {
    const row = memoryState().queue.get(jobId);
    if (!row || row.project_id !== projectId) {
      return;
    }
    memoryState().queue.delete(jobId);
    memoryState().jobs.delete(jobId);
    return;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  await sql`
    delete from demo_jobs
    where job_id = ${jobId}
      and project_id = ${projectId}
      and not exists (select 1 from demo_job_results r where r.job_id = ${jobId})
  `;
}

export async function listPendingQueueJobsForProject(projectId: string): Promise<PendingQueueJobRow[]> {
  if (!canUseNeon()) {
    const rows = [...memoryState().queue.values()].filter(
      (q) => q.project_id === projectId && (q.status === "queued" || q.status === "processing"),
    );
    rows.sort((a, b) => {
      const ta = a.job_request?.submitted_at ?? "";
      const tb = b.job_request?.submitted_at ?? "";
      return ta.localeCompare(tb);
    });
    return rows.map((q) => ({
      job_id: q.job_id,
      status: q.status as "queued" | "processing",
      source_package: q.source_package,
      created_at: q.job_request?.submitted_at ?? new Date().toISOString(),
    }));
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  const rows = (await sql`
    select job_id, status, source_package, created_at
    from demo_job_queue
    where project_id = ${projectId}
      and status in ('queued', 'processing')
    order by created_at asc
  `) as Array<{
    job_id: string;
    status: string;
    source_package: QueuedSourcePackage;
    created_at: Date | string;
  }>;
  return rows.map((r) => ({
    job_id: r.job_id,
    status: r.status as "queued" | "processing",
    source_package: r.source_package,
    created_at: typeof r.created_at === "string" ? r.created_at : (r.created_at as Date).toISOString(),
  }));
}

export async function claimNextQueuedJob(): Promise<QueuedJobRecord | null> {
  if (!canUseNeon()) {
    const queued = [...memoryState().queue.values()].find((q) => q.status === "queued") ?? null;
    if (!queued) {
      return null;
    }
    queued.status = "processing";
    queued.claimed_at = new Date().toISOString();
    memoryState().queue.set(queued.job_id, queued);
    return queued;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  // If a worker dies mid-job, rows stay "processing" forever. Re-queue after a quiet window.
  await sql`
    update demo_job_queue
    set status = ${"queued"},
        claimed_at = null,
        error_detail = null,
        updated_at = now()
    where status = ${"processing"}
      and claimed_at is not null
      and claimed_at < now() - interval '5 minutes'
  `;
  const rows = (await sql`
    with next_job as (
      select job_id
      from demo_job_queue
      where status = 'queued'
      order by created_at asc
      limit 1
      for update skip locked
    )
    update demo_job_queue q
    set status = 'processing',
        claimed_at = now(),
        updated_at = now()
    from next_job
    where q.job_id = next_job.job_id
    returning
      q.job_id,
      q.project_id,
      q.status,
      q.job_request,
      q.source_package,
      q.claimed_at,
      q.completed_at,
      q.error_detail
  `) as Array<QueuedJobRecord>;
  return rows[0] ?? null;
}

export async function markQueuedJobFailed(jobId: string, detail: string) {
  if (!canUseNeon()) {
    const row = memoryState().queue.get(jobId);
    if (!row) return;
    row.status = "failed";
    row.error_detail = detail;
    row.completed_at = new Date().toISOString();
    memoryState().queue.set(jobId, row);
    return;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  await sql`
    update demo_job_queue
    set status = ${"failed"},
        error_detail = ${detail},
        completed_at = now(),
        updated_at = now()
    where job_id = ${jobId}
  `;
}

export async function saveWorkspaceSnapshot(projectId: string, payload: Record<string, unknown>) {
  if (!canUseNeon()) {
    memoryState().workspaces.set(projectId, payload);
    return;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  await sql`
    insert into demo_workspace_snapshots (project_id, payload)
    values (${projectId}, ${JSON.stringify(payload)})
    on conflict (project_id) do update
      set payload = excluded.payload,
          updated_at = now()
  `;
}

export async function getWorkspaceSnapshot(projectId: string): Promise<Record<string, unknown> | null> {
  if (!canUseNeon()) {
    return memoryState().workspaces.get(projectId) ?? null;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  const rows = (await sql`
    select payload
    from demo_workspace_snapshots
    where project_id = ${projectId}
    limit 1
  `) as Array<{ payload: Record<string, unknown> }>;
  return rows[0]?.payload ?? null;
}

export type FactFlashcardClientAction = "forget" | "teach";

export async function recordFactFlashcardAction(
  projectId: string,
  factId: string,
  action: FactFlashcardClientAction,
  teachNote?: string | null
) {
  if (!canUseNeon()) {
    let byProject = memoryState().factFlashcardActions.get(projectId);
    if (!byProject) {
      byProject = new Map();
      memoryState().factFlashcardActions.set(projectId, byProject);
    }
    byProject.set(factId, { action, teach_note: teachNote?.trim() || null });
    return;
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  const note = action === "teach" ? teachNote?.trim() ?? null : null;
  await sql`
    insert into demo_fact_flashcard_actions (project_id, fact_id, action, teach_note)
    values (${projectId}, ${factId}, ${action}, ${note})
    on conflict (project_id, fact_id) do update
      set action = excluded.action,
          teach_note = excluded.teach_note,
          created_at = now()
  `;
}

export async function getHiddenFactChipIds(projectId: string): Promise<Set<string>> {
  if (!canUseNeon()) {
    const inner = memoryState().factFlashcardActions.get(projectId);
    return new Set(inner ? [...inner.keys()] : []);
  }
  await ensureQueueSchema();
  const sql = sqlClient();
  const rows = (await sql`
    select fact_id
    from demo_fact_flashcard_actions
    where project_id = ${projectId}
  `) as Array<{ fact_id: string }>;
  return new Set(rows.map((row) => row.fact_id));
}

export async function filterWorkspaceHiddenFactChips<
  T extends {
    fact_chips: Array<{ fact_id: string }>;
    intelligence_cards?: Array<{ card_id: string }>;
    visible_intelligence_cards?: Array<{ card_id: string }>;
  },
>(
  projectId: string,
  workspace: T
): Promise<T> {
  const hidden = await getHiddenFactChipIds(projectId);
  if (!hidden.size) {
    return workspace;
  }
  return {
    ...workspace,
    fact_chips: (workspace.fact_chips ?? []).filter((chip) => !hidden.has(chip.fact_id)),
    intelligence_cards: (workspace.intelligence_cards ?? []).filter((card) => !hidden.has(card.card_id)),
    visible_intelligence_cards: (workspace.visible_intelligence_cards ?? []).filter((card) => !hidden.has(card.card_id)),
  };
}

export function normalizeStoredJobResult(result: JobResult): JobResult {
  if (
    result.status !== "complete" ||
    typeof result.result_payload !== "object" ||
    result.result_payload === null ||
    !("recommended_tasks" in result.result_payload) ||
    !Array.isArray(result.result_payload.recommended_tasks)
  ) {
    return result;
  }

  return {
    ...result,
    result_payload: {
      ...result.result_payload,
      recommended_tasks: result.result_payload.recommended_tasks.map((task) => ({
        ...task,
        title: normalizeLegacyTaskText(task.title),
        why_now: normalizeLegacyTaskText(task.why_now),
        expected_advantage: normalizeLegacyTaskText(task.expected_advantage),
        execution_steps: task.execution_steps?.map((step: string) => normalizeLegacyTaskText(step)),
        done_definition: task.done_definition ? normalizeLegacyTaskText(task.done_definition) : task.done_definition,
      })),
    },
  };
}

function normalizeLegacyTaskText(value: string): string {
  return value
    .replaceAll("The worker drafted a buyer-pressure segment:", "We drafted a buyer-pressure segment from your source set:")
    .replaceAll("The worker drafted a pricing segment from the source set:", "We drafted a pricing segment from your source set:")
    .replaceAll("The worker drafted an asymmetric opportunity segment from the source set:", "We drafted an asymmetric opportunity segment from your source set:")
    .replaceAll("current competitor frame", "strongest visible competitor claim")
    .replaceAll("current market frame", "strongest visible market claim")
    .replaceAll(
      "The source set is signaling how competitors or the market frame buyer value right now.",
      "We can see how competitors and the market are framing buyer value right now."
    )
    .replaceAll(
      "If this positioning becomes the default comparison language, your current offer may lose urgency or clarity.",
      "If you do not answer that framing quickly, your current offer can lose urgency during live comparisons."
    );
}

export function resultNeedsRefresh(result: JobResult | null): boolean {
  if (
    !result ||
    result.status !== "complete" ||
    typeof result.result_payload !== "object" ||
    result.result_payload === null ||
    !("recommended_tasks" in result.result_payload) ||
    !Array.isArray(result.result_payload.recommended_tasks)
  ) {
    return false;
  }

  return result.result_payload.recommended_tasks.some((task) => {
    const combined = [
      task.title,
      task.why_now,
      task.expected_advantage,
      ...(task.execution_steps ?? []),
      task.done_definition ?? "",
    ]
      .join(" ")
      .toLowerCase();
    return (
      combined.includes("the worker drafted") ||
      combined.includes("current source set is building a market picture") ||
      combined.includes("no immediate checklist move yet") ||
      combined.includes("current competitor frame") ||
      combined.includes("buyer-facing response") ||
      combined.includes("use the linked intelligence")
    );
  });
}

export async function getJob(jobId: string): Promise<JobRequest | null> {
  if (!canUseNeon()) {
    return memoryState().jobs.get(jobId) ?? null;
  }
  const sql = sqlClient();
  const rows = (await sql`
    select payload
    from demo_jobs
    where job_id = ${jobId}
    limit 1
  `) as Array<{ payload: JobRequest }>;
  return rows[0]?.payload ?? null;
}

export async function getLatestSessionState(sessionId: string): Promise<SessionState> {
  if (!canUseNeon()) {
    const latestSessionProject = newestProjectRecord(
      [...memoryState().projects.values()].filter((project) => project.sessionId === sessionId)
    );
    const latestGlobalProject = newestProjectRecord([...memoryState().projects.values()]);
    const selectedProject =
      latestSessionProject && latestGlobalProject
        ? (latestSessionProject.createdAt >= latestGlobalProject.createdAt ? latestSessionProject : latestGlobalProject)
        : (latestSessionProject ?? latestGlobalProject);
    return loadProjectState(selectedProject);
  }

  const sql = sqlClient();
  const sessionProjectRows = (await sql`
    select project_id, session_id, summary, created_at
    from demo_projects
    where session_id = ${sessionId}
    order by created_at desc
    limit 1
  `) as Array<{
    project_id: string;
    session_id: string;
    summary: string;
    created_at: string;
  }>;

  const globalProjectRows = (await sql`
    select project_id, session_id, summary, created_at
    from demo_projects
    order by created_at desc
    limit 1
  `) as Array<{
    project_id: string;
    session_id: string;
    summary: string;
    created_at: string;
  }>;

  const sessionProjectRow = sessionProjectRows[0];
  const globalProjectRow = globalProjectRows[0];
  const selectedRow =
    sessionProjectRow && globalProjectRow
      ? (sessionProjectRow.created_at >= globalProjectRow.created_at ? sessionProjectRow : globalProjectRow)
      : (sessionProjectRow ?? globalProjectRow);

  if (!selectedRow) {
    return { project: null, job: null, result: null };
  }

  return loadProjectState({
    projectId: selectedRow.project_id,
    sessionId: selectedRow.session_id,
    summary: selectedRow.summary,
    createdAt: selectedRow.created_at,
  });
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
