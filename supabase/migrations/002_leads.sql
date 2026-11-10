-- Leads: local businesses with no (real) website, plus inbound requests from the website form.
create table if not exists leads (
  id                uuid primary key default gen_random_uuid(),
  place_id          text unique,                 -- Google place id; unique so reruns update instead of duplicating
  source            text not null default 'places' check (source in ('places', 'inbound')),

  business_name     text not null,
  category          text,                        -- the search term that found it, e.g. 'plumber'
  primary_type      text,                        -- Google's type, e.g. 'plumber'
  city              text,
  address           text,
  phone             text,
  email             text,                        -- inbound leads only
  website_uri       text,
  website_status    text check (website_status in ('none', 'social_only')),
  rating            numeric(2, 1),
  user_rating_count integer,
  opening_hours     jsonb,
  google_maps_uri   text,
  photos            jsonb,                       -- photo references (not the images themselves)

  score             integer check (score between 0 and 100),
  score_reason      text,                        -- one-line explanation
  score_breakdown   jsonb,                       -- points per factor

  enrichment        jsonb,                       -- Claude's summary, services, pitch...
  enriched_at       timestamptz,

  status            text not null default 'new'
                    check (status in ('new', 'demo_built', 'contacted', 'replied', 'won', 'lost')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists leads_score on leads (score desc);
create index if not exists leads_status on leads (status);

-- Do-not-contact list. A lead matching ANY filled-in field here is never saved as contactable.
create table if not exists dnc (
  id          uuid primary key default gen_random_uuid(),
  place_id    text,
  phone       text,
  email       text,
  reason      text,
  created_at  timestamptz not null default now(),
  check (place_id is not null or phone is not null or email is not null)
);

-- Waitlist for the future founders product (website /founders page).
create table if not exists waitlist (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  email         text not null unique,
  linkedin_url  text,
  source        text,
  created_at    timestamptz not null default now()
);

alter table leads enable row level security;
alter table dnc enable row level security;
alter table waitlist enable row level security;
