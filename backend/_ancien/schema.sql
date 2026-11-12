-- À exécuter UNE FOIS dans Supabase : menu « SQL Editor » > New query > coller > Run

create table if not exists public.users (
  id            bigint generated always as identity primary key,
  email         text not null unique,
  name          text not null,
  firm          text not null default '',
  password_hash text not null,
  created_at    timestamptz not null default now()
);

create table if not exists public.demo_requests (
  id         bigint generated always as identity primary key,
  name       text not null,
  email      text not null,
  firm       text not null default '',
  message    text not null default '',
  created_at timestamptz not null default now()
);

-- Sécurité : RLS activé, aucune policy => personne ne peut lire/écrire depuis le navigateur.
-- Seul votre backend (clé secrète) a accès.
alter table public.users          enable row level security;
alter table public.demo_requests  enable row level security;
