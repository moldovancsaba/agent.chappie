create table if not exists system_observations (
  signal_id text primary key,
  project_id text,
  competitor text not null,
  region text not null,
  signal_type text not null,
  summary text not null,
  source_ref text not null,
  observed_at timestamptz not null,
  confidence double precision not null,
  business_impact text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_system_observations_competitor on system_observations(competitor);
create index if not exists idx_system_observations_region on system_observations(region);
create index if not exists idx_system_observations_signal_type on system_observations(signal_type);
create index if not exists idx_system_observations_observed_at on system_observations(observed_at desc);
create index if not exists idx_system_observations_project_region on system_observations(project_id, region);
