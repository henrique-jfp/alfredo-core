# Alfredo Home OS

Alfredo Home OS é um ecossistema completo de assistente doméstico, projetado do zero para ser modular, escalável e ter **custo mensal zero**.

## Filosofia
- **Servidor Local:** Toda a inteligência (STT, TTS, Lógica, Memória) reside no servidor central.
- **Satélite "Burro":** Os terminais satélites (baseados em ESP32-S3) são estritamente interfaces de I/O (microfone, alto-falante, display). Não executam IA ou processamento pesado.
- **Custo Zero:** Uso de ferramentas e APIs gratuitas:
  - STT: Vosk (Local)
  - TTS: Piper (Local)
  - Clima: Open-Meteo
  - IA Fallback: Groq (Rápido) alternado com Gemini (Geral)

## Arquitetura de Hardware
### Servidor
- Hardware: HP Pavilion X360 11-N226BR
- CPU: Intel Celeron N2830 Dual Core 2.16GHz
- RAM: 4GB DDR3L + ZRAM
- SO: Ubuntu Server 24.04 LTS

### Satélites
- Hardware: DeepSeek AI Voice Robot Ball (ESP32-S3 WROOM-1-N16R8)
- Display: 1.28" 240x240 IPS (GC9A01)
- Touch: CST816 (I2C)

## 🧠 Habilidades Nativas (Skills)
O núcleo do Alfredo já processa diversas intenções de forma offline ou via integrações gratuitas:
- **TimeSkill**: Fornece hora e data baseada no fuso horário do servidor.
- **WeatherSkill**: Previsão do tempo local (cacheada via Open-Meteo).
- **TimerSkill**: Cronômetros, Alarmes e Lembretes textuais com background scheduler persistente em SQLite.
- **ListSkill**: Gerenciador persistente para Listas de Compras e Tarefas.
- **CalendarSkill**: Agendamento de eventos e reuniões com consulta por dia.
- **TrafficSkill**: Estimativa de trânsito em tempo real para o endereço de trabalho usando Mapbox.
- **NewsSkill**: Resumo das últimas manchetes utilizando NewsAPI.
- **MusicSkill**: Tocar e controlar músicas nativamente no Spotify (via Autenticação OAuth remota).
- **FallbackSkill**: Módulo de IA (Groq/Gemini) que assume o controle e responde a qualquer pergunta não mapeada.

## Estrutura do Projeto
- `core/`: Motor principal (Voz, Roteador de Intenções, Memória).
- `firmware/`: Código fonte do ESP32-S3 (ESP-IDF).
- `devices/`: Gerenciamento e status dos satélites no servidor.
- `integrations/`: Conectores externos (Weather, IA, ContaComigo, HomeAssistant).
- `dashboard/`: Painel web de administração.

Desenvolvido com ❤️ sob os princípios de Clean Code e Domain-Driven Design (DDD).
