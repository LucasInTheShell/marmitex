# Contribuindo

- Código e comentários em inglês; interface em português do Brasil.
- Alterações de schema entram primeiro em `migrations/` e precisam funcionar no
  PostgreSQL local e no Supabase.
- O frontend acessa dados somente por `frontend-next/src/lib/api/client.ts`.
- Cada módulo do backend separa `api`, `application`, `domain` e
  `infrastructure`. Domínio e aplicação não importam FastAPI ou psycopg.
- Tokens, senhas, CPF, telefone, corpo, query string e IP não entram em logs.
- Novos processos Go devem ser consumidores assíncronos. Eles não substituem a
  FastAPI no fluxo HTTP sem uma nova decisão de arquitetura.

Antes de abrir um PR, execute as verificações descritas no README.
