# Evidências — Frontend, impressão térmica e Modo TV

Data da validação: 28/08/2026

## Objetivo

Evoluir somente o frontend solicitado no fluxo de acesso do funcionário, preservando a arquitetura, o backend, a autenticação e as permissões já descritas no `README.md`.

## Alterações entregues

### Estrutura compartilhada dos painéis

- O painel administrativo passou a utilizar o mesmo `PanelShell` empregado nas áreas de Empresa e Cozinha.
- A navegação lateral pode ser recolhida e expandida no desktop.
- Em telas menores, a navegação é apresentada como menu lateral móvel com sobreposição.
- O item correspondente à rota atual recebe indicação visual e `aria-current`.
- Conta autenticada e ação de logout permanecem disponíveis.

Arquivos relacionados:

- `frontend-next/src/components/panel-shell.tsx`
- `frontend-next/src/app/admin/layout.tsx`
- `frontend-next/src/app/empresa/layout.tsx`

### Fluxo demonstrativo do funcionário

- Nova entrada pública em `/funcionario`.
- Validação visual do código de acesso.
- Identificação do funcionário por nome, setor e matrícula opcional.
- Seleção de refeição utilizando os itens demonstrativos já existentes no frontend.
- Seleção de tamanho, quantidade e observações.
- Revisão do pedido antes da confirmação.
- Estado visual de envio e tela de sucesso.
- Layout responsivo, com prioridade para uso em tablet e alvos de toque amplos.
- Todo o fluxo está identificado como demonstração frontend, sem API ou persistência.

Arquivos relacionados:

- `frontend-next/src/app/funcionario/layout.tsx`
- `frontend-next/src/app/funcionario/page.tsx`
- `frontend-next/src/app/funcionario/pedido/page.tsx`
- `frontend-next/src/components/employee-entry.tsx`
- `frontend-next/src/components/employee-order-flow.tsx`

### Gestão visual de acessos

- Nova página administrativa em `/admin/acessos-funcionarios`.
- Nova página da empresa em `/empresa/acesso-funcionarios`.
- Listagem, criação, edição, alteração de status e redefinição de senha simuladas em estado local.
- A página da empresa exibe somente o acesso demonstrativo da própria empresa.
- As telas informam explicitamente que ainda não existe integração com o backend.

Arquivos relacionados:

- `frontend-next/src/app/admin/acessos-funcionarios/page.tsx`
- `frontend-next/src/app/empresa/acesso-funcionarios/page.tsx`
- `frontend-next/src/components/employee-access-management.tsx`

### Requisitos futuros de backend

O documento `docs/BACKEND_REQUIREMENTS.md` registra somente as necessidades ainda não implementadas para o acesso do funcionário. Ele também identifica os recursos existentes que deverão ser reutilizados, evitando substituir a autenticação e as roles atuais.

## Garantias de compatibilidade

- Nenhum arquivo do backend ou das migrations foi alterado nesta entrega.
- As roles existentes `admin`, `company` e `kitchen` foram mantidas.
- As páginas administrativas e empresariais continuam protegidas por `requireRole`.
- O acesso de funcionário não foi incluído artificialmente nos tipos ou na autenticação existente.
- Uma conta de empresa tentando acessar `/admin/acessos-funcionarios` recebe redirecionamento HTTP 307 para `/empresa`.

## Evidências de validação

| Verificação | Resultado |
| --- | --- |
| Build de produção do Next.js | Aprovado |
| Verificação TypeScript durante o build | Aprovada |
| ESLint | Aprovado, sem erros |
| Testes Vitest | 10 testes aprovados |
| `/funcionario` | HTTP 200 |
| `/funcionario/pedido` | HTTP 200 |
| `/admin/acessos-funcionarios` com conta Admin | HTTP 200 |
| `/empresa/acesso-funcionarios` com conta Empresa | HTTP 200 |
| Rota Admin acessada por conta Empresa | HTTP 307 para `/empresa` |
| `docker compose up --build -d` | Imagens construídas e serviços iniciados |

Comandos utilizados na validação:

```powershell
docker build --target build -t mavi-next-checks ./frontend-next
docker run --rm mavi-next-checks npm run lint
docker run --rm mavi-next-checks npm test
docker compose up --build -d
docker compose ps
```

## Rotas geradas no build

As novas rotas apareceram no relatório do build do Next.js:

```text
/admin/acessos-funcionarios
/empresa/acesso-funcionarios
/funcionario
/funcionario/pedido
```

## Sugestão para branch e commit

Nome de branch:

```text
feat/frontend-acesso-funcionario
```

Mensagem de commit:

```text
feat(frontend): adiciona fluxo e gestão mock de acesso do funcionário
```

## Complemento — impressão térmica e Modo TV

### Impressão de pedidos

- A ação do pedido recebido agora abre uma comanda individual formatada para
  bobina térmica de 80 mm.
- A comanda contém número, horário, funcionário, empresa, setor, prato,
  quantidade, tamanho e observações.
- O mapa do dia também é gerado como documento térmico.
- Após o fechamento da janela de impressão, o pedido demonstrativo avança para
  `printed`.
- A tela orienta selecionar a impressora `EPSON TM-T20X Receipt` no diálogo do
  Windows.
- A limitação do navegador para impressão silenciosa e a proposta de agente
  local ESC/POS foram registradas em `docs/BACKEND_REQUIREMENTS.md`.

Arquivos relacionados:

- `frontend-next/src/components/thermal-print-document.tsx`
- `frontend-next/src/app/cozinha/panel.tsx`
- `frontend-next/src/app/globals.css`

### Modo TV

- Novo item `Modo TV` na navegação da Cozinha.
- Nova rota protegida `/cozinha/modo-tv`.
- Dashboard somente leitura sobrepõe o shell do painel e não exibe menu lateral.
- Organização em `Aguardando`, `Em preparo` e `Prontos`.
- Cards grandes com número, funcionário, empresa, prato, quantidade, tamanho,
  horário, observações, status temporal e tempo em fila.
- Destaques demonstrativos para pedidos novos e atrasados.
- Relógio, atualização visual automática, rolagem por coluna e botão de tela
  cheia.
- Layout dimensionado para Full HD, mantendo adaptação para telas menores.
- WebSocket/SSE, polling, reconexão e contrato de leitura foram documentados
  como requisitos futuros de backend.

Arquivos relacionados:

- `frontend-next/src/app/cozinha/modo-tv/page.tsx`
- `frontend-next/src/components/kitchen-tv-dashboard.tsx`
- `frontend-next/src/app/cozinha/layout.tsx`
- `frontend-next/src/lib/demo-orders.ts`
- `frontend-next/src/lib/use-demo-orders.ts`
- `docs/BACKEND_REQUIREMENTS.md`

### Validação do complemento

| Verificação | Resultado |
| --- | --- |
| Build de produção Next.js | Aprovado |
| TypeScript | Aprovado |
| ESLint | Aprovado, sem erros |
| Vitest | 10 testes aprovados |
| Rota `/cozinha/modo-tv` no build | Gerada |
| `/cozinha/modo-tv` com conta Kitchen | HTTP 200 |
| Conteúdo principal do Modo TV | Confirmado na resposta renderizada |
| `/cozinha` com conta Kitchen | HTTP 200 |
| Orientação de impressão térmica | Confirmada na resposta renderizada |
| Acesso sem sessão ao Modo TV | Redirecionado para `/login` |

### Complemento — impressão direta

- Área útil da comanda reduzida de 74 mm para 68 mm em bobina de 80 mm.
- Tipografia, espaçamentos e blocos de observação compactados.
- Adicionado `scripts/iniciar-modo-impressao.ps1` para abrir um perfil dedicado
  do Microsoft Edge com `--kiosk-printing`.
- Nesse modo, `window.print()` é enviado diretamente à impressora padrão, sem
  exigir confirmação na prévia.
- O script verifica e avisa quando a impressora padrão não corresponde à
  `EPSON TM-T20X`.
- O perfil dedicado preserva a sessão da Cozinha entre usos e não interfere no
  perfil normal do Edge.
- Sintaxe PowerShell, build, TypeScript, ESLint e 10 testes Vitest aprovados
  após o ajuste.
