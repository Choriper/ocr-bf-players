# OCR BFV com Python + Docker

Projeto simples para ler texto de imagens pequenas, como level e nome de jogador em HUD/lista do Battlefield.

Exemplo da imagem incluída:

```txt
76 uMarcosPC
```

## Arquivos principais

```txt
ocr-bfv/
  Dockerfile
  docker-compose.yml
  requirements.txt
  main.py
  api.py
  app/
    ocr_reader.py
  exemplos/
    player.png
  scripts/
    run_cli_windows.bat
    run_api_windows.bat
```

## Rodar como API com Docker Compose

Na pasta do projeto:

```bash
docker compose up --build
```

Depois abra:

```txt
http://localhost:8000/health
```

## Testar OCR pela API

### Windows CMD

```bat
curl -X POST "http://localhost:8000/ocr" -F "file=@exemplos/player.png"
```

### PowerShell

```powershell
curl.exe -X POST "http://localhost:8000/ocr" -F "file=@exemplos/player.png"
```

Resposta esperada:

```json
{
  "ok": true,
  "filename": "player.png",
  "result": {
    "raw_text": "76 uMarcosPC\n",
    "cleaned_text": "76 uMarcosPC",
    "level": "76",
    "name": "uMarcosPC"
  }
}
```

## Rodar pelo modo CLI dentro do Docker

Build:

```bash
docker build -t ocr-bfv .
```

Executar usando a imagem de exemplo:

```bash
docker run --rm ocr-bfv python main.py --image exemplos/player.png
```

Executar salvando a imagem preprocessada para debug:

```bash
docker run --rm -v "%cd%/saida:/app/saida" ocr-bfv python main.py --image exemplos/player.png --debug
```

No Linux:

```bash
docker run --rm -v "$(pwd)/saida:/app/saida" ocr-bfv python main.py --image exemplos/player.png --debug
```

## Usar suas próprias imagens

Crie uma pasta `imagens` na raiz do projeto e coloque as imagens lá.

Windows CMD:

```bat
docker run --rm -v "%cd%/imagens:/app/imagens" ocr-bfv python main.py --image imagens/minha_imagem.png
```

Linux:

```bash
docker run --rm -v "$(pwd)/imagens:/app/imagens" ocr-bfv python main.py --image imagens/minha_imagem.png
```

## Ajustar leitura

Se o OCR errar, teste outros valores:

```bash
docker run --rm ocr-bfv python main.py --image exemplos/player.png --scale 5 --threshold 130 --debug
```

Parâmetros úteis:

- `--scale`: aumenta a imagem. Para texto pequeno, use `4`, `5` ou `6`.
- `--threshold`: controla o corte de contraste. Teste entre `110` e `180`.
- `--debug`: salva a imagem tratada em `saida/debug_preprocess.png`.

## Observação

Para imagens de jogo, o OCR funciona melhor quando você recorta somente a região do texto, sem ícones, bordas e fundo demais.
