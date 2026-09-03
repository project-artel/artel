# 프로젝트 단위 번호 — 트랙 공유 계약

이 문서는 `.plan/general/2026-09-01-project-scoped-resource-numbers.md` 의 구현 트랙들이
같은 모양으로 움직이도록 하는 합의다. 트랙은 이 문서를 어기지 않는다.

작업 위치: `artel-orchestration-server/.worktrees/scoped-numbers`
브랜치: `feat/orchestration-리소스를-프로젝트-단위-번호로-가리킨다` (`origin/develop` 기준)

## 이미 끝난 것 — 손대지 말 것

| 마이그레이션 | 내용 |
|---|---|
| `V74__carry_project_id_on_qa_and_issue.sql` | `qa_try` · `qa_run` · `issue` 에 `project_id` 를 싣고 복합 FK 로 부모의 것과 묶었다 |
| `V75__number_resources_within_their_project.sql` | 프로젝트 단위 `number` 9개 표 + `(project_id, number)` 유니크 |
| `V76__number_content_map_rows_within_their_parent.sql` | `screen(scene_id, number)` · `capability(content_map_id, number)` · `content_map_document(content_map_id, number)` |
| `V77__assign_scoped_numbers_on_insert.sql` | `assign_scoped_number()` BEFORE INSERT trigger 12개 |

실데이터로 검증했다: 모든 범위가 빠짐없이 1..N, 20개 세션 동시 삽입 40건에 충돌 0, 복합 FK 가
프로젝트 어긋남을 실제로 거절.

## 채번은 코드가 하지 않는다

**어떤 트랙도 번호를 계산하지 않는다.** `INSERT` 에 `number` 를 싣지 않으면 trigger 가 채운다.
서비스에 MAX+1 도, 재시도 루프도, 채번 헬퍼 호출도 넣지 말 것. 값을 실어 보내면 그 값이 그대로
쓰이므로, 실수로 `number = 0` 같은 것을 넣으면 `CHECK (number >= 1)` 에 걸린다.

## Entity

각 트랙이 자기 entity 에 이 필드를 더한다. **기본값 `null` 을 반드시 준다** — 생성 지점
(main 24곳 · test 약 160곳)을 하나도 고치지 않는 것이 이 설계의 핵심이다.

```kotlin
/**
 * 프로젝트 안에서 1번부터 매기는 표시·주소용 번호. INSERT 때 비워 두면 DB trigger 가 채운다
 * (V77). 새로 만드는 자리에서 값을 계산해 넣지 말 것.
 */
@Column("number") val number: Int? = null
```

`qa_try` · `qa_run` · `issue` 는 `@Column("project_id") val projectId: Long? = null` 도 함께 더한다.
이 셋은 INSERT 때 **값을 실어야 한다**(trigger 가 채우는 것은 `number` 뿐이고, `project_id` 는
NOT NULL 이다). 부모에서 읽어 넣는다 — qa_try 는 test_scenario, qa_run 은 test_run, issue 는 qa_try.

## Repository

범위 안 번호로 한 행을 찾는 메서드를 더한다. 이름은 이 모양으로 통일한다.

```kotlin
@Query("SELECT * FROM qa_try WHERE project_id = :projectId AND number = :number")
suspend fun findByProjectIdAndNumber(projectId: Long, number: Int): QaTryEntity?
```

접근 제어는 지금과 같다 — 프로젝트 참여 여부는 `ProjectAccessService.isMember` 또는 기존
`findAccessible*` 조인이 판단한다. **번호로 찾는다고 해서 참여 확인을 빼지 말 것.**

## DTO

응답에 `number` 를 싣는다. 기존 `id` 는 **지우지 않는다** — `/api/sdk/*` 와 `/internal/*` 이 계속
PK 를 쓰고, 브라우저 경로도 한 릴리스는 두 벌로 간다.

```kotlin
data class QaTryResponse(
    val id: String,      // 그대로 둔다
    val number: Int,     // 새로 싣는다
    ...
)
```

## 경로

이미 프로젝트 스코프인 컨트롤러는 `@PathVariable` 의 **뜻만** 번호로 바꾼다. 경로 문자열은 그대로다.

전역 경로는 프로젝트 스코프 쌍을 **추가**한다. 기존 경로는 지우지 않는다.

| 지금 (남긴다) | 새로 (번호) |
|---|---|
| `/api/qa-tries/{id}` `/messages` `/cancel` `/logs` `/issues` `/events` | `/api/projects/{projectId}/qa-tries/{number}/…` |
| `/api/qa-runs/{id}` `/cancel` | `/api/projects/{projectId}/qa-runs/{number}/…` |
| `/api/issues/{id}/resolve` `/reopen` | `/api/projects/{projectId}/issues/{number}/…` |
| `/api/test-scenario/{id}` PUT · approve · delete | `/api/projects/{projectId}/test-scenario/{number}/…` |

**`/api/sdk/*` 와 `/internal/*` 은 건드리지 않는다.** Unity SDK 와 agent-server 는 PK 를 계속 쓴다.
경로에 `{projectId}` 가 있어도 그것은 프로젝트 PK 다 — 프로젝트는 이번에 번호를 받지 않는다.

## 화면에서 지울 것 (프론트 트랙)

| 위치 | 지금 | 바꿀 것 |
|---|---|---|
| `contentMap/SceneGraphInspector.tsx:130` + `i18n/messages/contentMap.ts:171,407` | `씬 id` 필드 | **필드째 삭제** (`scene.name` 이 이미 유일하고 위에 있다) |
| `contentMap/SceneGraphInspector.tsx:261` + `contentMap.ts:190,423` | `능력 {capabilityId}` | `capability.number` |
| `contentMap/EvidenceScanPanel.tsx:234` + `contentMap.ts:50,297` | `문서 {documentId}` | `document.number` |
| `knowledge/KnowledgeInspector.tsx:290` + `messages/knowledge.ts:101,220` | `화면 #4242` | `screen.number` |
| `knowledge/KnowledgeInspector.tsx:146,359` | `#{node.id}` | **표시 삭제** |
| `knowledge/KnowledgeInspector.tsx:216` | `#{createdByQaTryId}` | qa_try `number` |
| `qa/QaTryPage.tsx:130` · `QaTryPanel.tsx:311` · `DashboardSection.tsx:127` · `QaHistorySection.tsx:93` | `QA Try #{id}` | qa_try `number` |
| `DashboardSection.tsx:153` | `#{issue.qaTryId}` | qa_try `number` |
| `qa/QaLogTimeline.tsx:140,209` + `data-log-id` · `aria-labelledby` | `#{log.id}` | qa_log `number` (실행 안 순번) |
| `projects/GameInstanceDetailPage.tsx:119` | `instance.id` | `instance.number` |

`GameInstanceDetailPage.tsx:49-59` 의 "목록 받아서 find" 우회는 지운다 — 번호로 직접 조회가 된다.

## 검증

- 서버: `./mvnw test` (테스트 131 파일). `OpenApiSnapshotTest` 가 경로를 스냅샷으로 들고 있으므로
  경로를 더하면 스냅샷도 갱신해야 한다.
- 프론트: `export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH"; unset -f node npm npx 2>/dev/null; npm test` 와 `npm run typecheck`.
  lint 는 저장소 전체에 돌리면 `.worktrees/` 때문에 죽는다. 바뀐 파일만 `npx eslint <paths>`.
- 테스트 이름은 `` fun `...`(): Unit = runBlocking { `` 형태여야 한다. `: Unit` 을 빠뜨리면 JUnit 이
  조용히 건너뛴다(0 tests run).
