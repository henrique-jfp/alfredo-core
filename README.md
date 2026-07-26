<div align="center">

# 🎩 Alfredo OS

### O Sistema Operacional Doméstico Inteligente, Agêntico e "Custo Zero"

*Um mordomo digital que vive na nuvem, mas mora na sua casa.*

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_3.1_Flash_Lite-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_Whisper_Large_V3-F55036?style=for-the-badge&logo=groq&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20produção-success?style=for-the-badge)

</div>

---

## 📖 Sobre o Projeto

**Alfredo OS** é um ecossistema completo de assistente doméstico inteligente, construído do zero para rodar em hardware modesto (um Celeron de segunda mão) sem abrir mão de uma experiência de voz fluida, contextual e "agêntica" — no mesmo espírito de uma Alexa ou Google Home, mas 100% autoral, extensível e sem *vendor lock-in*.

O projeto nasceu de uma premissa simples: **um computador fraco não precisa gerar um assistente fraco.** Toda a inteligência pesada (transcrição, raciocínio, síntese de voz) é delegada a APIs de nuvem gratuitas ou de altíssimo custo-benefício, enquanto o servidor local atua apenas como orquestrador de tráfego, mantendo a latência baixa e o custo operacional próximo de zero.

---

## 📑 Sumário

- [Filosofia de Arquitetura](#-filosofia-de-arquitetura-agentic-first)
- [Como Funciona uma Interação](#-como-funciona-uma-interação-fim-a-fim)
- [Ferramentas Nativas (Tools/Skills)](#️-ferramentas-nativas-toolsskills)
- [Arquitetura de Hardware](#️-arquitetura-de-hardware)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Stack Tecnológica](#-stack-tecnológica)
- [Instalação e Deploy](#-instalação-e-deploy)
- [Configuração](#️-configuração)
- [Dashboard de Administração](#-dashboard-de-administração)
- [Roadmap](#️-roadmap)
- [Contribuindo](#-contribuindo)

---

## 🧠 Filosofia de Arquitetura "Agentic-First"

Alfredo abandona o modelo clássico de assistentes engessados por árvores de "palavras-chave" e *intents* fixos. Em vez disso, ele opera sob três pilares:

### 1. Roteamento em 3 Camadas para Latência Mínima

Cada frase do usuário passa por um **pipeline de decisão progressivo**, onde cada nível é mais rápido que o anterior:

| Camada | Tecnologia | Latência | Finalidade |
|--------|-----------|----------|------------|
| **1 — Semantic Router** | Regex local (8 módulos) | **< 5ms** | Comandos diretos: TV, timer, smart home, listas, música, clima, calendário |
| **2 — Groq Fast Path** | `llama-3.3-70b-versatile` | **~300ms** | Conversas simples sem tools: saudações, piadas, conhecimento geral, agradecimentos |
| **3 — Gemini Tool Calling** | `gemini-3.1-flash-lite` | **~2-3s** | Decisões complexas com function calling, RAG, sessões multi-turn |

Quando uma camada consegue responder, as seguintes são puladas — resultando em respostas instantâneas para a maioria dos comandos do dia a dia.

### 2. Pipeline de Streaming Real (3 Estágios)

A resposta de voz nunca espera o LLM terminar de pensar:

```
LLM tokens → Stage 1: enfileira frases completas
                  ↓
Stage 2: TTS sintetiza cada frase imediatamente (Edge-TTS ou Piper)
                  ↓
Stage 3: chunks de áudio são yield para o satélite em paralelo
```

Resultado: o **TTFA (Time-To-First-Audio)** chega a menos de 1 segundo, mesmo para respostas longas.

### 3. Satélites "burros" e captura híbrida de áudio

Os dispositivos espalhados pela casa funcionam estritamente como interfaces de I/O, sem inteligência própria:
- **OpenWakeWord** (ou Vosk) cuida exclusivamente da *wake word*, offline, sem consumir rede;
- Ao ser acionada, a gravação é controlada por **WebRTC VAD + filtro RMS**, que detecta o fim da frase com precisão;
- Um **pipeline único de áudio** via `sounddevice` elimina conflitos de dispositivo (ALSA) e processos zumbis.

### 4. Nuvem inteligente, custo próximo de zero

O hardware local atua apenas como orquestrador, delegando todo o processamento pesado:

| Etapa | Tecnologia | Observação |
|---|---|---|
| **STT** (fala → texto) | Whisper-Large-V3 via **Groq API** | Inferência ultrarrápida, com fallback para Gemini 1.5 Flash |
| **Raciocínio rápido** | **Groq** (`llama-3.3-70b`) | Fast path para queries conversacionais (~300ms) |
| **Raciocínio / Tool Calling** | **Gemini 3.1 Flash Lite** | Suporte nativo a function calling, RAG e sessões |
| **Resiliência de quota** | Round-Robin nativo de múltiplas API keys | Contorna rate limits sem custo extra |
| **TTS** (texto → fala) | **Microsoft Edge TTS** (vozes neurais) | Cache em memória + disco; 3 estágios de streaming |
| **TTS Local** (fallback) | **Piper TTS** | Síntese offline, sem dependência de nuvem |

---

## 🔄 Como Funciona uma Interação (Fim a Fim)

```
🎙️ Satélite detecta wake word (OpenWakeWord / Vosk, offline)
         │
         ▼
🗣️ VAD + RMS detectam início/fim da fala e capturam o áudio
         │
         ▼
☁️ Áudio enviado ao servidor via WebSocket (/api/ws/satellite/{id})
         │
         ▼
📝 STT via Groq Whisper Large V3 transcreve a fala (ou Vosk local)
         │
         ▼
╔═══════════════════════════════════════════════════════╗
║              ROTEADOR AGÊNTICO (3 NÍVEIS)            ║
║                                                       ║
║  NÍVEL 1 — Semantic Router (Regex, < 5ms)             ║
║  ├── TV, timer, smart home, listas, clima, música     ║
║  ├── YouTube, calendário → resposta direta            ║
║  └── Se não bater → cai para Nível 2                  ║
║                                                       ║
║  NÍVEL 2 — Groq Fast Path (llama-3.3-70b, ~300ms)    ║
║  ├── Saudações, piadas, conhecimento geral            ║
║  └── Se falhar ou tool necessária → cai para Nível 3  ║
║                                                       ║
║  NÍVEL 3 — Gemini Tool Calling (~2-3s)                ║
║  ├── Decide qual tool chamar (0, 1 ou N)              ║
║  ├── Injeta contexto: RAG, memórias, sessão ativa     ║
║  └── Executa Skill e retorna resposta                 ║
╚═══════════════════════════════════════════════════════╝
         │
         ▼
⚙️ Skills executam ações (Spotify, TV, Home Assistant, Clima...)
         │
         ▼
💬 Resposta em linguagem natural gerada
         │
         ▼
╔═══════════════════════════════════════════════════════╗
║              PIPELINE DE STREAMING REAL               ║
║  Stage 1: LLM → fila de frases completas              ║
║  Stage 2: Frases → áudio (Edge-TTS com cache)         ║
║  Stage 3: Chunks de áudio → WebSocket → satélite      ║
╚═══════════════════════════════════════════════════════╝
         │
         ▼
📡 Satélite reproduz áudio no alto-falante
```

---

## 🛠️ Ferramentas Nativas (Tools/Skills)

O agente decide sozinho quando e como acionar cada skill. Atualmente são **19 skills** registradas:

### 🏠 Automação e Casa Inteligente
| Skill | Descrição |
|---|---|
| 💡 **SmartHomeTool** | Integração completa com **Home Assistant** — controle de luzes, ventiladores, tomadas por cômodo. Comando offline direto (`/api/smart-home/offline`) sem passar pelo LLM. |
| 📺 **TVTool** | Controle completo de TVs Samsung: ligar/desligar (SmartThings + WOL), volume absoluto (SmartThings), mute/unmute, abertura de apps (Netflix, YouTube, Globoplay, Disney+...), troca de canais (antena e Claro tv+), seleção de fonte HDMI. Suporta múltiplos cômodos. |
| ⏱️ **TimerTool** | Cronômetros, alarmes e lembretes com alerta sonoro. Suporta avisos por cômodo ou broadcast. |

### 🎵 Entretenimento e Mídia
| Skill | Descrição |
|---|---|
| 🎵 **MusicTool** | Spotify Connect nativo via daemon `spotifyd` — tocar, pausar, pular, volume. Fallback para YouTube via `yt-dlp` quando não há dispositivo Spotify disponível. |
| ▶️ **YouTubeTool** | Reprodução de áudio do YouTube — lives (CazéTV, GloboNews), podcasts, conteúdo fora do Spotify. |
| 📰 **NewsTool** | Manchetes do Brasil e do mundo por categoria via NewsAPI. |
| 🎬 **MediaTool** | Recomendações de filmes e séries via TMDB (gênero, ano/década). |
| 📖 **BookReadingTool** | Alfredo Reads: Leitura interativa de ebooks (PDF/EPUB) com efeitos sonoros e mudanças de voz (Gemini + Edge-TTS) sincronizados com o texto. |

### 🧠 Memória e Produtividade
| Skill | Descrição |
|---|---|
| 🧠 **MemoryTool** | Memória de longo prazo com **RAG (embedding + cosine similarity)** — Alfredo memoriza fatos, alergias, preferências e injeta contexto relevante em respostas futuras. |
| 📝 **ListTool** | Listas de compras e tarefas com suporte a listas específicas (ex: `compras_churrasco`). Envio por Telegram. |
| 📅 **CalendarTool** | Agenda completa: leitura, adição, remoção e reagendamento com suporte a **datas em português** (`amanhã`, `depois de amanhã`, `próxima terça`, `daqui a 3 dias`, `mês que vem`). Múltiplos lembretes (`1 hora, 15 min e 5 min antes`). Detecção de conflitos. Sincronia bidirecional com Google Calendar via OAuth 2.0. |
| 🔄 **RoutineTool** | Criação/edição/exclusão de rotinas agendadas por voz (`"Toda segunda às 7h acende a luz do quarto"`). |

### 🧭 Utilidades Gerais
| Skill | Descrição |
|---|---|
| 🕒 **TimeTool** | Hora e data atuais. |
| 🌤️ **WeatherTool** | Previsão do tempo atual e estendida (até 5 dias) via Open-Meteo. Cache em banco. |
| 🚗 **TrafficTool** | Tempo de deslocamento entre origens e destinos salvos via Google Maps API. |
| 🌍 **TranslateTool** | Tradução entre idiomas e mini-aulas de idiomas (`"Como se fala obrigado em inglês?"`). |

### 🎓 Habilidades Especiais
| Skill | Descrição |
|---|---|
| 🍳 **RecipeTool** | Receitas passo a passo com sessão persistida em banco (pausa segura por horas) e harmonização de vinhos. |
| ☁️ **DreamTool** | Diário de sonhos com extração de temas e nuvem de palavras animada no Dashboard. |
| 🏫 **QuizTool** | Modo tarefa escolar — quizzes interativos com avaliação e persistência de sessão. |

### 💬 Conversação Nativa
Quando nenhuma ferramenta é necessária, Alfredo usa seu conhecimento geral para bater papo, responder dúvidas, traduzir textos ou contar piadas — tudo via **Groq Fast Path** em ~300ms, sem acionar o Gemini.

---

## 🖥️ Arquitetura de Hardware

A topologia física do Alfredo é organizada em dois papéis distintos: o **Nó Central** (fixo na sala) e os **Satélites Burros** (espalhados pelos cômodos).

### 🧠 Nó Central — Servidor + Satélite
Um único equipamento na parede da sala acumula dois papéis:
- **Cérebro/Servidor:** API FastAPI, roteador agêntico, banco SQLite;
- **Satélite local:** microfone e alto-falante próprios (a sala não fica "surda");

| Item | Especificação |
|---|---|
| Hardware | HP Pavilion x360 11-N226BR |
| CPU | Intel Celeron N2830 Dual-Core 2.16GHz |
| RAM | 4GB DDR3L + ZRAM |
| Microfone | Ps3 Eye (array de 4 mics) |
| SO | Ubuntu Server 26.04 LTS |
| Papel | Roteador de rede + API + banco + captura de voz + dashboard local |

### 📡 Satélites (demais cômodos)
Captam áudio via wake word local + VAD e reproduzem a resposta, delegando 100% do raciocínio ao Nó Central.

O servidor é **agnóstico a hardware** — reage exclusivamente às *capabilities* declaradas no registro do dispositivo.

#### 🛏️ Quarto do Casal (Satélite Android Fixo)
| Item | Especificação |
|---|---|
| Hardware | Samsung M21s (reaproveitado) |
| Áudio | Caixa externa via P2 |
| Software | Python (Termux) + OpenWakeWord + WebRTC VAD |

> Basta implementar o protocolo HTTP/WS padrão em qualquer dispositivo com microfone e alto-falante — zero alterações no servidor.

---

## 📁 Estrutura do Projeto

```
alfredo-core/
├── core/                          # Motor principal em Python
│   ├── api/                        # FastAPI: endpoints REST/WS
│   │   ├── main.py                  # App principal, startup, rotas globais
│   │   ├── dashboard.py             # API do dashboard (stats, CRUD, config)
│   │   ├── satellite.py             # WebSocket + REST dos satélites
│   │   ├── spotify.py               # Auth OAuth do Spotify
│   │   ├── tv.py                    # CRUD de configurações de TV
│   │   ├── smart_home.py            # CRUD de cômodos + devices + offline control
│   │   ├── google_auth.py           # OAuth do Google Calendar
│   │   └── schemas.py               # Schemas Pydantic
│   ├── brain/                       # Cérebro agêntico
│   │   ├── router.py                 # Roteador principal (3 níveis)
│   │   ├── semantic_router.py        # Roteador regex ultrarrápido (<5ms)
│   │   ├── routers/                  # Definições de rotas
│   │   │   ├── tv.py, timer.py, music.py, lists.py
│   │   │   ├── weather_time.py, calendar.py, youtube.py
│   │   │   └── smart_home.py
│   │   ├── skills/                   # 19 Skills (Weather, Timer, TV, Music, Books...)
│   │   │   ├── base.py               # Interface base Skill
│   │   │   └── *.py                  # Implementações
│   │   └── memory/                   # Banco de dados
│   │       ├── database.py            # SQLite + SQLAlchemy engine
│   │       └── models.py              # 15 modelos (Device, Interaction, Event...)
│   ├── services/                    # Serviços de integração
│   │   ├── key_manager.py            # Round-robin + cooldown de API keys
│   │   ├── spotify_service.py        # Spotify Connect (Spotipy)
│   │   ├── samsung_tv.py             # SmartThings + SamsungTVWS + WOL
│   │   ├── home_assistant.py         # Home Assistant REST
│   │   ├── calendar_service.py       # Calendário local (timezone, queries)
│   │   ├── google_calendar.py        # Google Calendar OAuth + sync
│   │   ├── weather_service.py        # Open-Meteo com cache
│   │   ├── youtube_service.py        # yt-dlp
│   │   ├── embedding_service.py      # Embeddings para RAG
│   │   ├── scheduler.py              # Loop de timers, eventos, rotinas
│   │   ├── env_manager.py            # Gerenciamento de .env
│   │   └── mail_service.py           # Serviço de e-mail
│   └── voice/                       # Pipeline de voz
│       ├── pipeline.py               # Streaming 3 estágios (LLM→frases→áudio)
│       ├── stt/
│       │   └── engine.py             # Groq Whisper / Vosk / Gemini fallback
│       └── tts/
│           └── engine.py             # Edge-TTS / Piper com cache
├── devices/                         # Implementações de satélites
│   ├── satellite_server/             # Linux (OpenWakeWord + VAD)
│   └── satellite_desktop/            # Desktop (Vosk + VAD)
├── dashboard/                       # Painel web (React)
│   ├── frontend/                     # Build estático (montado em /)
│   └── newdashboard/                 # Nova interface React (Vite + TS)
├── config/                          # Configurações auxiliares
│   └── .env.example                  # Exemplo de variáveis de ambiente
├── scripts/                         # Utilitários
│   ├── db_tools/                     # Migrações, queries, fixes
│   ├── seed_rooms.py, setup_spotify.py, mock_satellite.py
│   └── test_*.py                    # Scripts de teste avulsos
├── tests/                           # Testes automatizados
├── docs/                            # Documentação
├── deploy/                          # Scripts de instalação
│   ├── install.sh
│   └── update.sh
├── tmp/                             # Áudio temporário (gitignorado)
├── config.yml                       # Cloudflare Tunnel ingress
├── requirements.txt                 # Dependências Python
├── start.sh / restart.sh            # Scripts de execução
└── .env                             # Configuração sensível (não versionado)
```

---

## 🧰 Stack Tecnológica

**Backend & IA**
- `FastAPI` + `uvicorn[standard]` + `websockets` — API REST e comunicação em tempo real
- `google-generativeai` — Gemini 3.1 Flash Lite (tool calling, RAG)
- `groq` — Whisper-Large-V3 (STT) + llama-3.3-70b (fast path conversacional)
- `edge-tts` — Síntese de voz neural (cloud, com cache em memória + disco)
- `piper-tts` — Síntese de voz local (fallback opcional)
- `SQLAlchemy` — ORM com SQLite (WAL mode, pool de conexões)

**Áudio e Voz**
- `sounddevice`, `soundfile`, `numpy` — Captura e processamento de áudio
- `webrtcvad` — Detecção de atividade de voz (VAD) modo agressivo
- `openwakeword` — Wake word offline no satélite server
- `vosk` — Wake word / STT local (fallback)

**Integrações**
- `spotipy` — Controle do Spotify Connect
- `samsungtvws`, `wakeonlan` — Controle de TVs Samsung
- `requests` / `httpx` — Chamadas HTTP (Home Assistant, SmartThings, Telegram, APIs)
- `yt-dlp` — Extração de áudio do YouTube
- `google-api-python-client`, `google-auth-oauthlib` — Google Calendar OAuth 2.0
- `python-dotenv` — Carregamento de variáveis de ambiente
- `pydantic` — Validação de schemas
- `dateparser` — Parsing de datas em português (`search_dates`)
- Cloudflare Tunnel — Exposição segura da API sem port forwarding

---

## 🚀 Instalação e Deploy

### Pré-requisitos
- Linux baseado em Debian/Ubuntu (recomendado: Ubuntu Server 24.04+)
- Acesso à internet
- Chaves de API gratuitas do **Groq** e do **Google Gemini**

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/henrique-jfp/alfredo-core.git
cd alfredo-core

# 2. Execute o instalador automático
chmod +x deploy/install.sh
./deploy/install.sh
```

O script cuida de:
1. Instalar dependências de sistema (Python3, pip, venv);
2. Criar o ambiente virtual e instalar `requirements.txt`;
3. Baixar modelos offline (Vosk, Piper) se configurados;
4. Guiar a criação interativa do arquivo `.env` (na raiz do projeto);
5. Registrar os serviços `alfredo-api.service` e `alfredo-satellite.service` no `systemd`.

```bash
# 3. Ajuste fino das variáveis de ambiente no .env (raiz do projeto)
nano .env

# 4. Inicie os serviços
sudo systemctl start alfredo-api.service
sudo systemctl start alfredo-satellite.service

# 5. Acompanhe os logs
sudo journalctl -u alfredo-api.service -f
```

### Execução manual (modo desenvolvimento)
```bash
./start.sh     # sobe API (uvicorn), satélite local e spotifyd
./restart.sh   # reinicia os processos
```

---

## ⚙️ Configuração

Toda configuração sensível vive no arquivo `.env` na raiz do projeto (nunca versionado). Um exemplo está em `config/.env.example`.

**Chaves de API:**
- `GEMINI_API_KEYS` — Uma ou mais chaves Gemini (separadas por vírgula, round-robin automático)
- `GROQ_API_KEYS` — Uma ou mais chaves Groq

**Integrações:**
- `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN` — URL e token do Home Assistant
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` — Credenciais Spotify (OAuth)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Credenciais Google Calendar (OAuth)
- `PUBLIC_URL` — URL pública (para callback OAuth via Cloudflare Tunnel)
- `GOOGLE_MAPS_API_KEY` — Para a skill de trânsito
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Para envio de listas por Telegram

**Áudio:**
- `STT_BACKEND` — `groq` (padrão) ou `vosk`
- `TTS_BACKEND` — `edge` (padrão) ou `piper`

Consulte `docs/INSTALL.md` para o guia completo de provisionamento.

---

## 📊 Dashboard de Administração

O diretório `dashboard/` contém o painel web acessível via navegador (montado na raiz `/` do servidor):

- **Overview** — Status da API, satélites conectados, KPIs
- **Inteligência** — Memórias, métricas de IA (tokens, latência, RPM)
- **Satélites** — Dispositivos registrados, volume, brilho, online/offline
- **Calendário** — Visão semanal com navegação por datas
- **Rotinas** — CRUD de automações agendadas
- **Listas** — Compras e tarefas
- **Integrações** — Spotify, Google Calendar, TV
- **Sonhos** — Diário com nuvem de palavras
- **Dispositivos** — Cômodos e smart devices (Home Assistant)
- **Configurações** — Voz do assistente, nome, API keys

Há duas gerações: `frontend/` (build estável atual, servida em produção) e `newdashboard/` (React/Vite/TypeScript, em evolução).

### 🔐 Google Calendar (OAuth 2.0)

1. **Adicione a redirect URI** no [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
   ```
   https://seudominio.com/api/auth/google/callback
   http://localhost:10001/api/auth/google/callback
   ```
2. **Autorize** acessando: `GET /api/auth/google/authorize`
3. O servidor inicia sincronia automática a cada 5 minutos.

---

## 🗺️ Roadmap

### ✅ Implementado
- [x] Roteamento em 3 camadas (Semantic Router + Groq Fast Path + Gemini Tool Calling)
- [x] Pipeline de streaming real (LLM → frases → áudio em paralelo)
- [x] 19 skills nativas (Ebooks, TV, Smart Home, Música, YouTube, Clima, Listas, Timer, Agenda...)
- [x] Google Calendar Sync — bidirecional via OAuth 2.0 (push/pull a cada 5 min)
- [x] Memória de longo prazo com RAG (embedding + cosine similarity)
- [x] SmartThings para controle absoluto de TV (mute, volume, power on/off)
- [x] Suporte a múltiplas chaves Gemini/Groq com round-robin e cooldown
- [x] Dashboard React com 10 abas de gerenciamento
- [x] Wake word offline (OpenWakeWord e Vosk)
- [x] Sincronia Spotify + fallback YouTube
- [x] Scheduler de timers, eventos e rotinas
- [x] Satélites Android (Termux) e Desktop
- [x] Home Assistant — controle de dispositivos inteligentes
- [x] Endpoint offline de smart home (bypass do LLM)

### 🔜 Em andamento / Planejado
- [ ] OCR / câmera para disparar fotos a cada 10 minutos para detectar se tem humano no ambiente
- [ ] Suporte a múltiplos usuários com perfis de voz
- [ ] Modo hóspede (privacidade limitada)
- [ ] Skill de lembretes geolocalizados (ex: "me lembre de comprar leite quando chegar no mercado")

Consulte `docs/ALFREDO_CHECKLIST.md` para o backlog completo.

---

## 🤝 Contribuindo

Este é um projeto pessoal em evolução constante, mas sugestões, issues e PRs são bem-vindos. Ao contribuir:
1. Abra uma *issue* descrevendo o problema ou a ideia;
2. Siga a organização modular existente — novas skills vão em `core/brain/skills/`;
3. Execute os testes em `tests/` antes de abrir um PR.

---

<div align="center">

*Desenvolvido com ❤️ sob os princípios de simplicidade, resiliência e "custo zero".*

</div>
