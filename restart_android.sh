#!/bin/bash
tmux kill-server || true
tmux new-session -d -s alfredo 'while true; do bash ~/alfredo-core/start_satellite_v2.sh; sleep 5; done'
