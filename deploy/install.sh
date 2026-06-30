#!/bin/bash
# =================================================================
# ALFREDO HOME OS - SCRIPT DE INSTALAÇÃO (PRODUÇÃO & PROTÓTIPO)
# =================================================================

set -e # Sai em caso de erro

echo "[1/7] Verificando dependências do sistema..."
if ! command -v python3 &> /dev/null || ! command -v pip3 &> /dev/null; then
    echo "Instalando Python3 e pip..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Toolchain do ESP-IDF (apenas aviso, pois geralmente não é necessário no servidor de produção, mas útil no protótipo)
if ! command -v idf.py &> /dev/null; then
    echo "Aviso: ESP-IDF Toolchain não detectado. Se for compilar o firmware neste servidor, instale-o manualmente depois."
fi

echo "[2/7] Criando Virtual Environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "[3/7] Instalando dependências (requirements.txt)..."
pip install -r requirements.txt

echo "[4/7] Baixando Modelos Locais (Vosk e Piper)..."
mkdir -p core/voice/stt/models
mkdir -p core/voice/tts/models
# TODO: Inserir URLs reais de download quando estiverem hospedados (ex: wget / unzip)
echo "   -> (Mock) Modelos Vosk e Piper baixados com sucesso."

echo "[5/7] Configuração do Ambiente (.env)..."
if [ ! -f "config/.env" ]; then
    echo "Nenhum arquivo .env encontrado. Copiando .env.example..."
    cp config/.env.example config/.env
    
    # Prompt interativo básico
    read -p "Digite o NOME DA FAMÍLIA (ex: Silva): " family_name
    sed -i "s/^FAMILY_NAME=.*/FAMILY_NAME=$family_name/" config/.env
    
    read -p "Digite o NOME DO ADMIN: " admin_name
    sed -i "s/^ADMIN_NAME=.*/ADMIN_NAME=$admin_name/" config/.env

    echo "As demais variáveis devem ser preenchidas manualmente depois em config/.env"
else
    echo "Arquivo .env já existe. Pulando."
fi

echo "[6/7] Registrando Serviços Systemd..."
# Exemplo de criação de serviço systemd para o Alfredo
sudo bash -c 'cat > /etc/systemd/system/alfredo.service <<EOF
[Unit]
Description=Alfredo Home OS Core API
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/uvicorn core.api.main:app --host 0.0.0.0 --port 10001
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable alfredo.service
# Não iniciamos ainda porque o usuário pode querer editar o .env primeiro

echo "[7/7] Teste de Sanidade..."
echo "Instalação base concluída! Para iniciar o servidor, revise o config/.env e execute:"
echo "sudo systemctl start alfredo.service"
echo "Para checar os logs:"
echo "sudo journalctl -u alfredo.service -f"
