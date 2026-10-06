#!/bin/sh
# ARTEL self-host installer. Safe to run through:  curl -fsSL <url>/install.sh | sh
# Pass flags through a pipe with:                  curl -fsSL <url>/install.sh | sh -s -- --dir /opt/artel
#
# Idempotent: an existing docker-compose.yml (your edits and secrets) is never overwritten, and running
# it again re-runs `docker compose pull` and `docker compose up -d`.
set -eu

install_dir="${ARTEL_INSTALL_DIR:-$HOME/artel}"
http_port="${ARTEL_HTTP_PORT:-8088}"
base_url="${ARTEL_DEPLOY_BASE_URL:-https://raw.githubusercontent.com/project-artel/artel/main/deploy}"
start_stack=1

usage() {
  cat <<USAGE
Usage: install.sh [--dir DIRECTORY] [--port HTTP_PORT] [--no-start]

  --dir DIRECTORY   install directory (default: $install_dir)
  --port HTTP_PORT  host port for the web address (default: $http_port); only used when the file is created; the admin page stays on 8090
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
# docker-compose.yml inlines the Caddy configuration with `configs: content:`, which needs Compose 2.23.1 or later.
compose_version=$(docker compose version --short | sed 's/^v//')
compose_major=${compose_version%%.*}
compose_rest=${compose_version#*.}
compose_minor=${compose_rest%%.*}
compose_patch=${compose_rest#*.}
compose_patch=${compose_patch%%[!0-9]*}
if [ "$compose_major" -lt 2 ] || { [ "$compose_major" -eq 2 ] && { [ "$compose_minor" -lt 23 ] || { [ "$compose_minor" -eq 23 ] && [ "${compose_patch:-0}" -lt 1 ]; }; }; }; then
  fail "Docker Compose $compose_version is too old. ARTEL needs 2.23.1 or later. See https://docs.docker.com/compose/install/"
fi
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

if [ -f docker-compose.yml ]; then
  printf 'Keeping the existing docker-compose.yml (your edits and secrets are not touched).\n'
else
  # ARTEL_DEPLOY_SOURCE_DIR lets a clone install from its own deploy/ directory without the network.
  if [ -n "${ARTEL_DEPLOY_SOURCE_DIR:-}" ]; then
    cp "$ARTEL_DEPLOY_SOURCE_DIR/docker-compose.yml" docker-compose.yml.tmp
  else
    download "$base_url/docker-compose.yml" docker-compose.yml.tmp
  fi

  # Each placeholder is replaced only on the line that matches exactly, so a value can never leak
  # into another line. The values are hex, which has no characters that awk or the shell treat specially.
  public_url="http://localhost:$http_port"
  umask 077
  awk \
    -v jwt="$(openssl rand -hex 32)" \
    -v key="$(openssl rand -hex 32)" \
    -v db="$(openssl rand -hex 16)" \
    -v s3a="$(openssl rand -hex 8)" \
    -v s3s="$(openssl rand -hex 24)" \
    -v port="$http_port" \
    -v url="$public_url" '
    $0 == "x-jwt-secret: &jwt_secret CHANGE_ME"     { print "x-jwt-secret: &jwt_secret " jwt; next }
    $0 == "x-secrets-key: &secrets_key CHANGE_ME"   { print "x-secrets-key: &secrets_key " key; next }
    $0 == "x-db-password: &db_password CHANGE_ME"   { print "x-db-password: &db_password " db; next }
    $0 == "x-s3-access-key: &s3_access_key CHANGE_ME" { print "x-s3-access-key: &s3_access_key " s3a; next }
    $0 == "x-s3-secret-key: &s3_secret_key CHANGE_ME" { print "x-s3-secret-key: &s3_secret_key " s3s; next }
    $0 == "x-public-url: &public_url http://localhost:8088" { print "x-public-url: &public_url " url; next }
    $0 == "      - \"8088:80\"" { print "      - \"" port ":80\""; next }
    { print }
  ' docker-compose.yml.tmp > docker-compose.yml
  rm -f docker-compose.yml.tmp
  if grep -q '^x-.*: &.* CHANGE_ME$' docker-compose.yml; then
    rm -f docker-compose.yml
    fail "a CHANGE_ME placeholder is left in the downloaded docker-compose.yml; the file layout changed. Nothing was written."
  fi
  printf 'Wrote docker-compose.yml with generated secrets. It now holds secrets: do not commit or share it.\n'
fi

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
Edit $install_dir/docker-compose.yml to change settings, then run: docker compose up -d
DONE
