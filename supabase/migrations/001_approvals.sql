-- Approvals: anything that spends money waits here until a human approves it.
create table if not exists approvals (
  id                 uuid primary key default gen_random_uuid(),
  kind               text not null,              -- e.g. 'leads.find'
  description        text not null,              -- plain-English summary shown in the dashboard
  estimated_cost_usd numeric(10, 2) not null default 0,
  payload            jsonb not null default '{}',  -- exact request details
  payload_hash       text not null,              -- fingerprint of kind + payload
  status             text not null default 'pending'
                     check (status in ('pending', 'approved', 'rejected', 'used')),
  created_at         timestamptz not null default now(),
  decided_at         timestamptz,                -- set by the dashboard
  used_at            timestamptz
);

create index if not exists approvals_lookup on approvals (kind, payload_hash, status);

-- Row level security ON with no policies = only the server (service role key) can read/write.
alter table approvals enable row level security;
