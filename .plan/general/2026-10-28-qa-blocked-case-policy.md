# 2026-10-28 — QA의 사용자 질문과 TC 건너뛰기 정책 추가

- Date: 2026-10-28
- Jira: None (계획 단계, 기존 통합 PR의 후속 범위)
- Status: Proposed

## Goal

QA 시작 시 사용자가 '모르면 부르기'와 '그냥 넘기기'를 선택한다. 일반 브라우저 QA는 사용자에게 질문하고, CI는 사람을 기다리지 않고 막힌 TC를 넘겨 나머지 TC를 실행한다. 사용자가 확정한 대로 CI에서는 미검증 TC가 하나라도 있으면 실패 처리한다.

모델이 질문 tool을 선택하지 않고 판단 불가·전체 종료로 빠지는 경로를 실행 코드에서 통제한다. 이 문서는 설명·설계 계획이며 제품 코드는 아직 변경하지 않는다.

## Non-goals

모델 재학습, 문자열 '모름' 키워드 추측으로 판정, report_step 복원, Unity·영상 전송 구조 변경, 브라우저가 완전히 닫힌 상태의 Web Push 도입.

## Context / Constraints

현재 통합 코드에서 확인한 사실:

- `app/agents/qa/tools/reporting_tools.py`: `ask_user`는 별도 선택 tool이다. `report_test_case`는 질문 이력 검사 없이 `INCONCLUSIVE`를 저장할 수 있다. `finish_run`은 남은 TC·대기 질문 검사 없이 모델의 passed 값을 받아 종료한다.
- `app/agents/qa/runner.py`: 계획과 prompt는 증거 부족 시 INCONCLUSIVE, 진행 방법을 모르면 ask_user라는 두 경로를 안내하지만 실행 시 질문을 강제하지 않는다. tool 없는 모델 종료도 별도로 처리해야 한다.
- `app/qa/evaluation.py`: 질문 대기 시간은 ActiveRunClock에서 제외하고 답변 또는 취소까지 기다리는 기능이 이미 있다. 이를 재사용하고 다른 timeout·tool budget·복구 경로도 같은 대기 상태를 따르는지 검증해야 한다.
- `QaCaseAttempts.kt`: 원본 TC 결과 저장 경로에도 질문 정책의 일관성 검사가 필요하다.
- `QuestionNotifications.tsx`: 현재 브라우저 알림은 프로젝트 구독과 Notification 권한이 모두 필요하다. 클릭하면 QA history로만 이동하며 질문/TC/검증 시도를 특정하지 않는다. 현재 질문 답변 컴포넌트 연결도 QA 실행·history 화면까지 확인하고 연결한다.
- 기존 합의: 질문 중 QA 전체 정지, 답변 대기 timeout 없음, 프로젝트 멤버의 첫 답변으로 재개, 구독한 멤버에게 알림, 대기 중 녹화 지속. 판정 불가를 사람이 실제 실패로 검토하면 기존 미탐 집계 규칙을 유지한다.
- 기존 통합 PR: server #385, agent #279, home #232, CLI #49. 후속 구현은 이 PR들에 반영하거나 merge된 경우 그 base에서 진행하며 불필요한 PR 분할을 하지 않는다.

## Approach (Checklist)

- [x] **Step 0: Recon** 질문·판정·종료 tool, agent clock, 서버 결과 저장, 알림·시작 요청 경로를 확인했다. CI의 미검증 처리 기준을 사용자에게 확인했다.
- [ ] **Step 1: 실행 설정** `blockedCasePolicy = ASK_USER | SKIP_CASE`를 QA 시작 요청과 run_config에 저장해 시나리오별 시도·재시도·재연결·agent 재개에 동일하게 전달한다. 실행 정책은 모델이나 arch가 임의로 바꾸지 못한다. UI는 ASK_USER를 명시해서 보내고 CLI/CI/API의 새 요청 생략값은 SKIP_CASE로 제안한다. CLI에 명시적 정책 옵션을 제공한다. CI 환경변수나 User-Agent를 서버가 추측하지 않는다. 이미 실행 중인 QA와 이전 기록에 새 정책을 소급 적용하지 않는다. 잘못된 enum은 400이다.
- [ ] **Step 2: 막힘 처리** `ask_user`와 판단 불가 보고가 공통 정책 처리 경로를 사용한다. TC/attempt에 막힌 이유, 현재 화면·근거 참조, 시도한 조작, 필요한 정보/질문을 구조화한다. 특정 표현을 정규식으로 추측하지 않는다. ASK_USER에서 INCONCLUSIVE를 보고하려 하면 실행 코드가 질문을 만들고 기다리도록 전환하며 원본 TC 최종 판정은 아직 확정하지 않는다. 모델이 다음 턴에 ask_user를 선택하리라고만 기대하지 않는다. 서버도 정책에 맞지 않는 직접 결과 저장을 거절한다.
- [ ] **Step 3: ASK_USER** 질문 생성→브라우저 알림+QA 화면 표시→QA 전체 답변 대기→첫 유효 답변 적용→해당 TC 재검증 순서다. 답변은 판정 자체가 아니라 재검증을 위한 지시다. 사용자가 명시적으로 '이 TC 넘기기'를 선택하면 INCONCLUSIVE와 사용자 skip 사유로 완료할 수 있다. 같은 미해결 질문은 재사용해 알림을 중복 발송하지 않는다. 답변 후에도 막히면 수행 결과와 추가로 필요한 정보를 포함한 후속 질문을 한다. 질문을 한 번 했다는 사실만으로 판단 불가 종료를 허용하지 않는다. 사용자 취소/종료는 항상 가능하며 대기 중 영상은 계속 저장한다.
- [ ] **Step 4: SKIP_CASE** 질문/대기를 만들지 않고 해당 시도를 INCONCLUSIVE로 저장한다. 정책으로 넘긴 사유를 별도 metadata로 기록하고 다음 TC로 진행한다. `ask_user`가 잘못 호출돼도 같은 non-interactive 경로로 처리해 CI가 대기하지 않게 한다. 실제 게임 실패(PASSED/FAILED의 판단)와 미검증 수를 분리하고 미검증을 통과로 세지 않는다. INCONCLUSIVE만으로 TC 실패 issue를 생성하지 않는다. 미검증도 CI 최종 결과에는 실패 사유다.
- [ ] **Step 5: 종료·경쟁 제어** 정상 종료는 모든 대상 TC에 확정 결과 또는 정책/사용자로 승인된 skip 기록이 있고 대기 질문이 없을 때만 허용한다. `finish_run`의 임의 passed Boolean과 tool 없는 자연어 종료 모두 같은 최종 검사에 통과해야 한다. '모르겠다'는 이유로 미처리 TC를 남긴 채 정상 종료하지 못하게 한다. 미답 질문 중 action/report/finish의 병렬 호출과 늦은 응답을 차단한다. 사용자 취소·실행 예산 소진·치명적 인프라 오류는 별도 중단 사유와 미검증 목록을 보존한다. 질문 대기는 실행 timeout에서 제외하지만 취소·연결 오류 탐지까지 끄지는 않는다. server/agent의 잠금과 idempotency를 재사용하고 DB transaction을 열린 채 사람을 기다리지 않는다.
- [ ] **Step 6: 최종 결과·CI** 모델이 요청한 passed가 아니라 서버가 저장한 전체 TC 결과로 QA 최종 결과를 계산한다. 실제 FAILED 또는 INCONCLUSIVE/미처리/중단이 있으면 CI는 non-zero로 종료한다. 넘기기 모드는 '기다리지 않고 나머지를 실행'하는 정책이고 품질 기준을 통과시키는 정책이 아니다. history/CLI 결과에 실제 실패와 미검증을 구분해서 보여준다. 인간 검토·오탐/미탐 지표의 기존 기준은 유지한다.
- [ ] **Step 7: 화면·알림** 시작 화면에 두 선택을 추가하고 실행 중/history에서 적용한 정책을 확인할 수 있게 한다. 알림 클릭은 정확한 QA 실행·TC·attempt·질문으로 연결한다. 현재 영상과 질문, 답변/명시적 TC skip을 같은 맥락에서 볼 수 있게 한다. 권한 거부·알림 미구독이어도 질문은 QA 화면에서 확인하고 답할 수 있다. 기존 프로젝트 구독·멤버 답변 권한과 첫 답변 채택 규칙을 유지한다. 이번 범위는 ARTEL 브라우저 앱이 열려 있는 동안의 알림이며, 모든 탭을 닫은 상태의 push는 별도 범위다.
- [ ] **Step 8: prompt·복구** 새 정책별 지시를 새 prompt 판본에 추가한다. 과거 prompt는 수정하지 않는다. 최초 context, tool 설명, compaction summary, 재연결 시점의 context가 같은 정책과 대기/skip 상태를 보존하도록 한다. tool set과 종료 검사는 모든 지원 QA engine/arch에서 공통 적용해 우회하지 못한다.
- [ ] **Step 9: Tests** 아래 acceptance tests와 실제 통합 동작을 검증한다. 먼저 server/agent 계약과 종료 gate를 구현하고 home/CLI를 연결한다. 단순 prompt 지시만 추가하고 완료로 처리하지 않는다.
- [ ] **Step 10: Rollout / Rollback** server→agent→home/CLI 순서로 계약을 맞춘다. 새 실행 설정과 이력은 보존하고 진행 중 QA를 변경하지 않는다. 이전 client 생략값·정책 미지원 agent 감지와 명확한 오류 표시를 검증한다. rollback 시 정책으로 대기 중인 QA를 조용히 실행/통과로 바꾸지 않는다.

## Validation

- **Commands to run:** server Maven 관련 통합 테스트·package, agent pytest(보고/질문/종료/복구/각 engine), home/CLI 전체 테스트·typecheck·build 및 변경 파일 lint, 실제 브라우저 알림·답변 재개 확인.
- **Expected output:**
  1. ASK_USER에서 모델이 ask_user 없이 INCONCLUSIVE를 호출해도 질문 1개 생성·알림·대기이며 최종 판정/전체 종료는 아직 발생하지 않는다.
  2. 미답변 중 action/finish 병렬 호출, 자연어 종료, compaction/재연결, 동일 tool 재시도에도 질문과 실행이 중복되지 않는다.
  3. 답변이 오면 해당 TC를 재검증한다. 답변 대기 시간은 timeout 예산에서 제외되고 취소는 즉시 적용된다. 중복 답변은 하나만 채택된다.
  4. SKIP_CASE에서 판단 불가나 ask_user가 발생해도 질문·대기 없이 다음 TC로 간다. 넘긴 TC는 INCONCLUSIVE로 남고 실제 실패 issue를 만들지 않는다.
  5. CI에서 모두 통과한 경우만 성공이다. 실제 실패가 없어도 skip/미검증/중단이 하나라도 있으면 실패한다. 실패 수와 미검증 수는 구분한다.
  6. 알림 클릭으로 정확한 질문과 TC 영상/답변으로 이동한다. 알림 권한이 없어도 QA 화면 답변은 가능하다. 대기 중 녹화도 지속된다.
  7. 모드 값의 생략·잘못된 값·재실행·버전 미지원 경계와 과거 prompt bytes 보존을 검사한다.

## Risks & Rollback

- **Risks:** 모드 누락으로 CI 대기, question과 TC report 경쟁으로 질문 후 즉시 종료, 직접 API나 다른 engine의 종료 우회, 같은 질문 반복, 답변을 실제 검증 없이 통과 판정으로 사용, 알림 권한/구독 누락, 전체 QA 집계가 미검증을 누락하는 문제.
- **Rollback steps:** 새 실행 생성만 이전 버전으로 전환하고 기존 정책·질문·판정 이력을 보존한다. 진행 중인 대기 실행은 사용자에게 표시해 명시적으로 종료하거나 지원 버전으로 재개한다.

## Open Questions

- CI 미검증 결과: 사용자 확정 — 하나라도 있으면 CI 실패.
- 제안 기본값: 브라우저 새 실행 ASK_USER, CLI/CI/API 새 실행 SKIP_CASE. 구현 전에 이 계획을 기준으로 확정한다.

## Review 반영 사항

- 실제 로컬 QA 6을 읽기 전용으로 확인했다. TC 시도는 5개, INCONCLUSIVE 1개, ask_user TOOL log 0개, 사용자 질문 row 0개다. 이 실행은 질문을 만들지 않고 판단 불가로 넘어간 사례다.
- **질문의 범위:** TC 질문은 scope=TC와 case_id를 명시하고 해당 run의 attempt에 연결한다. TC 시작 전이라도 명시한 case_id의 시도를 idempotent하게 시작한 뒤 묻거나 skip한다. 임의 TC를 고르지 않는다. QA 전체 준비 문제는 scope=RUN으로 구분한다. ASK_USER는 실행 질문으로 대기하고 답변 후 준비를 재개한다. SKIP_CASE에서 실행 전체의 준비가 불가능하면 특정 TC나 모든 TC를 일괄 skip하지 않고 SETUP_BLOCKED 사유로 실행을 중단하며 CI 실패와 미검증 목록을 남긴다. 동시에 여러 TC를 열어두는 상황에서도 scope·case_id·attempt_id로 처리 대상을 결정한다.
- **재시도 최종 집계 제안:** history·원본 판정·신뢰도 지표는 기존 합의대로 모든 시도를 보존하고 각 시도로 집계한다. 실행의 TC별 최종 상태는 그 실행에서 마지막으로 시작한 시도를 기준으로 한다. 마지막 시도가 미완료면 이전 PASSED로 덮지 않고 미검증이다. INCONCLUSIVE→PASSED, FAILED→PASSED로 재검증 완료된 TC의 최종 상태는 PASSED다. 이전 실패·판단 불가 이력과 issue는 삭제하거나 자동 해결하지 않는다. 다른 모든 TC도 최종 PASSED일 때만 최종 CI 성공이다. 일반 QA의 명시적 사용자 skip 역시 INCONCLUSIVE로 남기므로 전체 QA는 미검증 포함으로 표시하고 완전 통과로 집계하지 않는다.
- **질문 IO와 사람 대기 분리:** 서버에 저장된 WAITING 질문임을 확인한 뒤에만 무제한 사람 대기로 들어간다. 등록 응답이 유실되면 같은 question ID로 조회·재등록해 복구한다. 질문 등록/조회 transport·5xx 오류는 사람 대기와 별도 wall-clock 복구 deadline(제안 60초)을 적용한다. 그동안 연결 복구 상태와 마지막 질문을 표시하며 취소는 즉시 허용한다. 복구되면 같은 질문으로 이어가고 새 알림을 중복 생성하지 않는다. 계속 실패하면 QUESTION_SERVICE_UNAVAILABLE 같은 명시적 인프라 사유로 실행을 중단한다. 이 동작은 '미답변 60초 timeout'이 아니다. 인증·설정 오류 4xx는 재시도하지 않는다. 종료된 QA의 늦은 답변은 재개시키지 않고 서버가 orphan WAITING 질문을 정리하도록 검증한다. DB transaction을 열린 채 복구/사람 답변을 기다리지 않는다.
- **추가 acceptance tests:** TC 시작 전 질문·다중 시도 질문의 정확한 연결, RUN scope의 ASK 대기/SKIP 중단, INCONCLUSIVE→PASSED·FAILED→PASSED 및 PASSED→미완료의 최종 집계, 사용자 skip의 일반 QA 결과, POST 응답 유실·조회 장애·복구 deadline·장애 중 취소·복구 후 동일 질문 재사용·늦은 답변 무시를 검증한다.
- Medium review PASS. Fast의 세 가지 must-fix를 위와 같이 반영했다. 기본값과 재시도 최종 집계·인프라 복구 60초는 이 계획의 명시적 제안이며 아직 제품 동작을 변경하지 않았다.

## 계획 검토 결과

- Medium PASS. Fast의 세 가지 지적을 반영한 뒤 Heavy PASS.
- 시작 화면에서 ASK_USER의 브라우저 알림 권한·프로젝트 질문 구독 상태를 확인할 수 있게 한다. 기존 알림 켜기 동작을 재사용하며 권한이 없어도 QA 화면의 질문·답변 경로는 유지한다.
- 현재 단계는 설계안 검토 완료다. 제품 코드·실행 중 QA·기존 PR은 변경하지 않았다.
