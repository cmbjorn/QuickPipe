#!/usr/bin/env bash
# Kill anything on port 8502, then start Quickpipe fresh.
set -e
echo "Installing / updating dependencies..."
pip install -q -r requirements.txt
echo "Stopping any running Quickpipe instances..."
lsof -ti :8502 | xargs kill -9 2>/dev/null || true
pkill -f "streamlit run quickpipe_app.py" 2>/dev/null || true
sleep 1
echo "Starting Quickpipe on http://127.0.0.1:8502 ..."
streamlit run quickpipe_app.py --server.address=127.0.0.1 --server.port=8502
