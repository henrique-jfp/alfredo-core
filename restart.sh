#!/bin/bash
# Reinicia a API e o Satélite usando o systemd
sudo systemctl restart alfredo-api.service
sudo systemctl restart alfredo-satellite.service

echo "Alfredo reiniciado com sucesso via SystemD."
