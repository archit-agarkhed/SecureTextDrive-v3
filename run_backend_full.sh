#!/usr/bin/env bash
set -euo pipefail
export DATA_ACCESS_ENABLED=1
export PORT=8000
cd "$(dirname "$0")/SecureTextDrive-Backend"
python3 app.py

