# 2026-10-16 — Project agent that operates the project workspace

- Date: 2026-10-16
- GitHub Issue: None
- Status: Draft

## Goal

1. A project-scoped agent chat in artel-home that operates every section of the project
   workspace on the user's behalf. Inside a project it replaces the dashboard at the index
   route `/projects/:projectId`.
2. The agent drives the console through actions each page registers, not through DOM clicks
   or raw API calls. Every click and every field it fills is highlighted on the page first;
   costly actions wait for the user's approval.
3. First version covers four task types: content map generation, starting a QA run, test
   case and test run authoring, and lookup and summary (QA history, issues, usage,
   performance).

## Non-goals

- Cross-project work. One conversation belongs to one project.
- Running tools when no console tab is open. The model loop runs on the server, but every
  tool runs in the browser; closing the tab stops the agent.
- Replacing the RunChat authoring agent. Scenario writing is delegated to it as it is.
- Replacing the QA agent's own chat (`src/qa/QaChatPanel.tsx`, `sendQaMessage`). That chat
  talks to a running QA try and stays on the QA run page.
- Mobile layout. `DESIGN.md` limits mobile to notifications and evidence review.
- A shared conversation. Conversations are private to the user who started them, like
  `test_run_message`.

## Decisions made on 2026-10-16

Decided in an interview with the user. Not reopened in this plan.

### Layout

- Inside a project the agent chat replaces the dashboard section (index route
  `/projects/:projectId`). The left `ProjectNav` rail stays.
- The chat sits in the centre. When the agent or the user opens a section page, that page
  slides out from the left, between the rail and the chat, and the chat narrows to the
  right. The boundary between page and chat is draggable.
- One page is open at a time. The next step replaces it; back reopens the previous one.
- The chat can be closed. Closed, the page takes the full width (today's behaviour) and a
  button on the screen edge reopens it. Closing does not stop the agent: it keeps working,
  highlights stay visible on the page, and the reopen button shows a badge when an approval
  is needed or a task finished.
- Navigating with the rail keeps the chat's open or closed state.

### How the agent operates the UI

- Each page registers actions ("select build", "start QA run", "set form field") and the
  button or field each action is bound to. The agent calls an action; the UI highlights the
  bound element, then runs the same handler the button runs.
- Everything the agent is about to click or fill is shown on the page.
- Navigation and form input: highlight and proceed. Costly or hard-to-undo actions (start QA
  run, delete, overwrite): highlight and wait for approval; once approved the agent runs it.
- The agent reads and writes the open page's form values. The user and the agent may both
  operate the page at once; the agent reads the user's changes on its next decision.
- Simple choices (pick one build) are asked in the chat as choice cards. Settings-heavy
  tasks (a QA run) open the page with the form pre-filled.

### Execution model

- Model calls run on a server. Tools run in the browser, through the page action registry.
- If the tab closes, the agent stops. Server jobs it already started (QA run, evidence scan)
  keep running. On reopen the agent asks whether to continue.
- Long tasks show a live progress card in the chat. On completion the agent says so first,
  then suggests next steps. Chains ("make a content map, generate TCs from it, run QA") are
  supported.

### Scope

- One project. Conversations are per user, several per project, and can be reopened.
- Scenario authoring is delegated to the existing RunChat agent and its result shown.
- First version: content map generation (check game instance and build, run the evidence
  scan), QA run start, TC and test run authoring, lookup and summary.

### Answered after the first draft (2026-10-16)

- With the chat closed at the index route, `DashboardSection` shows there, as it does today.
- On `RunEditPage` the project chat folds to the edge button and RunChat keeps the right
  column. Reopening the project chat there is still possible by hand.
- The project agent's model is one server setting, the same one the authoring chat uses
  (`artel.agent.model`, `ARTEL_AGENT_MODEL`). No per-conversation model picker.
- `query` lookups run in the browser through the existing api modules. Running them in
  agent-server would need a new way to call orchestration on the user's behalf, and with
  the agent stopping when the tab closes it would buy nothing.
- Kept as proposed below: fixed tools, the 15 s reload window, conversations reachable from
  the project only. The scan panel's ignored instance `<select>` is out of scope here.

## Facts checked on 2026-10-16

Commits read: artel-home `9e9d8cc`, artel-orchestration-server `a0643c2`, artel-agent-server
`cd59fd9`.

### Routes and the workspace layout (artel-home)

- `src/App.tsx`: `ProjectWorkspaceRoute` is the layout for `/projects/:projectId` and its 15
  sections; `DashboardSection` is the index route. The layout (`ProjectWorkspace.tsx`) owns
  every read (`useProject`, `useWorkspaceExtras`) and hands them down through
  `WorkspaceContext`, so moving between sections triggers no request.
- **Deep pages are outside that layout.** `/projects/:projectId/qa-runs/:qaRunId`,
  `.../qa-runs/:qaRunId/performance`, `.../test-runs/:runId`, `.../test-runs/:runId/edit`,
  `.../test-scenarios/:testScenarioId` and `.../instances/:instanceId` are siblings of
  `ProjectWorkspaceRoute` under `AppShell`, without the rail. A chat mounted in the workspace
  layout would unmount every time the agent opens a QA run.
- `src/projects/workspace/sections.ts` is the single source of section paths
  (`WORKSPACE_SECTIONS`, `sectionHref`, `sectionIdFromPath`).
- A resizable split already exists: `src/design-system/primitives/SplitHandle.tsx`
  (pointer and keyboard, `role="separator"`), used with `src/testScenarios/useChatWidth.ts`
  (default 360px, 300–720px, stored in `localStorage` under `artel.studio.chatWidth`) on
  `RunEditPage.tsx` and `TestScenarioPage.tsx`.
- Rail collapse is stored in `localStorage` (`artel.projectNavCollapsed`,
  `navCollapse.ts`).
- Dependencies are `react`, `react-dom`, `react-router-dom` only. Tests run on `node:test`
  with no DOM renderer, so registry logic must be testable as plain TypeScript.

### QA run start form

- The form is not on `QaRunPage.tsx`. `QaRunPage` shows one run (polls
  `GET /api/qa-runs/{id}` every 3 s with backoff to 30 s). The start form is `QaTryPanel`
  (`src/qa/QaTryPanel.tsx`), rendered by `QaSection` at `/projects/:projectId/qa`.
- `QaTryPanel` keeps its fields in local `useState`: `instanceId`, `runId` (the test run),
  `selectedModelKey`, `reasoningEnabled`, `reasoningValue`. Nothing outside the component
  can read or set them today.
- It calls `createQaRun` → `POST /api/qa-runs`
  `{testRunId, gameInstanceId, model, keySource, reasoning, force}`. A `409 qa_run_active`
  opens `TakeOverQaRunDialog`; `force` is only ever sent after the operator answers it
  (`qaApi.ts` says nothing may infer that intent). The agent must never send `force`.
- On success it navigates to `/projects/:projectId/qa-runs/:id`.

### Content map and evidence scan

- `ContentMapSection` keeps the selected build in the URL (`?build=`), with a `<select>`.
- `EvidenceScanPanel` keeps an instance `<select>` in local state, but
  **the server ignores the instance.** `requestEvidenceScan` sends none:
  `POST /api/projects/{projectId}/game-builds/{gameBuildId}/content-map/scan` and the server
  picks a live instance that last registered this build. 202 means queued, not done; 409
  means no game attached (`ProjectContentMapController.startScan`).
- `?generateTestCases=true&carryOver=` on the same call makes the server also generate TCs
  once the scan documents are read (ARTEL-1041); the result arrives as `lastScan.testCases`.
  A build that already has TCs answers 409 before the scan is sent.
- Separate generation: `POST .../content-map/test-cases?carryOver=&overwrite=`
  (`generateContentMapTestCases.ts`, `ContentMapTestCaseController`). `overwrite=true`
  replaces the map TCs of a build that already has them — an approval action.
- Completion is watched on `GET .../content-map/events` (SSE, `useContentMapEvents.ts`).

### Other endpoints the first version touches

| Task | Endpoint | Client module |
| --- | --- | --- |
| Create a test run | `POST /api/projects/{projectId}/test-runs` `{name, description, gameBuildId, unversioned, folderId}` | `testRuns/testRunApi.ts` |
| Create a TC by hand | `POST /api/projects/{projectId}/test-cases` | `testCases/` |
| QA history | `GET /api/qa-tries`, `GET /api/qa-runs/{id}` | `qa/qaApi.ts` |
| QA models | `GET /api/qa-models` | `qa/qaApi.ts` |
| Issues | `GET /api/projects/{projectId}/issues`, `/api/qa-tries/{id}/issues` | `issues/` |
| Usage | `GET /api/llm-usage/stats` | `usage/` |
| Performance | `GET .../game-builds/{buildId}/performance`, `/api/qa-runs/{id}/performance` | `performance/` |

### RunChat, the authoring agent

- Client: `src/testRuns/RunChat.tsx` (873 lines), `runChatApi.ts`, `useRunChatSession.ts`.
  Mounted on `RunEditPage.tsx` (right column behind a `SplitHandle`) and
  `TestScenarioPage.tsx`. It needs a `runId`: a conversation belongs to one test run.
- Endpoints (`TestRunController`, `/api/projects/{projectId}/test-runs/{runId}`):
  `GET chat/messages`, `GET chat/stream` (SSE, `EventSource` with `withCredentials` to the
  orchestration origin), `POST chat/message {message, autoApply, answer}`,
  `POST chat/cancel` (one turn), `POST chat/close` (session), `POST scenarios/commit`.
- Stream frames (`parseRunStreamEvent`): `result` (message, `scenarios[]` proposals,
  `reply {result, detail, changes[]}`, `refs`), `error`, `progress` (one of 15
  `AUTHORING_STAGES`, optional `done`/`total`), `notice`, `question` (all open questions in
  `questions[]`), `applied`.
- Questions: options are phrased as what the user would type; the answer goes back with
  the next `chat/message` as `{question_id, option_ids, text}`. Answered questions are
  recorded as `kind=answered` payloads so a reload does not revive their buttons.
- Proposal and commit: `autoApply` (stored in `localStorage` `artel.run-chat.autoApply`,
  default off) decides whether the server saves the scenarios itself or the client shows
  proposal cards and saves the picked ones with `scenarios/commit`, which goes through the
  same `ScenarioReconcileService`.
- Server side: `TestRunChatService` → `TestScenarioAgentService` (1,867 lines). Session key
  is `userId:runId`. It opens `POST {agent}/internal/sessions`, then a WebSocket
  `{agent-ws}/internal/sessions/{id}`; follow-up turns are `{type:"turn"}` frames. While a
  turn runs, the agent sends request frames (`test_case_search`, uncovered cases, find path,
  explain case, submit scenario) and orchestration answers each on the same socket.
  `TestScenarioStreamManager` relays to the browser with an in-memory `MutableSharedFlow`
  per session key. Messages persist in `test_run_message` (V22, plus a `payload` column).
- Agent side: `app/api/sessions.py`, `app/sessions/channel.py` (`ScenarioChannel` holds a
  future per request frame so a tool can `await` an answer that arrives as a separate
  inbound frame; 20 s timeout returned as a value), `app/sessions/redis_store.py` for
  session records, `app/agents/scenario/agent.py` built on `langchain.agents.create_agent`
  with `ModelCallLimitMiddleware` and `ToolCallLimitMiddleware`.

### Agent-server and models

- agent-server has no public surface (`project.md`). Every business route is under
  `/internal` and only orchestration calls it. The browser can never reach it directly.
- Chat agents are LangChain `create_agent` loops. `app/llm/chat_model.py` `build_chat_model`
  routes by model id prefix: OpenRouter slug (`ChatOpenAI`), `bedrock/`
  (`ChatBedrockConverse`), `claude/` (`ClaudeApiChat` on `ChatAnthropic`), `gpt/` (OpenAI
  API, user key only). User keys are bound per session (`app/llm/credentials.py`).
- The model catalog is in the orchestration database (`llm_model`, V109). agent-server reads
  `GET /internal/llm-models` and caches it (`app/llm/catalog.py`). `EnabledLLMModel` refuses a
  model an administrator turned off. `DEFAULT_MODEL` is `openai/gpt-6-luna`.
- The authoring chat does not let the user pick a model: orchestration sends
  `artel.agent.model` (`ARTEL_AGENT_MODEL`), or nothing so agent-server uses its default.
  The QA run lets the user pick from `GET /api/qa-models` (`QaModelPicker`,
  `offeredQaModels`, with `keySource`).
- `llm_usage.service` has a CHECK constraint with five values (`QA_RUN`, `SCENARIO`,
  `KNOWLEDGE_QUERY`, `GAME_CONTEXT`, `EMBEDDING`; V24) mirrored by `Service` in
  `app/llm/usage.py`. A new agent needs a new value in both.
- The newest orchestration migration on `develop` is `V111`.

## Architecture

### Overview

```text
browser (artel-home)                orchestration                     agent-server
──────────────────────              ─────────────────────────────     ─────────────────────────
ProjectAgentChat ──POST message──▶  ProjectAgentController     ──WS turn──▶  project_agent session
                 ◀──SSE stream───   ProjectAgentService          ◀─tool_call─  create_agent loop
ActionRegistry   ◀─tool_call(SSE)─  (relay + persist)                         ProjectAgentChannel
  highlight, approve, run           project_agent_message                     (future per call)
                 ──POST tool-result─▶                            ──tool_result──▶
```

The model loop runs in agent-server, which already owns every LLM backend, key binding, and
usage booking. orchestration owns authentication, project access, persistence, and the
browser-facing SSE, as it does for RunChat. The browser runs every tool.

### Server chat endpoint

orchestration, new package `kr.artel.orchestration.projectagent`, all under
`/api/projects/{projectId}/agent/conversations`, project membership checked through
`ProjectAccessService` (non-members get 404, as `TestRunChatService.accessible` does):

| Method and path | Purpose |
| --- | --- |
| `GET /` | the user's conversations in this project, newest first |
| `POST /` | start a conversation; the model comes from the server setting |
| `PATCH /{id}` `{title}` · `DELETE /{id}` | rename, delete |
| `GET /{id}/messages` | the thread, for reopen |
| `GET /{id}/stream` | SSE to the browser |
| `POST /{id}/messages` `{text, answer?, page}` | user turn; `page` is the open page's snapshot |
| `POST /{id}/tool-results` `{callId, status, result, page}` | a browser tool finished |
| `POST /{id}/tool-progress` `{callId, state}` | `highlighting`, `awaiting_approval`; keeps a waiting call alive |
| `POST /{id}/events` `{kind, ...}` | `job_finished`, `job_failed`, `resume`; starts a turn |
| `POST /{id}/cancel` | end the running turn |

agent-server, new routes under `/internal`: `POST /internal/project-agent/sessions` and WS
`/internal/project-agent/sessions/{session_id}`, in a new `app/api/project_agent.py` and
`app/agents/project_agent/`. The WS dispatch copies `app/api/sessions.py` (one task per
turn, a persistent receive, a write lock).

### Client-side tool protocol

1. The model emits a tool call. The tool function in agent-server sends
   `{type:"tool_call", call_id, tool, args}` on the WS and awaits a future in
   `ProjectAgentChannel` (the `ScenarioChannel` pattern).
2. orchestration stores a `TOOL_CALL` message and emits SSE event `tool_call`
   `{callId, tool, args}`.
3. The browser looks the tool up in the action registry. The registry, not the model,
   decides the risk: `auto` actions highlight the bound element for 600 ms and run;
   `approve` actions highlight it, post `tool-progress awaiting_approval`, show an approval
   card in the chat and a popover on the element, and wait.
4. The browser posts `tool-results` with `status` `ok`, `error`, `rejected` (user said no),
   or `unavailable` (no such action on the open page after navigation), plus a fresh `page`
   snapshot. orchestration checks that `callId` is the conversation's pending call for this
   user, stores a `TOOL_RESULT` message, and sends `{type:"tool_result"}` on the WS.
5. The future resolves and the loop continues.

Timeouts: a call with no progress for 30 s is answered `error: browser_timeout`. While
`awaiting_approval`, there is no timeout; the call waits for the user. When the SSE
subscription for a conversation ends (tab closed), orchestration waits 15 s for a
re-subscribe (a reload), then answers the pending call `cancelled`, sends `cancel` on the
WS, and marks the conversation `INTERRUPTED`.

Why browser-defined tools are safe: each action calls the same API a button does, with the
user's own cookie. A forged tool result can only change what the model reads, never what
the server permits.

### Tool set seen by the model

Fixed tools (defined in agent-server):

- `open_page(page, params)` — navigate; the page slides in.
- `read_page()` — current page id, registered actions, field values and their options.
- `call_action(action, args)` — run one action of the open page.
- `ask_choice(question, options)` — a choice card in the chat; the answer comes back as the
  tool result, so no extra turn is spent.
- `query(kind, args)` — read-only lookups (QA history, issues, usage, performance). These run
  in the browser through the existing api modules, without a highlight, because they change
  nothing on screen.
- `watch_job(kind, id)` — add a progress card; returns at once.
- `author_scenarios(runId, instruction)` — delegate to RunChat (below).

The page catalog (which pages exist, their params, and each page's actions with JSON
schemas and risk) is a static TypeScript module in artel-home, sent to orchestration when a
conversation's session opens and forwarded in the system prompt. Fixed tools keep the tool
list stable across pages, so the prompt cache survives navigation. One typed tool per action
was considered and dropped: it would give the model argument schemas directly, but the tool
list would change on every page and break the cache.

### Page action registry (React)

```ts
// src/projectAgent/registry/types.ts
export type ActionRisk = 'auto' | 'approve'

export type PageId =
  | 'documents' | 'testCases' | 'testRuns' | 'qa' | 'qaHistory' | 'contentMap'
  | 'macros' | 'performance' | 'issues' | 'knowledge' | 'usage'
  | 'qaRun' | 'testRun' | 'testRunEdit'

/** Static, importable without mounting the page. Sent to the model. */
export type ActionSpec<Args> = {
  id: string                       // 'qa.startRun'
  page: PageId
  description: string
  args: JsonSchema                 // validated before the handler runs
  risk: ActionRisk
  /** What the highlight label and the approval card say. */
  summarize: (args: Args) => string
}

/** Bound at mount by the component that owns the button. */
export type ActionBinding<Args, Result> = {
  spec: ActionSpec<Args>
  /** The element to highlight. Null while it is not rendered (e.g. a closed panel). */
  target: () => HTMLElement | null
  /** Why the action cannot run now, in the words the button's disabled hint uses. */
  blocked: () => string | null
  /** The same function the button's onClick calls. */
  run: (args: Args) => Promise<Result>
}

export type FieldBinding<Value> = {
  name: string                     // 'qa.testRunId'
  page: PageId
  target: () => HTMLElement | null
  read: () => Value
  options?: () => { value: Value; label: string }[]
  write: (value: Value) => void    // the field's own setter
}

export type PageSnapshot = {
  page: PageId | null
  params: Record<string, string>
  fields: Record<string, { value: unknown; options?: { value: unknown; label: string }[] }>
  actions: { id: string; blocked: string | null }[]
}

// Hooks a page calls:
export function useAgentAction<A, R>(binding: ActionBinding<A, R>): void
export function useAgentField<V>(binding: FieldBinding<V>): void
```

- `ActionRegistryProvider` sits in `ProjectWorkspace`. Hooks register on mount and
  unregister on unmount, so the registry always holds exactly the open page's bindings.
- Writing a field goes through `useAgentField.write`, which is the field's own setter, so
  `QaTryPanel`'s `useState` stays where it is. `set_field` is an action every page gets for
  free from its field bindings.
- The highlight is one overlay component (`AgentHighlight`) positioned from
  `target().getBoundingClientRect()`, a coral ring (the agent-action role in `DESIGN.md`) with
  a label from `summarize`. No shadow, `prefers-reduced-motion` turns the transition off,
  and the label is mirrored to an `aria-live="polite"` region.
- Simultaneous editing: the registry never caches field values. Every tool result carries
  a fresh `PageSnapshot`, so a change the user made between calls is in the next one the
  model reads.

### Reaching an action on a page that is not open

`call_action` only addresses the open page. The model calls `open_page` first; the browser
runs `navigate(sectionHref(...))`, then waits up to 5 s for the page's bindings to register
and answers with the new `PageSnapshot`. The URL stays the source of truth for which page is
open, so "back reopens the previous page" is the router's history and needs no stack of its
own. Closing the page navigates to the index route.

Deep pages (`qa-runs/:id`, `test-runs/:runId`, `test-runs/:runId/edit`) must render inside
the workspace layout for this to work, so Phase 1 nests them under `ProjectWorkspaceRoute`
with their paths unchanged.

### Delegating scenario authoring to RunChat

`author_scenarios(runId, instruction)` runs in the browser: it drives a
`useRunChatSession(projectId, runId)` instance owned by the project chat, sends the
instruction with `autoApply=false`, renders RunChat's `progress` frames in a progress card,
shows RunChat's `question` frames as choice cards in the project chat (answers go back
through RunChat's own `answer` field), and shows its proposal cards for the user to commit
with `scenarios/commit`. The tool result is RunChat's `reply.result` and `changes[]`. No
server change in the RunChat path.

### Long tasks and chains

`watch_job` returns immediately; the turn ends. The progress card subscribes from the
browser with the hooks that already exist (`useContentMapEvents`, `getQaRun` polling,
`useQaTry`). When a watched job ends, the browser posts `events {kind:"job_finished"}`, which
starts a turn whose first sentence announces the result and then proposes or continues the
next step. A chain is the model's plan carried across these turns; nothing holds a tool call
open for the 10 to 40 minutes a QA run takes.

On reopen, a conversation in `INTERRUPTED` shows a server-written notice with two options,
continue or stop. Continue posts `events {kind:"resume"}` with the current state of every
job the conversation watched.

### Conversation storage (orchestration, `V112` or the next free number)

```sql
CREATE TABLE project_agent_conversation (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    app_user_id     BIGINT NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
    title           VARCHAR(200),
    model           VARCHAR(120),
    key_source      VARCHAR(20) NOT NULL DEFAULT 'platform',
    status          VARCHAR(20) NOT NULL DEFAULT 'IDLE'
                    CHECK (status IN ('IDLE', 'RUNNING', 'INTERRUPTED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pac_project_user ON project_agent_conversation (project_id, app_user_id, last_message_at DESC);

CREATE TABLE project_agent_message (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES project_agent_conversation (id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL
                    CHECK (role IN ('USER', 'ASSISTANT', 'TOOL_CALL', 'TOOL_RESULT', 'EVENT', 'NOTICE')),
    content         TEXT NOT NULL DEFAULT '',
    -- tool_call: {callId, tool, args}; tool_result: {callId, status, result};
    -- event: {kind, jobs}; card: {kind:'choice'|'progress'|'approval', ...}
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pam_conversation ON project_agent_message (conversation_id, id);
```

The same migration adds `PROJECT_AGENT` to the `llm_usage.service` CHECK constraint;
`reference_id` is the conversation id. agent-server adds it to `Service` in `app/llm/usage.py`.

The orchestration database is the source of truth for the thread. When agent-server opens a
session it receives the stored messages and rebuilds the LangChain history, so a session
lost to a restart or a Redis TTL is reopened from the database, not lost.

### Layout shell

- `ProjectWorkspace` renders `rail | page slot | SplitHandle | chat`. With the chat open, the
  index route renders an empty page slot, so the chat takes the full width beside the rail.
  With the chat closed, the index route renders `DashboardSection`.
- On `RunEditPage` the chat folds to the edge button on entry, so RunChat keeps the right
  column. Leaving the page restores the stored open state.
- Chat open state and width are stored in `localStorage` (`artel.projectAgent.open`,
  `artel.projectAgent.width`), so the rail and reloads keep them. Width reuses the
  `useChatWidth` clamping with a 640px page minimum (the `DESIGN.md` viewport minimum).
- Closed: the page slot takes the full width, and a 32 × 32px button on the right edge
  reopens the chat. It carries a badge for `awaiting_approval` and for an unread
  `job_finished`.
- The page slides in over 240 ms (`motion slow`), off under `prefers-reduced-motion`.
- At 1024px the rail collapses to 48px: 48 + 640 + 6 + 300 = 994px.

## Approach (Checklist)

PR-sized phases. Inside each phase the tracks have disjoint write scopes.

### Phase 1 — layout shell (artel-home)

- [ ] Nest the deep pages (`qa-runs/:qaRunId`, `qa-runs/:qaRunId/performance`,
  `test-runs/:runId`, `test-runs/:runId/edit`, `test-scenarios/:testScenarioId`,
  `instances/:instanceId`) under `ProjectWorkspaceRoute` with paths unchanged. Check each
  page still renders at 1024px beside the rail.
- [ ] `src/projectAgent/AgentDock.tsx`: page slot, `SplitHandle`, chat column, closed state,
  edge reopen button with a badge slot. Chat content is a placeholder in this PR.
- [ ] Index route renders the empty page slot while the chat is open, and
  `DashboardSection` while it is closed.
- [ ] `RunEditPage` folds the chat to the edge button on entry.
- [ ] i18n strings in `src/i18n/messages/projectAgent.ts` (`en`, `ko`).
- [ ] `node:test` for the width clamping and the open-state storage.

### Phase 2 — action registry and highlight (artel-home)

- [ ] `src/projectAgent/registry/`: types above, `ActionRegistryProvider`, `useAgentAction`,
  `useAgentField`, snapshot builder, JSON schema check for args.
- [ ] `AgentHighlight` overlay and the approval popover, `aria-live` mirror.
- [ ] Static page catalog `src/projectAgent/catalog.ts`.
- [ ] A dev-only panel (behind `import.meta.env.DEV`) that calls actions by hand, so the
  registry is checked before any server exists.
- [ ] `node:test` for registration order, unregister on unmount, snapshot content, args
  validation, and the `approve` gate.

### Phase 3 — chat protocol end to end, with lookup and summary as the first task

Three tracks in parallel, one per repository.

- [ ] orchestration: migration (tables, `PROJECT_AGENT`), `projectagent` controller,
  service, SSE relay (copy `TestScenarioStreamManager`), WS client to agent-server,
  pending-call check on `tool-results`, the 30 s and 15 s timeouts, integration tests.
- [ ] agent-server: `app/api/project_agent.py`, `app/agents/project_agent/` (`create_agent`,
  fixed tools, `ProjectAgentChannel`, call and model limits as in the scenario agent, prompt
  under `app/prompts/`), `PROJECT_AGENT` in `usage.py`, pytest with a fake channel.
- [ ] artel-home: `ProjectAgentChat` (thread, composer, conversation list),
  `useProjectAgentSession` (SSE, tool dispatch to the registry),
  `query` handlers for QA history, issues, usage and performance.

### Phase 4 — content map generation

- [ ] Bind `ContentMapSection` (build `<select>` as a field), `EvidenceScanPanel` (scan and
  scan-with-TCs as actions, `blocked` from `describeBlock`).
- [ ] Bind `generateContentMapTestCases` with `overwrite=true` as an `approve` action.
- [ ] `watch_job` for `content_map` on `useContentMapEvents`.

### Phase 5 — QA run start

- [ ] Bind `QaTryPanel` fields (`instanceId`, `runId`, model, reasoning) and
  `qa.startRun` (`approve`). The agent pre-fills; the user approves on the page.
- [ ] `qa_run_active` still opens `TakeOverQaRunDialog` for the user; the tool result reports
  it. No action sends `force`.
- [ ] `watch_job` for `qa_run` on `getQaRun` polling.

### Phase 6 — TC and test run authoring

- [ ] Bind test run creation (`NewRunDialog`) and TC creation.
- [ ] `author_scenarios` driving `useRunChatSession`; RunChat questions and proposal cards
  inside the project chat.

### Phase 7 — chains and resume

- [ ] `job_finished` and `resume` events, the `INTERRUPTED` notice, the reopen button badge.
- [ ] A three-step chain checked by hand: content map → TCs → QA run.

## Validation

- **Commands to run:**
  - artel-home: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` (set `PATH`
    directly; the nvm shim recurses in the agent shell).
  - orchestration: the `projectagent` tests with `-Dkotlin.compiler.daemon=false`.
  - agent-server: `LANGSMITH_TRACING=false python -m pytest tests/test_project_agent*.py`.
- **Expected output:** all pass. Then against a local stack (`qa-run-local` skill, session
  from the `artel-jwt` skill), screen captures at 1024px and 1440px of:
  - Phase 1: chat only at the index route; a section open beside it; resized; chat closed
    with the edge button; a QA run page with the rail.
  - Phase 2: a highlight on the QA start button and the approval popover.
  - Phases 4–6: each task from one sentence in the chat to its finished state, including a
    rejected approval and a user editing a field while the agent works.
  - Phase 7: tab closed during a QA run, reopened, continue chosen, completion announced.

## Risks & Rollback

- **Risks:**
  - Single orchestration instance assumed. Sessions and SSE flows live in memory, as RunChat's
    do (`TestScenarioAgentService.sessions`, `TestScenarioStreamManager.streams`). A second
    replica would route a `tool-results` POST to an instance without the WS.
  - Nesting the deep pages under the workspace layout changes their width; `RunEditPage`
    already has its own chat column and `QaRunPage` a stream viewport.
  - A page that renders its button conditionally (`target()` null) cannot be highlighted.
    The action must report `blocked` instead of running unseen.
  - Model cost: every turn re-reads the page catalog; keep it in the cached prefix.
  - Migration number collision with other open branches (`V112`).
- **Rollback steps:** each phase is its own pull request. Phase 1 can be reverted to bring
  `DashboardSection` back at the index route; later phases add files and one migration whose
  tables nothing else reads.

## Open Questions

None. The eight questions of the first draft were answered on 2026-10-16; see "Answered
after the first draft".
