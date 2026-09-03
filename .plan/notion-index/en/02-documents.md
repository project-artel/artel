> 29 design, development, and general documents. Where the reasoning lives.
> Database `36e0bce5-474c-80de-9026-d310fa0884a5` · data source `36e0bce5-474c-808d-91e2-000b77669a97`
> Location: `Artel` → `이동 경로 (삭제 X)` → `문서`
> Surveyed 2026-08-26.

`Category` splits `설계` 11 · `개발` 12 · `일반` 6. Rows whose `최종 편집자` is
`ArtelNotionToken` were written by an agent.

## 설계 — what we decided to build

| Document | Read it when |
|---|---|
| 아키텍처 | Setting server boundaries |
| DB Schema | Checking tables and relations |
| Usecase | Looking at features as user flows |
| 핵심 기능 | Deciding what is inside the MVP |
| MVP 목표 | Cutting scope |
| Artel 기능 명세서 | Feature list — but the database inside is unmaintained (see below) |
| 명세서{MetaData}\| 설계 - | Spec metadata design |
| BM 설계 | Revenue model |
| 아르텔 기획 · 기획 초안 · [기획] Agent 게임 플랫폼 | Early planning lineage. May contradict current decisions |

## 개발 — how we built it

| Document | Read it when |
|---|---|
| SDK WebSocket JSON-RPC 명세 | Working on the SDK protocol |
| Artel SDK 적용 방식 서칭 | Wondering why the SDK attaches to a game the way it does |
| 1주차 Artel SDK 개발 기록 | Tracing early SDK implementation |
| SDK 생각 해볼 것들 | Open questions |
| Keyboard Proxy에 대한 고민 · KeyCode 종류 | Touching input injection |
| Scene Block 구조 | Scene structure |
| GameContext Hadn off | Game context handoff |
| TestScenario 데이터 흐름 (FE↔Orche↔Agent) | Following a flow across all three servers |
| Agent의 정량적 평가 | Measuring agent quality |
| WordVenture 에이전트 성능 벤치마크 시나리오 | Benchmark baseline |
| API 명세 | **Contains the `API 명세서` database.** Go to the API Spec Index |

## 일반 — team, users, decisions

| Document | Read it when |
|---|---|
| 결정이 필요한 안건 | Looking for open decisions |
| 설계 중 멘토링 질문 사항 | Revisiting what blocked us during design |
| FGI · 설문 조사 & 멘트 | User research |
| 멘토 매칭을 위한 팀 소개 | External introductions |
| API 전체화면 | API grouped by screen |

## Design documents outside this database

Two pages that are not rows here and matter most right now:

- **중간 발표 대비 3주 스프린트 계획 (8/18~9/7)** — directly under `Artel`. Holds
  the pipeline `게임+SDK → evidence → 씬 명세 → TC → TS → QA 런 → 화면 명세`, the
  owner of each stage, and the two hard constraints: TC input is the scene spec
  alone, and scene transitions are observable only at runtime. **The reference
  document for work in flight.**
- **content_map — 씬·화면·기능 스키마 설계** — under the `개발 문서` page.

## Cautions

- **The `Artel 기능 명세서` database (30 rows) is unmaintained.** Every row reads
  `구현 완료 = false` while `API 명세서` records 118 endpoints as done. It was
  filled during planning and never kept up. Take implementation status from the
  API Spec Index; read this one only as a trace of the original feature list.
  - Its title property is named `기능 ` — **with a trailing space.**
  - `도메인` carries a typo: `OrchastratorSDK`.
- **`설계 문서` is not connected to the integration** (404). A human has to add
  the connection under `... > Connections` before an agent can read it.
- The planning-lineage documents (`기획 초안`, `[기획] Agent 게임 플랫폼`, …)
  describe a different product than the one being built. Do not cite them as
  grounds for a current decision.

## Adding a document

```bash
ntn pages create --parent data-source:36e0bce5-474c-808d-91e2-000b77669a97 \
  --content '# Title

Body'
```

`ntn pages create` sets the title only. Attach `Category` afterwards.

```bash
ntn api v1/pages/<page-id> -X PATCH -d '{"properties":{"Category":{"select":{"name":"개발"}}}}'
```
