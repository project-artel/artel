# Move the model catalog into the database

## Goal

1. Add two AWS Bedrock catalog entries: Claude Haiku 5.5 and GPT-6.1 Sol.
2. Let an administrator turn any catalog model off from the admin page. A model that is
   off is hidden from the model pickers and refused when a request names it.
3. Move the model catalog out of `artel-agent-server/app/llm/models.py` (`LLMModel`,
   `MODEL_SPECS`) into the orchestration server's Postgres database. The orchestration
   server becomes the single source of truth; the agent-server reads the catalog from it.

This builds on the uncommitted self-host work (admin settings page, `platform_setting`,
`app/llm/api_key.py`) in the same working trees.

## Facts checked on 2026-10-14

- Bedrock `us-west-2` lists `us.anthropic.claude-haiku-5-5` and `us.openai.gpt-6.1-sol` as
  `ACTIVE` inference profiles, but a Converse call to either answers
  `... is not available for this account`. The same key calls
  `us.anthropic.claude-haiku-4-5-20251001-v1:0` and `openai.gpt-oss-20b-1:0` fine, so the
  key works and the account lacks access to these two models. Both entries are therefore
  seeded with `enabled = false`; an administrator turns them on once AWS grants access.
- OpenAI models on Bedrock take the reasoning effort as
  `additionalModelRequestFields.reasoning_effort` (checked on gpt-oss: `low`, `medium`,
  `high` accepted there, `xhigh` refused with a validation error). GPT-6.1 Sol itself could
  not be called, so its effort list comes from the OpenRouter catalog entry
  `openai/gpt-6.1-sol`: `max, xhigh, high, medium, low`, reasoning mandatory, 1,050,000
  context, 128,000 max completion, input `text, image, file`.
- Structured outputs for OpenAI models through Bedrock Converse are unverified, so the
  Sol entry uses `supports_strict_json = false` (tool-calling fallback), as the Haiku 5.5
  Bedrock entry already does.
- Bedrock pricing for GPT-6.1 Sol was not verified, so its `pricing` is null and
  `cost_usd` stays empty for it, following the rule in `ModelSpec.pricing`.

## Catalog entries after this change

Seed order is `sort_order` 10, 20, 30, ... in this order. Values are copied from the
current `MODEL_SPECS` in `artel-agent-server/app/llm/models.py` unless noted.

| id | label | enabled |
| --- | --- | --- |
| `openai/gpt-5.6-luna` | GPT-5.6 Luna | true |
| `openai/gpt-5.6-sol` | GPT-5.6 Sol | true |
| `openai/gpt-chat-latest` | GPT Chat Latest | true |
| `anthropic/claude-haiku-5.5` | Claude Haiku 5.5 | true |
| `anthropic/claude-sonnet-5` | Claude Sonnet 5 | true |
| `anthropic/claude-opus-5` | Claude Opus 5 | true |
| `google/gemini-3.8-flash` | Gemini 3.8 Flash | true |
| `google/gemini-3.7-flash` | Gemini 3.7 Flash | true |
| `google/gemma-4-31b-it:free` | Gemma 4 (free) | true |
| `x-ai/grok-4.6` | Grok 4.6 | true |
| `moonshotai/kimi-k3` | Kimi K3 | true |
| `z-ai/glm-5.3-flash` | GLM-5.3 Flash | true |
| `qwen/qwen3.8-max` | Qwen3.8 Max | true |
| `bedrock/us.anthropic.claude-haiku-5-5` | Claude Haiku 5.5 (AWS Bedrock) | false |
| `bedrock/us.openai.gpt-6.1-sol` | GPT-6.1 Sol (AWS Bedrock) | false |

New entry `bedrock/us.openai.gpt-6.1-sol`: provider `openai`, `supports_strict_json`
false, `max_input_tokens` 922000 (1,050,000 − 128,000), `input_modalities`
`["text","image","file"]`, reasoning kind `effort` with efforts
`["max","xhigh","high","medium","low"]`, pricing null.

## Database (orchestration, `V107__move_the_model_catalog_into_the_database.sql`)

V97 to V106 are taken on develop or on other open branches, so this uses V107.

Table `llm_model`:

| column | type | notes |
| --- | --- | --- |
| `id` | `VARCHAR(200) PRIMARY KEY` | catalog value; `bedrock/` prefix means the Bedrock route |
| `label` | `VARCHAR(200) NOT NULL` | |
| `provider` | `VARCHAR(32) NOT NULL` | OpenRouter author segment: `openai`, `anthropic`, `google`, `x-ai`, `moonshotai`, `z-ai`, `qwen` |
| `supports_strict_json` | `BOOLEAN NOT NULL` | |
| `max_input_tokens` | `INTEGER NOT NULL` | |
| `input_modalities` | `JSONB NOT NULL` | array of strings |
| `reasoning_kind` | `VARCHAR(16)` | `effort`, `max_tokens`, or null |
| `reasoning_efforts` | `JSONB` | array of strings or null |
| `reasoning_min_tokens` | `INTEGER` | |
| `reasoning_max_tokens` | `INTEGER` | |
| `reasoning_step` | `INTEGER` | |
| `pricing` | `JSONB` | object with the camelCase keys below, or null |
| `enabled` | `BOOLEAN NOT NULL DEFAULT TRUE` | |
| `sort_order` | `INTEGER NOT NULL` | |
| `updated_by` | `BIGINT REFERENCES app_user (id) ON DELETE SET NULL` | |
| `updated_at` | `TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP` | |

Adding a model is a new migration that inserts a row. The admin page only toggles
`enabled`.

## API contract

All JSON is camelCase, matching `/internal/settings/llm`.

### `GET /internal/llm-models` (internal port, no authentication)

Every row, enabled or not, ordered by `sort_order`. The agent-server needs disabled rows
too: it still prices and labels past usage, and internal callers (router, compaction)
may use any row.

```json
[
  {
    "id": "bedrock/us.anthropic.claude-haiku-5-5",
    "label": "Claude Haiku 5.5 (AWS Bedrock)",
    "provider": "anthropic",
    "supportsStrictJson": false,
    "maxInputTokens": 872000,
    "inputModalities": ["text", "image"],
    "reasoning": {
      "kind": "effort",
      "efforts": ["max", "xhigh", "high", "medium", "low"],
      "minTokens": null,
      "maxTokens": null,
      "step": null
    },
    "pricing": {
      "inputPerMtok": 0.10,
      "outputPerMtok": 0.50,
      "cacheWritePerMtok": 0.125,
      "cacheReadPerMtok": 0.01,
      "asOf": "2026-10-13",
      "source": "Anthropic Claude Haiku 5.5 overview",
      "longContextThresholdTokens": 100000,
      "longContextInputPerMtok": 0.50,
      "longContextOutputPerMtok": 2.50,
      "longContextCacheWritePerMtok": 0.625,
      "longContextCacheReadPerMtok": 0.05
    },
    "enabled": false,
    "sortOrder": 140
  }
]
```

`reasoning` is null when `reasoning_kind` is null. `pricing` is null when the column is
null; inside it, the `longContext*` keys may be null.

### `GET /api/qa-models` (existing, signed-in users)

Same response shape as today (`QaModelResponse`), now built from `llm_model` where
`enabled = true`, ordered by `sort_order`. `supportsVision` is `"image" in
inputModalities`; `multimodal` is `inputModalities.size > 1`. The orchestration server
no longer calls the agent-server's `GET /models` for this.

### `GET /api/admin/llm-models` (ADMIN only)

Every row, ordered by `sort_order`:

```json
[
  {
    "id": "bedrock/us.openai.gpt-6.1-sol",
    "label": "GPT-6.1 Sol (AWS Bedrock)",
    "provider": "openai",
    "route": "bedrock",
    "enabled": false,
    "supportsVision": true,
    "maxInputTokens": 922000,
    "updatedAt": "2026-10-14T00:00:00Z"
  }
]
```

`route` is `bedrock` when `id` starts with `bedrock/`, otherwise `openrouter`.

### `PATCH /api/admin/llm-models` (ADMIN only)

Request body `{ "id": "google/gemma-4-31b-it:free", "enabled": false }`. The id is in the
body rather than the path because ids contain `/` and `:`. Response: the updated row in
the `GET /api/admin/llm-models` shape. Unknown id: 404. Records `updated_by` and
`updated_at`.

### OpenRouter key check

`REQUIRED_OPENROUTER_MODELS` is replaced by a query: enabled rows whose id does not start
with `bedrock/`, plus the embedding model (`artel.knowledge.backfill.model`). A disabled
model no longer has to be reachable with the key.

## Where "disabled" is enforced

- Pickers: `/api/qa-models` lists enabled rows only.
- Requests that name a model: the agent-server refuses a disabled model with a 422
  validation error on the request models that carry a user's choice (QA session start,
  scenario session create and update). Model ids not in the catalog are refused the same
  way they are today.
- Internal callers keep working: `router_model`, `compaction_model`, `DEFAULT_MODEL` and
  usage pricing resolve any catalog row, enabled or not.

## Agent-server

- New `app/llm/catalog.py`, following `app/llm/api_key.py`: fetches
  `GET {ORCHESTRATION_BASE_URL}/internal/llm-models`, caches it for
  `model_catalog_ttl_seconds` (30), times out after `model_catalog_fetch_timeout_seconds`
  (3), keeps the last good catalog when a refresh fails, and raises a clear error when no
  catalog has ever loaded.
- `LLMModel` stops being a `StrEnum`. Model ids are strings validated against the catalog.
  `DEFAULT_MODEL` becomes the string `openai/gpt-5.6-luna`. `MODEL_SPECS` goes away;
  `get_model_spec` reads the catalog.
- Tests load a fixture catalog that mirrors the seed rows above instead of calling the
  orchestration server.
- Bedrock calls branch on the spec's provider: `anthropic` keeps adaptive `thinking` and
  `output_config.effort`; `openai` sends `reasoning_effort`, sends no `thinking`, and gets
  no `cachePoint` blocks.
- `GET /models` and `GET /models/required` are removed; nothing calls them once the
  orchestration server reads its own table.

## Admin page

A model section in the admin settings view lists every row from
`GET /api/admin/llm-models` with an on/off switch that calls
`PATCH /api/admin/llm-models`, a route badge (OpenRouter or AWS Bedrock), and the
provider. It follows `.agents/docs/DESIGN.md`.

## Validation

- orchestration: targeted integration tests for the migration seed, the three endpoints,
  ADMIN gating, and the key check reading the table.
- agent-server: full pytest with the fixture catalog; unit tests for the catalog client
  (TTL, stale-on-failure, never-loaded error) and the Bedrock OpenAI request fields.
- admin-page: API parser tests and a render test for the switch.
- Not verified end to end: no Bedrock call to Haiku 5.5 or GPT-6.1 Sol can succeed until
  AWS grants the account access.

## Follow-up: provider keys live only in the database

Decided on 2026-10-14, to start after the three tracks above are integrated, because it
touches the same files (`app/config.py`, `app/llm/api_key.py`, the orchestration
`settings` package, `SettingsView`).

- The OpenRouter key and the Bedrock API key are both stored encrypted in
  `platform_setting` (AES-GCM, key derived from `ARTEL_SECRETS_KEY`). `ARTEL_SECRETS_KEY`
  is the only secret left in `.env`.
- The environment fallbacks are removed: `OPENROUTER_API_KEY` / `LLM_API_KEY` in both
  servers and `BEDROCK_API_KEY` in the agent-server. Every install enters its keys on the
  admin page once.
- When no Bedrock key is stored, the agent-server still lets the standard AWS credential
  chain answer (an IAM role, for example). That chain is not a key in `.env`.
- `BEDROCK_REGION` stays in `.env`: it is not a secret and rarely changes.
- `GET /internal/settings/llm` returns both keys. The admin page gets a Bedrock key input
  and a check that calls Converse once for every enabled Bedrock catalog row, reporting
  reachable and refused models the way the OpenRouter check does.

### Dropping the agent-server's cached key and catalog from the admin page

The agent-server keeps a fetched key for `llm_key_cache_ttl_seconds` (30) and the catalog
for `model_catalog_ttl_seconds` (30). An administrator who rotates a leaked key should not
have to wait for that.

- agent-server: `POST /internal/llm-cache/invalidate` drops both cached values; the next
  model call fetches them again from the orchestration server.
- orchestration: `POST /api/admin/settings/llm/invalidate-cache` (ADMIN only) calls that
  endpoint and reports whether the agent-server answered. Saving or deleting a key and
  toggling a model call it too, so the change takes effect on the next model call.
- admin page: a "캐시된 키 비우기" button in the key section showing the result.
- Limit: the orchestration server calls the single `artel.agent.base-url`. With several
  agent-server replicas behind one address, only the replica that answers drops its
  cache; the others still expire within the 30-second TTL.

## Follow-up contract (fixed before the second round of workers)

### Settings stored in `platform_setting`

| setting_key | encrypted | meaning |
| --- | --- | --- |
| the existing OpenRouter key row | yes | unchanged |
| `bedrock.api_key` | yes | Bedrock API key (bearer token) |
| `bedrock.last_check` | no | JSON of the last Bedrock check, like the OpenRouter one |

The environment fallbacks are removed everywhere: orchestration `artel.llm.openrouter-api-key`
(`OPENROUTER_API_KEY`), agent-server `llm_api_key` (`LLM_API_KEY` / `OPENROUTER_API_KEY`) and
`bedrock_api_key` (`BEDROCK_API_KEY`). `LlmKeySource` keeps only `admin` and `none`.
Region stays in the environment: agent-server `BEDROCK_REGION`, orchestration
`artel.bedrock.region` (`BEDROCK_REGION`, default `us-west-2`) for the check call.

### `GET /internal/settings/llm` (changed shape)

```json
{ "openrouterApiKey": "sk-or-...", "bedrockApiKey": null }
```

Either may be null. `toString` must keep hiding both values.

### Bedrock key admin API (ADMIN only)

- `GET /api/admin/settings/bedrock` → `{ "configured": true, "maskedKey": "…abcd", "updatedAt": "...", "region": "us-west-2", "lastCheck": BedrockCheck | null }`
- `PUT /api/admin/settings/bedrock` body `{ "apiKey": "..." }`; null or blank deletes the key and `bedrock.last_check`. Responds with the `GET` shape. 409 `secrets_key_missing` when `ARTEL_SECRETS_KEY` is empty, as for OpenRouter.
- `POST /api/admin/settings/bedrock/check` → `BedrockCheck`:
  `{ "checkedAt": "...", "keyConfigured": true, "models": [ { "id": "bedrock/us.openai.gpt-6.1-sol", "reachable": false, "error": "openai.gpt-6.1-sol is not available for this account. ..." } ] }`.
  It sends one Converse call (`maxTokens` 16, prompt "ping") to
  `https://bedrock-runtime.{region}.amazonaws.com/model/{id without bedrock/}/converse`
  with `Authorization: Bearer <key>` for every **enabled** Bedrock row; `reachable` is a
  2xx answer, `error` is the provider's `message` (truncated to 300 characters) or the
  transport error. No key stored: `keyConfigured` false and `models` empty, no calls.

### Cache invalidation

- agent-server `POST /internal/llm-cache/invalidate` → 204. Drops the cached keys (OpenRouter
  and Bedrock) and the cached catalog's freshness, so the next model call asks the
  orchestration server again.
- orchestration `POST /api/admin/settings/llm/invalidate-cache` (ADMIN only) →
  `{ "agentServerInvalidated": true, "error": null }`. It calls
  `POST {artel.agent.base-url}/llm-cache/invalidate` with a 3-second timeout (the base URL
  already ends in `/internal` in deployments, e.g. `http://agent-server:8000/internal`); a
  failure is reported in `error`, never thrown as 5xx.
- The orchestration server also calls it, best effort, after saving or deleting either
  key and after `PATCH /api/admin/llm-models`. A failed call never fails the save.

### QA run and try creation

`CreateQaRunRequest.model` and `CreateQaTryRequest.model`, when present, are checked against
`llm_model` before anything is forwarded: unknown id → 400 `llm_model_unknown`, disabled →
400 `llm_model_disabled`, each with a message naming the id.

## Follow-up: Claude API key as a third route

Requested on 2026-10-14 after the first PRs. Lands as extra commits on
artel-orchestration-server#307 and artel-agent-server#224 (still drafts), plus new PRs for
admin-page, onboarding and the root repo.

### Route and catalog rows

- Catalog id = `claude/` + the Anthropic model id. `claude/` routes to the Anthropic API with the
  official SDK through `langchain-anthropic` (`ChatAnthropic`); `anthropic/...` stays OpenRouter
  and `bedrock/...` stays Bedrock. Provider is `anthropic`.
- Seed rows, appended to the V107 seed (not merged yet, so edited in place), all
  `enabled = false` until an administrator stores a key and the check passes:

| id | label | max_input_tokens | input | efforts | pricing per MTok (input / output / cache write / cache read) |
| --- | --- | --- | --- | --- | --- |
| `claude/claude-opus-5-5` | Claude Opus 5.5 (Claude API) | 872000 | text, image, file | max, xhigh, high, medium, low | 4.00 / 20.00 / 5.00 / 0.20 |
| `claude/claude-sonnet-5-5` | Claude Sonnet 5.5 (Claude API) | 872000 | text, image, file | max, xhigh, high, medium, low | 2.00 / 10.00 / 2.50 / 0.20 |
| `claude/claude-haiku-5-5` | Claude Haiku 5.5 (Claude API) | 872000 | text, image, file | max, xhigh, high, medium, low | 0.10 / 0.50 / 0.125 / 0.01, above 100K prompt tokens 0.50 / 2.50 / 0.625 / 0.05 |
| `claude/claude-fable-5-1` | Claude Fable 5.1 (Claude API) | 872000 | text, image, file | max, xhigh, high, medium, low | 10.00 / 50.00 / 12.50 / 0.25 |

  1M context minus 128K output = 872,000. Reasoning kind `effort`. `supports_strict_json` true
  (structured outputs via `output_config.format`). Pricing `asOf` 2026-10-14, source "Anthropic
  model table (claude-api skill, cached 2026-10-06)"; the cache write price is 1.25x input
  (5-minute TTL). The Anthropic API does not return a cost, so these rows carry pricing.

### Request shape (agent-server)

- `temperature` is never sent (Opus 5.5 / Fable 5.1 reject sampling; Sonnet 5.5 / Haiku 5.5
  reject non-default values). `max_tokens` 128,000 with streaming.
- Effort → adaptive thinking plus `output_config.effort`. No effort chosen → omit both.
- `ReasoningConfig.disabled` (router-style calls): Opus 5.5 and Fable 5.1 cannot turn thinking
  off, so send effort `low`; Sonnet 5.5 sends `thinking: {type: "between_tools"}`; Haiku 5.5 sends
  `thinking: {type: "disabled"}`. This mapping lives in code keyed by model id.
- Never force `tool_choice` `any`/`tool` (400 on Opus 5.5, Sonnet 5.5, Fable 5.1); structured
  output uses `json_schema`.
- Prompt caching: top-level `cache_control: {type: "ephemeral"}` when `cache_prompt` is set.
- Client is rebuilt when the stored key changes (same approach as Bedrock); a 401 drops the cached
  key.

### Key storage and API (orchestration)

- `platform_setting` key `anthropic.api_key` (encrypted with `SecretCipher`, own associated data)
  and `anthropic.last_check` (plain JSON).
- `GET /internal/settings/llm` → `{ openrouterApiKey, bedrockApiKey, anthropicApiKey }`.
- ADMIN only:
  - `GET /api/admin/settings/anthropic` → `{ configured, maskedKey, updatedAt, lastCheck }`
  - `PUT /api/admin/settings/anthropic` body `{ apiKey }`; null or blank deletes. 409
    `secrets_key_missing` without `ARTEL_SECRETS_KEY`. Key must start with `sk-ant-`, 400
    `invalid_api_key` otherwise.
  - `POST /api/admin/settings/anthropic/check` → `{ checkedAt, keyConfigured, keyValid, models: [{ id, reachable, error }] }`.
    One `GET https://api.anthropic.com/v1/models?limit=1000` with `x-api-key` and
    `anthropic-version: 2023-06-01`; 401 → `keyValid` false; otherwise each **enabled** `claude/`
    row is reachable when its model id appears in the list. Base URL is the property
    `artel.anthropic.base-url` so tests use a fake server.
- Saving or deleting the key triggers the agent-server cache invalidation, like the other keys.
