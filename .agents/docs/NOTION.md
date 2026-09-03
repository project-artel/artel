# Notion Workspace Manual (for agents)

How to read from and write to the ARTEL Notion workspace. Written for an agent
that has shell access to this repository.

Surveyed 2026-08-26 against the live workspace (541 objects, 13 databases).
Row counts and staleness notes reflect that date.

---

## 1. Access

Credentials live in `.jira.env`-style sibling file `.notion.env` (gitignored):

```bash
set -a && . ./.notion.env && set +a
```

That exports `NOTION_API_TOKEN` and `NOTION_WORKSPACE_ID`. The `ntn` CLI
(`~/.local/bin/ntn`, version 0.22.1) picks up `NOTION_API_TOKEN` automatically.
Never run `ntn login`; never print the token.

The integration is named `ArtelNotionToken` (bot user id
`3a00bce5-474c-815b-b7f8-0027b6b24e3f`). A page or database that has not been
connected to the integration returns `404 object_not_found` even though it
exists. That is a sharing problem, not a wrong id.

Repository tooling note: `jq` is **not installed** on this machine. Use
`python3` (3.14) for JSON handling, or `ntn`'s own formatting.

---

## 2. Two API surfaces

Notion has two live API generations, and this workspace is affected by both.

| | Old (`Notion-Version: 2022-06-28`) | New (`ntn` default, `2025-09-03`) |
|---|---|---|
| Query a table | `POST /v1/databases/{database_id}/query` | `POST /v1/data_sources/{data_source_id}/query` |
| Read schema | `GET /v1/databases/{database_id}` | `GET /v1/data_sources/{data_source_id}` |
| Create a row | `parent: {database_id}` | `parent: {data_source_id}` |

`ntn api ...` speaks the new surface. Raw `curl` with
`Notion-Version: 2022-06-28` speaks the old one. Both work today. Prefer `ntn`
plus the data source id — the old surface already fails on some objects in this
workspace (`"does not contain any data sources accessible by this API bot"`).

Both ids per database are listed in section 4.

---

## 3. Workspace map

Root page **Artel** — `36d0bce5-474c-8021-8b4a-c39f9ced694d` — is the only
workspace-level page. Everything else hangs off it.

Start workspace discovery at **🧭 Artel Index** —
`3c80bce5-474c-8125-89f1-dcbef41b2726`. Read it first when you need to
understand the workspace structure or find relevant project context. It routes
to the API Spec, Documents, Progress Log, and Personal Notes area indexes and
records the current database map and known traps.

```
Artel  (team base rules in the page body)
├─ 🧭 Artel Index              page  3c80bce5-474c-8125-89f1-dcbef41b2726
├─ 회의록                     page  36d0bce5-474c-804b-b9b1-faace28cf32b
│   └─ 🗄 회의록               db    3850bce5-474c-801e-8dc7-cbc3ba8bb142
├─ 🗄 문서 (linked view)       block 3ab0bce5-474c-8064-a5a0-c774320390ed
├─ 개인 페이지                 page  37c0bce5-474c-8000-bf66-ccb6b8901cbb
│   ├─ 🗄 개인 정리용 페이지     db    37c0bce5-474c-80d4-b4fc-efecef3832dc
│   └─ GC                    page  3ac0bce5-474c-8062-92da-e811c28bdf8c   (demo game planning)
├─ 멘토링                     page  3900bce5-474c-808f-be71-c0628c7e0993
│   └─ 🗄 질문                 db    3900bce5-474c-80d6-bd6c-dd65be002fd2
├─ 개발 문서                   page  3b30bce5-474c-8083-a711-fa953d537064
│   ├─ 🗄 (linked view)        block 3b30bce5-474c-801f-9cc7-d4c3014889a1
│   └─ content_map — 씬·화면·기능 스키마 설계   page 3c00bce5-474c-8163-9b3f-f4e28eae8a59
├─ 개발 스탠드 업               page  39f0bce5-474c-803f-91c0-db32056d428e
│   └─ 🗄 개발 스탠드 업         db    39f0bce5-474c-8061-bdd0-fe9c99dfe556
├─ 팀원 정보                   page  36f0bce5-474c-8099-a4dc-f994d4a4099a   (contains personal data)
├─ 🗄 (untitled inline view)   block 38f0bce5-474c-802d-8507-d50d063fe31f
├─ 이동 경로 (삭제 X)           page  3ab0bce5-474c-80f0-8d09-d23b3e3bb253   (redirect stub, do not delete)
│   └─ 문서                    page  36e0bce5-474c-80ce-8ad3-fbb457c16d90
│       ├─ 🗄 문서              db    36e0bce5-474c-80de-9026-d310fa0884a5
│       │   ├─ (row) API 명세         → 🗄 API 명세서        db 3990bce5-474c-80e8-bb41-d52ee7233141
│       │   └─ (row) Artel 기능 명세서 → 🗄 Artel 기능 명세서  db 3990bce5-474c-8083-b2ed-f7010b2db82f
│       └─ 🗄 설계 문서          db    3990bce5-474c-804b-8087-d2a5005474c6   (NOT shared with the integration)
└─ 중간 발표 대비 3주 스프린트 계획 (8/18~9/7)   page 3c00bce5-474c-8176-afb0-f58a57c3798a
```

The important structural fact: **the two most valuable databases (`API 명세서`,
`Artel 기능 명세서`) are nested three levels deep, inside rows of the `문서`
database, under a page literally named "이동 경로 (삭제 X)"**. They are not
reachable by browsing down from the root in an obvious way. Use the ids below.

---

## 4. Database reference

### 4.1 `API 명세서` — the API contract of record

- database id: `3990bce5-474c-80e8-bb41-d52ee7233141`
- data source id: `c080bce5-474c-8264-b176-0706704849ee`
- 168 rows. **This is the highest-value database in the workspace.**
- Location: row `API 명세` of the `문서` database.

One row = one endpoint (HTTP or WebSocket message). Properties:

| Property | Type | Notes |
|---|---|---|
| `Name` | title | Korean endpoint name, e.g. `씬 명세 조회 (Content Map)` |
| `Server` | select | `Orchestrator` (140) / `Agent Server` (26) / `Artel SDK` (1) |
| `Type` | select | `HTTP` (157) / `Websocket` (8) |
| `Request Method` | select | `GET` `POST` `PATCH` `DELETE` `PUT` `WebSocket` `해당 없음` |
| `Url` | rich_text | path template, e.g. `/api/projects/{projectId}/game-builds/{gameBuildId}/content-map` |
| `Category` | select | `Auth` `Project` `Game Build` `Document` `TestScenario` `TestCase` `TestRun` `QA` `Issue` `SDK` `Agent` `Tool` `Knowledge` `ReferenceContext` `LLMUsage` `개발` `deprecated` |
| `인증` | select | `Bearer JWT` (97) / `없음` / `API Key` / `내부 전용` / `내부(permitAll)` / `내부(Orchestration→Agent)` / `미정` |
| `Input type` | select | `없음` `JSON` `Query` `WebSocket 메시지` |
| `Input` | rich_text | free-form, but conventionally `[header] …` / `[path] …` / `[query] …` / `[body] …` lines |
| `응답` | rich_text | `[200] TypeName { … }`; long rows carry a full JSON shape and design rationale |
| `오류 응답` | rich_text | `401 미인증 / 404 빌드 없음 / 400 …` |
| `구현 현황` | select | `구현 완료` (118) / `미구현` (34) / `대체됨` (9) / `구현 중` (4) |
| `근거` | rich_text | source of truth: code path with line number, Jira key, PR number |
| `명세 버전` | rich_text | e.g. `artel-orchestration-server@develop (2bba4fe)` or `ARTEL-487 계약 (2026-08-21)` |
| `명세 변경` | select | `Hermes 추가` (new) / `Hermes 보완` (amended) / `기존 명세` |
| `명세 구분` | select | `API 명세` (125) / `작성 템플릿` (1) |
| `최종 편집 일시` | last_edited_time | |

**Row body convention.** The authoring template lives at page
`3a40bce5-474c-8197-b257-ca2af06c36d5` (`🧩 API 명세 작성 템플릿`). It prescribes
sections `## 1. 기본 계약` (a table restating the DB properties),
`## 2. 요청 계약` (path/query/headers/request body), `## 3. 성공 응답`, and
onward. In practice many rows carry everything in the properties and leave the
body empty — the properties are the real contract, the body is the elaboration.

**How to use it.** When you need to know whether an endpoint exists, what it
returns, or whether it is implemented, query this database before reading
Kotlin source. The `근거` field then points you at the exact file and line.

**Trust caveats.**
- 42 rows have `명세 구분` empty and 57 have `명세 변경` empty — older rows
  predating those fields. Absence is not a signal.
- Some select values were saved with literal quote characters:
  `"대체됨"`, `"Hermes 보완"`. Filter on both forms or you silently miss rows.
- 15 rows are `Category = deprecated`. Exclude them unless doing history work.

### 4.2 `API 명세서 (1)` — stale duplicate, do not use

- database id: `3a80bce5-474c-80eb-8f1f-d38f428cbf0d`, 82 rows.
- Its parent database is not accessible to the integration; its `Category`
  options predate `TestCase` / `TestRun` / `Knowledge` / `LLMUsage`.
- A copy taken before the current spec work. **Never write here.** If a search
  result surfaces a row from this id, re-look it up in 4.1.

### 4.3 `문서` — the document index

- database id: `36e0bce5-474c-80de-9026-d310fa0884a5`
- data source id: `36e0bce5-474c-808d-91e2-000b77669a97`
- 29 rows. Properties: `Name` (title), `Category` (select: `설계` 11 / `개발` 12 /
  `일반` 6), `URL` (url, mostly empty), `Created time`, `최종 편집 일시`,
  `최종 편집자`.

Each row is a full document page. This is the entry point for design and
planning context. Current contents:

| Category | Name | page id |
|---|---|---|
| 개발 | 1주차 Artel SDK 개발 기록 | `3b30bce5-474c-8195-bf82-e8cd4cbc03e0` |
| 개발 | API 명세 | `3990bce5-474c-8063-8dab-f3470590e719` |
| 개발 | Agent의 정량적 평가 | `3b30bce5-474c-8121-a8f1-d979d4985666` |
| 개발 | Artel SDK 적용 방식 서칭 | `3960bce5-474c-808b-a907-c0524b995d03` |
| 개발 | GameContext Hadn off | `3a50bce5-474c-8024-bb23-c36835a6a071` |
| 개발 | KeyCode 종류 | `3b30bce5-474c-8174-a23a-fe4c8bd81f9b` |
| 개발 | Keyboard Proxy에 대한 고민 | `3b30bce5-474c-81a6-85a6-d9ef2a009e7a` |
| 개발 | SDK WebSocket JSON-RPC 명세 | `3a50bce5-474c-813f-9563-ffd32aeefe59` |
| 개발 | SDK 생각 해볼 것들 | `3b90bce5-474c-80ec-9998-f2240b917ba8` |
| 개발 | Scene Block 구조 | `39e0bce5-474c-8055-ac9c-dad94e34f032` |
| 개발 | TestScenario 데이터 흐름 (FE↔Orche↔Agent) | `3a50bce5-474c-812c-887f-f7240b477042` |
| 개발 | WordVenture 에이전트 성능 벤치마크 시나리오 | `3c80bce5-474c-8115-888f-f1c531e4921f` |
| 설계 | Artel 기능 명세서 | `3990bce5-474c-8073-aec2-c503f0dc1b08` |
| 설계 | BM 설계 | `37d0bce5-474c-80a4-84aa-fb7ecbca142e` |
| 설계 | DB Schema | `3990bce5-474c-80b4-bb3e-ea7bfdcc0cde` |
| 설계 | MVP 목표 | `37d0bce5-474c-8006-a161-c7c2098b5ca8` |
| 설계 | Usecase | `3990bce5-474c-80a9-b03d-cc2a15314df7` |
| 설계 | [기획] Agent 게임 플랫폼 | `3770bce5-474c-802c-8838-cdbfdd2bcaac` |
| 설계 | 기획 초안 | `3770bce5-474c-80db-9236-ec136c871a4d` |
| 설계 | 명세서{MetaData}\| 설계 - | `3b30bce5-474c-80ae-b968-dd1c213006c5` |
| 설계 | 아르텔 기획 | `37d0bce5-474c-8054-b28d-fbb3cada1fda` |
| 설계 | 아키텍처 | `37d0bce5-474c-800b-b87e-d2f0b966714d` |
| 설계 | 핵심 기능 | `37d0bce5-474c-801f-9e8f-f4d83b7008dc` |
| 일반 | API 전체화면 | `3a80bce5-474c-80cf-b522-c33f9de6a083` |
| 일반 | FGI | `3800bce5-474c-808a-8dab-e1737902825d` |
| 일반 | 결정이 필요한 안건 | `37f0bce5-474c-80f1-9737-ee12c7f2da21` |
| 일반 | 멘토 매칭을 위한 팀 소개 | `37b0bce5-474c-8011-8518-e2436cefbfe0` |
| 일반 | 설계 중 멘토링 질문 사항 | `3900bce5-474c-80ab-b379-da587ed0104d` |
| 일반 | 설문 조사 & 멘트 | `3770bce5-474c-8073-ad17-efc07ef5cf9e` |

Rows written by the integration show `최종 편집자: ArtelNotionToken` — that is
how you tell agent-written documents from human ones.

### 4.4 `개발 스탠드 업` — daily standup log

- database id: `39f0bce5-474c-8061-bdd0-fe9c99dfe556`
- data source id: `39f0bce5-474c-8081-9909-000ba0124546`
- 95 rows. Properties: `이름` (title, format `YY.MM.DD 한 일`), `태그` (select:
  `김태민` / `정의진` / `정윤성` — one row per person per day), `생성일`
  (created_time), `작성 완료` (checkbox).

**Body convention** (agent-generated rows follow this exactly):

```markdown
# 개요
- 조회(기준: 최근 1일, KST): Jira …건, GitHub PR …건.
- <one or two sentences of what the day was about>
## PR
- [merged] feat(scenario): … — artel-agent-server#101
- [open]   fix(scenario): … (ARTEL-508) — artel-orchestration-server#163
# 회고
회고 작성 필요
```

Rules visible in the existing rows: state the evidence base explicitly
(`GitHub 근거만으로 작성(Jira 근거 없음, 추측으로 채우지 않음)`), one bullet per
PR with state, conventional-commit subject, and `repo#number`. Leave
`# 회고` for the human — an agent does not write someone's retrospective, and
`작성 완료` stays `false` until the human ticks it.

### 4.5 `회의록` — meeting notes

- database id: `3850bce5-474c-801e-8dc7-cbc3ba8bb142`
- data source id: `3850bce5-474c-80b4-bd39-000bd9c844f5`
- 45 rows. Properties: `이름` (title), `Date` (date, supports start/end times),
  `태그` (multi_select: `팀 회의` `멘토링` `계획` `일정`), `할 일` (select:
  `없음` / `할 일 있음` / `진행 중` / `완료`, plus a polluted `"할 일 있음"`),
  `사람` (people), `장소` (place), `생성일`, `회의 요약본` (url — CLOVA Note
  link, usually empty).

Bodies are free-form Korean: `## 목표`, bullets with owner arrows
(`evidence ← 의진`), photos of whiteboards, code fences. Some meeting rows
contain their own inline `할 일` database (see 4.9). Read-mostly for agents;
writing meeting notes is a human act unless asked.

### 4.6 `Artel 기능 명세서` — feature backlog (stale)

- database id: `3990bce5-474c-8083-b2ed-f7010b2db82f`
- data source id: `3990bce5-474c-80fe-bd19-000bf0d6900e`
- 30 rows. Properties: `기능 ` (title — **note the trailing space in the
  property name**), `도메인` (select: `Auth` `Project` `GameBuild` `QACenter`
  `QAIssue` `QAReport` `Agent` `OrchastratorSDK` (sic) `ArtelSDK`),
  `우선순위` / `개발 난이도` (select `상`/`중`/`하`), `구현 완료` (checkbox),
  `설명` (rich_text, empty on every row).

**All 30 rows have `구현 완료 = false`** while `API 명세서` records 118 endpoints
as `구현 완료`. This database was filled during planning and never maintained.
Treat it as a historical wish-list, **not** as implementation status. For
current status use `API 명세서.구현 현황`.

### 4.7 `개인 정리용 페이지` — personal research notes

- database id: `37c0bce5-474c-80d4-b4fc-efecef3832dc`
- data source id: `37c0bce5-474c-805e-8c1d-000bd6c455bc`
- 23 rows. Properties: `이름` (title), `페이지 소유자` (**status** type, not
  select — options are the three member names), `다중 선택` (multi_select:
  `Infrastructure` / `Orchestraion` (sic)), `최종 편집 일시`.

High-signal engineering write-ups live here, e.g. token cost measurements,
embedding model selection rationale (ARTEL-184), coroutine migration pitfalls,
the TestCase/TestScenario/TestRun junction-vs-JSON trade-off. Worth searching
before re-deriving a decision.

Etiquette: these are owned by individuals. **Read freely, do not edit another
person's row.** Create rows only under your own owner value when asked.

### 4.8 `질문` — mentoring questions

- database id: `3900bce5-474c-80d6-bd6c-dd65be002fd2`
- data source id: `3900bce5-474c-80ea-8708-000bc8a8389e`
- 10 rows. Properties: `질문 내용` (title — actually holds the mentor and date,
  e.g. `박재범 멘토님 멘토링 (8/17)`), `상태` (status: `시작 전` / `진행 중` /
  `완료`), `생성 일시`.

Bodies hold the questions and the mentor's answers, often with an answer table
keyed by mentor name.

### 4.9 Minor / inline databases

| Name | id | Rows | Notes |
|---|---|---|---|
| `토큰 실측치 (2026-08-13)` | `4df2b6ee-b2d7-4bfa-8114-a920ff4b0d05` (ds `2f28c331-e02c-413a-96dd-f70348fbec0f`) | 21 | Chart data for the token-cost write-up. `규모` / `항목` / `차트` selects + `토큰` number. |
| `할 일` | `3b20bce5-474c-80fb-9a10-edfe08b8f176` | 1 | Inline in `3번째 스프린트 회의록`. `카테고리` select has zero options. |
| `할 일` | `3980bce5-474c-8016-9583-e0f042025528` | 1 | Inline in `오늘 회의록`. Different schema from the other `할 일`. |
| `멘토링` | `afdcba39-367c-4231-b8e4-429a57547f05` | 0 | Empty, title-only. Inline in `박재범 멘토님 오프라인 멘토링`. |
| `설계 문서` | `3990bce5-474c-804b-8087-d2a5005474c6` | ? | **Returns 404 to the integration.** Not connected. Ask a human to add the connection before relying on it. |

Two ad-hoc `할 일` tables with the same name and different schemas means "the
todo database" is ambiguous. Always resolve by id, never by name.

---

## 5. Standalone pages worth knowing

| Page | id | Why |
|---|---|---|
| `Artel` (root) | `36d0bce5-474c-8021-8b4a-c39f9ced694d` | Body holds `# Team Base Rule` — working hours, daily standup at ~17:00, Monday issue assignment, PR self-comment and fast-review norms. |
| `🧭 Artel Index` | `3c80bce5-474c-8125-89f1-dcbef41b2726` | Agent-oriented entry point for understanding workspace structure and routing into the API Spec, Documents, Progress Log, and Personal Notes indexes. |
| `중간 발표 대비 3주 스프린트 계획 (8/18~9/7)` | `3c00bce5-474c-8176-afb0-f58a57c3798a` | Current plan of record: the pipeline `게임+SDK → evidence → 씬 명세 → TC → TS → QA 런 → 화면 명세`, owner per stage, and the two hard constraints (TC input is 씬 명세 alone; scene edges are observable only at runtime). |
| `content_map — 씬·화면·기능 스키마 설계` | `3c00bce5-474c-8163-9b3f-f4e28eae8a59` | Scene/screen/capability schema design. |
| `팀원 정보` | `36f0bce5-474c-8099-a4dc-f994d4a4099a` | Contains phone numbers, emails, birthdays, and a signature image. **Personal data — do not copy out of Notion, do not paste into code, issues, or PRs.** |
| `이동 경로 (삭제 X)` | `3ab0bce5-474c-80f0-8d09-d23b3e3bb253` | A one-link redirect stub kept deliberately. Do not delete or tidy. |
| `GC` | `3ac0bce5-474c-8062-92da-e811c28bdf8c` | Demo game planning drafts (`데모 게임 기획_1`, `데모 게임 기획 2`, `기획 메몸`). |

---

## 6. Recipes

Every snippet assumes `set -a && . ./.notion.env && set +a` has been run.

**Read a page (or a database row) as Markdown — the default move:**

```bash
ntn pages get 3c30bce5-474c-81c6-ba62-fa0683265555
```

Properties come back as YAML frontmatter, body as Markdown. If stderr warns
about truncation, re-run with `--json` and follow `unknown_block_ids`.

**Find an endpoint by category:**

```bash
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query -d '{"page_size":50,"filter":{"property":"Category","select":{"equals":"TestScenario"}}}'
```

**Find unimplemented endpoints on one server:**

```bash
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query -d '{"page_size":100,"filter":{"and":[{"property":"Server","select":{"equals":"Agent Server"}},{"property":"구현 현황","select":{"equals":"미구현"}}]}}'
```

**Full-text search across the workspace:**

```bash
ntn api v1/search -d '{"query":"content-map","page_size":20}'
```

Search matches titles only, not body text. For body text, fetch candidate pages
and grep locally.

**Create a document row in `문서`:**

```bash
ntn pages create --parent data-source:36e0bce5-474c-808d-91e2-000b77669a97 --content '# Title

Body in Markdown.'
```

`ntn pages create` sets only the title (from a frontmatter `title:` block;
leading frontmatter is stripped from the input). **All other properties are
ignored.** To set `Category`,
`Server`, `구현 현황` and friends, create with `ntn api v1/pages` and a full
`properties` object, or create then `PATCH /v1/pages/{id}`:

```bash
ntn api v1/pages/<page-id> -X PATCH -d '{"properties":{"Category":{"select":{"name":"개발"}}}}'
```

**Replace a page body:**

```bash
ntn pages edit <page-id> < body.md
```

This replaces the whole body. It refuses to delete child pages and databases
unless `--allow-deleting-content` is passed — never pass that flag without an
explicit human instruction.

**Endpoint discovery, when unsure of syntax:** `ntn api ls`,
`ntn api <path> --help`, `ntn api <path> --docs`, `ntn api <path> --spec`.
The CLI is self-documenting; prefer it to guessing.

---

## 7. Traps

1. **Linked views cannot be resolved by the API.** Blocks
   `3ab0bce5-474c-8064-a5a0-c774320390ed`, `3b30bce5-474c-801f-9cc7-d4c3014889a1`,
   and `38f0bce5-474c-802d-8507-d50d063fe31f` render as databases in the Notion
   UI but return `400 … does not contain any data sources accessible by this API
   bot`. They are views of databases listed in section 4. Never treat one as a
   distinct database; go to the real id.

2. **Duplicate names.** `API 명세서` vs `API 명세서 (1)`; two different `할 일`
   databases; the page `API 명세` (a `문서` row) vs the database `API 명세서`
   inside it; the page `문서` vs the database `문서`. Resolve by id always.

3. **Polluted select options.** `"대체됨"`, `"Hermes 보완"`, `"할 일 있음"`
   exist as separate options with literal quotes. A naive equality filter
   under-reports. Either filter with `or`, or fetch and normalise in Python.

4. **A trailing space in a property name.** `Artel 기능 명세서` has a title
   property named `기능 ` (with a trailing space). Copy it exactly.

5. **`페이지 소유자` is a `status` property**, not a `select`. Filters differ.

6. **Empty ≠ false.** Many older `API 명세서` rows have empty `명세 구분`,
   `명세 변경`, `명세 버전`. Absence means "predates the field", not "no".

7. **S3 file URLs expire.** Image links returned by the API are presigned and
   valid for about an hour. Do not store them in documents or issues; re-fetch.

8. **Do not exfiltrate personal data** from `팀원 정보` or from meeting-note
   photos.

9. **`설계 문서` is not connected to the integration.** If a task needs it, ask
   a human to open the page and add the connection under `... > Connections`.

---

## 8. Write policy

- Read anything the integration can reach. Writing is narrower.
- Safe to write when asked: new rows in `개발 스탠드 업` (own the format in 4.4),
  new rows in `문서`, new rows in `API 명세서` following the template.
- Ask first: editing an existing `API 명세서` row's `구현 현황` or `근거`
  (it is the contract of record), anything in `개인 정리용 페이지` owned by
  someone else, anything in `회의록`.
- Never: write to `API 명세서 (1)`, delete `이동 경로 (삭제 X)`, pass
  `--allow-deleting-content`, tick someone's `작성 완료`, or write a `# 회고`.
- Every `API 명세서` row you add or change must carry a `근거` that a reader can
  verify — a code path with a line number, a PR number, or a Jira key. A row
  without evidence is worse than no row.
