# 2026-11-03 — Game identity 등록과 변경 이력 및 build·QA 버전 고정 추가

- Date: 2026-11-03
- Jira: ARTEL-1356 (1357 server, 1358 SDK, 1359 home, 1360 agent, 1361 MCP)
- Status: Implemented; draft PRs opened, not merged or deployed

## Goal
attribute·SDK, MCP, 웹에서 game identity를 등록하고 출처와 immutable 변경 이력을 보관한다. build가 선택한 revision을 다른 build의 수정으로부터 분리하고 QA가 실제 사용한 선언을 보존한다.

## Non-goals
운영 배포, 기존 PR merge, fact·rule 관리, 과거 QA에 선언을 추측해서 채우기.

## Context / Constraints
서버는 PR #403(62e87237) 위 후속 작업이다. 나머지 저장소는 origin/develop, MCP는 PR #13 위에서 시작한다. 기존 로컬 변경은 별도 worktree로 보존한다. 새 migration으로 기존 선언을 LEGACY revision과 해당 build binding으로 backfill한다.

## Approach (Checklist)
- [x] **Step 0: Recon** PR #403은 프로젝트·이름별 최신 행을 upsert하며 이력은 없다. QA는 단일 try와 multi-scenario run 경로가 있다.
- [x] **Step 1: Implementation** 서버가 immutable revision과 build binding을 소유한다. 명시적 PUT/DELETE는 build를 지정하고 선택된 revision의 expectedVersion으로 충돌을 검증한다. 최초 등록 expectedVersion=0. revision 번호는 프로젝트·이름별 단조 증가한다. 삭제는 tombstone revision이며 과거 revision은 유지한다. 출처는 인증 principal(MCP JWT 여부) 또는 SDK socket에서 서버가 결정한다. SDK 재전송은 동일 내용이면 no-op, WEB/MCP binding은 건드리지 않는다. SDK에서 제거된 항목은 해당 build의 SDK binding만 tombstone으로 기록한다.
- [x] **Step 1: Implementation** 공통 API: GET /api/projects/{projectId}/game-identities?gameBuildId={id} → {identities:[]}; PUT 같은 경로에 기존 선언 필드+gameBuildId+expectedVersion; DELETE 같은 경로에 name,gameBuildId,expectedVersion. GET /history?name=... → {identities:[]} (삭제 포함). 응답은 기존 필드와 revisionId(string), source(SDK/MCP/WEB/LEGACY), deleted(boolean), createdBy(string|null), createdAt를 포함한다. 수정 후 version은 반환값을 다시 사용한다. build별 목록에서 tombstone은 제외한다. GET에 build가 없으면 프로젝트 최신 목록은 호환 제공한다.
- [x] **Step 1: Implementation** SDK는 [ArtelGameIdentity]를 field/property에서 수집해 GAME_IDENTITY_CATALOG 프레임 {identities:[기존 선언 필드, gameBuildId 제외]}을 DEVICE_CONTEXT 이후 전송한다. name은 실제 DeclaringType.Name.member에서 생성하며 getter는 실행하지 않는다. 서버는 인증된 instance.lastGameBuildId로 build와 project를 정한다. 실패한 수집을 빈 목록으로 보내지 않는다.
- [x] **Step 1: Implementation** QA 시작 시 build binding을 한 번 읽고 선언 전체를 game_identities 배열로 모든 try의 run_config에 저장한다. 단일 try와 multi-scenario run 모두, STARTING 단계부터 보관하고 agent 응답이 덮어쓰지 못하게 한다. 동일 배열을 context.game_identities로 agent에게 전달한다. agent는 snapshot을 record에 저장하고 엔진 지침에 사용하며 최신 프로젝트 선언 재조회로 바꾸지 않는다. 빈 배열은 확정된 빈 snapshot이고 누락은 이전 프로토콜이다.
- [x] **Step 1: Implementation** 웹은 build 상세에 선언 목록·등록·수정·삭제·출처·revision 이력을 제공한다. 현재 build binding과 프로젝트 변경 이력을 구분하고 409 시 재조회한다. MCP 도구는 build 선택과 expectedVersion 및 이력 조회를 지원한다.
- [x] **Step 2: Tests** revision 불변성, 다른 build 격리, 삭제 이력, SDK idempotency와 override 보존, auth 출처 판정, 동시 수정 충돌, 기존 backfill, QA snapshot 전달·보존·빈 배열, 웹 폼과 API 및 렌더 확인, SDK attribute 수집을 검증한다.
- [x] **Step 3: Rollout / Rollback** 서버 migration/API를 먼저 반영하고 SDK/MCP/agent/home을 이어 적용한다. 배포는 이 작업에 포함하지 않는다. rollback 시 immutable 기록은 삭제하지 않고 소비 코드를 먼저 되돌린다.

## Validation
- **Results:** Server103 PASS; Unity EditMode18+PlayMode7 PASS; home1620 PASS, build/lint/desktop+mobile light+dark mock-API browser checks PASS; agent85 PASS; MCP full70 PASS plus final focused52 PASS; CLI421 PASS and existing61 skipped, build/typecheck/changed-file lint PASS. Independent implementation reviews PASS after fixing history output and preview guide prerequisites. Live CLI guide list/show read the published skills commit successfully.
- **Draft PRs:** skills4, orchestration405 (base403), SDK191, home245, agent308 (base305), MCP14 (base13), CLI52. Story ARTEL-1356 links all repository subtasks.
- **Guide scope added by user:** CLI `artel guide list/show [--reference] [--json]`, MCP `skill_guide` tool and `artel_guide` prompt use skills commit `5674a5b885102903281ede87c7ae4ba09e6f6b7b`. The new self-contained skill explains preview SDK/skill installation, attribute declaration, build registration, remote MCP OAuth, web editing, provenance/history and QA snapshots. The real skills CLI interprets a slash branch as a path; the install URL therefore uses `game-identity-guide-preview-20261103` tag.
- **Not verified:** Actual authenticated full-stack Unity QA, development IL2CPP player stripping. Remote CI may still be running; local results above are separate evidence.
- **Commands to run:** 저장소별 실제 package 설정에서 확인한 focused test와 build. 서버 Maven integration tests(Testcontainers), agent pytest, MCP tests, home npm test/build, SDK 기존 도구 기반 C# tests.
- **Expected output:** build A 수정이 B에 영향 없고 QA 시작 이후 변경·삭제·재접속에도 snapshot은 동일하다.

## Risks & Rollback
- **Risks:** 기존 build가 비어 있던 프로젝트 최신 선언을 잘못 상속하지 않게 한다. LEGACY에 없는 과거 이력은 복원할 수 없다. snapshot write와 agent 전달은 같은 읽기 결과를 사용한다.
- **Rollback steps:** 소비 코드부터 revert, revision과 snapshot 데이터는 보존한다.

## Review changes
Fast/medium 모두 삭제한 build binding의 version을 재조회할 수 없다고 지적했다. GET 목록에 includeDeleted=true를 추가해 선택된 tombstone을 함께 반환한다. 웹·MCP는 수정·재등록 전 이 목록에서 expectedVersion을 얻는다. 삭제 후 다른 build 수정이 있어도 해당 build tombstone version으로 재등록할 수 있는 테스트를 추가한다. SDK는 동일 Type.member 충돌을 거절하고 수집 실패 시 전체 목록을 보내지 않는다. 게임 선언을 가져올 때 getter를 실행하지 않는다.

## Open Questions
없음. 동시 수정은 409로 처리하며 전체 build를 영구 잠그는 기능은 추가하지 않는다. build binding을 명시적으로 변경할 수 있지만 다른 build와 기존 QA snapshot은 유지한다.

## MCP·CLI·skills 안내 이름 통일
- 사용자 요청에 따라 표시 이름을 `변수 메타데이터`(en: `Variable metadata`)로 통일했다. MCP 도구 설명·응답·prompt, skill 설명·제목·웹 메뉴 안내, catalog와 README를 수정했다. 기존 topic ID·attribute·API·도구 이름은 유지한다.
- CLI·MCP는 skills commit `4a9dbc4b8e89950b3a8c1756fd4f2b1b07e2031e`를 함께 읽는다. 설치 URL은 새 고정 tag `variable-metadata-preview-20261103`를 사용한다.
- 기존 CLI52·skills4는 merge된 상태를 확인해 후속 draft PR CLI53·skills5를 만들었고 MCP14는 갱신했다. 이번 후속 변경은 merge·배포하지 않았다.
- 검증: MCP 전체71 PASS·ruff PASS, CLI guide4 PASS·build·변경 파일 ESLint PASS. 실제 skills 목록6개와 CLI list/show에서 새 제목·본문·고정 revision 조회를 확인했다.

## PR CI 수정
- 2026-11-04: CLI53의 테스트 배열 직접 접근에서 발생한 TS2532를 `toContainEqual`로 수정했다. typecheck·전체 lint·build, 테스트421 PASS·기존61 skipped, GitHub Actions CI PASS를 확인했다.
- SDK191의 실패 작업은 테스트 전 Unity 라이선스 인증401이었다. 재실행 후 모든 matrix 작업 PASS를 확인했다.
- 서버405는 다른 PR의 `V174__store_game_facts_and_rules.sql`과 번호가 겹쳐 Jenkins UNSTABLE이었다. 새 migration을 V175로 이동하고 backfill test target과 주석을 갱신했다. 최신 refs 충돌 검사와 PostgreSQL base→branch upgrade·validate PASS. commit `9a9b5cba7856111a0f1c4f0a459319159e189129`의 Jenkins #5 SUCCESS를 확인했다.

## ArtelMetadata attribute 이름 적용
- 사용자 후속 요청으로 새 공개 attribute를 `[ArtelMetadata]`로 변경했다. `[ArtelGameIdentity]`는 `Obsolete` 경고를 내는 호환 alias로 남기며 두 이름이 같은 수집·검증·wire 경로를 사용한다. getter 실행 없이 `CustomAttributeData`를 읽는다. 서버 wire·저장 식별자는 유지한다.
- SDK191에 구현·README·호환 회귀 테스트를 반영했다. 작업 중 merge된 최신 develop 위에 변경을 다시 적용한 commit `61263a8adeabba180e51f21ad2d72ab7fb6f87c9`에서 Unity EditMode19·PlayMode7 PASS를 확인했다.
- skills5 원문·예제를 갱신하고 `metadata-attribute-preview-20261104` tag와 commit `475b6a1b79bad90a4c89d0b76a5d1fc1c660addf`를 게시했다. 실제 skills 목록6개 및 CLI 원문에서 ArtelMetadata·deprecated alias 안내를 확인했다.
- CLI53은 작업 중 merge되어 후속 CLI54를 생성했다. MCP14는 PR13을 거쳐 현재 PR9 branch에 merge되어, 최신 PR9 head 위 후속 MCP18을 생성했다. CLI54·MCP18은 같은 새 skills commit을 읽는다. CLI typecheck·전체 lint·guide4·build PASS, MCP 전체79·ruff PASS.
- 최종 원격 CI 확인: SDK191 최신 attribute commit의 Preflight와 Unity matrix8개 모두 SUCCESS, CLI54 GitHub Actions SUCCESS, MCP18 Jenkins PR·branch SUCCESS. 서버405·웹245·agent308도 SUCCESS. skills5는 CI가 없으며 실제 설치 목록·CLI 원문 조회로 확인했다. 새 CLI54·MCP18은 draft이며 직접 merge·배포하지 않았다.
- 이후 MCP 기반 PR9에 PR17의 expected_version 생략 지원이 merge되어 README 충돌을 해결했다. 새 등록 동작을 보존하고 ArtelMetadata 안내를 변수 메타데이터 절에 적용했다. 최종 commit `21e18567da5be99d2b7210b7d55dea41e5a50b4f`에서 pytest81 PASS·ruff PASS, Jenkins PR18 #2 SUCCESS·병합 가능을 확인했다.

## 프로젝트 목록 화면과 내비게이션 추가
- 사용자 후속 결정: 화면 명칭은 `변수 메타데이터`(en: `Variable metadata`)로 통일한다. 일반 목록/table과 build 상세 card에서 선언 version 번호를 숨기고 변경 이력에서만 확인한다. 내부 game_identity/API/attribute 이름과 optimistic concurrency 및 QA snapshot 데이터는 유지한다.
- 사용자 요청으로 PR245에 `/projects/:projectId/game-identities` 목록 route와 데이터 그룹 메뉴를 추가한다. `?build=`로 선택을 유지하고 기존 BuildSwitcher로 build를 전환한다.
- 최신 build를 기본으로 선택하되 잘못된 build query는 다른 build로 자동 대체하지 않는다. 로딩·실패·build 없음·선언 없음 상태를 구분한다.
- GameIdentityPanel을 재사용하고 전용 화면에는 비교 가능한 table 목록을 제공한다. 등록·수정·삭제·재등록·이력 동작과 expectedVersion은 그대로 사용한다. build 변경은 panel key를 바꿔 이전 build의 editor/history 상태를 초기화한다.
- route/menu 회귀 tests와 전체 build/test/lint를 확인하고 mock API를 연결한 실제 프로젝트 shell에서 내비게이션 진입·build 변경·뒤로 가기·mobile/light/dark를 확인한다. 전체 shell 캡처를 PR 본문에 추가한다.
- 완료: 전체 tests1621 PASS, build/targeted ESLint/diff check PASS, 독립 critic PASS. 실제 App shell+mock API로 active nav, build 전환/back, 이전 editor 초기화, invalid build 명시적 최신 build 복구, 이력, 빈 build/선언·조회 실패, ko/en, desktop/mobile light/dark, 페이지 overflow 없음 및 mobile 키보드 가로 스크롤을 검증했다. 전체 shell 캡처 6장을 PR245에 추가했다. API fixture의 배경 endpoints도 실제 array 계약에 맞췄으며 실제 로그인된 서버 연동은 별도 미검증이다.
