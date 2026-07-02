kill $(ps aux | grep "alfredo-core.*uvicorn" | grep -v grep | awk '{print $2}') || true
screen -S uvicorn -X quit || true
cd ~/alfredo-core
screen -S uvicorn -dm bash -c "source .venv/bin/activate && uvicorn core.api.main:app --host 0.0.0.0 --port 10001 | tee uvicorn.log"
