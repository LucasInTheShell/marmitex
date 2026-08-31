# Fluxo de pedidos (`orders`)

Este documento descreve a implementação do módulo de pedidos no backend, do
contrato HTTP até o PostgreSQL. O escopo atual permite que uma conta
`CompanyAccount` registre um pedido em nome de um funcionário. A futura role
`Employee` ainda não foi criada, mas poderá reutilizar os mesmos casos de uso.

## Decisões de domínio

Um pedido é um agregado composto por:

- um cabeçalho `orders`, que identifica empresa, funcionário, data, horário,
  cutoff, total e estado de produção;
- uma ou mais linhas `order_items`, cada uma com prato, tamanho, quantidade,
  preço e observação;
- um único horário de refeição para todos os itens do pedido;
- um único estado de produção para o conjunto inteiro.

Assim, duas marmitas diferentes são enviadas em `items`, mas continuam fazendo
parte do mesmo pedido e do mesmo protocolo. Nesta versão existe no máximo um
pedido por `company_id + employee_cpf + date`. Para repetir o mesmo prato e
tamanho, o cliente deve aumentar `quantity`; o mesmo prato pode aparecer em
tamanhos diferentes.

Preço, nome do prato, descrição e horário são gravados como snapshots. Uma
alteração posterior no cadastro do prato ou no horário da empresa não muda o
histórico do pedido já confirmado.

## Endpoints e permissões

Todas as rotas usam o prefixo `/api/v1` e autenticação Bearer existente.

| Método e rota | Role | Finalidade |
| --- | --- | --- |
| `POST /orders` | Company | Cria um pedido para a própria empresa. |
| `GET /orders?start=&end=&status=&company_id=` | Company/Admin | Company lista somente a própria empresa; Admin pode listar e filtrar todas. |
| `GET /orders/{id}` | Company/Admin | Company lê somente pedido próprio; Admin pode ler qualquer pedido. |
| `POST /orders/{id}/cancel` | Company | Cancela pedido próprio ainda pendente e antes do cutoff. |
| `PATCH /orders/{id}/status` | Kitchen/Admin | Avança o pedido para o próximo estado permitido. |
| `GET /kitchen/production-board?date=` | Kitchen | Lista pedidos não cancelados do dia, inclusive entregues, sem CPF e telefone. |
| `GET /kitchen/production-summary?date=` | Kitchen | Resume quantidades por horário, empresa, prato e tamanho. |

O intervalo de `GET /orders` pode possuir no máximo 31 dias. Se nenhuma data
for enviada, a API usa o dia atual em `APP_TIME_ZONE`.

## Resumo de produção da cozinha

Cada pedido é salvo com a data escolhida em `date` e com o instante completo do
almoço em `scheduled_for`. O endpoint de resumo agrupa pedidos de empresas
diferentes quando o horário real é o mesmo. Portanto dois cadastros de horário
distintos que resultam em `11:00` aparecem em um único bloco de produção.

```json
{
  "date": "2026-08-31",
  "total_orders": 4,
  "total_meals": 60,
  "meal_times": [
    {
      "scheduled_for": "2026-08-31T11:00:00-03:00",
      "meal_time": "11:00:00",
      "schedule_ids": ["uuid-empresa-a", "uuid-empresa-b"],
      "schedule_labels": ["Almoço", "Turno 1"],
      "total_orders": 2,
      "total_meals": 30,
      "items": [
        {
          "menu_item_id": "uuid-parmegiana",
          "item_name": "Parmegiana de frango",
          "total_quantity": 20,
          "sizes": [
            {"size": "M", "quantity": 10},
            {"size": "G", "quantity": 10}
          ]
        },
        {
          "menu_item_id": "uuid-feijoada",
          "item_name": "Feijoada",
          "total_quantity": 10,
          "sizes": [{"size": "G", "quantity": 10}]
        }
      ]
    },
    {
      "scheduled_for": "2026-08-31T11:30:00-03:00",
      "meal_time": "11:30:00",
      "schedule_ids": ["uuid-empresa-c"],
      "schedule_labels": ["Almoço"],
      "total_orders": 2,
      "total_meals": 30,
      "items": [
        {
          "menu_item_id": "uuid-lasanha",
          "item_name": "Lasanha",
          "total_quantity": 10,
          "sizes": [{"size": "M", "quantity": 10}]
        },
        {
          "menu_item_id": "uuid-macarronada",
          "item_name": "Macarronada",
          "total_quantity": 20,
          "sizes": [{"size": "M", "quantity": 20}]
        }
      ]
    }
  ],
  "companies": [
    {
      "company_id": "uuid-empresa-a",
      "company_name": "Empresa A",
      "total_orders": 1,
      "total_meals": 20,
      "meal_times": [
        {
          "scheduled_for": "2026-08-31T11:00:00-03:00",
          "meal_time": "11:00:00",
          "total_orders": 1,
          "total_meals": 20
        }
      ],
      "items": [
        {
          "menu_item_id": "uuid-parmegiana",
          "item_name": "Parmegiana de frango",
          "total_quantity": 20,
          "sizes": [{"size": "M", "quantity": 20}]
        }
      ]
    }
  ]
}
```

Pedidos cancelados não entram nas quantidades. Pedidos entregues continuam no
resumo porque foram produzidos e precisam fazer parte do fechamento do dia. O
board individual devolve todos os pedidos não cancelados, inclusive os
`delivered`, para que o painel mostre o histórico e o total entregue do dia. O
Modo TV é que filtra os entregues e exibe somente a fila ativa.

O agrupamento `companies` é calculado pelo backend no mesmo percurso usado para
o agrupamento por horário. Isso impede o frontend de duplicar regra de negócio
e garante que ambos os resumos ignorem exatamente os mesmos cancelamentos.
Como o PostgreSQL pode devolver `timestamptz` normalizado em UTC, o serviço
converte `scheduled_for` explicitamente para `APP_TIME_ZONE` antes de produzir
o campo `meal_time`; ele nunca remove o offset antes dessa conversão.

## Contrato de criação

O corpo aceita os dados do funcionário, o horário escolhido e uma lista de
itens. Não aceita `company_id`, preço, total, cutoff ou status:

```json
{
  "date": "2026-08-31",
  "meal_schedule_id": "ef9ed897-1602-46d6-b3b3-438e8d537f57",
  "employee_name": "Maria da Silva",
  "employee_phone": "(11) 99999-8888",
  "employee_department": "Financeiro",
  "employee_cpf": "123.456.789-01",
  "employee_internal_id": "1042",
  "items": [
    {
      "menu_item_id": "670aa20f-7f60-4cbd-b3d3-d64709288d63",
      "size": "M",
      "quantity": 1,
      "notes": "Sem cebola"
    },
    {
      "menu_item_id": "7ce0ac69-2b99-4fd6-b2f7-bd417a5939e9",
      "size": "P",
      "quantity": 1,
      "notes": null
    }
  ]
}
```

Limites atuais:

- de 1 a 10 linhas por pedido;
- de 1 a 10 unidades em cada linha;
- no máximo 20 marmitas somando todas as quantidades;
- observação de até 300 caracteres por linha;
- CPF normalizado para exatamente 11 dígitos;
- telefone normalizado para 10 a 15 dígitos;
- tamanhos aceitos pela API: `P`, `M` e `G`, desde que também estejam
  cadastrados no prato.

O header opcional `Idempotency-Key`, com até 120 caracteres, protege contra
duplo clique ou retry de rede. Repetir a mesma chave e o mesmo conteúdo devolve
o pedido já criado. Reutilizar a chave com conteúdo diferente devolve `409
idempotency_conflict`.

## Resposta

A resposta `201 Created` contém o protocolo operacional, os snapshots e os
valores calculados pelo servidor:

```json
{
  "id": "9bcc5434-1f33-4f33-8168-e01fb46a873c",
  "order_number": 81,
  "company_id": "bf51e642-dfe2-4b62-b281-5e5f99ac1942",
  "company_name": "Empresa Teste",
  "date": "2026-08-31",
  "meal_schedule_id": "ef9ed897-1602-46d6-b3b3-438e8d537f57",
  "meal_schedule_label": "Almoço",
  "scheduled_for": "2026-08-31T13:00:00-03:00",
  "cutoff_at": "2026-08-31T11:30:00-03:00",
  "employee_name": "Maria da Silva",
  "employee_phone": "11999998888",
  "employee_department": "Financeiro",
  "employee_cpf": "12345678901",
  "employee_internal_id": "1042",
  "production_status": "pending",
  "total_price": 52.4,
  "created_at": "2026-08-29T12:00:00-03:00",
  "updated_at": "2026-08-29T12:00:00-03:00",
  "cancelled_at": null,
  "cancellation_reason": null,
  "items": [
    {
      "id": "72dc6719-820e-4f0b-9db3-e0fbcb96cc67",
      "menu_item_id": "670aa20f-7f60-4cbd-b3d3-d64709288d63",
      "item_name": "Frango grelhado",
      "item_description": "Arroz, feijão e salada",
      "size": "M",
      "quantity": 1,
      "unit_price": 24.9,
      "subtotal": 24.9,
      "notes": "Sem cebola"
    },
    {
      "id": "9753e2b8-2aec-48b4-b81b-0e8568139030",
      "menu_item_id": "7ce0ac69-2b99-4fd6-b2f7-bd417a5939e9",
      "item_name": "Carne de panela",
      "item_description": null,
      "size": "P",
      "quantity": 1,
      "unit_price": 27.5,
      "subtotal": 27.5,
      "notes": null
    }
  ]
}
```

## Fluxo completo da criação

```text
POST /api/v1/orders + Bearer Company
  → FastAPI valida formato e limites básicos do JSON
  → autorização carrega a conta e deriva company_id da sessão
  → CreateOrder carrega a empresa e seus horários
  → confirma que o horário está ativo e atende o dia da semana
  → carrega order_cutoff_lead_minutes do banco
  → recalcula scheduled_for e cutoff_at no fuso configurado
  → rejeita se now >= cutoff_at
  → carrega o cardápio publicado exatamente para a data
  → valida cada prato, tamanho, quantidade e preço
  → normaliza CPF/telefone e calcula subtotais/total
  → verifica a chave de idempotência, quando enviada
  → PostgresOrderRepository abre uma transação
      → insere o cabeçalho em orders
      → insere todas as linhas em order_items na ordem recebida
  → relê o agregado completo
  → schema de resposta omite campos internos
```

O frontend recebe os horários disponíveis em `GET /menus/available`, mas essa
resposta serve somente para exibição. `CreateOrder` recalcula e revalida o
cutoff no instante da confirmação. Portanto uma aba deixada aberta não consegue
criar pedido depois do prazo.

## Ciclo de produção e cancelamento

As transições válidas são lineares:

```text
pending → printed → separated → delivered
    └──────────────→ cancelled (somente via cancelamento antes do cutoff)
```

Na implementação atual `printed` continua representando o passo visual “em
preparo” usado pelo frontend. Impressão física e produção são conceitos
diferentes; quando houver agente de impressão, o ideal é adicionar estados
explícitos de produção e manter print jobs separados.

O cancelamento:

- pertence à empresa autenticada;
- só funciona em `pending`;
- exige `now < cutoff_at`;
- não apaga o pedido nem seus itens;
- registra instante, conta responsável e motivo opcional;
- usa atualização condicional no SQL para proteger contra concorrência.

A atualização de produção também usa o status anterior na cláusula `WHERE`.
Dois operadores tentando mudar o mesmo pedido simultaneamente não conseguem
pular silenciosamente uma etapa.

## Modelo PostgreSQL

A migration `migrations/0003_multi_item_orders.sql`:

1. acrescenta `cancelled` ao enum `production_status`;
2. amplia `orders` com número operacional, snapshots do horário, matrícula,
   total, idempotência, timestamps e dados de cancelamento;
3. cria `order_items` com posição, snapshots do prato, tamanho, quantidade,
   preço, subtotal e observação;
4. converte cada pedido antigo de item único em uma linha de `order_items`;
5. remove `menu_item_id` e `size` do cabeçalho depois da conversão;
6. troca a unicidade global de CPF/data por empresa/CPF/data;
7. adiciona constraints e índices para integridade e consultas operacionais.

Para um volume Docker já existente, aplique `0003` manualmente antes de subir
a API construída com o código novo:

```powershell
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0003_multi_item_orders.sql
docker compose up --build -d api
```

Em um volume novo, os arquivos `0001`, `0002` e `0003` são executados em ordem
pelo entrypoint do PostgreSQL.

## Responsabilidade de cada arquivo

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Domain | `orders/domain/entities.py` | Agregado `Order`, linhas, drafts e enum de estado. |
| Domain | `orders/domain/rules.py` | Limites e normalização de CPF/telefone. |
| Domain | `orders/domain/exceptions.py` | Erros de negócio estáveis expostos pela API. |
| Domain | `orders/domain/repositories.py` | Port de persistência e conflitos independentes de psycopg. |
| Application | `orders/application/create_order.py` | Orquestra cardápio, empresa, horário, cutoff, preço e transação. |
| Application | `orders/application/cancel_order.py` | Garante propriedade, estado pendente e prazo de cancelamento. |
| Application | `orders/application/services.py` | Consulta, detalhe, painel e transições de produção. |
| Infrastructure | `orders/infrastructure/models.py` | Converte rows PostgreSQL no agregado. |
| Infrastructure | `orders/infrastructure/repository.py` | SQL transacional, filtros, locks e hidratação dos itens. |
| API | `orders/api/schemas.py` | Contratos e limites do HTTP, sem lógica de autorização. |
| API | `orders/api/dependencies.py` | Compõe casos de uso e adapters na conexão da requisição. |
| API | `orders/api/router.py` | Rotas, roles, parâmetros e horário atual do servidor. |

Application e Domain não importam FastAPI nem psycopg. A API conhece os casos
de uso, e Infrastructure implementa os ports definidos pelo domínio.

## Principais erros de negócio

| HTTP/código | Situação |
| --- | --- |
| `409 ordering_window_closed` | O cutoff foi atingido. |
| `422 invalid_meal_schedule` | Horário não pertence à empresa, está inativo ou não atende o dia. |
| `422 menu_unavailable` | Não existe cardápio publicado com itens na data. |
| `422 menu_item_unavailable` | Um prato não está no cardápio publicado. |
| `422 invalid_order_size` | O prato não oferece o tamanho solicitado. |
| `422 menu_item_without_price` | O prato ainda não possui preço. |
| `409 order_already_exists` | A pessoa já possui pedido na empresa/data. |
| `409 idempotency_conflict` | Uma chave foi reutilizada com outro conteúdo. |
| `409 order_cannot_be_cancelled` | Pedido fora do prazo ou já em produção. |
| `409 invalid_production_status_transition` | Tentativa de pular ou retroceder estado. |
| `404 order_not_found` | Pedido inexistente ou fora do escopo da empresa. |

O `404` também é usado quando uma empresa tenta consultar pedido de outra
empresa, evitando confirmar a existência de dados de terceiros.

## Teste manual da API

Depois da migration e do rebuild, faça login com a conta Company:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login -ContentType 'application/json' -Body '{"email":"empresa@mavi.local","password":"sua-senha"}'
$headers = @{ Authorization = "Bearer $($login.token)"; "Idempotency-Key" = "teste-orders-001" }
```

Consulte primeiro os IDs realmente disponíveis:

```powershell
Invoke-RestMethod -Headers $headers -Uri 'http://localhost:8000/api/v1/menus/available?start=2026-08-31&end=2026-08-31'
```

Use `meal_schedule_id` de `available_schedules` e os IDs/tamanhos de `items` no
JSON de criação. Salve o JSON como `order.json` e execute:

```powershell
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' -InFile .\order.json -Uri http://localhost:8000/api/v1/orders
Invoke-RestMethod -Headers $headers -Uri 'http://localhost:8000/api/v1/orders?start=2026-08-31&end=2026-08-31'
```

Para testar a cozinha, faça login com uma conta `kitchen`, troque o token no
header e use:

```powershell
Invoke-RestMethod -Headers $headers -Uri 'http://localhost:8000/api/v1/kitchen/production-board?date=2026-08-31'
Invoke-RestMethod -Headers $headers -Uri 'http://localhost:8000/api/v1/kitchen/production-summary?date=2026-08-31'
Invoke-RestMethod -Method Patch -Headers $headers -ContentType 'application/json' -Body '{"production_status":"printed"}' -Uri http://localhost:8000/api/v1/orders/UUID_DO_PEDIDO/status
```

## Testes automatizados

Os testes cobrem múltiplos pratos, snapshots e total, item não publicado,
cutoff na confirmação, idempotência, cancelamento, sequência de produção,
limite de consulta, escopo Company, permissões e remoção de CPF/telefone do
painel Kitchen.

```powershell
backend-python\.venv\Scripts\python.exe -m ruff check backend-python
backend-python\.venv\Scripts\python.exe -m pytest backend-python\tests -q
```

## Integração com os painéis Next.js

As páginas autenticadas são Server Components. Elas leem o token `httpOnly` da
sessão e fazem as consultas iniciais diretamente na API, em paralelo. O token
não é exposto ao navegador.

### Painel da empresa

`frontend-next/src/app/empresa/page.tsx` carrega empresa, configurações,
cardápios disponíveis e os pedidos de uma janela de 28 dias. O componente
interativo permite:

- selecionar somente datas e horários ainda devolvidos por
  `/menus/available`;
- montar um carrinho com pratos, tamanhos, quantidades e observações distintas;
- criar o agregado inteiro por `POST /orders`, usando uma nova
  `Idempotency-Key` em cada confirmação;
- acompanhar itens, total, horário e estado reais do pedido;
- cancelar pedidos pendentes antes do cutoff.

Mesmo com o filtro visual, o backend recalcula cardápio, horário e cutoff no
momento do POST. A interface não é usada como fonte de autorização.

### Painel da cozinha

`frontend-next/src/app/cozinha/page.tsx` consulta o board e o resumo em paralelo
para a data da query string. O painel apresenta, nessa ordem:

1. resumo de produção por horário, prato e tamanho;
2. resumo por empresa, com volumes, horários e composição;
3. pedidos individuais em quatro colunas operacionais.

As mudanças de status usam Server Actions e aceitam somente o próximo passo da
sequência. Imprimir uma comanda pendente avança o pedido para `printed` depois
da janela de impressão. O mapa do dia e a comanda listam todas as linhas do
pedido, e não apenas o primeiro prato.

O painel e o Modo TV executam `router.refresh()` a cada 20 segundos. Como as
consultas usam `no-store`, cada atualização relê a API sem enviar o Bearer token
ao browser. Essa é a estratégia simples atual; SSE ou WebSocket podem substituir
o polling quando houver necessidade operacional comprovada.

Arquivos centrais da integração:

| Arquivo | Papel |
| --- | --- |
| `frontend-next/src/lib/types.ts` | Contratos de pedidos, board e resumos. |
| `frontend-next/src/lib/orders.ts` | Status, carrinho, totais e helpers puros. |
| `frontend-next/src/app/empresa/actions.ts` | Criação e cancelamento autenticados. |
| `frontend-next/src/app/empresa/panel.tsx` | Carrinho e histórico real da empresa. |
| `frontend-next/src/app/cozinha/actions.ts` | Transição autenticada de produção. |
| `frontend-next/src/app/cozinha/panel.tsx` | Resumos e quadro individual. |
| `frontend-next/src/components/kitchen-tv-dashboard.tsx` | Fila ativa para monitor. |
| `frontend-next/src/components/thermal-print-document.tsx` | Comandas multi-item. |

## O que ainda não está integrado

- A role compartilhada `Employee` e suas telas ainda não usam esta API.
- Print jobs persistidos e um agente local da EPSON continuam fora deste slice;
  hoje a impressão usa a janela padrão do navegador.
- Atualização push em tempo real ainda não existe; os painéis usam polling de
  20 segundos.
- Paginação deverá ser adicionada quando consultas administrativas crescerem;
  por enquanto o período máximo de 31 dias limita o volume.
