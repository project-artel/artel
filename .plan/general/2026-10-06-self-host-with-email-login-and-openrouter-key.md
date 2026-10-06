# Self-host ARTEL with email login, an admin role and an OpenRouter key

## Goal

Let anyone run ARTEL on their own machine with one command, sign in with an email and a password, and
use a single OpenRouter API key for every model call. The first person to sign up becomes the admin.

## Current state (from the survey)

- Login is GitHub OAuth only. `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are required to boot
  (`artel-orchestration-server/src/main/resources/application.yml`).
- `app_user.platform_role` has `USER` and `DEVELOPER`. There is no `ADMIN` and no write endpoint
  that sets a role. Latest Flyway migration is V92, so the next one is V93.
- Cookies `artel_access_token` and `artel_refresh_token` are issued by `JwtService` and `AuthCookies`.
- The orchestration server holds no LLM key. `artel-agent-server` reads `LLM_API_KEY` (alias
  `OPENROUTER_API_KEY`) and `LLM_BASE_URL` from its environment. OpenRouter is already the default path.
- Models a key must reach: 12 chat slugs in `app/llm/models.py:37-48` and the embedding model
  `openai/text-embedding-3-large`. The default model is `openai/gpt-5.6-luna`.
- `app/agents/scenario/router.py:46` pins `ROUTER_MODEL` to a Bedrock Haiku 4.5 model. An OpenRouter-only
  install fails at that call.
- No docker-compose file, no install script, no self-hosting document exists. The onboarding FAQ says
  "Self-hosting is not offered yet."
- S3 is needed in practice (`ARTEL_S3_BUCKET`, `ARTEL_S3_REGION`; MinIO works through `ARTEL_S3_ENDPOINT`).
  PostgreSQL must be the `pgvector/pgvector:pg16` image. Redis is needed for SDK login codes.

## Decisions (recommended defaults, open to change)

1. **Password login.** New table `local_credential` (`app_user_id`, `password_hash` as BCrypt,
   `must_change_password`, timestamps). Login and signup issue the same JWT cookies as OAuth.
   GitHub OAuth becomes optional: the server boots without the two GitHub variables, and the GitHub
   registration is created only when both `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are non-blank.
   A request to `/oauth2/authorization/github` without them answers 404 instead of redirecting.
   `artel-home` shows the GitHub button only when the server reports `github: true`; the email form is always shown.
2. **Admin role.** Add `ADMIN` to `PlatformRole`. The first signup becomes `ADMIN`, decided inside one
   transaction guarded by an advisory lock so two simultaneous signups cannot both win. After the first
   user, public signup is closed unless `ARTEL_SIGNUP_OPEN=true`.
3. **Admin creates users.** `POST /api/admin/users` creates an account with a random 20-character
   password, returned once in the response, with `must_change_password=true`. Until the password is
   changed, every endpoint except `GET /api/auth/me` and `POST /api/auth/password` answers 403.
   The check reads the database, as `PlatformAccessService` already does.
4. **OpenRouter key.** Source order: the admin page value, then the `OPENROUTER_API_KEY` environment variable.
   The page value is stored in `platform_setting`, encrypted with AES-GCM under a key derived from
   `ARTEL_SECRETS_KEY`. It is never returned by any endpoint, only a masked tail and a "key works" result.
   `artel-agent-server` asks orchestration for the key through the internal port 8081, caches it for a short
   time, and falls back to its own environment.
5. **Bedrock is optional.** `ROUTER_MODEL` becomes a setting whose default is `openai/gpt-5.6-luna`, the catalog's
   default model, so no Bedrock credential is needed anywhere. The `bedrock/...` catalog entry and `BEDROCK_*`
   settings stay for operators who have them, but nothing in a default install calls Bedrock, and the server
   boots and passes its tests without any `BEDROCK_*` value.
6. **Packaging.** One `docker-compose.yml` in the parent repository under `deploy/` with postgres (pgvector),
   redis, minio, orchestration, agent-server, admin-page, artel-home, and one reverse proxy that serves all
   of them on one origin, so cookies work without CORS setup. `install.sh` writes `.env` with generated secrets,
   pulls the images and starts the stack. The same page documents plain `docker run` commands.
7. **Onboarding.** A new `/self-hosting` page in Korean and English: one-line install, compose commands,
   `docker run` commands, OpenRouter key setup (admin page or environment variable), the model list the key
   must reach, and the admin and user flow. The FAQ line changes, with `shipped` and `planned` badges kept honest.

## API contract (orchestration server)

| Method and path | Who | Purpose |
| --- | --- | --- |
| `GET /api/auth/providers` | anyone | `{ "password": true, "github": <both GitHub variables set>, "signupOpen": <first user pending or ARTEL_SIGNUP_OPEN> }` |
| `POST /api/auth/signup` | anyone, first user or `ARTEL_SIGNUP_OPEN` | email, password, name; first user is `ADMIN` |
| `POST /api/auth/login` | anyone | email, password; sets cookies |
| `POST /api/auth/password` | signed in | current and new password; clears `must_change_password` |
| `GET /api/auth/me` | signed in | adds `platformRole` `ADMIN` and `mustChangePassword` |
| `GET /api/admin/users` | `ADMIN` | list users |
| `POST /api/admin/users` | `ADMIN` | create user, returns the temporary password once |
| `POST /api/admin/users/{id}/reset-password` | `ADMIN` | new temporary password |
| `PATCH /api/admin/users/{id}` | `ADMIN` | role, disabled |
| `GET /api/admin/settings/llm` | `ADMIN` | masked key, source, last check |
| `PUT /api/admin/settings/llm` | `ADMIN` | set or clear the key |
| `POST /api/admin/settings/llm/check` | `ADMIN` | asks OpenRouter which of the required models the key reaches |
| `GET /internal/settings/llm` | agent-server, port 8081 only | the key |

## Work tracks (disjoint write scopes)

| Track | Repository | Scope | Depends on |
| --- | --- | --- | --- |
| A | `artel-orchestration-server` | V93 migration, credentials, signup and login, `ADMIN`, admin API, settings, OAuth optional, tests | none |
| B | `artel-agent-server` | key from orchestration with env fallback, `ROUTER_MODEL` setting, `.env.example`, required-model list endpoint, tests | contract only |
| C | `admin-page`, `artel-home` | users tab, settings tab, email login form, forced password change screen | contract only |
| D | parent repository `deploy/` | compose file, reverse proxy, frontend Dockerfiles, `install.sh`, `docker run` reference | contract only |
| E | `onboarding` | `/self-hosting` page, FAQ, i18n, `npm run check` | D for exact commands |

Track E waits for D's command names; A, B, C and D start together.

## Validation

- A: boot test with no GitHub variables, and `providers` reporting `github: false` then `true`.
- C: `artel-home` hides the GitHub button when `github: false`.
- A: unit and integration tests for first-user race, signup closed after the first user, forced password change,
  admin-only endpoints, key never serialized. Flyway check script.
- B: pytest with `LANGSMITH_TRACING=false`.
- C and E: `npm run build` and the repository check scripts. Screens checked with a minted JWT.
- D: `docker compose config`, then a full boot on this machine and a signup through the proxy.

## Open questions

- Decided: the repositories and the container images are public, with images at `ghcr.io/project-artel/<name>`.
  Making them public on GitHub is a manual step for the owner; this plan does not change visibility.
- Decided: the license is AGPL-3.0. The parent repository has `LICENSE` with the unmodified GNU text. Each submodule
  gets the same file after tracks A to D finish, so no track's write scope is touched.
- Still open: where `install.sh` is hosted (candidate: raw GitHub URL of the parent repository).
