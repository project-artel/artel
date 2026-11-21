# 2026-10-28 — 프로젝트별 TC 식별 번호 추가

- Date: 2026-10-28
- GitHub Issue: None (기존 서버385/home232 후속)
- Status: Draft

## Goal
프로젝트마다 TC-001부터 독립적으로 영구 번호를 부여한다. 같은 프로젝트 안에서만 유일하고 정렬·필터·버전·삭제에 따라 변경하거나 재사용하지 않는다.

## Non-goals
기존 내부 ID/URL/API 도구 인자 교체, 프로젝트 간 전역 표시번호 유일성, 기존 사용자 issue 제목 일괄변경.

## Context / Constraints
사용자가 프로젝트 안에서만 유일한 번호임을 명시했다. 전역 DB ID padding은 잘못된 접근이므로 미커밋 표시작업을 수정한다. DB번호·공통조회API가 source of truth. 문자열로전달하여큰정수손실방지. 같은TC모든버전은같은번호. TC가삭제돼도QA이력에서원래표시번호조회가능.

## Approach (Checklist)
- [ ] **Step 0: Recon** 기존렌더러·TC쓰기경로·projectworkspace경계확인. 계획Fast/Medium/Heavy재검토.
- [ ] **Step 1: Implementation** 서버V147.1 additive test_case_identifier(test_case_id PK,project_id,case_number positive,UNIQUEproject/number)와project counter. TC FK는삭제후mapping보존위해두지않는다. 기존TC및qa_case_attempt의삭제TC도project별내부id순서로backfill. counter=max번호로초기화. BEFORE INSERT test_case trigger가project counter atomic upsert allocation 후mapping생성하여모든쓰기경로보장. idempotent같은TC는기존번호유지,project이동/ID재사용은금지. 삭제후다음새TC는계속증가. rollback시번호재사용금지(트랜잭션실패로소비되지않은번호는사용된번호가아님). memberonly GET /api/projects/{projectId}/test-case-identifiers returns array {testCaseId:string,caseNumber:string} 전체(삭제mapping포함).
- [ ] home은공통project provider에서mapping한번조회해실제caseId→project번호→TC-001포맷. loading/error에서전역ID나ordinal로추정하지않고TC-…표시·오류retry. provider는workspace전체(챗/deep routes포함)를감싸고TEST_CASES변경시재조회,프로젝트별state격리·abort/sequence처리. 목록/시트/호버/검토탭/QA기록/시나리오/issueTC링크가같은mapping사용. count/일반step순서·APIpayload값은유지. ID검색은mapping표시번호와기존원본id 둘다지원.
- [ ] **Step 2: Tests** 서버기존backfill/같은프로젝트중복금지/서로다른프로젝트001공존/동시생성/삭제후새번호비재사용/삭제된TC이력mapping/프로젝트권한. homeformatter·프로젝트mappingsearch·반복TC/정렬/순서와실제번호차이·mapping없는상태거짓ID금지. 전체home test/build/lint,서버focusedtests/package/Flyway검사. project1과fixture110147이각각TC-001보이는실제화면캡처. 별도fixture에서새TC만들고삭제후다음번호증가확인(사용자데이터변경없음).
- [ ] **Step 3: Rollout / Rollback** 기존server385/home232에commitpush와캡처보존. server먼저적용. 번호table은rollback에도보존. 실제사용자QA진행중재시작금지. SDK/agent/CLI rawID계약은유지.

## Validation
- **Commands to run:** 서버focused integration/package/Flyway검사,home전체test/build/scopedeslint,diffcheck,브라우저.
- **Expected output:** 서로다른프로젝트가독립TC-001,TC-002를갖고삭제·필터·재검증에도번호가유지된다.

## Risks & Rollback
- **Risks:** counter경합/삭제번호재사용/다른프로젝트표시mapping오염/과거deletedTCmapping유실/ordinal혼동.
- **Rollback steps:** codecommitrevert,additive번호mapping/counter유지.

## Open Questions
없음. 사용자명시프로젝트범위번호. 기존issue제목은사용자문자열을변경하지않고TC연결label을신규형식으로표시한다.

## 범위 수정
이전전역ID포맷계획은폐기했다. 이전UI변경은미커밋상태이며새provider기반으로전환한다.

## 프로젝트 번호 계획 검토 반영
FAST NONPASS 해결: migration transaction에서 test_case 쓰기 lock을먼저획득하고backfill/counter/trigger설치를원자적으로완료한다. DB에서 project이동과삭제된ID재사용거절,같은ID idempotent/ONCONFLICT는기존번호유지,경합에따른공백허용을검증한다. MEDIUM PASS 권고반영: 과거삭제TC는qa_case_attempt뿐아니라project연결이유효하고양의BIGINT로검증된qa_log.payload.case_id도backfill한다. 현재TC소유프로젝트를우선하며다른프로젝트의잘못된로그로번호mapping을생성하지않는다. 소속을판단할수없는모호한과거기록에는번호를지어내지않는다.

## 구현·검증 완료
프로젝트별 번호 발급·전체 mapping API·공통 화면 provider 구현 완료. 기존 PR의 시연 제거 변경 위에서 서버 신규 11개·전체 migration 120개 적용, 화면 전체 1,554개·build·변경 파일 lint 통과. 두 프로젝트의 독립 TC-001과 새 내부 ID 6의 TC-002 발급을 실제 UI로 확인하고 캡처 7장 저장. 삭제 후 비재사용은 integration test로 확인했으며 실제 사용자 TC 삭제는 실행하지 않았다. 기존 server PR385(27830e1e), home PR232(49b57a9)에 push·문서·캡처 반영 완료.

공유 작업 폴더 초안 정리는 자동 승인 검토가 거절해 실행하지 않았다. 다른 작업 커밋을 보존한 독립 작업 폴더에서 기존 원격 PR 브랜치로 fast-forward push했다. 후속 작업은 .work/tc-identifiers-handoff.md를 따른다.
