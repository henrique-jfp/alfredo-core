#!/bin/bash
# Install vosk in Termux and download the small model

echo "Instalando dependencias do Vosk..."
# No termux, pip install vosk as vezes falha se nao tiver build-essential
# Mas existe wheel pre-compilado para aarch64!
pip install vosk

echo "Baixando modelo small..."
mkdir -p /data/data/com.termux/files/home/alfredo-core/models
cd /data/data/com.termux/files/home/alfredo-core/models
if [ ! -d "vosk-model-small-pt-0.3" ]; then
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
    unzip -q vosk-model-small-pt-0.3.zip
    rm vosk-model-small-pt-0.3.zip
fi

echo "Atualizando .env.satellite..."
cd /data/data/com.termux/files/home/alfredo-core
if grep -q "VOSK_MODEL_PATH" .env.satellite; then
    sed -i 's|VOSK_MODEL_PATH=.*|VOSK_MODEL_PATH=/data/data/com.termux/files/home/alfredo-core/models/vosk-model-small-pt-0.3|' .env.satellite
else
    echo "VOSK_MODEL_PATH=/data/data/com.termux/files/home/alfredo-core/models/vosk-model-small-pt-0.3" >> .env.satellite
fi

# Desativa VAD-only fallback, pois agora temos Wake Word local (Vosk)
sed -i 's|VAD_ONLY_FALLBACK=.*|VAD_ONLY_FALLBACK=False|' .env.satellite
if ! grep -q "VAD_ONLY_FALLBACK" .env.satellite; then
    echo "VAD_ONLY_FALLBACK=False" >> .env.satellite
fi

echo "Pronto!"
