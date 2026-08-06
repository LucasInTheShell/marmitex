# CLAUDE.md — Mavi Connect

> Arquivo de contexto persistente do projeto. Leia antes de qualquer alteração.
> Se uma decisão deste arquivo conflitar com um pedido do usuário, **pergunte antes de codar**.

@AGENTS.md

---

## 1. Contexto

**Mavi Connect** é um sistema de gestão de marmitas corporativas para a **Mavi**, restaurante/cozinha própria que fornece refeições para empresas por contrato.

Hoje os pedidos são feitos de forma informal (WhatsApp/planilha/papel), sem antecedência, o que impede a cozinha de planejar produção. O sistema centraliza o agendamento antecipado, dispara a produção e organiza a separação por empresa.

**Time:** desenvolvedor solo (dev + testes + QA). Priorize código simples, legível e testado sobre código "esperto".

---

## 2. Os três papéis (v1)

| Papel | Onde acessa | O que faz |
|---|---|---|
| **Colaborador** | Web mobile, com o **login da empresa** | Agenda suas marmitas da semana (1 por dia útil) |
| **Cozinha** | TV / monitor grande | Vê os pedidos do dia agrupados por empresa e imprime etiquetas |
| **Administração** | Web desktop | Cadastra empresas, publica o cardápio da semana, também imprime etiquetas |

**Entregador** existe no processo real, mas **não tem interface na v1**.

> **Não existe cadastro de colaborador na v1.** O acesso é por empresa
> (credencial compartilhada). O colaborador se identifica preenchendo nome,
> telefone, departamento e CPF no próprio pedido.

---

## 3. Escopo v1 — o que está DENTRO

O critério de sucesso da v1 é uma frase só:

> Um colaborador agenda a marmita da semana, o pedido aparece no painel da cozinha agrupado pela empresa dele, e a cozinha imprime uma etiqueta com nome, empresa, prato e tamanho.

Isso significa exatamente três funcionalidades núcleo:

1. **Agendamento semanal** pelo colaborador
2. **Painel da cozinha** com pedidos do dia agrupados por empresa
3. **Impressão de etiqueta** por marmita

Mais o mínimo que sustenta as três:
- Login **da empresa** (uma credencial por empresa)
- Área admin para publicar cardápio da semana e cadastrar empresas

---

## 4. Escopo v1 — o que está FORA (não implementar)

Não construa, não deixe stub, não "prepare terreno" para:

- ❌ **Pagamento** (Pix, maquininha, checkout) — pedido nasce confirmado na v1
- ❌ **WhatsApp / notificações** de qualquer tipo
- ❌ **Relatórios e dashboard gerencial**
- ❌ **Fotos dos pratos** (só texto no cardápio)
- ❌ **App do entregador** e rastreamento de entrega
- ❌ **Multi-restaurante** (o sistema atende só a Mavi por enquanto)
- ❌ **Cancelamento/edição de pedido pelo colaborador** após o corte
- ❌ **Cadastro individual de colaborador** (login, perfil, histórico pessoal)

Exceção: o **modelo de dados** deve ter os campos que a Fase 2 vai precisar (ver §9), mesmo sem tela. Campo em tabela é barato; tela e fluxo não são.

---

## 5. Stack

Mínima, madura e que um dev solo consegue manter:

- **Next.js** (App Router, TypeScript)
- **Supabase** — Postgres + Auth + Realtime + RLS
- **Tailwind CSS**
- **Vitest** para unitários, **Playwright** para E2E
- Deploy: **Vercel**

**Por que Supabase:** o painel da cozinha precisa atualizar sozinho quando um pedido entra. Realtime do Supabase resolve isso sem WebSocket próprio. Não construa polling manual.

**Não adicionar sem pedir:** Redis, fila de jobs, microserviço, ORM alternativo, state manager global, biblioteca de UI pesada.

---

## 6. Modelo de dados (v1)

```
companies        id, name, active, created_at
accounts         id, name, email, company_id, role (company|kitchen|admin)
menu_items       id, name, description, size_options[], price
menus            id, date, menu_item_ids[], published
orders           id, company_id, date, menu_item_id, size,
                 employee_name, employee_phone, employee_department, employee_cpf,
                 production_status, payment_status, created_at
labels_printed   id, order_id, printed_at
```

- `accounts` são **credenciais, não pessoas**. `role = 'company'` é a credencial
  compartilhada de uma empresa; `kitchen` e `admin` são a equipe da Mavi.
- `production_status`: `pending` → `printed` → `separated` → `delivered`
- `payment_status`: existe desde a v1, sempre `not_applicable`. **Não misturar com production_status** — foram separados de propósito.

**RLS obrigatório:**
- A conta da empresa **não tem `SELECT` em `orders`** — o pedido é "cego".
  A escrita passa pela função `create_order()` (`SECURITY DEFINER`), porque
  `INSERT ... RETURNING` exigiria policy de `SELECT` e exporia os pedidos dos
  colegas pela API.
- Cozinha e admin enxergam todos os pedidos.
- A empresa só enxerga menus com `published = true`, e só a própria empresa.

As regras acima são verificadas por `npm run test:db`.

---

## 7. Regras de negócio (invioláveis)

1. **Horário de corte:** `10:00 do mesmo dia`. Depois do corte, o dia some do
   cardápio do colaborador. O valor vive em variável de ambiente
   (`ORDER_CUTOFF_TIME`), **nunca hardcoded**. Fuso: `APP_TIME_ZONE`
   (`America/Sao_Paulo`).
2. Uma marmita por pessoa por dia útil — ancorada em **CPF + data**
   (`UNIQUE (employee_cpf, date)`), já que não há cadastro de colaborador.
3. Pedidos são sempre **agrupados por empresa** no painel da cozinha — nunca listados soltos.
4. Só aparece no cardápio do colaborador o menu com `published = true`.
5. O colaborador só vê e agenda dentro da própria empresa (a credencial define a empresa).
6. Etiqueta impressa contém, no mínimo: **nome do colaborador, empresa, prato, tamanho, data**.
7. Tamanhos de marmita: **P, M, G**.

---

## 8. Testes e QA (dev solo — inegociável)

Sem QA humano, o teste automatizado é a única rede de segurança. **Todo PR mexe no teste junto.**

**Caminho crítico coberto por Playwright desde o dia 1:**
```
admin publica o cardápio da semana →
colaborador entra com o login da empresa → vê o cardápio → agenda 5 dias →
pedido aparece no painel da cozinha agrupado pela empresa →
etiqueta é gerada com os 5 campos obrigatórios
```

Testes unitários obrigatórios para:
- cálculo do horário de corte (inclui virada de dia e fim de semana)
- agrupamento por empresa
- filtro de cardápio publicado

Antes de dizer que uma tarefa está pronta: rodar `npm run test`, `npm run test:db`
e `npm run test:e2e`. Não declare conclusão sem os três passando.

---

## 9. Mapa de esforço — o que vem depois e quanto custa

Ordenado por relação valor/esforço. Use isso para negociar prazo, não improvise fora dessa ordem.

### 🟢 Rápido (horas a 1–2 dias) — pode entrar cedo
- **Fotos dos pratos** — upload no Supabase Storage + `<img>`. Risco baixo.
- **Cardápio recorrente** (duplicar semana anterior) — economiza muito tempo da admin.
- **Relatório simples** (quantidade por empresa/dia em CSV) — query + export, sem BI.
- **Marcar "separado"/"entregue"** no painel da cozinha — só update de status.

### 🟡 Médio (3–7 dias) — exige revisão de arquitetura
- **Impressão de etiqueta em impressora térmica real.** A v1 usa `window.print()` com CSS de bobina de cupom. Migrar para ESC/POS numa impressora física é o ponto mais subestimado do projeto: driver, tamanho da bobina, encoding de acentos, teste no hardware do cliente. **Reserve um dia só para testar na impressora real, presencialmente.** Modelo exato ainda a validar com a Mavi.
- **Cancelamento/edição de pedido.** Parece trivial, mas cria buraco na regra de corte e na contagem da cozinha. Precisa definir com o cliente: pode cancelar depois do corte? Quem absorve o custo?
- **Cadastro individual de colaborador.** Se a Mavi quiser histórico por pessoa, preferência salva ou pedido não-cego, isso deixa de ser preenchimento de formulário e vira autenticação por pessoa — muda a RLS e o modelo de `orders`.
- **Relatório financeiro com fechamento mensal por empresa.** O problema não é código, é acordar a regra de fechamento com a Mavi.

### 🔴 Longo (1–3 semanas) — planejar como fase própria
- **Pagamento (Pix + pagar na entrega).** Integração com PSP, webhook de confirmação, conciliação, estorno, estados intermediários. É o item que mais gera bug em produção. O `payment_status` já separado do `production_status` existe justamente para isso — **não fundir os dois quando implementar.**
- **WhatsApp (confirmação e "a caminho").** Exige API oficial (Meta Cloud API ou BSP), aprovação de templates, número verificado. O gargalo é burocrático, não técnico — o prazo depende da Meta, não de você.
- **Multi-restaurante / multi-tenant de verdade.** Confirmado com o cliente que a expansão prevista é de **mais empresas clientes da Mavi**, não de outras cozinhas. O sistema segue mono-restaurante. Se isso mudar, é refatoração de RLS e de todas as queries.

---

## 10. Decisões do cliente (fechadas)

- **Nome oficial:** Mavi Connect
- **Horário de corte:** 10:00 do mesmo dia
- **Escala inicial:** 5 empresas, com expansão prevista (mais empresas, mesma cozinha)
- **Tamanhos:** P, M, G
- **Cozinha:** própria da Mavi, com tela dedicada na cozinha
- **Impressão de etiqueta:** cozinha **e** administração podem imprimir
- **Impressora:** térmica de cupom, modelo exato a validar
- **Cadastro do colaborador:** não existe. A admin cadastra a empresa; o
  colaborador usa o login da empresa e preenche nome, telefone, departamento e
  CPF no pedido.

### Ponto em aberto a comunicar à Mavi
- O CPF de cada colaborador passa a ser armazenado, num sistema cuja credencial
  é compartilhada pela empresa. É a chave certa para a regra de uma marmita por
  pessoa por dia, mas é dado pessoal sob LGPD e a Mavi precisa saber disso.

---

## 11. Convenções

- Código e comentários em **inglês**; copy da interface em **português (pt-BR)**.
- Commits: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`.
- Um PR = uma funcionalidade + seus testes.
- Painel da cozinha tem **regra visual própria**: alto contraste, tipografia grande, feito para ser lido a 3 metros de distância numa TV. Não aplicar a paleta pastel do app do colaborador nessa tela.
- Antes de criar arquivo novo, verificar se já existe algo parecido no projeto.
