# QA 버그 수정의 원래 PR 통합

- Date: 2026-10-29
- Jira: ARTEL-1219, ARTEL-1222, ARTEL-1223, ARTEL-1270 기존 항목 재사용
- Status: Complete

## Goal

#285를 닫고 진단 description 호환은 #263·#266, macro text cursor 수정은 #265, indexed object 인용 대조는 #275에 각각 회귀 테스트와 함께 포함한다. 최종 #275 tree는 작업 전 #285와 같게 유지한다. 별도 작업에서 닫은 #282는 그대로 유지한다.

## Non-goals

시각 점검 개편, 독립 PR과 다른 작성자의 PR 변경, develop merge, 새로운 제품 동작 추가.

## Context / Constraints

현재 stack289와 실제 원격 head를 기준으로 별도 clone에서 구성한다. #263에는 get_performance가 없으므로 get_errors의 호환만 넣는다. 중간 prompt v31~v34와 최종 역사 판본 v27·v29의 description 본문이 같음을 확인하고 단계별로 존재하는 fallback을 사용한다. 판본과 arch schema는 변경하지 않는다.

## Approach (Checklist)

- [x] 실제 head·base·상태를 기록하고 기능별 patch와 테스트를 분리한다.
- [x] 새 #263 → #264 → #265 → #266 → #275 chain을 준비한다.
- [x] 단계별 compile·기능 테스트와 최종 전체 pytest, 최종 tree 동일성, pair review를 확인한다.
- [x] 모든 기존 head를 backup하고 원격 SHA를 다시 확인한다. stack 해제 후 #285를 먼저 닫는다.
- [x] 수정된 다섯 branch만 atomic force-with-lease로 갱신하고 URL 기반 stack을 재구성한다.
- [x] 각 PR 설명과 #279 안내·handoff를 갱신하고 원격 상태를 확인한다.

## Validation

구버전 prompt에서도 단계에 존재하는 진단 tool을 조립한다. typewriter의 기존 줄 변경·cursor 상한 테스트를 #265에서 통과한다. indexed selector mismatch·match·missing 테스트를 #275에서 통과한다. 최종 tree가 기존 #285와 같고 독립 PR·다른 작성자 PR·develop은 변경되지 않는다.

## Risks & Rollback

동시 시각 점검 작업이 원격 head를 바꾸면 lease 전에 중단한다. 이전 stack289 tip과 head manifest를 보존한다. #285를 먼저 닫아 후속 branch 재구성 중 자동 merged 처리를 피한다. PR ready 상태는 유지한다.

## Open Questions

없음. 기존 버그의 검토 위치만 옮기는 요청이다.


## 검증과 원격 반영 결과

5단계 compile과 관련 테스트가 통과했다(#263 211개, #264 179개, #265 184개, #266 226개, #275 773개). 최종 #275 전체 pytest는 2,947개 통과했다. 독립 pair review도 PASS다. 새 #275 전체 tree는 작업 전 #285와 byte 단위로 같다.

작업 전 모든 QA head를 codex/backup-agent-stack-289-before-285-absorption-20261029에 보존했다. #285를 닫은 뒤 명시적 SHA lease로 다섯 branch를 atomic 갱신했다. 새 stack290은 #263 → #264 → #265 → #266 → #275다. 각 PR 설명과 #279 검토 안내, 닫힌 #282·#283의 현재 검토 위치를 갱신했다. develop·독립 네 PR·다른 작성자의 #269·#270과 ready 상태는 유지했다. 새 head의 원격 CI는 별도로 진행한다.
