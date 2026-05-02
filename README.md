# OCR BF Players

API simples em Python + FastAPI + Tesseract para ler prints pequenos de jogadores do Battlefield.

Ela foi feita para imagens no estilo:

```text
64 [RIP]ADM-RIP
73 [STF]Peacock-atomic
76 uMarcosPC
```

A API retorna o level e o nome lido pelo OCR.

---

## Estrutura esperada

```text
ocr-bf-players/
  Dockerfile
  docker-compose.yml
  requirements.txt
  api.py
  main.py
  app/
    __init__.py
    ocr_reader.py
```

---

## Docker Compose

Exemplo usando porta `8020`:

```yaml
ocr-bf-players:
  build:
    context: ./ocr-bf-players
    dockerfile: Dockerfile
  container_name: ocr-bf-players
  restart: unless-stopped
  expose:
    - "8020"
  ports:
    - "127.0.0.1:8020:8020"
  environment:
    TZ: America/Sao_Paulo
    HOST: 0.0.0.0
    PORT: 8020
    PYTHONUNBUFFERED: "1"
  command: uvicorn api:app --host 0.0.0.0 --port 8020
  networks: [edge]
```

URL interna para outros containers:

```env
CHORIPER_OCR_BF=http://ocr-bf-players:8020
```

URL local no host/VPS:

```text
http://127.0.0.1:8020
```

---

## Subir o container

```bash
docker compose up -d --build ocr-bf-players
```

Ver logs:

```bash
docker logs -f ocr-bf-players
```

Testar se a API está online:

```bash
curl http://127.0.0.1:8020/
```

Resposta esperada:

```json
{
  "ok": true,
  "message": "OCR BFV Players API online",
  "endpoint": "POST /ocr"
}
```

---

## Endpoint OCR

### `POST /ocr`

Recebe uma imagem via `multipart/form-data`.

Exemplo no Linux:

```bash
curl -X POST "http://127.0.0.1:8020/ocr" \
  -H "accept: application/json" \
  -F "file=@image.png;type=image/png"
```

Exemplo no Windows CMD:

```cmd
curl -X POST "http://127.0.0.1:8020/ocr" -H "accept: application/json" -F "file=@image.png;type=image/png"
```

---

## Exemplo: ADM-RIP

Imagem:

```text
64 [RIP]ADM-RIP
```

Resposta esperada:

```json
{
  "ok": true,
  "filename": "image.png",
  "result": {
    "raw_text": "64 [RIP]ADM-RIP",
    "cleaned_text": "64 [RIP]ADM-RIP",
    "level": 64,
    "name": "[RIP]ADM-RIP"
  }
}
```

Se sua API também separar clã no backend que consome o OCR, você pode converter:

```json
{
  "level": 64,
  "ocr_name": "[RIP]ADM-RIP",
  "clan_tag": "RIP",
  "player_name": "ADM-RIP"
}
```

---

## Exemplo: Peacock

Imagem:

```text
73 [STF]Peacock-atomic
```

Resposta esperada:

```json
{
  "ok": true,
  "filename": "Captura de tela 2026-05-02 150337.png",
  "result": {
    "raw_text": "73 [STF]Peacock-atomic",
    "cleaned_text": "73 [STF]Peacock-atomic",
    "level": 73,
    "name": "[STF]Peacock-atomic"
  }
}
```

---

## Exemplo: sem clã

Imagem:

```text
76 uMarcosPC
```

Resposta esperada:

```json
{
  "ok": true,
  "filename": "player.png",
  "result": {
    "raw_text": "76 uMarcosPC",
    "cleaned_text": "76 uMarcosPC",
    "level": 76,
    "name": "uMarcosPC"
  }
}
```

---

## Como chamar de outro serviço Python

Exemplo usando `requests`:

```python
import os
import requests

OCR_BASE_URL = os.getenv("CHORIPER_OCR_BF", "http://ocr-bf-players:8020")

def ocr_player_image(image_path: str):
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{OCR_BASE_URL}/ocr",
            files={"file": ("image.png", f, "image/png")},
            timeout=30,
        )

    response.raise_for_status()
    return response.json()


result = ocr_player_image("image.png")
print(result)
```

---

## Como chamar com `httpx` assíncrono

```python
import os
import httpx

OCR_BASE_URL = os.getenv("CHORIPER_OCR_BF", "http://ocr-bf-players:8020")

async def ocr_player_image(image_bytes: bytes, filename: str = "image.png"):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{OCR_BASE_URL}/ocr",
            files={"file": (filename, image_bytes, "image/png")},
        )

    response.raise_for_status()
    return response.json()
```

---

## Separar clã e nome

Se o OCR retornar:

```json
{
  "name": "[RIP]ADM-RIP"
}
```

Use esta função:

```python
import re

def split_clan_name(ocr_name: str):
    if not ocr_name:
        return None, None

    match = re.match(r"^\[([^\]]+)\](.+)$", ocr_name)

    if match:
        clan_tag = match.group(1).strip()
        player_name = match.group(2).strip()
        return clan_tag, player_name

    return None, ocr_name.strip()


clan_tag, player_name = split_clan_name("[RIP]ADM-RIP")

print(clan_tag)     # RIP
print(player_name)  # ADM-RIP
```

---

## Debug

Durante testes, você pode deixar no `api.py`:

```python
save_debug=True
```

Isso cria imagens na pasta:

```text
debug_ocr/
```

Quando terminar os testes, deixe:

```python
save_debug=False
```

para não ficar salvando imagem a cada requisição.

---

## Limpeza Docker

Se o Docker encher o disco:

```bash
docker builder prune -f
docker system prune -a -f
```

Ver quanto está usando:

```bash
docker system df
```

---

## Observações

- A porta interna usada neste exemplo é `8020`.
- Outros containers devem chamar `http://ocr-bf-players:8020`.
- O host/VPS pode testar por `http://127.0.0.1:8020`.
- Para produção, não exponha publicamente sem autenticação.
