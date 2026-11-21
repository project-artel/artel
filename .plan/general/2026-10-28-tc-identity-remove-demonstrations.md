# 2026-10-28 — TC 시연 기능과 데이터 제거

- Date: 2026-10-28
- GitHub Issue: None (기존 저장소별 통합 PR 재사용)
- Status: Implemented

## Goal
시연 입력 제어, 시연 기록·판정·승인 절차와 agent 참고 기능을 제품에서 제거한다.

## Non-goals
QA 실행 녹화·스트리밍·판정 검토·사용자 피드백과 TC 수정 후 재검증은 유지한다. 기존 내부 ID·URL은 변경하지 않는다. TC 번호 표시는 다른 세션 소유이며 수정·commit하지 않는다. 사용자가 기존 시연 영상·기록 삭제를 명시적으로 승인했다.

## Context / Constraints
WSL 저장소별 통합 branch/기존 draft PR에 반영한다. 변경된 Flyway migration은 되돌리지 않으며 V142를 보존한다. 새 migration과 재시도 가능한 정리 작업으로 시연 데이터·시연 knowledge·전용 storage 객체를 삭제한다. V142 checksum은 보존한다. 객체 삭제 완료 전 key 목록을 잃지 않으며 QA 영상 prefix는 삭제하지 않는다. 시연 knowledge 문서가 QA 또는 일반 검색에 재유입되지 않도록 읽기 경로를 확인한다.

## Approach (Checklist)
- [x] **Step 0: Recon**: home demonstrations, orchestration demonstration 패키지와 SDK handler, agent verification_procedure, SDK lease를 추적한다.
- [ ] **Step 1: Implementation**: home 화면·번역·스타일·API 제거. orchestration endpoint·입력 제어·추출·procedure 공급 및 활성 설정 제거. agent 추출 route·prompt/context 제거. SDK 시연 lease와 capability 송수신 제거, 일반 입력·QA streaming 유지. 기존 QA snapshot에 verification_procedure가 있어도 agent가 무시한다.
- [ ] **Step 2: Tests**: 각 저장소 관련 회귀 테스트, home 전체 test/build/lint, server compile/관련 테스트, agent 관련 테스트, SDK 지원 검사. 기존 SDK DEMONSTRATION_CAPABILITIES/DEMONSTRATION_CONTROL_RESULT는 연결 종료 없이 무시하고 일반 ACTION/PULSE/streaming 회귀 확인. 시연 진입점 제거 화면 캡처 보존.
- [ ] **Step 3: Rollout / Rollback**: 기존 저장소별 draft PR 갱신. 서버 먼저 배포 후 소비자 적용. 데이터 삭제는 복구 불가이며 사용자가 승인했다. 실패한 storage 삭제는 다시 시도한다.

## Validation
- **Commands to run:** 저장소 package/프로젝트 지침에서 확인한 test/build, 제거된 기능 실행 코드 검색, git diff --check.
- **Expected output:** 시연 진입점·동작·agent 참고 없음. QA 기존 기능 회귀 없음.

## Risks & Rollback
- **Risks:** 일반 SDK ACTION과 시연 ACTION이 혼합돼 있다. 시연 전용 필드만 제거하고 기존 QA 계약은 보존한다. knowledge에 남은 시연 문서가 읽히지 않도록 필터한다. 기존 설치 SDK에서 보낼 수 있는 미지원 메시지는 안전하게 무시한다.
- **Rollback steps:** 저장소별 commit revert. migration 이력은 유지하며 삭제된 데이터는 복구되지 않는다.

## Open Questions
없음. 기능 및 데이터 삭제 승인 완료. TC 번호 변경은 다른 세션에서 진행한다.


## Review 반영
- 기존 QA snapshot의 시연 전용 verification_procedure 필드를 제거하고 시연 knowledge 원문·이력·embedding·참조도 삭제한다. QA 판정·영상·일반 knowledge는 보존한다.
- storage 삭제는 demonstrations/ 전용 prefix에 한정한다. DB에서 참조한 객체뿐 아니라 해당 prefix orphan도 포함한다. 보관된 객체 버전이 있으면 삭제 범위를 확인하고 명시한다.
- 삭제 성공, 실패 후 재시도, 재실행, 빈 데이터 상태를 검증한다. 전용 데이터만 사라지고 QA 영상·일반 knowledge가 유지되는 회귀 검사를 추가한다.
- 삭제 key queue는 DB purge 전에 확보하고 저장소 정리가 실패해도 유지한다. prefix 검증을 통과한 key만 삭제하며 완료 상태를 남긴다.

## 검증 진행 기록
- home: 제거분 격리 test 1,547개·build·변경 파일 lint 통과, 독립 리뷰 PASS. 9ffcd83을 PR232에 push하고 캡처를 첨부했다. 전체 lint의 기존 hooks 오류 4개는 변경 범위 밖이다.
- SDK: GPU EditMode614·PlayMode95·New Input전용105 통과, 독립 리뷰 PASS. 0fc38d8을 PR176에 push했다. 이후 GitHub CI 8개 입력 구성 job도 통과했다.
- agent: 전체 pytest2,959·focused120·실제 분리 Redis CAS/TTL 검사 통과, 독립 검토 결함 없음. b61b871을 PR279에 push했다. Jenkins는 This commit cannot be built ERROR이며 상세 로그는 읽기 권한이 없어 원인 미확정이다.
- server: V148 및 정리 코드 독립 리뷰 PASS. filesystem orphan 및 삭제 실패 공정성 수정 반영. 다른 세션 TC 번호 파일을 제외한 격리 snapshot으로 최종 테스트·package 진행 중이다.

## 완료
- server 격리 snapshot에서103개 테스트·package 통과. 시연 클래스·TC 번호 코드가 JAR에 없고 V142 checksum이 유지됨을 확인했다. eae9c3a을 기존 PR385에 push했다.
- home232·server385·agent279·SDK176 설명을 수정했고 시연 버튼 제거 캡처를 homePR에 첨부했다. 번호 변경 소스는 stage·commit하지 않았다.
- 실제 운영 데이터는 아직 삭제하지 않았다. 서버 배포 시 V148/객체 정리, agent 시작 시 Redis 정리가 수행된다. QA 영상과 판정 이력은 보존한다. 상세 배포·권한·pending 확인은 각 저장소 docs에 기록했다.
