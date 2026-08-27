# Arquitetura e fluxo de funcionamento do Mavi Connect

Este documento descreve o estado atual da branch `feat/structure-backend`. Ele
explica a divisão do projeto, o papel de cada arquivo relevante, o `core` do
backend e o caminho percorrido por uma requisição desde o navegador até o
PostgreSQL.

Para uma leitura bloco por bloco de uma requisição real, consulte também
[`FLUXO_CORE_AUTH.md`](./FLUXO_CORE_AUTH.md).

> Importante: esta é uma fotografia do código atual. `auth`, `companies` e
> `menus` possuem fluxos HTTP implementados. `orders` está apenas parcialmente
> implementado, e `employees` e `kitchen` ainda contêm somente a estrutura de
> pacotes.

## 1. Visão geral

O sistema tem três processos principais:

```text
Navegador
   │ formulário, navegação e HTML
   ▼
Next.js 16
   │ HTTP/JSON; token enviado como Bearer
   ▼
FastAPI
   │ SQL parametrizado por psycopg
   ▼
PostgreSQL
```

- O **Next.js** renderiza a interface e funciona como cliente server-side da
  API. O token da sessão fica em um cookie HTTP-only do Next.js.
- O **FastAPI** é a fronteira real de segurança. Ele autentica, autoriza,
  valida entradas, executa os casos de uso e controla o acesso ao banco.
- O **PostgreSQL** guarda empresas, contas, sessões, pratos, cardápios, pedidos
  e registros de impressão.
- O **Supabase**, quando usado, é somente o provedor do PostgreSQL. O frontend
  não usa Supabase Auth, SDK, RLS ou acesso direto às tabelas.

O backend é um **monólito modular**. É um único processo FastAPI e um único
banco, mas o código é separado por áreas de negócio. Dentro de cada módulo é
aplicada uma variação de Clean Architecture:

```text
api ───────► application ───────► domain
 │                  │                ▲
 │                  └── usa ports ───┘
 └── monta adapters de infrastructure

infrastructure ─────► domain
```

As setas representam dependências de código. `domain` não conhece FastAPI nem
psycopg. `application` trabalha com entidades e interfaces (`Protocol`), não
com PostgreSQL diretamente. `api` monta os objetos concretos da
`infrastructure` e os entrega à aplicação.

## 2. Estrutura do repositório

```text
marmitex/
├── backend-python/       API FastAPI e testes unitários da API
├── frontend-next/        interface Next.js e testes do frontend
├── migrations/           fonte oficial do schema PostgreSQL
├── docs/                 decisões e documentação de arquitetura
├── docker-compose.yml    stack local: banco + API + frontend
├── .env.example          variáveis da stack Docker
├── README.md             instruções rápidas para executar o projeto
├── CONTRIBUTING.md       regras para contribuir
├── CLAUDE.md             contexto, escopo e regras de negócio do produto
├── AGENTS.md             instruções específicas para agentes de código
└── .gitignore            artefatos locais que não entram no Git
```

### Arquivos da raiz

| Arquivo | Responsabilidade |
|---|---|
| `.env.example` | Valores de exemplo usados pelo Docker Compose: credenciais locais do PostgreSQL, `DATABASE_URL` e origem da API. |
| `.gitignore` | Ignora dependências, builds, caches, arquivos `.env`, resultados de testes e ambientes virtuais; preserva os `.env.example`. |
| `AGENTS.md` | Alerta que a versão do Next.js pode ter mudanças incompatíveis e exige consulta à documentação instalada antes de alterar código Next.js. |
| `CLAUDE.md` | Fonte extensa de contexto funcional: papéis, escopo v1, regras invioláveis, dados e decisões do cliente. |
| `CONTRIBUTING.md` | Define separação das camadas, regras de log, fluxo de migrations e verificações obrigatórias. |
| `README.md` | Resume arquitetura, execução local, criação do primeiro admin e comandos de teste. |
| `docker-compose.yml` | Sobe PostgreSQL 17, FastAPI na porta 8000 e Next.js na porta 3000. |

## 3. Ciclo de vida da API

O ponto de entrada é `backend-python/app/main.py`.

Quando o Uvicorn importa `app.main:app`, o Python executa `app = create_app()`.
`create_app` faz o seguinte:

1. Chama `configure_logging()` para configurar o log padrão.
2. Obtém um `Settings` a partir do ambiente com `get_settings()`.
3. Cria `Database(settings)`, que configura um pool assíncrono.
4. Cria a instância `FastAPI` com um `lifespan`.
5. Guarda configuração e banco em `app.state`.
6. Registra CORS e o middleware de log.
7. Registra os três tratadores globais de erro.
8. Cria `GET /health`.
9. Inclui o roteador versionado definido em `app/api/router.py`.

O `lifespan` abre o pool de conexões antes de a API começar a receber tráfego e
o fecha durante o desligamento:

```text
início do processo → Database.open() → API pronta
desligamento       → Database.close() → processo termina
```

Esse desenho também facilita testes: `create_app` aceita `Settings` e
`Database` alternativos. `tests/test_health.py`, por exemplo, injeta um banco
falso e testa a rota sem abrir PostgreSQL.

## 4. O `core` completo

`backend-python/app/core/` contém recursos transversais. Ele não representa um
domínio de negócio; são peças compartilhadas por toda a API.

### `core/config.py`

Define `Settings`, baseada em `pydantic-settings`.

Campos:

- `app_name`: nome exibido no OpenAPI; padrão `Mavi Connect API`.
- `environment`: ambiente atual; padrão `development`.
- `database_url`: obrigatório.
- `session_ttl_hours`: duração da sessão; padrão de 168 horas, mínimo de 1 hora
  e máximo de 90 dias.
- `cors_origins`: origens autorizadas a fazer chamadas cross-origin.

O validador `validate_postgres_url` impede que a API seja iniciada com uma URL
que não comece por `postgresql://` ou `postgres://`.

`get_settings()` possui `@lru_cache`. Assim, no uso normal, as variáveis são
lidas e validadas uma vez por processo, e a mesma configuração é reutilizada.

### `core/database.py`

Encapsula `AsyncConnectionPool` do psycopg:

- `min_size=1`: mantém pelo menos uma conexão.
- `max_size=10`: permite até dez conexões simultâneas por processo da API.
- `open=False`: o pool não abre no construtor; quem controla isso é o
  `lifespan`.
- `row_factory=dict_row`: resultados SQL chegam como dicionários, por exemplo
  `row["email"]`, em vez de tuplas posicionais.

Métodos:

- `open()`: abre o pool e espera ele estar pronto.
- `close()`: encerra o pool.
- `healthcheck()`: pega uma conexão e executa `select 1`.

### `core/exceptions.py`

Define `ApplicationError`, o contrato comum de erro esperado:

```python
ApplicationError(code, message, status_code)
```

Os módulos especializam essa classe. Por exemplo, `UnauthorizedError` usa
status 401 e `CompanyConflictError` usa 409. `main.py` converte qualquer
`ApplicationError` no mesmo formato JSON:

```json
{
  "error": {
    "code": "email_already_exists",
    "message": "Já existe um acesso com esse e-mail."
  }
}
```

Isso evita que cada endpoint tenha seu próprio formato de erro.

### `core/logging.py`

`configure_logging()` configura nível `INFO` e um formato com data, nível,
logger e mensagem.

`request_log_middleware` envolve cada requisição:

1. gera um UUID como `request_id`;
2. marca o instante inicial;
3. chama o restante da aplicação;
4. identifica o padrão da rota, não a URL completa;
5. registra método, rota, status, duração e request ID;
6. devolve o ID no header `X-Request-ID`.

Usar o padrão da rota evita registrar query strings. Isso é importante porque
CPF, telefone, token e outros dados sensíveis não podem aparecer nos logs. O
teste `test_request_log_does_not_capture_query_string` protege essa garantia.

### `core/security.py`

Cria o esquema `HTTPBearer(auto_error=False)`. Com `auto_error=False`, a
ausência do header não gera automaticamente um erro genérico do FastAPI; o
módulo de autenticação pode devolver o erro padronizado do projeto.

`bearer_token(credentials)` só devolve o token quando o esquema é realmente
`Bearer`. Caso contrário, devolve `None`.

### `core/__init__.py`

Marca `core` como pacote Python. Atualmente não exporta símbolos.

## 5. Composição HTTP global

### `app/api/router.py`

Cria `api_router` com prefixo `/api/v1` e inclui os routers de:

- autenticação;
- empresas;
- cardápios/pratos;
- pedidos.

O router de pedidos está incluído, mas ainda não possui endpoints. Centralizar
os imports aqui transforma esse arquivo na raiz de composição HTTP: é fácil
ver quais módulos estão publicados pela API.

### `app/api/dependencies.py`

A dependência `connection(request)` recupera o `Database` de
`request.app.state`, pega uma conexão do pool e faz `yield` para o restante da
requisição.

`DatabaseConnection` é um alias com `Annotated` + `Depends`, permitindo que
outras funções declarem apenas:

```python
def algum_servico(connection: DatabaseConnection): ...
```

O FastAPI normalmente armazena dependências em cache durante a mesma
requisição. Assim, autenticação e serviço de negócio que dependam da mesma
função `connection` compartilham a conexão naquele request. Ao encerrar o
contexto sem erro, o psycopg confirma a transação pendente; em caso de exceção,
faz rollback antes de devolver a conexão ao pool.

### Tratamento de erros em `main.py`

| Origem | Resposta |
|---|---|
| `ApplicationError` | Status, código e mensagem definidos pelo domínio/aplicação. |
| `RequestValidationError` | 422 com `invalid_request` e mensagem pt-BR genérica. |
| `StarletteHTTPException` 404 | `not_found`. |
| `StarletteHTTPException` 405 | `method_not_allowed`. |
| outro HTTP error | `http_error`. |

Erros não previstos não são transformados por esses handlers e continuam sendo
falhas internas 500. Isso é desejável para não esconder bugs como se fossem
erros normais de negócio.

## 6. Como uma requisição percorre a aplicação

### 6.1 Fluxo geral de uma rota protegida

Exemplo: `GET /api/v1/companies`.

```text
Browser
  │ abre /admin/empresas
  ▼
Next.js Server Component (page.tsx)
  │ requireRole("admin")
  │ lê cookie HTTP-only mavi_session
  │ GET /api/v1/auth/me com Bearer
  ▼
FastAPI autentica a sessão no PostgreSQL
  │ devolve Account admin
  ▼
Next.js chama GET /api/v1/companies com o mesmo Bearer
  ▼
FastAPI
  ├─ valida o Bearer novamente
  ├─ exige AccountRole.ADMIN
  ├─ injeta CompanyApplicationService
  ├─ chama PostgresCompanyRepository.list()
  └─ serializa list[CompanyResponse]
  ▼
Next.js renderiza o HTML da lista
  ▼
Browser
```

Passo a passo dentro da segunda chamada ao FastAPI:

1. O middleware inicia tempo e request ID.
2. O router global encontra `/api/v1/companies`.
3. O FastAPI resolve `AdminAccount`.
4. `Credentials` lê o header `Authorization`.
5. `auth_service` monta `AuthApplicationService` com implementações concretas.
6. `current_account` extrai o token e chama `authenticate`.
7. A aplicação gera SHA-256 do token recebido.
8. O repositório procura uma sessão não revogada e não expirada.
9. `admin_account` confere se o papel é `admin`.
10. `company_service` monta o serviço de empresas.
11. O endpoint chama `service.list()`.
12. O repositório executa SQL e mapeia rows para entidades `Company`.
13. O Pydantic converte as entidades em `CompanyResponse`.
14. A conexão volta ao pool.
15. O middleware registra o resultado e adiciona `X-Request-ID`.

O `requireRole` do Next.js melhora navegação e experiência do usuário, mas não
é a autorização de segurança. Toda rota FastAPI protegida verifica o token e o
papel novamente.

### 6.2 Fluxo do login

1. `frontend-next/src/app/login/page.tsx` exibe o formulário no navegador.
2. O envio chama a Server Action `signIn` em `login/actions.ts`.
3. A action faz validação básica de presença de e-mail e senha.
4. `apiRequest` envia `POST /api/v1/auth/login` ao FastAPI.
5. `LoginRequest` valida formato do e-mail e tamanho da senha.
6. `auth_service` cria o serviço de aplicação com:
   - `PostgresAuthRepository`;
   - `ArgonPasswordService`;
   - `OpaqueSessionService`;
   - TTL vindo de `Settings`.
7. `AuthApplicationService.login` busca a conta pelo e-mail sem diferenciar
   maiúsculas e minúsculas.
8. O repositório também bloqueia, na prática, login de conta ligada a empresa
   inativa.
9. O Argon2 verifica a senha contra `password_hash`.
10. O serviço cria 32 bytes aleatórios codificados para URL como token opaco.
11. Calcula SHA-256 do token e persiste **somente o hash** em `sessions`.
12. A API devolve o token original uma única vez, com expiração e conta.
13. O Next.js grava o token no cookie `mavi_session`, com `httpOnly`,
   `sameSite=lax`, `path=/`, expiração e `secure` em produção.
14. A action redireciona para a página inicial correspondente ao papel.

O banco não guarda o token que o cliente usa. Se a tabela `sessions` vazar, os
hashes não podem ser usados diretamente como Bearer tokens.

### 6.3 Fluxo do logout

1. A Server Action lê o cookie.
2. Chama `POST /api/v1/auth/logout` com Bearer.
3. O serviço calcula o hash e preenche `revoked_at` na sessão ainda ativa.
4. Mesmo se a API estiver indisponível, o Next.js apaga o cookie local.
5. O usuário é redirecionado para `/login`.

Nesse caso de indisponibilidade, a sessão pode continuar válida no banco até a
expiração, mas o navegador que executou o logout deixa de possuir o token.

## 7. Módulo `auth`, arquivo por arquivo

Esse é o exemplo mais completo das quatro camadas e também sustenta todas as
rotas protegidas.

### Camada `domain`

#### `domain/entities.py`

- `AccountRole`: enum textual com `company`, `kitchen` e `admin`.
- `Account`: dataclass imutável com ID, nome, e-mail, empresa, papel e hash de
  senha opcional.

`password_hash` é necessário durante o login, mas não é selecionado quando a
conta é recuperada por sessão e não aparece nos schemas de resposta.

#### `domain/repositories.py`

Define três ports como `Protocol`:

- `AuthRepository`: busca contas e cria/revoga sessões.
- `PasswordService`: cria e verifica hashes de senha.
- `SessionService`: cria token opaco e calcula seu hash.

Essas interfaces permitem testar a aplicação com fakes, sem banco e sem
Argon2. `tests/test_auth_service.py` demonstra exatamente isso.

#### `domain/exceptions.py`

- `UnauthorizedError`: erro 401, normalmente `invalid_credentials`.
- `ForbiddenError`: erro 403 quando a conta existe, mas não tem o papel exigido.

### Camada `application`

#### `application/dto.py`

`LoginResult` agrega o token, a expiração e a entidade `Account`. É um contrato
de saída do caso de uso, independente de HTTP e Pydantic.

#### `application/services.py`

`AuthApplicationService` recebe todas as dependências pelo construtor.

- `login(email, password)` coordena busca, verificação de senha, geração do
  token, cálculo da expiração e persistência do hash.
- `authenticate(token)` calcula o hash e procura uma sessão válida.
- `logout(token)` calcula o hash e revoga a sessão correspondente.

O serviço não importa FastAPI, psycopg, Argon2 ou funções de aleatoriedade. Ele
depende apenas dos contratos do domínio.

### Camada `infrastructure`

#### `infrastructure/password.py`

`ArgonPasswordService` implementa hash e verificação com Argon2. Hash inválido
ou senha divergente vira `False`, evitando expor detalhes internos.

#### `infrastructure/session.py`

`OpaqueSessionService.create()` usa `secrets.token_urlsafe(32)`.
`hash()` usa SHA-256 e produz os 64 caracteres guardados em `sessions.token_hash`.

#### `infrastructure/repository.py`

`PostgresAuthRepository` recebe uma `AsyncConnection` e implementa o port:

- `account_by_email`: procura e-mail case-insensitive e só aceita conta sem
  empresa ou ligada a empresa ativa.
- `account_by_session_hash`: junta `sessions`, `accounts` e `companies`; exige
  sessão não revogada, ainda não expirada e empresa ativa.
- `create_session`: insere account ID, hash e expiração.
- `revoke_session`: preenche `revoked_at` somente se ainda estiver nulo.

Todas as entradas são parâmetros `%s`, não interpolação de strings, reduzindo
risco de SQL injection.

#### `infrastructure/models.py`

`account_from_row` é o mapper que converte o dicionário do psycopg em entidade
`Account` e converte o texto do banco para `AccountRole`.

### Camada `api`

#### `api/schemas.py`

- `LoginRequest`: e-mail válido e senha de 1 a 256 caracteres.
- `AccountResponse`: representação pública da conta, sem hash de senha.
- `LoginResponse`: token, expiração e conta.

`from_attributes=True` permite que o Pydantic serialize dataclasses do domínio.

#### `api/dependencies.py`

É a composição do módulo:

- `auth_service` liga os ports às implementações reais.
- `CurrentAccount` autentica qualquer conta com Bearer válido.
- `AdminAccount` reutiliza `CurrentAccount` e exige papel `admin`.
- `Credentials` representa o resultado opcional do esquema HTTP Bearer.

Para criar no futuro `KitchenAccount`, o padrão natural é uma dependência que
recebe `CurrentAccount` e verifica `AccountRole.KITCHEN` ou uma combinação de
papéis permitidos.

#### `api/router.py`

Publica:

- `POST /auth/login`;
- `GET /auth/me`;
- `POST /auth/logout`.

O prefixo `/api/v1` vem do router global; portanto, as URLs finais são
`/api/v1/auth/...`.

## 8. Módulo `companies`, arquivo por arquivo

Esse módulo mostra bem um fluxo de escrita transacional envolvendo duas
tabelas.

### `domain/entities.py`

`Company` é uma dataclass imutável com dados da empresa e `access_email`. O
e-mail vem da conta compartilhada de papel `company`, não da tabela
`companies`.

### `domain/repositories.py`

- `CompanyRepository` declara `list` e `create`.
- `PasswordHasher` declara apenas `hash`, que é tudo que esse módulo precisa.

Esse port menor segue segregação de interface: empresas não precisam conhecer
o método de verificação de senha.

### `domain/exceptions.py`

- `DuplicateCompanyEmailError` é um erro interno de persistência, sem status
  HTTP.
- `CompanyConflictError` é o erro de aplicação público, com código
  `email_already_exists` e status 409.

### `application/services.py`

- `list()` delega a listagem ao repositório.
- `create()` normaliza o e-mail para minúsculas, gera o hash da senha e chama o
  repositório. Um conflito técnico de unicidade é traduzido em erro de negócio
  estável.

Assim, a API não fica acoplada a `psycopg.errors.UniqueViolation`.

### `infrastructure/repository.py`

`list()` junta `companies` e `accounts` para devolver também o e-mail de acesso.

`create()` abre uma transação explícita e executa duas inserções:

```text
INSERT companies
       │ retorna company.id
       ▼
INSERT accounts com role='company' e o mesmo company.id
```

Se a segunda inserção falhar, a primeira também é revertida. Isso impede a
criação de uma empresa sem sua credencial compartilhada. Uma violação de
unicidade é convertida em `DuplicateCompanyEmailError`.

### `infrastructure/models.py`

`company_from_row` converte row em `Company`. Na criação, o e-mail já está na
memória e é passado separadamente; na listagem, ele vem como `access_email` no
resultado do JOIN.

### `api/dependencies.py`

Monta `CompanyApplicationService` com `PostgresCompanyRepository` e reutiliza
`ArgonPasswordService` do módulo de autenticação.

### `api/schemas.py`

- `CompanyCreate`: nome obrigatório, e-mail válido e senha com no mínimo oito
  caracteres.
- `CompanyResponse`: ID, nome, estado ativo, criação e e-mail de acesso.

### `api/router.py`

Publica `GET /companies` e `POST /companies`. Os dois exigem `AdminAccount`.
O endpoint POST remove espaços nas pontas do nome e devolve status 201.

## 9. Módulo `menus`

### `domain`

- `entities.py`: define `MenuItem` e `Menu` como dataclasses imutáveis.
- `repositories.py`: port para listar/criar pratos, consultar intervalo, salvar
  semana e publicar datas.
- `exceptions.py`: `EmptyMenuError` retorna 422 quando nenhuma data preenchida
  pode ser publicada.

### `application/services.py`

`MenuApplicationService` coordena os cinco casos de uso. A regra adicional está
em `publish`: se o repositório atualizar zero cardápios, lança `EmptyMenuError`.

### `infrastructure`

- `models.py`: usa `Menu(**row)` e `MenuItem(**row)` porque nomes das colunas e
  campos das entidades coincidem.
- `repository.py`: contém SQL de pratos e cardápios.
- `save_week` faz upsert por data dentro de uma transação. Se a seleção de
  pratos mudou, `published` volta para `false`; se não mudou, preserva o estado.
- `publish` só publica linhas cuja lista `menu_item_ids` não esteja vazia e
  devolve `rowcount`.

### `api`

- `dependencies.py`: monta serviço e repositório.
- `schemas.py`: valida tamanhos literais `P`, `M`, `G`, preço não negativo,
  listas de 1 a 7 dias e contratos de resposta.
- `router.py`: publica as rotas de pratos e cardápios, todas restritas a admin
  no estado atual.

## 10. Módulos ainda incompletos

### `orders`

O módulo já tem parte do domínio e persistência, mas ainda não entrega um caso
de uso HTTP:

| Arquivo | Estado atual |
|---|---|
| `api/router.py` | Cria router `/orders`, sem endpoints. |
| `api/schemas.py` | Apenas docstring reservando os contratos HTTP. |
| `application/create_order.py` | Apenas documentação da fronteira futura. |
| `application/cancel_order.py` | Apenas documentação; cancelamento está fora da v1 atual. |
| `application/services.py` | Apenas docstring. |
| `domain/entities.py` | Define `ProductionStatus` e a entidade `Order`. |
| `domain/exceptions.py` | Declara a base `OrderDomainError`. |
| `domain/repositories.py` | Declara somente `by_id`. |
| `domain/rules.py` | Define tamanhos válidos e normalização de CPF para dígitos. |
| `infrastructure/models.py` | Converte row em `Order`. |
| `infrastructure/repository.py` | Implementa apenas busca de pedido por ID. |

Consequência prática: embora existam tabela `orders`, router incluído e algumas
classes, nenhuma requisição de criação, listagem, produção ou impressão de
pedido está disponível nesta branch.

### `employees`

Contém apenas `__init__.py` em `api`, `application`, `domain` e
`infrastructure`. Não possui código funcional nem endpoints. Além disso, o
produto v1 não prevê conta individual de colaborador; os dados do colaborador
pertencem ao pedido.

### `kitchen`

Também contém apenas a estrutura de pacotes. Ainda não existem endpoints para
painel da cozinha, agrupamento por empresa, status de produção ou impressão.

### Arquivos `__init__.py`

Os `__init__.py` espalhados por `app`, `api`, `cli`, `modules` e subpastas
marcam diretórios como pacotes Python. Nesta branch eles estão vazios e não
adicionam comportamento.

## 11. Rotas HTTP disponíveis atualmente

Todas as rotas de negócio recebem o prefixo `/api/v1`.

| Método e rota | Autorização | Função |
|---|---|---|
| `GET /health` | pública | Confere API e banco. |
| `POST /api/v1/auth/login` | pública | Cria sessão e devolve token opaco. |
| `GET /api/v1/auth/me` | Bearer válido | Devolve a conta atual. |
| `POST /api/v1/auth/logout` | Bearer válido | Revoga a sessão; resposta 204. |
| `GET /api/v1/companies` | admin | Lista empresas e acessos. |
| `POST /api/v1/companies` | admin | Cria empresa e credencial; resposta 201. |
| `GET /api/v1/menu-items` | admin | Lista pratos. |
| `POST /api/v1/menu-items` | admin | Cria prato; resposta 201. |
| `GET /api/v1/menus?start=...&end=...` | admin | Lista cardápios no intervalo. |
| `PUT /api/v1/menus/week` | admin | Salva/upserta os dias; resposta 204. |
| `POST /api/v1/menus/week/publish` | admin | Publica dias preenchidos; resposta 204. |

Não há endpoint `/orders` funcional apesar de o prefixo estar registrado.

### Exemplos de requisição direta à API

Login:

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@mavi.local",
  "password": "senha-do-admin"
}
```

Resposta resumida:

```json
{
  "token": "token-opaco-devolvido-uma-vez",
  "expires_at": "2026-09-02T12:00:00Z",
  "account": {
    "id": "00000000-0000-0000-0000-000000000000",
    "name": "Admin Mavi",
    "email": "admin@mavi.local",
    "company_id": null,
    "role": "admin"
  }
}
```

Chamada protegida:

```http
GET /api/v1/companies HTTP/1.1
Authorization: Bearer token-opaco-devolvido-uma-vez
Accept: application/json
```

Criação de prato:

```http
POST /api/v1/menu-items HTTP/1.1
Authorization: Bearer token-opaco-devolvido-uma-vez
Content-Type: application/json

{
  "name": "Frango grelhado",
  "description": "Arroz, feijão e salada",
  "size_options": ["P", "M", "G"],
  "price": 22.90
}
```

## 12. Banco de dados e migration

`migrations/0001_initial.sql` é a fonte oficial do schema. O Docker monta a
pasta em `/docker-entrypoint-initdb.d`, então a migration inicial roda ao criar
um volume PostgreSQL vazio.

### Tipos enum

- `account_role`: `company`, `kitchen`, `admin`.
- `production_status`: `pending`, `printed`, `separated`, `delivered`.
- `payment_status`: atualmente apenas `not_applicable`.

### Tabelas

#### `companies`

Empresa cliente, com UUID, nome, indicador `active` e criação.

#### `accounts`

Credenciais compartilhadas ou internas. E-mail é único e senha é sempre hash.
A constraint exige:

- conta `company` com `company_id`;
- conta `kitchen` ou `admin` sem `company_id`.

#### `menu_items`

Pratos com descrição, tamanhos em array e preço opcional. Constraints impedem
lista vazia, tamanho fora de `P/M/G` e preço negativo.

#### `menus`

Uma linha por data, com array de IDs dos pratos e flag `published`.

#### `orders`

Guarda empresa, data, prato, tamanho e identificação preenchida pelo
colaborador. A constraint `unique (employee_cpf, date)` garante uma marmita por
CPF por dia. CPF precisa conter exatamente 11 dígitos.

#### `labels_printed`

Registra cada impressão e apaga os registros associados se o pedido for
apagado.

#### `sessions`

Guarda hash SHA-256 do token, conta, expiração, revogação e criação. O índice
parcial acelera consultas de sessões não revogadas.

As foreign keys de empresa usam `on delete restrict`, protegendo histórico
contra remoção acidental. Sessões usam cascade ao apagar uma conta.

## 13. Como o Next.js conversa com a API

O frontend atual usa um desenho semelhante a um BFF: a origem interna da API e
o token ficam no lado servidor do Next.js.

### `src/lib/env.ts`

- Exige `API_URL` no servidor e remove `/` final.
- Expõe funções para horário de corte e fuso.
- Nada usa prefixo `NEXT_PUBLIC_`, portanto esses valores não são empacotados
  intencionalmente para o navegador.

### `src/lib/api/client.ts`

`apiRequest<T>` é o único cliente central da API:

- monta URL a partir de `API_URL`;
- adiciona `Accept: application/json`;
- adiciona `Content-Type` quando há corpo;
- adiciona Bearer quando recebe `token`;
- usa `no-store` por padrão;
- aplica timeout de dez segundos;
- converte falha de rede em `ApiError(503)`;
- entende o formato padronizado `{ error: { code, message } }`;
- trata 204 sem tentar ler JSON.

### `src/lib/session.ts`

Lê, grava e apaga o cookie HTTP-only `mavi_session`. Como ele é HTTP-only, o
JavaScript executado no navegador não consegue ler seu valor.

### `src/lib/auth.ts`

- `currentAccount` lê o cookie e chama `/auth/me`.
- 401 vira `null`; outras falhas continuam sendo erro.
- `homePathFor` escolhe o destino por papel. No momento, apenas admin possui
  área pronta; outros papéis retornam ao login.
- `requireRole` protege páginas server-side e redireciona acessos inválidos.

### Páginas e Server Actions

Os `page.tsx` de admin são Server Components: buscam dados na API antes de
renderizar. Os formulários são Client Components porque usam `useActionState`.
Ao enviar, eles chamam funções com `"use server"`:

```text
Client Component form.tsx
        │ FormData
        ▼
Server Action actions.ts
        │ valida e chama apiRequest
        ▼
FastAPI
        │ sucesso
        ▼
revalidatePath
        │ nova renderização server-side
        ▼
HTML atualizado no navegador
```

O token não precisa ser colocado no estado React nem devolvido ao código client.

## 14. Frontend, arquivo por arquivo

### Configuração

| Arquivo | Responsabilidade |
|---|---|
| `frontend-next/package.json` | Dependências e scripts de dev, build, lint, typecheck, Vitest e Playwright. |
| `package-lock.json` | Lockfile gerado pelo npm para instalações reproduzíveis. |
| `next.config.ts` | Gera build standalone e define a raiz do Turbopack. |
| `tsconfig.json` | TypeScript estrito, sem emissão e alias `@/*`. |
| `eslint.config.mjs` | ESLint com Core Web Vitals e TypeScript. |
| `postcss.config.mjs` | Integra Tailwind CSS 4 ao PostCSS. |
| `vitest.config.mts` | Testes Node para `src/**/*.test.ts` e alias `@`. |
| `playwright.config.ts` | E2E serial em Chromium, servidor Next local e configuração de CI. |
| `.env.example` | `API_URL`, corte e fuso, todos server-side. |
| `Dockerfile` | Build multi-stage e execução do servidor standalone. |

### `src/app`

| Arquivo | Responsabilidade |
|---|---|
| `layout.tsx` | HTML raiz, idioma pt-BR, metadata e CSS global. |
| `globals.css` | Importa Tailwind e define a família de fontes. |
| `page.tsx` | Consulta a sessão e redireciona para home do papel ou login. |
| `login/page.tsx` | Formulário client-side de login. |
| `login/actions.ts` | Login, persistência do cookie, logout e redirecionamentos. |
| `admin/layout.tsx` | Exige admin, cria navegação e formulário de logout. |
| `admin/empresas/page.tsx` | Busca e lista empresas. |
| `admin/empresas/form.tsx` | Formulário client-side e mensagens de estado. |
| `admin/empresas/actions.ts` | Valida FormData, cria empresa e revalida a página. |
| `admin/pratos/page.tsx` | Busca e lista pratos. |
| `admin/pratos/form.tsx` | Formulário de prato, preço, descrição e tamanhos. |
| `admin/pratos/actions.ts` | Normaliza dados e chama POST de pratos. |
| `admin/cardapio/page.tsx` | Calcula semana, busca pratos e menus em paralelo. |
| `admin/cardapio/form.tsx` | Checkboxes por dia, ações de salvar e publicar. |
| `admin/cardapio/actions.ts` | Monta payload semanal, salva/publica e revalida. |

### `src/lib`

| Arquivo | Responsabilidade |
|---|---|
| `api/client.ts` | Cliente HTTP server-side central. |
| `auth.ts` | Sessão atual, destino por papel e guarda de páginas. |
| `env.ts` | Leitura de configuração. |
| `session.ts` | Cookie HTTP-only. |
| `types.ts` | Espelho TypeScript dos contratos públicos da API. |
| `week.ts` | Cálculos de data sem deslocamento de fuso e labels pt-BR. |
| `week.test.ts` | Testa viradas de data, dias úteis, domingo, fuso e labels. |

### `e2e`

- `critical-path.spec.ts`: atualmente cobre a fatia administrativa: login,
  empresa, prato, montagem e publicação da semana.
- `support.ts`: massa de teste e helpers de login/logout.
- `global-setup.ts`: exige explicitamente uma stack isolada já migrada.

O comentário do teste diz que o caminho crítico crescerá por fatias. Hoje ele
ainda não testa colaborador pedindo, painel da cozinha ou etiqueta, pois essas
fatias não estão implementadas.

## 15. Backend, demais arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend-python/pyproject.toml` | Metadados Python 3.12, dependências, extras de dev, pytest e Ruff. |
| `backend-python/Dockerfile` | Instala o pacote e inicia Uvicorn na porta 8000. |
| `backend-python/.env.example` | URL do banco, TTL de sessão e CORS. |
| `app/main.py` | Application factory, lifespan, middlewares, erros, health e routers. |
| `app/cli/create_admin.py` | CLI que pede senha sem eco, aplica Argon2 e insere a primeira conta admin. |
| `tests/conftest.py` | Define uma URL PostgreSQL falsa para importação segura nos testes. |
| `tests/test_auth_service.py` | Testa ports/fakes, senha inválida e persistência apenas do hash do token. |
| `tests/test_health.py` | Testa health 200/503 e privacidade do log. |
| `tests/test_routes.py` | Confere no OpenAPI que os contratos principais estão publicados. |
| `tests/test_security.py` | Testa Argon2 e estabilidade/não exposição do hash da sessão. |
| `mavi_connect_api.egg-info/*` | Metadados gerados pela instalação/build do pacote; não contêm regra de negócio. |

## 16. Infraestrutura local com Docker

`docker-compose.yml` define:

1. `database`: PostgreSQL 17, volume persistente, migration inicial e
   healthcheck.
2. `api`: build de `backend-python`, URL interna
   `postgresql://...@database:5432/...`, porta 8000 e espera banco saudável.
3. `frontend`: build de `frontend-next`, chama a API pelo hostname Docker
   `http://api:8000`, porta 3000 e depende da API.

Os hostnames `database` e `api` funcionam dentro da rede do Compose. Fora do
Docker, os exemplos usam `localhost`.

## 17. O que está protegido em cada camada

```text
Browser/HTML
  valida required, tipos de input e mostra feedback
        │
Next.js Server Action
  valida presença/formato simples e protege navegação
        │
FastAPI schema
  valida o contrato HTTP de forma autoritativa
        │
Application/domain
  aplica regras do caso de uso
        │
PostgreSQL
  garante unicidade, referências, enums e checks
```

As validações são complementares. Nunca se deve remover a validação da API ou
do banco só porque o formulário já impede determinado valor.

## 18. Limites e pontos de atenção do estado atual

1. **A v1 funcional ainda está incompleta.** Não existem criação de pedidos,
   menu publicado para empresa, painel de cozinha ou etiquetas.
2. **`ORDER_CUTOFF_TIME` e `APP_TIME_ZONE` existem apenas no frontend atual.**
   Como pedidos ainda não foram implementados, a regra de corte ainda não é
   aplicada autoritativamente pelo FastAPI. Ao implementar pedidos, o backend
   também deverá receber e validar essa regra; frontend não é fronteira de
   segurança.
3. **Somente admin tem home pronta.** `company` e `kitchen` autenticam no
   backend, mas `homePathFor` os redireciona para `/login`.
4. **As rotas de menu são somente de admin.** Ainda falta uma consulta
   protegida para empresa que exponha apenas menus publicados.
5. **Os tipos TypeScript são espelhos manuais.** O backend continua sendo a
   fonte da verdade; mudanças de schema precisam atualizar `types.ts` e testes.
6. **A migration inicial só roda automaticamente em volume novo do Docker.**
   Alterar `0001_initial.sql` não modifica sozinho um volume já existente.
7. **CORS está configurado**, mas o fluxo normal atual é Next.js servidor para
   FastAPI. CORS passa a importar diretamente se código executado no navegador
   chamar a API em outra origem.

## 19. Padrão para implementar uma nova fatia

Para completar, por exemplo, `create order`, a ordem coerente com a arquitetura
atual é:

1. definir/ajustar entidade, regras e exceções em `orders/domain`;
2. ampliar o `OrderRepository` como port;
3. escrever o caso de uso em `orders/application` usando apenas ports;
4. testar o caso de uso com repositório e relógio falsos;
5. implementar SQL e mappers em `orders/infrastructure`;
6. criar schemas e dependências em `orders/api`;
7. publicar o endpoint no router com autenticação/autorização;
8. criar Server Component/Action no Next.js usando `apiRequest`;
9. adicionar teste de integração/E2E à fatia crítica.

Para a regra de corte, é importante injetar uma abstração de relógio e usar o
fuso configurado. Isso permite testar exatamente antes/depois das 10:00,
viradas de dia e fim de semana sem depender do relógio real da máquina.

## 20. Resumo mental

Ao ler qualquer funcionalidade, siga esta sequência:

```text
router/schema
    ↓ entrada HTTP validada
dependency
    ↓ objetos concretos montados
application service/use case
    ↓ regra e orquestração
domain entity + repository Protocol
    ↓ contrato
infrastructure repository/mapper
    ↓ SQL
PostgreSQL
```

Na volta, o row do banco vira entidade, a entidade vira schema Pydantic, o
FastAPI produz JSON, `apiRequest` converte o JSON em tipo TypeScript e o Next.js
renderiza a interface.
