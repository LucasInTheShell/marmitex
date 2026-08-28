# Mavi Connect

Aplicação de agendamento de marmitas corporativas da Mavi.

## Arquitetura

```text
Browser → Next.js → FastAPI → PostgreSQL
                              ├─ Docker (local)
                              └─ Supabase (staging/produção)
```

O Supabase é somente o provedor do PostgreSQL nos ambientes compartilhados.
Autenticação, sessões, autorização e regras de negócio pertencem à FastAPI. O
frontend nunca recebe `DATABASE_URL`, chaves do Supabase ou acesso direto às
tabelas.

```text
frontend-next/   Next.js 16 + React 19
backend-python/  Monólito modular FastAPI
migrations/      Fonte oficial do schema PostgreSQL
docs/            Decisões de arquitetura e operação
```

O backend é organizado por domínio:

```text
backend-python/app/
├── core/                 configuração e recursos transversais
├── api/                  composição e dependências globais HTTP
├── modules/
│   ├── auth/
│   ├── companies/
│   ├── employees/
│   ├── menus/
│   ├── orders/
│   └── kitchen/
└── cli/

Cada módulo separa:

├── api/                  routers, schemas e dependências
├── application/          casos de uso e orquestração
├── domain/               entidades, regras e ports de repositório
└── infrastructure/       PostgreSQL, hashes e outros adapters
```

Go não faz parte do caminho HTTP síncrono. Ele poderá ser adicionado depois,
em processo separado, para mensageria assíncrona, schedules, jobs e workers.

## Desenvolvimento local

Crie os arquivos locais de ambiente a partir dos exemplos:

```bash
cp .env.example .env
cp backend-python/.env.example backend-python/.env
cp frontend-next/.env.example frontend-next/.env.local
```

Suba a stack completa:

```bash
docker compose up --build
```

Ou execute os processos separadamente após aplicar
`migrations/0001_initial.sql` em um PostgreSQL:

```bash
cd backend-python
python -m venv .venv
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload

cd ../frontend-next
npm ci
npm run dev
```

Crie o primeiro administrador após aplicar a migration:

```bash
cd backend-python
python -m app.cli.create_admin --name "Admin Mavi" --email admin@mavi.com.br
```

## Verificações

```bash
cd backend-python
ruff check .
pytest

cd ../frontend-next
npm run lint
npm run typecheck
npm run test
npm run build
```

O E2E exige uma stack isolada já migrada e `E2E_DATABASE_READY=1`; ele não apaga
automaticamente o banco de desenvolvimento.

## Supabase em staging e produção

Use a connection string PostgreSQL do projeto apenas como `DATABASE_URL` do
backend. Aplique as migrations de `migrations/` com uma conta de deploy. Não
configure variáveis `NEXT_PUBLIC_SUPABASE_*` no frontend.
