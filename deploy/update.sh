#!/bin/bash
# =================================================================
# ALFREDO HOME OS - SCRIPT DE ATUALIZAÇÃO
# =================================================================

set -e

echo "[1/4] Puxando atualizações do repositório (Git Pull)..."
git pull origin main

echo "[2/4] Atualizando dependências..."
source venv/bin/activate
pip install -r requirements.txt

# Espaço reservado para eventuais migrações de banco de dados (Alembic)
# echo "[3/4] Rodando migrações do banco de dados..."
# alembic upgrade head

echo "[4/4] Reiniciando serviços Systemd..."
sudo systemctl restart alfredo-api.service
sudo systemctl restart alfredo-satellite.service

echo "Atualização concluída com sucesso! Verificando status da API..."
sudo systemctl status alfredo-api.service --no-pager | grep Active
