> Where to find things and where to put them. Four area indexes go deeper.
> Surveyed 2026-08-26 — 541 objects, 13 databases.

## Area indexes

| Index | Covers |
|---|---|
| [📘 API Spec Index](https://app.notion.com/p/API-Spec-Index-3c80bce5474c81fa9964ead8c2651524) | 168 endpoints. The source of truth for contracts and implementation status |
| [📗 Documents Index](https://app.notion.com/p/Documents-Index-3c80bce5474c816eae14d004b0233962) | 29 design, development, and general documents |
| [📙 Progress Log Index](https://app.notion.com/p/Progress-Log-Index-3c80bce5474c81c9a408cfa3824d0598) | 45 meetings · 95 standup entries · 10 mentoring question sets |
| [📕 Personal Notes Index](https://app.notion.com/p/Personal-Notes-Index-3c80bce5474c81b486d9f640b197545f) | 23 personal research and trade-off notes |

## Do this here

| What you are doing | Where | Watch out |
|---|---|---|
| Check whether an endpoint exists, and what it returns | `API 명세서` database | Start here, before reading Kotlin. `근거` points at the file and line |
| Check whether something is implemented | `구현 현황` in `API 명세서` | Not `Artel 기능 명세서` — all 30 of its rows sit unmaintained at "not done" |
| Record a new endpoint contract | New row in `API 명세서` | Duplicate `🧩 API 명세 작성 템플릿`. A row without `근거` is worse than no row |
| Find why a design decision went that way | `문서` (`설계`) and `개인 정리용 페이지` | Trade-off write-ups usually live in the personal notes |
| Architecture, DB schema, use cases | `문서` database (`설계`) | |
| SDK and Agent internals | `문서` database (`개발`) | |
| Log what you did today | `개발 스탠드 업` | One row per person per day. Format in the Progress Log Index |
| Write up a meeting | `회의록` | |
| Mentor questions and answers | `질문` database | |
| Research, measurements, trade-offs | `개인 정리용 페이지` | Only under your own owner value |
| Check the current sprint goal | `중간 발표 대비 3주 스프린트 계획 (8/18~9/7)` | Carries the pipeline and the owner of each stage |
| Team rules — hours, standup time, PR norms | `Artel` root body, `# Team Base Rule` | |
| Teammate contact details | `팀원 정보` | Personal data. Does not leave Notion |

## Map

```
Artel  (root; Team Base Rule in the body)
├─ 회의록 ─ 🗄 회의록                45 rows
├─ 🗄 문서 (linked view)
├─ 개인 페이지
│   ├─ 🗄 개인 정리용 페이지           23 rows
│   └─ GC                          3 demo-game planning drafts
├─ 멘토링 ─ 🗄 질문                  10 rows
├─ 개발 문서
│   ├─ 🗄 (linked view)
│   └─ content_map — 씬·화면·기능 스키마 설계
├─ 개발 스탠드 업 ─ 🗄 개발 스탠드 업     95 rows
├─ 팀원 정보                         holds personal data
├─ 🗄 (untitled linked view)
├─ 이동 경로 (삭제 X)                 deliberate redirect stub — do not delete
│   └─ 문서
│       ├─ 🗄 문서                   29 rows
│       │   ├─ (row) API 명세         → 🗄 API 명세서        168 rows
│       │   └─ (row) Artel 기능 명세서  → 🗄 Artel 기능 명세서   30 rows
│       └─ 🗄 설계 문서               not connected to the integration
└─ 중간 발표 대비 3주 스프린트 계획 (8/18~9/7)
```

One structural fact matters more than the rest. **`API 명세서` and `Artel 기능
명세서` live inside rows of the `문서` database, under a page named `이동 경로
(삭제 X)`.** You will not find them by scrolling down from the root. Come through
this index, or go straight to the ID.

## Every database

| Database | Rows | Database ID | Data source ID | State |
|---|---|---|---|---|
| API 명세서 | 168 | `3990bce5-474c-80e8-bb41-d52ee7233141` | `c080bce5-474c-8264-b176-0706704849ee` | Active · highest value |
| 개발 스탠드 업 | 95 | `39f0bce5-474c-8061-bdd0-fe9c99dfe556` | `39f0bce5-474c-8081-9909-000ba0124546` | Active |
| 회의록 | 45 | `3850bce5-474c-801e-8dc7-cbc3ba8bb142` | `3850bce5-474c-80b4-bd39-000bd9c844f5` | Active |
| 문서 | 29 | `36e0bce5-474c-80de-9026-d310fa0884a5` | `36e0bce5-474c-808d-91e2-000b77669a97` | Active |
| 개인 정리용 페이지 | 23 | `37c0bce5-474c-80d4-b4fc-efecef3832dc` | `37c0bce5-474c-805e-8c1d-000bd6c455bc` | Active |
| 질문 | 10 | `3900bce5-474c-80d6-bd6c-dd65be002fd2` | `3900bce5-474c-80ea-8708-000bc8a8389e` | Active |
| Artel 기능 명세서 | 30 | `3990bce5-474c-8083-b2ed-f7010b2db82f` | `3990bce5-474c-80fe-bd19-000bf0d6900e` | **Unmaintained** — not a status source |
| 토큰 실측치 (2026-08-13) | 21 | `4df2b6ee-b2d7-4bfa-8114-a920ff4b0d05` | `2f28c331-e02c-413a-96dd-f70348fbec0f` | Chart data for one write-up |
| API 명세서 (1) | 82 | `3a80bce5-474c-80eb-8f1f-d38f428cbf0d` | — | **Stale copy. Never write here** |
| 할 일 | 1 | `3b20bce5-474c-80fb-9a10-edfe08b8f176` | — | Inline in `3번째 스프린트 회의록` |
| 할 일 | 1 | `3980bce5-474c-8016-9583-e0f042025528` | — | Inline in `오늘 회의록`. Different schema |
| 멘토링 | 0 | `afdcba39-367c-4231-b8e4-429a57547f05` | — | Empty |
| 설계 문서 | ? | `3990bce5-474c-804b-8087-d2a5005474c6` | — | **Not connected to the integration (404)** |

## Traps

1. **Names collide.** `API 명세서` vs `API 명세서 (1)`; two different `할 일`
   databases; the page `문서` vs the database `문서`; the page `API 명세` vs the
   database `API 명세서` inside it. Resolve by ID, never by name.
2. **Linked views cannot be resolved through the API.** They render as databases
   in the UI but return `400 does not contain any data sources`. Use the real IDs
   in the table above.
3. **Some select options carry literal quote marks.** `"대체됨"`,
   `"Hermes 보완"`, `"할 일 있음"` exist as separate options. A plain equality
   filter drops those rows silently.
4. **Empty is not "no".** Older rows have `명세 구분`, `명세 변경`, `명세 버전`
   blank. That means the row predates the field.
5. **`이동 경로 (삭제 X)` is a redirect kept on purpose.** Do not tidy it away.
6. **`설계 문서` is not connected to the integration.** If an agent needs it, a
   human has to add the connection under `... > Connections`.

## Agent access

The token lives in `.notion.env` in the repository. The CLI is `ntn`.

```bash
set -a && . ./.notion.env && set +a
ntn pages get <page-id>
ntn api v1/data_sources/<data-source-id>/query -d '{"page_size":50}'
```

Filters, write policy, and the full API notes are in `.agents/docs/NOTION.md`.
