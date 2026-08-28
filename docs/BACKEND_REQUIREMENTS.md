# Requisitos de backend — extensões do frontend

Este documento registra as lacunas de backend introduzidas pelas telas de
Employee, impressão térmica e Modo TV. A arquitetura e as funcionalidades já implementadas continuam
seguindo o `README.md` e permanecem como fonte de verdade.

## O que já existe e deve ser reutilizado

- FastAPI é responsável por autenticação, sessões, autorização e regras de
  negócio.
- PostgreSQL é a fonte de dados; Supabase pode atuar somente como provedor do
  PostgreSQL nos ambientes compartilhados.
- A sessão usa token opaco armazenado no PostgreSQL e cookie HTTP-only no
  frontend.
- As roles `admin`, `company` e `kitchen` já existem e têm proteção real na API
  e nas páginas.
- A conta `company` já é vinculada a uma empresa.
- A tabela `orders` já registra empresa, funcionário, prato, tamanho, data e
  estado de produção.
- O frontend nunca deve receber `DATABASE_URL`, hashes de senha ou acesso
  direto às tabelas.

Nada desta lista deve ser reimplementado no frontend ou substituído por acesso
direto ao banco.

## Estado das telas desta etapa

As rotas `/funcionario` e `/funcionario/pedido` são protótipos exclusivamente
visuais. Os dados são mantidos apenas no estado React durante a navegação e não
são enviados à API.

As telas `/admin/acessos-funcionarios` e
`/empresa/acesso-funcionarios` usam registros mockados. Seus botões demonstram
criação, edição, ativação, desativação e redefinição de senha, mas não persistem
alterações.

## 1. Nova role Employee

Adicionar `employee` ao modelo existente de contas:

- migration do enum PostgreSQL `account_role`;
- `AccountRole` no domínio FastAPI;
- contratos públicos da API e tipos TypeScript;
- destino pós-login `/funcionario/pedido`;
- dependência de autorização `EmployeeAccount` equivalente às dependências de
  roles atuais.

Um Employee deve acessar somente o ambiente de solicitação da empresa à qual
está vinculado. Admin e Company não devem ser convertidos em Employee para
acessar essa área.

## 2. Vínculo e cardinalidade

Regra inicial: uma conta Employee compartilhada por empresa.

Requisitos:

- `employee` exige `company_id` não nulo;
- índice único parcial em `accounts(company_id)` para `role = 'employee'`;
- a empresa precisa estar ativa para autenticar ou utilizar o acesso;
- exclusão/desativação da empresa deve impedir novas sessões Employee;
- a API nunca aceita `company_id` fornecido por uma conta Company: deve
  derivá-lo da sessão autenticada.

## 3. Gerenciamento de acessos Employee

Endpoints sugeridos, preservando o prefixo atual `/api/v1`:

- `GET /employee-accounts`
  - Admin: lista todas as empresas;
  - Company: retorna somente seu próprio acesso.
- `POST /employee-accounts`
  - Admin pode criar para qualquer empresa ativa;
  - Company pode criar somente para a empresa da sessão.
- `PATCH /employee-accounts/{id}` para nome de exibição e status.
- `POST /employee-accounts/{id}/reset-password` para redefinição segura.
- `POST /employee-accounts/{id}/activate` e `/deactivate`, ou operação
  equivalente via `PATCH`.

DTO de leitura esperado pelas telas:

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "company_name": "Acme Ltda",
  "name": "Acme Funcionários",
  "email": "funcionarios@acme.com.br",
  "status": "active",
  "last_access_at": "2026-08-28T11:42:00Z"
}
```

O backend deve continuar gerando hashes Argon2; nenhuma senha ou hash é
retornado em respostas.

## 4. Sessão e último acesso

Reutilizar o fluxo atual de login e sessão opaca. Para Employee:

- registrar `last_access_at` após autenticação válida;
- permitir revogar todas as sessões ao desativar ou redefinir senha;
- manter as mesmas propriedades de cookie HTTP-only, `SameSite` e expiração;
- aplicar rate limit ao login e à redefinição de senha antes de produção.

## 5. Identificação do funcionário

A conta é compartilhada, portanto a pessoa deve ser identificada dentro de
cada pedido. O front atual prevê:

- nome completo obrigatório;
- setor obrigatório;
- matrícula/identificação interna opcional.

Decidir antes da migration se a identificação continuará como snapshot em
`orders` ou se haverá uma entidade `employees`. Para o primeiro fluxo, manter
snapshot é coerente com a tabela atual e evita criar autenticação individual.

Se matrícula for adotada, adicionar campo opcional e índice por empresa para
consultas operacionais. Validar tamanho e formato no FastAPI.

## 6. Pedidos Employee

Criar endpoint autenticado para envio do pedido, reaproveitando o módulo
`orders`:

- derivar `company_id` da sessão Employee;
- validar que o item pertence a um cardápio publicado e disponível na data;
- aplicar horário limite configurado;
- aceitar tamanho permitido pelo prato;
- adicionar `quantity` com mínimo 1 e limite de negócio;
- adicionar `notes` opcional com limite de caracteres;
- registrar nome, setor e matrícula do funcionário;
- calcular preço no servidor, nunca confiar no valor enviado pelo frontend;
- retornar identificador/protocolo e estado inicial;
- manter a regra existente de unicidade por pessoa/data ou revisá-la
  explicitamente para o cenário de matrícula.

Contrato de criação esperado:

```json
{
  "employee_name": "Maria da Silva",
  "employee_department": "Financeiro",
  "employee_internal_id": "1042",
  "menu_item_id": "uuid",
  "date": "2026-08-28",
  "size": "M",
  "quantity": 1,
  "notes": "Sem cebola"
}
```

## 7. Cardápio do Employee

Disponibilizar leitura autenticada dos cardápios publicados para a role
Employee. A resposta precisa conter somente campos públicos:

- nome e descrição;
- acompanhamentos, caso sejam modelados;
- tamanhos disponíveis;
- preço aplicável;
- disponibilidade;
- imagem ou URL pública de imagem, quando esse recurso existir.

Admin continua responsável por editar/publicar; Employee possui somente
permissão de leitura.

## 8. Permissões obrigatórias

| Operação | Admin | Company | Employee | Kitchen |
| --- | --- | --- | --- | --- |
| Listar todos os acessos Employee | Sim | Não | Não | Não |
| Gerenciar Employee de uma empresa | Sim | Somente a própria | Não | Não |
| Ler cardápio publicado | Conforme fluxo admin | Conforme fluxo atual | Sim | Conforme necessidade operacional |
| Criar pedido Employee | Não | Não | Somente própria empresa | Não |
| Acompanhar produção | Conforme regras atuais | Somente própria empresa | Somente confirmação própria | Sim |

Todas as verificações devem ocorrer na API, próximas à consulta/mutação. A
ocultação de botões e os redirects do Next.js são apenas uma camada de
experiência, não uma fronteira de segurança.

## 9. Integração esperada

Fluxo final:

```text
Employee autenticado
  → cardápio publicado
  → identificação do funcionário
  → pedido vinculado à empresa da sessão
  → fila de produção da cozinha
  → acompanhamento pela empresa
```

## 10. Testes mínimos futuros

- Employee ativo autentica; inativo ou com empresa inativa não autentica.
- Admin gerencia qualquer acesso; Company recebe `403` ao tentar outra empresa.
- Employee recebe `403` em rotas Admin, Company e Kitchen.
- Company não consegue forjar `company_id` no payload.
- Pedido fora do horário, item não publicado, tamanho inválido e quantidade
  inválida são rejeitados.
- Redefinição de senha revoga sessões anteriores.
- DTOs nunca incluem `password_hash`, token hash ou dados de outra empresa.

## 11. Impressão térmica — EPSON TM-T20X Receipt

### Estado entregue no frontend

A Fila de Produção gera uma comanda em CSS de bobina de 80 mm e chama
`window.print()`. Esse fluxo funciona quando a EPSON TM-T20X Receipt está
instalada no Windows e selecionada na janela de impressão do navegador. A
impressão do mapa diário usa o mesmo documento térmico.

O navegador não pode, por segurança, escolher uma impressora específica nem
imprimir silenciosamente sem confirmação do usuário. O evento `afterprint`
também não informa se a pessoa confirmou ou cancelou a impressão. Portanto, o
frontend atual é adequado para operação assistida, mas não garante entrega
automática ao spooler.

### Integração necessária para impressão automática

Se a operação exigir envio direto e silencioso à EPSON, implementar um agente
local de impressão na máquina da cozinha:

- serviço Windows ou aplicativo local iniciado com o sistema;
- integração com o spooler do Windows ou envio ESC/POS suportado pela
  TM-T20X;
- configuração explícita do nome da impressora, largura de 80 mm, code page
  para português e acionamento do corte de papel;
- canal autenticado entre o backend e o agente local, sem expor uma porta
  irrestrita na rede;
- fila local persistente, retentativas, timeout e indicação de offline;
- idempotência por `order_id` e tipo de documento para evitar comandas
  duplicadas;
- retorno de estados `queued`, `printing`, `printed` e `failed`;
- registro em `labels_printed` somente após confirmação do spooler/agente;
- reimpressão auditada com usuário, data, motivo e contador de tentativas;
- teste presencial com driver oficial EPSON, acentos, QR/codebar quando
  aplicável, margem, densidade e corte.

Endpoints sugeridos:

```text
POST /api/v1/orders/{order_id}/print-jobs
GET  /api/v1/print-jobs/{print_job_id}
POST /api/v1/print-jobs/{print_job_id}/retry
```

O backend deve validar a role Kitchen/Admin, produzir o payload canônico da
comanda e nunca aceitar comandos ESC/POS arbitrários enviados pelo navegador.

## 12. Modo TV e atualização em tempo real

### Estado entregue no frontend

A rota `/cozinha/modo-tv` é uma visualização protegida pela role Kitchen,
sem controles de edição. Nesta etapa ela usa os pedidos mockados compartilhados
via `localStorage`. O relógio e o tempo em fila são atualizados no próprio
navegador; eventos de `storage` permitem apenas demonstração entre abas do
mesmo navegador.

Mapeamento visual provisório dos estados atuais:

| Estado atual | Modo TV |
| --- | --- |
| `pending` | Aguardando |
| `printed` | Em preparo |
| `separated` | Prontos |
| `delivered` | Removido do painel ativo |

Antes da integração, decidir se `printed` continuará representando o início da
produção ou se o domínio receberá estados explícitos como `in_preparation` e
`ready`. Impressão e andamento da produção são conceitos diferentes e não
devem permanecer acoplados caso a operação precise reimprimir uma comanda.

### Contrato de leitura

Disponibilizar um endpoint Kitchen somente leitura, otimizado para o dia e com
todos os campos necessários aos cards:

```text
GET /api/v1/kitchen/production-board?date=YYYY-MM-DD
```

Cada pedido deve fornecer identificador/número operacional, funcionário,
empresa, prato, tamanho, quantidade, observações, horário de entrada, estado e
instante da última mudança de estado.

### Sincronização

Implementar uma das estratégias abaixo:

1. WebSocket ou Server-Sent Events para eventos de criação e mudança de
   estado, com reconexão e busca de snapshot após perda de conexão.
2. Polling com `ETag`/`If-None-Match` a cada 10–30 segundos como fallback.

Requisitos adicionais:

- heartbeat e indicador de conexão na tela;
- ordenação estável pelo horário de entrada;
- horário calculado a partir do servidor para evitar relógios divergentes;
- remoção de pedidos entregues sem apagar o histórico;
- alerta visual/sonoro configurável para pedidos novos;
- limite de atraso configurável por ambiente;
- autenticação Kitchen reaproveitando a sessão atual;
- proteção contra exposição de CPF, telefone completo ou dados não necessários
  em uma TV visível;
- testes de reconexão, eventos duplicados, troca de estado concorrente e grande
  volume de pedidos.
