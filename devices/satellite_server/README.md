# Satélite do Servidor (HP Pavillion)

Este diretório contém o código do **satélite de software** que roda no próprio servidor central (HP Pavillion) para captar o áudio ambiente da sala e reproduzir os retornos de voz do Alfredo.

## O que é?
Embora o Alfredo Core possua inteligência centralizada, ele se comunica com o mundo físico através de "satélites". Os satélites comuns são placas físicas (ESP32) distribuídas pela casa.
Como o servidor central já está localizado fisicamente na sala e possui microfone/caixa de som, ele roda uma **instância local** de satélite para economizar hardware.

O arquivo `main.py` roda em segundo plano e atua **exatamente** como um microcontrolador externo atuaria:
1. Escuta a palavra de ativação offline (via Vosk).
2. Captura o áudio com VAD (Voice Activity Detection).
3. Envia os bytes de áudio para a porta WebSocket do servidor (`http://localhost:10001/api/ws/satellite/server-satellite-sala`).
4. Recebe payloads de áudio e os reproduz na caixa de som local via `sounddevice`.

## Execução
Este satélite é iniciado automaticamente pelo script raiz `/start.sh` na sessão `screen` de nome `satellite`.
