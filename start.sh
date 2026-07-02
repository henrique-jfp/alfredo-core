#!/bin/bash
pkill -f alfredo-core || true
screen -S uvicorn -dm bash -c 'cd ~/alfredo-core && source .venv/bin/activate && uvicorn core.api.main:app --host 0.0.0.0 --port 10001 | tee uvicorn.log'
screen -S satellite -dm bash -c 'cd ~/alfredo-core && source .venv/bin/activate && python3 -u scripts/local_satellite.py | tee satellite.log'
echo "Started."
