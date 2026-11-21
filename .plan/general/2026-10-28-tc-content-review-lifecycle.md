# 2026-10-28 — TC 내용 수정과 재검증 상태 추가

- Date: 2026-10-28
- GitHub Issue: None (기존 QA 평가 작업 ARTEL-1271 후속)
- Status: Implemented

## Goal
사람의 TC_CONTENT_ISSUE 평가로 TC 수정 필요 상태를 설정하고 이유·해당 attempt 영상 링크를 표시한다. 내용 변경 후 재검증 필요, 수정된 내용을 사용하는 새 검증의 확정 결과로 완료한다. 기존 서버385/home232 PR에 반영한다.

## Non-goals
신규 issue 자동 생성, 기존 VerificationStatus 변경, agent 자동판단으로 TC문제 확정, 기존 영상 보관기간 연장.

## Context / Constraints
원본 agent verdict는 그대로 유지한다. 사람 평가 decision에 TC_CONTENT_ISSUE를 추가하되 FP/FN에는 포함하지 않는다(검토건수에는 포함). 버전별 검증결과와 TC 내용 품질은 별도 축이다. 기존 migration143/144의 review-history/issue 연동을 보존한다. 현재 branch와 Jira 재사용.

## Approach (Checklist)
- [x] **Step 0: Recon** 기존 review/attempt/schema와 TC 수정 경로 확인. 계획 Fast/Medium/Heavy 검토.
- [x] **Step 1: Implementation** 서버 additive migration147로 per-TC content review 행(state NEEDS_REVISION/NEEDS_REVALIDATION/READY,source log와 reason,보고 시 내용,수정시각) 저장. 기존 review decision 허용을 확장하고 TC내용문제에서는 원본게임판정을 덮어쓰지 않는다. TC프로젝트 접근 검증, review수정이력 보존. GET /api/projects/{projectId}/qa-evaluation/case-content-reviews?testCaseId= 선택 필터. 응답 array: testCaseId,state,note,logId,attemptId,qaTryId,qaRunId,updatedAt,revisedAt,resolvedAt(문자열 nullable except id/state/updatedAt). member만 접근.
- [x] DB lifecycle은 모든 내용수정 경로에서 적용한다. scene/precondition/step/expected_value/condition/expected_items/functions 실제 변경 시 NEEDS_REVALIDATION. 무변경save와 verificationStatus수정만으로는 전환하지 않는다. 재검증은 수정시각 이후 시작, 현재TC내용과 snapshot일치, PASSED/FAILED만 허용. 예전시도/수정전내용/inconclusive/interrupted/미시작 legacy는 완료시키지 않는다. 여러 보고가 있으면 기존 review revision을 보존하며 현재 source만 교체; source 아닌 평가 철회는 무시. 현재 source를 정상평가로 수정하면 내용수정 전 NEEDS_REVISION만 철회한다. 내용을 고친 뒤 대기 상태는 과거평가 수정으로 해제하지 않는다. 삭제TC는 역사평가 보존하되 상태변경 불가. 게임실패issue는 TC내용문제에서 유효실패로 계산하지 않는다.
- [x] home은 verdict와 별도 ReviewDecision union을 사용하고 사람평가 radio·history·TC탭에 TC내용문제를 표시한다. API별 content 상태를 불러와 TC library 행/TC상세에 상태표시, 사유·원본영상 attempt직접링크 제공. 기존 TC 편집 저장 시 상태 갱신. 재검증 버튼은 수정필요에서는 편집으로, 재검증필요에서는 해당TC로 기존 QA 실행 설정을 열어 새검증 진행. 실행은 사용자가 확인한다. 사용자 요청 labels만 추가하고 기존 semantic styles사용.
- [x] **Step 2: Tests** DB migration/integration: report·reason/history, real edit/no-op, old/inconclusive/mismatched attempt 금지, fresh definitive clear, review철회·다른source·권한·reliability·issue 기존연동. home parse/SSR/회귀 tests/build/lint. 실제 또는 명확히 표시한 isolated fixture로 브라우저 상태/영상링크/편집/재검증 설정 캡처. 실QA 수행 여부를 구분한다.
- [x] **Step 3: Rollout / Rollback** 서버385/home232에 각commit/push, API변경은 서버우선 의존성 명시. 캡처와 한국어 docs·집계정의 업데이트. 파괴적 DBrollback 없이 code revert, additive행 보존. 실제 실행 중인 QA가 있으면 재시작으로 중단하지 않는다.

## Validation
- **Commands to run:** server Maven focused/integration tests/package, home npm test/build/scoped eslint, git diff --check.
- **Expected output:** 사람TC문제→수정필요→실제내용변경→재검증필요→수정후새확정검증→READY. 이유·영상 출처 보존.

## Risks & Rollback
- **Risks:** 과거시도 상태덮어쓰기, 잘못된 snapshot, 타입호환, DB경합, 다른프로젝트 링크.
- **Rollback steps:** 각repo commit revert, additive schema는 보존.

## Open Questions
없음. 이유는 기존 원칙대로 선택입력이며 영상이 만료돼도 사유·링크·상태 이력은 남는다.

## 1차 검토 반영
Fast NONPASS 두 항목 반영: 과거 내용 snapshot의 TC_CONTENT_ISSUE는 review 이력·이유·영상에만 남기고 현재 상태를 변경하지 않는다. 내용 수정/완료/재보고/철회 경합은 testcase행 lock 및 revision 또는 내용 조건부 UPDATE로 직렬화하여 새 수정을 덮어쓰지 않는다. 동일 검증결과로 반복 완료하지 않는다. Medium PASS: lifecycle은 DB 함수가 단독 소유하고 service는 권한·저장·조회만 담당한다. 기존 issue함수와는 분리한다. 과거평가·동시편집 회귀 테스트를 추가한다.

## 구현 중 보완
지도 생성 TC는 기존 editor의 identity-only update가 QA의 build snapshot에 반영되지 않아 재검증할 수 없었다. update request의 optional gameBuildId로 선택한 build snapshot만 수정하고 다른버전은 보존한다. home Library selectedBuildId→Sheet editGameBuildId→Editor payload로 전달한다. manual은 기존identity수정 유지. scope없는 과거client동작은 보존한다. latestidentitysync후 실제내용변경 trigger로 lifecycle전환한다. two-build snapshot보존과 agentcomposition 최신내용 회귀를 추가한다.

## 최종 검증
서버64·home1561 PASS, package/build/lint/diff-check/Flyway충돌검사 PASS. 초기독립review P1 legacyBoolean매핑·issue파싱수정후양쪽PASS. 별도fixture110147에서UI평가→수정필요→내용수정→재검증필요→대상TC선택QA설정 확인. 새start/report합성PASSED로READY확인(실게임QA아님, fixture영상없어sourceattempt링크확인만). 캡처10개docs/images/tc-content-review보존. 로컬V142누락확인후일시out-of-order로142·147적용새JAR정상시작. 기존사용자project1평가내용유지.
