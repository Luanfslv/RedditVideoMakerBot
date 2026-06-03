-- Fila de render: threads enviadas pelo app Devvit (ou outras integrações)

create table if not exists public.studio_render_queue (
  id uuid primary key default gen_random_uuid(),
  thread_id text not null,
  title text,
  reddit_object jsonb not null,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'done', 'failed')),
  source text not null default 'devvit',
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists studio_render_queue_status_created
  on public.studio_render_queue (status, created_at desc);

alter table public.studio_render_queue enable row level security;

create policy "studio_render_queue_read" on public.studio_render_queue
  for select to anon, authenticated using (true);

create policy "studio_render_queue_write" on public.studio_render_queue
  for all to anon, authenticated using (true) with check (true);
