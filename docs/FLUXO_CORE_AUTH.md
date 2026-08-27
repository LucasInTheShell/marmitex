# Fluxo do `core` até o módulo `auth`

Este guia acompanha duas requisições reais do projeto:

1. `POST /api/v1/auth/login`, que cria uma sessão;
2. `GET /api/v1/auth/me`, que usa essa sessão para autenticar uma conta.

O objetivo é mostrar em qual ordem os arquivos são executados e o que cada
bloco de código faz.

## 1. Mapa do fluxo

```text
Uvicorn importa app.main:app
        │
        ▼
core/config.py ── lê e valida as variáveis
        │
        ▼
core/database.py ── configura e abre o pool PostgreSQL
        │
        ▼
main.py ── monta FastAPI, middleware, erros e routers
        │
        ▼
api/router.py ── adiciona /api/v1 e inclui auth
        │
        ▼
auth/api/router.py ── encontra /auth/login ou /auth/me
        │
        ▼
auth/api/dependencies.py ── monta as dependências concretas
        │
        ▼
auth/application/services.py ── executa o caso de uso
        │
        ├──► auth/domain ── entidades, erros e contratos
        │
        └──► auth/infrastructure ── Argon2, token e PostgreSQL
        │
        ▼
Schema Pydantic ── serializa a resposta
        │
        ▼
Middleware registra o resultado e adiciona X-Request-ID
```

## 2. Antes da primeira requisição: inicialização

### 2.1 O Uvicorn importa `app.main:app`

O Dockerfile inicia o backend com:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`app.main:app` significa:

- importe o módulo Python `app/main.py`;
- encontre nele o objeto chamado `app`;
- use esse objeto como aplicação ASGI.

No final de `main.py` existe:

```python
app = create_app()
```

Portanto, a montagem da aplicação começa em `create_app`.

## 3. `core/config.py`: configuração

O objeto central é:

```python
class Settings(BaseSettings):
```

Herdar de `BaseSettings` faz o Pydantic obter valores das variáveis de ambiente
e do arquivo `.env`.

```python
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)
```

- `env_file`: procura um `.env` no diretório de execução.
- `env_file_encoding`: lê o arquivo como UTF-8.
- `extra="ignore"`: variáveis adicionais não quebram a inicialização.

Os campos relevantes para autenticação e banco são:

```python
database_url: str
session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
cors_origins: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

- `database_url` não tem padrão: é obrigatório.
- `session_ttl_hours` define por quantas horas um login permanece válido.
- `ge=1` e `le=24 * 90` limitam a duração entre uma hora e 90 dias.
- `cors_origins` define quais origens de navegador podem chamar a API.

O validador:

```python
@field_validator("database_url")
@classmethod
def validate_postgres_url(cls, value: str) -> str:
    if not value.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
    return value
```

impede que a aplicação inicie com uma URL que não seja PostgreSQL.

Por fim:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`@lru_cache` guarda a instância retornada. Chamadas posteriores reutilizam a
mesma configuração em vez de reler o ambiente.

## 4. `core/database.py`: pool de conexões

`main.py` entrega o `Settings` para:

```python
app_database = database or Database(app_settings)
```

O construtor de `Database` cria:

```python
self.pool = AsyncConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
)
```

- `conninfo`: endereço do PostgreSQL.
- `min_size=1`: mantém no mínimo uma conexão.
- `max_size=10`: permite até dez conexões simultâneas.
- `open=False`: apenas configura; ainda não conecta.
- `dict_row`: cada linha SQL vira dicionário.

Exemplo do formato produzido por `dict_row`:

```python
{
    "id": UUID(...),
    "email": "admin@mavi.local",
    "role": "admin",
}
```

Sem ele, o código teria que acessar valores por posição, como `row[0]`.

## 5. `main.py`: montagem da aplicação

### 5.1 Lifespan

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await app_database.open()
    try:
        yield
    finally:
        await app_database.close()
```

Antes do `yield`, a API abre o pool. Durante o `yield`, ela recebe requisições.
No desligamento, o `finally` fecha o pool mesmo que tenha ocorrido uma falha.

```text
open() → aplicação atendendo → close()
```

### 5.2 Estado compartilhado

```python
app.state.settings = app_settings
app.state.database = app_database
```

Esses objetos ficam disponíveis em qualquer requisição por meio de
`request.app.state`. Isso será usado pelas dependências de banco e autenticação.

### 5.3 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

O middleware permite as origens configuradas, credenciais, os métodos usados
pelo projeto e os headers necessários para JSON e Bearer token.

### 5.4 Middleware de log

```python
app.middleware("http")(request_log_middleware)
```

Essa linha registra a função de `core/logging.py` ao redor de toda requisição.

### 5.5 Routers

```python
app.include_router(api_router)
```

Essa linha conecta as rotas de negócio à aplicação principal.

## 6. `core/logging.py`: entrada e saída da requisição

Quando `POST /api/v1/auth/login` chega, este middleware envolve o processamento:

```python
async def request_log_middleware(request: Request, call_next):
    request_id = str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
```

- gera um ID único;
- marca o tempo inicial;
- entrega a requisição ao FastAPI por `call_next`;
- aguarda router, dependências e caso de uso terminarem.

Na volta:

```python
route = request.scope.get("route")
route_pattern = getattr(route, "path", "unmatched")
```

O código obtém o padrão da rota, como `/api/v1/auth/login`, e não a URL com
query string. Isso evita colocar dados enviados na URL dentro do log.

Depois registra:

```python
logger.info(
    "request_complete method=%s route=%s status=%s duration_ms=%s request_id=%s",
    request.method,
    route_pattern,
    response.status_code,
    round((time.perf_counter() - started) * 1000),
    request_id,
)
```

e devolve o mesmo identificador ao cliente:

```python
response.headers["X-Request-ID"] = request_id
```

## 7. `app/api/router.py`: descoberta da rota

O router global é:

```python
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
```

O módulo `auth` define seu próprio prefixo como `/auth`. A soma dos prefixos
gera:

```text
/api/v1 + /auth + /login = /api/v1/auth/login
```

Essa composição permite versionar todas as rotas de negócio em um só lugar.

## 8. `auth/api/schemas.py`: validação do JSON

O endpoint espera:

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
```

Para este corpo:

```json
{
  "email": "admin@mavi.local",
  "password": "minha-senha"
}
```

o Pydantic:

- confirma que `email` tem formato de e-mail;
- confirma que a senha não está vazia;
- impede uma senha com mais de 256 caracteres;
- cria um objeto `LoginRequest`.

Se a validação falhar, o endpoint nem começa a executar.

## 9. `app/api/dependencies.py`: conexão por requisição

Antes de montar o serviço de autenticação, o FastAPI resolve:

```python
async def connection(request: Request) -> AsyncIterator[AsyncConnection]:
    database: Database = request.app.state.database
    async with database.pool.connection() as database_connection:
        yield database_connection
```

Passos:

1. recupera o `Database` salvo por `main.py`;
2. empresta uma conexão do pool;
3. entrega a conexão às dependências da requisição;
4. ao final, confirma ou reverte a transação conforme o resultado;
5. devolve a conexão ao pool.

O alias:

```python
DatabaseConnection = Annotated[AsyncConnection, Depends(connection)]
```

faz o FastAPI entender que um parâmetro desse tipo deve ser injetado.

## 10. `auth/api/dependencies.py`: montagem do módulo

O login declara `service: AuthServiceDependency`. Esse alias aponta para:

```python
def auth_service(
    request: Request,
    connection: DatabaseConnection,
) -> AuthApplicationService:
    return AuthApplicationService(
        PostgresAuthRepository(connection),
        ArgonPasswordService(),
        OpaqueSessionService(),
        request.app.state.settings.session_ttl_hours,
    )
```

Essa função é a composição concreta do módulo:

| Objeto | Função |
|---|---|
| `PostgresAuthRepository` | Lê contas e grava sessões no PostgreSQL. |
| `ArgonPasswordService` | Verifica o hash da senha. |
| `OpaqueSessionService` | Gera o token e seu hash SHA-256. |
| `session_ttl_hours` | Define o vencimento da sessão. |

O serviço de aplicação recebe tudo pelo construtor. Ele não cria essas
dependências por conta própria.

O alias final é:

```python
AuthServiceDependency = Annotated[
    AuthApplicationService,
    Depends(auth_service),
]
```

## 11. `auth/api/router.py`: início do endpoint

O endpoint é:

```python
@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, service: AuthServiceDependency):
    result = await service.login(str(payload.email), payload.password)
```

Neste ponto:

- `payload` já foi validado pelo Pydantic;
- `service` já foi montado pelo sistema de dependências;
- a conexão já foi emprestada do pool;
- o router apenas converte entrada HTTP e chama o caso de uso.

Essa camada não contém SQL, Argon2 ou cálculo da sessão.

## 12. `auth/application/services.py`: caso de uso de login

O método começa buscando a conta:

```python
account = await self.repository.account_by_email(email)
if not account or not account.password_hash:
    raise UnauthorizedError()
```

Ele usa `self.repository`, que para produção é um
`PostgresAuthRepository`. Porém, a aplicação conhece somente o contrato
`AuthRepository`.

Conta inexistente e conta sem hash devolvem o mesmo erro. Isso evita revelar se
determinado e-mail está cadastrado.

Depois verifica a senha:

```python
if not self.passwords.verify(account.password_hash, password):
    raise UnauthorizedError()
```

Senha incorreta também produz a mesma resposta genérica.

Com credenciais válidas:

```python
token = self.sessions.create()
expires_at = datetime.now(UTC) + timedelta(hours=self.session_ttl_hours)
```

- cria um token aleatório;
- calcula a expiração em UTC.

Então persiste:

```python
await self.repository.create_session(
    account.id,
    self.sessions.hash(token),
    expires_at,
)
```

O detalhe mais importante é que `token` não é enviado ao repositório. O banco
recebe somente `self.sessions.hash(token)`.

Por fim:

```python
return LoginResult(
    token=token,
    expires_at=expires_at,
    account=account,
)
```

`LoginResult` é um DTO da aplicação, não uma resposta HTTP.

## 13. `auth/domain/repositories.py`: os contratos

O serviço pode usar `self.repository` porque o domínio define:

```python
class AuthRepository(Protocol):
    async def account_by_email(self, email: str) -> Account | None: ...

    async def create_session(
        self,
        account_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> None: ...
```

`Protocol` funciona como uma interface estrutural. Qualquer classe com esses
métodos e assinaturas pode ser usada, sem precisar herdar explicitamente de
`AuthRepository`.

O mesmo vale para:

```python
class PasswordService(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...


class SessionService(Protocol):
    def create(self) -> str: ...
    def hash(self, token: str) -> str: ...
```

Por isso o teste consegue substituir PostgreSQL, Argon2 e tokens reais por
classes fake.

## 14. `auth/infrastructure/repository.py`: busca da conta

O adapter concreto executa:

```sql
select a.id, a.name, a.email, a.company_id, a.role, a.password_hash
from accounts a
left join companies c on c.id = a.company_id
where lower(a.email) = lower(%s)
  and (a.company_id is null or c.active)
```

O parâmetro é enviado separadamente:

```python
(email,)
```

Isso evita concatenar entrada do usuário no SQL.

A query:

- encontra e-mail ignorando maiúsculas/minúsculas;
- aceita admin/cozinha, que não têm empresa;
- aceita conta de empresa somente quando a empresa está ativa;
- seleciona `password_hash` porque o login precisa verificá-lo.

Depois:

```python
row = await result.fetchone()
return account_from_row(row) if row else None
```

Sem resultado, retorna `None`. Com resultado, chama o mapper.

## 15. `auth/infrastructure/models.py`: row para entidade

O mapper contém:

```python
def account_from_row(row: dict) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        company_id=row["company_id"],
        role=AccountRole(row["role"]),
        password_hash=row.get("password_hash"),
    )
```

Ele isola a conversão do formato de persistência para o formato de domínio.
`AccountRole(row["role"])` transforma a string PostgreSQL em enum Python.

O resultado é a entidade definida em `auth/domain/entities.py`:

```python
@dataclass(frozen=True, slots=True)
class Account:
```

- `dataclass` gera inicialização e comparação.
- `frozen=True` impede alterações depois da criação.
- `slots=True` restringe os atributos aos campos declarados.

## 16. `auth/infrastructure/password.py`: verificação Argon2

O adapter possui uma instância de:

```python
self._hasher = PasswordHasher()
```

Durante o login:

```python
return self._hasher.verify(password_hash, password)
```

O Argon2 recebe primeiro o hash do banco e depois a senha informada. Se a senha
não corresponder ou o hash estiver corrompido:

```python
except (InvalidHashError, VerifyMismatchError):
    return False
```

O caso de uso recebe apenas `True` ou `False`; detalhes da biblioteca não
vazam para `application`.

## 17. `auth/infrastructure/session.py`: token opaco

A criação usa:

```python
secrets.token_urlsafe(32)
```

`secrets` é apropriado para valores de segurança. O resultado é aleatório e
pode ser transportado em HTTP.

O hash usa:

```python
hashlib.sha256(token.encode("utf-8")).hexdigest()
```

Isso produz uma string hexadecimal de 64 caracteres, compatível com
`sessions.token_hash char(64)`.

Token e hash têm papéis diferentes:

```text
token original → devolvido ao cliente e usado como Bearer
hash do token  → armazenado e pesquisado no PostgreSQL
```

## 18. `auth/infrastructure/repository.py`: gravação da sessão

O repositório executa:

```python
await self.connection.execute(
    "insert into sessions "
    "(account_id, token_hash, expires_at) values (%s, %s, %s)",
    (account_id, token_hash, expires_at),
)
```

Quando o endpoint termina sem erro, o contexto da conexão confirma a transação.
Se uma exceção interromper a requisição, a transação é revertida.

## 19. Retorno do login

De volta ao router:

```python
return LoginResponse(
    token=result.token,
    expires_at=result.expires_at,
    account=AccountResponse.model_validate(result.account),
)
```

- converte o DTO da aplicação para contrato HTTP;
- converte a entidade `Account` em `AccountResponse`;
- não inclui `password_hash` porque esse campo não existe no schema público.

O JSON resultante tem:

```json
{
  "token": "token-original",
  "expires_at": "2026-09-02T15:00:00Z",
  "account": {
    "id": "uuid",
    "name": "Admin Mavi",
    "email": "admin@mavi.local",
    "company_id": null,
    "role": "admin"
  }
}
```

O middleware de log recebe essa resposta, registra status/duração e adiciona
`X-Request-ID`.

## 20. Quando o login falha

O domínio define:

```python
class UnauthorizedError(ApplicationError):
    def __init__(self, message: str = "Credenciais inválidas.") -> None:
        super().__init__("invalid_credentials", message, 401)
```

`ApplicationError` guarda:

```python
self.code = code
self.message = message
self.status_code = status_code
```

O handler global de `main.py` captura esse erro:

```python
@app.exception_handler(ApplicationError)
async def application_error(_, error: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
            }
        },
    )
```

A resposta fica consistente:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Credenciais inválidas."
  }
}
```

Uma entrada estruturalmente inválida, como e-mail sem formato válido, segue
outro handler e retorna 422 com código `invalid_request`.

## 21. Segunda requisição: `GET /api/v1/auth/me`

Depois do login, o cliente envia:

```http
GET /api/v1/auth/me HTTP/1.1
Authorization: Bearer token-original
```

O endpoint é pequeno:

```python
@router.get("/me", response_model=AccountResponse)
async def me(account: CurrentAccount):
    return account
```

Toda a autenticação está concentrada em `CurrentAccount`.

## 22. `core/security.py`: leitura do Bearer

```python
bearer = HTTPBearer(auto_error=False)
```

O FastAPI interpreta o header. `auto_error=False` permite que o projeto
controle sua própria resposta quando o header estiver ausente.

Depois:

```python
def bearer_token(credentials):
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials
```

- sem credencial: `None`;
- esquema diferente de Bearer: `None`;
- Bearer válido estruturalmente: devolve a parte do token.

Isso ainda não confirma que a sessão existe. Apenas extrai a credencial.

## 23. `auth/api/dependencies.py`: conta atual

```python
async def current_account(
    credentials: Credentials,
    service: AuthServiceDependency,
) -> Account:
    token = bearer_token(credentials)
    if not token:
        raise UnauthorizedError("Sessão inválida ou expirada.")
    return await service.authenticate(token)
```

O fluxo é:

1. extrair token;
2. rejeitar ausência ou header incorreto;
3. chamar o caso de uso `authenticate`;
4. injetar a entidade retornada no endpoint.

O alias:

```python
CurrentAccount = Annotated[Account, Depends(current_account)]
```

permite proteger qualquer rota apenas declarando `account: CurrentAccount`.

## 24. `AuthApplicationService.authenticate`

```python
async def authenticate(self, token: str) -> Account:
    account = await self.repository.account_by_session_hash(
        self.sessions.hash(token)
    )
    if not account:
        raise UnauthorizedError("Sessão inválida ou expirada.")
    return account
```

O token original nunca é procurado diretamente. O serviço calcula o mesmo
SHA-256 usado no login e pesquisa o hash.

## 25. Query que valida a sessão

O repositório executa:

```sql
select a.id, a.name, a.email, a.company_id, a.role
from sessions s
join accounts a on a.id = s.account_id
left join companies c on c.id = a.company_id
where s.token_hash = %s
  and s.revoked_at is null
  and s.expires_at > now()
  and (a.company_id is null or c.active)
```

A conta só é devolvida quando todas estas condições são verdadeiras:

1. o hash corresponde;
2. a sessão não foi revogada;
3. a sessão ainda não expirou;
4. a conta não pertence a empresa ou a empresa continua ativa.

Note que `password_hash` não é selecionado. Uma rota autenticada não precisa
ter acesso ao hash de senha.

## 26. Autorização de admin

Uma rota como `GET /api/v1/companies` usa `AdminAccount`, não apenas
`CurrentAccount`:

```python
async def admin_account(account: CurrentAccount) -> Account:
    if account.role is not AccountRole.ADMIN:
        raise ForbiddenError()
    return account
```

Diferença entre os erros:

- 401: não foi possível identificar uma sessão válida;
- 403: a sessão é válida, mas a conta não possui permissão.

O router de empresas declara:

```python
async def list_companies(
    _: AdminAccount,
    service: CompanyServiceDependency,
):
    return await service.list()
```

O nome `_` indica que o endpoint não usa os dados da conta; ele precisa apenas
que a dependência conclua a autorização antes do caso de uso.

## 27. Como o frontend usa o resultado

No Next.js, a Server Action de login chama:

```typescript
const session = await apiRequest("/api/v1/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, password }),
});
```

Depois grava:

```typescript
await setSessionToken(session.token, session.expires_at);
```

O cookie usa:

```typescript
{
  httpOnly: true,
  sameSite: "lax",
  secure: process.env.NODE_ENV === "production",
  path: "/",
  expires: new Date(expiresAt),
}
```

Em chamadas seguintes, `apiRequest` recebe o token no servidor Next.js e monta:

```typescript
headers.set("Authorization", `Bearer ${token}`);
```

O navegador não precisa ler o token. Ele envia o cookie ao Next.js, e o
Next.js envia o Bearer para o FastAPI.

## 28. Responsabilidade de cada camada neste fluxo

| Camada | Responsabilidade no login |
|---|---|
| `core` | Configuração, pool, segurança HTTP genérica, logs e formato global de erros. |
| `auth/api` | Validar JSON/header, montar dependências e converter saída para HTTP. |
| `auth/application` | Orquestrar busca, senha, token, expiração e sessão. |
| `auth/domain` | Definir conta, papéis, erros e interfaces. |
| `auth/infrastructure` | Executar SQL, Argon2, aleatoriedade e SHA-256. |
| PostgreSQL | Persistir conta/sessão e garantir constraints. |
| Next.js | Manter cookie HTTP-only, chamar a API e controlar navegação. |

## 29. Regra prática para ler outros módulos

O mesmo raciocínio pode ser aplicado a `companies` e `menus`:

```text
schema/router
    ↓
dependency monta service + repository
    ↓
application service executa o caso de uso
    ↓
domain fornece entidade, erro e Protocol
    ↓
infrastructure executa SQL e converte row
    ↓
schema serializa a entidade na resposta
```

Se uma regra de negócio estiver no router ou SQL estiver na aplicação, a
separação foi quebrada. O router deve tratar HTTP, a aplicação deve coordenar o
caso de uso, o domínio deve expressar conceitos/regras e a infraestrutura deve
lidar com tecnologias externas.
