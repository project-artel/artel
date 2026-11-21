# 2026-10-23 — SDK PR #154–#158 stack 충돌 해결

- Date: 2026-10-23
- Jira: ARTEL-1232, ARTEL-1233
- Status: Complete

## Goal
#154 → #155 → #156 → #157 → #158의 base 관계를 유지하며 충돌을 해결한다.

## Non-goals
PR merge, draft 상태 변경, 기존 checkout의 수정 파일 변경.

## Context / Constraints
#154–#156은 갱신됐으나 #157–#158은 이전 commit 기반이다. 별도 sdk-stack-158 checkout에서 처리한다.

## Approach (Checklist)
- [x] **Step 0: Recon** 원격 PR 관계와 commit 확인.
- [x] **Step 1: Implementation** #157 고유 commit을 새 #156 위로 rebase하고 로그아웃 시 project name 삭제와 identity 파일 삭제를 모두 보존. #158 고유 commit을 그 위로 rebase.
- [x] **Step 2: Tests** range-diff, 충돌 marker 검사, Unity EditMode 및 PlayMode 실행.
- [x] **Step 3: Rollout / Rollback** 원격 SHA를 재확인한 뒤 두 브랜치를 explicit force-with-lease로 갱신하고 5개 PR mergeability 확인.

## Validation
- **Commands to run:** git range-diff, git diff --check, Unity 2022.3.34f1 -runTests.
- **Expected output:** 기존 기능 변경 보존, conflict 없음, 테스트 통과.

## Risks & Rollback
- **Risks:** 작업 중 원격 변경은 lease로 보호. 충돌 한쪽 선택으로 로그아웃 동작이 누락되지 않도록 검증.
- **Rollback steps:** 기존 #157 9280453697123d685d591021fe7af1d8046e9351, #158 b3f6506f718f31c5063016b305b4edee9e85a6bd 보존.

## Open Questions
없음.

## 결과
- #157: 8d3eebb, #158: e2077e3. atomic push 및 explicit force-with-lease로 반영.
- #158 overlay의 프로젝트 이름 표시와 Input System 안내를 모두 보존.
- range-diff, diff --check, 전체 stack ancestor 검사 통과. pair-review PASS.
- Unity 2022.3.34f1: EditMode 565/565, PlayMode 87/87 통과.
- 결과 파일: sdk-stack-158-tests/editmode-results.xml, sdk-stack-158-tests/playmode-results.xml.
