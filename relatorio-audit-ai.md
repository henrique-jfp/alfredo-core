RELATÓRIO DE AUDITORIA TÉCNICA — Alfredo Home OS
1. Visão Geral
Objetivo do projeto: Alfredo Home OS é um ecossistema completo de assistente doméstico inteligente, modular, auto-hospedado e com custo operacional mensal zero. Ele processa voz (STT/TTS) localmente, roteia intenções por skills nativas e usa IA em nuvem apenas como fallback.
Problema que resolve: Substitui assistentes domésticos proprietários (Alexa, Google Home) por uma solução open-source, privada, sem dependência de nuvem para funcionalidades básicas, executável em hardware modesto (Celeron N2830, 4GB RAM).
Público-alvo: Residências familiares, entusiastas de automação residencial, makers com ESP32, desenvolvedores que buscam controle total sobre assistente de voz.
Estado atual: Desenvolvimento ativo. Backend (FastAPI + Skills + Memória) operacional. Dashboard web funcional. Firmware ESP32-S3 em estágio inicial de scaffold. 
Nível de maturidade: Beta (MVP funcional para desenvolvimento local, hardware satélite não finalizado).
2. Arquitetura
Arquitetura: Cliente-Servidor híbrida com satélites "burros" (thin clients). O servidor central concentra toda a inteligência.
┌─────────────────────────────────────────────────────┐
│                   SERVIDOR CENTRAL                   │
│  HP Pavilion X360 / Intel Celeron N2830 / 4GB RAM    │
│  Ubuntu Server 24.04 LTS                             │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ FastAPI  │  │ Uvicorn  │  │   SQLite DB       │   │
│  │ (Porta   │  │ (WebSock)│  │   alfredo_memory  │   │
│  │  10001)  │  │          │  │                   │   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │                 │              │
│  ┌────▼──────────────▼─────────────────▼──────────┐  │
│  │             API Layer (main.py)                 │  │
│  │  POST /api/voice  │  POST /api/devices/register │  │
│  │  GET /api/dashboard/* │  WS /ws/satellite/{id}  │  │
│  └──────────────────────┬─────────────────────────┘  │
│                         │                             │
│  ┌──────────────────────▼─────────────────────────┐  │
│  │          AgentRouter (agent_router.py)          │  │
│  │     Tool Calling via Cerebras (gemma-4-31b)     │  │
│  └────┬──────┬──────┬──────┬──────┬───────┬──────┘  │
│       │      │      │      │      │       │          │
│  ┌────▼┐ ┌──▼──┐ ┌─▼───┐ ┌▼───┐ ┌▼────┐ ┌▼──────┐ │
│  │Time │ │Wea- │ │Tra- │ │Lis-│ │Timer│ │YouTube│ │
│  │Skill │ │ther │ │ffic │ │t   │ │Skill│ │Skill  │ │
│  └─────┘ └─────┘ └─────┘ └────┘ └─────┘ └───────┘ │
│  ┌────────────────────────────────────────────────┐  │
│  │   IntentRouter (router.py - NLP Spacy/Regex)   │  │
│  │   FallbackSkill → Groq (Llama-3) → Gemini      │  │
│  └────────────────────────────────────────────────┘  │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ STT Engine  │  │ TTS Engine │  │  Scheduler   │  │
│  │ (Groq       │  │ (Piper TTS)│  │  Background  │  │
│  │  Whisper)   │  │            │  │  Timers/     │  │
│  │             │  │            │  │  Routines    │  │
│  └─────────────┘  └────────────┘  └──────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │         Dashboard Web (HTML+JS+CSS)            │  │
│  │   Visão Geral │ Integrações │ Rotinas │ Config │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼              ▼               ▼
┌─────────────────┐ ┌──────────┐ ┌──────────────┐
│ Satélite ESP32- │ │ Mock     │ │ Local        │
│ S3 (DeepSeek    │ │Satellite │ │Satellite     │
│ Ball) - Em      │ │(Windows) │ │(Linux/Microf)│
│ desenvolvimento │ │          │ │              │
└─────────────────┘ └──────────┘ └──────────────┘
     ┌────┴────┐
     │Wi-Fi    │
     │Display  │
     │Áudio    │
     │OTA      │
     └─────────┘
Organização das pastas:
- core/ — Motor principal (API, Brain/Voz, Serviços)
- firmware/ — Código ESP32-S3 (ESP-IDF)
- dashboard/ — Frontend web (HTML/JS/CSS) + Backend (mesmo FastAPI)
- integrations/ — Placeholders para integrações futuras
- devices/ — Gerenciamento de satélites (placeholder)
- scripts/ — Scripts utilitários (satélite mock, testes)
- deploy/ — Scripts de instalação e atualização
- docs/ — Documentação técnica
- config/ — Configuração de ambiente (.env.example)
- tests/ — Pasta placeholder para testes
- logs/ — Pasta placeholder para logs
- tmp/ — Áudios temporários (in/out WAV)
Responsabilidades dos módulos:
- core/api/ — Endpoints REST (FastAPI + WebSocket), schemas Pydantic, dashboard backend
- core/brain/ — Roteadores (IntentRouter via Spacy/regex + AgentRouter via Cerebras Tool Calling), skills nativas, memória (SQLite ORM)
- core/voice/ — Engines STT (Groq Whisper) e TTS (Piper)
- core/services/ — Scheduler (timers, rotinas) + Weather Service (Open-Meteo)
- dashboard/frontend/ — SPA com HTML, CSS, JS vanilla
Pontos de entrada: core/api/main.py (FastAPI app, uvicorn)
3. Tecnologias
Tecnologia	Versão	Finalidade
Python	3.x	Linguagem do servidor
FastAPI	≥0.109.0	Framework API REST/WS
Uvicorn	≥0.27.0	Servidor ASGI
SQLAlchemy	≥2.0.25	ORM
SQLite	—	Banco de dados local
Spacy	≥3.7.2	NLP (intent extraction)
Pydantic	≥2.5.0	Validação de schemas
Piper TTS	≥1.2.0	Síntese de voz offline
Groq API	≥0.36.0	STT (Whisper) + LLM Fallback
Spotipy	≥2.23.0	Spotify API
yt-dlp	≥2023.12.30	YouTube áudio extraction
httpx	≥0.26.0	HTTP client
NumPy	≥1.26.0	Processamento de áudio
soundfile	≥0.12.1	Leitura WAV
dotenv	≥1.0.0	Variáveis de ambiente
ESP-IDF	v5.x	Framework ESP32
Cerebras API	—	Tool Calling LLM (AgentRouter)
Open-Meteo	—	API gratuita de clima
OSRM	—	API gratuita de rotas
Google Maps API	—	API de rotas (c/ trânsito)
Gemini API	—	LLM fallback
NewsAPI / RSS	—	Notícias (G1 RSS)
Cloudflare Tunnel	—	Exposição segura HTTPS
systemd	—	Gerenciamento de serviços
PulseAudio	—	Áudio Linux
PyAudio	—	Captura/Reprodução áudio
4. Dependências
Críticas (sem as quais o sistema não funciona):
- Groq API — Usada para STT (Whisper) E LLM Fallback. Duplo ponto de falha.
- Piper TTS — Síntese de voz offline (depende de download do modelo ONNX).
- Cerebras API — Essencial para o AgentRouter (Tool Calling). Sem ela, o router principal falha.
- SQLite + SQLAlchemy — Toda persistência do sistema (memória, timers, interações, configurações).
Moderadas:
- Spotify API (Spotipy) — MusicSkill requer OAuth e token.
- Open-Meteo — WeatherSkill (gratuita, sem chave).
- OSRM / Google Maps — TrafficSkill.
- yt-dlp — YouTubeSkill (dependente da estabilidade do YouTube).
- Gemini API — Fallback secundário.
Risco de dependência:
- Cerebras API: Chave exposta no .env commitado. API pode mudar ou ter custos.
- Groq: Modelo whisper-large-v3 e llama-3.1-8b-instant — disponibilidade e rate limits.
- yt-dlp: Legalmente controverso, YouTube muda constantemente.
5. Fluxo da aplicação
Inicialização
1. load_dotenv() carrega variáveis do .env
2. SQLAlchemy Base.metadata.create_all() cria tabelas no SQLite
3. FastAPI app instancia com SchedulerManager
4. Evento startup inicia scheduler em background (asyncio.create_task)
Fluxo principal de voz
 1. Satélite captura áudio (16kHz, mono, 16bit WAV)
 2. POST /api/voice → autentica Bearer Token → salva WAV em tmp/
 3. Registra interação vazia no SQLite
 4. STT: Groq Whisper transcreve áudio → texto
 5. Atualiza interação com input_text
 6. Router: AgentRouter ou IntentRouter processa texto
 7. Callback Cerebras identifica tool call OU Intenção Spacy/regex identifica skill
 8. Skill executa → retorna texto resposta
 9. Atualiza interação com output_text
10. TTS: Piper sintetiza resposta → WAV
11. FileResponse retorna WAV ao satélite
Fluxo de texto (Dashboard)
1. POST /api/voice/text → router processa → TTS → WAV → FileResponse
WebSocket
- WS /ws/satellite/{device_id} → conexão persistente
- Envia weather_update ao conectar
- Servidor envia push: timer_expired, play_alarm, play_audio, update_wake_word
Encerramento
- Evento shutdown → scheduler.stop()
Autenticação
- Bearer Token via header Authorization
- Validação existe mas TODO no register_device (não verifica o token de fato)
6. Banco de Dados
ORM: SQLAlchemy 2.0+ com SQLite (arquivo único: alfredo_memory.db)
Tabelas:
Tabela	Finalidade
devices	Satélites registrados
interactions	Histórico de conversas
ai_usage	Consumo de tokens IA
weather_cache	Cache do clima (30min)
timers	Cronômetros/alarmes
list_items	Listas de compras/tarefas
events	Eventos de calendário
app_integrations	Integrações (Spotify)
routines	Rotinas automáticas
settings	Configurações chave-valor
saved_locations	Endereços salvos
Migrações: Manuais via scripts Python (sem Alembic). Ex: migrate_db.py, migrate_locations.py, update_db.py
Riscos: SQLite sem concorrência real (check_same_thread=False), sem migrations automatizadas, chaves do Spotify armazenadas em texto puro.
7. Qualidade do Código
Aspecto	Nota
Organização	8/10
Legibilidade	7/10
Modularização	8/10
Reutilização	6/10
Consistência	5/10
Padronização	7/10
Separação de responsabilidades	7/10
Geral: 7/10 — Código bom para MVP, com áreas que precisam de refatoração.
8. Dívida Técnica
 1. Duplicação de routers — router.py (IntentRouter com Spacy/Regex) e agent_router.py (AgentRouter com Cerebras Tool Calling). Cada um com seu próprio conjunto de skills (parcialmente duplicado). Isso gera confusão e manutenção dobrada. Média prioridade.
 2. main.py excessivo (~334 linhas) — Mistura configuração de app, endpoints, lógica de voz, roteamento, e tratamento de WebSocket em um único arquivo. Alta prioridade.
 3. dashboard.py inchado (~335 linhas) — CRUDs, lógica de negócio, regras de integração misturadas. Alta prioridade.
 4. Tratamento de erros inconsistente — Algumas skills usam try/except com fallback, outras não. Média prioridade.
 5. Sem testes automatizados — tests/ vazio (só README placeholder). Crítico.
 6. Integrações placeholders — integrations/ contém apenas READMEs vazios sem código. Baixa prioridade.
 7. Firmware ESP32 minimalista — main.c com apenas loop vazio. Crítico para conclusão do hardware.
 8. Uso de global para singletons — _router_instance, _stt_instance, _tts_instance via funções globais. Média prioridade.
 9. Chaves de API hardcoded no .env commitado — .env com chaves reais no repositório. CRÍTICO.
10. Código comentado e scripts de fix — fix_satellite.py modifica arquivo de produção diretamente. Baixa prioridade.
9. Segurança
Problema	Risco	Descrição
Chaves de API no .env commitado	CRÍTICO	.env com GROQ_API_KEY, GEMINI_API_KEY, CEREBRAS_API_KEY e ALFREDO_AUTH_TOKEN reais estão no repositório git
Token de autenticação não validado	Alto	TODO no register_device: token não é verificado
Spotify credentials em texto puro	Alto	client_secret do Spotify armazenado sem criptografia no SQLite
Dashboard sem autenticação	Alto	Nenhum login/senha/JWT no dashboard
Sem HTTPS	Médio	HTTP plano em produção (Cloudflare Tunnel pode mitigar)
Variáveis de ambiente não validadas	Baixo	Ausência de chaves gera erros não tratados gracefulmente
Injeção SQL	Baixo	SQLAlchemy ORM protege, mas scripts raw SQL existem
Validação de entrada mínima	Médio	Headers X-Device-ID e X-Room-ID não são sanitizados
10. Performance
- STT via Groq (Whisper - nuvem): Latência alta (~2-5s), dependente de internet. O checklist menciona Vosk local, mas o código usa Groq Whisper.
- TTS via Piper (local): Razoável, mas modelo ONNX de 30MB carregado em memória.
- SQLite com check_same_thread=False: Pode causar corrupção em concorrência.
- Scheduler loop a cada 1 segundo: Polling constante no banco para timers e rotinas.
- Arquivos WAV em tmp/: Sem limpeza automática, acumulam.
- Spacy carregado em memória: Modelo NLP de ~15MB em RAM limitada (4GB).
- Múltiplas requisições HTTP externas encadeadas: STT → Cerebras → TTS = latência total alta (3-8s).
11. Escalabilidade
Limitações severas:
- SQLite não escala para múltiplos servidores ou alta concorrência
- Servidor single-thread (Celeron N2830) com 4GB RAM
- Satélites se registram via polling WebSocket único
- Design monousuário (room_id é o máximo de segmentação)
- Scheduler com polling a cada 1 segundo em banco único
Partes que se tornam gargalos:
- Banco SQLite (escrita concorrente)
- CPU do servidor para TTS Piper
- Memória RAM para modelos Spacy + Piper
- Rede para STT/LLM em nuvem
12. Manutenibilidade
- Adicionar novas funcionalidades: Bom. Criar nova skill = implementar Skill ABC e registrar. Razoável.
- Depuração: Logs estruturados com logging.getLogger. Bom.
- Testes: Inexistentes. Péssimo.
- Onboarding: README, INSTALL.md, CLIENT_ONBOARDING.md excelentes. Docs README com placeholder genérico, porém.
13. Testes
Inexistentes. Diretório tests/ contém apenas README placeholder. Arquivos de teste na raiz (test_amp.py, test_db.py, test_mic.py, test_transcribe.py, test_timers.py, test_yt_api.py) são scripts ad-hoc para validação manual, não testes automatizados.
Nota: 0/10 — Ausência crítica.
14. Documentação
Tipo	Avaliação
README raiz	Excelente. Filosofia, habilidades, estrutura
README_SERVER	Excelente. Deploy, systemd, rede, manutenção
ALFREDO_CHECKLIST	Excelente. Checklist completo de desenvolvimento
checklist_funcoes	Excelente. Capacidades com exemplos de voz
INSTALL.md	Bom. Passo a passo de instalação
CLIENT_ONBOARDING.md	Bom. Checklist para novos clientes
Firmware shared-protocol	Bom. Contrato de comunicação
READMEs de módulo	Genéricos/automáticos. Cada pasta tem README.md placeholder sem conteúdo útil
Comentários no código	Razoáveis. Muitos comentários de TODO úteis
15. Funcionalidades
Core
- Pipeline STT (Groq Whisper) → TTS (Piper)
- Registro de dispositivos satélites
- WebSocket para push de notificações
Skills (10 implementadas)
 1. TimeSkill — Hora e data atuais (local)
 2. WeatherSkill — Clima via Open-Meteo (cache 30min)
 3. TimerSkill — Cronômetros, alarmes, lembretes (SQLite + WebSocket)
 4. ListSkill — Listas de compras e tarefas (CRUD)
 5. CalendarSkill — Agenda local (criar/ler eventos)
 6. TrafficSkill — Trânsito (Google Maps + OSRM fallback)
 7. NewsSkill — Manchetes RSS (G1)
 8. MusicSkill — Spotify (play, pause, next, search)
 9. YouTubeSkill — Áudio de vídeos/lives (yt-dlp + YouTube API)
10. FallbackSkill — IA conversacional (Groq → Gemini)
Dashboard Web
- Visão geral com KPIs
- Histórico de conversas
- Mini "virtual mic" para testar comandos por texto
- Listas (compras e tarefas)
- Timers ativos
- Integração Spotify (configuração + login OAuth via QR Code)
- Rotinas automáticas (CRUD + toggle)
- Configurações (nome, voz, APIs, endereços)
- Teste de vozes TTS
Infraestrutura
- Script install.sh com systemd
- Script update.sh com git pull + restart
- Deploy via Cloudflare Tunnel
- Scripts de satélite mock (Windows) e local (Linux)
16. Funcionalidades Incompletas
TODOs no código:
- main.py:59 — "TODO: Implementar verificação do Bearer token (SATELLITE_AUTH_TOKEN)"
- router.py:81 — "TODO: Adicionar heurísticas de Automação (Ligar luz, etc)"
- main.c:12-15 — "TODO: Inicializar NVS/Wi-Fi/Display/Áudio"
ALFREDO_CHECKLIST.md — Itens pendentes:
- Etapa 3: Intenção MÚSICA, LEMBRETE, SERVIDOR, FINANCEIRO, CASA (parcial)
- Etapa 3: Saudações contextuais, resposta para "quem é você"
- Etapa 5: Nome da música no display, exibição timer no hardware
- Etapa 5: Tabela users com perfis
- Etapa 6: OTA (inteira — servidor e cliente)
- Etapa 7: Autenticação JWT, heartbeat, filtros, gráficos de IA
- Etapa 8: ContaComigo, Home Assistant, Rotinas automáticas avançadas
- Etapa 9: Script de instalação completo, documentação final, segurança production
Integrações placeholders: integrations/{weather,ai_fallback,calendar,contacomigo,homeassistant,music}/ — apenas READMEs.
Firmware: Apenas scaffold básico (main.c vazio, componentes com READMEs placeholder).
17. Melhorias Sugeridas
Alta Prioridade
1. Remover .env do git — Adicionar ao .gitignore imediatamente, rotacionar todas as chaves expostas.
2. Implementar autenticação no dashboard — Login com senha/JWT antes de expor via Cloudflare.
3. Implementar testes automatizados — Pytest para skills, API, e integração.
4. Refatorar main.py — Separar endpoints em módulos (voice, devices, websocket).
5. Validar Bearer Token — Implementar verificação real no register_device.
Média Prioridade
 6. Unificar routers — Decidir entre IntentRouter (Spacy/Regex) e AgentRouter (Cerebras). Manter apenas um padrão.
 7. Alembic para migrações — Substituir scripts manuais de migração SQLite.
 8. Limpeza automática de tmp/ — Evitar acúmulo de WAVs.
 9. Implementar Vosk local — Código menciona mas não usa (usa Groq Whisper). Inconsistência.
10. Melhorar tratamento de erros — Respostas consistentes para falhas de API externa.
Baixa Prioridade
11. READMEs de módulo com conteúdo real — Substituir placeholders genéricos.
12. Remover scripts de fix — fix_satellite.py não deveria estar no repositório.
13. Type hints consistentes — Em todo o código Python.
14. Configurar CI/CD — GitHub Actions para lint + testes.
18. Riscos do Projeto
Risco	Classificação
Chaves de API expostas no git	Crítico
Dependência de APIs gratuitas	Alto
Sem testes automatizados	Alto
Firmware não implementado	Alto
Dashboard sem autenticação	Alto
SQLite como banco único	Médio
Ausência de backup de dados	Médio
Latência alta (STT em nuvem)	Médio
Python em hardware limitado	Médio
yt-dlp legalmente instável	Médio
19. Pontos Positivos
 1. Documentação excelente — README, checklist, onboarding, protocolo. Raro em projetos independentes.
 2. Arquitetura modular DDD — Skills baseadas em ABC, separação clara de responsabilidades.
 3. Foco em custo zero — Open-Meteo, OSRM, Piper, Vosk. Filosofia bem executada.
 4. Código limpo e legível — Fácil de entender mesmo sem conhecimento prévio.
 5. Checklist de desenvolvimento robusto — 430 linhas de etapas validadas.
 6. Escolha inteligente de hardware — Notebook velho como servidor (bateria = nobreak natural).
 7. Web Dashboard de alta qualidade — Design system premium, glassmorphism, UX refinada (JS vanilla).
 8. Deploy híbrido maduro — systemd, Cloudflare Tunnel, separação de venvs.
 9. Múltiplos fallbacks — Cerebras → Groq → Gemini, Google Maps → OSRM.
10. Potencial de replicação — Arquitetura feita para ser instalável em qualquer hardware.
20. Resumo Executivo
Nota Geral: 6.5/10
Principais Qualidades
- Documentação excelente e detalhada
- Arquitetura modular bem planejada (DDD)
- Dashboard web de alta qualidade
- Pipeline de voz funcional (STT → LLM → TTS)
- Deploy híbrido maduro (systemd + Cloudflare)
- 10 skills nativas implementadas
Principais Problemas
- CRÍTICO: Chaves de API reais commitadas no .env
- CRÍTICO: Ausência total de testes automatizados
- ALTO: Firmware ESP32 não implementado (apenas scaffold)
- ALTO: Dashboard sem autenticação
- ALTO: Dois routers concorrentes e conflitantes
- MÉDIO: main.py monolítico, difícil de manter
- MÉDIO: Dependência excessiva de APIs gratuitas de terceiros
Prioridades Imediatas
1. Remover .env do git e rotacionar todas as chaves
2. Implementar autenticação no dashboard
3. Decidir e unificar o roteador de intenções (IntentRouter vs AgentRouter)
4. Criar suite de testes automatizados (pytest)
5. Validar token de autenticação nos endpoints
Próximos Passos Recomendados
1. Segurança primeiro: Gitignore .env, rotacionar chaves, adicionar JWT ao dashboard
2. Decisão arquitetural: Escolher entre AgentRouter (Cerebras Tool Calling) ou IntentRouter (Spacy/Regex) como padrão, remover o outro
3. Testes: Pytest para todas as skills e endpoints da API
4. Firmware: Implementar comunicação Wi-Fi + envio de áudio no ESP32-S3
5. Refatoração: Extrair lógica do main.py para módulos especializados
6. Migrações: Implementar Alembic para schema SQLite
7. Documentação finalizar: READMEs de módulo com conteúdo real
Relatório gerado em 02/07/2026 após análise completa do repositório alfredo-core com 322 arquivos mapeados.
▣  Build · DeepSeek V4 Flash Free · 8m 13s
agora que você tem esse conhecimento completo, qual sua sugestão para ser a voz do meu sistema, o servidor não vai mudar tão em breve, mas gostaria de mais opções de voz, o que estou usando atualmente só tem voz masculina e só uma presta, quais suas sugestões, explique pros e contra e qual sua escolha  e porque
+ Thought: 15.8s
Com base na auditoria que fiz, aqui vai minha análise:
Situação Atual
Você usa Piper TTS com modelos ONNX da Rhasspy. As vozes PT-BR disponíveis no Piper são:
- faber-medium (masculino suave) — a que está funcionando
- edresson-low/medium (masculino leve)
- jeff-medium (masculino grave)
- cadu-medium (masculino)
- tugão-medium (PT-PT, masculino)
Todas masculinas. E como você observou, a qualidade varia. O problema é que o ecossistema Piper é mantido pela comunidade e o português não tem tantas opções.
Opções Viáveis para seu Hardware (Celeron N2830, 4GB)
1. edge-tts (Microsoft Edge TTS) — Minha recomendação
Prós:
- Vozes PT-BR de altíssima qualidade: Francisca (feminino, melhor), Antonio (masculino)
- Dezenas de vozes em vários idiomas
- API simples via pip install edge-tts, ~10 linhas de integração
- Gratuito e sem chave de API
- Latência baixa (~0.5-1s para frases curtas)
- Zero impacto na CPU/RAM do servidor (processamento na nuvem Microsoft)
Contras:
- Requer internet (mas você já usa Groq Whisper + Cerebras na nuvem, então não é adicional)
- Dependência de serviço externo (pode mudar ou ser bloqueado)
Por que escolho essa: Sua filosofia de "custo zero" não é violada (é grátis), você já depende de internet para STT/LLM, a qualidade é MUITO superior ao Piper, e libera zero CPU no Celeron. Adicione como provider principal e mantenha Piper como fallback offline.
Código de integração seria algo direto no core/voice/tts/engine.py.
2. gTTS (Google TTS)
Prós: Simples, pip install gTTS, voz feminina PT-BR disponível
Contras: Qualidade inferior ao edge-tts, latência maior, Google pode rate-limit
3. Sherpa-ONNX + VITS (local)
Prós: Processamento 100% local, qualidade boa, modelos VITS em português existem
Contras: Mais complexo de integrar, consome CPU (~1-2s por frase no Celeron), RAM extra, menos opções de voz
4. ElevenLabs (premium)
Prós: Qualidade surreal, vozes femininas PT-BR perfeitas, controle total (velocidade, tom)
Contras: Pago (US$5/mês mínimo), fere a filosofia de custo zero
Comparativo Final
Opção	Qualidade	Offline
edge-tts ⭐	Excelente	Não
Piper (atual)	Mediana	Sim
Sherpa-ONNX	Boa	Sim
gTTS	Boa	Não
ElevenLabs	Excelente	Não
Minha Escolha
Implemente edge-tts como engine principal com fallback para Piper (já existente).
Benefícios:
1. Voz feminina (Francisca) e masculina (Antonio) de altíssima qualidade
2. Impacto zero no hardware limitado
3. Gratuito e sem chave
4. Latência ~1s, comparável ou melhor que Piper local
5. Adiciona variedade real de vozes (você pode alternar por perfil/cômodo)
Risco baixo: Se a internet cair, o Piper assume automaticamente. Você mantém resiliência.
Quer que eu prepare o plano de integração ou faça um protótipo do código quando for a hora?
▣  Build · DeepSeek V4 Flash Free · 40.7s
OK, AGORA FALANDO DE FUNÇÕES DO ASSISTENTE, VAMOS ESQUECER CONEXÇÃO COM LUZ E OUTROS SATELITES QUE NÃO TENHO AINDA, DIGA 10 FUNÇÕES TOP'S PARA ADICIONAR AO PROJETO, EXPLIQUE UM POUCO A IMPORTANCIA DE CADA UMA
+ Thought: 955ms
Com base na auditoria completa, aqui estão 10 funções que trazem MAIOR impacto real com menor esforço:
1. Multiusuário com Reconhecimento por Voz (Speaker Diarization)
O que é: O sistema identifica QUEM está falando pela voz e responde com base no perfil da pessoa (agenda, lista, preferências).
Importância: Hoje o Alfredo trata "todos" como um usuário só. Sua esposa pede "minha agenda" e ele não sabe de quem é. Com isso, cada membro da família tem listas, eventos e preferências próprias. É a feature que separa um brinquedo de um assistente familiar real.
2. Wake Word "Ei Alfredo" (Vosk contínuo offline)
O que é: Detecção da palavra de ativação 100% local sem precisar apertar botão. O código já tem o Vosk baixado e o local_satellite.py faz isso, mas não está integrado no servidor.
Importância: Sem wake word, o sistema exige interação física (botão/toque) ou um "modo de escuta" constante que consome bateria/recursos. Com wake word local, fica natural como Alexa/Google — você simplesmente fala.
3. Preferências Persistentes por Sala
O que é: Cada cômodo tem seu próprio conjunto de preferências (voz, volume, cidade para clima, lista de compras da cozinha vs quarto).
Importância: Hoje tudo é global. A cozinha pergunta "o que tenho na agenda?" e recebe a agenda inteira da casa. Com preferências por sala, o assistente se adapta ao contexto físico — comportamento esperado de um assistente doméstico.
4. Histórico de Gastos Financeiros (ContaComigo)
O que é: Integrar o ContaComigo (já mencionado como módulo irmão) para responder "quanto gastei hoje/esse mês?" com dados reais.
Importância: É o comando que sua esposa mais vai usar. Controle financeiro é uma das dores mais reais de uma casa. E você já tem o sistema irmão — é conectar os pontos. Difícil de implementar sem o ContaComigo, mas se ele existir, é alta prioridade.
5. Respostas Contextuais com Memória de Longo Prazo
O que é: "Alfredo, que horas é a consulta da Laura amanhã?" → "Amanhã às 14h, na Dra. Maria." Sem precisar criar evento antes. O sistema lembra de conversas de dias atrás.
Importância: Hoje o contexto dura 10 minutos. Conversas naturais exigem memória de longo prazo. Isso faz o assistente parecer INTELIGENTE de verdade, não apenas um script de comandos.
6. Leitura de Mensagens do WhatsApp/Telegram
O que é: "Alfredo, leia minhas mensagens" → O sistema lê as mensagens não lidas do WhatsApp/Telegram em voz.
Importância: É uma das funcionalidades mais pedidas em assistentes domésticos. Útil enquanto você está cozinhando, com as mãos ocupadas. Requer integração com API não oficial (whatsapp-web.js, telegram API).
7. Tradução Simultânea
O que é: "Alfredo, como se diz 'estou com fome' em inglês?" → "I'm hungry." Ou "traduza 'good morning' para português".
Importância: Extremamente útil no dia a dia, especialmente em famílias bilíngues. Usa o LLM que VOCÊ JÁ TEM (Groq/Gemini), zero custo adicional de implementação.
8. Leitura de documentos em voz (PDF/TXT)
O que é: "Alfredo, leia o contrato que chegou por email" ou "leia essa receita". O sistema extrai texto de PDF e lê em voz alta.
Importância: Mãos ocupadas na cozinha? "Alfredo, leia a receita de bolo de cenoura." Trabalhando? "Leia o resumo desse artigo." É uma skill simples (PyMuPDF + TTS) que transforma o assistente em ferramenta produtiva.
9. Reprodutor de Áudio Local (Músicas Baixadas / Playlists Locais)
O que é: "Alfredo, toque minha playlist de MP3s" ou "toque músicas da pasta Músicas". Sem depender de Spotify.
Importância: Spotify pode falhar, acabar a cota, ou simplesmente você ter música local. Hoje o MusicSkill só funciona com Spotify autenticado. Um reprodutor local com VLC/mplayer (que você já usa no YouTubeSkill) garante música SEMPRE disponível, mesmo sem internet.
10. Temporizador com Nome (Timers Nomeados + Múltiplos)
O que é: "Alfredo, 10 minutos para o macarrão" e "15 minutos para o arroz" simultaneamente. Quando um acabar: "Seu timer 'macarrão' finalizou!"
Importância: Hoje o TimerSkill cria timers sem nome e sem suporte a múltiplos concorrentes. Isso limita severamente o uso real. Na cozinha, você sempre tem múltiplos tempos. É uma skill de altíssimo valor cotidiano e requer pouca mudança no código existente.
Tabela de Prioridade vs Esforço
#	Função
10	Timers com nome + múltiplos
2	Wake word local
7	Tradução simultânea
8	Leitura de PDF/texto
9	Player de áudio local
3	Preferências por sala
1	Multiusuário + diarização
5	Memória de longo prazo
6	Leitura WhatsApp/Telegram
4	ContaComigo (gastos)
Minha recomendação pessoal: comece pelo #10 (timers nomeados, 1-2 dias de código) e #7 (tradução, algumas horas). São vitórias rápidas que os moradores da casa sentem no mesmo dia. Depois #2 (wake word) e #8 (leitura de PDF), que transformam a experiência de uso completamente. O multiusuário e memória longa são os maiores investimentos mas também o maior salto de qualidade.