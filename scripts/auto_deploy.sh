#!/bin/bash
# Script para verificar o GitHub e atualizar automaticamente o servidor

cd "$(dirname "$0")/.." # Vai para a raiz do alfredo-core
REPO_DIR=$(pwd)

# Busca as novidades do remote sem alterar arquivos locais
git fetch origin main >/dev/null 2>&1

# Compara o commit local atual com o commit remoto
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Novas atualizações encontradas! Atualizando de $LOCAL para $REMOTE..."
    
    # Faz o pull forçado para garantir que está idêntico ao GitHub
    git reset --hard origin/main
    
    # Atualiza as dependências caso o requirements.txt tenha mudado
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        pip install -r requirements.txt >/dev/null 2>&1
    fi
    
    # Reinicia o servidor
    echo "$(date): Reiniciando instâncias..."
    bash start.sh
    echo "$(date): Deploy automático finalizado com sucesso."
fi
