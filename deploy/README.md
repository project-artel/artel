# Self-hosting ARTEL

This directory runs the whole product on one machine with Docker: PostgreSQL (pgvector), Valkey (the Redis-compatible store, service name `redis`), MinIO,
the orchestration server, the agent server, the console (artel-home), and a Caddy reverse proxy.
The console has one address, and the browser talks to that address only, so no CORS setup is needed.
The administrator's screens (users, provider keys, models, and the cross-project dashboards) are part of the console under `/admin`, visible to administrators only.

The images are the public ones that the organization's CI publishes on every push:
`ghcr.io/project-artel/orchestration:develop`, `ghcr.io/project-artel/agent:develop`,
and `ghcr.io/project-artel/console:develop` (artel-home).
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
| `--port HTTP_PORT` | `8088` | host port of the web address; written into the public URL and the published port of a new file |
| `--no-start` | off | write the file only |
| `--telemetry` | off | 새 `docker-compose.yml` 을 만들 때 `x-telemetry` 에 `on` 을 쓴다. 환경 변수 `ARTEL_TELEMETRY=on` 도 같다 |

The script checks `docker`, `docker compose` (2.23.1 or later, otherwise it stops with an error) and `openssl`, downloads `docker-compose.yml`,
replaces the `CHANGE_ME` placeholders at the top of it with random secrets from `openssl rand`, and runs `docker compose up -d`.
An existing `docker-compose.yml` is never overwritten, so running the script again only pulls and restarts.

**The file now contains secrets. Do not commit it or share it, and back it up.**
`x-secrets-key` encrypts the OpenRouter, Bedrock and Claude API keys saved in the admin settings; if it is lost or changed the saved keys are unreadable and must be entered again.

When it finishes, open `http://localhost:8088`. **The first account to sign up becomes the admin.**
Signed in as that account, open `http://localhost:8088/admin/settings` (the "관리" / "Admin" link in the top bar, then the Settings tab) and enter the OpenRouter key, and optionally the Bedrock key and the Claude API key (Anthropic). They are stored encrypted in the database.

## 사용 통계 전송 (telemetry, 선택, 기본 꺼짐)

admin 이 동의한 설치만 UTC 기준 하루에 한 번 그날의 사용 통계를 ARTEL 팀의 서버(`https://stage-orch.artel.kr/telemetry/reports`)로 보낸다.
동의하기 전에는 아무것도 보내지 않는다.

`install.sh --telemetry`(또는 `ARTEL_TELEMETRY=on sh install.sh`)로 설치하거나, 첫 admin 가입 화면의 체크박스를 켜거나, `/admin/settings` 에서 켠다.
플래그는 새로 만드는 `docker-compose.yml` 의 `x-telemetry` 에 `on` 을 쓴다. 이미 있는 파일은 건드리지 않으므로, 그 경우에는 `x-telemetry` 를 직접 고치고 `docker compose up -d` 를 다시 실행한다.
`/admin/settings` 에서는 다음에 보낼 JSON 을 그대로 볼 수 있다. admin 이 화면에서 한 번 정하면 그 값이 `x-telemetry` 보다 우선한다.
끌 때는 이미 보낸 통계를 삭제하도록 요청할 수 있다. `ARTEL_TELEMETRY_URL` 을 비우면 보내는 기능 자체가 꺼진다.

보내는 값은 아래가 전부다(`schemaVersion: 1`).

설치 정보(`install`)

| field | 값 |
| --- | --- |
| `installId` | 이 설치에 무작위로 만든 UUID. 사람이 아니라 설치를 구분한다 |
| `orchestrationVersion` | `ARTEL_VERSION`. 없으면 null |
| `agentServerVersions` | 그날 끝난 QA run 에 쓰인 agent-server 의 `image_tag`, 없으면 `git_sha` |
| `reportDate` | 통계가 다루는 날짜(UTC) |

QA run(`qaStructures`). `agentArch`(agent 구조 이름), `agentFingerprint`, `model`, `reasoningEffort` 가 같은 scenario 실행끼리 묶는다.

| field | 값 |
| --- | --- |
| `tries` | 그날 끝난 scenario 실행 수 |
| `triesByStatus` | 상태(`COMPLETED`, `FAILED`, `CANCELLED` 등)별 실행 수 |
| `stepsTotal`, `stepsPassed` | step 전체 수와 통과 수 |
| `casesTotal`, `casesPassed` | test case 전체 수와 통과 수 |
| `durationSecondsSum`, `durationSecondsMax` | 실행 시간의 합과 최댓값(초) |
| `toolCalls` | tool 이름별 호출 수. 그 실행의 내장 tool 목록에 없는 이름은 `other` 로 합친다 |

LLM 사용량(`llmUsage`). `service`(QA run, scenario 생성, knowledge 검색, game context, embedding), `provider`, `model`, `keySource`(admin key 인지 사용자 key 인지)가 같은 호출끼리 묶는다.

| field | 값 |
| --- | --- |
| `calls` | 호출 수 |
| `inputTokens`, `outputTokens`, `cachedInputTokens`, `cacheWriteTokens`, `reasoningTokens` | token 수의 합 |
| `costUsdSum` | 비용 합(USD). 단가를 모르는 호출만 있으면 null |
| `latencyMsSum` | 응답 시간 합(ms) |

오류(`errors`). `source`(`qa_run` 또는 `orchestration`), `code`, `exceptionType`(예외 class 이름)이 같은 오류끼리 묶는다.

| field | 값 |
| --- | --- |
| `count` | 발생 횟수 |
| `frames` | 처음 발생한 오류의 코드 위치 최대 10개(`module:function:line` 또는 `class:method:line`). 파일 경로는 없다 |

보내지 않는 값:

- QA run 의 원본 기록: `qa_log` 메시지, agent 의 추론, action, screen capture, game state.
- content map, knowledge 문서, scenario, test case 본문, 프로젝트 이름, 게임 이름.
- email, 이름, user id, IP 주소. 받는 서버는 보낸 쪽 IP 주소도 저장하지 않는다.
- 오류 메시지 본문과 파일 경로.
- 게임이 등록한 함수의 이름.

## Addresses and ports

| What | Where |
| --- | --- |
| Console (artel-home) | `x-public-url`, default `http://localhost:8088/` |
| Admin screens | `/admin` on the console origin, for administrators only; other accounts get the not-found page |
| API, OAuth, WebSocket | `/api`, `/oauth2`, `/login/oauth2`, `/ws` on the console origin, proxied to the orchestration server port 8080 |
| MinIO API | `/<bucket>/*` (default `/artel/*`) on the console origin, proxied to MinIO; MinIO has no published port |
| Orchestration internal port 8081 | never published and never routed by the proxy |

The console container listens on port 8080 and replaces a placeholder in its bundle at start with the environment variable
`VITE_ORCHESTRATION_URL`. Compose sets it from `x-public-url`;
the container exits if it is missing. When you change the URL, run `docker compose up -d` so the container restarts.

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
  `x-secrets-key` is required: it encrypts the provider keys that you enter in the admin settings, and without a real value no key can be saved safely. Make one by hand with `openssl rand -base64 48`. It must never change after first start.
- `x-public-url`: the address people type, without a trailing slash.
- `x-bedrock-region`: AWS region for `bedrock/...` models. Default `us-west-2`.
- LLM provider keys are not environment variables and `OPENROUTER_API_KEY`, `LLM_API_KEY` and `BEDROCK_API_KEY` are no longer read. After the stack is up, sign in as the first account and enter the OpenRouter key, and optionally the Bedrock key and the Claude API key (Anthropic), at `<public URL>/admin/settings`. The `claude/...` models start switched off and are switched on after the check for the Claude API key on that page passes. Without a stored Bedrock key the agent server uses the standard AWS credential chain (for example an IAM role).

Settings you rarely change are plain values under each service's `environment:`: `ARTEL_SIGNUP_OPEN` (public signup after the first account, default `false`),
`ARTEL_GITHUB_SIGNUP_OPEN`, `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` (the GitHub login button is hidden unless both are set; callback URL `<public URL>/login/oauth2/code/github`),
`ARTEL_SECURE_COOKIE`, the login rate limits, and the `image:` lines.
The orchestration service also sets `LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_WEB` and `..._REACTIVE` to `INFO`; the server's own default is `DEBUG`, which logs a line for every request.

The published ports and the Caddy site addresses are literals, and the Caddy text cannot read the `x-` values. To change the port or serve from a host name, edit these together:
the public URL, the `ports:` of the `proxy` service, and the site address (`:80`) inside `configs:`.
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

No CORS setup is needed because the browser calls the console origin only.

MinIO image: Docker Hub no longer serves `minio/minio`, so the file uses `cgr.dev/chainguard/minio` on the `latest` tag, because Chainguard
serves no versioned tags without a login. Replace the `image:` line with a pinned reference if you have access to one.

### Upgrade

```sh
cd <install directory>
docker compose pull
docker compose up -d
```

The images track the `develop` branch (orchestration, agent, console) of their repositories,
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

Building the console from a clone is not covered: that repository has no Dockerfile, and its image comes from the organization's CI.
The backend images on `develop` contain new backend code only after the matching pull requests are merged there.
