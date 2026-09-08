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
│   ├── operations/
│   ├── payments/
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

Os scripts de `migrations/` rodam automaticamente apenas quando o volume do
PostgreSQL é criado. Para um banco local que já possuía a migration `0001`,
aplique a incremental antes de reconstruir os serviços:

```bash
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0002_operational_cutoff_and_company_meal_schedules.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0003_multi_item_orders.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0004_menu_item_images_and_soft_delete.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0005_menu_item_image_gallery.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0006_employees_and_cpf_access.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0007_stripe_pix_payments.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0008_asaas_payment_provider.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0009_payment_reliability.sql
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0010_menu_item_size_prices.sql
```

Ou execute os processos separadamente após aplicar, em ordem, todos os arquivos
SQL de `migrations/` em um PostgreSQL:

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

## Impressão direta na EPSON TM-T20X

A comanda utiliza papel de 80 mm com área útil de 68 mm. Para imprimir com um
clique, sem abrir a prévia do navegador:

1. Instale a `EPSON TM-T20X Receipt` no Windows e configure-a como impressora
   padrão, com papel de 80 mm.
2. Mantenha a stack em execução em `http://localhost:3000`.
3. Abra o terminal PowerShell na raiz do projeto e execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\iniciar-modo-impressao.ps1
```

4. No Edge separado que será aberto, faça login na Cozinha uma vez.
5. Use `Imprimir comanda` ou `Imprimir mapa do dia`. O Edge iniciado pelo script
   envia `window.print()` diretamente para a impressora padrão.

O script usa um perfil separado em `%LOCALAPPDATA%\MaviConnect\EdgePrintProfile`
para garantir que a opção de impressão em quiosque seja aplicada mesmo quando
já existe outra janela do Edge aberta. Feche esse Edge quando não quiser mais
impressão automática. No navegador aberto normalmente, a prévia continua sendo
exibida.

## Supabase em staging e produção

Use a connection string PostgreSQL do projeto apenas como `DATABASE_URL` do
backend. Aplique as migrations de `migrations/` com uma conta de deploy. Não
configure variáveis `NEXT_PUBLIC_SUPABASE_*` no frontend.

Para configurar as fotos dos pratos no storage local ou no Supabase Storage,
consulte [docs/IMAGENS_DOS_PRATOS.md](docs/IMAGENS_DOS_PRATOS.md).

Para configurar, testar no sandbox e operar pagamentos Pix via Asaas, consulte
[docs/PAGAMENTOS_ASAAS_PIX.md](docs/PAGAMENTOS_ASAAS_PIX.md).
