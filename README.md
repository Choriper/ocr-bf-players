# OCR Player Search - Add Ban

Sistema para buscar jogador do Battlefield V usando imagem, print ou nome manual dentro da aba **Add Ban** do painel ADM.

## Objetivo

Permitir que o ADM possa:

- Digitar o nome do jogador manualmente
- Colar uma print com `Ctrl + V`
- Arrastar uma imagem para o campo
- Selecionar uma imagem do computador
- Identificar automaticamente:
  - Level
  - Clan tag
  - Nome do jogador
  - EA ID / Persona ID
  - Avatar
  - Plataforma

## Endpoint usado

```bash
POST /api/bfv/ocr/player-search
```

URL pública:

```bash
https://manager.choriper.com/api/bfv/ocr/player-search
```

## Exemplo com cURL

### Windows CMD

```cmd
curl -X POST "https://manager.choriper.com/api/bfv/ocr/player-search" -H "accept: application/json" -F "file=@adm-rip.png;type=image/png"
```

### PowerShell

```powershell
curl.exe -X POST "https://manager.choriper.com/api/bfv/ocr/player-search" -H "accept: application/json" -F "file=@adm-rip.png;type=image/png"
```

## Exemplo de imagem lida

Imagem:

```txt
64 [RIP]ADM-RIP
```

Resultado esperado:

```json
{
  "ok": true,
  "ocr_name": "[RIP]ADM-RIP",
  "clan_tag": "RIP",
  "player_name": "ADM-RIP",
  "level": 64,
  "player_found": true,
  "player": {
    "name": "ADM-RIP",
    "eaid": "ADM-RIP",
    "nickname": "ripbfadmin",
    "clan_tag": "RIP",
    "ocr_full_name": "[RIP]ADM-RIP",
    "search_name": "ADM-RIP",
    "ea_id": "1007367211454",
    "player_id": "1007367211454",
    "persona_id": "1007367211454",
    "platform": "pc",
    "status": "ACTIVE"
  }
}
```

## Regra de exibição no painel

No card de **Player selecionado**, o nome principal deve ser sempre o nome do Battlefield:

```txt
ADM-RIP
```

O nickname da conta deve aparecer abaixo:

```txt
ripbfadmin
```

Exemplo visual:

```txt
Player selecionado

ADM-RIP
ripbfadmin
personaId: 1007367211454
```

## Campos usados no Add Ban

Quando o OCR encontra o jogador, o painel preenche automaticamente:

| Campo | Valor |
|---|---|
| EA ID | `player.ea_id` |
| Persona ID | `player.persona_id` |
| Nome | `player.eaid` ou `player.name` |
| Nickname | `player.nickname` |
| Plataforma | `player.platform` |
| Avatar | `player.avatar` |

## Fluxo no frontend

1. ADM abre a aba **Bans**
2. Clica em **Add Ban**
3. Em **Pesquisar jogador**, ele pode:
   - Digitar o nome
   - Colar imagem
   - Arrastar imagem
   - Selecionar imagem
4. O frontend envia a imagem para:

```txt
/api/bfv/ocr/player-search
```

5. A API retorna o jogador encontrado
6. O painel preenche automaticamente o campo **EA ID**
7. ADM escolhe motivo, visibilidade e tipo de ban
8. Clica em **Add Ban**

## Observação importante

Para envio de imagem, não usar `Content-Type: application/json`.

O envio precisa ser feito com `FormData`:

```ts
const formData = new FormData();
formData.append('file', file);

await fetch('/api/bfv/ocr/player-search', {
  method: 'POST',
  credentials: 'include',
  body: formData,
  headers: {
    accept: 'application/json'
  }
});
```

O navegador define automaticamente o `Content-Type` correto:

```txt
multipart/form-data
```

## Exemplo de mapeamento correto

```ts
const battlefieldName =
  player.eaid ||
  player.name ||
  player.search_name ||
  data.player_name ||
  foundEaId;

const mappedPlayer = {
  EAID: battlefieldName,
  userId: player.ea_pd || player.nucleus_id || player.pd || foundEaId,
  id: foundEaId,
  avatarUrl: player.avatar || undefined,
  nickname:
    player.nickname && player.nickname !== battlefieldName
      ? player.nickname
      : undefined,
  platform: player.platform || 'pc',
  status: player.status || undefined,
};
```

## Resultado

Com isso, a busca por imagem no **Add Ban** funciona para prints como:

```txt
64 [RIP]ADM-RIP
```

E o painel seleciona corretamente:

```txt
Nome Battlefield: ADM-RIP
Nickname: ripbfadmin
Persona ID: 1007367211454
```
