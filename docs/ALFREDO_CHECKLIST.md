# ✅ Alfredo Home OS — Checklist de Desenvolvimento

> Marque cada item conforme for concluindo. Não avance para a próxima etapa sem validar a atual.

---

## 🏗️ Etapa 0 — Fundação Arquitetural
> Status: ✅ Concluída

- [x] Scaffold completo de pastas criado
- [x] READMEs de domínio em cada módulo
- [x] Repositório git inicializado
- [x] `.gitignore` configurado (Python, logs, `.env`)
- [x] `requirements.txt` base criado
- [x] Estrutura ESP-IDF em `firmware/` com `CMakeLists.txt` e `main.c`
- [x] `deploy/install.sh` criado
- [x] `deploy/update.sh` criado
- [x] `config/.env.example` criado com todas as variáveis
- [x] `docs/INSTALL.md` criado
- [x] `docs/CLIENT_ONBOARDING.md` criado
- [x] Protocolo de registro de dispositivo definido (`/api/devices/register`)
- [x] Pasta `firmware/satellite-deepseek-ball/` criada
- [x] Pasta `firmware/shared-protocol/` criada com contrato documentado
- [x] Tabela `devices` com campo `capabilities` no schema SQLite

---

## 🔊 Etapa 1 — Firmware ESP32-S3 (DeepSeek Ball)
> Pré-requisito: Etapa 0 concluída · Hardware em mãos

### 1.1 Ambiente e toolchain
- [ ] ESP-IDF v5.x instalado e configurado no servidor de desenvolvimento
- [ ] Projeto compila sem erros (`idf.py build`)
- [ ] Flash via USB funcionando (`idf.py flash`)
- [ ] Monitor serial funcionando (`idf.py monitor`)

### 1.2 Conectividade Wi-Fi
- [ ] ESP32 conecta na rede Wi-Fi via credenciais no `.env` / `menuconfig`
- [ ] Reconexão automática em caso de queda de sinal
- [ ] IP do dispositivo logado no serial após conexão
- [ ] Ping ao servidor confirma conectividade

### 1.3 Protocolo de registro
- [ ] POST `/api/devices/register` enviado ao ligar
- [ ] Payload com `device_id`, `room_id`, `hardware`, `firmware_version`, `capabilities`
- [ ] Servidor responde 200 e salva no SQLite
- [ ] Re-registro automático após reboot

### 1.4 Display GC9A01 (tela circular 240×240)
- [ ] Driver GC9A01 inicializado via SPI
- [ ] Tela acende e exibe cor sólida (teste básico)
- [ ] Fonte bitmap carregada e texto exibido
- [ ] Estado IDLE: relógio digital centralizado
- [ ] Estado IDLE: data exibida abaixo do horário
- [ ] Estado IDLE: temperatura e ícone de clima no rodapé
- [ ] Estado OUVINDO: animação de ondas de áudio
- [ ] Estado OUVINDO: texto "Ouvindo..." na borda
- [ ] Estado PROCESSANDO: animação de órbita/loading
- [ ] Estado PROCESSANDO: texto "Pensando..." piscante
- [ ] Estado FALANDO: forma de onda animada
- [ ] Estado NOTIFICAÇÃO: ícone + título centralizados
- [ ] Estado ERRO/OFFLINE: ícone de alerta + mensagem
- [ ] Estado OTA: barra de progresso + aviso "não desligue"
- [ ] Transições entre estados sem flickering

### 1.5 Captura de áudio
- [ ] Microfone inicializado (I2S ou ADC conforme hardware)
- [ ] Gravação de áudio em buffer na RAM
- [ ] Formato WAV correto: 16kHz, mono, 16bit
- [ ] Wake-up por tecla física funcionando
- [ ] Wake-up por toque (CST816 via I2C) funcionando
- [ ] Silêncio detectado para encerrar gravação automaticamente
- [ ] Indicador visual no display durante gravação

### 1.6 Envio de áudio ao servidor
- [ ] POST `/api/voice` com áudio WAV em multipart
- [ ] Header de autenticação `Authorization: Bearer <TOKEN>` incluído
- [ ] Header `X-Device-ID` e `X-Room-ID` incluídos
- [ ] Timeout configurado (máximo 15 segundos)
- [ ] Retry automático em caso de falha de rede

### 1.7 Reprodução de áudio
- [ ] Resposta WAV do servidor recebida via HTTP
- [ ] Áudio reproduzido no alto-falante embutido
- [ ] Volume ajustável via configuração
- [ ] Display atualiza para estado FALANDO durante reprodução
- [ ] Display volta para IDLE após fim da reprodução

### 1.8 WebSocket para push do servidor
- [ ] Conexão WebSocket persistente com `/ws/satellite/{room_id}`
- [ ] Reconexão automática em caso de queda
- [ ] Servidor consegue atualizar o display remotamente
- [ ] Servidor consegue enviar notificações sem o usuário falar

### ✅ Validação da Etapa 1
- [ ] Falar → ESP32 grava → envia ao servidor → recebe resposta → reproduz
- [ ] Latência total abaixo de 5 segundos (meta: abaixo de 3s)
- [ ] Display muda de estado corretamente em cada fase
- [ ] Sistema se recupera sozinho após queda de Wi-Fi

---

## 🎙️ Etapa 2 — Pipeline de Voz no Servidor
> Status: ✅ Concluída

### 2.1 Recepção de áudio (FastAPI)
- [x] Endpoint `POST /api/voice` implementado
- [x] Autenticação Bearer Token validada
- [x] Áudio WAV salvo temporariamente em `/tmp`
- [x] Headers `X-Device-ID` e `X-Room-ID` extraídos e logados
- [x] Interação registrada no SQLite (tabela `interactions`)

### 2.2 STT — Vosk (transcrição offline)
- [x] Modelo `vosk-model-small-pt-0.3` baixado pelo `install.sh`
- [x] Vosk inicializado e carregado em memória na startup
- [x] Áudio WAV transcrito para texto
- [x] Texto logado no `journalctl`
- [x] Tempo de transcrição logado (benchmark no Celeron N2830)
- [x] Fallback para mensagem de erro se transcrição falhar

### 2.3 TTS — Piper (síntese offline)
- [x] Modelo de voz PT-BR baixado pelo `install.sh`
- [x] Piper gera áudio WAV a partir de texto
- [x] Qualidade de voz validada (naturalidade)
- [x] Tempo de geração logado (meta: abaixo de 1s por frase)
- [x] Áudio temporário limpo após envio

### 2.4 Fluxo completo STT → TTS
- [x] Texto transcrito → resposta gerada → Piper → WAV → retornado ao ESP32
- [x] Teste com frase simples: "Olá Alfredo, que horas são?"
- [x] Teste com frase longa (mais de 20 palavras)
- [x] Latência total medida e documentada

### 2.5 Serviço systemd
- [x] Arquivo `alfredo.service` criado em `/etc/systemd/system/`
- [x] `Restart=always` configurado
- [x] Logs visíveis via `journalctl -u alfredo -f`
- [x] Serviço inicia automaticamente no boot

### ✅ Validação da Etapa 2
- [x] Falar qualquer frase → servidor transcreve → responde em voz
- [x] Sistema funciona após `sudo reboot` sem intervenção manual
- [x] Latência STT + TTS documentada

---

## 🧠 Etapa 3 — Router de Intenção
> Status: ✅ Concluída

### 3.1 Estrutura do router
- [x] Módulo `core/brain/router/` implementado
- [x] Interface clara: recebe texto → retorna (módulo, parâmetros)
- [x] Cada módulo de destino tem um handler registrado
- [x] Logs de roteamento: qual intenção foi detectada e para onde foi

### 3.2 Classificação por palavras-chave
- [x] Intenção HORA: "que horas", "hora certa", "que dia" → resposta local
- [x] Intenção CLIMA: "temperatura", "vai chover", "previsão", "tempo" → Open-Meteo
- [ ] Intenção MÚSICA: "toca", "próxima", "pausa", "para a música" → player local
- [ ] Intenção LEMBRETE: "me lembra", "anota", "lembrete" → SQLite
- [ ] Intenção SERVIDOR: "como está o servidor", "temperatura do servidor" → Alfredo-Ops
- [ ] Intenção FINANCEIRO: "quanto gastei", "meu saldo", "extrato" → ContaComigo
- [ ] Intenção CASA: "acende", "apaga", "liga", "desliga" → Home Assistant (placeholder)
- [x] Intenção GERAL: qualquer outra coisa → AI Fallback

### 3.3 Respostas locais imediatas
- [x] Hora atual formatada em PT-BR ("São quinze horas e vinte minutos")
- [x] Data atual formatada ("Hoje é segunda-feira, vinte e três de junho")
- [ ] Saudações contextuais (bom dia / boa tarde / boa noite)
- [ ] Resposta para "quem é você" / "seu nome"

### ✅ Validação da Etapa 3
- [x] 10 frases de teste roteadas corretamente
- [x] Nenhuma chamada à AI para comandos locais
- [x] Intenção desconhecida cai corretamente no AI Fallback

---

## 🤖 Etapa 4 — AI Fallback (Groq + Gemini)
> Status: ✅ Concluída

### 4.1 Integração Groq
- [x] Chave de API configurada no `.env`
- [x] Modelo `llama-3.1-8b-instant` integrado
- [x] System prompt em PT-BR com personalidade do Alfredo
- [x] Resposta limitada a 2 frases por padrão
- [x] Timeout de 8 segundos configurado

### 4.2 Integração Gemini
- [x] Chave de API do Google AI Studio configurada no `.env`
- [x] Modelo `gemini-1.5-flash` integrado
- [x] Mesmo system prompt do Groq aplicado
- [x] Timeout de 10 segundos configurado

### 4.3 Lógica de alternância
- [x] Groq tentado primeiro
- [x] Se erro 429 (cota): Gemini assume automaticamente
- [x] Se ambos falharem: resposta de fallback local ("Estou com dificuldades agora, tente em instantes")
- [x] Tabela `ai_usage` no SQLite registrando uso por provider por dia
- [x] Reset de contadores diário à meia-noite (cron ou scheduler)
- [x] Log de qual provider respondeu cada requisição

### 4.4 Contexto de conversa
- [x] Últimas 3 interações do usuário incluídas no contexto enviado à AI
- [x] Contexto separado por `room_id`
- [x] Contexto limpo após 10 minutos de inatividade

### ✅ Validação da Etapa 4
- [x] Pergunta geral respondida pelo Groq
- [x] Simular erro 429 e confirmar que Gemini assume
- [x] Resposta sempre em PT-BR
- [x] Resposta sempre curta (máximo 2 frases)


---

## 🌤️ Etapa 5 — Integrações Básicas
> Pré-requisito: Etapa 4 validada

### 5.1 Clima (Open-Meteo)
- [x] Cidade configurada no `.env`
- [x] Endpoint `GET /api/weather/{city}` implementado
- [x] Cache de 30 minutos no SQLite (tabela `weather_cache`)
- [x] Temperatura, umidade e condição retornadas
- [x] Display IDLE do ESP32 atualizado com dados climáticos via WebSocket
- [x] Resposta em voz: "Agora são 28 graus, céu parcialmente nublado"

### 5.2 Player de Música (Spotify Integration)
- [x] Autenticação OAuth2 com a API do Spotify (Spotipy)
- [x] Login via painel/dashboard para salvar o token do usuário
- [x] Comando "toca [música/artista]" pesquisa e inicia no dispositivo ativo
- [x] Comando "próxima", "pausa" e "continua" integrados com a API do Spotify
- [ ] Nome da música atual exibido no display via WebSocket

### 5.3 Lembretes, Despertador e Cronômetro (SQLite + WebSocket)
- [x] Tabela `timers` (com message) ajustada para agendamentos (Lembretes e Despertador)
- [x] Comando "me lembra de X às Y horas" salva lembrete textual
- [x] Comando "desperte amanhã às 7h" configura alarme sonoro
- [x] Comando "cronômetro de X minutos" inicia contagem regressiva
- [x] Envio via WebSocket do estado `timer_start` com o tempo em segundos para a bolinha
- [ ] Display do hardware exibindo contagem regressiva visual em tempo real
- [x] Scheduler (agendador) no servidor gerencia o disparo no horário correto
- [x] Disparo de alerta sonoro repetitivo no hardware ao zerar o tempo (WebSocket timer_expired)

### 5.4 Preferências de usuário
- [ ] Tabela `users` com nome e preferências básicas
- [ ] Perfis cadastrados via painel (Henrique, Esposa, Laura)
- [ ] Saudação personalizada por nome

### ✅ Validação da Etapa 5
- [ ] "Alfredo, vai chover hoje?" → resposta com dados reais
- [ ] "Toca jazz" → música inicia na conta do Spotify conectada
- [ ] "Cronômetro de 5 minutos" → bolinha exibe timer na tela e apita ao fim

---

## ⬆️ Etapa 6 — OTA (Atualização Automática de Firmware)
> Pré-requisito: Etapa 5 validada

### 6.1 Servidor OTA
- [ ] Endpoint `GET /api/ota/check?version=X.X.X` implementado
- [ ] Versão atual comparada com versão disponível no servidor
- [ ] Endpoint `GET /api/ota/download/{version}` retorna binário `.bin`
- [ ] Checksum SHA256 do binário disponível via `GET /api/ota/checksum/{version}`
- [ ] Pasta `firmware/releases/` organizada por versão

### 6.2 Cliente OTA no ESP32
- [ ] Verificação de versão ao ligar (`esp_https_ota`)
- [ ] Download do binário se versão nova disponível
- [ ] Verificação de checksum SHA256 antes de aplicar
- [ ] Display mostra barra de progresso durante download
- [ ] Reboot automático após atualização bem-sucedida
- [ ] Rollback automático se nova versão falhar ao iniciar

### 6.3 Script de release
- [ ] `scripts/release.sh` compila firmware e publica na pasta de releases
- [ ] Versão incrementada automaticamente
- [ ] Changelog de versão registrado

### ✅ Validação da Etapa 6
- [ ] Publicar versão nova → ESP32 atualiza sozinho em até 5 minutos
- [ ] Simular binário corrompido → rollback ocorre sem brick do dispositivo

---

## 📊 Etapa 7 — Dashboard Web
> Pré-requisito: Etapa 6 validada

### 7.1 Autenticação
- [ ] Login com usuário e senha configurados no `.env`
- [ ] Sessão com token JWT
- [ ] Logout funcionando
- [ ] Acesso bloqueado sem autenticação

### 7.2 Visão geral (home)
- [x] Lista de satélites registrados com status online/offline
- [ ] Último heartbeat de cada dispositivo
- [ ] Versão de firmware de cada satélite
- [ ] Temperatura da CPU do servidor
- [ ] Uso de RAM e disco do servidor

### 7.3 Logs
- [x] Últimas 50 interações listadas (quem falou, o que foi dito, resposta) (Feito: 15 últimas)
- [ ] Filtro por cômodo
- [ ] Filtro por data
- [ ] Qual provider de AI foi usado em cada interação

### 7.4 Gerenciamento de dispositivos
- [x] Listar todos os satélites registrados (Apenas o total em números no MVP)
- [ ] Ver capabilities de cada um
- [ ] Forçar atualização de firmware de um satélite específico
- [ ] Remover satélite do registro

### 7.5 Configurações
- [ ] Editar perfis de usuário
- [ ] Editar nome dos cômodos
- [ ] Editar cidade para clima
- [ ] Ver uso de cotas de AI (Groq e Gemini) do dia

### 7.6 Controle de uso de AI
- [ ] Gráfico de uso Groq vs Gemini por dia
- [ ] Alerta visual quando cota diária atingir 80%

### ✅ Validação da Etapa 7
- [ ] Dashboard acessível via `https://alfredo.seudominio.dev`
- [ ] Todos os satélites visíveis com status correto
- [ ] Logs das últimas interações exibidos

---

## 🔗 Etapa 8 — Integrações Avançadas
> Pré-requisito: Etapa 7 validada

### 8.1 ContaComigo (bot financeiro)
- [ ] Endpoint interno de consulta ao ContaComigo documentado
- [ ] "Quanto gastei hoje?" → consulta e responde com valor real
- [ ] "Qual meu saldo?" → retorna saldo atual
- [ ] Autenticação entre os dois sistemas via token interno

### 8.2 Home Assistant
- [ ] URL e token do Home Assistant configurados no `.env`
- [ ] "Acende a luz da sala" → chama serviço HA `light.turn_on`
- [ ] "Apaga tudo" → chama `homeassistant.turn_off` para grupo
- [ ] "Qual a temperatura do quarto?" → lê sensor do HA
- [ ] Entidades mapeadas por cômodo no `.env`

### 8.3 Rotinas automáticas
- [ ] Tabela `routines` no SQLite
- [ ] Rotina por horário: "todo dia às 7h fala bom dia com o clima do dia"
- [ ] Rotina por evento: "quando chegar em casa, toca música ambiente"
- [ ] Interface no dashboard para criar e editar rotinas
- [ ] Rotinas testáveis manualmente pelo dashboard

### 8.4 Calendário (SQLite Local)
- [x] Tabela `Event` criada para gerenciamento local de agenda
- [x] "O que tenho hoje?" → lista eventos agendados para hoje
- [x] "Adicione reunião amanhã às 14 horas" → cria evento para o dia seguinte
- [ ] Lembrete automático 30 minutos antes de cada evento

### ✅ Validação da Etapa 8
- [ ] "Quanto gastei essa semana?" → valor correto do ContaComigo
- [ ] "Acende a luz da sala" → luz acende via Home Assistant
- [ ] Rotina de bom dia disparando corretamente às 7h
- [ ] "O que tenho hoje?" → eventos do Google Calendar lidos em voz

---

## 🚀 Etapa 9 — Produto Final e Replicabilidade
> Pré-requisito: Etapas 1–8 funcionando na sua casa

### 9.1 Script de instalação (deploy/install.sh)
- [ ] Instalação completa em Raspberry Pi 5 do zero em menos de 20 minutos
- [ ] Download automático de modelos Vosk e Piper
- [ ] Criação e habilitação dos serviços systemd
- [ ] Geração automática de token de autenticação
- [ ] Teste de sanidade ao final (API sobe, STT funciona, TTS funciona)
- [ ] Mensagem clara de sucesso ou erro ao final

### 9.2 Script de atualização (deploy/update.sh)
- [ ] `git pull` + restart dos serviços
- [ ] Migração automática do banco SQLite se schema mudou
- [ ] Rollback automático se serviço não subir após update

### 9.3 Documentação final
- [ ] `docs/INSTALL.md` completo e testado por você em uma instalação limpa
- [ ] `docs/CLIENT_ONBOARDING.md` com checklist de configuração por família
- [ ] `docs/HARDWARE.md` com lista de hardwares suportados e como portar novos
- [ ] `firmware/shared-protocol/README.md` com contrato completo de integração
- [ ] README.md raiz do projeto atualizado e apresentável

### 9.4 Segurança para produção
- [ ] `.env` nunca commitado no git (validado)
- [ ] Token de autenticação único por instalação
- [ ] HTTPS via Cloudflare Tunnel em todas as instalações
- [ ] Dashboard com senha forte obrigatória no `install.sh`
- [ ] Logs sem dados sensíveis (sem CPF, senhas, tokens)

### 9.5 Teste de replicação real
- [ ] Instalar do zero em um segundo hardware (RPi 5 ou outro)
- [ ] Tempo de instalação registrado
- [ ] Checklist CLIENT_ONBOARDING seguido completamente
- [ ] Sistema funcionando sem nenhum ajuste manual extra

### ✅ Validação Final do Projeto
- [ ] Sistema rodando 24/7 na sua casa há pelo menos 2 semanas sem intervenção
- [ ] Instalação em hardware diferente concluída com sucesso
- [ ] Custo mensal de APIs confirmado em R$0
- [ ] Dashboard acessível e mostrando dados reais
- [ ] OTA funcionando (atualização remota sem tocar no hardware)
- [ ] Pelo menos 5 comandos de cada categoria funcionando

---

## 📦 Backlog Futuro (pós-lançamento)

- [ ] Reconhecimento de voz por perfil (identificar quem está falando)
- [ ] App mobile para controle remoto
- [ ] Suporte a novos hardwares de satélite (ESP32 genérico, RPi Zero)
- [ ] Wake word customizada ("Ei Alfredo") sem pressionar botão
- [ ] Integração com Spotify / YouTube Music
- [ ] Histórico de gastos com gráficos via ContaComigo
- [ ] Câmera no satélite (reconhecimento facial)
- [ ] Integração com campainha / interfone
- [ ] Suporte a múltiplos idiomas por perfil

---

**Última atualização:** Junho 2026  
**Versão do checklist:** 1.0  
**Responsável:** Henrique
