# 2026-10-20 — Package ARTEL as a headless server and an Electron desktop app without Docker

- Date: 2026-10-20
- GitHub Issue: None
- Status: Draft

## Goal

Ship the whole ARTEL stack as one installable program, with no Docker on the user's machine.

1. **Headless.** `artel server start|stop|status|logs|doctor` in the existing `@project-artel/cli` starts
   every service as a native process, on Windows, macOS and Linux.
2. **Desktop.** An Electron app that starts the same stack through the same code and shows the console
   (`artel-home`) in its own window instead of a browser tab.
3. **The CLI comes with the desktop app.** Installing the desktop app puts the `artel` command on `PATH`
   with no separate `npm install`, the way VS Code installs `code`.

Decided with the user on 2026-10-20: everything bundled, no Docker; headless lives in `artel-cli`;
targets are Windows, macOS and Linux on both x64 and arm64; the desktop app has the user create the first
account; the runtime bundle ships inside the installer; everything new lives in a new submodule
`artel-desktop`.

## Non-goals

- Replacing `deploy/docker-compose.yml`. Server installs keep it; this plan adds a second way in.
- A cloud-connected thin client. The desktop app runs its own stack.
- Multi-machine or high-availability setups. One machine, one stack.
- New console features. `artel-home` is shown as it is.

## Context / Constraints

The compose stack has 7 services. What each one needs to run natively:

| Service | Today | Native plan | Why |
| --- | --- | --- | --- |
| postgres | `pgvector/pgvector:pg16` | PostgreSQL 16 binaries per OS plus pgvector built in our CI | Flyway runs `CREATE EXTENSION vector` (V18, V23, V102 use `vector(1024)`) |
| valkey | `valkey/valkey` | **Removed** in bundled mode | Valkey has no native Windows build |
| minio | Chainguard image | **Removed** in bundled mode | MinIO stopped shipping community binaries |
| orchestration | Spring Boot jar, Java 21 | Fat jar plus a `jlink` runtime per OS | |
| agent-server | Python, FastAPI | `python-build-standalone` plus a pre-built virtual environment per OS | Wheels such as `pdfplumber` and `uvloop` are native |
| artel-home | nginx serving `dist/` | Served by the supervisor's proxy | |
| proxy | Caddy | A Node reverse proxy inside the supervisor | One origin for cookies, same as Caddy does now |

Redis users that must move off Redis:

- orchestration: `SdkLoginCodeStore`, `RefreshTokenService`, `TrackerInstallationChoiceStore`.
- agent-server: `RedisSessionStore` and `RedisQaSessionStore`, wired in `app/main.py:50-62`.
  `InMemorySessionStore` already exists in `app/sessions/store.py`; a QA counterpart does not.

Object storage: `DocumentStorage` (`project/storage/DocumentStorage.kt`) is already an interface with one
implementation, `S3DocumentStorage`, used from 11 files. A filesystem implementation can sit beside it.
Presigned upload and download URLs become URLs on orchestration itself, signed with an HMAC and an expiry.

`artel-home` bakes `VITE_ORCHESTRATION_URL` as the placeholder `__ARTEL_ORCHESTRATION_URL__` and
`docker-entrypoint.sh` replaces it at container start. The supervisor does the same replacement once, into
its data directory, at first start and after each upgrade.

## Architecture

```
artel (CLI, Node)                       ARTEL Desktop (Electron)
  └─ artel server start ──┐               └─ main process ──┐
                          ▼                                 ▼
                 @project-artel/cli/supervisor  (one module, both callers)
                          │
     ┌──────────┬─────────┼──────────────┬───────────────────┐
     ▼          ▼         ▼              ▼                   ▼
 postgres   orchestration  agent-server   Node proxy :8088    state file + logs
 (pg_ctl)   (java -jar)    (python -m     ├ /api /oauth2 /ws → orchestration
                            uvicorn)      ├ /storage/*       → orchestration
                                          └ everything else  → artel-home dist/
```

- **Runtime bundle.** One archive per OS and architecture,
  `artel-runtime-<version>-<os>-<arch>.tar.zst`: PostgreSQL with pgvector, a `jlink` Java runtime,
  `orchestration.jar`, Python with the agent-server virtual environment, and `artel-home/dist`.
  Expected 150 to 250 MB compressed. Built by a GitHub Actions matrix on native runners
  (`ubuntu-latest`, `ubuntu-24.04-arm`, `macos-13`, `macos-14`, `windows-latest`, `windows-11-arm`).
  Six targets: `linux-x64`, `linux-arm64`, `darwin-x64`, `darwin-arm64`, `win32-x64`, `win32-arm64`.
- **Supervisor** (in `artel-cli`, `src/server/`):
  - Data directory per OS: `~/.local/share/artel`, `~/Library/Application Support/ARTEL`, `%LOCALAPPDATA%\ARTEL`.
    Holds `pgdata/`, `storage/`, `logs/`, `config.json` (mode 0600) and `state.json`.
  - First start: generates the JWT secret, `ARTEL_SECRETS_KEY` and the database password, runs `initdb`,
    picks free ports on `127.0.0.1`.
  - Start order with health checks: postgres (`pg_isready`), orchestration (`/actuator/health` or the
    existing health route), agent-server, then the proxy. Restarts a crashed process with backoff.
  - Stop: proxy, agent-server, orchestration, then `pg_ctl stop -m fast`.
  - A lock file makes the CLI and the desktop app share one running stack instead of starting two.
  - Binds to `127.0.0.1` by default. `--host 0.0.0.0 --public-url <url>` opens it to a network.
- **Headless install.** `npm i -g @project-artel/cli`, then `artel server install` downloads the runtime
  bundle that matches the CLI version from GitHub Releases and checks its SHA-256. The bundle is not put
  in the npm package, which would make every CLI user download it.
  Decided 2026-10-20: `artel server start` runs the same install step itself when the runtime is missing, so
  `npm i -g` then `artel server start` is enough. `--no-install` turns that off. It never downloads when
  `ARTEL_RUNTIME_DIR` is set (the desktop app's bundled runtime).
- **Desktop app.** New repository `project-artel/artel-desktop`, public and AGPL-3.0-only like the other
  repositories, added to this workspace as a submodule on branch `main`. It holds both the runtime bundle
  build and the Electron app. `electron-builder` puts the runtime bundle in
  `extraResources`, so the installer works offline. The main process imports the supervisor from
  `@project-artel/cli`, shows a start-up window with progress per service, then loads the proxy URL in a
  `BrowserWindow`. Tray icon with open, stop, logs and quit. Updates through `electron-updater`.
- **First account.** No automatic account. On a fresh data directory the window opens the console's
  existing email and password signup, and that first account becomes `ADMIN`, the same rule the compose
  install already follows. `ARTEL_SIGNUP_OPEN` stays `false`, so later accounts are created by the admin.
  The headless install behaves the same way: `artel server start` prints the URL to open for signup.
- **CLI inside the desktop app.** The app ships `bin/artel` (`bin/artel.cmd` on Windows), which runs the
  CLI with the app's own Node through `ELECTRON_RUN_AS_NODE=1`.
  - Windows: the NSIS installer adds `bin` to the user `PATH`.
  - macOS: first launch offers to link `/usr/local/bin/artel` (needs an administrator prompt), and a menu
    item does it later.
  - Linux: the `.deb` links `/usr/bin/artel`; the AppImage offers the same link to `~/.local/bin`.
  - The bundled CLI's default server URL is the local stack, so `artel login` works with no flag.

## Approach (Checklist)

- [ ] **Step 0: Recon**
  - Read `AGENTS.md` and `.agents/docs/` in `artel-cli`, `artel-orchestration-server`, `artel-agent-server`.
  - List every Redis key orchestration writes and its TTL; list every `DocumentStorage` caller that hands a
    presigned URL to the browser or to the agent-server.
  - Confirm the orchestration health route and the agent-server start command used in their Dockerfiles.
- [ ] **Step 1: Services run without Redis and MinIO** (orchestration, agent-server; can run in parallel)
  - orchestration: `artel.store=redis|postgres`. The `postgres` variant keeps the three stores in one table
    with `expires_at`, so refresh tokens survive a restart. New Flyway migration.
  - orchestration: `artel.storage=s3|filesystem`. `FilesystemDocumentStorage` writes under
    `ARTEL_STORAGE_DIR` and serves `PUT`/`GET /storage/{key}` with an HMAC-signed, expiring query string.
  - agent-server: `SESSION_STORE=redis|memory`, plus an in-memory `QaSessionStore`.
  - Defaults stay `redis` and `s3`, so compose and the hosted service do not change.
- [ ] **Step 2: Runtime bundle for linux-x64**
  - Build scripts in `artel-desktop/runtime/`: PostgreSQL 16 binaries, pgvector compiled against them,
    `jlink` with the modules `jdeps` reports, `python-build-standalone` 3.12 with `uv pip install`.
  - Smoke test in CI: unpack, start every process by hand, run Flyway, hit `/api` through the proxy.
- [ ] **Step 3: Supervisor and `artel server` commands** (artel-cli)
  - `install`, `start`, `stop`, `status`, `logs [service] [--follow]`, `doctor` (ports, disk, bundle hash).
  - Unit tests for config generation, port selection, start order and the lock file, with fake processes.
- [ ] **Step 4: Bundles for the other five targets** (`linux-arm64`, `darwin-x64`, `darwin-arm64`,
  `win32-x64`, `win32-arm64`)
  - Windows: pgvector with MSVC `nmake`; `uvicorn[standard]` without `uvloop`; Postgres must not run as an
    administrator, so the supervisor refuses to start from an elevated shell.
  - `win32-arm64`: no ready-made PostgreSQL binaries exist, so PostgreSQL 16 and pgvector are built from
    source with Meson and MSVC on the `windows-11-arm` runner. Java (Microsoft Build of OpenJDK) and
    `python-build-standalone` (`aarch64-pc-windows-msvc`) ship arm64 builds.
- [ ] **Step 5: Electron app** (`artel-desktop`)
  - Start-up window, `BrowserWindow`, tray, single instance lock, quit stops the stack unless the user
    chose "keep running in the background".
  - External links (GitHub OAuth, docs) open in the system browser, not in the app window.
  - Bundled `bin/artel` and the `PATH` step per OS.
- [ ] **Step 6: Signing, updates, documents**
  - macOS: Developer ID signing and notarization, including every bundled executable (`postgres`, `java`,
    `python`, `.dylib`, `.so`). Windows: Authenticode certificate.
  - Upgrade path: back up `pgdata` before Flyway runs on a new version. PostgreSQL stays on 16; a major
    upgrade needs `pg_upgrade` and its own plan.
  - Onboarding `/self-hosting` page gains a desktop and headless section in Korean and English.

## Validation

- **Commands to run:**
  - Step 1: orchestration and agent-server test suites with each new flag value; the compose stack still
    starts unchanged.
  - Step 3 and later, on each OS: `artel server install && artel server start`, sign up the first account,
    upload a design document, run one QA run with the `qa-run-local` skill against a Unity build,
    `artel server stop`, start again and confirm the session and the uploaded document are still there.
  - Desktop: install from the built installer on a clean virtual machine with no Node, Java, Python or Docker,
    then run `artel --version` in a new terminal.
- **Expected output:** the same QA run result as the compose stack on the same build and model.

## Risks & Rollback

- **Risks:**
  - macOS notarization of many bundled executables is the step most likely to take longer than planned.
  - pgvector on Windows is the least-tested build, and `win32-arm64` needs PostgreSQL itself built from
    source. If that target slips, it can ship one release later without blocking the other five.
  - Memory: a JVM, Python and PostgreSQL together idle at about 1 to 1.5 GB. Set `-Xmx` and Postgres
    `shared_buffers` low for desktop.
  - Two storage and two store implementations to keep in step. Both run in CI.
  - Antivirus software on Windows may quarantine unsigned bundled executables.
- **Rollback steps:** the new flags default to the current behaviour, so Steps 1 to 3 can be reverted per
  repository with `git revert`; the desktop app is a separate repository and release.

## Open Questions

1. ~~Desktop sign-in~~: decided 2026-10-20, the user creates the first account in the app (see Architecture).
2. ~~Bundle placement~~: decided 2026-10-20, inside the installer.
3. ~~Repository~~: decided 2026-10-20, new submodule `artel-desktop`.
4. ~~arm64~~: decided 2026-10-20, Windows arm64 and Linux arm64 ship in the first release.

## Shared contract (fixed before the parallel tracks start, 2026-10-20)

Jira: story ARTEL-1140. Subtasks: ARTEL-1141 orchestration store, ARTEL-1142 orchestration storage,
ARTEL-1143 agent-server store, ARTEL-1144 CLI supervisor, ARTEL-1145 runtime bundle, ARTEL-1146 Electron app.
A track that needs to change anything in this section stops and reports instead of changing it alone.

### 1. Service environment variables in bundled mode

orchestration (ARTEL-1141, ARTEL-1142 add the first three; the rest already exist):

| Variable | Bundled value | Default when unset |
| --- | --- | --- |
| `ARTEL_STORE` | `postgres` | `redis` |
| `ARTEL_STORAGE` | `filesystem` | `s3` |
| `ARTEL_STORAGE_DIR` | `<dataDir>/storage` | none, required when `ARTEL_STORAGE=filesystem` |
| `SERVER_PORT`, `ARTEL_INTERNAL_API_PORT` | chosen ports | 8080, 8081 |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_SSL_MODE` | `127.0.0.1`, chosen, `artel`, `artel`, generated, `disable` | |
| `ARTEL_AGENT_BASE_URL`, `ARTEL_AGENT_WS_BASE_URL` | `http://127.0.0.1:<agent>/internal`, `ws://127.0.0.1:<agent>/internal` | |
| `ARTEL_HOME_URL`, `ARTEL_ALLOWED_ORIGINS` | public URL | |
| `ARTEL_JWT_SECRET`, `ARTEL_SECRETS_KEY` | generated | |
| `ARTEL_SECURE_COOKIE`, `ARTEL_SIGNUP_OPEN`, `ARTEL_GITHUB_SIGNUP_OPEN` | `false`, `false`, `false` | |
| `LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_WEB`, `..._WEB_REACTIVE` | `INFO` | |

JVM options from the supervisor: `-Xmx512m -XX:+UseSerialGC`.

Filesystem storage URLs (ARTEL-1142): `<ARTEL_HOME_URL>/api/storage/objects/<objectKey>?expires=<epochSeconds>&signature=<hex HMAC-SHA256>`.
`PUT` uploads, `GET` downloads. They sit under `/api`, so the proxy needs no extra route.
Download URLs also carry `&filename=<name>` (covered by the signature) because callers ask for different
`Content-Disposition` names for the same object, as S3's `response-content-disposition` does. Consumers treat
the URL as opaque. The signing key is derived from `ARTEL_JWT_SECRET` (label `artel/storage-url-signature/v1`),
so rotating that secret invalidates issued URLs. (Amended 2026-10-20 after ARTEL-1142.)

agent-server (ARTEL-1143 adds `SESSION_STORE`):

| Variable | Bundled value | Default |
| --- | --- | --- |
| `SESSION_STORE` | `memory` | `redis` |
| `APP_PORT` | chosen port | |
| `APP_ENV` | `production` | |
| `ORCHESTRATION_BASE_URL` | `http://127.0.0.1:<internal port>` | |
| `LANGSMITH_TRACING` | `false` | |

Start command: `<python> -m uvicorn app.main:app --host 127.0.0.1 --port <APP_PORT>` with the working directory
`<runtimeDir>/agent-server`. Health: `GET /health` (outside the `/internal` prefix) answers 200.
orchestration has no health route: the supervisor treats any HTTP response from `GET /api/auth/me` (401 included)
as ready.

### 2. Runtime bundle layout (ARTEL-1145 produces, ARTEL-1144 and ARTEL-1146 consume)

Archive: `artel-runtime-<version>-<target>.tar.gz` plus `artel-runtime-<version>-<target>.tar.gz.sha256`
(hex digest, two spaces, file name). `<target>` is one of `linux-x64`, `linux-arm64`, `darwin-x64`,
`darwin-arm64`, `win32-x64`, `win32-arm64` (Node's `process.platform-process.arch`). Released on
`project-artel/artel-desktop` under tag `runtime-v<version>`:
`https://github.com/project-artel/artel-desktop/releases/download/runtime-v<version>/<archive>`.

The archive unpacks to one directory, the runtime directory:

```
manifest.json
postgres/            bin/, lib/, share/ (pgvector's vector.control and SQL files installed into share/extension)
java/                jlink runtime
orchestration/orchestration.jar
python/              python-build-standalone with the agent-server dependencies installed into its site-packages
agent-server/app/    agent-server source, run from agent-server/
home/                artel-home dist built with VITE_ORCHESTRATION_URL=__ARTEL_ORCHESTRATION_URL__
```

`manifest.json`:

```json
{
  "schemaVersion": 1,
  "version": "0.1.0",
  "target": "linux-x64",
  "executables": {
    "postgres": "postgres/bin/postgres",
    "initdb": "postgres/bin/initdb",
    "pg_ctl": "postgres/bin/pg_ctl",
    "pg_isready": "postgres/bin/pg_isready",
    "createdb": "postgres/bin/createdb",
    "java": "java/bin/java",
    "python": "python/bin/python3"
  },
  "orchestrationJar": "orchestration/orchestration.jar",
  "agentServerDir": "agent-server",
  "homeDir": "home",
  "components": { "postgres": "16.x", "pgvector": "0.8.x", "java": "21.x", "python": "3.12.x" },
  "sources": { "orchestration": "<git sha>", "agentServer": "<git sha>", "home": "<git sha>" }
}
```

Paths are relative to the runtime directory, with `/` separators, and carry `.exe` on Windows
(`python/python.exe` there). Consumers read paths only from the manifest and never build them per OS.

### 3. Supervisor module (ARTEL-1144 exports, ARTEL-1146 imports)

`@project-artel/cli` adds the package export `"./supervisor"`. Electron imports it; it must not import commander
or write to stdout.

```ts
export type ServiceName = 'postgres' | 'orchestration' | 'agent-server' | 'proxy';
export type ServiceState = 'stopped' | 'starting' | 'ready' | 'crashed';

export interface SupervisorOptions {
  runtimeDir?: string;   // default: ARTEL_RUNTIME_DIR, then <dataDir>/runtime/<version>
  dataDir?: string;      // default: defaultDataDir()
  host?: string;         // default 127.0.0.1
  port?: number;         // proxy port; default: saved in config.json, first start tries 8088 then a free port
  publicUrl?: string;    // default http://<host>:<port>
  onEvent?: (event: SupervisorEvent) => void;
}

export type SupervisorEvent =
  | { type: 'service'; service: ServiceName; state: ServiceState; detail?: string }
  | { type: 'log'; service: ServiceName; line: string }
  | { type: 'ready'; url: string };

export interface RunningStack { url: string; attached: boolean; stop(): Promise<void>; }
export interface StackStatus {
  running: boolean; url?: string; pid?: number;
  services: Record<ServiceName, ServiceState>;
}

export function defaultDataDir(): string;
export function startStack(options?: SupervisorOptions): Promise<RunningStack>;
export function stopStack(options?: Pick<SupervisorOptions, 'dataDir'>): Promise<void>;
export function stackStatus(options?: Pick<SupervisorOptions, 'dataDir'>): Promise<StackStatus>;
export function logDir(options?: Pick<SupervisorOptions, 'dataDir'>): string;
```

- `startStack` returns `{ attached: true }` without starting anything when `state.json` names a live
  supervisor whose proxy answers. `stop()` on an attached handle does nothing; `stopStack` stops it.
- Data directory: `$XDG_DATA_HOME/artel` or `~/.local/share/artel`, `~/Library/Application Support/ARTEL`,
  `%LOCALAPPDATA%\ARTEL`. Files: `config.json` (mode 0600: secrets, ports), `state.json`, `pgdata/`,
  `storage/`, `home/` (dist with the placeholder replaced), `logs/<service>.log`, `runtime/<version>/`.
- Proxy: `/api/*`, `/oauth2/*`, `/login/oauth2/*`, `/ws/*` go to orchestration with WebSocket upgrade and no
  response buffering; everything else is served from `home/`, falling back to `index.html`.
- Added in ARTEL-1144 (2026-10-20): the proxy also answers `GET /__artel/supervisor` (the liveness check, returns
  the supervisor pid) and `POST /__artel/supervisor/stop`, which needs the `controlToken` from `state.json` (0600)
  in a header; `stopStack` uses it because Windows has no SIGTERM. A `supervisor.lock` file guards start.
  Postgres settings live in `pgdata/artel.conf`; postgres tools run with `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`
  set to `postgres/lib`.

### 4. CLI inside the desktop app (ARTEL-1146 ships, ARTEL-1144 honours)

The desktop app ships `bin/artel` and `bin/artel.cmd`, which run
`ELECTRON_RUN_AS_NODE=1 <app executable> <unpacked cli.js>` with `ARTEL_RUNTIME_DIR=<resources>/runtime`.
When `ARTEL_RUNTIME_DIR` is set, no `--api-url`, `ARTEL_API_BASE_URL` or credentials-file URL is given, and a
local stack is running, the CLI uses the local stack's URL as both the API and the console base URL.
