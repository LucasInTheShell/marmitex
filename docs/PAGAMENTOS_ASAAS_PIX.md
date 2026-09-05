# Pix com Asaas — implementação e homologação

## Estado da entrega

O backend e os fluxos da empresa/funcionário utilizam Asaas. Stripe.js não é mais
utilizado. As migrations 0008 e 0009 foram aplicadas ao banco local nesta entrega;
API e frontend foram reconstruídos. Não repita migrations já aplicadas.

As credenciais reais do sandbox **não foram configuradas nem testadas**. No `.env`
local, `ASAAS_API_KEY` e `ASAAS_WEBHOOK_TOKEN` estão vazios. Sem ambos, a API
recusa iniciar Pix e o worker de pagamentos não é iniciado. Pagamento na entrega
continua disponível. Chaves antigas Stripe não são lidas pelo backend.

## Fluxo implementado

1. O pedido Pix é criado como `pending`, fora da cozinha.
2. O backend bloqueia a linha do pedido durante criação/retomada/cancelamento.
3. Cria ou reutiliza um cliente Asaas por empresa/CPF. O nome e CPF são do
   funcionário; o e-mail utilizado é o da empresa. Notificações do cliente são
   desabilitadas na criação para evitar mensagens de cobrança duplicadas.
4. Cria a cobrança em `POST /v3/lean/payments`, com valor calculado no servidor,
   `billingType=PIX` e `externalReference` igual ao UUID do pedido.
5. Recupera o QR em `GET /v3/payments/{id}/pixQrCode`.
6. A API devolve `provider`, `provider_payment_id`, `qr_code_base64`,
   `pix_copy_paste`, `amount_cents`, `currency` e `expires_at`, além dos dados
   de cobrança. Não há chave publicável nem `client_secret`.
7. O componente compartilhado exibe o QR diretamente e consulta apenas a API
   local a cada quatro segundos. O browser nunca confirma o pagamento.

Endpoints preservados:

```text
POST /api/v1/orders/{id}/payments/pix
POST /api/v1/employee/orders/{id}/payments/pix
POST /api/v1/orders/{id}/payment-method/delivery
POST /api/v1/employee/orders/{id}/payment-method/delivery
POST /api/v1/webhooks/asaas
```

## Webhook, concorrência e recuperação

- O webhook valida `asaas-access-token` com comparação em tempo constante.
- Persiste o evento normalizado em `payment_event_inbox` e faz commit **antes**
  de responder HTTP 200. Falha na persistência não é reconhecida como sucesso.
- Um worker iniciado junto à API processa a fila. Erros são mantidos com
  `attempts`, `last_error` e `next_attempt_at`; há novas tentativas com atraso
  crescente de até cinco minutos. Eventos não são descartados por faltar o
  registro local de pagamento.
- Um pagamento remoto sem vínculo local pode ser recuperado pelo
  `externalReference`, após consulta autenticada e conferência de pedido,
  identificador, valor, moeda e tipo Pix.
- `payment_webhook_events` é o registro dos eventos aplicados, com chave por
  provedor/evento. A atualização financeira e a conclusão do processamento são
  transacionais. Uma falha entre recebimento e processamento não perde o evento.
- O worker consulta o **estado atual** da cobrança. O nome `PAYMENT_RECEIVED`
  sozinho nunca marca um pedido como pago.
- Bloqueio PostgreSQL por pedido serializa checkouts e alterações de método.
  Um advisory lock por empresa/CPF serializa o cadastro remoto de clientes.
- Antes de criar novamente, o adaptador pesquisa cobranças por referência externa,
  recuperando respostas anteriores inconclusivas. A referência externa não é uma
  chave de idempotência garantida pelo Asaas: falhas externas ambíguas precisam
  ser acompanhadas na homologação e nos logs.
- Estorno é terminal; eventos atrasados não reabrem um pagamento estornado.
  Estorno parcial e estados desconhecidos vão para análise, não para estorno total.

## Estados e horário de corte

| Estado verificado | Estado no aplicativo | Cozinha |
| --- | --- | --- |
| Pendente | `pending` | Não |
| Confirmado, saldo ainda não recebido | `processing` | Não |
| Recebido dentro da janela validada | `paid` | Sim |
| Cobrança removida no corte | `expired` | Não |
| Removida antes do corte | `cancelled` | Não |
| Estornado integralmente | `refunded` | Não |
| Recebimento tardio, estorno parcial ou divergência de estado | `review_required` | Não |

O vencimento Asaas é uma **data**, não o horário de corte do pedido. O QR pode
continuar válido no provedor depois desse horário. Por isso:

- O frontend oculta QR/copia-e-cola no corte e impede novas ações de pagamento.
- A API rejeita início/retomada e troca de método fora da janela.
- O worker verifica o corte e remove cobranças ainda pendentes, consultando antes
  e depois da remoção. Falhas são registradas e tentadas novamente.
- O intervalo padrão do worker é 15 segundos, em lotes de 20. Cancelamento remoto
  é eventual: carga, indisponibilidade ou API desligada podem aumentar o atraso.
  Não existe garantia de bloquear um Pix exatamente no segundo do corte.
- Se o pagamento for verificado pela primeira vez após o corte, sem confirmação
  anterior registrada, fica em `review_required`. Mesmo um webhook atrasado de um
  pagamento possivelmente pontual é retido por segurança: não presumimos um
  horário de liquidação que não conseguimos comprovar.
- Confirmação Asaas já observada antes do corte permite recebimento posterior.
- A empresa vê a análise no histórico; o funcionário recebe orientação de não
  pagar novamente. Não há estorno automático nem liberação manual automática.
  O responsável deve conferir a transação no Asaas e, quando necessário,
  devolver pelo fluxo de estorno do provedor. O webhook reconciliará o estorno.

Além do corte, cobranças abertas são reconciliadas aproximadamente a cada cinco
minutos como defesa contra webhooks ausentes. A consulta de status no frontend
não chama o Asaas diretamente.

No corte, pedidos Pix sem registro local de cobrança também são pesquisados no
Asaas por referência externa. Isso recupera cobranças criadas antes de um timeout
mesmo sem webhook, permitindo removê-las. Se não houver cobrança remota, apenas
o pedido local é marcado como expirado.

## Configurar o sandbox

1. Crie a conta de sandbox e a chave pela interface web do Asaas, em Integrações.
   Sandbox e produção têm contas/chaves separadas.
2. Configure no `.env` da raiz (Docker) ou no ambiente do processo da API:

```dotenv
ASAAS_API_URL=https://api-sandbox.asaas.com/v3
ASAAS_API_KEY='SUA_CHAVE_SANDBOX'
ASAAS_WEBHOOK_TOKEN='SEU_TOKEN_ALEATORIO_DE_32_A_255_CARACTERES'
ASAAS_REQUEST_TIMEOUT_SECONDS=10
ASAAS_USER_AGENT=mavi-connect/0.1.0
PAYMENT_WORKER_INTERVAL_SECONDS=15
```

Use aspas simples na chave para preservar caracteres `$` no arquivo `.env`.
Não coloque segredos no frontend, em commits, logs ou mensagens.
O token do webhook é diferente da chave da API; pode ser gerado pelo painel Asaas.

3. Recrie a API para carregar as variáveis:

```powershell
docker compose up -d --force-recreate api
```

4. Para o webhook alcançar o backend local, use um túnel HTTPS de teste. Com
   `cloudflared` instalado:

```powershell
cloudflared tunnel --url http://localhost:8000
```

O túnel expõe o backend publicamente enquanto aberto. Mantenha autenticação e
use apenas dados de homologação. Feche o túnel ao terminar.

5. No Asaas, acesse Menu do usuário → Integrações → Webhooks → Criar Webhook:

   - URL: `https://SEU-TUNEL/api/v1/webhooks/asaas`.
   - Auth Token: exatamente o valor de `ASAAS_WEBHOOK_TOKEN`.
   - API Version: 3; habilitado; envio sequencial.
   - Eventos: `PAYMENT_CREATED`, `PAYMENT_UPDATED`, `PAYMENT_CONFIRMED`,
     `PAYMENT_RECEIVED`, `PAYMENT_OVERDUE`, `PAYMENT_DELETED`, `PAYMENT_REFUNDED`,
     `PAYMENT_PARTIALLY_REFUNDED`, `PAYMENT_REFUND_IN_PROGRESS`.

Atualize a URL no painel quando o túnel temporário mudar. Cadastre somente eventos
de cobrança nesse endpoint; eventos de transferências têm outro formato.

## Fazer um pagamento de teste

1. Configure cardápio, horário ainda aberto, empresa com e-mail e funcionário
   com dados de teste aceitos pelo Asaas. Use contatos próprios/controlados.
2. No aplicativo, faça um pedido escolhendo Pix. Confirme que QR e copia-e-cola
   aparecem, o pedido está pendente e não aparece na cozinha.
3. No painel **sandbox**, abra a cobrança que o aplicativo acabou de criar
   (identifique pelo número do pedido/valor e referência externa).
4. Clique em **Confirmar pagamento** na interface de sandbox.
5. Confira a entrega do webhook (HTTP 200) e aguarde o processamento do worker.
   Recebimento reconhecido dentro do prazo passa a pago e libera a cozinha.

Não pague pelo aplicativo bancário e não use dinheiro real. A confirmação pela
interface do sandbox simula o recebimento. Uma cobrança criada manualmente sem
vínculo com um pedido não serve para testar a atualização daquele pedido.

Outros cenários obrigatórios: retomar o mesmo pedido (mesmo ID remoto), dois
checkouts simultâneos, trocar para entrega antes do corte, confirmar e depois
tentar trocar, cruzar o corte, recebimento tardio, reenvio de webhook, estorno,
API temporariamente desligada e recuperação após reinício.

## Operação e diagnóstico

```powershell
docker compose logs --tail=100 api
docker compose ps
```

Para acompanhar continuamente, acrescente `-f` ao comando de logs.
Mensagens `Payment event processed`, `Payment event retry` e
`Payment reconciliation retry` identificam o resultado sem expor segredos.

Consulta operacional, sem o corpo dos eventos:

```sql
select event_id, attempts, last_error, next_attempt_at
from payment_event_inbox
where processed_at is null
order by received_at;

select order_id, provider_payment_id, provider_status, review_reason
from order_payments where review_reason is not null;
```

HTTP 200 do webhook significa recebimento durável, não pagamento aprovado.
401/403 do provedor: verifique chave/ambiente/permissões. 400 no webhook:
verifique token/payload. 404 na rota: confira imagem da API e URL do túnel.
Fila pendente: confira configuração do worker e `last_error`. Não marque pedidos
como pagos manualmente no banco para contornar uma falha de integração.

## Migrations e validação

0008 generaliza os identificadores e adiciona clientes por provedor. 0009 adiciona
inbox durável, `confirmed_at`, `last_checked_at`, motivo de análise e o novo estado.
Em outros ambientes, aplique migrations ainda pendentes em ordem, uma única vez.
Não use `docker compose down -v` para atualizar schema: isso apaga o volume.

Validação realizada: 90 testes de backend sem rede externa, quatro testes em um
banco PostgreSQL temporário isolado, 22 testes frontend, lint/typecheck e build.
Os testes PostgreSQL validam concorrência, inbox, estorno terminal, corte e retry.
Não substituem a homologação com a conta Asaas real de sandbox.

```powershell
# Dentro de backend-python
python -m pytest -q
# Opcional: conexão administrativa de um PostgreSQL de desenvolvimento.
# Cria e remove somente um banco novo mavi_payment_test_<uuid>.
$env:PAYMENT_TEST_ADMIN_URL='postgresql://USUARIO:SENHA@localhost:5434/postgres'
python -m pytest tests/test_payments_postgres.py -q

# Dentro de frontend-next
npm run test
npm run lint
npm run typecheck
```

## Referências oficiais

- [Cobranças Pix e QR dinâmico](https://docs.asaas.com/docs/cobrancas-via-pix)
- [Consultar cobrança](https://docs.asaas.com/reference/recuperar-uma-unica-cobranca)
- [Remover cobrança não equivale a estornar](https://docs.asaas.com/reference/delete-payment)
- [Configurar webhook](https://docs.asaas.com/docs/criar-novo-webhook-pela-aplicacao-web)
- [Simular confirmação no sandbox](https://docs.asaas.com/docs/como-adicionar-dinheiro-para-testes)
- [Chaves de API](https://docs.asaas.com/docs/chaves-de-api)
