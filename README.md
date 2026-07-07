# Alfredo OS 🎩

Alfredo OS v3.0 é um ecossistema completo de assistente doméstico inteligente. Projetado do zero para ser modular, altamente expressivo e incrivelmente rápido, com foco na fluidez conversacional e em arquitetura orientada a Agentes Autônomos.

## 🌟 Filosofia "Agentic"
O Alfredo abandonou o modelo clássico de assistentes engessados por "palavras-chave".
1. **Cérebro Agente:** Utilizamos o modelo **Gemini 2.5 Flash** não apenas como "Fallback", mas como o **Roteador Principal**. Ele interpreta cada frase de forma contextual e decide autonomamente quais ferramentas (Tools) do sistema deve invocar (ou se deve usar mais de uma ao mesmo tempo).
2. **Satélites "Burros" & Captura Híbrida:** Os dispositivos espalhados pela casa (ou o próprio servidor com microfone local) servem estritamente como interfaces de I/O. Utilizamos **Vosk (Offline Leve)** apenas para ouvir a palavra de ativação (Wake Word) silenciosamente, sem consumir rede. Ao acionar, a gravação da fala é controlada por **Google WebRTC VAD + Filtro RMS** para detectar o fim da frase com precisão milimétrica e cortar ruídos de fundo (ventiladores, estática). O áudio é capturado por um **pipeline único** com `sounddevice`, eliminando conflitos de microfone (ALSA) e processos zumbis.
3. **Custo Próximo a Zero (Nuvem Inteligente):** O HP Celeron atua como orquestrador, delegando tarefas pesadas de IA para a nuvem através de APIs gratuitas ou de altíssimo custo-benefício:
   - **STT (Fala p/ Texto):** Whisper-Large-V3 rodando em velocidade absurda via API do **Groq**.
   - **Raciocínio & Roteamento:** **Gemini 2.5 Flash** (Rápido, inteligente e adaptável a chamadas de ferramentas).
   - **Revezamento de APIs:** Sistema de Round-Robin nativo para rotacionar múltiplas chaves (keys) do Gemini automaticamente, contornando o limite rigoroso de "Requests Per Minute" (429 Quota Exceeded) sem custo adicional.
   - **TTS (Texto p/ Fala):** **Microsoft Edge TTS** (Voz Neural *FranciscaNeural*, *AntonioNeural*, *DuarteNeural*, etc), com processamento 100% na nuvem e resposta quase instantânea.

## 🛠️ Ferramentas Nativas (Tools)
O Agente Gemini tem acesso livre a essas ferramentas do ecossistema e sabe perfeitamente quando e como acioná-las:

### 🏠 Automação e Casa Inteligente
- 💡 **SmartHomeTool**: Integração completa com o **Home Assistant**. O Alfredo descobre todos os dispositivos da casa e controla luzes, TVs, ares-condicionados e interruptores inteligentes de forma natural ("Apague a luz da sala e ligue a TV").
- ⏱️ **TimerTool**: Criação de Cronômetros, Alarmes e Lembretes exatos, disparando alertas sonoros no alto-falante físico do satélite.

### 🎵 Entretenimento e Mídia
- 🎵 **MusicTool (Spotify Connect Nativo)**: O Alfredo funciona como uma verdadeira "Caixa de Som Inteligente" (estilo Alexa). Com um daemon próprio (`spotifyd`), ele aceita comandos diretos ("Toque The Beatles", "Próxima música", "Pause", "Volume máximo") e gerencia a fila do Spotify nativamente pelo alto-falante, sem precisar de um celular pareado. Possui também fallback de segurança via YouTube (`yt-dlp`).
- 📰 **NewsTool**: Manchetes recentes e notícias de última hora do Brasil e do mundo (via NewsAPI).

### 🧠 Memória e Produtividade
- 🧠 **MemoryTool**: Memória de longo prazo persistente. O Alfredo memoriza fatos vitais sobre o usuário (alergias, hábitos, números da sorte) e injeta esse contexto "Always-On" em todas as respostas futuras silenciosamente.
- 📝 **ListTool**: Gerenciamento de Listas de Compras e Tarefas ("Adicione pão na minha lista de mercado").
- 📅 **CalendarTool**: Leitura e agendamento de eventos e compromissos.

### 🧭 Utilidades Gerais
- 🕒 **TimeTool**: Informa hora e data com base no fuso horário do servidor.
- 🌤️ **WeatherTool**: Previsão do tempo local e global (via Open-Meteo).
- 🚗 **TrafficTool**: Tempo de deslocamento em tempo real usando coordenadas GPS (Mapbox).

### 🎓 Habilidades Especiais
- 🍳 **RecipeTool**: Assistente de Enogastronomia. Guia o usuário em receitas culinárias **um passo de cada vez**, mantendo o contexto em banco de dados (pausa segura por horas), além de fazer harmonizações finas de vinhos e queijos.
- ☁️ **DreamTool**: Diário Psicanalítico de Sonhos. Ouve os relatos de sonhos do usuário, extrai a semântica via "Zero Latency Parsing" e exibe uma nuvem de palavras animada (Word Cloud) no Dashboard.
- 🏫 **QuizTool**: Modo de Tarefa Escolar. Auxilia crianças fazendo quizzes interativos de matemática e história, avaliando as respostas verbalmente e mantendo a dinâmica lúdica. O estado da sessão é persistido no banco de dados.

### 💬 Conversação Nativa
- Se nenhuma ferramenta for necessária, o Alfredo usa seu vasto conhecimento geral para bater papo, responder dúvidas complexas, traduzir textos ou contar piadas de forma puramente fluida.

## 🖥️ Arquitetura de Hardware

### O Orquestrador (Servidor Central)
- **Hardware:** HP Pavilion X360 11-N226BR
- **CPU:** Intel Celeron N2830 Dual Core 2.16GHz
- **RAM:** 4GB DDR3L + ZRAM
- **SO:** Ubuntu Server 26.04 LTS (Resolute)
- **Desempenho:** Todo o processamento de áudio (STT/TTS) e inferência foi retirado da CPU e enviado para a nuvem. O Celeron atua apenas como Roteador de Tráfego de Rede, API FastAPI e acesso ao Banco de Dados SQLite.

### Os Satélites (Terminais)
- **Hardware:** DeepSeek AI Voice Robot Ball (ESP32-S3 WROOM-1-N16R8)
- **Display:** 1.28" 240x240 IPS (GC9A01)
- **Touch:** CST816 (I2C)

## 📁 Estrutura do Projeto
- `core/`: Motor principal em Python (FastAPI, Agente Gemini, Integração TTS/STT, Banco de Dados).
- `firmware/`: Código fonte C++ do ESP32-S3 (ESP-IDF / PlatformIO).
- `devices/`: Gerenciamento e status de saúde dos satélites.
- `integrations/`: Conectores externos (Weather, ContaComigo, APIs).
- `dashboard/`: Painel web de administração visual ("Obsidian & Brass" v3.0) para gerenciar rotinas, memória, status da API e integrações do Alfredo OS.

---
*Desenvolvido com ❤️ sob os princípios de Clean Code, Domain-Driven Design (DDD) e Agentic Frameworks.*
