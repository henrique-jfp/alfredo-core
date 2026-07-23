#!/bin/bash
# Inicia o satélite Alfredo no Android (Termux) usando o satellite_server/main.py
cd /data/data/com.termux/files/home/alfredo-core
export $(cat .env.satellite | xargs)
exec python3 -c "import sys; sys.path.insert(0, '.'); from devices.satellite_server.main import main; main()"
