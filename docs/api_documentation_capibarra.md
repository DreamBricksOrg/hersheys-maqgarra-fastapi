# API Documentation — Máquina de Garra CAPIBARRA / Hershey's

## Visão geral

- validar nota por QR Code c/ parser/webscrapping
- validar nota por leitura da imagem
- consultar uma nota já processada
- aplicar override manual na quantidade de barras
- associar tags às notas

### Endpoints

- `GET /alive`
- `POST /api/receipts/qr`
- `POST /api/receipts/image`
- `GET /api/receipts/{receipt_id}`
- `POST /api/receipts/override`
- `POST /api/tags/associate`

---

### Autenticação

Todas as rotas de negócio devem receber a API key do tablet.

#### Header obrigatório

```http
x-api-key: <API_KEY_DO_TABLET>
```

#### Header opcional

```http
x-device-id: tablet-01
```

### Content-Type

- JSON: `application/json`
- Upload de imagem: `multipart/form-data`

### Formato padrão de erro

```json
{
  "error": {
    "code": "receipt_duplicate",
    "message": "Esta nota já foi utilizada",
    "details": {
      "receipt_key": "1234567890",
      "used_at": "2026-03-22T14:10:00-03:00"
    }
  }
}
```

### Status

Valores usados em `receipt.status`:

- `valid`
- `used`
- `invalid`
- `error`

---

## Fluxo funcional da API

### 1. Nota com QR

O tablet lê o QR, envia para o backend, o backend faz parse/web scraping, conta produtos elegíveis, detecta duplicidade e retorna a quantidade.

### 2. Nota sem QR

O tablet tira foto, envia para a API de leitura de nota, recebe JSON, processa produtos e retorna quantidade.

### 3. Override

Se a automação não reconhecer corretamente, a promotora informa a quantidade correta e o sistema salva `final_bars` acima de `found_bars`.

### 4. Associação de tag

Depois de acumular barras suficientes, a API associa as tags às notas.

---

# Endpoints

## `GET /alive`

Verifica se a API está respondendo.

### Request

Sem body.

### Response `200 OK`

```json
{
  "status": "ok"
}
```

---

## `POST /api/receipts/qr`

Recebe o conteúdo do QR Code da nota fiscal, executa o parse da nota, identifica produtos Hershey elegíveis, verifica duplicidade e retorna o resultado.

### Services envolvidos

- Auth
- Receipt QR
- Parser
- Product Matching
- Receipt Validation

### Headers

```http
x-api-key: <API_KEY_DO_TABLET>
x-device-id: tablet-01
Content-Type: application/json
```

### Request body

```json
{
  "qr_value": "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx?p=...."
}
```

### Campos

| Campo      | Tipo     | Obrigatório | Descrição                                                                           |
| ---------- | -------- | ----------: | ----------------------------------------------------------------------------------- |
| `qr_value` | `string` |         Sim | Conteúdo bruto lido do QR. Pode ser URL completa ou string compatível com o parser. |

### Processamento esperado

1. valida API key
2. loga `receipt-qr-received`
3. faz parse/web scraping da nota
4. extrai `receipt_key` e lista de itens
5. verifica se a nota já foi usada
6. executa matching dos produtos
7. calcula `found_bars`
8. inicializa `final_bars = found_bars`
9. define `review` e `status`
10. salva em Mongo
11. retorna o resultado

### Response `200 OK`

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56789",
  "receipt_key": "35260312345678901234550010000012345678901234",
  "source": "qr",
  "timestamp": "2026-03-22T14:10:00-03:00",
  "found_bars": 6,
  "final_bars": 6,
  "review": false,
  "status": "valid",
  "items": [
    {
      "name": "HERSHEYS OVO AO LEITE 20G",
      "quantity": 2,
      "matched": true
    },
    {
      "name": "HERSHEYS COOKIES 77G",
      "quantity": 4,
      "matched": true
    }
  ],
  "raw_payload": {
    "receipt_key": "35260312345678901234550010000012345678901234",
    "products": [
      {
        "name": "HERSHEYS OVO AO LEITE 20G",
        "quantity": "2"
      },
      {
        "name": "HERSHEYS COOKIES 77G",
        "quantity": "4"
      }
    ]
  }
}
```

### Response `409 Conflict` — nota duplicada

```json
{
  "error": {
    "code": "receipt_duplicate",
    "message": "Esta nota já foi utilizada",
    "details": {
      "receipt_key": "35260312345678901234550010000012345678901234",
      "status": "used"
    }
  }
}
```

### Response `422 Unprocessable Entity` — QR inválido

```json
{
  "error": {
    "code": "qr_invalid",
    "message": "QR code inválido ou não suportado",
    "details": {}
  }
}
```

### Response `502 Bad Gateway` — falha no parser

```json
{
  "error": {
    "code": "qr_parse_failed",
    "message": "Não foi possível interpretar a nota pelo QR",
    "details": {}
  }
}
```

### Eventos

- `auth-api_key-validated`
- `receipt-qr-received`
- `receipt-qr-parsed`
- `receipt-qr-parse_failed`
- `product_matching-started`
- `product_matching-finished`
- `receipt-validation-started`
- `receipt-validation-finished`
- `receipt-duplicate-detected`

---

## `POST /api/receipts/image`

Recebe imagem da nota. O backend envia a imagem para o fluxo de leitura, recebe o JSON da nota, faz matching de produtos, valida e retorna a quantidade.

### Services envolvidos

- Auth
- Receipt Image
- Parser
- Product Matching
- Receipt Validation

### Headers

```http
x-api-key: <API_KEY_DO_TABLET>
x-device-id: tablet-01
Content-Type: multipart/form-data
```

### Request body

`multipart/form-data`

### Campos

| Campo              | Tipo      | Obrigatório | Descrição                                                |
| ------------------ | --------- | ----------: | -------------------------------------------------------- |
| `image`            | `file`    |         Sim | Arquivo da nota fiscal.                                  |
| `save_error_image` | `boolean` |         Não | Indica se a imagem deve ser persistida no fluxo de erro. |
| `notes`            | `string`  |         Não | Observações técnicas ou operacionais.                    |

### Processamento esperado

1. valida API key
2. recebe imagem
3. envia imagem para leitura da nota
4. recebe JSON original
5. se necessário, salva a imagem em `/static/upload`
6. executa product matching
7. calcula `found_bars`
8. inicializa `final_bars = found_bars`
9. define `review`
10. salva `receipt` no Mongo
11. retorna o resultado

### Response `200 OK`

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56790",
  "receipt_key": "35260312345678901234550010000099999999999999",
  "source": "image",
  "timestamp": "2026-03-22T14:12:00-03:00",
  "found_bars": 3,
  "final_bars": 3,
  "review": false,
  "status": "valid",
  "items": [
    {
      "name": "H COOK 77",
      "quantity": 3,
      "matched": true
    }
  ],
  "raw_payload": {
    "products": [
      {
        "name": "H COOK 77",
        "quantity": "3"
      }
    ]
  }
}
```

### Response `200 OK` — caso de erro auditável

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56791",
  "receipt_key": "35260312345678901234550010000088888888888888",
  "source": "image",
  "timestamp": "2026-03-22T14:15:00-03:00",
  "found_bars": 0,
  "final_bars": 0,
  "review": true,
  "status": "error",
  "items": [],
  "error_audit": {
    "image_path": "/static/upload/2026-03-22/67d1f8e9a0b1c2d3e4f56791.jpg"
  }
}
```

### Response `422 Unprocessable Entity` — imagem inválida

```json
{
  "error": {
    "code": "invalid_image",
    "message": "Arquivo de imagem inválido",
    "details": {}
  }
}
```

### Response `502 Bad Gateway` — falha na leitura da nota

```json
{
  "error": {
    "code": "receipt_image_parse_failed",
    "message": "Não foi possível processar a nota pela imagem",
    "details": {}
  }
}
```

### Eventos

- `receipt-image-erro-uploaded`
- `receipt-image-erro-stored`
- `receipt-image-erro-audited`
- `product_matching-started`
- `product_matching-finished`
- `receipt-validation-started`
- `receipt-validation-finished`
- `receipt-validation-failed`

---

## `GET /api/receipts/{receipt_id}`

Retorna os dados de uma nota já processada.

### Headers

```http
x-api-key: <API_KEY_DO_TABLET>
x-device-id: tablet-01
```

### Path params

| Campo        | Tipo     | Obrigatório | Descrição                             |
| ------------ | -------- | ----------: | ------------------------------------- |
| `receipt_id` | `string` |         Sim | ObjectId do documento salvo em Mongo. |

### Response `200 OK`

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56789",
  "receipt_key": "35260312345678901234550010000012345678901234",
  "source": "qr",
  "timestamp": "2026-03-22T14:10:00-03:00",
  "found_bars": 6,
  "final_bars": 6,
  "review": false,
  "status": "valid",
  "raw_payload": {
    "products": [
      {
        "name": "HERSHEYS OVO AO LEITE 20G",
        "quantity": "2"
      }
    ]
  }
}
```

### Response `404 Not Found`

```json
{
  "error": {
    "code": "receipt_not_found",
    "message": "Nota não encontrada",
    "details": {}
  }
}
```

---

## `POST /api/receipts/override`

Aplica correção manual na quantidade de barras de uma nota já processada.

### Headers

```http
x-api-key: <API_KEY_DO_TABLET>
x-device-id: tablet-01
Content-Type: application/json
```

### Request body

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56791",
  "final_bars": 6,
  "reason": "promotora confirmou seis barras na nota"
}
```

### Campos

| Campo        | Tipo      | Obrigatório | Descrição                   |
| ------------ | --------- | ----------: | --------------------------- |
| `receipt_id` | `string`  |         Sim | ID da nota processada.      |
| `final_bars` | `integer` |         Sim | Quantidade final corrigida. |
| `reason`     | `string`  |         Não | Motivo do override.         |

### Regras

- a nota precisa existir
- `final_bars` não pode ser negativo
- a API sobrescreve `final_bars`
- `found_bars` é preservado para comparação
- `review` pode continuar `true` ou ser atualizado conforme regra interna
- `status` pode permanecer `valid` se a nota segue elegível

### Response `200 OK`

```json
{
  "receipt_id": "67d1f8e9a0b1c2d3e4f56791",
  "found_bars": 0,
  "final_bars": 6,
  "review": true,
  "status": "valid",
  "override_applied": true
}
```

### Response `404 Not Found`

```json
{
  "error": {
    "code": "receipt_not_found",
    "message": "Nota não encontrada",
    "details": {}
  }
}
```

### Response `422 Unprocessable Entity`

```json
{
  "error": {
    "code": "invalid_override",
    "message": "Quantidade final inválida",
    "details": {}
  }
}
```

### Eventos

- `receipt-override`
- `receipt-validation-finished`

---

## `POST /api/tags/associate`

Associa uma ou mais tags às notas ou a uma sessão de agrupamento.

### Headers

```http
x-api-key: <API_KEY_DO_TABLET>
x-device-id: tablet-01
Content-Type: application/json
```

### Request body — forma mínima por nota

```json
{
  "receipt_ids": ["67d1f8e9a0b1c2d3e4f56789", "67d1f8e9a0b1c2d3e4f56790"],
  "tags": ["100001", "100002"]
}
```

### Request body — forma compatível com sessão

```json
{
  "session_id": "67d1f8e9a0b1c2d3e4f56800",
  "tags": ["100001", "100002"]
}
```

### Campos

| Campo         | Tipo            | Obrigatório | Descrição                                              |
| ------------- | --------------- | ----------: | ------------------------------------------------------ |
| `receipt_ids` | `array[string]` |         Não | Lista de notas a associar, se não houver `session_id`. |
| `session_id`  | `string`        |         Não | Sessão de agrupamento das notas.                       |
| `tags`        | `array[string]` |         Sim | Lista de tags a ativar e associar.                     |

### Regras

- cada tag deve existir
- a tag deve estar disponível para ativação
- a associação marca a tag como ativa
- as notas associadas deixam de poder ser reutilizadas
- a quantidade de tags deve ser compatível com as regras do total de barras

### Response `200 OK`

```json
{
  "session_id": "67d1f8e9a0b1c2d3e4f56800",
  "receipt_ids": ["67d1f8e9a0b1c2d3e4f56789", "67d1f8e9a0b1c2d3e4f56790"],
  "tags": [
    {
      "tag_key": "100001",
      "status": "valid"
    },
    {
      "tag_key": "100002",
      "status": "valid"
    }
  ],
  "associated": true
}
```

### Response `409 Conflict` — tag já usada

```json
{
  "error": {
    "code": "tag_already_used",
    "message": "Uma ou mais tags já estão em uso",
    "details": {
      "tags": ["100001"]
    }
  }
}
```

### Response `404 Not Found` — tag inexistente

```json
{
  "error": {
    "code": "tag_not_found",
    "message": "Tag não encontrada",
    "details": {
      "tag_key": "100001"
    }
  }
}
```

### Eventos

- `tag-association-created`
- `tag-association-used`
- `tag-association-failed`

---

# Schemas

## Receipt

```json
{
  "_id": "ObjectId",
  "receipt_key": "string | null",
  "source": "qr | image",
  "timestamp": "ISODate",
  "found_bars": 0,
  "final_bars": 0,
  "review": false,
  "status": "valid | used | invalid | error",
  "raw_payload": {},
  "session_id": "ObjectId | null"
}
```

### Campos

| Campo         | Tipo               | Descrição                                             |
| ------------- | ------------------ | ----------------------------------------------------- |
| `_id`         | `ObjectId`         | Identificador interno do documento.                   |
| `receipt_key` | `string \| null`   | Chave principal da nota para checagem de duplicidade. |
| `source`      | `qr \| image`      | Origem da leitura.                                    |
| `timestamp`   | `ISODate`          | Data/hora do scan.                                    |
| `found_bars`  | `integer`          | Quantidade encontrada automaticamente.                |
| `final_bars`  | `integer`          | Quantidade final após override, se houver.            |
| `review`      | `boolean`          | Indica se precisa revisão.                            |
| `status`      | `enum`             | Estado final da nota.                                 |
| `raw_payload` | `object`           | JSON original retornado pelo parser/leitor.           |
| `session_id`  | `ObjectId \| null` | Sessão de agrupamento.                                |

---

## Session

```json
{
  "_id": "ObjectId",
  "receipt_ids": ["ObjectId"],
  "tag_ids": ["ObjectId"],
  "created_at": "ISODate",
  "finished_at": "ISODate | null"
}
```

### Campos

| Campo         | Tipo              | Descrição                  |
| ------------- | ----------------- | -------------------------- |
| `_id`         | `ObjectId`        | Identificador da sessão.   |
| `receipt_ids` | `array[ObjectId]` | Notas agrupadas na sessão. |
| `tag_ids`     | `array[ObjectId]` | Tags entregues na sessão.  |
| `created_at`  | `ISODate`         | Início da sessão.          |
| `finished_at` | `ISODate \| null` | Fim da sessão.             |

---

## Tag

```json
{
  "_id": "ObjectId",
  "tag_key": "num",
  "status": "valid | invalid"
}
```

### Campos

| Campo     | Tipo               | Descrição                  |
| --------- | ------------------ | -------------------------- |
| `_id`     | `ObjectId`         | Identificador interno.     |
| `tag_key` | `string`           | Valor escaneável da tag.   |
| `status`  | `valid \| invalid` | Status operacional da tag. |

---

## barsNames

```json
{
  "_id": "ObjectId",
  "name": "product name not normalized"
}
```

### Campos

| Campo  | Tipo       | Descrição                                         |
| ------ | ---------- | ------------------------------------------------- |
| `_id`  | `ObjectId` | Identificador interno.                            |
| `name` | `string`   | Nome do produto exatamente como apareceu na nota. |

---

# DTOs resumidos

## `ReceiptQRRequest`

```json
{
  "qr_value": "string"
}
```

## `ReceiptResponse`

```json
{
  "receipt_id": "string",
  "receipt_key": "string | null",
  "source": "qr | image",
  "timestamp": "string",
  "found_bars": 0,
  "final_bars": 0,
  "review": false,
  "status": "valid | used | invalid | error",
  "items": [],
  "raw_payload": {}
}
```

## `ReceiptOverrideRequest`

```json
{
  "receipt_id": "string",
  "final_bars": 0,
  "reason": "string"
}
```

## `TagAssociateRequest`

```json
{
  "session_id": "string",
  "tags": ["string"]
}
```

ou

```json
{
  "receipt_ids": ["string"],
  "tags": ["string"]
}
```

---

# Observabilidade / Log Center

```json
{
  "event": "http-request-completed",
  "service": "hersheys-receipt-api",
  "request_id": "uuid",
  "device_id": "tablet-01",
  "path": "/api/receipts/qr",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 231
}
```

---
