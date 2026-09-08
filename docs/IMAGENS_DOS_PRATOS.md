# Imagens dos pratos: arquitetura, fluxo e operação

## Objetivo

O cadastro de pratos aceita até seis fotos. Uma delas é marcada como principal e as demais são exibidas em um carrossel no painel da empresa. Na edição é possível adicionar novas fotos, remover fotos existentes e trocar a principal. A exclusão do prato também remove toda a galeria do storage, sem apagar a linha do banco: o prato recebe `deleted_at` para preservar referências e o histórico dos pedidos.

A implementação não acopla o módulo ao Supabase. O caso de uso depende da porta `ObjectStorage`; em desenvolvimento ela aponta para disco local e, em produção, para qualquer storage compatível com S3, incluindo Supabase Storage, Amazon S3, Cloudflare R2 ou MinIO.

## Fluxo completo

```text
Painel admin
  -> Server Action (FormData)
  -> POST/PUT multipart da API
  -> MenuApplicationService
  -> PillowImageProcessor (valida, redimensiona e converte para WebP)
  -> ObjectStorage (local ou S3)
  -> PostgresMenuRepository (salva chaves e ordem em menu_item_images)
  -> MenuItemResult (devolve image_url principal + images[])
  -> painel admin / cardápio disponível da empresa
```

O browser nunca recebe uma chave S3 de escrita. O upload passa pelo backend autenticado como `admin`, e as credenciais do storage ficam somente no ambiente da API.

## Responsabilidade de cada arquivo

### Banco e domínio

- `migrations/0004_menu_item_images_and_soft_delete.sql`: introduz a primeira imagem e o soft delete.
- `migrations/0005_menu_item_image_gallery.sql`: cria `menu_item_images`, migra automaticamente a foto anterior como principal e remove a coluna transitória `image_key`.
- `app/modules/menus/domain/entities.py`: representa a galeria com `MenuItemImage`, contendo chave, ordem e indicação de principal. O domínio não guarda URLs dependentes do provedor.
- `app/modules/menus/domain/repositories.py`: define leitura por ID, criação com UUID previamente gerado, atualização e exclusão lógica.
- `app/modules/menus/domain/exceptions.py`: erros de imagem inválida, prato ausente e storage indisponível com códigos HTTP adequados.

### Application

- `application/ports.py`: contratos `ImageProcessor` e `ObjectStorage`. Também concentra o limite de upload de 5 MB.
- `application/dto.py`: modelos de saída que acrescentam `image_url` sem contaminar a entidade de domínio.
- `application/services.py`: orquestra criação, seleção da principal, adição, remoção e exclusão da galeria, garantindo no máximo seis imagens e uma única principal.

Na criação, o serviço gera primeiro o UUID do prato, produz uma chave imutável como:

```text
menu-items/<id-do-prato>/<uuid-da-versao>.webp
```

Se os uploads funcionarem e a escrita no banco falhar, os objetos recém-enviados são excluídos como compensação. As remoções antigas só são apagadas do storage depois que a nova galeria é persistida. Como cada arquivo tem uma URL imutável, o cache do CDN pode ser longo sem exibir uma foto antiga.

### Infrastructure

- `infrastructure/image_processing.py`: abre e valida o conteúdo real com Pillow, aceita JPEG/PNG/WebP, aplica orientação EXIF, limita a 50 megapixels, reduz para no máximo 1200×900, remove metadados e gera WebP RGB com qualidade 82.
- `infrastructure/storage.py`: implementa `LocalObjectStorage` e `S3ObjectStorage`. O S3 usa assinatura v4 e path-style, necessário para endpoints compatíveis como o Supabase.
- `infrastructure/repository.py`: carrega a galeria ordenada, atualiza seus metadados de forma transacional, ignora pratos com `deleted_at`, faz soft delete e remove o ID dos cardápios. Se um cardápio ficar vazio, ele é despublicado.
- `infrastructure/models.py`: converte a linha SQL para a entidade.

### API e composição

- `api/router.py`: recebe `multipart/form-data`, limita cada arquivo a 5 MB e cada prato a seis imagens, e expõe o CRUD administrativo.
- `api/schemas.py`: inclui `image_url` na resposta.
- `api/dependencies.py`: injeta storage, processador e repositórios no serviço.
- `app/main.py`: cria os adaptadores uma vez. No modo local também publica `/media` com `StaticFiles`.
- `app/core/config.py`: valida as variáveis de storage, inclusive as obrigatórias quando `STORAGE_BACKEND=s3`.

### Frontend

- `src/app/admin/pratos/actions.ts`: valida todos os arquivos, preserva os itens repetidos em `FormData` e chama POST, PUT ou DELETE.
- `src/app/admin/pratos/form.tsx`: cadastro múltiplo com prévias, escolha da principal, adição, remoção e confirmação de exclusão.
- `src/lib/api/client.ts`: não força `Content-Type: application/json` quando o corpo é `FormData`; o runtime define o boundary multipart correto.
- `src/app/empresa/panel.tsx`: mostra a principal na lista e a galeria navegável do prato selecionado.
- `next.config.ts`: autoriza as origens de imagem, usa imagens remotas sem otimização duplicada e eleva o limite da Server Action para 32 MB. Cada arquivo continua limitado a 5 MB e a galeria a seis itens.

## Contrato HTTP

Somente contas `admin` podem alterar pratos.

### Criar

```http
POST /api/v1/menu-items
Content-Type: multipart/form-data

name=Frango grelhado
description=Arroz, feijão e salada
size_options=P
size_options=M
price=24.90
images=<arquivo 1 opcional>
images=<arquivo 2 opcional>
primary_image_index=1
```

`primary_image_index` é baseado em zero; no exemplo, a segunda foto é a principal.

### Editar a galeria

```http
PUT /api/v1/menu-items/{item_id}
Content-Type: multipart/form-data
```

O PUT recebe todos os campos do prato. Novas fotos são enviadas repetindo `images`. Use `remove_image_ids` para cada foto removida. Para escolher uma foto existente como principal, envie `primary_image_id`; para escolher uma nova, envie `primary_new_image_index`. Os dois campos de principal são mutuamente exclusivos.

### Excluir

```http
DELETE /api/v1/menu-items/{item_id}
```

Retorna `204`. A linha fica marcada com `deleted_at`, sai das listagens e dos cardápios, mas itens já copiados para pedidos continuam preservados.

## Teste local com Docker

1. Reconstrua os serviços para instalar `Pillow`, `python-multipart` e `boto3`:

```powershell
docker compose up -d --build
```

2. Em uma base já existente, aplique a migração. Os arquivos em `docker-entrypoint-initdb.d` só são executados automaticamente quando o volume do PostgreSQL é criado pela primeira vez:

```powershell
Get-Content migrations\0004_menu_item_images_and_soft_delete.sql | docker compose exec -T database psql -U mavi -d mavi_connect
Get-Content migrations\0005_menu_item_image_gallery.sql | docker compose exec -T database psql -U mavi -d mavi_connect
```

3. Entre como admin em `http://localhost:3000/admin/pratos`, selecione uma ou mais fotos, marque a principal e salve.

4. A foto local ficará no volume nomeado `media-data` e será servida por uma URL parecida com:

```text
http://localhost:8000/media/menu-items/<item-id>/<versao>.webp
```

5. Publique um cardápio contendo o prato e confirme a principal e o carrossel no painel da empresa.

6. Execute as verificações automatizadas:

```powershell
cd backend-python
python -m pytest -q
python -m ruff check app tests

cd ..\frontend-next
npm run lint
npm run build
```

## Integração com Supabase Storage

O projeto usa a interface S3 do Supabase diretamente pelo backend. Não é necessário instalar `@supabase/supabase-js` no frontend.

### 1. Criar o bucket

No Dashboard do Supabase:

1. Abra **Storage** e crie um bucket chamado `dish-images`.
2. Marque o bucket como **public**. Fotos de pratos são conteúdo público do cardápio; um bucket privado exigiria URLs assinadas e outro contrato de cache.
3. Configure no bucket limite de 5 MB e MIME types `image/jpeg`, `image/png` e `image/webp`, como segunda barreira. O arquivo armazenado pela API será sempre WebP.

Bucket público só libera leitura pública. Escrita e exclusão continuam protegidas; neste projeto elas usam credenciais S3 exclusivas do backend.

### 2. Ativar S3 e gerar credenciais

Em **Storage > Configuration > S3**:

1. Ative o protocolo S3.
2. Gere `Access Key ID` e `Secret Access Key` e guarde o segredo no gerenciador de secrets da hospedagem.
3. Copie também o endpoint direto e a região exibidos pelo painel.

As chaves S3 têm acesso amplo ao storage e ignoram RLS. Nunca use `NEXT_PUBLIC_`, nunca coloque essas chaves no frontend e nunca as versione no Git.

### 3. Configurar o ambiente da API

Troque `<project-ref>` e `<project-region>` pelos valores do Dashboard:

```dotenv
STORAGE_BACKEND=s3
STORAGE_BUCKET=dish-images
STORAGE_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
STORAGE_REGION=<project-region>
STORAGE_ACCESS_KEY_ID=<access-key-id>
STORAGE_SECRET_ACCESS_KEY=<secret-access-key>
STORAGE_PUBLIC_BASE_URL=https://<project-ref>.supabase.co/storage/v1/object/public/dish-images
```

`STORAGE_PUBLIC_BASE_URL` já termina no nome do bucket. A API acrescenta somente a chave `menu-items/...`.

No Docker local, você pode colocar esses valores em um arquivo `.env` que não seja commitado e recriar apenas a API:

```powershell
docker compose up -d --build --force-recreate api frontend
docker compose logs -f api
```

Em produção, defina as mesmas variáveis no serviço que executa a API. O frontend não precisa das credenciais nem de uma URL Supabase própria: ele usa a `image_url` devolvida pela API.

### 4. Verificar

1. Crie um prato pelo painel admin.
2. No Supabase, confirme o objeto em `dish-images/menu-items/<id>/<versao>.webp`.
3. Abra a `image_url` retornada por `GET /api/v1/menu-items` em uma janela anônima. Ela deve responder sem autenticação.
4. Adicione várias imagens, altere a principal e confirme a ordem em `menu_item_images`.
5. Remova uma imagem e confira que somente sua chave desapareceu.
6. Exclua o prato e confirme o soft delete no PostgreSQL e a remoção de toda a galeria.

## Decisões operacionais e limites

- As imagens são públicas por desenho; não coloque dados pessoais nelas.
- A exclusão de objeto depois de uma alteração confirmada é *best effort*: falha do storage é registrada no log e não desfaz dados válidos do prato. Uma rotina periódica de limpeza de órfãos pode ser adicionada quando o volume justificar.
- O Supabase não oferece versionamento S3 para recuperação de objetos apagados. A exclusão do arquivo é definitiva.
- A aplicação não depende das transformações pagas do Supabase porque já normaliza tamanho e formato antes do upload.
- Para trocar de fornecedor, mantenha o bucket público, ajuste as variáveis S3 e, se necessário, migre os objetos preservando suas chaves. Nenhuma linha do banco precisa mudar.

## Referências oficiais

- [Supabase: autenticação S3](https://supabase.com/docs/guides/storage/s3/authentication)
- [Supabase: buckets públicos e privados](https://supabase.com/docs/guides/storage/buckets/fundamentals)
- [Supabase: formato da URL pública](https://supabase.com/docs/guides/storage/serving/downloads)
- [Supabase: compatibilidade S3](https://supabase.com/docs/guides/storage/s3/compatibility)
