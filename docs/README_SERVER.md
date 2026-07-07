# 🧠 Alfredo Core — Guia do Servidor (pvserver)

Referência técnica completa para operação, manutenção e deploy do servidor que hospeda o **Alfredo Home OS**. Este documento cobre **todos** os comandos necessários para iniciar, reiniciar e desligar cada componente do ecossistema.

---

## 💻 1. Hardware do Servidor

| Spec | Detalhe |
| :--- | :--- |
| **Modelo** | HP Pavilion X360 11-N226BR |
| **CPU** | Intel Celeron N2830 (Dual Core @ 2.16GHz) |
| **RAM** | 4GB DDR3L + 4GB Swap + ZRAM |
| **SSD** | 120GB (~450 MB/s leitura) |
| **SO** | Ubuntu Server 24.04 LTS (Headless) |
| **Nobreak** | Bateria interna do notebook (3-5h de autonomia) |
| **Microfone** | USB (no rack da TV, captura voz a ~3m do sofá) |
| **Áudio** | Saída P2 + amplificação via `sox` (3x) |

> **Nota:** O notebook fica com a tampa fechada. O `logind.conf` está configurado para ignorar o fechamento da tampa (`HandleLidSwitch=ignore`).

---

## 🏗️ 2. Arquitetura do Ecossistema

```
┌─────────────────────────────────────────────────────────┐
│                    SERVIDOR (pvserver)                   │
│                                                         │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  screen: uvicorn │    │   screen: satellite         │ │
│  │                  │    │                             │ │
│  │  FastAPI :10001  │◄───│  local_satellite.py         │ │
│  │  ├─ /api/voice   │    │  ├─ Vosk (Wake Word)       │ │
│  │  ├─ /api/ws/*    │    │  ├─ WebRTC VAD             │ │
│  │  ├─ /api/dashboard│   │  ├─ sounddevice (mic USB)  │ │
│  │  └─ /api/spotify │    │  └─ sox + aplay (speaker)  │ │
│  └─────────────────┘    └─────────────────────────────┘ │
│                                                         │
│  ┌─────────────────┐    ┌───────────────┐               │
│  │  Cloudflare     │    │  AdGuard Home │               │
│  │  Tunnel         │    │  :53 / :80    │               │
│  └─────────────────┘    └───────────────┘               │
└─────────────────────────────────────────────────────────┘
```

O Alfredo roda em **2 processos independentes** dentro de sessões `screen`:

| Sessão Screen | Processo | O que faz |
| :--- | :--- | :--- |
| `uvicorn` | `uvicorn core.api.main:app` | API FastAPI (STT, TTS, Router Gemini, Dashboard, WebSocket) |
| `satellite` | `python3 scripts/local_satellite.py` | Captura de áudio USB, Wake Word (Vosk), VAD, envio para API |

---

## 🚀 3. Comandos — Iniciar, Reiniciar, Desligar

### 3.1 🟢 Iniciar Tudo (do zero)

```bash
cd ~/alfredo-core
bash start.sh
```

Este comando mata qualquer processo antigo e sobe as duas sessões screen (uvicorn + satellite).

**Iniciar manualmente cada componente:**

```bash
# Servidor API (FastAPI/Uvicorn)
cd ~/alfredo-core
screen -S uvicorn -dm bash -c 'source .venv/bin/activate && uvicorn core.api.main:app --host 0.0.0.0 --port 10001 | tee uvicorn.log'

# Satélite Local (Microfone + Wake Word)
cd ~/alfredo-core
screen -S satellite -dm bash -c 'source .venv/bin/activate && python3 -u scripts/local_satellite.py | tee satellite.log'
```

### 3.2 🔄 Reiniciar Tudo

```bash
cd ~/alfredo-core
bash start.sh
```

O `start.sh` já faz `pkill -f alfredo-core` antes de subir, então serve como restart.

**Ou via Python (para ser chamado remotamente pelo MCP/Dashboard):**

```bash
cd ~/alfredo-core
source .venv/bin/activate
python3 scripts/server_restart.py
```

### 3.3 🔄 Reiniciar Apenas o Servidor API (sem tocar no satélite)

```bash
cd ~/alfredo-core
bash restart.sh
```

Ou manualmente:

```bash
# Mata só o uvicorn
kill $(ps aux | grep "alfredo-core.*uvicorn" | grep -v grep | awk '{print $2}') || true
screen -S uvicorn -X quit || true

# Sobe novamente
cd ~/alfredo-core
screen -S uvicorn -dm bash -c 'source .venv/bin/activate && uvicorn core.api.main:app --host 0.0.0.0 --port 10001 | tee uvicorn.log'
```

### 3.4 🔄 Reiniciar Apenas o Satélite (microfone/wake word)

```bash
# Mata a sessão do satélite
screen -S satellite -X quit || true
pkill -f "local_satellite.py" || true

# Sobe novamente
cd ~/alfredo-core
screen -S satellite -dm bash -c 'source .venv/bin/activate && python3 -u scripts/local_satellite.py | tee satellite.log'
```

### 3.5 🔴 Desligar Tudo

```bash
# Desligar apenas o Alfredo (API + Satélite)
pkill -f alfredo-core || true
screen -S uvicorn -X quit || true
screen -S satellite -X quit || true
```

```bash
# Desligar o servidor inteiro (cuidado!)
sudo shutdown -h now
```

### 3.6 📋 Resumo Rápido

| Ação | Comando |
| :--- | :--- |
| **Iniciar tudo** | `cd ~/alfredo-core && bash start.sh` |
| **Reiniciar tudo** | `cd ~/alfredo-core && bash start.sh` |
| **Reiniciar só API** | `cd ~/alfredo-core && bash restart.sh` |
| **Reiniciar só satélite** | `screen -S satellite -X quit; cd ~/alfredo-core && screen -S satellite -dm bash -c 'source .venv/bin/activate && python3 -u scripts/local_satellite.py \| tee satellite.log'` |
| **Desligar tudo** | `pkill -f alfredo-core; screen -S uvicorn -X quit; screen -S satellite -X quit` |
| **Restart via Python** | `cd ~/alfredo-core && source .venv/bin/activate && python3 scripts/server_restart.py` |
| **Desligar servidor** | `sudo shutdown -h now` |
| **Reiniciar servidor** | `sudo reboot` |

---

## 📺 4. Monitoramento — Logs e Sessões

### 4.1 Ver Logs ao Vivo

```bash
# Entrar na sessão do Uvicorn (API) — ver requests, erros, transcrições
tail -f ~/alfredo-core/uvicorn.log

# Entrar na sessão do Satélite — ver wake word, calibração, gravação
tail -f ~/alfredo-core/satellite.log
```

> **Para sair de uma sessão screen sem matar:** pressione `Ctrl+A` depois `D` (detach).

### 4.2 Ver Logs em Arquivo

```bash
# Logs do servidor API
tail -f ~/alfredo-core/uvicorn.log

# Logs do satélite (microfone)
tail -f ~/alfredo-core/satellite.log
```

### 4.3 Listar Sessões Screen Ativas

```bash
screen -ls
```

Saída esperada quando tudo está rodando:

```
There are screens on:
    12345.uvicorn    (Detached)
    12346.satellite  (Detached)
2 Sockets in /run/screen/S-pvserver.
```

### 4.4 Monitoramento de Saúde do Sistema

```bash
btop                          # Monitor visual (CPU, RAM, Temp, Disco)
free -h                       # Memória RAM e Swap
df -h                         # Espaço em disco
uptime                        # Tempo ligado
cat /sys/class/thermal/thermal_zone*/temp   # Temperatura CPU (divide por 1000 = °C)
```

### 4.5 Logs de Outros Serviços

```bash
sudo journalctl -u AdGuardHome -f     # AdGuard Home (DNS/Ad Blocker)
sudo journalctl -u cloudflared -f     # Cloudflare Tunnel
```

---

## 🔊 5. Configuração de Áudio (ALSA + Microfone USB)

### 5.1 Verificar Dispositivos de Áudio

```bash
arecord -l                    # Lista microfones (procure o USB)
aplay -l                      # Lista saídas de áudio
cat /proc/asound/cards        # Cards de áudio detectados
```

### 5.2 Ajustar Ganho do Microfone USB

```bash
# Listar controles disponíveis do microfone (card 1 = USB geralmente)
amixer -c 1 contents

# Ajustar volume de captura (80% é ideal — 100% causa clipping)
amixer -c 1 sset 'Mic' 80%

# Desativar AGC (Auto Gain Control) se disponível
amixer -c 1 sset 'Auto Gain Control' off
```

### 5.3 Ajustar Volume de Saída (Speaker)

```bash
amixer sset 'Master' 85%
```

### 5.4 Otimização do Buffer USB (Anti-Dropout)

```bash
# Adicionar configuração de buffer para USB audio
echo "options snd-usb-audio nrpacks=1" | sudo tee -a /etc/modprobe.d/alsa-base.conf

# Aplicar sem reiniciar
sudo modprobe -r snd-usb-audio && sudo modprobe snd-usb-audio
```

### 5.5 Testar Microfone Rapidamente

```bash
# Grava 5 segundos do microfone USB
arecord -D hw:1 -f S16_LE -r 16000 -c 1 -d 5 test_mic.wav

# Reproduz a gravação
aplay test_mic.wav
```

---

## 🌐 6. Rede e Portas

| Serviço | Porta Interna | Domínio Externo (Tunnel) | Protocolo |
| :--- | :--- | :--- | :--- |
| **Alfredo Core API** | `10001` | `alfredo.henriquedejesus.dev` | HTTP / WebSocket |
| **AdGuard Home** | `53` / `80` | Local (192.168.1.23) | DNS / HTTP |
| **Cloudflare Tunnel** | — | — | HTTPS (proxy) |

### 6.1 Gerenciar Cloudflare Tunnel

```bash
sudo systemctl status cloudflared      # Ver status
sudo systemctl restart cloudflared     # Reiniciar tunnel
sudo systemctl stop cloudflared        # Parar tunnel
```

### 6.2 Gerenciar AdGuard Home

```bash
sudo systemctl status AdGuardHome      # Ver status
sudo systemctl restart AdGuardHome     # Reiniciar
sudo systemctl stop AdGuardHome        # Parar
```

---

## 📦 7. Deploy e Atualização

### 7.1 Atualização Rápida (Git + Restart)

```bash
cd ~/alfredo-core
git pull origin main
bash start.sh
```

### 7.2 Atualização Completa (com dependências)

```bash
cd ~/alfredo-core
bash deploy/update.sh
```

Este script faz: `git pull` → `pip install -r requirements.txt` → `restart`.

### 7.3 Instalação do Zero

```bash
cd ~/alfredo-core
bash deploy/install.sh
```

Cria venv, instala dependências, baixa modelos Vosk/Piper, configura `.env` e registra o serviço `systemd`.

---

## ⚠️ 8. Manutenção e Cuidados

### 8.1 Limpeza de Logs e Espaço em Disco

```bash
# Limpar logs do journalctl (manter últimos 7 dias)
sudo journalctl --vacuum-time=7d

# Ver espaço usado
df -h /

# Limpar arquivos temporários do Alfredo
rm -f ~/alfredo-core/tmp/*.wav
rm -f ~/alfredo-core/request.wav ~/alfredo-core/response.wav ~/alfredo-core/response_loud.wav
```

### 8.2 Verificar se Tudo Está Rodando

```bash
# Checar screens
screen -ls

# Checar processos
ps aux | grep -E "uvicorn|local_satellite" | grep -v grep

# Testar API
curl -s http://localhost:10001/api/health | python3 -m json.tool
```

### 8.3 Configurações do Sistema

| Arquivo | O que configura |
| :--- | :--- |
| `~/alfredo-core/.env` | API keys (Groq, Gemini, Spotify, TMDB), coordenadas GPS, voz TTS |
| `~/alfredo-core/config/.env.example` | Template de referência com todas as variáveis |
| `/etc/logind.conf` | `HandleLidSwitch=ignore` (tampa fechada) |
| `/etc/modprobe.d/alsa-base.conf` | Buffer USB audio (`nrpacks=1`) |

### 8.4 Backup

```bash
# Backup do banco de dados
cp ~/alfredo-core/alfredo_memory.db ~/alfredo-core/alfredo_memory.db.bak

# Backup das configurações
cp ~/alfredo-core/.env ~/alfredo-core/.env.bak
```

---

## 📁 9. Estrutura de Pastas

```
~/alfredo-core/
├── core/                      # Motor principal
│   ├── api/                   # FastAPI (main.py, dashboard.py, satellite.py, spotify.py)
│   ├── brain/                 # Gemini Router + Skills + Memory
│   ├── services/              # Scheduler, Media Service
│   └── voice/                 # STT (Groq Whisper) + TTS (Edge TTS)
├── scripts/                   # Scripts operacionais
│   ├── local_satellite.py     # 🎙️ Satélite de produção (mic USB + Vosk + VAD)
│   ├── mock_satellite.py      # Satélite de teste (Windows/PyAudio)
│   ├── server_restart.py      # Restart via Python (usado pelo MCP)
│   ├── download_vosk.py       # Download do modelo Vosk
│   └── fix_satellite.py       # Hotfix de produção
├── deploy/                    # Scripts de instalação e atualização
│   ├── install.sh             # Instalação completa do zero
│   └── update.sh              # Atualização (git pull + pip + restart)
├── dashboard/                 # Painel web de administração
├── devices/                   # Gerenciamento de satélites (ESP32)
├── firmware/                  # Código C++ dos satélites ESP32-S3
├── integrations/              # Conectores externos (Weather, etc)
├── docs/                      # Documentação (este arquivo)
├── start.sh                   # 🟢 Iniciar tudo (uvicorn + satellite)
├── restart.sh                 # 🔄 Reiniciar só o servidor API
├── .env                       # Variáveis de ambiente (secrets)
├── requirements.txt           # Dependências Python
├── alfredo_memory.db          # Banco SQLite (memória, listas, timers)
└── logs/                      # Logs persistentes
```

---

**Status:** 🟢 Operacional
**Servidor:** pvserver (HP Pavilion X360)
**Última atualização:** Julho de 2026