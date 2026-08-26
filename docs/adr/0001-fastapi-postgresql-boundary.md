# ADR 0001 — FastAPI como limite do backend

Status: aceito em 25/08/2026.

## Contexto

O frontend acessava Supabase Auth e as tabelas diretamente. Isso distribuía
autenticação, autorização e regras entre Next.js, RLS e funções SQL.

## Decisão

- Next.js é a camada de interface e consome HTTP/JSON.
- FastAPI é um monólito modular; cada domínio aplica Clean Architecture com
  camadas `api`, `application`, `domain` e `infrastructure`.
- PostgreSQL é a persistência. Docker hospeda o banco local; Supabase hospeda e
  administra o banco compartilhado.
- `migrations/` é a única fonte oficial do schema.
- O token de sessão é opaco, armazenado em hash no banco e mantido pelo Next.js
  em cookie HTTP-only.
- Go poderá operar consumidores, schedules, jobs e workers assíncronos em um
  processo separado, sem entrar no caminho HTTP atual.

## Consequências

Não existem SDKs ou chaves Supabase no frontend. RLS baseada em `auth.uid()` e
Supabase Auth deixam de ser dependências da aplicação. Toda rota FastAPI faz sua
própria autenticação e autorização, mesmo quando o Next.js já protege a tela.
