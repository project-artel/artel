# 2026-10-28 — QA 실행 TC 판정 표시 복구

- Date: 2026-10-28
- Jira: ARTEL-1271 (기존 home PR #228 재사용)
- Status: Implemented

## Goal

QA 중 왼쪽 TC 목록에서 TC의 실제 판정을 초록 체크·실패·판단 불가로 표시하고 통계를 갱신한다. QA 6에 저장된 `STATUS {case_id, attempt_id, case_outcome, status}` 판정 5개(통과 4·판단 불가 1)를 UI가 읽지 못하는 회귀를 고친다.

## Non-goals

report_step 복원, 참고 step을 완료한 것으로 꾸미기, 원본 판정·사람 평가·서버 판정 변경, TC 배치·전체 디자인 변경은 하지 않는다.

## Context / Constraints

현재 deriveQaProgress는 STATUS.step만 읽고, deriveCaseVerdicts는 CASE_VERDICT만 읽는다. FREE 행은 TC지만 step 번호 기반 progress로만 그린다. 기존 step 로그·CASE_VERDICT와 expectation grade는 호환해야 한다. 실제 신규 TC 판정은 step이 없고 case_id로 식별한다.

## Approach (Checklist)

- [x] **Step 0: Recon** 실제 QA 6 DB 이벤트와 parser·QaScenarioSteps·QaScenarioRail·QaRunPage·기존 semantic 상태색을 확인했다.
- [x] **Step 1: Implementation** `STATUS`의 case_outcome(PASSED/FAILED/INCONCLUSIVE)과 case_id를 읽는 공통 TC report map을 만든다. 신규 TC report가 없을 때만 기존 CASE_VERDICT를 fallback으로 읽고 reference step STATUS는 TC 판정으로 취급하지 않는다. 같은 TC는 마지막 검증 시도가 이기며 표시 순서는 scenario 순서다. 실행 terminal result·관계없는 log·잘못된 outcome을 무시한다.
- [x] FREE에서는 case_id를 scenario row에 대응시켜 현재 progress·glyph·log jump·총 판정 수를 갱신한다. INCONCLUSIVE는 별도 상태/기존 '판단 불가' 문구를 써서 pending·실패와 구분한다. expectation grade는 확정된 통과/실패에만 계산한다. 다른 시나리오의 TC는 집계하지 않는다.
- [x] ORDERED에서는 TC report를 TC header에만 표시하고 참고 step progress는 새로 만들지 않는다. 기존 step-only 기록은 기존대로 보인다. TC의 report log ID로 이동할 수 있게 한다. 기존 저장 TC 상태 표시는 의미를 유지한다.
- [x] **Step 2: Tests** 실제 wire fixture, 순서가 다른 case_id, 재검증 마지막 결과·판단 불가, 무관한 run/step log·중복 reference·잘못된 ID/outcome, live log 추가와 terminal/reload, 기존 step 회귀, TC header·FREE glyph/summary를 검증한다. 변경 TSX에 React 체크와 scoped lint·typecheck·전체 tests·build를 적용한다.
- [x] **Step 3: Rollout / Rollback** 로컬 Vite에 적용하고 기존 home PR #228에 commit/push한다. 서버·SDK restart와 DB 변경은 없다. rollback은 해당 home commit만 되돌린다.

## Validation

- **Commands to run:** node test hooks 기반 qaProgress 및 TC report 테스트, npm run typecheck/test/build, 수정 파일 eslint.
- **Expected output:** QA 6의 TC 1·2·3·5는 passed, TC 4는 inconclusive이며 reported=5·passed=4·failed=0. ORDERED 참고 step의 완료는 만들지 않는다.

## Risks & Rollback

- **Risks:** case_id와 step 번호 혼동, 예전 CASE_VERDICT가 새 판정을 덮기, INCONCLUSIVE를 실패·미검증으로 집계하는 문제, 같은 TC의 중복 reference가 통계를 부풀리는 문제를 경계한다. 기존 history window 밖의 판정은 지어내지 않는다.
- **Rollback steps:** home UI commit만 revert한다. 서버·원본 로그·평가 이력은 유지한다.

## Open Questions

없음. 새 문구는 기존 '판단 불가'를 재사용한다.

## Result

- home commit: `0dba11c`, 기존 draft PR #228에 push 완료.
- 전체 테스트 1,519개 통과. 신규 TC report 및 legacy SSR 회귀 10개 추가.
- typecheck를 포함한 build, 수정 파일 eslint, diff check 통과. pair review PASS.
- 로컬 Vite 5176에서 변경 module 응답 확인. 서버·SDK 재시작이나 DB 변경 없음.
