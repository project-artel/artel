#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077

if [[ ! -f .env ]]; then cp .env.example .env; fi
mkdir -p .qa
if grep -qx 'GAME_MIGRATIONS=./.qa/database/migration' .env && [[ ! -d .qa/database/migration ]]; then
    git clone --depth 1 --branch dev https://github.com/Apptive-Game-Team/ArcaneCastersDatabase.git .qa/database
fi
if [[ ! -s .qa/private.pem ]]; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .qa/private.pem.tmp 2>/dev/null
    mv .qa/private.pem.tmp .qa/private.pem
fi
openssl pkey -in .qa/private.pem -pubout -out .qa/public.pem

python3 - <<'PY'
import base64
import json
import pathlib
import subprocess
import time

def encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")

now = int(time.time())
header = {"alg": "RS256", "kid": "2026-04-06-01"}
claims = {"iss": "self", "sub": "server", "scope": "WORDONLINE_SERVER",
          "type": "server_token", "iat": now, "exp": now + 365 * 86400}
message = b".".join(encode(json.dumps(part).encode()) for part in (header, claims))
signature = subprocess.check_output(
    ["openssl", "dgst", "-sha256", "-sign", ".qa/private.pem"], input=message)
pathlib.Path(".qa/service.jwt").write_bytes(message + b"." + encode(signature) + b"\n")
PY
