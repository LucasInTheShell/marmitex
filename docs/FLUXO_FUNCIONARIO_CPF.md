# Fluxo de pedidos do funcionário por CPF

## Objetivo

O frontend existente em `/funcionario` deixou de ser uma demonstração. O funcionário informa somente o CPF, consulta os cardápios reais da empresa e confirma um pedido que é salvo em `orders` e aparece no painel da cozinha.

O funcionário **não é uma conta**. As roles de `accounts` continuam sendo apenas `admin`, `company` e `kitchen`. O novo registro `employees` guarda a relação entre CPF e empresa e fornece os dados que já são exigidos pelo pedido: nome, telefone, setor e matrícula opcional.

## Fluxo completo

```text
CPF em /funcionario
        |
        v
POST /api/v1/employee/access
        |
        +-- procura employees.cpf e verifica funcionário/empresa ativos
        +-- cria employee_sessions com hash do token e validade de 12 h
        |
        v
cookie HTTP-only no servidor Next.js
        |
        +-- GET /employee/me
        +-- GET /employee/menus/available
        |
        v
frontend existente: cardápio -> detalhes -> revisão
        |
        v
POST /api/v1/employee/orders
        |
        +-- identidade e company_id vêm da sessão, nunca do navegador
        +-- reutiliza CreateOrder
        +-- valida menu, horário, cutoff, tamanho, preço e duplicidade
        |
        v
orders + order_items -> painel da cozinha
```

## Banco de dados

A migration `migrations/0006_employees_and_cpf_access.sql` cria:

- `employees`: cadastro operacional do funcionário e vínculo com uma empresa;
- `employee_sessions`: sessões opacas e temporárias separadas das sessões de contas;
- índices de consulta por empresa e sessão ativa;
- importação inicial dos funcionários encontrados nos pedidos já existentes.

Nesta primeira versão, o CPF é único no sistema e, portanto, identifica uma única empresa. Se futuramente a mesma pessoa puder pedir por duas empresas, o acesso precisará receber também um identificador da empresa ou um segundo fator.

Para aplicar em um volume Docker existente:

```powershell
Get-Content migrations\0006_employees_and_cpf_access.sql | docker compose exec -T database psql -U mavi -d mavi_connect -v ON_ERROR_STOP=1
```

As migrations montadas em `/docker-entrypoint-initdb.d` só rodam automaticamente quando o volume do PostgreSQL é criado pela primeira vez.

## Cadastro de funcionário

O suporte de cadastro está disponível no backend para contas `company` e `admin`. A interface administrativa atual não foi redesenhada nesta entrega.

### Pela API com uma conta Company

O `company_id` é obtido da sessão e não precisa ser enviado:

```http
POST /api/v1/employees
Authorization: Bearer TOKEN_DA_EMPRESA
Content-Type: application/json

{
  "name": "Maria da Silva",
  "cpf": "12345678901",
  "phone": "11999999999",
  "department": "Financeiro",
  "internal_id": "1042"
}
```

Uma conta admin usa o mesmo endpoint, mas informa `company_id`. Também existem:

- `GET /api/v1/employees`: lista somente os funcionários da conta Company; admin pode filtrar por `company_id`;
- `PATCH /api/v1/employees/{id}`: edita dados ou altera `active`;
- `POST /api/v1/employee/access`: acesso público por CPF;
- `GET /api/v1/employee/me`: identidade da sessão;
- `POST /api/v1/employee/logout`: revoga a sessão;
- `GET /api/v1/employee/menus/available`: cardápios e horários da empresa do funcionário;
- `POST /api/v1/employee/orders`: cria o pedido no contexto do funcionário.

### Diretamente no PostgreSQL local

Use apenas para teste local, substituindo o e-mail da conta Company e os dados:

```powershell
docker compose exec database psql -U mavi -d mavi_connect -c "insert into employees (company_id, name, cpf, phone, department, internal_id) select company_id, 'Maria da Silva', '12345678901', '11999999999', 'Financeiro', '1042' from accounts where email = 'empresa@mavi.local' and role = 'company';"
```

Depois, abra `http://localhost:3000/funcionario` e informe `12345678901`.

## Regras de segurança e domínio

- O cookie `mavi_employee_session` é `HTTP-only`, `SameSite=Lax` e, em produção, `Secure`.
- O banco armazena somente SHA-256 do token; o token bruto fica no cookie.
- A sessão dura `EMPLOYEE_SESSION_TTL_HOURS`, com padrão de 12 horas e máximo de 24.
- CPF inválido, desconhecido, funcionário inativo e empresa inativa retornam a mesma resposta 401, evitando indicar quais CPFs existem.
- O payload do pedido não aceita `company_id`, nome, telefone, setor ou CPF. Esses dados sempre vêm do funcionário autenticado.
- A disponibilidade exibida e a criação usam a mesma empresa, o mesmo cardápio publicado e as mesmas regras de cutoff.
- A `Idempotency-Key` evita pedidos duplicados em repetição de rede; a regra atual também limita o funcionário a um pedido por empresa e data.

CPF isolado é uma identificação de baixa segurança, porque pode ser conhecido por terceiros. Antes de expor este endpoint diretamente na internet, recomenda-se adicionar rate limiting por IP/dispositivo e, se o risco exigir, um segundo fator curto fornecido pela empresa. Isso não exige transformar o funcionário em uma conta.

## Principais arquivos

- `backend-python/app/modules/employees/domain`: entidade, contratos e erros de domínio;
- `backend-python/app/modules/employees/application/services.py`: acesso por CPF e cadastro;
- `backend-python/app/modules/employees/infrastructure/repository.py`: SQL de funcionários e sessões;
- `backend-python/app/modules/employees/api/router.py`: endpoints públicos, do funcionário e de gestão;
- `frontend-next/src/components/employee-entry.tsx`: entrada por CPF;
- `frontend-next/src/app/funcionario/actions.ts`: ações server-side e cookie;
- `frontend-next/src/app/funcionario/pedido/page.tsx`: carrega funcionário e cardápio real;
- `frontend-next/src/components/employee-order-flow.tsx`: mantém o fluxo visual e envia o pedido real.
