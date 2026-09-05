# Pagamentos com Stripe Pix

> Documento histórico, substituído pela integração Asaas. Não utilize as instruções
> de configuração abaixo na versão atual. Consulte [PAGAMENTOS_ASAAS_PIX.md](PAGAMENTOS_ASAAS_PIX.md).

## Objetivo e regras implementadas

O pedido pode ser criado com uma destas formas de pagamento:

- `pay_on_delivery`: pagamento na entrega; o pedido entra imediatamente no fluxo da cozinha.
- `pix`: pagamento dentro do aplicativo; o pedido começa como `pending` e só entra no fluxo da cozinha depois do webhook de pagamento confirmado.

O status de produção e o status financeiro são independentes. Isso evita tratar “aguardando Pix” como uma etapa da cozinha e impede a preparação de um pedido ainda não pago.

Até o horário de corte, um Pix pendente pode ser retomado ou alterado para pagamento na entrega. A alteração cancela o `PaymentIntent` na Stripe antes de persistir o novo método. Pix pago, em processamento, estornado ou pedido fora do corte não pode ser alterado.

Por enquanto, a cobrança usa:

- nome e CPF do funcionário como dados do pagador;
- o e-mail de acesso da empresa como e-mail de cobrança para todos os seus funcionários;
- valor, moeda e prazo calculados exclusivamente no backend.

## Modelo de domínio

### Pedido

`orders` recebeu `payment_method`:

- `pay_on_delivery`
- `pix`

Pedidos legados permanecem com `payment_method = null` e `payment_status = not_applicable`, preservando compatibilidade.

### Status financeiro

| Status | Significado | Entra na cozinha |
|---|---|---:|
| `not_applicable` | Pagamento na entrega ou pedido legado | Sim |
| `pending` | Pix ainda não concluído | Não |
| `processing` | Stripe processando o pagamento | Não |
| `paid` | Pagamento confirmado pelo webhook | Sim |
| `failed` | Tentativa não concluída | Não |
| `expired` | Tentativa expirada | Não |
| `cancelled` | PaymentIntent cancelado | Não |
| `refunded` | Pagamento estornado, reservado para evolução | Não |

### Persistência Stripe

A migration `migrations/0007_stripe_pix_payments.sql` cria:

- `order_payments`: relação 1:1 entre pedido e `PaymentIntent`, valor em centavos, moeda, status do provedor, expiração e datas terminais;
- `stripe_webhook_events`: IDs dos eventos já processados, garantindo idempotência;
- constraints de coerência entre método e status;
- índices para consulta por pedido, status e período.

O `PaymentIntent` usa uma chave de idempotência estável derivada do ID do pedido. Uma falha entre criar o intent e persistir o registro pode ser recuperada sem gerar uma cobrança duplicada.

## Fluxo completo

### Criação do pedido

1. Empresa ou funcionário escolhe a forma de pagamento.
2. O backend valida empresa, funcionário, cardápio, preço e horário de corte.
3. `pay_on_delivery` é salvo como `not_applicable` e fica disponível para a cozinha.
4. `pix` é salvo como `pending` e permanece fora da cozinha.
5. O frontend solicita o checkout Pix para o pedido autorizado.
6. O backend cria ou recupera o único `PaymentIntent` do pedido e devolve o `client_secret`, a chave publicável e os dados de cobrança autorizados.
7. Stripe.js confirma o Pix e devolve QR Code e código copia-e-cola.
8. O frontend consulta o status do pedido enquanto aguarda, apenas para atualizar a experiência visual.
9. O webhook assinado é a fonte oficial da confirmação.

O frontend nunca define valor, moeda, e-mail, CPF ou expiração enviados à Stripe. Esses campos vêm do pedido e da empresa carregados pelo backend.

### Webhook

Endpoint público:

```text
POST /api/v1/webhooks/stripe
```

Eventos tratados:

- `payment_intent.succeeded` → `paid`
- `payment_intent.processing` → `processing`
- `payment_intent.payment_failed` → `failed`, ou `expired` quando o código indica expiração
- `payment_intent.canceled` → `cancelled`

Antes de alterar o pedido, o backend valida:

- assinatura `Stripe-Signature` com o segredo do endpoint;
- ID do pedido em `metadata`;
- ID do `PaymentIntent` persistido;
- valor em centavos;
- moeda.

Eventos repetidos são ignorados pelo ID Stripe. Um evento tardio não rebaixa um pagamento já marcado como pago.

### Retomar ou trocar o pagamento

Os painéis exibem pedidos Pix pendentes enquanto o corte ainda está aberto. O usuário pode:

- reabrir o mesmo `PaymentIntent` e gerar novamente as instruções Pix;
- cancelar o intent e trocar para `pay_on_delivery`;
- cancelar o pedido, o que também cancela um Pix pendente.

### Histórico

O painel da empresa aceita um intervalo de até 31 dias e filtros separados de produção e pagamento. O fluxo do funcionário carrega seus próprios pedidos, limitado por empresa e CPF, para permitir a retomada segura de Pix pendente.

## Endpoints

| Método e rota | Autorização | Uso |
|---|---|---|
| `POST /api/v1/orders/{id}/payments/pix` | Conta da empresa dona | Criar/retomar Pix |
| `POST /api/v1/employee/orders/{id}/payments/pix` | Sessão do funcionário dono | Criar/retomar Pix |
| `POST /api/v1/orders/{id}/payment-method/delivery` | Conta da empresa dona | Trocar para entrega |
| `POST /api/v1/employee/orders/{id}/payment-method/delivery` | Sessão do funcionário dono | Trocar para entrega |
| `POST /api/v1/webhooks/stripe` | Assinatura Stripe | Atualizar status financeiro |

Também foram adicionadas consultas de pedidos do funcionário e de um pedido individual, sempre escopadas por empresa e CPF.

## Configuração

Nunca versione chaves reais. Copie os arquivos de exemplo e preencha apenas arquivos locais/segredos do ambiente:

```dotenv
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_API_VERSION=
```

`STRIPE_API_VERSION` é opcional. Quando definido, deve corresponder à versão testada/configurada no endpoint de webhook da conta Stripe.

Para desenvolvimento com Stripe CLI:

```bash
stripe login
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

Copie o `whsec_...` mostrado pelo comando para `STRIPE_WEBHOOK_SECRET` e reinicie a API. A chave secreta e a publicável não substituem o segredo de webhook.

No Dashboard Stripe, habilite Pix para a conta brasileira em modo de teste. Em produção, configure o endpoint HTTPS definitivo e assine somente os eventos necessários.

Referências oficiais:

- [Aceitar pagamentos Pix](https://docs.stripe.com/payments/pix/accept-a-payment)
- [Criar PaymentIntent](https://docs.stripe.com/api/payment_intents/create)
- [Verificar status de PaymentIntent](https://docs.stripe.com/payments/payment-intents/verifying-status)
- [Assinaturas de webhook](https://docs.stripe.com/webhooks/signature)

## Aplicação da migration

Em um banco novo, os scripts são executados na criação do volume Docker. Em banco existente, aplique uma única vez:

```bash
docker compose exec database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0007_stripe_pix_payments.sql
```

Em staging e produção, use a conta de deploy do PostgreSQL e mantenha a ordem numérica das migrations. Faça backup antes da mudança de schema.

## Verificação

```bash
cd backend-python
ruff check app tests
pytest -q

cd ../frontend-next
npm run lint
npm run typecheck
npm test
npm run build
```

Cenários essenciais de homologação:

1. Pedido na entrega aparece na cozinha imediatamente.
2. Pedido Pix pendente não aparece na cozinha.
3. QR Code e copia-e-cola são exibidos no painel correto.
4. `payment_intent.succeeded` marca o pedido como pago e o libera para a cozinha.
5. Reenvio do mesmo evento não altera o resultado.
6. Evento com valor, moeda ou pedido divergente é rejeitado.
7. Antes do corte, Pix pendente pode ser retomado ou trocado para entrega.
8. Depois do corte, ou após pagamento/processamento, a troca é recusada.
9. Um funcionário não consulta nem paga pedido de outro CPF.

## Operação e próximas evoluções

- Rotacionar imediatamente qualquer chave secreta compartilhada em chat, log ou outro canal não destinado a segredos.
- Configurar alertas para falhas de webhook e reconciliação.
- Criar rotina periódica de reconciliação como defesa adicional contra indisponibilidade prolongada de webhook.
- Implementar fluxo explícito de estorno antes de habilitar cancelamento de pedidos pagos.
- Adicionar uma trilha administrativa de ajustes financeiros e motivo do ajuste.
- Avaliar e-mail individual do funcionário quando o cadastro garantir endereço válido e consentimento adequado.
