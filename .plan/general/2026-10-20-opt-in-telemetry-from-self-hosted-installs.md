# 2026-10-20 — Opt-in telemetry from self-hosted installs

- Date: 2026-10-20
- GitHub Issue: None
- Status: Draft

## Goal

A self-hosted ARTEL install whose admin agreed sends one aggregated report per day to the
orchestration server on artel.kr. The report tells us which QA agent structures are used, how many
steps they pass, which tools they call how often, how many tokens each model spends, and which
errors stop runs. Nothing is sent without consent, and the default is off.

## Non-goals

- Raw QA run records: `qa_log` messages, agent reasoning, actions, screen captures, game state.
- Content maps, knowledge documents, scenarios, test case text, project or game names.
- User data: emails, names, user ids, IP addresses (the receiver does not store the sender IP).
- A dashboard for the received data. Version one is queried with SQL.
- Telemetry from the SDK inside a game or from `artel-cli`.

## Context / Constraints

From the survey (paths relative to each repository):

- The agent-server only talks to orchestration, over the QA WebSocket and `POST /internal/llm-usage`.
  Everything this report needs is already in the orchestration database, so aggregation and sending
  live in orchestration only.
- `qa_try` has `agent_arch`, `agent_fingerprint`, `model`, `status`, `steps_total`, `steps_passed`,
  `cases_total`, `cases_passed`, `started_at`, `completed_at` (V25, V35). Run duration is
  `completed_at - started_at`; no column stores it.
- Tool calls are `qa_log` rows with `type = 'TOOL'`; the tool name is in `payload`.
  Errors are `qa_log` rows with `type = 'ERROR'`; `ErrorPayload.code` is today always `run_incomplete`
  and the reason is free text in `message` (`app/qa/service.py:~265`).
- `llm_usage` holds per-call `service`, `provider`, `model`, token columns, `cost_usd`,
  `latency_ms`, `key_source`, `called_at`.
- `platform_setting` (V97) stores settings by key; `PlatformSettingRepository.upsert` requires a
  non-null `updatedBy`. `AnthropicKeyService` is the pattern to copy.
- Admin endpoints check `platformAccessService.requireAdmin(userId)` per handler.
- `POST /api/auth/signup` (`PasswordAccountService.kt:71`) makes the first user `ADMIN` under
  `FirstUserGate`. GitHub-first installs get `ADMIN` through SQL, so signup cannot be the only
  consent path.
- Public paths are listed as `permitAll` in `SecurityConfig.kt:163-210`. `/internal/**` is trusted
  only because it is on port 8081, so the receiver must not live there. The only rate limiter is
  `LoginAttemptLimiter`.
- Schedulers follow `TestCaseEmbeddingScheduler.kt`; the pool size is 3
  (`ARTEL_SCHEDULING_POOL_SIZE`), so a fourth job raises it to 4.
- Outbound HTTP uses `WebClient` with explicit timeouts (`OpenRouterModelClient.kt:52`).
- The orchestration server has no runtime version (pom says `0.0.1-SNAPSHOT`). The agent-server's
  `git_sha` and `image_tag` are in each `qa_run.run_config`.
- Highest Flyway migration is V111. Check develop and every open branch before taking V112.
- `deploy/install.sh` runs as `curl | sh`, has no tty and never prompts. Settings are YAML anchors at
  the top of `deploy/docker-compose.yml`, filled by an awk pass.
- `artel-home` admin settings: `src/admin/settings/SettingsPage.tsx` and `settingsApi.ts`.
  Signup form: `src/auth/PasswordLoginForm.tsx`. Messages: `src/i18n/messages/*.ts` (ko, en).
- `onboarding` FAQ (`src/i18n/messages.ts:810-811`) says self-hosted data stays on the machine. That
  sentence becomes false for a consenting install and must change.
  `src/pages/composeFile.generated.ts` is regenerated from the compose file.

## Decisions

1. **Where the switch lives.** Two settings:
   - `ARTEL_TELEMETRY_URL` (orchestration, `artel.telemetry.endpoint`). Blank by default in
     `application.yml`, so the hosted artel.kr server never sends and hides the admin section.
     `deploy/docker-compose.yml` sets it to `https://stage-orch.artel.kr/api/telemetry/reports`, the
     same host `artel-cli` already uses as its default (`artel-cli/src/config.ts:7`).
   - Consent. The effective value is the `telemetry.consent` platform setting when present, else the
     `ARTEL_TELEMETRY` environment variable (`on` or `off`, default `off`). Once an admin decides in
     the UI, the database value wins over the environment.
2. **Where consent is asked.**
   - `install.sh --telemetry` or `ARTEL_TELEMETRY=on sh install.sh` writes `on` into a new
     `x-telemetry` anchor. Without either, it writes `off` and prints one line saying how to turn it on.
   - The first-admin signup form shows an unchecked checkbox when `GET /api/auth/providers` reports
     `telemetryAvailable: true` and no consent is stored. `SignupRequest` gets
     `telemetryOptIn: Boolean? = null`, written inside the signup transaction for the first user only.
   - `/admin/settings` gets a telemetry section: toggle, install id, last sent date, and a preview of
     the exact JSON that the next report will send.
3. **Install id.** A random UUID stored as `telemetry.install_id`, created the first time consent turns
   on. It identifies an install, not a person, and it is the only key the receiver stores.
4. **Report content** (`schemaVersion: 1`, one per UTC day, built only from that day's rows):
   - `install`: `installId`, `orchestrationVersion`, `agentServerVersions` (distinct `image_tag` or
     `git_sha` seen in `run_config` that day), `reportDate`.
   - `qaStructures[]`, grouped by `agentArch`, `agentFingerprint`, `model`, `reasoningEffort`:
     `tries`, `triesByStatus`, `stepsTotal`, `stepsPassed`, `casesTotal`, `casesPassed`,
     `durationSecondsSum`, `durationSecondsMax`, `toolCalls` (map of tool name to count).
   - `llmUsage[]`, grouped by `service`, `provider`, `model`, `keySource`: `calls`, the five token
     sums, `costUsdSum`, `latencyMsSum`.
   - `errors[]`, grouped by `source` (`qa_run` or `orchestration`), `code`, `exceptionType`:
     `count`, and `frames` from the first occurrence.
5. **What a tool name may be.** Only names of tools shipped in the agent-server. A name outside the
   built-in set is counted under `other`, so a game-registered function name
   (plans of 2026-10-13 and 2026-10-14) never leaves the install. The built-in set is the `tools` list
   in `run_config` minus anything the game registered; until game functions merge, that is the whole
   list.
6. **Error detail without free text.** Messages are never sent.
   - agent-server: `ErrorPayload` gains `exceptionType` (class name) and `frames` (up to 10
     `module:function:line` entries under `app/`, no file system paths). `run_with_deadline` fills them.
   - orchestration: the global exception handler records 5xx exceptions into a new
     `telemetry_error_event` table with the class name and up to 10 frames under `kr.artel`, only while
     consent is on. Rows older than 14 days are deleted by the sending job.
7. **Sending.** A `TelemetryReportScheduler` runs every hour. If consent is on and the last sent date
   is before yesterday, it sends each missing day, oldest first, at most 7 days back, then stores
   `telemetry.last_sent_date`. Timeout 10 seconds, failure logs a warning and retries next hour.
   Each send logs one INFO line with the report date and byte size.
8. **Receiving** (artel.kr orchestration). `POST /api/telemetry/reports`, `permitAll`, body limit
   256 KB, JSON schema validated, an in-memory limiter of 30 requests per hour per address, answers 204.
   Stored in `telemetry_report` (`install_id`, `report_date`, `schema_version`, `report` JSONB,
   `received_at`), unique on `install_id, report_date` and upserted. The sender address is not stored.
   `DELETE /api/telemetry/reports/{installId}` deletes all rows for that install; the admin toggle offers
   it when turning consent off.
9. **Version.** Orchestration reads `ARTEL_VERSION` (set by the image build, the compose image tag as
   fallback). No static pom value is sent.

## Approach (Checklist)

- [x] **Step 0: Recon** (three surveys, summarised above)
- [ ] **Step 1: Implementation**, four tracks with disjoint write scopes
  - [ ] Track A, `artel-orchestration-server`: settings, consent service, report builder, scheduler,
        sender client, receiver controller and limiter, `telemetry_report` and `telemetry_error_event`
        migrations, `SignupRequest.telemetryOptIn`, `AuthProvidersResponse.telemetryAvailable`,
        admin endpoints `GET/PUT /api/admin/settings/telemetry` and `GET .../telemetry/preview`,
        `ARTEL_VERSION`, scheduler pool size 4.
  - [ ] Track B, `artel-agent-server`: `exceptionType` and `frames` on `ErrorPayload`.
  - [ ] Track C, `artel-home`: signup checkbox, admin telemetry section with preview and delete,
        ko and en messages.
  - [ ] Track D, workspace `deploy/` and `onboarding`: `x-telemetry` anchor, `ARTEL_TELEMETRY` and
        `ARTEL_TELEMETRY_URL` on orchestration, `install.sh --telemetry`, FAQ sentence, a telemetry
        section on the self-hosting page listing every field above, regenerated
        `composeFile.generated.ts`.
  - Track C and D code against the API contract below; Track A owns it.
- [ ] **Step 2: Tests**
  - Report builder against fixture rows: grouping, null summaries, tool name `other` bucket, day bounds.
  - Consent precedence: environment only, database over environment, signup only for first user.
  - Receiver: 204, upsert on resend, 413 over 256 KB, 400 on schema mismatch, 429 over the limit.
  - Sender does nothing with a blank endpoint or consent off.
  - agent-server: `frames` contain no absolute path and no message text.
- [ ] **Step 3: Rollout / Rollback**
  - Deploy the receiver to artel.kr first, then release images and compose with the endpoint set.

## API contract

| Method and path | Who | Body or response |
| --- | --- | --- |
| `GET /api/auth/providers` | anyone | adds `telemetryAvailable` (endpoint set and no consent stored yet) |
| `POST /api/auth/signup` | anyone | adds optional `telemetryOptIn` |
| `GET /api/admin/settings/telemetry` | admin | `{ available, enabled, source: "setting"\|"environment", installId, lastSentDate }` |
| `PUT /api/admin/settings/telemetry` | admin | `{ enabled, deleteSentData? }` |
| `GET /api/admin/settings/telemetry/preview` | admin | the report JSON for yesterday, exactly as it would be sent |
| `POST /api/telemetry/reports` | public, artel.kr | report JSON, answers 204 |
| `DELETE /api/telemetry/reports/{installId}` | public, artel.kr | answers 204 |

## Validation

- **Commands to run:** orchestration `mvn test -Dkotlin.compiler.daemon=false` on the telemetry
  tests; agent-server `LANGSMITH_TRACING=false pytest` on the envelope and runner tests;
  `artel-home` and `onboarding` type check and tests.
- **Expected output:** new tests pass; the preview endpoint on a local stack after one QA run shows
  one `qaStructures` row with the run's `agentArch` and its tool counts; a local receiver gets the
  same JSON.

## Risks & Rollback

- **Risks:**
  - A tool or error field carries game content. Mitigated by decision 5 and 6; the preview lets an
    admin check before agreeing.
  - The public receiver is abused. Mitigated by size limit, schema check and per-address limit.
  - The hosted server reports to itself. Prevented by the blank default endpoint.
- **Rollback steps:** set `ARTEL_TELEMETRY_URL` blank; revert the receiver; the tables stay empty.

## Open Questions

- Resolved: the receiver is `https://stage-orch.artel.kr`. If a production host replaces it later,
  installs already deployed keep the old URL until they update the compose file, so the stage host
  must keep accepting reports or redirect them.
- Should the telemetry section also be visible on the hosted artel.kr? Decision 1 hides it.
