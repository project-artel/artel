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
| `--port HTTP_PORT` | `8088` | host port of the web address; written into the public URL and the published port of a new file (the admin page stays on `8090`) |
| `--no-start` | off | write the file only |

The script checks `docker`, `docker compose` (2.23.1 or later, otherwise it stops with an error) and `openssl`, downloads `docker-compose.yml`,
replaces the `CHANGE_ME` placeholders at the top of it with random secrets from `openssl rand`, and runs `docker compose up -d`.
An existing `docker-compose.yml` is never overwritten, so running the script again only pulls and restarts.

**The file now contains secrets. Do not commit it or share it, and back it up.**
`x-secrets-key` encrypts the OpenRouter key saved on the admin page; if it is lost or changed the saved key is unreadable and must be entered again.

When it finishes, open `http://localhost:8088`. **The first account to sign up becomes the admin.**
The admin page is at `http://localhost:8090` (`x-admin-url`), where the OpenRouter key can be set.
Both addresses use the same host name, and cookies are scoped by host name and not by port, so signing in on one is valid on the other.

## Addresses and ports

| What | Where |
| --- | --- |
| Console (artel-home) | `x-public-url`, default `http://localhost:8088/` |
| Admin page | `x-admin-url`, default `http://localhost:8090/`, its own origin served by the second Caddy site (published on host port `8090`) |
| API, OAuth, WebSocket | `/api`, `/oauth2`, `/login/oauth2`, `/ws` on both origins, proxied to the orchestration server port 8080 |
| MinIO API | `/<bucket>/*` (default `/artel/*`) on the console origin, proxied to MinIO; MinIO has no published port |
| Orchestration internal port 8081 | never published and never routed by the proxy |

Both frontend images reference their assets at the root (`/assets/...`), so they cannot share one origin and each gets its own.

The frontend containers listen on port 8080 and replace a placeholder in their bundle at start with the environment variables
`VITE_ORCHESTRATION_URL` (both) and `VITE_HOME_URL` (admin only). Compose sets them from `x-public-url` and `x-admin-url`;
the container exits if one is missing. When you change either URL, run `docker compose up -d` so the containers restart.

## Docker Compose

Docker Compose 2.23.1 or later is required: the Caddy configuration is written inside `docker-compose.yml` (the `configs:` element with `content:`), so the install needs this one file.
Run `install.sh`, or do it by hand:

1. Copy `docker-compose.yml` into a directory.
2. Edit the block at the top (the lines that start with `x-`). Replace every `CHANGE_ME` with a secret, for example from `openssl rand -hex 32`.
3. Run:

```sh
docker compose up -d        # pulls the ghcr.io/project-artel/* images
docker compose ps
docker compose logs -f orchestration   # or any service: agent-server, proxy, postgres, minio ...
docker compose down         # stop, keep data
docker compose build orchestration agent-server   # optional, in a clone of this repository only (needs the submodules checked out)
```

### Configuration

Every setting is in `docker-compose.yml`. The `x-` block at the top holds the values you change, each written once:

- `x-jwt-secret`: signs session tokens. The server refuses to start with fewer than 32 bytes, so a leftover `CHANGE_ME` stops the orchestration container with the error `ARTEL_JWT_SECRET must contain at least 32 bytes`.
- `x-secrets-key`, `x-db-password`, `x-s3-access-key`, `x-s3-secret-key`: secrets. The server and the databases accept a leftover `CHANGE_ME` for these, so the stack starts and is weakly protected; replace all of them before use.
  `x-secrets-key` must never change after first start.
- `x-public-url` and `x-admin-url`: the addresses people type, without a trailing slash. Keep the same host name in both, so one login works on both (cookies are scoped by host name, not by port).
- `x-openrouter-api-key`: optional. The admin page can set the key, and its value wins.

Settings you rarely change are plain values under each service's `environment:`: `ARTEL_SIGNUP_OPEN` (public signup after the first account, default `false`),
`ARTEL_GITHUB_SIGNUP_OPEN`, `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` (the GitHub login button is hidden unless both are set; callback URL `<public URL>/login/oauth2/code/github`),
`ARTEL_SECURE_COOKIE`, the login rate limits, and the `image:` lines.
The orchestration service also sets `LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_WEB` and `..._REACTIVE` to `INFO`; the server's own default is `DEBUG`, which logs a line for every request.

The published ports and the Caddy site addresses are literals, and the Caddy text cannot read the `x-` values. To change the port or serve from a host name, edit these together:
the two URLs, the `ports:` of the `proxy` service, and the site addresses (`:80`, `:8090`) inside `configs:`.
A host name as a site address makes Caddy fetch a TLS certificate; then use `https://` in the URLs and set `ARTEL_SECURE_COOKIE` to `"true"`.

After editing the file, run `docker compose up -d` again.

### Object storage and the browser

Uploads and downloads use presigned URLs, and the browser opens them directly. The orchestration server signs them
for the public URL, so they look like `<public URL>/artel/<key>?X-Amz-...`, and the proxy forwards
`/artel/*` to MinIO without changing the path or the `Host` header (S3 signatures cover both). Nothing needs an
`/etc/hosts` entry and MinIO publishes no port. The bucket is named `artel` and is created by the `minio-init` service as a directory of the MinIO volume.
A bucket name must not equal a proxy route: `api`, `oauth2`, `login`, `ws`, `assets`, `projects`, `account`.

The server's own S3 calls (screen captures) go to `http://minio:9000` over the compose network, and
`ARTEL_S3_PRESIGN_ENDPOINT` (the public URL) is only the address written into presigned URLs. The
compose file always passes MinIO credentials, so URLs are signed; they never take the unsigned anonymous form.

No CORS setup is needed because each browser page calls its own origin.

MinIO image: Docker Hub no longer serves `minio/minio`, so the file uses `cgr.dev/chainguard/minio` on the `latest` tag, because Chainguard
serves no versioned tags without a login. Replace the `image:` line with a pinned reference if you have access to one.

### Upgrade

```sh
cd <install directory>
docker compose pull
docker compose up -d
```

The images track the `develop` branch (orchestration, agent, console) and the `main` branch (admin) of their repositories,
so an upgrade moves to whatever the branch holds at that moment. Your edited `docker-compose.yml` is kept. To stay on a fixed build, change the `image:` lines to a reference you pinned yourself.

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

Also back up the `artel_minio-data` volume (uploaded documents and screen captures) the same way, and keep `docker-compose.yml`.

## Building the images from a clone

`docker compose build orchestration agent-server` builds the two backends from the submodules in this clone:
`Dockerfile.orchestration` (Maven build, no prebuilt jar needed) with `artel-orchestration-server` as the context, and the
agent server's own Dockerfile, `runtime` target. Compose names the result with the same image reference it would pull, so a
local build is used in place of the published image until you run `docker compose pull`.

Building the console and the admin page from a clone is not covered: those repositories have no Dockerfile, and their images come from the organization's CI.
The backend images on `develop` contain new backend code only after the matching pull requests are merged there.
