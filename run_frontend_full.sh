#!/usr/bin/env bash
set -euo pipefail
export BACKEND_URL=http://127.0.0.1:8000/api
export PORT=5000
cd "$(dirname "$0")/SecureTextDrive-FrontEnd"
python3 app.py

