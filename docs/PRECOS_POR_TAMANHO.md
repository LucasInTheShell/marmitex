# Preços de pratos por tamanho

Implementado em 05/09/2026.

## Como usar

Em **Administração → Pratos**, no cadastro ou edição, use **Tamanhos e preços**:

- **Preço único para todos os tamanhos** mantém o funcionamento anterior.
- **Preço diferente por tamanho** permite informar valores para P, M e G.
- Marque apenas os tamanhos disponíveis. No modo por tamanho, todos os tamanhos
  marcados precisam de preço. Valores aceitam vírgula ou ponto e até duas casas
  decimais. Preços negativos são rejeitados; zero é permitido, como no catálogo anterior.

Os cards mostram “A partir de” quando há preços diferentes. Na seleção do
tamanho, o preço correspondente aparece para empresa e funcionário. Carrinho,
subtotal e confirmação usam o tamanho selecionado.

## Contrato e persistência

`POST /api/v1/menu-items` e `PUT /api/v1/menu-items/{id}` continuam multipart.
O campo `size_prices` recebe um objeto JSON, por exemplo:

```json
{"P":"12.99","M":"18.00","G":"23.90"}
```

As respostas do catálogo e dos cardápios disponíveis incluem `size_prices` como
mapa de valores numéricos. `price` continua sendo o preço único/fallback.
No formulário, preço por tamanho envia `price` vazio e o mapa completo.
Voltar ao preço único envia `size_prices={}`.

Para compatibilidade, uma atualização que omite `size_prices` preserva os preços
por tamanho ainda habilitados. Clientes novos devem sempre enviar o mapa explícito.
API e banco validam tamanhos, valores não negativos, limite de R$ 99.999.999,99 e
até duas casas decimais. Um mapa parcial exige preço único para os demais tamanhos.

A migration `0010_menu_item_size_prices.sql` adiciona a coluna JSONB, com mapa
vazio por padrão, e sua restrição de integridade. Pratos antigos mantêm o preço
único. Não há recálculo nem alteração de pedidos anteriores.

O backend resolve o preço pelo tamanho ao criar o pedido, grava `unit_price` e
`subtotal` no item e calcula `total_price` com Decimal. O Pix usa esse total salvo
em centavos; alterações posteriores no catálogo não alteram a cobrança existente.

## Ambiente local e validação

A migration 0010 foi aplicada ao banco local, e API e frontend foram reconstruídos.
Em outro ambiente com banco existente, aplique a migration uma única vez antes
de iniciar a nova API:

```powershell
docker compose exec -T database psql -v ON_ERROR_STOP=1 -U mavi -d mavi_connect -f /docker-entrypoint-initdb.d/0010_menu_item_size_prices.sql
docker compose up -d --build api frontend
```

Verificações realizadas:

- Backend: 105 testes aprovados; os cinco testes PostgreSQL opcionais foram
  executados separadamente e também passaram, em bancos aleatórios isolados.
- Testes novos cobrem cadastro/edição multipart, valores inválidos, tamanhos
  incompletos, compatibilidade, persistência e publicação do cardápio.
- Pedido com 2×P a R$ 12,99, 1×M a R$ 18,00 e 1×G a R$ 23,90 totaliza R$ 67,88;
  o gateway Pix simulado recebe 6788 centavos, mesmo após mudar o catálogo.
- Frontend: 25 testes aprovados, TypeScript, ESLint e build de produção aprovados.
- A validação financeira desta mudança usou gateway simulado; nenhuma nova
  cobrança foi criada no Asaas durante os testes.

Para conferir visualmente, edite um prato, escolha preço por tamanho, salve e
abra o cardápio como empresa ou funcionário. Adicione dois tamanhos diferentes
ao pedido e confira seus subtotais antes de confirmar.
