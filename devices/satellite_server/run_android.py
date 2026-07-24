"""Runner script for Android satellite.
Reads .env.satellite from home dir and starts the satellite server.
"""
import os
import sys

HOME = "/data/data/com.termux/files/home"
PROJECT = os.path.join(HOME, "alfredo-core")
ENV_PATH = os.path.join(PROJECT, ".env.satellite")

# Carrega .env.satellite manualmente no environ
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ[key.strip()] = val.strip()

sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

from devices.satellite_server.main import main
main()
