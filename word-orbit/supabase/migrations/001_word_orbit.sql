-- Word Orbit database setup.
-- Run this once in Supabase: Dashboard > SQL Editor > New query > paste > Run.

-- One row per family account: all learners and progress as one JSON document.
create table if not exists public.families (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.families enable row level security;

-- Each parent can only see and change their own family's data.
drop policy if exists "families: read own" on public.families;
create policy "families: read own" on public.families
  for select using (auth.uid() = user_id);

drop policy if exists "families: insert own" on public.families;
create policy "families: insert own" on public.families
  for insert with check (auth.uid() = user_id);

drop policy if exists "families: update own" on public.families;
create policy "families: update own" on public.families
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "families: delete own" on public.families;
create policy "families: delete own" on public.families
  for delete using (auth.uid() = user_id);

-- Family Plan status. Only the Stripe webhook (service role) writes here,
-- so a user cannot give themselves the paid plan.
create table if not exists public.subscriptions (
  user_id                uuid primary key references auth.users (id) on delete cascade,
  stripe_customer_id     text unique,
  stripe_subscription_id text,
  status                 text,          -- active, trialing, past_due, canceled, unpaid ...
  plan                   text,          -- monthly or yearly
  current_period_end     timestamptz,
  updated_at             timestamptz not null default now()
);

alter table public.subscriptions enable row level security;

drop policy if exists "subscriptions: read own" on public.subscriptions;
create policy "subscriptions: read own" on public.subscriptions
  for select using (auth.uid() = user_id);
-- No insert/update/delete policies on purpose: only the service role can write.
