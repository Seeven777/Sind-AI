-- Execute no SQL Editor do Supabase. Troque o email ao final ANTES de executar.
create extension if not exists pgcrypto;

create table if not exists public.team_members (
  email text primary key,
  name text not null,
  role text not null default 'member' check (role in ('admin','member')),
  created_at timestamptz not null default now()
);

create or replace function public.is_team_member() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.team_members where email = lower((select auth.jwt() ->> 'email')));
$$;
create or replace function public.is_team_admin() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.team_members where email = lower((select auth.jwt() ->> 'email')) and role = 'admin');
$$;

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null check (length(trim(title)) between 1 and 220),
  description text not null default '',
  status text not null default 'ideas' check (status in ('ideas','planned','doing','review','done')),
  priority text not null default 'normal' check (priority in ('low','normal','high','urgent')),
  category text not null default 'Conteúdo',
  assignee_email text references public.team_members(email) on delete set null,
  due_date date,
  publish_date date,
  channel text not null default '',
  campaign text not null default '',
  reference_url text not null default '',
  created_by text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);
create index if not exists tasks_status_idx on public.tasks(status);
create index if not exists tasks_due_idx on public.tasks(due_date);
create index if not exists tasks_assignee_idx on public.tasks(assignee_email);

create table if not exists public.daily_updates (
  id uuid primary key default gen_random_uuid(),
  author_email text not null references public.team_members(email),
  report_date date not null,
  accomplished text not null default '',
  next_steps text not null default '',
  blockers text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(author_email, report_date)
);
create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references public.tasks(id) on delete set null,
  actor_email text not null,
  action text not null,
  detail text not null default '',
  created_at timestamptz not null default now()
);

create or replace function public.touch_updated_at() returns trigger language plpgsql as $$ begin
  new.updated_at = now();
  if tg_table_name = 'tasks' then
    if new.status = 'done' and old.status is distinct from 'done' then new.completed_at = now(); end if;
    if new.status <> 'done' and old.status = 'done' then new.completed_at = null; end if;
  end if;
  return new;
end $$;
create or replace function public.initial_completed_at() returns trigger language plpgsql as $$ begin
  if new.status = 'done' then new.completed_at = coalesce(new.completed_at, now()); end if;
  return new;
end $$;
drop trigger if exists tasks_initial_completed on public.tasks;
create trigger tasks_initial_completed before insert on public.tasks for each row execute function public.initial_completed_at();
drop trigger if exists tasks_touch on public.tasks;
create trigger tasks_touch before update on public.tasks for each row execute function public.touch_updated_at();
drop trigger if exists updates_touch on public.daily_updates;
create trigger updates_touch before update on public.daily_updates for each row execute function public.touch_updated_at();

alter table public.team_members enable row level security;
alter table public.tasks enable row level security;
alter table public.daily_updates enable row level security;
alter table public.activity_events enable row level security;

drop policy if exists team_read on public.team_members;
create policy team_read on public.team_members for select to authenticated using (public.is_team_member());
drop policy if exists team_insert on public.team_members;
create policy team_insert on public.team_members for insert to authenticated with check (public.is_team_admin());
drop policy if exists team_update on public.team_members;
create policy team_update on public.team_members for update to authenticated using (public.is_team_admin()) with check (public.is_team_admin());
drop policy if exists team_delete on public.team_members;
create policy team_delete on public.team_members for delete to authenticated using (public.is_team_admin() and email <> lower((select auth.jwt() ->> 'email')));

drop policy if exists tasks_read on public.tasks;
create policy tasks_read on public.tasks for select to authenticated using (public.is_team_member());
drop policy if exists tasks_insert on public.tasks;
create policy tasks_insert on public.tasks for insert to authenticated with check (public.is_team_member() and created_by = lower((select auth.jwt() ->> 'email')));
drop policy if exists tasks_update on public.tasks;
create policy tasks_update on public.tasks for update to authenticated using (public.is_team_member()) with check (public.is_team_member());
drop policy if exists tasks_delete on public.tasks;
create policy tasks_delete on public.tasks for delete to authenticated using (public.is_team_admin());

drop policy if exists updates_read on public.daily_updates;
create policy updates_read on public.daily_updates for select to authenticated using (public.is_team_member());
drop policy if exists updates_insert on public.daily_updates;
create policy updates_insert on public.daily_updates for insert to authenticated with check (public.is_team_member() and author_email = lower((select auth.jwt() ->> 'email')));
drop policy if exists updates_update on public.daily_updates;
create policy updates_update on public.daily_updates for update to authenticated using (author_email = lower((select auth.jwt() ->> 'email'))) with check (author_email = lower((select auth.jwt() ->> 'email')));
drop policy if exists updates_delete on public.daily_updates;
create policy updates_delete on public.daily_updates for delete to authenticated using (author_email = lower((select auth.jwt() ->> 'email')) or public.is_team_admin());

drop policy if exists events_read on public.activity_events;
create policy events_read on public.activity_events for select to authenticated using (public.is_team_member());
drop policy if exists events_insert on public.activity_events;
create policy events_insert on public.activity_events for insert to authenticated with check (public.is_team_member() and actor_email = lower((select auth.jwt() ->> 'email')));

-- ALTERE O EMAIL antes de executar este arquivo. Depois convide a mesma pessoa em Authentication > Users.
insert into public.team_members(email,name,role) values ('SEU-EMAIL@EXEMPLO.COM','Administrador','admin') on conflict(email) do nothing;
