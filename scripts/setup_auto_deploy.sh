#!/bin/bash
# Script para configurar o timer do Systemd (roda a cada minuto)

mkdir -p ~/.config/systemd/user

# Criar o arquivo de serviço
cat <<EOF > ~/.config/systemd/user/alfredo-deploy.service
[Unit]
Description=Alfredo Auto Deploy Service
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash /home/pvserver/alfredo-core/scripts/auto_deploy.sh
WorkingDirectory=/home/pvserver/alfredo-core
StandardOutput=append:/home/pvserver/alfredo-core/logs/auto_deploy.log
StandardError=append:/home/pvserver/alfredo-core/logs/auto_deploy.log
EOF

# Criar o arquivo do timer
cat <<EOF > ~/.config/systemd/user/alfredo-deploy.timer
[Unit]
Description=Alfredo Auto Deploy Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Unit=alfredo-deploy.service

[Install]
WantedBy=timers.target
EOF

# Recarregar daemon e habilitar
systemctl --user daemon-reload
systemctl --user enable --now alfredo-deploy.timer

echo "Auto Deploy configurado e rodando a cada 1 minuto via Systemd!"
