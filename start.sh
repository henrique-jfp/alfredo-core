#!/bin/bash
# Inicia a API e o Satélite usando o systemd
sudo systemctl start alfredo-api.service
sudo systemctl start alfredo-satellite.service

# Inicia o Spotifyd isolado (pois ele exige ambiente pulse de usuário)
pkill -f spotifyd || true
nohup bash -c 'cd ~/alfredo-core && \
  export XDG_RUNTIME_DIR=/run/user/1000 && \
  export PULSE_SERVER=unix:/run/user/1000/pulse/native && \
  if [ -f config/spotifyd.conf ]; then \
    ./spotifyd --no-daemon --config-path config/spotifyd.conf; \
  else \
    echo "ERRO: config/spotifyd.conf não encontrado"; \
    exit 1; \
  fi' > spotifyd.log 2>&1 &

echo "Alfredo iniciado com sucesso via SystemD."
