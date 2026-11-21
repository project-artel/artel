# 2026-10-29 — SDK script reload 후 초기화 복원 수정

- Date: 2026-10-29
- Jira: None
- Status: Complete

## Goal
Unity script reload 뒤 Manager와 Overlay의 runtime 객체를 복원하고 반복 null 예외를 막는다.

## Non-goals
게임 코드 변경, 전역 assembly reload 잠금, UI 문구 변경은 포함하지 않는다.

## Context / Constraints
`.work/qa-websocket-sdk`의 변경을 runtime package에도 적용한다. 기존 transport 주입 순서와 중복 manager 제거를 유지한다.

## Approach (Checklist)
- [x] **Step 0: Recon** 오류 위치와 Unity lifecycle 확인.
- [x] **Step 1: Implementation** runtime 소유 표시의 직렬화 제외, OnEnable 복원, overlay 재초기화와 종료 보호.
- [x] **Step 2: Tests** runtime 손실 뒤 프레임 처리와 재활성화, 중복 manager, 반복 종료 검증.
- [x] **Step 3: Rollout / Rollback** 로컬 runtime package 동기화. 배포는 하지 않는다.

## Validation
- **Commands to run:** Unity 2022.3.62f3 PlayMode 및 EditMode 테스트.
- **Expected output:** 초기화 복원 뒤 Update와 StopTransport에 null 예외 없음. 기존 테스트 통과.
- **Results:** Unity 2022.3.62f3 PlayMode 94개 통과, EditMode 577개 통과와 기존 Ignore 1개. 실제 EditorUtility.RequestScriptReload 후 runtime과 overlay 복원, StopTransport 2회 및 재활성화, 두 번째 Play/Stop까지 오류 없이 완료. 수정 전 회귀 테스트는 runtime 소유 표시의 직렬화 검증에서 실패했다.
- **Evidence:** `.work/qa-websocket-sdk-unity/results-lifecycle-playmode.xml`, `results-lifecycle-editmode.xml`, `lifecycle-reload.log`. 이는 로컬 Unity lifecycle 검증이며 실제 서버 연결 복구 E2E 검증은 포함하지 않는다.

## Risks & Rollback
- **Risks:** script reload는 실행 중인 연결과 coroutine을 끊는다. 복원 시 저장된 세션으로 재등록한다.
- **Rollback steps:** 이번 lifecycle 변경만 되돌리고 기존 작업은 보존한다.

## Open Questions
- 없음.
