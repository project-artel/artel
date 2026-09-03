# 2026-09-01 — PK 노출 제거: 프로젝트 단위 번호 도입

- Date: 2026-09-01
- GitHub Issue: None
- Status: Draft

## Goal

브라우저가 보는 URL 과 화면 글자에서 전역 `BIGSERIAL` PK 를 없앤다. 자리를 대신할 값은
**프로젝트 안에서 1번부터 매기는 번호**다. GitHub 이슈 번호와 같은 모양이고,
`(project_id, number)` 복합 유니크가 그 유일성을 DB 가 지키게 한다.

성공 기준 두 가지.

1. `/projects/1/qa-tries/4242` 가 `/projects/1/qa-runs/7` 처럼 읽힌다 — 링크에서 새는 것이
   "이 프로젝트의 7번째" 로 줄고, 서비스 전체 QA 실행 횟수는 더 이상 나가지 않는다.
2. 화면에 찍히는 `#4242` 열 곳이 전부 사라진다.

## Non-goals

- **`project` 자체는 `id` 를 유지한다.** slug 도 번호도 넣지 않는다. `/projects/2` 를 찍어보는
  열거는 그대로 남고, 그건 이번 범위 밖이다. 나중에 프로젝트만 따로 바꿔도 이 작업을 되돌릴
  일은 없다.
- **`/api/sdk/*` 와 `/internal/*` 은 PK 를 유지한다.** Unity SDK 와 agent-server 는 인증된
  신뢰 호출자라 URL 을 가려서 얻는 것이 없고, 번호를 강요하면 서버가 매번 번호를 다시 푸는
  일만 늘어난다.
- **hash 를 쓰지 않는다.** `capability.capability_key` 는 내용 기반 문자열이라 재적재를 넘는
  참조용으로만 남기고, 화면 표시는 번호가 맡는다.
- 접근 제어 로직 자체를 새로 쓰지 않는다. 전역 경로가 프로젝트 스코프로 바뀌면서 조인이
  구조적으로 강제되는 것은 부수 효과지 목표가 아니다.
- `.worktrees/` 를 깨는 eslint 설정 등 눈에 걸리는 다른 문제는 건드리지 않는다.

## Context / Constraints

### 지금 새는 곳 (2026-09-01 실측)

URL 에 박힌 PK 7종 — `artel-home/src/App.tsx:86-127`:
`projectId` · `instanceId` · `testScenarioId` · `runId` · `qaRunId` · `buildId` · `qaTryId`.

화면에 글자로 찍히는 PK 열 곳:

| 위치 | 찍히는 것 | 처리 |
|---|---|---|
| `contentMap/SceneGraphInspector.tsx:130` | `씬 id` 라벨 + `scene.id` | **필드 삭제** — `uk_scene_map_name` 으로 이름이 이미 유일하고 바로 위에 표시 중 |
| `contentMap/SceneGraphInspector.tsx:261` | `능력 {capabilityId}` | content_map 단위 번호 |
| `contentMap/EvidenceScanPanel.tsx:234` | `문서 {documentId}` | content_map 단위 번호 |
| `knowledge/KnowledgeInspector.tsx:290` (`i18n/messages/knowledge.ts:101,220`) | `화면 #4242` | scene 단위 번호 |
| `knowledge/KnowledgeInspector.tsx:146,359` | `#{knowledge node.id}` | 표시 삭제 |
| `knowledge/KnowledgeInspector.tsx:216` | `#{createdByQaTryId}` | 프로젝트 단위 번호 |
| `qa/QaTryPage.tsx:130`, `QaTryPanel.tsx:311`, `DashboardSection.tsx:127`, `QaHistorySection.tsx:93` | `QA Try #{id}` | 프로젝트 단위 번호 |
| `DashboardSection.tsx:153` | `#{issue.qaTryId}` | 프로젝트 단위 번호 |
| `qa/QaLogTimeline.tsx:140,209` | `#{log.id}` | **qa_try 안 순번** — 프로젝트 번호는 뜻이 없다 |
| `projects/GameInstanceDetailPage.tsx:119` | `instance.id` | 프로젝트 단위 번호 |

DOM 에도 남는다: `QaLogTimeline.tsx:134,190,196,211` 의 `data-log-id` 와
`aria-labelledby="qa-log-{id}-message"`.

### 접근 제어는 이미 걸려 있다

`ProjectService.get` 이 `findAccessibleById(projectId, userId)` 로 `project_member` 를 조인한다
(`ProjectRepository.kt`). 즉 이건 권한 우회 문제가 아니라 **열거와 규모 노출** 문제다.
우선순위를 그 기준으로 잡았다.

다만 `TestScenarioController.kt:30` 의 `/api/test-scenario/{testScenarioId}` 와
`IssueController.kt:21` 의 `/api/issues/{issueId}` 는 **경로에 프로젝트가 없는 전역 PK 경로**라
검사가 서비스 안에만 있다. 프로젝트 스코프로 옮기면 `projectId` 가 경로에 들어와 조인을 타야만
성립한다.

### 밖으로 튀는 범위 (실측)

| 소비자 | 부르는 경로 | 영향 |
|---|---|---|
| Unity SDK | `/api/sdk/projects`, `/api/sdk/registrations`, `/api/sdk/game-builds/`, `/api/sdk/qa-captures/tickets`, `/api/auth/sdk/token` | **0** — 브라우저용 `/api/projects/*` 를 한 번도 안 부른다. 릴리스 불필요 |
| agent-server | `/internal/*` 만 | **0** |
| admin-page | `expectedLabelsApi.ts:53` 한 줄 | **1줄** |
| artel-home | API 모듈 10개, 호출 지점 약 59곳 | 여기가 전부 |

`project` 를 `id` 로 두기로 한 덕분에 SDK 의 `Artel.ProjectId` PlayerPrefs
(`ArtelOwnedPlayerPrefs.cs:33`) 도 그대로다.

### project_id 가 없는 네 테이블

복합 유니크는 두 컬럼이 같은 테이블에 있어야 DB 가 걸 수 있다.

| 테이블 | 프로젝트까지 닿는 경로 | 결정 |
|---|---|---|
| `qa_try` (`V9:1`) | `test_scenario_id` → `project_id` | `project_id` 비정규화 |
| `qa_run` (`V30:6`) | `test_run_id` → `project_id` | `project_id` 비정규화 |
| `issue` (`V12:21`) | `qa_try_id` → … | `project_id` 비정규화 |
| `qa_log` (`V9:26`) | `qa_try_id` → … | **비정규화하지 않음** — 범위가 `qa_try` |

비정규화는 `V42` 가 `capability` 에 `content_map_id` 를 넣을 때 쓴 방법을 그대로 따른다.
거기 주석이 이유를 이미 적어놨다: "scene 을 통해 이미 알 수 있는 값이지만 복합 FK 로 씬의 것과
묶어 두 벌이 갈라지지 않게 한다."

### 번호 채번은 새로 설계하지 않는다

`project_document.version` 이 이미 같은 일을 한다.

- `ProjectDocumentRepository.kt:27` — `SELECT COALESCE(MAX(version), 0) … WHERE project_id = :projectId`
- `ProjectDocumentService.kt:239` — "MAX(version) + 1은 읽고 쓰는 사이에 경합이 난다.
  유니크 제약이 그 충돌을 예외로 만들고" 재시도
- `ProjectDocumentService.kt:103-105` — 트랜잭션 안에서 유니크 위반이 나면 롤백되므로
  **재시도 루프를 트랜잭션 밖에** 둔다

프로젝트마다 Postgres sequence 객체를 만드는 방식은 쓰지 않는다. 위 세 줄이 그대로 새 채번
코드가 된다.

### 컬럼 이름

`number` 로 한다. GitHub 의 `issue.number` 와 같은 개념이고, Postgres 에서 non-reserved 라
따옴표 없이 쓸 수 있다. 코드에서는 `qaTry.number`, URL 에서는 `/qa-tries/7`.

## Approach (Checklist)

- [x] **Step 0: Recon** — 노출 지점 열 곳, URL 7종, 소비자 4곳, 채번 선례 확인 완료 (위 Context)

- [ ] **Step 1: Migration `V64` — `project_id` 비정규화**
  - 대상: `qa_try` · `qa_run` · `issue`
  - `V42` 순서를 그대로 따른다: 컬럼 추가(nullable) → 부모에서 `UPDATE` 로 채움 → `SET NOT NULL`.
    기존 행이 있는 데이터베이스에서 기본값 없는 `NOT NULL` 은 거절되므로 한 번에 걸지 않는다.
  - 두 벌이 갈라지지 않게 복합 FK 로 묶는다:
    - `test_scenario` 에 `UNIQUE (id, project_id)` → `qa_try (test_scenario_id, project_id)` FK
    - `test_run` 에 `UNIQUE (id, project_id)` → `qa_run (test_run_id, project_id)` FK
    - `qa_try` 에 `UNIQUE (id, project_id)` → `issue (qa_try_id, project_id)` FK
  - 참고: `test_run.project_id` · `test_scenario.project_id` · `test_case.project_id` 는
    `project` 로의 FK 가 원래 없다(`V17:42`, `V5:12` — 인덱스만). 기존 결함이고 이번에 고치지
    않는다. 복합 FK 는 그것과 무관하게 성립한다.

- [ ] **Step 2: Migration `V65` — 프로젝트 단위 `number`**
  - 컬럼 추가 → `ROW_NUMBER()` 로 backfill → `SET NOT NULL` → 복합 유니크.
  - backfill 순서는 `created_at` 오름차순, 같은 시각은 `id` 로 가른다:
    `ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at, id)`.
    `created_at` 이 없는 표는 `id` 만 쓴다.

  | 테이블 | 유니크 |
  |---|---|
  | `test_run` | `(project_id, number)` |
  | `test_scenario` | `(project_id, number)` |
  | `game_build` | `(project_id, number)` |
  | `game_instance` | `(project_id, number)` |
  | `test_case` | `(project_id, number)` |
  | `qa_try` | `(project_id, number)` |
  | `qa_run` | `(project_id, number)` |
  | `issue` | `(project_id, number)` |
  | `qa_log` | `(qa_try_id, number)` — 범위가 다르다 |

- [ ] **Step 3: Migration `V66` — content map 계층**
  - 프로젝트까지 세 단계라 프로젝트 번호를 붙이면 빌드가 바뀔 때마다 번호가 뒤섞인다.
    각자의 진짜 부모로 잡는다.

  | 테이블 | 유니크 | 비고 |
  |---|---|---|
  | `screen` | `(scene_id, number)` | `created_at` 이 없어 `id` 순으로 backfill |
  | `capability` | `(content_map_id, number)` | `capability_key` 는 그대로 둔다 |
  | `content_map_document` | `(content_map_id, number)` | |

  - `scene` 은 번호를 넣지 않는다. `uk_scene_map_name UNIQUE (content_map_id, name)` 으로
    이름이 이미 유일하다.

- [ ] **Step 4: 서버 — 채번**
  - `ProjectDocumentService.kt:103-105,239` 패턴을 옮긴 공통 헬퍼 하나.
    `MAX(number) + 1` 조회 → insert → 유니크 위반이면 **트랜잭션 밖 루프에서** 재시도.
  - 각 생성 지점(`QaTryService.create`/`createRun`, `TestRunService`, `TestScenarioService`,
    `GameBuildService`, `SdkRegistrationService`, `TestCaseService`, 이슈 적재, qa_log 적재,
    `ContentMapIngestService`)이 이 헬퍼를 쓴다.

- [ ] **Step 5: 서버 — 경로**
  - 이미 프로젝트 스코프인 컨트롤러는 `@PathVariable` 의 **뜻만** 바뀐다(PK → number):
    `TestRunController` · `GameBuildController` · `GameInstanceController` ·
    `TestCaseController` · `ProjectTestScenarioController` · `ProjectContentMapController` ·
    `SdkPerfController`.
  - 전역 경로는 프로젝트 스코프 쌍을 **추가**한다:

  | 지금 | 새로 |
  |---|---|
  | `/api/qa-tries/{id}` + `/messages` `/cancel` `/logs` `/issues` `/events` | `/api/projects/{projectId}/qa-tries/{number}/…` |
  | `/api/qa-runs/{id}` + `/cancel` | `/api/projects/{projectId}/qa-runs/{number}/…` |
  | `/api/issues/{id}/resolve` `/reopen` | `/api/projects/{projectId}/issues/{number}/…` |
  | `/api/test-scenario/{id}` PUT · approve · delete | `ProjectTestScenarioController` 로 이관 |

  - `POST /api/qa-runs` 와 `POST /api/qa-tries` 는 body 기반이라 경로는 그대로. body 의
    `testRunId` · `gameInstanceId` 는 number 로 받는다.
  - `(projectId, number, userId)` → 엔티티 변환은 한 곳에 모으고 `ProjectAccessService` 를 탄다.
  - **기존 PK 경로는 지우지 않는다.** Step 8 참고.

- [ ] **Step 6: 프론트 — 라우트와 API**
  - `App.tsx:86-127` 의 파라미터가 number 를 뜻하게 된다. 경로 모양은 `projectId` 를 빼면
    그대로다.
  - API 모듈 10개: `qaApi.ts` · `testRunApi.ts` · `runChatApi.ts` · `contentMapApi.ts` ·
    `gameApi.ts` · `issueApi.ts` · `scenarioApi.ts` · `scenarioCaseApi.ts` ·
    `performanceApi.ts` · `streamApi.ts` (약 59곳).
  - `GameInstanceDetailPage.tsx:49-59` 의 "목록 받아서 `find`" 우회는 **삭제한다**.
    번호로 직접 조회가 되면 필요 없다.

- [ ] **Step 7: 프론트 — 표시**
  - Context 표의 열 곳을 번호로 바꾸거나 지운다.
  - `SceneGraphInspector.tsx:130` 과 `i18n/messages/contentMap.ts:171,407` 의 `sceneIdLabel`
    은 필드째 삭제.
  - `QaLogTimeline.tsx` 의 `data-log-id` · `aria-labelledby` 도 number 로.

- [ ] **Step 8: admin-page**
  - `expectedLabelsApi.ts:53` 한 줄.

## Validation

- **Commands to run:**
  - 서버: `cd artel-orchestration-server && ./mvnw test` (테스트 131개)
  - 마이그레이션: 운영 스냅샷 복원본에 `V64`–`V66` 적용 후, 각 표에서
    `SELECT scope, COUNT(*), COUNT(DISTINCT number), MIN(number), MAX(number) GROUP BY scope`
  - 프론트:
    `export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH"; unset -f node npm npx 2>/dev/null; npm test`
    그리고 `npm run typecheck`
  - lint 는 리포지토리 전체에 돌리면 `.worktrees/` 때문에 파싱 단계에서 죽는다. 바뀐 파일만
    `npx eslint <paths>`.
- **Expected output:**
  - backfill 검증 질의에서 모든 scope 가 `COUNT(*) = COUNT(DISTINCT number)` 이고
    `MIN = 1`, `MAX = COUNT(*)` — 빈칸도 중복도 없다.
  - `./mvnw test` 통과. 채번 경합 테스트를 새로 추가한다: 같은 프로젝트에 동시 생성 N 건이
    1..N 을 빠짐없이 받는지.
  - 수동 확인: 프로젝트 둘을 만들고 각각 QA Try 를 돌려 양쪽 모두 1번부터 시작하는지.

## Risks & Rollback

- **Risks:**
  - **깨는 변경이다.** `artel-home` · `artel-orchestration-server` · `admin-page` 가 같이
    나가야 하는데 프론트는 Vercel, 서버는 Jenkins 로 배포가 따로다. 그 사이에 옛 프론트가
    새 서버를 때리는 구간이 생긴다. → 기존 PK 경로를 **한 릴리스 살려 두고** 다음에 지운다.
    `/api/sdk/*` 와 `/internal/*` 이 계속 PK 를 쓰므로 서비스 계층의 PK 조회 코드는 어차피
    남아 있고, 컨트롤러 매핑만 한동안 두 벌이다.
  - **네트워크 탭에는 여전히 PK 가 안 보이게 되지만**, 그건 서버 경로까지 바꾸기 때문이다.
    반대로 `/api/sdk/*` 를 보는 사람에게는 PK 가 그대로 보인다. 의도한 것이다.
  - **backfill 중 쓰기.** `V65` 의 `ROW_NUMBER()` 와 `SET NOT NULL` 사이에 새 행이 들어오면
    `NOT NULL` 이 거절된다. 배포 창에서 돌리거나, 컬럼을 nullable 로 두고 애플리케이션이
    먼저 채우게 한 뒤 다음 마이그레이션에서 조인다.
  - **활성 QA 실행.** `uk_qa_try_active_instance` 로 인스턴스당 활성 try 는 하나뿐이라
    마이그레이션 시점에 돌고 있는 실행이 있으면 그 행도 번호를 받아야 한다. backfill 이
    상태를 안 가리므로 문제없지만, 실행 중 취소가 안 나는지 확인한다.
  - **북마크 사망.** 기존 `/projects/1/qa-tries/4242` 링크는 새 뜻으로 읽히면 다른 것을
    가리키거나 404 가 된다. 되돌릴 방법이 없다. 사내 도구라 감수한다.
- **Rollback steps:**
  - 컨트롤러/프론트는 `git revert`. 기존 PK 경로를 한 릴리스 살려 두므로 서버만 되돌려도
    옛 프론트가 돈다.
  - 마이그레이션은 되돌리지 않는다. `V64`–`V66` 은 전부 컬럼·제약 **추가**라 옛 코드가
    그 컬럼을 몰라도 동작한다. 정말 지워야 하면 `V67` 로 `DROP` 한다 — `V40` 주석이 적어둔
    대로 이미 적용된 파일의 본문은 checksum 이 계약이라 고칠 수 없다.

## Open Questions

- `V65` 의 backfill 과 `SET NOT NULL` 사이 경합을 배포 창으로 막을지, nullable 2단계로 갈지.
  운영 데이터 규모를 모른다 — 행 수가 작으면 배포 창이 간단하다.
- `knowledge` 노드(`KnowledgeInspector.tsx:146,359`)의 `#{id}` 는 표시를 지우기로 했는데,
  디버깅에 쓰이고 있었다면 대신 무엇을 보여줄지.
- 기존 PK 경로를 지우는 "다음 릴리스" 를 이 계획에 넣을지, 별도 작업으로 끊을지.
