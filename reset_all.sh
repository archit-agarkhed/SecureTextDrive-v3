#!/usr/bin/env bash
set -euo pipefail

# Optional: override DB creds here via env vars if needed
# export DB_HOST=...
# export DB_NAME=...
# export DB_USER=...
# export DB_PASSWORD=...
# export DB_PORT=5432

cd "$(dirname "$0")"

echo "Resetting database (users, filecon)..."
python3 reset_db.py

echo "Clearing frontend server-side sessions..."
rm -rf SecureTextDrive-FrontEnd/.flask_session || true

echo "Done. Restart your backend(s) and frontend, then sign up new accounts."

