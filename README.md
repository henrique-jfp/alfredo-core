# Alfredo Home OS 🎩

Alfredo Home OS é um ecossistema completo de assistente doméstico inteligente. Projetado do zero para ser modular, altamente expressivo e incrivelmente rápido, com foco na fluidez conversacional e em arquitetura orientada a Agentes Autônomos.

## 🌟 Filosofia "Agentic"
O Alfredo abandonou o modelo clássico de assistentes engessados por "palavras-chave".
1. **Cérebro Agente:** Utilizamos o modelo **Gemini 2.5 Flash** não apenas como "Fallback", mas como o **Roteador Principal**. Ele interpreta cada frase de forma contextual e decide autonomamente quais ferramentas (Tools) do sistema deve invocar (ou se deve usar mais de uma ao mesmo tempo).
2. **Satélites "Burros" (Terminais):** Os dispositivos espalhados pela casa (baseados em ESP32-S3) servem estritamente como interfaces de I/O (microfone, alto-falante e display). Nenhum processamento pesado ocorre nas bordas.
3. **Custo Próximo a Zero (Nuvem Inteligente):** O HP Celeron atua como orquestrador, delegando tarefas pesadas de IA para a nuvem através de APIs gratuitas ou de altíssimo custo-benefício:
   - **STT (Fala p/ Texto):** Whisper-Large-V3 rodando em velocidade absurda via API do **Groq**.
   - **Raciocínio & Roteamento:** **Gemini 2.5 Flash** (Rápido, inteligente e adaptável a chamadas de ferramentas).
   - **TTS (Texto p/ Fala):** **Microsoft Edge TTS** (Voz Neural *Francisca* ou *Antonio*), com processamento 100% na nuvem e resposta quase instantânea.

## 🛠️ Ferramentas Nativas (Tools)
O Agente Gemini tem acesso livre a essas ferramentas do ecossistema e sabe perfeitamente quando e como acioná-las:
- 🕒 **TimeTool**: Informa hora e data com base no fuso horário do servidor.
- 🌤️ **WeatherTool**: Previsão do tempo local e global (via Open-Meteo).
- ⏱️ **TimerTool**: Criação de Cronômetros, Alarmes e Lembretes (persistentes em SQLite).
- 📝 **ListTool**: Gerenciamento de Listas de Compras e Tarefas ("Adicione pão na minha lista").
- 📅 **CalendarTool**: Leitura e agendamento de eventos e compromissos.
- 🚗 **TrafficTool**: Tempo de deslocamento em tempo real usando coordenadas GPS (Mapbox).
- 📰 **NewsTool**: Manchetes recentes do Brasil e do mundo (NewsAPI).
- 🎵 **MusicTool**: Integração e controle OAuth nativo do Spotify ("Toque Beatles").
- 🧠 **Conversação Geral**: Se nenhuma ferramenta for necessária, o Alfredo usa seu vasto conhecimento geral para bater papo, responder dúvidas ou fazer piadas de forma fluida (estilo Alexa/ChatGPT).

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
- `dashboard/`: Painel web de administração visual para gerenciar o Alfredo.

---
*Desenvolvido com ❤️ sob os princípios de Clean Code, Domain-Driven Design (DDD) e Agentic Frameworks.*
