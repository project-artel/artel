# 2026-10-28 — 저장소별 내 PR 35개를 4개로 통합

- Date: 2026-10-28
- GitHub Issue: None (기존 PR/Jira 작업 통합)
- Status: Complete

## Goal

사용자가 지정한 dev-yunseong의 열린 PR 35개를 저장소별 draft PR 하나씩, 총 4개로 통합한다. develop merge는 하지 않는다. 팀원의 PR과 원본 브랜치는 유지한다.

## Non-goals

다른 계정 PR 종료, develop/main merge, 원본 branch 삭제나 force push, 실행 중인 로컬 stack·작업 디렉터리 변경.

## Context / Constraints

원본 목록은 `.work/bundle-artel-*.json`에 body·head SHA·base·author와 함께 보존했다.

- orchestration-server: #367 #368 #369 #370 #371 #379 #381 #382 #383 (9)
- home: #224 #227 #228 #229 #230 #231 (6)
- agent-server: #181 #257 #261 #262 #263 #264 #265 #266 #267 #268 #275 (11)
- sdk: #161 #162 #163 #164 #165 #166 #168 #169 #174 (9)

일부 head에는 다른 팀원의 기반 commit이 이미 포함돼 있다. 원본 commit ancestry를 유지한 merge로 이 의존성을 보존하고 통합 PR에 명시한다. 원본 head는 수정하지 않아 해당 branch를 base로 쓰는 팀원 PR에 새 diff를 유입하지 않는다.

## Approach (Checklist)
- [x] **Step 0: Recon** 사용자 범위 확인, 계정별 열린 PR 목록·head/base/body 저장.
- [x] **Step 1: Implementation** 저장소별 독립 worktree를 workspace `.worktrees/<repo>/pr-bundle-20261028`에 생성한다. branch는 `codex/pr-bundle-20261028`, base는 최신 origin/develop. 원본 head를 전용 pinned refs로 fetch하고 저장한 SHA와 일치 확인. 포함 관계 순서로 source head를 merge한다. original commits/author를 유지하고 충돌은 승인된 최신 기능·동작을 보존하며 해결한다. 기존 작업 파일은 건드리지 않는다.
- [x] 각 source SHA가 최종 HEAD의 ancestor인지 전수 검사한다. 이미 develop에 포함된 PR은 중복 변경 없이 기록한다. source PR/head가 작업 중 바뀌면 새 commit도 통합하고 다시 검증한 뒤 종료한다.
- [x] **Step 2: Tests** 저장소별 diff check 및 실제 project의 build/typecheck/tests를 실행한다. 통합 충돌 지점과 공통 protocol/DB migration 번호를 검토한다. 실행 stack을 중단하거나 실제 유료 QA를 시작하지 않는다. SDK는 Unity test runtime 가용성을 확인하고 가능한 검증을 수행하며 불가 항목은 구체적으로 기록한다.
- [x] **Step 3: Rollout / Rollback** 검토 가능한 결과를 push하고 draft PR 4개를 생성·현재 채팅에 attach한다. 원본 PR·Jira 링크·기존 screenshots/검증 이력·의존성·통합 검증 결과를 body/문서로 보존한다. 새 PR의 diff/commit 포함과 확인 가능한 CI 결과를 검토한 다음 해당 저장소 원본 PR만 종료한다. 원본마다 대체 PR 링크를 남긴다. 닫기 직전에 author/state/head SHA를 다시 확인한다. branch 삭제와 develop merge는 하지 않는다.

## Validation
- **Commands to run:** pinned SHA ancestry 검사, git diff --check, npm test/build/typecheck 또는 저장소별 Maven/Python/Unity 검증, PR head/base·원본 상태 재조회.
- **Expected output:** 원본 35개 source commit 손실 없음. 신규 draft PR 4개가 develop 기준으로 열리고 원본 35개는 CLOSED(MERGED 아님). 다른 계정 PR 상태/head는 유지. 원본 screenshots 보존.

## Risks & Rollback
- **Risks:** stack 중간 branch 누락, 최신 원본 변경 누락, 충돌 해결 중 동작 되돌림, migration 충돌, 다른 팀원 PR의 기존 기반 포함, CI 환경 의존성.
- **Rollback steps:** 통합 PR을 닫고 원본 PR을 reopen한다. 원본 branch·head를 유지하므로 원래 review 구조 복원 가능.

## Open Questions
- 없음. 사용자가 내 계정 PR만 저장소별 통합으로 지정했다.

## Review changes

- 대상을 위의 35개 명시 목록과 `author.login == dev-yunseong`의 교집합으로 고정한다.
- 각 close 직후 author/state/head SHA를 다시 읽는다. 통합한 SHA가 같고 CLOSED일 때만 종료 완료로 기록한다. 새 head가 생겼으면 이번 작업으로 닫은 PR을 reopen하고 새 head 통합·검증 후 다시 닫는다. 다른 사용자가 이미 merge한 PR은 상태를 바꾸지 않고 별도 기록한다.
- snapshot JSON과 최종 처리 기록을 로컬에 남겨 reopen/미처리 대상을 확인할 수 있게 한다.
- Fast finding 반영 완료. Medium PASS.

## 조직 전체 목록 추가 확인

사용자 범위인 dev-yunseong 계정의 조직 전체 열린 PR을 재조회해 총 43개·8개 저장소를 확인했다. 기존 4개 저장소(35개) 외에 아래를 같은 규칙으로 처리한다.

- artel-cli: #45 #46 #47 → 새 draft PR 1개 (기존 base main)
- onboarding: #37 #38 → 새 draft PR 1개 (기존 base main)
- insomnia-api: #21 #23 → 새 draft PR 1개 (기존 base master, 실제 remote branch 확인)
- artel: #30만 있으므로 통합 없이 유지

최종 대상은 원본 PR 42개 → 새 draft PR 7개이며, 기존 artel #30을 포함해 열린 본인 PR은 총 8개가 된다. main/master/develop 어느 branch에도 merge하지 않는다. 추가 저장소도 같은 pin·ancestry·tests·원본 종료 전후 SHA 확인·rollback 규칙을 적용한다. source snapshots는 .work/bundle-<repo>.json에 보존한다.

## Final result

- 조직 전체 본인 PR: 43개 → 8개. 원본42개 CLOSED(merge 아님), 통합 draft7개 OPEN, 기존workspace#30유지.
- 통합 PR: server385, home232, agent279, sdk176, CLI49, onboarding39, insomnia28.
- Source42개 각각 close 전후 author/state/head SHA 검사와 최종 재조회 통과. snapshot 및 처리 기록은 .work/bundle-*.json, 최종 감사는 .work/bundle-final-audit.json.
- Source commit/author/branch/기존스크린샷/리뷰링크보존. 다른작성자의PR종료·기본branchmerge·forcepush·실행중stack변경 없음.
- 검증: home1547tests/build/typecheck/scopedlint, agent2984pytest+44보존회귀/wheel, SDK2909Unitymatrix, CLI460tests/build/typecheck/lint, onboardinglocale/docs/build/lint, InsomniaYAML/JSON모두PASS. 서버전체실행후13class124개재검증/packagePASS, 최종보고서2417고유tests·fail/error0. 서버 수정후전체suite재실행수치는아님.
- 독립통합reviewPASS. Agent과거prompt판본및충돌원문archive의bytes/file-set/hash보존확인.
- SDK/home/CLI/onboardingCI성공확인, server/agentCI는최종재확인중. Insomnia에는별도CI없음.
