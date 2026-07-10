# 🧠 Alfredo Core — Guia Oficial do Servidor (pvserver)

Este é o manual de sobrevivência do servidor Linux que hospeda o **Alfredo Home OS**. 
Aqui estão catalogados **todos os comandos** que você vai precisar no dia a dia para atualizar, reiniciar, ver logs e consertar problemas.

---

## 🏗️ 1. Arquitetura Atual (`systemd`)

Nós abandonamos os processos soltos (`nohup` e `screen`)! Agora o Alfredo é um cidadão de primeira classe no Linux, rodando através do gerenciador de serviços oficial (`systemd`). Isso significa que ele reinicia sozinho se der erro e liga junto com o computador.

Temos dois serviços rodando o tempo todo no fundo do sistema:
1. **`alfredo-api.service`**: O cérebro (FastAPI, Roteamento, Gemini, Dashboard).
2. **`alfredo-satellite.service`**: O ouvido (Microfone USB, OpenWakeWord 'Alexa', VAD).

---

## 🚀 2. Comandos do Dia a Dia

Para rodar qualquer um destes comandos, você primeiro precisa entrar no servidor:
```bash
ssh pvserver
```

### 📦 2.1 Como fazer o Deploy / Atualizar o Código
Sempre que você programar algo novo no Windows e fizer o `commit/push` pro GitHub, rode isso no servidor para aplicar:
```bash
cd ~/alfredo-core
git pull origin main
bash deploy/update.sh
```
*(O script `update.sh` instala bibliotecas novas automaticamente e reinicia os serviços no final).*

---

### 🔄 2.2 Ligar, Desligar e Reiniciar (Serviços)

```bash
# Reiniciar tudo de uma vez (O comando que salva vidas)
sudo systemctl restart alfredo-api.service alfredo-satellite.service

# Parar tudo (se quiser calar o Alfredo)
sudo systemctl stop alfredo-api.service alfredo-satellite.service

# Ligar tudo
sudo systemctl start alfredo-api.service alfredo-satellite.service

# Ver se os serviços estão verdes e rodando felizes
sudo systemctl status alfredo-api.service alfredo-satellite.service
```

Se precisar reiniciar apenas uma parte específica:
```bash
# Reiniciar só o Cérebro (não corta a escuta)
sudo systemctl restart alfredo-api.service

# Reiniciar só o Ouvido (recalibra o microfone USB)
sudo systemctl restart alfredo-satellite.service
```

---

## 🕵️ 3. Como ver os Logs (O que ele está fazendo?)

Se deu algum erro ou você quer ver a transcrição do que ele entendeu, você precisa olhar os logs.

### 📝 Logs do Cérebro (API, Gemini, Roteador, TV)
Tudo que a API faz fica gravado no arquivo `uvicorn.log`. Para ver ao vivo:
```bash
cd ~/alfredo-core
tail -f uvicorn.log
```
*(Para parar de ver ao vivo, aperte `CTRL + C`)*.

Para pesquisar erros graves no histórico da API:
```bash
grep -i "error" ~/alfredo-core/uvicorn.log
```

### 🎙️ Logs do Satélite (Microfone, Wake Word, Echo)
Tudo que o microfone escuta fica gravado no `satellite.log`. Para ver ao vivo:
```bash
cd ~/alfredo-core
tail -f satellite.log
```

Se o serviço do Linux acusar algum erro estrutural, você também pode ver os logs do próprio gerenciador `systemd`:
```bash
sudo journalctl -u alfredo-api.service -n 50 --no-pager
sudo journalctl -u alfredo-satellite.service -n 50 --no-pager
```

---

## 🛠️ 4. Comandos de Manutenção

### 4.1 Entrar no Ambiente Virtual do Python
Se você precisar rodar um script manual ou instalar um pacote no servidor na mão:
```bash
cd ~/alfredo-core
source .venv/bin/activate
```
*(Você vai ver um `(.venv)` aparecer no começo da linha do terminal).*

### 4.2 Consertar Microfone Bugado (Hardware)
Se a placa de som USB der pau ou for desconectada, o satélite vai reclamar nos logs.
1. Tire e coloque o microfone na porta USB física.
2. Descubra se o Linux reconheceu ele rodando:
```bash
# Tem que aparecer a USB_Camera na lista
~/alfredo-core/.venv/bin/python -c 'import sounddevice; print(sounddevice.query_devices())'
```
3. Reinicie o satélite:
```bash
sudo systemctl restart alfredo-satellite.service
```

### 4.3 Matar clones fantasmas
Se por um acaso o antigo `start.sh` com nohup for rodado acidentalmente e duplicar o Alfredo (causando ecos e bizarrices), mate os falsos e preserve os oficiais assim:
```bash
# 1. Pare os oficiais primeiro
sudo systemctl stop alfredo-api.service alfredo-satellite.service

# 2. Aniquile qualquer processo rebelde
sudo killall python3
sudo killall uvicorn

# 3. Ligue os oficiais novamente
sudo systemctl start alfredo-api.service alfredo-satellite.service
```

---

## 🌐 5. Rede Externa
Se o painel web parar de acessar de fora de casa, o túnel da Cloudflare pode ter caído:
```bash
sudo systemctl restart cloudflared
```

---

**Status Atual:** 🟢 Rodando puro e liso via Systemd!
**Última Atualização:** Julho de 2026