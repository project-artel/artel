# 2026-10-20 — Project agent wire contract

- Date: 2026-10-20
- Jira: ARTEL-1125 (story), ARTEL-1126 agent-server, ARTEL-1127 orchestration, ARTEL-1128 / 1129 / 1130 home
- Plan: `2026-10-16-project-agent-that-operates-the-workspace.md`. This file replaces that plan's
  "Server chat endpoint", "Client-side tool protocol", and "Conversation storage" sections.
  Where the two disagree, this file wins.

## Change from the plan: a stateless step call

The plan kept a WebSocket open between orchestration and agent-server and let a LangChain loop
await each browser tool result on a future. That loses the turn when the socket drops or a
server restarts, and needs timers for every wait.

Instead agent-server exposes one stateless call that runs the model **once**. Orchestration owns
the loop:

```text
browser                      orchestration                           agent-server
POST messages ───────────▶  store USER, status RUNNING
                            build history from DB ──POST /step──────▶ one model call
                            ◀──────────── {content, tool_calls} ─────
                            store ASSISTANT (tool calls in payload)
◀── SSE message ──────────  status AWAITING_TOOL (or IDLE if no calls)
run tool, highlight, approve
POST tool-results ────────▶ store TOOL_RESULT
                            all calls of that ASSISTANT answered? ──POST /step──▶ ...
```

Nothing waits on anything. A closed tab leaves the conversation in `AWAITING_TOOL`; the next
time it opens, the browser sees unanswered calls and offers to continue or stop.

## 1. agent-server: `POST /internal/project-agent/step`

Router `app/api/project_agent.py`, mounted under `INTERNAL_PREFIX` like the others.

Request (snake_case, pydantic):

```json
{
  "conversation_id": 12,
  "project_id": 1,
  "model": "openai/gpt-6-luna",
  "locale": "ko",
  "tools_enabled": true,
  "page_catalog": { "pages": [ ... ] },
  "messages": [
    { "role": "user", "content": "QA 돌려 줘" },
    { "role": "assistant", "content": "QA 실행 페이지를 엽니다.",
      "tool_calls": [ { "id": "call_1", "name": "open_page", "args": { "page": "qa" } } ] },
    { "role": "tool", "tool_call_id": "call_1", "content": "{\"status\":\"ok\",\"page\":{...}}" }
  ]
}
```

- `model` may be null; agent-server then uses `DEFAULT_MODEL`. An unknown or disabled model is 422.
- `tools_enabled: false` binds no tools, so the model must answer in text. Orchestration sends it
  when the turn has used its 30 tool calls.
- `page_catalog` is opaque JSON produced by the browser (section 4). agent-server renders it into
  the system prompt as text; it does not validate its inner shape beyond `pages` being a list.

Response:

```json
{
  "content": "QA 실행 페이지를 엽니다.",
  "tool_calls": [ { "id": "call_1", "name": "open_page", "args": { "page": "qa" } } ]
}
```

- `id` is the provider's tool call id, or a generated `call_<uuid>` when the provider gives none.
- Provider errors are 502 with `detail`. agent-server stores nothing.
- Usage is booked with service `PROJECT_AGENT` and the conversation id as the reference
  (`set_usage_scope`). Add `PROJECT_AGENT` to `Service` in `app/llm/usage.py`.

### Tools (agent-server owns the schemas)

| Name | Args | Meaning |
| --- | --- | --- |
| `open_page` | `page` (enum of page ids, section 4), `params` (object of strings, optional) | Open a page beside the chat. Returns the new page snapshot. |
| `read_page` | none | The open page's snapshot: fields with values and options, actions with why they are blocked. |
| `set_field` | `field` (string), `value` (any JSON) | Write one field of the open page. |
| `call_action` | `action` (string), `args` (object, optional) | Run one action of the open page. An approval action waits for the user. |
| `ask_choice` | `question` (string), `options` (array of `{id, label}`, 2–8), `multiple` (bool, optional) | Show a choice card. Returns the picked ids. |
| `query` | `kind` (`qa_history`, `qa_run`, `issues`, `usage`), `args` (object, optional) | Read-only lookup. |
| `watch_job` | `kind` (`content_map_scan`, `qa_run`), `id` (string), `label` (string, optional) | Show a progress card and return at once. The browser reports completion later as an event. |
| `author_scenarios` | `run_id` (integer), `instruction` (string) | Ask the scenario authoring agent (RunChat) to write scenarios into a test run. |

### System prompt rules

- One page is open at a time. To act on another page, `open_page` first, then `read_page` or use
  the snapshot it returned. Only the actions and fields in the latest snapshot exist.
- Prefer `set_field` then `call_action` over asking the user to click.
- An action marked `approve` in the catalog is approved by the user on screen. A result with
  `status: "rejected"` means the user declined: do not retry it; ask what to change.
- Use `ask_choice` for a choice among a few known options (which build, which test run). Do not ask
  in prose when a card fits.
- After `watch_job`, end the turn with one sentence saying what is running. A later user message
  starting `[event:job_finished]` or `[event:job_failed]` reports the outcome: say the outcome
  first, then continue the user's original plan if one was given.
- Never invent ids. Get them from a snapshot, a query, or the user.
- Answer in the conversation's `locale`. Keep replies short.

## 2. Orchestration: browser API

Base `/api/projects/{projectId}/agent/conversations`. Project membership is checked like
`TestRunChatService.accessible` (non-members get 404). A conversation belongs to one user; another
member's conversation is 404 too. Lists are wrapped in `items`.

| Method and path | Body | Response |
| --- | --- | --- |
| `GET /` | | `{items: Conversation[]}` newest `lastMessageAt` first |
| `POST /` | `{pageCatalog}` | `201 Conversation` |
| `GET /{id}` | | `Conversation` |
| `PATCH /{id}` | `{title}` | `Conversation` |
| `DELETE /{id}` | | `204` |
| `GET /{id}/messages` | | `{items: Message[]}` oldest first |
| `GET /{id}/stream` | | SSE, section 2.2 |
| `POST /{id}/messages` | `{text, pageCatalog?, page?}` | `202 Message` (the stored USER message) |
| `POST /{id}/tool-results` | `{callId, status, result?, error?, page?}` | `202 Message` (the stored TOOL_RESULT) |
| `POST /{id}/events` | `{kind, summary, data?}` | `202 Message` (the stored EVENT) |
| `POST /{id}/cancel` | | `200 Conversation` |

```ts
type Conversation = {
  id: number
  projectId: number
  title: string | null
  status: 'IDLE' | 'RUNNING' | 'AWAITING_TOOL' | 'ERROR'
  createdAt: string
  lastMessageAt: string
}

type Message = {
  id: number
  conversationId: number
  role: 'USER' | 'ASSISTANT' | 'TOOL_RESULT' | 'EVENT' | 'NOTICE'
  content: string
  payload: Record<string, unknown> | null
  createdAt: string
}
```

Payloads by role:

- `USER`: `{page?: PageSnapshot}` — the open page when the user sent it.
- `ASSISTANT`: `{toolCalls: {callId, tool, args}[]}` — empty array when the model only answered.
- `TOOL_RESULT`: `{callId, status, result?, error?, page?}`, `status` one of `ok`, `error`,
  `rejected`, `unavailable`, `cancelled`.
- `EVENT`: `{kind, data?}`; `content` is the browser's `summary`.
- `NOTICE`: `{kind}` with `kind` one of `error`, `step_limit`, `stopped`; `content` is a short
  sentence for the screen. Notices are never sent to the model.

### 2.1 Rules

- `POST messages` and `POST events` are accepted only in `IDLE` or `ERROR`; otherwise
  `409 {"error":"conversation_busy"}`.
- `POST tool-results` is accepted only for a `callId` that appears in the latest ASSISTANT message's
  `toolCalls` and has no TOOL_RESULT yet; otherwise `409 {"error":"not_pending"}`.
- When the last pending call of that ASSISTANT message is answered, orchestration runs the next step.
- `POST cancel`: every pending call gets a TOOL_RESULT `{status:"cancelled"}`, a NOTICE `stopped` is
  stored, status becomes `IDLE`. No model call.
- The title is the first USER text cut to 60 characters, set when that message is stored.
- `pageCatalog`, when present, replaces the conversation's stored catalog.

### 2.2 SSE

`GET /{id}/stream`, named events, JSON data:

- `message` — every stored Message, as it is stored (USER, ASSISTANT, TOOL_RESULT, EVENT, NOTICE).
- `conversation` — the Conversation whenever its status or title changes.
- A comment line every 15 s keeps proxies from closing the stream.

The stream does not replay history; the browser reads `GET messages` first, then subscribes, and
drops a `message` whose id it already has.

### 2.3 The loop

1. Set status `RUNNING`, emit `conversation`.
2. Build `messages` for agent-server from every stored message in id order:
   `USER` → `user` (content, plus `\n\n[current page]\n<snapshot JSON>` when `payload.page` is set);
   `EVENT` → `user` with content `[event:<kind>] <content>` plus `\n<data JSON>` when data is set;
   `ASSISTANT` → `assistant` with `tool_calls` from the payload;
   `TOOL_RESULT` → `tool` with content = the payload as a JSON string; `NOTICE` → skipped.
3. Count TOOL_RESULTs after the latest USER or EVENT. `tools_enabled` is `count < 30`.
4. Call `POST {artel.agent.base-url}/project-agent/step` with the model from `FeatureModelService`
   (the same model the scenario authoring agent uses) and `locale` from the user.
5. Store the ASSISTANT message, emit it. If it has tool calls, status `AWAITING_TOOL`; else `IDLE`.
   If `tools_enabled` was false, also store a NOTICE `step_limit`.
6. On a non-2xx or a timeout (120 s), store a NOTICE `error`, status `ERROR`.

The step call runs in a coroutine started after the HTTP response is sent; the request that
triggered it returns 202 at once.

### 2.4 Storage — `V117__store_project_agent_conversations.sql` (next free number at merge time)

```sql
CREATE TABLE project_agent_conversation (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    app_user_id     BIGINT NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
    title           VARCHAR(200),
    status          VARCHAR(20) NOT NULL DEFAULT 'IDLE'
                    CHECK (status IN ('IDLE', 'RUNNING', 'AWAITING_TOOL', 'ERROR')),
    page_catalog    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pac_project_user
    ON project_agent_conversation (project_id, app_user_id, last_message_at DESC);

CREATE TABLE project_agent_message (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES project_agent_conversation (id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL
                    CHECK (role IN ('USER', 'ASSISTANT', 'TOOL_RESULT', 'EVENT', 'NOTICE')),
    content         TEXT NOT NULL DEFAULT '',
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pam_conversation ON project_agent_message (conversation_id, id);
```

The same migration adds `PROJECT_AGENT` to the `llm_usage.service` CHECK constraint (drop and
recreate it with the existing values plus the new one; read the current constraint first).

A `RUNNING` conversation found at startup is set to `ERROR` with a NOTICE `error`, since its step
call died with the process.

## 3. Browser: tool execution

The browser executes every tool call of an ASSISTANT message in order, then posts one
`tool-results` per call. Result bodies:

| Tool | `status: ok` result | Other statuses |
| --- | --- | --- |
| `open_page` | `page` = snapshot after the page's bindings registered (wait up to 5 s) | `error` unknown page or bad params |
| `read_page` | `page` | |
| `set_field` | `page` | `unavailable` field not on the open page |
| `call_action` | `result` = the handler's return value, `page` | `unavailable` no such action; `error` blocked (with the reason) or the handler threw; `rejected` user declined |
| `ask_choice` | `result: {optionIds: string[]}` | `cancelled` the user stopped the conversation |
| `query` | `result` = trimmed JSON (at most 20 rows) | `error` |
| `watch_job` | `result: {watching: true}` | `error` unknown kind |
| `author_scenarios` | `result: {summary, changes}` from RunChat's `reply` | `error` |

- `set_field` and `call_action` highlight their target for 600 ms before acting.
- An `approve` action highlights its target, shows an approval card in the chat and a popover on
  the element, and waits with no timeout.
- `watch_job`: when the job ends, the browser posts `events {kind: "job_finished" | "job_failed",
  summary, data}`. If the conversation is busy at that moment, the event waits until it is `IDLE`.
- On load, a conversation in `AWAITING_TOOL` whose pending calls this tab is not executing shows a
  card: continue (execute the pending calls now) or stop (`POST cancel`).

## 4. Browser: page catalog and snapshot

```ts
type PageId =
  | 'home' | 'documents' | 'testCases' | 'testRuns' | 'qa' | 'qaHistory' | 'contentMap'
  | 'macros' | 'performance' | 'issues' | 'knowledge' | 'usage'
  | 'qaRun' | 'testRun' | 'testRunEdit'

type PageCatalog = {
  pages: {
    id: PageId
    title: string
    path: string            // relative to /projects/:projectId, e.g. 'qa-runs/:qaRunId'
    params: string[]        // names in path, plus query params such as 'build'
    description: string
    fields: { name: string; description: string }[]
    actions: { id: string; description: string; args: JsonSchema; risk: 'auto' | 'approve' }[]
  }[]
}

type PageSnapshot = {
  page: PageId | null
  params: Record<string, string>
  fields: Record<string, { value: unknown; options?: { value: unknown; label: string }[] }>
  actions: { id: string; blocked: string | null }[]
}
```

Paths: `home` → `` (the index), `documents`, `test-cases`, `test-runs`, `qa`, `qa-history`,
`content-map` (query `build`), `macros`, `performance`, `issues`, `knowledge`, `usage`,
`qa-runs/:qaRunId`, `test-runs/:runId`, `test-runs/:runId/edit`.

The catalog is static TypeScript in artel-home, sent with `POST /` and with every
`POST messages`.

## 5. Ownership

| Track | Repository | Owns |
| --- | --- | --- |
| ARTEL-1126 | agent-server | `app/api/project_agent.py`, `app/agents/project_agent/`, `app/prompts/project_agent*`, `Service` in `usage.py`, tests |
| ARTEL-1127 | orchestration | package `kr.artel.orchestration.projectagent`, migration, `llm_usage` constraint, tests |
| ARTEL-1128 | home | `src/projectAgent/registry/**`, `AgentHighlight`, provider wiring in `ProjectWorkspace` |
| ARTEL-1129 | home | `src/projectAgent/chat/**`, tool executor, queries, `AgentChatPanel` |
| ARTEL-1130 | home | page bindings in `qa/`, `contentMap/`, `testRuns/`, the catalog entries, `watch_job`, `author_scenarios` |

## 6. What the implementation changed (2026-10-20)

Recorded after ARTEL-1126 to 1130 were built and run end to end against a real model.

- 409 bodies use orchestration's common error shape `{code, message, fields}`
  (`{code: "conversation_busy"}`, `{code: "not_pending"}`), not `{error}`; `error-handling.md`
  forbids a new handler. The browser only checks the status.
- `POST cancel` while `RUNNING` cancels the step coroutine and drops a result that arrives late.
  A tool result that arrives while the conversation is not `AWAITING_TOOL` is `not_pending`.
- Orchestration settings: `artel.project-agent.step-timeout` (120 s), `heartbeat-interval` (15 s),
  `tool-call-limit` (30). Tool calls returned while `tools_enabled` is false are dropped.
- agent-server maps missing Claude / GPT keys to 502 as well, and adds one prompt rule: read a
  non-ok tool result's reason and do not repeat the same call with the same arguments.
- `JobKind` gained `author_scenarios` for the RunChat progress card.
- `query qa_history` reads `GET /api/projects/:id/qa-runs`; on a 404 (orchestration without
  that endpoint yet) it falls back to `GET /api/qa-tries` grouped by QA run.
- QA run fields and `qa.startRun` live on `src/qa/launch/{QaLaunch,LaunchPanel}.tsx`, since
  `QaTryPanel` was replaced on `develop`. `contentMap.overwriteTestCases` is registered on
  `EvidenceScanPanel` and highlights its "scan and generate" button, because the map page has no
  overwrite button of its own.
