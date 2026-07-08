#!/bin/bash
pkill -f alfredo-core || true
pkill -f spotifyd || true
export XDG_RUNTIME_DIR=/run/user/1000
export PULSE_SERVER=unix:/run/user/1000/pulse/native
nohup bash -c 'cd ~/alfredo-core && source .venv/bin/activate && uvicorn core.api.main:app --host 0.0.0.0 --port 10001' > uvicorn.log 2>&1 &
nohup bash -c 'cd ~/alfredo-core && export XDG_RUNTIME_DIR=/run/user/1000 && export PULSE_SERVER=unix:/run/user/1000/pulse/native && source .venv/bin/activate && python3 -u devices/satellite_server/main.py' > satellite.log 2>&1 &
nohup bash -c 'cd ~/alfredo-core && export XDG_RUNTIME_DIR=/run/user/1000 && export PULSE_SERVER=unix:/run/user/1000/pulse/native && ./spotifyd --no-daemon --config-path spotifyd.conf' > spotifyd.log 2>&1 &
echo "Started."
