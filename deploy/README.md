# Self-hosting ARTEL

This directory runs the whole product on one machine with Docker: PostgreSQL (pgvector), Valkey (the Redis-compatible store, service name `redis`), MinIO,
the orchestration server, the agent server, the console (artel-home), the admin page, and a Caddy reverse proxy.
The console and the admin page each have their own address, and each browser talks to its own address only, so no CORS setup is needed.

The images are the public ones that the organization's CI publishes on every push:
`ghcr.io/project-artel/orchestration:develop`, `ghcr.io/project-artel/agent:develop`,
`ghcr.io/project-artel/console:develop` (artel-home) and `ghcr.io/project-artel/admin:main` (admin-page).
There is no `latest` tag.

## Install with one command

```sh
curl -fsSL https://raw.githubusercontent.com/project-artel/artel/main/deploy/install.sh | sh
```

Flags go after `sh -s --`:

```sh
curl -fsSL https://raw.githubusercontent.com/project-artel/artel/main/deploy/install.sh | sh -s -- --dir /opt/artel --port 8088
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--dir DIRECTORY` | `$HOME/artel` | install directory |
| `--port HTTP_PORT` | `8088` | host port of the web address (the admin page keeps `ARTEL_ADMIN_PORT`, default `8090`) |
| `--no-start` | off | write files only |

The script checks `docker` and `docker compose`, downloads `docker-compose.yml`, `Caddyfile` and
`.env.example`, writes `.env` with random secrets from `openssl rand` (an existing `.env` is never overwritten),
and runs `docker compose up -d`. Running it again is safe and acts as an upgrade of the compose files.

When it finishes, open `http://localhost:8088`. **The first account to sign up becomes the admin.**
The admin page is at `http://localhost:8090` (`ARTEL_ADMIN_URL`), where the OpenRouter key can be set.
Both addresses use the same host name, and cookies are scoped by host name and not by port, so signing in on one is valid on the other.

## Addresses and ports

| What | Where |
| --- | --- |
| Console (artel-home) | `ARTEL_PUBLIC_URL`, default `http://localhost:8088/` |
| Admin page | `ARTEL_ADMIN_URL`, default `http://localhost:8090/`, its own origin served by the second Caddy site (published on `ARTEL_ADMIN_PORT`) |
| API, OAuth, WebSocket | `/api`, `/oauth2`, `/login/oauth2`, `/ws` on both origins, proxied to the orchestration server port 8080 |
| MinIO API | `/<bucket>/*` (default `/artel/*`) on the console origin, proxied to MinIO; MinIO has no published port |
| Orchestration internal port 8081 | never published and never routed by the proxy |

Both frontend images reference their assets at the root (`/assets/...`), so they cannot share one origin and each gets its own.

The frontend containers listen on port 8080 and replace a placeholder in their bundle at start with the environment variables
`VITE_ORCHESTRATION_URL` (both) and `VITE_HOME_URL` (admin only). Compose sets them from `ARTEL_PUBLIC_URL` and `ARTEL_ADMIN_URL`;
the container exits if one is missing. When you change either URL, run `docker compose up -d` so the containers restart.

## Docker Compose

```sh
cd deploy
cp .env.example .env        # then replace every __GENERATE_...__ value, for example with: openssl rand -hex 32
docker compose up -d        # pulls the ghcr.io/project-artel/* images
docker compose build orchestration agent-server   # optional: build these two from this clone (needs the submodules checked out)
docker compose ps
docker compose logs -f orchestration   # or any service: agent-server, proxy, postgres, minio ...
docker compose down         # stop, keep data
```

### Configuration

All settings live in `.env`; comments in `.env.example` explain each one. Highlights:

- `ARTEL_JWT_SECRET`, `ARTEL_SECRETS_KEY`, `DB_PASSWORD`, `ARTEL_S3_ACCESS_KEY`, `ARTEL_S3_SECRET_KEY`: generated secrets.
  **Back up `.env`.** `ARTEL_SECRETS_KEY` encrypts the OpenRouter key saved on the admin page; if it is lost or changed the saved key is unreadable and must be entered again. `install.sh` never regenerates an existing `.env`.
- `OPENROUTER_API_KEY`: optional. The admin page can set the key, and its value wins.
- `ARTEL_SIGNUP_OPEN`: public signup after the first account. Default `false`.
- `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`: optional. The GitHub login button is hidden unless both are set.
  Callback URL: `<ARTEL_PUBLIC_URL>/login/oauth2/code/github`.
- `BEDROCK_API_KEY`: optional and not needed.
- `ARTEL_PUBLIC_URL`, `ARTEL_SITE_ADDRESS`, `ARTEL_SECURE_COOKIE`: set these when you serve from a real host name.
  A host name in `ARTEL_SITE_ADDRESS` makes Caddy fetch a TLS certificate; then use `https://` in `ARTEL_PUBLIC_URL` and set `ARTEL_SECURE_COOKIE=true`.
- `ARTEL_ADMIN_URL` (default `http://localhost:8090`), `ARTEL_ADMIN_PORT` (default `8090`), `ARTEL_ADMIN_SITE_ADDRESS` (default `:8090`):
  the admin page's address, its published port and its Caddy site address. A host name in `ARTEL_ADMIN_SITE_ADDRESS` makes Caddy fetch a certificate for it.
  Keep the admin host name under the same host name as the console, or sign in on each separately.
- `ARTEL_ORCHESTRATION_IMAGE`, `ARTEL_AGENT_IMAGE`, `ARTEL_CONSOLE_IMAGE`, `ARTEL_ADMIN_IMAGE`: image references. The defaults are the four images listed at the top.

- `ARTEL_GITHUB_SIGNUP_OPEN`: lets a GitHub account that has no ARTEL user sign up. Default `false`; with `false`, a GitHub account signs in only when an admin already created a user with the same email.

After editing `.env`, run `docker compose up -d` again.

Docker Compose reads variables exported in your shell before it reads `.env`. If your shell exports `OPENROUTER_API_KEY` or any other variable listed in `.env`, the exported value silently wins. Run `env | grep -E 'ARTEL|OPENROUTER|GITHUB|DB_'` before `docker compose up -d` to check.

### Object storage and the browser

Uploads and downloads use presigned URLs, and the browser opens them directly. The orchestration server signs them
for `ARTEL_PUBLIC_URL`, so they look like `<ARTEL_PUBLIC_URL>/<bucket>/<key>?X-Amz-...`, and the proxy forwards
`/<bucket>/*` to MinIO without changing the path or the `Host` header (S3 signatures cover both). Nothing needs an
`/etc/hosts` entry and MinIO publishes no port. The bucket name (`ARTEL_S3_BUCKET`, default `artel`) must not equal
a proxy route: `api`, `oauth2`, `login`, `ws`, `assets`, `projects`, `account`. `install.sh` checks this.

The server's own S3 calls (screen captures) go to `http://minio:9000` over the compose network, and
`ARTEL_S3_PRESIGN_ENDPOINT` (set to `ARTEL_PUBLIC_URL`) is only the address written into presigned URLs. The
compose file always passes MinIO credentials, so URLs are signed; they never take the unsigned anonymous form.

No CORS setup is needed because each browser page calls its own origin.

MinIO images: Docker Hub no longer serves `minio/minio`, so the default images are
`cgr.dev/chainguard/minio` and `cgr.dev/chainguard/minio-client`, both on the `latest` tag because Chainguard
serves no versioned tags without a login. Set `ARTEL_MINIO_IMAGE` to a pinned reference if you have access to one. Override them with `ARTEL_MINIO_IMAGE` and
`ARTEL_MINIO_CLIENT_IMAGE`.

### Upgrade

```sh
cd <install directory>
docker compose pull
docker compose up -d
```

The images track the `develop` branch (orchestration, agent, console) and the `main` branch (admin) of their repositories,
so an upgrade moves to whatever the branch holds at that moment. To stay on a fixed build, set the `ARTEL_*_IMAGE` variables to a reference you pinned yourself.

Database migrations run when the orchestration server starts.

### Backup and restore

The PostgreSQL data lives in the `artel_postgres-data` volume (the project name is `artel`).

```sh
# Backup (a consistent SQL dump; run while the stack is up)
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > artel-$(date +%F).sql

# Restore into a fresh, empty database
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < artel-2026-10-06.sql

# Or copy the raw volume (stop postgres first for a consistent copy)
docker compose stop postgres
docker run --rm -v artel_postgres-data:/data -v "$PWD":/backup alpine tar czf /backup/postgres-data.tgz -C /data .
docker compose start postgres
```

Also back up the `artel_minio-data` volume (uploaded documents and screen captures) the same way, and keep `.env`.

## Plain `docker run`

The same stack without compose. Values below match a default `.env`; replace the secrets with your own.
Container names double as host names on the `artel` network, which is why the Caddyfile finds them.

```sh
export DB_PASSWORD=$(openssl rand -hex 16)
export ARTEL_JWT_SECRET=$(openssl rand -hex 32)
export ARTEL_SECRETS_KEY=$(openssl rand -hex 32)
export S3_ACCESS_KEY=$(openssl rand -hex 8)
export S3_SECRET_KEY=$(openssl rand -hex 24)

docker network create artel
docker volume create artel_postgres-data
docker volume create artel_minio-data

docker run -d --name postgres --network artel --restart unless-stopped \
  -e POSTGRES_DB=artel -e POSTGRES_USER=artel -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  -v artel_postgres-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

docker run -d --name redis --network artel --restart unless-stopped \
  valkey/valkey:8.1.10-alpine valkey-server --save "" --appendonly no

docker run -d --name minio --network artel --restart unless-stopped \
  -e MINIO_ROOT_USER="$S3_ACCESS_KEY" -e MINIO_ROOT_PASSWORD="$S3_SECRET_KEY" \
  -v artel_minio-data:/data \
  cgr.dev/chainguard/minio:latest server /data --console-address :9001

# One-shot: create the bucket. If MinIO is not ready yet, run it again after a few seconds.
docker run --rm --network artel \
  -e MC_HOST_local="http://$S3_ACCESS_KEY:$S3_SECRET_KEY@minio:9000" \
  cgr.dev/chainguard/minio-client:latest mb --ignore-existing local/artel

docker run -d --name orchestration --network artel --restart unless-stopped \
  -e DB_HOST=postgres -e DB_PORT=5432 -e DB_NAME=artel -e DB_USERNAME=artel -e DB_PASSWORD="$DB_PASSWORD" \
  -e DB_SSL_MODE=disable -e REDIS_URL=redis://redis:6379 \
  -e ARTEL_INTERNAL_API_PORT=8081 -e ARTEL_AGENT_BASE_URL=http://agent-server:8000 \
  -e ARTEL_HOME_URL=http://localhost:8088 -e ARTEL_ALLOWED_ORIGINS=http://localhost:8088,http://localhost:8090 \
  -e ARTEL_JWT_SECRET="$ARTEL_JWT_SECRET" -e ARTEL_SECRETS_KEY="$ARTEL_SECRETS_KEY" \
  -e ARTEL_SECURE_COOKIE=false -e ARTEL_SIGNUP_OPEN=false -e ARTEL_GITHUB_SIGNUP_OPEN=false \
  -e OPENROUTER_API_KEY= -e GITHUB_CLIENT_ID= -e GITHUB_CLIENT_SECRET= \
  -e ARTEL_S3_BUCKET=artel -e ARTEL_S3_REGION=us-east-1 -e ARTEL_S3_ENDPOINT=http://minio:9000 -e ARTEL_S3_PRESIGN_ENDPOINT=http://localhost:8088 \
  -e ARTEL_S3_ACCESS_KEY="$S3_ACCESS_KEY" -e ARTEL_S3_SECRET_KEY="$S3_SECRET_KEY" \
  ghcr.io/project-artel/orchestration:develop
# No -p here: port 8081 serves /internal/** without authentication and must stay on the network.

docker run -d --name agent-server --network artel --restart unless-stopped \
  -e APP_PORT=8000 -e APP_ENV=production -e OPENROUTER_API_KEY= \
  -e ORCHESTRATION_BASE_URL=http://orchestration:8081 -e LANGSMITH_TRACING=false \
  ghcr.io/project-artel/agent:develop

# The frontend images listen on 8080 and need these variables at start (they exit without them).
docker run -d --name admin-page --network artel --restart unless-stopped \
  -e VITE_ORCHESTRATION_URL=http://localhost:8090 -e VITE_HOME_URL=http://localhost:8088 \
  ghcr.io/project-artel/admin:main

docker run -d --name artel-home --network artel --restart unless-stopped \
  -e VITE_ORCHESTRATION_URL=http://localhost:8088 \
  ghcr.io/project-artel/console:develop

# Run from the deploy directory so ./Caddyfile exists.
docker run -d --name proxy --network artel --restart unless-stopped \
  -e ARTEL_SITE_ADDRESS=:80 -e ARTEL_ADMIN_SITE_ADDRESS=:8090 -e ARTEL_S3_BUCKET=artel \
  -p 8088:80 -p 8443:443 -p 8090:8090 \
  -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" -v artel_caddy-data:/data -v artel_caddy-config:/config \
  caddy:2-alpine
```

The Caddyfile has two sites, the console on `ARTEL_SITE_ADDRESS` and the admin page on `ARTEL_ADMIN_SITE_ADDRESS`.
Open `http://localhost:8088`; the first sign-up becomes the admin, and `http://localhost:8090` is the admin page. To stop everything:
`docker rm -f proxy artel-home admin-page agent-server orchestration minio redis postgres`
(volumes and the network stay until you remove them).

## Building the images from a clone

`docker compose build orchestration agent-server` builds the two backends from the submodules in this clone:
`Dockerfile.orchestration` (Maven build, no prebuilt jar needed) with `artel-orchestration-server` as the context, and the
agent server's own Dockerfile, `runtime` target. Compose names the result with the same image reference it would pull, so a
local build is used in place of the published image until you run `docker compose pull`.

Building the console and the admin page from a clone is not covered: those repositories have no Dockerfile, and their images come from the organization's CI.
The backend images on `develop` contain new backend code only after the matching pull requests are merged there.
