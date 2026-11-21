# 2026-10-28 — TC 판정 검토의 가로 스크롤 선택 바 적용

- Date: 2026-10-28
- Jira: ARTEL-1271 (기존 home 통합 PR #232 후속)
- Status: Implemented

## Goal

TC 판정 검토의 dropdown을 항상 보이는 가로 스크롤 TC 선택 바로 바꾼다. 선택한 TC의 판정·영상·평가를 함께 전환하고 영상은 해당 구간 0초·정지에서 시작한다.

## Non-goals

QA 질문 정책 구현(별도 계획), 서버/SDK/API 변경, 영상 구간 선택 dropdown 변경, 평가 자동 저장이나 데이터 수정.

## Context / Constraints

현재 CaseEvaluationPanel의 AttemptList가 검증 시도를 select로 렌더링한다. API는 최근 시도 100개와 다음 페이지를 제공하고 URL attempt 직접 링크도 지원한다. 같은 TC의 반복 시도를 잃으면 안 된다. 기존 Blueprint Paper tokens·판정 색·접근성 문구를 재사용한다.

## Approach (Checklist)
- [x] **Step 0: Recon** 실제 renderer·선택 state·영상 key·API·스타일 확인.
- [x] **Step 1: Implementation** 독립 CaseAttemptPicker에서 TC ID별 그룹을 자연수 순으로 정렬한 가로 tabs를 그린다. 각 tab에 TC ID·검증 절차 요약·agent 판정과 사람 검토 상태를 표시한다. TC 전환은 최신 시도를 선택하며, 이미 선택된 TC 재클릭은 현재 시도를 유지한다. 같은 TC의 여러 시도는 별도 가로 button 목록으로 선택한다. 페이지 추가와 직접 링크된 오래된 시도를 보존한다. 새 copy를 만들지 않고 기존 labels를 재사용한다.
- [x] 선택 tab은 aria-selected·tabindex·tabpanel 연결과 좌우/Home/End 키를 지원하고 선택 항목이 가로 바 안에 보이게 한다. 좁은 화면도 dropdown으로 되돌리지 않고 가로 overflow만 허용한다. 실제 검토 내용은 기존 attempt key를 유지해 영상·평가 상태를 분리한다.
- [x] **Step 2: Tests** SSR에서 TC 중복 제거·ID 자연 정렬·판정/평가 상태·선택·반복 시도 접근·dropdown 제거·tabpanel 연결을 검증한다. 전체 tests/typecheck/build와 수정 파일 lint, 실제 QA6 TC 전환·영상0초·keyboard·모바일 캡처를 확인한다.
- [x] **Step 3: Rollout / Rollback** 기존 home draft PR #232에 push하고 캡처를 repo/PR에 보존한다. localhost5176은 통합 home worktree의 build 결과를 기존 로그인 세션으로 검증한다. orch/agent/Unity는 중단하지 않는다. rollback은 이번 home commit revert.

## Validation
- **Commands to run:** npm test/build, 변경 파일 eslint, git diff --check, 브라우저 QA6 선택/keyboard/overflow 확인.
- **Expected output:** TC1~5가 가로 bar에서 선택되고 현재 TC만 selected. 재시도는 별도 선택 가능. 전환 직후 영상0초·정지. 모바일에서 page 가로 overflow 없음.

## Risks & Rollback
- **Risks:** 반복 시도 소실, 선택 TC 재클릭으로 평가 시도 변경, bar 스크롤로 page 위치가 움직이는 문제, deep-linked older attempt 누락.
- **Rollback steps:** 해당 home commit revert, 기존 local Vite worktree로 복귀.

## Open Questions
- 없음. 사용자가 기존에 요청한 가로 TC 선택 UI 복원이다.

## Review 반영

Fast/Medium PASS. 오래된 직접 링크 시도가 options 맨 앞에 있어도 TC 전환 시 최신 createdAt·ID 기준 시도를 선택한다. 선택 TC tab의 agent/사람 상태는 현재 선택한 시도와 일치시키고 다른 TC tab만 최신 시도를 표시한다. 해당 deep-link/재시도 회귀를 추가한다.

## 실행 결과

전체 테스트 1,551 PASS, build/ESLint/diff-check PASS. 실제 QA6에서 TC 전환, 영상 0초·정지, Home/End, 390px 가로 스크롤을 확인했다. 캡처 6개를 home docs/images/qa-tc-picker에 보존했다. Windows localhost 연결 문제로 로컬 static preview와 기존 API proxy를 사용했고 orch/agent/Unity는 유지했다.
