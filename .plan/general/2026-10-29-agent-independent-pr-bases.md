# 2026-10-29 — Agent 독립 PR의 develop 기준 적용

- Date: 2026-10-29
- Jira: 기존 원본 PR 항목 재사용
- Status: Complete

## Goal

사용자 요청대로 관련 없는 기능을 선형 stack에서 분리한다. #181·#257·#261·#267은 develop을 직접 base로 삼고 QA262→263→264→265→266→275→285→282만 연결한다.

## Non-goals

기능 변경, PR merge, 새 PR 생성, 다른 작성자의 PR 수정, 공유 작업 폴더 변경.

## Context / Constraints

기존 선형 stack의 head에는 앞 기능의 ancestry와 코드가 함께 있으므로 base만 수정하면 diff가 섞인다. 독립 기능은 source별로 분리하고 QA tree에서는 해당 기능만 제거한다. 원본 pinned source head·저자는 보존하되 앞서 만든 인위적 누적 ancestry는 제거한다. 각 PR 번호는 유지한다.

## Approach (Checklist)

- [x] **Step 0: Recon** 네 기능의 실제 호출 의존성이 없음을 확인했다. planner 언어 관련 최종 pe5 label과 테스트는 독립257에, model 검증 추가2건은 독립181에 둔다. startup memory test 격리는 독립 PR과 QA 양쪽에 유지한다.
- [x] **Step 1: Implementation** 새 독립 clone에서 source tree와 commit을 재구성했다. QA 최신 버그 수정283은 보존자료282를 기다리지 않도록 먼저 둔다.
- [x] **Step 2: Tests** 12단계 compile·기능 회귀 통과. 실제 Git merge-tree로 독립4개와 QA를 합성했고, API import·API 계약 test 추가 위치의 공존 충돌2곳을 해결하면 기존 b4e8df3 tree와 byte 단위 동일하다.
- [x] **Step 3: Rollout / Rollback** 기존 원격 head가 준비 당시와 같은지 확인한다. 기존 linear tip42dab929의 remote backup branch를 먼저 만들고 모든 이전 head ancestry 보존을 확인한다. stack284를 unstack하고 모든 PR이 분리됐는지 확인한다. 원격12개 head는 명시적 expected SHA를 둔 atomic force-with-lease로만 갱신한다. develop base4개와 QA 새 stack을 설정하고 PR 설명·검증 이력을 갱신한다.

## Validation

- **Commands to run:** compileall, 단계별 focused pytest, merge-tree, tree hash 비교, 원격head/base/stack 조회.
- **Expected output:** 독립 PR4개 base develop·stack=null, QA8개만 새stack, 전부충돌없음,기존다른작성자PR불변.

## Risks & Rollback

- **Risks:** 번호를 유지한 독립화에는 head 재구성이 필요하다. 이전 head는 이번 작업에서 만든 commit이며 원격이 다르면 갱신을 중단한다. #181과 #261은 runtime 의존이 없지만 나중에 함께 합칠 때 import·test삽입 위치가 겹칠 수 있다.
- **Rollback steps:** 보존한 기존 tip과 각 head manifest로 기존 branch·stack 구조를 복원할 수 있다. backup을 삭제하지 않는다.

## Open Questions

없음. 코드 동작이 아닌 PR 의존관계 정리 요청이다.

## 최종 원격 확인

독립 PR 네 개는 develop 기준이며 stack에 속하지 않는다. QA PR 여덟 개는 stack286에 연결했다. 모든 예상 head와 base가 일치하고 충돌이 없다. CI는 7개 SUCCESS, 5개 PENDING이며 단독 기능 테스트 12단계는 모두 통과했다.

branch 갱신과 base 변경 순서를 잘못 잡아 #283이 당시 base branch에 포함되면서 GitHub가 자동 merged 처리했다. develop은 변경되지 않았다. 동일 commit을 올바른 base의 draft #285로 다시 열고 설명과 검토 링크를 갱신했다. 새 PR을 만들지 않는다는 초기 범위의 예외는 이 복구에 한한다.
