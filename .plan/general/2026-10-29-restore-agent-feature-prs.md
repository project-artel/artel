# 2026-10-29 — Agent 기능별 PR 복원

- Date: 2026-10-29
- Jira: 기존 원본 PR의 ARTEL 항목 재사용
- Status: Complete

## Goal

#279의 통합을 원래 기능별 PR 번호로 나누어 검토할 수 있게 한다. 최근 검증한 최종 코드 tree `b4e8df3^{tree}`는 보존한다.

## Non-goals

새 기능 구현, PR merge, force push, 다른 작성자의 PR 변경, 시연 기능 복구, 공유 작업 폴더 정리.

## Context / Constraints

원본 11개는 모두 closed/unmerged이고 원격 branch와 pinned head가 남아 있다. #268의 시연 추가는 후속 사용자 요청으로 폐기됐으므로 closed 상태를 유지한다. #269/#270은 다른 작성자의 선행 변경이며 수정하지 않는다. #262의 참고 step 판정은 마지막 TC 전환에서 대체되므로 최종 TC 계약을 반드시 유지한다.

## Approach (Checklist)

- [x] **Step 0: Recon** 원본 PR 번호·base·head·원격 branch·통합 단계별 tree 조사.
- [x] **Step 1: Implementation** 독립 clone에서 원본181/257/261/262/263/264/265/266/267/275를 기능별 stack으로 복원한다. 각 단계의 원본 head ancestry와 이전 단계 ancestry를 모두 보존한다. 앞의 9개는 해당 기능이 통합됐던 단계의 tree를 재사용한다. TC275는 시연이 제거된 b61 tree를 사용하되 별도 검토할 원본 archive·manifest·보존 test·통합 이력 문서·폐기 시연 계획을 다음 단계로 옮긴다. 원본 prompt 보존 PR은 해당 자료와 Docker test stage COPY를 함께 복원한다. no_bedrock memory test 격리는 첫181 단계부터, 제거된 시연 API test 격리는 TC275 단계부터 적용해 중간 단계의 CI 의존 오류도 막는다. 마지막 리뷰 수정 PR의 tree는 정확히 b4 tree가 된다.
- [x] **Step 2: Tests** 각 단계 diff가 자기 기능 범위인지 검사하고 compile·원본 기능 focused test를 실행한다. 마지막 tree가 기존 검증 tree와 정확히 일치하는지 검사한다. 최종 전체 테스트와 Docker 검증은 같은 tree에서 이미 통과했으며 CI는 새 branch별로 다시 확인한다.
- [x] **Step 3: Rollout / Rollback** 원격 head 재확인 후 원본 branch를 일반 fast-forward push한다. 원본 PR 10개를 reopen하고 gh stack으로 base를 연결한다. 보존 자료·최근 수정용 작은 draft PR 2개를 만든다. 각 PR에 기능·검토 경로·의존관계·검증 상태를 적는다. 원격 전체 tree와 누락 여부 확인 후 #279를 close한다. 기존 통합 branch는 삭제하지 않는다.

## Validation

- **Commands to run:** git merge-base --is-ancestor, git rev-parse tip^{tree}, git diff --stat previous..tip, python -m compileall, 각 기능 focused pytest, gh stack view, 원격 PR metadata·check 조회.
- **Expected output:** 최종 tree `72a3917985fdceb26513fdc6d4fea55c8b4f2bfa`, 원본 head ancestry 보존, 기능별 diff·원본 PR 번호 복원, 다른 작성자 branch/state 불변.

## Risks & Rollback

- **Risks:** 중간 단계의 구계약은 뒤 단계의 TC 계약으로 바뀐다. 원본 순서와 최종 배포 순서를 명확히 적고, 최종 stack 적용 전 개별 단계 배포를 권하지 않는다. 동시 원격 push는 기대 head가 다르면 중단하고 먼저 보존한다.
- **Rollback steps:** #279 reopen, 복원 PR과 새 PR close. branch 삭제·force push 없이 원래 pinned SHA와 새 commit을 모두 남긴다.

## Open Questions

원본 PR 구조 복원 요청은 #279에 한정한다. 다른 저장소 PR은 바꾸지 않는다.

## 계획 검토 반영
FAST/MEDIUM 검토에서 중간단계 CI2건을발견해수정: appboot test의Redis격리는그테스트가있는첫단계부터유지하고,promptmanifest를추가하는PR에DockerCOPY도같이포함한다. b61 tree동일은내부중간조건이므로해제하고,최종b4 tree정확일치는유지한다.


## 결과
원본181·257·261·262·263·264·265·266·267·275를reopen하고보존PR282·최근수정PR283을draft로생성했다. gh stack link로stack284에연결해각기능diff만표시된다. 원격12개head/base/diff와타인269270불변·폐기268closed를검증하고최종tree72a3917985fdceb26513fdc6d4fea55c8b4f2bfa동일을확인후279를닫았다. 원본source와통합branch는보존했다. 각단계compile/focused모두통과. 원격모두MERGEABLE/draft이며181CI성공,나머지CI순차대기·실행중이다. forcepush/rebase/merge없음.
