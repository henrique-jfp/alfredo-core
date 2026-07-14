# Manual do Usuário — Spotify & YouTube

## Sumário

1. [Spotify](#spotify)
   - [Autenticação](#autenticação)
   - [Comandos de Música](#comandos-de-música)
   - [Fallback para YouTube](#fallback-para-youtube)
   - [Dashboard](#dashboard)
2. [YouTube](#youtube)
   - [Reprodução](#reprodução)
   - [Lives e Transmissões ao Vivo](#lives-e-transmissões-ao-vivo)
   - [Podcasts](#podcasts)
   - [Parar Reprodução](#parar-reprodução)
3. [Arquitetura Interna](#arquitetura-interna)
   - [Fluxo Spotify](#fluxo-spotify)
   - [Fluxo YouTube](#fluxo-youtube)

---

## Spotify

### Autenticação

1. Acesse o **Dashboard** (painel web) do Alfredo.
2. Vá em **Configurações → Spotify** e clique em **"Conectar com Spotify"**.
3. Faça login na sua conta do Spotify (gratuita ou Premium).
   - **Nota**: Controle de reprodução (play/pause/skip/volume) requer **Spotify Premium**.
   - Contas gratuitas só conseguem pesquisar e obter informações.

### Comandos de Música

| Comando | Exemplo | Ação |
|---------|---------|------|
| "Toca/tocar **música/som**" | "toca um rock nacional" | Retoma a música ou pesquisa e toca |
| "Pausa/pausar/parar **música**" | "pausa a música" | Pausa a reprodução |
| "Próxima/pular" | "próxima música" | Pula para a faixa seguinte |
| "Voltar/anterior" | "volta a música" | Volta para a faixa anterior |

**Regras de interpretação**:

- Se você disser apenas *"toca rock nacional"* (sem mencionar "música" ou "spotify"), o Alfredo pode interpretar como busca geral e usar o Gemini. Para garantir que toque no Spotify, inclua **"no Spotify"** ou **"música"** no comando.
- Quando uma música começa, o Dashboard exibe o card do Spotify com capa, nome da faixa, artista, barra de progresso e controle de volume.

### Fallback para YouTube

Se o Alfredo não encontrar dispositivos Spotify disponíveis, ele **automaticamente** busca a música no YouTube e toca diretamente no alto-falante do dispositivo.

```
Exemplo:
Usuário: "toca bohemian rhapsody"
→ Alfredo tenta tocar no Spotify
→ Nenhum dispositivo Spotify encontrado
→ Busca no YouTube com yt-dlp
→ "Tocando Bohemian Rhapsody diretamente no alto-falante."
```

**Limitação**: No fallback para YouTube, não há controle de pausa, volume ou próxima faixa — é uma reprodução linear.

### Dashboard

- **Cards de Reprodução**: Ao tocar algo, o card do Spotify aparece no canto do Dashboard.
- **SSE (Server-Sent Events)**: O card atualiza em tempo real via conexão contínua (sem polling de 3 segundos).
- **Botões**: Play/Pause, Próxima, Anterior, controle de volume.

---

## YouTube

### Reprodução

O Alfredo pode tocar áudio de vídeos, podcasts e transmissões ao vivo do YouTube diretamente no alto-falante do dispositivo.

| Comando | Exemplo | Ação |
|---------|---------|------|
| "Toca **canal/vídeo** no YouTube" | "toca o flow podcast no youtube" | Busca e toca o áudio |
| "Coloca **live**" | "coloca a cazetv" | Busca live e toca ao vivo |
| "Quer ouvir **podcast**" | "quero ouvir o podpah" | Busca podcast e toca |
| "Para o YouTube" | "para o youtube" | Para a reprodução |

**Dicas**:
- Se você mencionar **"no YouTube"**, o Alfredo entende que é YouTube mesmo que a busca seja música.
- Para **lives**, diga o nome do canal (ex: "CazéTV", "GloboNews", "CNN Brasil").
- Para **podcasts**, diga o nome (ex: "Flow Podcast", "Podpah", "Inteligência LTDA").

### Lives e Transmissões ao Vivo

O Alfredo usa uma API interna do YouTube para encontrar transmissões ao vivo. Se você pedir:

- *"coloca a globonews"* → sistema entende que é uma live
- *"caze tv"* → sistema busca a live da CazéTV

**Funcionamento**:
1. Se `is_live=True` (detectado pelo Gemini ou pelo contexto), usa a API de busca de lives do YouTube.
2. Se a API de lives falhar, faz **fallback** para a busca normal do yt-dlp.

### Podcasts

Podcasts são tratados como vídeos normais do YouTube. Basta dizer o nome do podcast.

```
Exemplo:
Usuário: "quero ouvir inteligência ltda"
→ Alfredo busca "inteligência ltda" no YouTube
→ Extrai áudio via yt-dlp
→ "Tocando agora o áudio de: Inteligência Ltda."
```

### Parar Reprodução

Para parar o áudio do YouTube a qualquer momento:

```
"para o youtube"
"para o audio"
"para de tocar"
```

O comando é processado pelo **roteador semântico** (fast path), sem precisar do Gemini.

---

## Arquitetura Interna

### Fluxo Spotify

```
Usuário → "toca [música]"
   │
   ▼
Router (Groq fast path → "manage_music")
   │
   ├── Semantic Router match → "manage_music" (fast path, <5ms)
   │
   └── Gemini → "manage_music" (se não passou pelo semantic router)
         │
         ▼
MusicSkill.execute_tool()
   ├── Ação play → busca no Spotify + toca no dispositivo
   ├── Ação pause → pausa
   ├── Fallback → youtube_service.search_audio(...)
   │
   └── Dashboard → SSE endpoint /api/spotify/now-playing/stream
```

**Serviço compartilhado**: `core/services/spotify_service.py`
- Gerencia OAuth (credenciais criptografadas)
- Seleciona o melhor dispositivo disponível
- Busca e toca músicas, controla reprodução
- Obtém "agora tocando" para o Dashboard

**Endpoints**:
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/spotify/auth` | Inicia OAuth |
| GET | `/api/spotify/callback` | Callback OAuth |
| GET | `/api/spotify/now-playing` | Dados da faixa atual |
| GET | `/api/spotify/now-playing/stream` | SSE em tempo real |
| POST | `/api/spotify/control` | Controle (play/pause/skip/volume) |

### Fluxo YouTube

```
Usuário → "toca [canal] no youtube"
   │
   ├── Semantic Router match → "play_youtube" (stop action)
   │
   └── Gemini → "play_youtube(query=..., is_live=...)"
         │
         ▼
YouTubeSkill.execute_tool()
   ├── action="stop" → envia stop_audio via WebSocket
   ├── action="play" (padrão):
   │     ├── is_live=True  → youtube_service._search_live_api()
   │     ├── is_live=False → youtube_service.search_audio() (yt-dlp + fallback live)
   │     └── Resultado → {"type":"play_audio", "url":"..."} via WebSocket
   │
   └── Satellite → mplayer/vlc reproduz áudio
```

**Serviço compartilhado**: `core/services/youtube_service.py`

Funções expostas:

| Função | Parâmetros | Retorno | Descrição |
|--------|-----------|---------|-----------|
| `search_audio(query, is_live)` | query: str, is_live: bool | dict \| None | Busca áudio no YouTube |
| `is_ambiguous_query(query)` | query: str | bool | Verifica se a query é muito vaga |
| `_search_live_api(query)` | query: str | str \| None | Busca live na API interna do YouTube |

**Rotas semânticas** (`routers/youtube.py`):

| Padrão | Ação |
|--------|------|
| "parar" + "youtube/audio/video/musica/podcast/live" | `play_youtube(action="stop")` |

---

## Resolução de Problemas

### Spotify não conecta
1. Vá no Dashboard → Configurações → Spotify
2. Desconecte e conecte novamente
3. Verifique se sua conta tem Premium (necessário para controle)

### YouTube não toca áudio
1. Verifique se o yt-dlp está instalado: `pip show yt-dlp`
2. Verifique se o player (mplayer/vlc) está disponível no sistema
3. Confira os logs: `alfredo.log`

### Comando não vai para YouTube
Se você disser "toca [algo]" sem mencionar "youtube", pode cair no Spotify. Use:
- Explícito: "no YouTube"
- Contexto: "live", "podcast", "canal" (palavras-chave que forçam YouTube)
