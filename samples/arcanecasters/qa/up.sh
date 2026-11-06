#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

bash qa/prepare.sh
docker compose up --build --wait --wait-timeout 150
python3 qa/seed-accounts.py
