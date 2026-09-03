# 📘 API 명세서 Index

> endpoint 168개. **API 계약과 구현 상태의 유일한 기준.** 코드를 읽기 전에 여기부터 본다.
> database `3990bce5-474c-80e8-bb41-d52ee7233141` / data source `c080bce5-474c-8264-b176-0706704849ee`
> 조사 기준일 2026-08-26.

## 한눈에

| 축 | 분포 |
|---|---|
| Server | Orchestrator 140 · Agent Server 26 · Artel SDK 1 |
| Type | HTTP 157 · Websocket 8 |
| 구현 현황 | 구현 완료 118 · 미구현 34 · 대체됨 9(+2) · 구현 중 4 |
| 인증 | Bearer JWT 97 · 없음 16 · 내부 계열 11 · API Key 3 · 미기재 40 |

## 카테고리별 (구현 현황)

| Category | 건 | 구현 완료 | 미구현 | 그 외 |
|---|---|---|---|---|
| QA | 19 | 15 | 4 | |
| Agent | 15 | 15 | | |
| SDK | 15 | 14 | 1 | |
| deprecated | 15 | 2 | 8 | 대체됨 5 |
| Auth | 13 | 10 | 1 | 대체됨 2 |
| TestRun | 13 | 13 | | |
| Game Build | 12 | 2 | 5 | 대체됨 3 · 구현 중 2 |
| TestScenario | 12 | 12 | | |
| Tool | 11 | | 11 | **전부 미구현** |
| Project | 10 | 10 | | |
| TestCase | 9 | 9 | | |
| Document | 7 | 7 | | |
| Issue | 7 | 3 | 3 | 대체됨 1 |
| Knowledge | 5 | 5 | | |
| 개발 | 2 | | | 구현 중 2 |
| LLMUsage | 1 | 1 | | |

읽는 법 세 가지. `Tool` 11개는 하나도 구현되지 않았다 — 설계만 있고 손대지 않은
영역이다. `Game Build` 는 12개 중 실제로 도는 것이 2개뿐이고 나머지가 미구현·
대체됨으로 갈려 있으니 이 영역을 건드릴 때는 어느 행이 살아 있는지부터 확인한다.
`개발` 카테고리 2개는 `SDK` 의 성능 조회와 같은 URL 을 가리키는 중복이다.

## ⚠️ 중복 행 — 읽기 전에 알아야 할 것

**같은 (Server, Method, URL) 을 가진 행이 18쌍, 총 37행 있다.** 옛 계획 단계 행과
Hermes 재작성 행이 겹쳐 남은 것이다. 구분법:

- **살아 있는 쪽**: `명세 변경 = Hermes 추가` 이고 `명세 버전` 에 실제 커밋이
  적혀 있다 (`artel-orchestration-server@develop (2bba4fe)` 처럼).
- **낡은 쪽**: `명세 버전` 이 `v1` 이거나 비어 있고, `명세 변경` 이 비어 있거나
  `Hermes 보완` 이다.

중복 목록:

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
| Agent Server | GET | `/health` (3행) |
| Agent Server | (WS) | `/internal/qa-sessions/{session_id}` |

정리는 아직 안 했다. 손대려면 어느 쪽을 남길지 사람이 정해야 한다.

## 속성 읽는 법

| 속성 | 뜻 |
|---|---|
| `Server` | Orchestrator / Agent Server / Artel SDK |
| `Type` · `Request Method` · `Url` | HTTP 계약. WebSocket 은 Method 가 `해당 없음` |
| `Category` | 도메인. 위 표의 17종 |
| `인증` | `Bearer JWT` · `없음` · `API Key` · `내부 전용` · `내부(permitAll)` · `내부(Orchestration→Agent)` |
| `Input type` · `Input` | `[header]` `[path]` `[query]` `[body]` 줄로 적는다 |
| `응답` | `[200] TypeName { … }`. 긴 행은 JSON 형태와 설계 근거까지 담는다 |
| `오류 응답` | `401 미인증 / 404 빌드 없음 / 400 …` |
| `구현 현황` | **구현 여부의 기준.** `Artel 기능 명세서` 가 아니다 |
| `근거` | 코드 경로+줄번호, Jira 키, PR 번호. 검증 가능해야 한다 |
| `명세 버전` | 어느 커밋 기준인지 |
| `명세 변경` | `Hermes 추가`(신규) / `Hermes 보완`(보강) / `기존 명세` |

## 행 쓰는 법

`🧩 API 명세 작성 템플릿` (`3a40bce5-474c-8197-b257-ca2af06c36d5`) 을 복제하고
`명세 구분` 을 `API 명세` 로 바꾼다. 본문 골격은 `## 1. 기본 계약` → `## 2. 요청
계약` → `## 3. 성공 응답` 순이다.

실무에서는 속성이 진짜 계약이고 본문은 부연이다. 속성만 채우고 본문을 비워둔 행이
많다. 다만 `근거` 는 반드시 채운다 — 읽는 사람이 검증할 수 없는 명세는 없느니만
못하다.

## 자주 쓰는 조회

```bash
# 한 도메인 전부
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query \
  -d '{"page_size":50,"filter":{"property":"Category","select":{"equals":"TestScenario"}}}'

# 특정 서버의 미구현 endpoint
ntn api v1/data_sources/c080bce5-474c-8264-b176-0706704849ee/query \
  -d '{"page_size":100,"filter":{"and":[
        {"property":"Server","select":{"equals":"Agent Server"}},
        {"property":"구현 현황","select":{"equals":"미구현"}}]}}'
```

`구현 현황` 을 `대체됨` 으로 거를 때는 `"대체됨"` (따옴표 포함) 옵션도 함께
`or` 로 묶는다. 2행이 그쪽에 들어가 있다.
