<div align="center">

# 🎩 Alfredo OS

### O Sistema Operacional Doméstico Inteligente, Agêntico e "Custo Zero"

*Um mordomo digital que vive na nuvem, mas mora na sua casa.*

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32--S3-E7352C?style=for-the-badge&logo=espressif&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow?style=for-the-badge)

</div>

---

## 📖 Sobre o Projeto

**Alfredo OS** é um ecossistema completo de assistente doméstico inteligente, construído do zero para rodar em hardware modesto (um Celeron de segunda mão) sem abrir mão de uma experiência de voz fluida, contextual e "agêntica" — no mesmo espírito de uma Alexa ou Google Home, mas 100% autoral, extensível e sem *vendor lock-in*.

O projeto nasceu de uma premissa simples: **um computador fraco não precisa gerar um assistente fraco.** Toda a inteligência pesada (transcrição, raciocínio, síntese de voz) é delegada a APIs de nuvem gratuitas ou de altíssimo custo-benefício, enquanto o servidor local atua apenas como orquestrador de tráfego, mantendo a latência baixa e o custo operacional próximo de zero.

> 💡 Se você quer entender o "porquê" por trás de cada decisão técnica, veja a seção [Filosofia de Arquitetura](#-filosofia-de-arquitetura-agentic-first) abaixo.

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

### 1. Cérebro Agente, não um roteador de regras
O **Gemini 2.5 Flash** não é usado como "fallback" quando tudo mais falha — ele é o **roteador principal** do sistema. Cada frase do usuário é interpretada contextualmente pelo modelo, que decide autonomamente:
- Se nenhuma ferramenta é necessária (conversa livre, dúvidas gerais, tradução, piadas);
- Qual ferramenta (ou combinação de ferramentas) deve ser invocada;
- Como encadear múltiplas *tool calls* em uma única solicitação ("Toque uma música e apague as luzes").

### 2. Satélites "burros" e captura híbrida de áudio
Os dispositivos espalhados pela casa (ou o próprio servidor com microfone local) funcionam estritamente como interfaces de I/O, sem inteligência própria:
- **Vosk** (reconhecimento offline e leve) cuida exclusivamente da *wake word*, sem consumir rede nem enviar áudio contínuo para a nuvem;
- Ao ser acionada, a gravação é controlada por **WebRTC VAD + filtro RMS**, que detecta o fim da frase com precisão e corta ruídos de fundo (ventiladores, estática);
- Um **pipeline único de áudio** via `sounddevice` elimina conflitos de dispositivo (ALSA) e processos zumbis — problema clássico em soluções caseiras baseadas em `arecord`/`aplay` soltos.

### 3. Nuvem inteligente, custo próximo de zero
O hardware local (mesmo um Celeron fraco) atua apenas como orquestrador de rede, delegando todo o processamento pesado:

| Etapa | Tecnologia | Observação |
|---|---|---|
| **STT** (fala → texto) | Whisper-Large-V3 via **Groq API** | Velocidade de inferência extremamente alta |
| **Raciocínio / Roteamento** | **Gemini 2.5 Flash** | Suporte nativo a *tool/function calling* |
| **Resiliência de quota** | Round-Robin nativo de múltiplas API keys Gemini | Contorna o limite de RPM (`429 Quota Exceeded`) sem custo extra |
| **TTS** (texto → fala) | **Microsoft Edge TTS** (vozes neurais `FranciscaNeural`, `AntonioNeural`, `DuarteNeural`...) | 100% nuvem, resposta quase instantânea |

---

## 🔄 Como Funciona uma Interação (Fim a Fim)

```
🎙️ Satélite ouve a wake word (Vosk, offline)
        │
        ▼
🗣️ VAD + RMS detectam início/fim da fala e capturam o áudio
        │
        ▼
☁️ Áudio enviado ao servidor central (FastAPI / WebSocket)
        │
        ▼
📝 STT via Groq (Whisper-Large-V3) transcreve a fala
        │
        ▼
🧠 Router Agêntico (Gemini 2.5 Flash) interpreta o texto
        │
        ├── Decide chamar 0, 1 ou N Tools (Skills) em paralelo/sequência
        │        │
        │        ▼
        │   ⚙️ Skills executam (Home Assistant, Spotify, Clima, Memória...)
        │
        ▼
💬 Resposta final é sintetizada em linguagem natural
        │
        ▼
🔊 TTS via Edge TTS gera o áudio da resposta
        │
        ▼
📡 Áudio devolvido ao satélite, que reproduz no alto-falante físico
```

---

## 🛠️ Ferramentas Nativas (Tools/Skills)

O agente Gemini tem acesso livre ao catálogo de *skills* abaixo e decide sozinho quando e como acioná-las.

### 🏠 Automação e Casa Inteligente
| Skill | Descrição |
|---|---|
| 💡 **SmartHomeTool** | Integração completa com o **Home Assistant** — descobre todos os dispositivos da casa e controla luzes, TVs, ares-condicionados e interruptores de forma natural (*"Apague a luz da sala e ligue a TV"*). |
| ⏱️ **TimerTool** | Criação de cronômetros, alarmes e lembretes exatos, com alerta sonoro disparado no alto-falante físico do satélite. |

### 🎵 Entretenimento e Mídia
| Skill | Descrição |
|---|---|
| 🎵 **MusicTool** | Spotify Connect nativo via daemon próprio (`spotifyd`) — comandos diretos (*"Toque The Beatles"*, *"Próxima"*, *"Pause"*, *"Volume máximo"*) sem depender de celular pareado. Fallback de segurança via YouTube (`yt-dlp`). |
| ▶️ **YouTubeTool** | Reprodução independente de áudio do YouTube — lives (CazéTV, GloboNews), podcasts (Flow, Podpah), músicas fora do Spotify. Usa `yt-dlp` + busca com *scoring* por similaridade de canal para transmissões ao vivo. |
| 📰 **NewsTool** | Manchetes recentes e notícias de última hora do Brasil e do mundo, via NewsAPI. |

### 🧠 Memória e Produtividade
| Skill | Descrição |
|---|---|
| 🧠 **MemoryTool** | Memória de longo prazo persistente — Alfredo memoriza fatos vitais do usuário (alergias, hábitos, preferências) e injeta esse contexto *always-on* silenciosamente em respostas futuras. |
| 📝 **ListTool** | Gerenciamento de listas de compras e tarefas (*"Adicione pão na minha lista de mercado"*). |
| 📅 **CalendarTool** | Agenda completa com leitura por voz (`"O que tenho amanhã?"`), adição (`"Marque dentista próxima terça às 14h"`), **reagendamento** (`"Move a reunião para quinta"` / `"Adia em 30 minutos"`), **cancelamento inteligente** (pergunta qual quando há múltiplos), **múltiplos lembretes** (`"Me lembre 1 hora, 15 min e 5 min antes"`), **detecção de conflitos** (`"Você já tem dentista às 14h"`), **datas naturais** (`"depois de amanhã"`, `"daqui a 3 dias"`, `"mês que vem"`, `"próxima terça"`), **sincronia bidirecional com Google Calendar** (OAuth + push/pull automático a cada 5 min), e **dashboard visual** com visão semanal. |

### 🧭 Utilidades Gerais
| Skill | Descrição |
|---|---|
| 🕒 **TimeTool** | Hora e data com base no fuso horário do servidor. |
| 🌤️ **WeatherTool** | Previsão do tempo local e global, via Open-Meteo. |
| 🚗 **TrafficTool** | Tempo de deslocamento em tempo real com coordenadas GPS, via Mapbox. |

### 🎓 Habilidades Especiais
| Skill | Descrição |
|---|---|
| 🍳 **RecipeTool** | Guia receitas culinárias passo a passo, com contexto persistido em banco (pausa segura por horas) e harmonizações de vinhos/queijos. |
| ☁️ **DreamTool** | Diário psicanalítico de sonhos — extrai semântica dos relatos e exibe uma nuvem de palavras animada no Dashboard. |
| 🏫 **QuizTool** | Modo tarefa escolar — quizzes interativos de matemática e história, avaliação verbal das respostas e estado de sessão persistido em banco. |

### 💬 Conversação Nativa
Quando nenhuma ferramenta é necessária, Alfredo usa seu conhecimento geral para bater papo, responder dúvidas complexas, traduzir textos ou contar piadas de forma fluida.

---

## 🖥️ Arquitetura de Hardware

A topologia física do Alfredo é organizada em dois papéis distintos: o **Nó Central** (fixo na sala) e os **Satélites Burros** (espalhados pelos cômodos).

### 🧠 Nó Central — Servidor + Satélite + Dashboard (sala)
Diferente de uma arquitetura clássica de "hub escondido + dispositivos na casa", o Alfredo concentra tudo em um único equipamento fixado na parede da sala, acumulando três papéis ao mesmo tempo:
- **Cérebro/Servidor:** roda a API FastAPI, o roteador agêntico (Gemini) e o banco de dados;
- **Satélite local:** tem microfone e alto-falante próprios, funcionando como mais um ponto de captura de voz da casa (a sala não fica "surda" só porque o servidor está lá);
- **Dashboard físico:** a tela fica exposta na parede, exibindo o painel **"Obsidian & Brass"** (status, rotinas, nuvem de sonhos etc.) como uma espécie de "quadro inteligente" central da casa.

| Item | Especificação |
|---|---|
| Hardware | HP Pavilion x360 11-N226BR |
| CPU | Intel Celeron N2830 Dual-Core 2.16GHz |
| RAM | 4GB DDR3L + ZRAM |
| Microfone | Ps3 Eye(array de 4 mics) |
| SO | Ubuntu Server 26.04 LTS (Resolute) |
| Papel | Roteador de tráfego de rede, API FastAPI, banco SQLite, **e** captura de voz + exibição do dashboard local. Nenhum processamento pesado de áudio/IA roda localmente — tudo é delegado à nuvem (ver [Filosofia de Arquitetura](#-filosofia-de-arquitetura-agentic-first)). |

> Como o x360 tem tela sensível ao toque e dobra 360°, ele se presta bem a ficar "pregado" na parede em modo *tablet*, servindo de tela fixa para o dashboard sem hardware extra.

### 📡 Satélites Burros (demais cômodos)
Os outros cômodos recebem satélites **sem inteligência própria** — apenas captam áudio (wake word local via Vosk + VAD) e reproduzem a resposta, delegando 100% do raciocínio ao Nó Central pela rede.

> ⚠️ **Hardware ainda em avaliação.** O `DeepSeek AI Voice Robot Ball (ESP32-S3)` abaixo foi o primeiro candidato prototipado, mas não é uma decisão fechada — outras opções (ESP32 genérico, M5Stack, Raspberry Pi Zero, alto-falantes reaproveitados) seguem sendo avaliadas cômodo a cômodo.

| Item | Especificação (protótipo avaliado) |
|---|---|
| Hardware | DeepSeek AI Voice Robot Ball (ESP32-S3 WROOM-1-N16R8) |
| Display | 1.28" 240×240 IPS (GC9A01) |
| Touch | CST816 (I2C) |

> O servidor é **agnóstico a hardware**: ele reage exclusivamente às *capabilities* que o satélite declara no momento do registro. Isso é o que torna essa indefinição segura — qualquer que seja a escolha final por cômodo (ou até escolhas diferentes por cômodo), basta implementar o `shared-protocol` em `firmware/` — zero alteração no servidor.

---

## 📁 Estrutura do Projeto

```
alfredo-core/
├── core/                    # Motor principal em Python
│   ├── api/                  # FastAPI: endpoints REST/WebSocket, satélites, Spotify, TV, dashboard
│   ├── brain/                 # Cérebro agêntico
│   │   ├── router.py           # Roteador principal (Gemini 2.5 Flash + tool calling)
│   │   ├── skills/              # Implementação de cada Tool (Music, Weather, Memory, Recipe...)
│   │   ├── memory/              # Persistência de memória de longo prazo (SQLAlchemy)
│   │   └── context/              # Gerenciamento de contexto conversacional
│   ├── services/               # Serviços auxiliares compartilhados
│   └── voice/                   # Pipeline de voz
│       ├── stt/                   # Speech-to-Text (Groq / Whisper)
│       └── tts/                   # Text-to-Speech (Edge TTS / Piper)
├── firmware/                  # Código-fonte C++ (ESP-IDF / PlatformIO) dos satélites
│   ├── satellite-deepseek-ball/    # Firmware do robô-bola ESP32-S3 (um dos protótipos avaliados)
│   └── shared-protocol/             # Especificação do protocolo HTTP/WS multi-hardware
├── devices/                   # Gerenciamento e monitoramento de saúde dos satélites
├── integrations/               # Conectores externos
│   └── homeassistant/, music/, weather/, calendar/, contacomigo/, ai_fallback/
├── dashboard/                  # Painel web de administração ("Obsidian & Brass")
│   ├── frontend/                # Interface legada
│   ├── newdashboard/             # Nova interface (React)
│   └── backend/                  # API de suporte ao dashboard
├── deploy/                     # Scripts de instalação e atualização (install.sh, update.sh)
├── scripts/                    # Utilitários operacionais (satélite local, diagnóstico de mic, migrações...)
├── docs/                       # Documentação funcional, guias e onboarding de clientes
├── tests/                      # Testes automatizados
├── config/                     # Configuração de ambiente (.env)
├── requirements.txt             # Dependências Python do servidor
├── start.sh / restart.sh         # Scripts de execução em produção (screen sessions)
└── config.yml                   # Configuração do túnel Cloudflare (ingress)
```

---

## 🧰 Stack Tecnológica

**Backend & IA**
- `FastAPI` + `uvicorn[standard]` + `websockets` — API e comunicação em tempo real com satélites
- `google-generativeai` — Gemini 2.5 Flash (roteador agêntico / tool calling)
- `groq` — Whisper-Large-V3 (STT ultrarrápido)
- `edge-tts` — Síntese de voz neural na nuvem (com suporte opcional a `piper-tts` local)
- `SQLAlchemy` — Persistência de memória, listas, timers e sessões

**Áudio e Voz**
- `sounddevice`, `soundfile`, `numpy` — Captura e processamento de áudio em pipeline único
- `webrtcvad` — Detecção de atividade de voz (VAD)
- `vosk` — Reconhecimento offline da *wake word*

**Integrações**
- `spotipy` + `spotifyd` — Controle nativo do Spotify Connect
- `yt-dlp` — Extração de áudio do YouTube (fallback de música e lives)
- `httpx` / `requests` — Chamadas HTTP a serviços externos (clima, trânsito, notícias, Home Assistant)
- `samsungtvws`, `wakeonlan` — Controle de TVs Samsung
- `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` — Sincronia bidirecional com Google Calendar
- Cloudflare Tunnel — Exposição segura da API sem *port forwarding*

**Firmware**
- ESP-IDF / PlatformIO em C++ para os satélites ESP32-S3

---

## 🚀 Instalação e Deploy

### Pré-requisitos
- Linux baseado em Debian/Ubuntu (recomendado: Ubuntu Server 24.04+)
- Acesso à internet para download de pacotes e modelos
- Chaves de API gratuitas do **Groq** e do **Google Gemini**

### Passo a passo

```bash
# 1. Clone o repositório na máquina de destino
git clone https://github.com/henrique-jfp/alfredo-core.git
cd alfredo-core

# 2. Execute o instalador automático
chmod +x deploy/install.sh
./deploy/install.sh
```

O script cuida de:
1. Instalar dependências de sistema (Python3, pip, venv);
2. Criar o ambiente virtual e instalar `requirements.txt`;
3. Baixar os modelos offline de STT (Vosk) e TTS (Piper);
4. Guiar a criação interativa do arquivo `config/.env`;
5. Registrar o serviço `alfredo.service` no `systemd`.

```bash
# 3. Ajuste fino das variáveis de ambiente
nano config/.env

# 4. Inicie o serviço
sudo systemctl start alfredo.service

# 5. Acompanhe os logs
sudo journalctl -u alfredo.service -f
```

> 🔄 **Atualizações:** para versões futuras, basta rodar `./deploy/update.sh` — ele puxa o código mais recente do Git, atualiza as dependências e reinicia o serviço automaticamente.

### Execução manual (modo desenvolvimento)
```bash
./start.sh     # sobe API (uvicorn), satélite local e spotifyd em sessões screen separadas
./restart.sh   # reinicia os processos
```

---

## ⚙️ Configuração

Toda a configuração sensível vive em `config/.env` (nunca commitado). Principais grupos de variáveis:

- **Identidade da família:** `FAMILY_NAME`, `ADMIN_NAME`
- **Chaves de API:** Gemini (com suporte a múltiplas keys em round-robin), Groq, NewsAPI, Mapbox
- **Home Assistant:** URL e token de acesso de longa duração
- **Spotify:** credenciais OAuth (`spotipy`) + configuração do `spotifyd.conf`
- **Google Calendar:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (credenciais OAuth 2.0) + `PUBLIC_URL` (domínio público com túnel Cloudflare para callback OAuth)
- **Banco de dados:** caminho do SQLite local

Consulte `docs/INSTALL.md` para o guia completo de provisionamento de um novo servidor, e `docs/CLIENT_ONBOARDING.md` para o fluxo de onboarding de uma nova família/cliente.

---

## 📊 Dashboard de Administração

O diretório `dashboard/` contém o painel web **"Obsidian & Brass"**, usado para:
- Visualizar e editar a memória de longo prazo do Alfredo;
- Gerenciar rotinas, listas e lembretes;
- Acompanhar status de saúde da API e dos satélites conectados;
- Explorar a nuvem de sonhos gerada pela `DreamTool`;
- **Visualizar compromissos da agenda** em visão semanal com navegação por datas.

A pasta possui duas gerações de interface: `frontend/` (legada) e `newdashboard/` (React, em evolução), além de um `backend/` de suporte dedicado.

### 🔐 Google Calendar (OAuth 2.0)

A sincronia com Google Calendar segue o fluxo OAuth padrão:

1. **Adicione a redirect URI** no [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
   ```
   https://henriquedejesus.dev/api/auth/google/callback
   http://localhost:10001/api/auth/google/callback
   ```
2. **Autorize** acessando no navegador: `GET /api/auth/google/authorize`
3. O servidor troca o código por um token **refresh** e inicia sincronia automática a cada 5 minutos.

Endpoints disponíveis:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/auth/google/authorize` | Redireciona para OAuth do Google |
| GET | `/api/auth/google/callback` | Callback OAuth — recebe e armazena o token |
| GET | `/api/auth/google/status` | Status da integração (conectado, eventos pendentes) |
| POST | `/api/auth/google/sync` | Dispara sincronia manual bidirecional |
| GET | `/api/dashboard/events` | Eventos do calendário em intervalo de datas |

---

## 🗺️ Roadmap

✅ **Google Calendar Sync** — implementado. Sincronia bidirecional via OAuth 2.0.  
Consulte `docs/ALFREDO_CHECKLIST.md` e `docs/ideiasFeatures.md` para o backlog vivo de funcionalidades planejadas e em avaliação.

---

## 🤝 Contribuindo

Este é um projeto pessoal em evolução constante, mas sugestões, issues e PRs são bem-vindos. Ao contribuir:
1. Abra uma *issue* descrevendo o problema ou a ideia;
2. Siga a organização modular existente (`core/brain/skills/` para novas ferramentas, `firmware/` seguindo o `shared-protocol` para novos hardwares);
3. Rode os testes em `tests/` antes de abrir um PR.

---

<div align="center">

*Desenvolvido com ❤️ sob os princípios de Clean Code, Domain-Driven Design (DDD) e Agentic Frameworks.*

</div>