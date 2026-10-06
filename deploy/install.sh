#!/bin/sh
# ARTEL self-host installer. Safe to run through:  curl -fsSL <url>/install.sh | sh
# Pass flags through a pipe with:                  curl -fsSL <url>/install.sh | sh -s -- --dir /opt/artel
#
# Idempotent: an existing .env is never overwritten, and running it again updates the compose
# files and re-runs `docker compose up -d`.
set -eu

install_dir="${ARTEL_INSTALL_DIR:-$HOME/artel}"
http_port="${ARTEL_HTTP_PORT:-8088}"
admin_port="${ARTEL_ADMIN_PORT:-8090}"
base_url="${ARTEL_DEPLOY_BASE_URL:-https://raw.githubusercontent.com/project-artel/artel/main/deploy}"
start_stack=1

usage() {
  cat <<USAGE
Usage: install.sh [--dir DIRECTORY] [--port HTTP_PORT] [--no-start]

  --dir DIRECTORY   install directory (default: $install_dir)
  --port HTTP_PORT  host port for the web address (default: $http_port); the admin page uses $admin_port
  --no-start        write the files but do not start the stack
USAGE
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) [ $# -ge 2 ] || fail "--dir needs a value"; install_dir="$2"; shift 2 ;;
    --port) [ $# -ge 2 ] || fail "--port needs a value"; http_port="$2"; shift 2 ;;
    --no-start) start_stack=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; fail "unknown flag: $1" ;;
  esac
done

case "$http_port" in
  ''|*[!0-9]*) fail "--port must be a number" ;;
esac

command -v docker >/dev/null 2>&1 || fail "docker is not installed. See https://docs.docker.com/engine/install/"
docker info >/dev/null 2>&1 || fail "the docker daemon is not reachable. Start it, or check that your user may run docker."
docker compose version >/dev/null 2>&1 || fail "docker compose v2 is not available. See https://docs.docker.com/compose/install/"
command -v openssl >/dev/null 2>&1 || fail "openssl is required to generate secrets"

if command -v curl >/dev/null 2>&1; then
  download() { curl -fsSL "$1" -o "$2"; }
elif command -v wget >/dev/null 2>&1; then
  download() { wget -qO "$2" "$1"; }
else
  fail "curl or wget is required to download the compose files"
fi

mkdir -p "$install_dir"
cd "$install_dir"

# ARTEL_DEPLOY_SOURCE_DIR lets a clone install from its own deploy/ directory without the network.
fetch_file() {
  name="$1"
  if [ -n "${ARTEL_DEPLOY_SOURCE_DIR:-}" ]; then
    cp "$ARTEL_DEPLOY_SOURCE_DIR/$name" "$name"
  else
    download "$base_url/$name" "$name.tmp"
    mv "$name.tmp" "$name"
  fi
}

fetch_file docker-compose.yml
fetch_file Caddyfile
# The template is fetched on every run so a new variable shows up in .env.example after an upgrade.
fetch_file .env.example

generate_secret() {
  openssl rand -hex "$1"
}

if [ -f .env ]; then
  printf 'Keeping the existing .env (secrets are not regenerated).\n'
else
  umask 077
  sed \
    -e "s|__GENERATE_ARTEL_JWT_SECRET__|$(generate_secret 32)|" \
    -e "s|__GENERATE_ARTEL_SECRETS_KEY__|$(generate_secret 32)|" \
    -e "s|__GENERATE_DB_PASSWORD__|$(generate_secret 16)|" \
    -e "s|__GENERATE_ARTEL_S3_ACCESS_KEY__|$(generate_secret 8)|" \
    -e "s|__GENERATE_ARTEL_S3_SECRET_KEY__|$(generate_secret 24)|" \
    -e "s|^ARTEL_HTTP_PORT=.*|ARTEL_HTTP_PORT=$http_port|" \
    -e "s|^ARTEL_PUBLIC_URL=.*|ARTEL_PUBLIC_URL=http://localhost:$http_port|" \
    .env.example > .env
  printf 'Wrote .env with generated secrets.\n'
fi

# The proxy sends /<bucket>/ to MinIO, so the bucket name must not shadow a route of the product.
bucket_name=$(grep '^ARTEL_S3_BUCKET=' .env | tail -n 1 | cut -d= -f2-)
case "${bucket_name:-artel}" in
  api|oauth2|login|ws|assets|projects|account)
    fail "ARTEL_S3_BUCKET=$bucket_name collides with a proxy route. Choose another bucket name in $install_dir/.env." ;;
esac

public_url=$(grep '^ARTEL_PUBLIC_URL=' .env | tail -n 1 | cut -d= -f2-)
admin_url=$(grep '^ARTEL_ADMIN_URL=' .env | tail -n 1 | cut -d= -f2-)
admin_url="${admin_url:-http://localhost:$admin_port}"

if [ "$start_stack" -eq 0 ]; then
  printf 'Files are in %s. Start the stack with: cd %s && docker compose up -d\n' "$install_dir" "$install_dir"
  exit 0
fi

docker compose pull --quiet || printf 'Could not pull some images; compose will use local copies if there are any.\n' >&2
docker compose up -d

cat <<DONE

ARTEL is starting in $install_dir

  Open:     $public_url
  Admin:    $admin_url
  Logs:     cd $install_dir && docker compose logs -f
  Stop:     cd $install_dir && docker compose down

The first account to sign up becomes the admin. Sign up at $public_url,
then open the admin page to set your OpenRouter key.
Edit $install_dir/.env to change settings, then run: docker compose up -d
DONE
