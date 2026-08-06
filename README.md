# Mavi Connect

Agendamento de marmitas corporativas da Mavi. O contexto e as regras do projeto
estão em [`CLAUDE.md`](./CLAUDE.md) — leia antes de mexer no código.

## Rodando localmente

```bash
npm install
cp .env.example .env.local

npx supabase start          # sobe Postgres, Auth e Realtime locais
npx supabase status         # copie a anon key e a service_role key para .env.local
npx supabase db reset       # aplica as migrations + supabase/seed.sql

npm run dev
```

O seed cria o acesso da administração: `admin@mavi.local` / `mavi-admin-2026`.
As empresas são cadastradas pela própria área admin.

## Testes

```bash
npm run test        # unitários (Vitest)
npm run test:db     # schema + RLS contra um Postgres real
npm run test:e2e    # caminho crítico (Playwright)
npm run typecheck
```

`npm run test:db` não precisa do stack do Supabase: aplica as migrations num
banco descartável e usa `supabase/tests/shim.sql` para recriar o que o Supabase
fornece (schema `auth`, `auth.uid()`, roles da API). Ele valida as regras de RLS
de `CLAUDE.md` §6 e §7 — inclusive o fato de a conta da empresa não conseguir ler
`orders`. Requer `psql` e uma conexão de superusuário (`PGHOST`, `PGPORT`,
`PGUSER`).

`npm run test:e2e` precisa do stack completo (`npx supabase start`), porque
autentica de verdade pelo Supabase Auth. Em máquinas que já têm um Chromium
próprio, aponte `PLAYWRIGHT_CHROMIUM_EXECUTABLE` para ele.
