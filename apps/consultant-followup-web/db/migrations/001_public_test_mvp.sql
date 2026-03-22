create table if not exists demo_projects (
  project_id text primary key,
  session_id text not null,
  summary text not null,
  created_at timestamptz not null default now()
);

create table if not exists demo_jobs (
  job_id text primary key,
  app_id text not null,
  project_id text not null references demo_projects(project_id) on delete cascade,
  priority_class text not null,
  job_class text not null,
  submitted_at timestamptz not null,
  requested_capability text not null,
  requested_by text,
  payload jsonb not null
);

create table if not exists demo_job_results (
  job_id text primary key references demo_jobs(job_id) on delete cascade,
  project_id text not null references demo_projects(project_id) on delete cascade,
  status text not null,
  completed_at timestamptz not null,
  payload jsonb not null
);

create table if not exists demo_feedback (
  feedback_id text primary key,
  job_id text not null references demo_jobs(job_id) on delete cascade,
  project_id text not null references demo_projects(project_id) on delete cascade,
  feedback_type text not null,
  user_action text not null,
  submitted_at timestamptz not null,
  payload jsonb not null
);

create index if not exists idx_demo_jobs_project_id on demo_jobs(project_id);
create index if not exists idx_demo_job_results_project_id on demo_job_results(project_id);
create index if not exists idx_demo_feedback_project_id on demo_feedback(project_id);
