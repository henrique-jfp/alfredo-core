#!/bin/bash
echo "========================================="
echo " ALFREDO SATELLITE - MODO IMORTAL"
echo "========================================="

# Garante que o PulseAudio está rodando corretamente (Mata o antigo e inicia o novo)
echo "[1/3] Iniciando servidor de áudio (PulseAudio)..."
pulseaudio -k 2>/dev/null
pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --load="module-sles-source" --load="module-sles-sink" --exit-idle-time=-1

echo "[2/3] Entrando na pasta do projeto..."
# Descobre o diretório raiz independente de onde o script foi chamado
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

echo "[3/3] Iniciando loop de ressurreição..."
# Loop infinito: Se a internet cair, o websocket morre, o python fecha.
# O loop espera 5 segundos e liga o python de novo.
while true; do
    echo "-> (Re)iniciando satélite..."
    python3 scripts/android_continuous_satellite.py
    
    echo "-> Satélite desconectado ou falhou. Tentando novamente em 5 segundos..."
    sleep 5
done
