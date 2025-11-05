#!/usr/bin/env bash
set -euo pipefail
export DATA_ACCESS_ENABLED=0
export PORT=8001
cd "$(dirname "$0")/SecureTextDrive-Backend"
python3 app.py

