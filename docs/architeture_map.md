# Mapa da Arquitetura do Alfredo

Este documento descreve os principais arquivos e diretórios do projeto `alfredo-core`, ignorando arquivos temporários ou irrelevantes, para te dar uma visão clara de como as engrenagens se conectam.

---

## 📂 `core/` (O Coração do Sistema)
Este é o backend principal. Tudo que processa dados e executa tarefas reais mora aqui.

### 🧠 `core/brain/`
Responsável pela inteligência, decisão e memória.
- **`router.py`**: O "cérebro principal". Recebe o texto falado, decide se manda para o `FastSemanticRouter` ou para o modelo de LLM (Gemini), orquestra a chamada de ferramentas e devolve a resposta final.
- **`semantic_router.py`**: O "Fast Path" que construímos. Avalia comandos instantâneos via Regex. Importa e usa as rotas de `core/brain/routers/`.
- **`routers/`** *(Diretório)*: Contém os extratores de intenção rápida (`tv.py`, `music.py`, `timer.py`, etc.). Se conectam diretamente com o `semantic_router.py`.
- **`skills/`** *(Diretório)*: Cada arquivo aqui (ex: `tv_skill.py`, `timer_skill.py`, `weather_skill.py`) expõe uma "Ferramenta" (`Tool`) para a Inteligência Artificial. Eles definem os parâmetros e chamam os *services*.
- **`memory/`** *(Diretório)*: Arquivos como `database.py` e `models.py`. Gerenciam a persistência (memória de longo prazo, timers salvos) usando SQLAlchemy (SQLite).

### 🛠️ `core/services/`
A camada de integração. Aqui ficam os arquivos que falam com o mundo externo.
- **`samsung_tv.py`**: Conecta-se à API da SmartThings (nuvem) e usa Websockets (`samsungtvws`) na rede local. Chamado pela `tv_skill.py` e pelo `semantic_router.py`.
- **`media_service.py` / `spotify.py`**: Controlam música e player. Chamados pela `music_skill.py`.
- **`weather_service.py`**: Consulta APIs de clima.
- **`scheduler.py`**: Roda em background executando os Timers e Alarmes, enviando avisos pro sistema falar.

### 🌐 `core/api/`
Disponibiliza o Alfredo como um serviço acessível na rede.
- **`main.py`**: Inicia o servidor FastAPI. Registra todas as rotas web e Websockets.
- **`satellite.py`**: A rota Websocket `/ws/satellite`. É por aqui que os microfones da casa (os satélites) enviam áudio e recebem respostas de voz.
- **`tv.py`**, **`dashboard.py`**: Rotas HTTP usadas pelo frontend do dashboard para configurar coisas.

### 🗣️ `core/voice/`
Transforma voz em texto e texto em voz.
- **`pipeline.py`**: Junta tudo. Pega o áudio recebido pelo `satellite.py`, manda pro STT, envia o texto pro `brain/router.py`, pega a resposta, manda pro TTS e devolve o áudio gerado de volta pro satélite.
- **`stt/engine.py`**: Speech-to-Text (reconhecimento de voz).
- **`tts/engine.py`**: Text-to-Speech (geração de voz).

---

## 📡 `devices/` (Os Satélites/Ouvidos)
O Alfredo é descentralizado. O "core" fica num servidor, mas os microfones ficam espalhados pela casa.
- **`satellite_server/main.py`**: O código que roda no Raspberry Pi ou PC local. Ele fica ouvindo a palavra de ativação ("Alfredo" ou "Alexa"). Quando detecta, ele abre uma conexão Websocket com `core/api/satellite.py` e faz streaming do que você fala.

---

## 🖥️ `dashboard/` (Interface Visual)
- Contém o Frontend (HTML, React, ou Vue) onde você entra via navegador para colocar os tokens, senhas do Spotify, SmartThings e configurar a TV. Ele faz requisições HTTP para a pasta `core/api/`.

---

## 🚀 Arquivos Raiz
- **`start.sh` / `restart.sh`**: Scripts de conveniência para iniciar o sistema (sobem o Uvicorn apontando para `core/api/main.py`).
- **`deploy/update.sh`**: Script que eu chamo para puxar atualizações do GitHub e reiniciar o serviço no seu Raspberry Pi/Servidor.
- **`config.yml` / `.env`**: Configurações de chaves de API e variáveis de ambiente (Tokens do Gemini, etc.).

## 🔄 Resumo do Fluxo Principal (Como as peças se conectam)
1. Você fala na sala. O `devices/satellite_server/main.py` capta e manda o áudio via Websocket para `core/api/satellite.py`.
2. A API encaminha o áudio para `core/voice/pipeline.py`.
3. O Pipeline converte em texto e manda pro `core/brain/router.py`.
4. O Router tenta primeiro o `semantic_router.py`. Se achar algo rápido (como os timers ou a TV), extrai as intenções. Senão, manda pro Gemini.
5. Se for TV, o Router chama `core/services/samsung_tv.py` (que fala com a SmartThings).
6. A resposta volta pro Router -> Pipeline -> TTS, vira áudio, e desce pelo Websocket pro Satélite tocar na sua sala!
