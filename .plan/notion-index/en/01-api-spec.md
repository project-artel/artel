> 168 endpoints. **The single source of truth for API contracts and implementation status.** Read this before reading the code.
> Database `3990bce5-474c-80e8-bb41-d52ee7233141` · data source `c080bce5-474c-8264-b176-0706704849ee`
> Surveyed 2026-08-26.

## At a glance

| Axis | Distribution |
|---|---|
| Server | Orchestrator 140 · Agent Server 26 · Artel SDK 1 |
| Type | HTTP 157 · Websocket 8 |
| 구현 현황 | 구현 완료 118 · 미구현 34 · 대체됨 9 (+2) · 구현 중 4 |
| 인증 | Bearer JWT 97 · 없음 16 · internal variants 11 · API Key 3 · blank 40 |

## By category

| Category | Rows | 구현 완료 | 미구현 | Other |
|---|---|---|---|---|
| QA | 19 | 15 | 4 | |
| Agent | 15 | 15 | | |
| SDK | 15 | 14 | 1 | |
| deprecated | 15 | 2 | 8 | 대체됨 5 |
| Auth | 13 | 10 | 1 | 대체됨 2 |
| TestRun | 13 | 13 | | |
| Game Build | 12 | 2 | 5 | 대체됨 3 · 구현 중 2 |
| TestScenario | 12 | 12 | | |
| Tool | 11 | | 11 | **none implemented** |
| Project | 10 | 10 | | |
| TestCase | 9 | 9 | | |
| Document | 7 | 7 | | |
| Issue | 7 | 3 | 3 | 대체됨 1 |
| Knowledge | 5 | 5 | | |
| 개발 | 2 | | | 구현 중 2 |
| LLMUsage | 1 | 1 | | |

Three things to read out of that table. `Tool` has eleven endpoints and not one
of them is built — designed, never started. `Game Build` has twelve rows but only
two that actually run; the rest split across 미구현 and 대체됨, so check which row
is live before touching that area. The two `개발` rows point at the same URLs as
the `SDK` performance endpoints — they are part of the duplication below.

## ⚠️ Duplicate rows — know this before you read

**18 pairs, 37 rows in total, share the same (Server, Method, URL).** Old
planning-era rows and the Hermes rewrite both survive. Telling them apart:

- **Live row**: `명세 변경 = Hermes 추가`, and `명세 버전` names a real commit
  (`artel-orchestration-server@develop (2bba4fe)`).
- **Stale row**: `명세 버전` is `v1` or blank, and `명세 변경` is blank or
  `Hermes 보완`.

| Server | Method | URL |
|---|---|---|
| Orchestrator | GET | `/api/auth/me` |
| Orchestrator | POST | `/api/auth/refresh` |
| Orchestrator | GET · POST | `/api/projects` |
| Orchestrator | GET · PATCH · DELETE | `/api/projects/{projectId}` |
| Orchestrator | GET · POST | `/api/projects/{projectId}/documents` |
| Orchestrator | POST | `/api/projects/{projectId}/documents/upload-url` |
| Orchestrator | GET | `/api/projects/{projectId}/game-builds` |
| Orchestrator | GET | `/api/projects/{projectId}/game-builds/{gameBuildId}/performance` |
| Orchestrator | GET | `/api/projects/{projectId}/issues` |
| Orchestrator | GET | `/api/projects/{projectId}/test-scenario` |
| Orchestrator | GET | `/api/projects/{projectId}/test-scenario/{testScenarioId}` |
| Orchestrator | GET | `/api/qa-runs/{runId}/performance` |
| Agent Server | GET | `/health` (3 rows) |
| Agent Server | (WS) | `/internal/qa-sessions/{session_id}` |

Not cleaned up yet. Deciding which row survives is a human call.

## Reading the properties

| Property | Meaning |
|---|---|
| `Server` | Orchestrator / Agent Server / Artel SDK |
| `Type` · `Request Method` · `Url` | The HTTP contract. WebSocket rows carry `해당 없음` as the method |
| `Category` | Domain — the 17 above |
| `인증` | `Bearer JWT` · `없음` · `API Key` · `내부 전용` · `내부(permitAll)` · `내부(Orchestration→Agent)` |
| `Input type` · `Input` | Written as `[header]` / `[path]` / `[query]` / `[body]` lines |
| `응답` | `[200] TypeName { … }`. Long rows carry the full JSON shape and the design rationale |
| `오류 응답` | `401 미인증 / 404 빌드 없음 / 400 …` |
| `구현 현황` | **The status of record.** Not `Artel 기능 명세서` |
| `근거` | Code path with line number, Jira key, or PR number. Must be verifiable |
| `명세 버전` | Which commit the row was written against |
| `명세 변경` | `Hermes 추가` (new) / `Hermes 보완` (amended) / `기존 명세` |

## Writing a row

Duplicate `🧩 API 명세 작성 템플릿` (`3a40bce5-474c-8197-b257-ca2af06c36d5`) and
switch `명세 구분` to `API 명세`. The body follows `## 1. 기본 계약` →
`## 2. 요청 계약` → `## 3. 성공 응답`.

In practice the properties are the contract and the body is elaboration — plenty
of rows fill the properties and leave the body empty. `근거` is the exception.
Fill it every time. A spec the reader cannot verify is worse than no spec.

## Common queries

```bash
# One domain
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query \
  -d '{"page_size":50,"filter":{"property":"Category","select":{"equals":"TestScenario"}}}'

# Unimplemented endpoints on one server
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query \
  -d '{"page_size":100,"filter":{"and":[
        {"property":"Server","select":{"equals":"Agent Server"}},
        {"property":"구현 현황","select":{"equals":"미구현"}}]}}'
```

When filtering `구현 현황` for `대체됨`, `or` it with the quoted `"대체됨"`
option too. Two rows sit under that one.
