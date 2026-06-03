-- RedditMaker Studio: persistent config and library data

create table if not exists public.studio_config (
  id text primary key default 'default',
  config_toml text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.studio_backgrounds (
  key text primary key,
  youtube_uri text not null,
  filename text not null,
  citation text not null default '',
  position text not null default 'center',
  updated_at timestamptz not null default now()
);

create table if not exists public.studio_videos (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  title text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.studio_config enable row level security;
alter table public.studio_backgrounds enable row level security;
alter table public.studio_videos enable row level security;

create policy "studio_config_read" on public.studio_config
  for select to anon, authenticated using (true);

create policy "studio_config_write" on public.studio_config
  for all to anon, authenticated using (true) with check (true);

create policy "studio_backgrounds_read" on public.studio_backgrounds
  for select to anon, authenticated using (true);

create policy "studio_backgrounds_write" on public.studio_backgrounds
  for all to anon, authenticated using (true) with check (true);

create policy "studio_videos_read" on public.studio_videos
  for select to anon, authenticated using (true);

create policy "studio_videos_write" on public.studio_videos
  for all to anon, authenticated using (true) with check (true);
