# 2026-10-28 — TC 영상 전환 시 재생 진행도 초기화 수정

- Date: 2026-10-28
- GitHub Issue: None (ARTEL-1271 / PR #228 follow-up)
- Status: Implemented

## Goal

TC 변경 시 해당 검증 구간 처음에서 정지하고 진행도와 시간을 0부터 표시한다. 사용자 최종 설명은 장면은 바뀌지만 진행도가 남는다는 것이다. 실제 QA 6에서 기존 video controls가 TC 구간이 아닌 60초 원본 segment 시간을 표시하는 것을 확인했다.

## Non-goals

서버의 영상 분할·변환 변경, 새 영상 생성, 평가 저장 동작이나 화면 배치 변경.

## Context / Constraints

CaseEvaluationPanel의 VideoEvidence는 clipSegments의 from/to를 loadedmetadata에서 적용하지만 native controls는 전체 segment 시간을 표시한다. 검증 시도는 여러 segment에 걸칠 수 있다. 60초 URL 갱신에는 같은 TC의 현재 위치와 재생 상태를 유지해야 한다.

## Approach (Checklist)
- [x] **Step 0: Recon** 실제 QA 6의 TC 전환과 native 재생 시간을 확인했다.
- [x] **Step 1: Implementation** clipSegments를 기준으로 상대 진행 시간·전체 길이·seek 위치를 계산한다. TC/recording identity를 key로 state를 분리하고 이전 video는 unmount 시 pause한다. native controls 대신 같은 영상 영역에 작은 play/pause·seek·시간·mute·fullscreen controls를 둔다. 기존 semantic tokens와 keyboard-accessible range/button을 사용한다. 일반 TC 전환은 pause+0, 자동 segment 전환은 재생 지속, signed URL refresh는 현재 위치·재생 여부 보존. async play 완료가 unmounted media를 다시 재생하지 않게 한다.
- [x] **Step 2: Tests** 서로 다른 TC가 같은 segment를 사용하는 경우, segment 경계 seek/끝/자동 전환/URL 갱신을 검증한다. 상대 시간 계산은 node tests, 실제 QA 6 선택과 controls는 browser 검증. typecheck/build·수정 파일 lint 실행.
- [x] **Step 3: Rollout / Rollback** Vite 5176에 반영하고 기존 home draft PR #228에 push한다. 서버·SDK·DB 변경 없음. rollback은 home commit revert.

## Validation
- **Commands to run:** npm test, npm run build, 수정 파일 eslint.
- **Expected output:** TC 선택 직후 상대 시간 0, paused. 선택 구간 범위에서 seek하고 여러 segment를 연속 재생한다.

## Risks & Rollback
- **Risks:** 원본 segment 시간과 TC 상대 시간 혼동, 경계에서 잘못된 segment 선택, 늦은 play Promise, URL 갱신 시 불필요한 reset.
- **Rollback steps:** 이번 home commit revert.

## Open Questions
- 없음.

## Review changes

- 상대 시간은 첫 재생 가능한 frame을 0으로 하고 각 clip의 `to - from` 합으로 계산한다. 영상 누락 시간은 재생 길이에 넣지 않고 기존 누락 안내로 보인다. 정확한 경계는 다음 clip의 시작, 마지막 끝은 마지막 clip의 to로 매핑한다.
- browser 검증은 같은 원본 segment에 걸친 TC 전환·재선택에서 pause와 0 초기화, segment 경계의 seek와 자동 전환을 확인한다.
- 순수 시간 매핑은 videoEvidence.ts에 두고 media lifecycle과 controls는 작은 EvidencePlayer 컴포넌트로 분리한다. 새 library는 추가하지 않는다.
- Fast finding 반영 완료, Medium PASS.

## Result

- Commit `f1825ba`를 기존 draft PR #228에 push했다.
- 전체 tests 1,523개, build/typecheck, 수정 파일 eslint, diff check 통과. plan review와 pair review PASS.
- 실제 QA 6에서 TC5 재생→TC4 선택 후 0:00/정지, segment 경계의 연속 재생, 끝에서 정지/재시작을 확인했다.
- 라이트·다크·390px 화면을 포함한 스크린샷 7장을 repo와 PR에 보존했다.
