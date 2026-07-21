# Alfredo Android Satellite (M21s) 🚀

Este diretório contém o código do satélite Android (projetado especificamente para rodar no Samsung M21s via Termux + Ubuntu PRoot).

## O que é esse Satélite?
Na nossa arquitetura, o satélite é apenas **a boca e os ouvidos** do Alfredo.
1. **Ouvidos:** Ele fica rodando o `OpenWakeWord` localmente o tempo todo. Assim que você diz *"Alexa"*, ele começa a gravar sua voz.
2. **Cérebro (Servidor):** A gravação é enviada via WebSocket para o Servidor Principal (Raspberry/Desktop). Lá o servidor transcreve, pensa (LLM), acende a luz se precisar, e gera o áudio da resposta (MP3).
3. **Boca:** O servidor manda os bytes do MP3 de volta para cá, e o script usa o `ffplay` conectado ao PulseAudio para tocar a resposta.

## Roteamento de Áudio (JBL / P2 / Bluetooth)
**O roteamento é 100% automático e gerido pelo Android!**
Graças à configuração do PulseAudio com o `module-sles-sink` (OpenSL ES), o áudio do Ubuntu está espetado direto no motor nativo do celular. 
- Se a JBL for desconectada do P2 ou Bluetooth cair, o Android joga a voz para o alto-falante do celular automaticamente.
- Se plugar de novo, o áudio volta para a JBL na hora, sem precisar reiniciar o script!

---

## 🛠️ Comandos e Manutenção do Dia a Dia

Sempre que acessar o celular (via SSH ou direto na tela), a primeira coisa a fazer é **entrar no Ubuntu**:
```bash
proot-distro login ubuntu
```

### 1. Atualizar o Código
```bash
cd ~/alfredo-core
git pull origin main
```

### 2. Iniciar o Satélite (Modo Imortal em Segundo Plano)
O script `start_satellite_loop.sh` garante que o Alfredo não morra (se cair a internet, ele reinicia sozinho). Usamos o `tmux` para ele rodar "escondido".
```bash
tmux new-session -d -s alfredo "bash ~/alfredo-core/scripts/start_satellite_loop.sh"
```

### 3. Como "espiar" se ele está funcionando? (Logs)
Se quiser ver a telinha do Alfredo trabalhando enquanto você fala:
```bash
tmux attach -t alfredo
```
**🚨 IMPORTANTE:** Para sair dessa tela **sem desligar o Alfredo**, faça o atalho:
Pressione `Ctrl + B`, solte as teclas, e então aperte a tecla `D` (de Detach).

### 4. Caça aos Zumbis (Matar instâncias travadas)
Se o microfone bugar ou achar que tem cópias fantasmas dele rodando, passe a foice:
```bash
# Mata todos os processos Python do Alfredo:
pkill -f android_continuous_satellite.py

# Fecha todas as sessões "escondidas" do Tmux:
tmux kill-server
```

---

## 🔋 Configurações Críticas no Aparelho Android
Para que ele funcione **24 horas por dia, 7 dias por semana** como uma verdadeira Alexa de cabeceira, o Android não pode "dormir".

1. **Wake Lock:** Dentro do app Termux (na tela preta do Android), rode o comando `termux-wake-lock`. Isso cria uma notificação fixa que impede o processador de hibernar quando a tela apagar.
2. **Otimização de Bateria:** Vá nas `Configurações do Celular > Aplicativos > Termux > Bateria` e mude para **Não Restrito** (Sem otimização). Senão o Android mata o app de madrugada.
