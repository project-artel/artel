# 2026-10-27 — QA 영상 기반 TC 평가와 신뢰도 측정 추가

- Date: 2026-10-27
- Jira: ARTEL-1268 (orchestration ARTEL-1269, agent ARTEL-1270, home ARTEL-1271)
- Status: Reviewed — HEAVY REVIEW: PASS; 구현·자동 검증·draft PR 3개 제출 완료. 실제 Unity 비교는 설정 미비로 미실행.

## Goal

docs/qa-tc-evaluation-requirements.md의 전체 범위를 구현한다. QA 전체 영상, 시도별 TC 판정과 사람 평가, 다음 실행 피드백, 신뢰도 지표, 질문·무기한 대기, 반복 실패 issue를 연결한다.

## Non-goals

운영 배포, 모델 재학습, 버전별 agent 성능 비교, 기존 사용자 변경 정리.

## Context / Constraints

- 기존 checkout에 사용자 변경이 있어 각 저장소 origin/develop에서 별도 worktree를 사용한다.
- Kotlin WebFlux/R2DBC/Postgres의 public /api와 internal /internal 포트 경계를 보존한다.
- StreamSignalRelay는 SDP/ICE만 중계하고 SDK가 offer를 만든다. SDK 변경 없이 서버 쪽 WebRTC 수신 peer와 viewer 송신 peer를 분리한다.
- QaAgentInboundRouter의 STATUS가 TC 현재 판정을 갱신한다. 현재 판정과 시도 이력은 별개로 유지한다.
- Agent는 report_case/report_step, 최대 300초 wait_for_operator 및 실행 deadline이 있다. TC 명시 tool과 질문 대기는 이 경로를 갱신해야 한다.
- 멤버 여부는 기존 ProjectAccessService로 확인하고 프로젝트 밖 ID는 404로 거절한다.

## Approach (Checklist)

- [x] **Step 0: Recon** 기존 stream, TC verdict, issue, agent reporting 경로 조사. 최신 develop과 기존 사용자 변경 확인.
- [x] **Step 1: Implementation** 아래 저장소별 단계 실행. TC-only 추가 결정 반영.
- [x] **Step 2: Tests** migration/API/동시성, agent tool, 합성 미디어 입력-저장-재생, 실제 API에 연결한 최종 화면을 검증했다. 실제 Unity QA 변경 전·후 비교는 LLM 복호화 설정이 없어 미실행으로 남겼다.
- [x] **Step 3: Rollout / Rollback** 미디어 활성화 설정과 additive migration 보존, 소비자 배포 철회 절차를 문서화했다. 운영 배포는 하지 않는다.

### Orchestration 계약과 상태 저장 추가

- qa_case_attempt: UUID idempotency key, project/TC/TC-version snapshot/qa_try, 시작·종료 시각, 원래 판정 PASS/FAIL/INCONCLUSIVE/INTERRUPTED와 이유. 재검증은 별도 행. start 중복은 동일 행, report 중복은 동일 결과 또는 conflict.
- 기존 qa_verdict_review에 현재 평가를 유지하고 qa_verdict_review_revision에 변경 이력을 추가한다. 평가와 issue 전이는 같은 transaction이며 attempt lock과 TC ID별 advisory lock으로 직렬화한다.
- Public /api/projects/{projectId}/qa-evaluation/attempts (qaTryId/testCaseId filter), attempts/{id}, verdicts/{logId}/review 및 reviews, reliability (from/to), questions, question-subscription. Internal /internal/qa/tries/{id}/case-attempts/start, case-attempts/{id}/report, questions 및 답변 조회. 피드백은 기존 scenario composition 계약으로 제공한다.
- QA 종료 시 남은 attempt를 INTERRUPTED로 닫는다. report 시각 이후 5초까지 media capture를 유지한다. 기존 agent compatibility는 STATUS 검증 판정으로 별도 legacy attempt를 기록하되 명시 tool로 이미 기록한 이벤트와 중복하지 않는다.
- 리뷰 최신본만 지표에 사용. 집계 축은 attempt.started_at의 UTC 기간, 추이는 Asia/Seoul 일자. 수정 시 과거 추이도 최신 평가로 재계산. 분모 0은 null. INCONCLUSIVE/INTERRUPTED+실제 FAIL은 FN. 나머지 미검토/판단 불가는 제외.
- issue에 TC 식별자·이전 issue·자동 종료 사유 추가, occurrence는 attempt에 유일. TC row lock 아래 열린 issue 조회/생성, manual resolve는 유지. 오탐만 남으면 자동 종료, 정정 시 기존 자동 종료 issue 재개. 이미 열린 issue가 있으면 정정 이력을 그 열린 issue로 모으고 이전 관계 보존. 판단 불가 평가로 바꾸면 원래 FAIL을 미확정 실패로 유지. 중단+실제 FAIL도 미탐 issue에 포함.
- 피드백은 기존 계약의 TC별 최근 3개 평가를 재사용하고 TC snapshot과 current version mismatch를 제공한다. 설명은 4000자 제한. 내용은 명령이 아닌 증거로 전달.
- 질문은 qa_run당 하나의 미응답 질문, 첫 답변 UPDATE WHERE answered_at IS NULL로 채택. 구독자 대상 SSE로 질문 알림. 질문/답변은 DB에 남고 대기는 만료 없음. 수동 종료는 기존 cancel 경로. 세션 유실 시 실패로 종료하고 질문은 취소 표시.

### orch 미디어 수신·저장 추가

- orch 저장소에 private media worker를 둔다. aiortc로 SDK offer를 받고 answer/ICE를 orch를 통해 돌려준다. MediaRelay로 viewer마다 별도 peer를 생성해 다중 viewer와 recorder 수명을 분리한다. Worker는 공개 포트를 노출하지 않는다.
- recording은 QA 시작에 구동되며 browser 접속과 무관하게 stream lease를 갱신한다. 대기 중 유지, 마지막 QA 종료 5초 뒤 종료. 기존 viewer lease는 recorder를 멈추지 않는다.
- 시간 구간별 MP4 H.264 segment를 worker에서 encode하고 orch의 저장 계약으로 S3 업로드. 메모리에 전체 영상 누적 금지. segment 시작·끝·오류를 DB에 기록해 누락을 표현한다.
- segment 완료 시각부터 30일 expiry로 장기 QA도 정리. 접근은 멤버 확인 후 짧은 presign URL 반환. 정리 scheduler는 S3 삭제 성공 뒤 segment EXPIRED로 변경하고 판정·평가는 유지.
- worker 재시작/SDK 끊김/인코딩·업로드 실패는 gap으로 기록하며 QA 계속. 재연결은 새 segment. time mapping은 서버 session epoch와 segment media timestamp를 사용한다.
- media 기본 설정은 비활성으로 배포 호환, 활성 설정과 worker 실행 구성을 문서화. UI는 비활성/저장 실패/만료를 구분한다.

### Agent tool과 질문 대기 추가

- start_test_case(case_id)로 attempt 생성, report_test_case(case_id, verdict, message)로 종료. tool은 현재 scenario 소속 case만 허용하고 attempt UUID는 agent 내부에서 만들어 재시도 때 유지한다. 모델이 UUID를 입력하지 않는다. 피드백은 scenario composition 결과를 실행 context에 전달한다.
- report_step/report_case를 tool 목록에서 제거한다. 서버가 명시 attempt와 원본 STATUS를 같은 transaction에서 저장한다. 역사적인 STATUS 수신 경로는 계속 호환한다.
- ask_user(question)는 질문을 생성하고 첫 답변까지 await. 실행 timeout에서 질문 대기 시간을 제외하고 cancel/disconnect는 전파. session의 다음 scenario 진행도 대기가 끝날 때까지 멈춘다.
- 일반 report_issue는 TC 실패 자동 issue와 중복되지 않도록 tool description과 closing asks 수정.
- QA_ARCH_LABEL 갱신, 새 prompt version, 계약 테스트 및 같은 설정의 before/after 실제 run 결과 기록.

### Home 화면 연결 추가

- QA history/TC 상세에서 동일 attempt list·video player·평가 form·review history 컴포넌트를 사용.
- segment 목록을 절대 시각 기준으로 연결하고 시작 -10초/보고 +5초로 제한. 미디어 경계는 clamp, gap은 명시 표시. 중단은 중단 시각을 종료점으로 사용.
- 프로젝트 신뢰도 화면에 전체·일별·TC별 지표, 분모·검토율·선택 편향·중단 FN 표시. 버전 비교 없음.
- 프로젝트 구독 토글, permission 요청은 사용자 클릭에서 수행. SSE 수신 시 구독자만 Notification, 권한 거절 시 화면 질문은 유지. 질문 답변 충돌은 이미 채택된 답변을 표시.
- issue에 TC/QA history/검증 구간 링크, occurrence 목록, 오탐·수동 해결·정정·재발 표시.
- 기존 semantic tokens·i18n·멤버 프로젝트 shell 재사용. 다크/라이트, 모바일·데스크톱, 키보드 확인.

## Validation

- **Commands to run:** server ./mvnw test (Docker pgvector 필요), agent python -m pytest, home npm test / npm run typecheck / npm run lint / npm run build. 미디어 worker의 합성 프레임 녹화·재생과 다중 viewer 테스트.
- **Expected output:** 실패 0, migration upgrade 성공, 모든 예외 상태 전이 및 외부 프로젝트 접근 거절 확인. 실제 QA before/after와 화면 검증은 실행 환경 준비 후 수행하며 미실행을 성공으로 보고하지 않는다.
- 동시 평가, 동일 이벤트 재전송, 첫 답변 경합, TC 재발/오탐 정정, 만료 후 metadata 보존, worker 죽음/브라우저 이탈 검증을 포함한다.

## Risks & Rollback

- **Risks:** WebRTC codec·ICE·NAT, encode CPU·저장 부하, 무기한 대기의 실행 자원 유지, 늦은 이벤트와 issue 경합.
- **Rollback steps:** media 비활성화, 소비자 배포 철회. additive 테이블은 보존하며 사용자 평가 삭제 migration은 만들지 않는다. 기존 streaming fallback은 명시 설정으로만 사용하고 녹화됨으로 오인시키지 않는다.

## Open Questions

위 세부 정책은 구현 제안이다. plan-review에서 정책 충돌·불충분한 검증을 먼저 확인한다. 사용자가 확정한 요구사항을 축소하지 않는다.

## Review 반영과 기존 PR 재사용

아래 결정은 앞 절의 충돌하는 제안을 대체한다.

- 기존 서버 PR #378(ARTEL-1256, #377/#376/#375 포함), agent #270(ARTEL-1257), home #225(ARTEL-1255) 위에 stack한다. qa_verdict_review 및 기존 알림/SSE·피드백 DTO를 확장하며 병렬 평가 저장소를 만들지 않는다. 명시 attempt는 원본 STATUS log에 연결하고 기존 평가 API도 같은 revision 기록 경로를 사용한다.
- 오탐 정정은 반드시 원래 자동 종료 issue를 재개한다. 다른 열린 issue가 있으면 그 발생 이력을 원래 issue로 병합하고 병합 관계를 보존한다. TC ID별 advisory transaction lock으로 단일 열린 issue 조건을 유지해 TC 삭제 후 평가도 직렬화한다.
- 질문·녹화 소유권은 qa_run 또는 단독 qa_try다. 소유 키는 run:<id>/try:<id>로 충돌 없이 구분한다. 여러 scenario는 run 하나로 녹화가 이어진다.
- SDK ingress 소유권은 instance별 하나의 서비스로 모은다. QA recording 참조와 viewer 참조를 따로 유지하고 둘 다 없어질 때만 중지한다. 뷰어가 새로 붙거나 끊겨도 recorder의 streamId는 바뀌지 않는다.
- legacy STATUS는 관측하지 않은 시작 시각을 만들어내지 않는다. startKnown=false, 시작 시각 null, 보고 주변 구간이라는 표시를 사용한다. message_id 멱등키와 attempt_id 연결을 사용하며 명시 report→STATUS와 STATUS→report 모두 하나의 시도에 연결한다.
- worker HTTP 제어 API는 내부망 전용이다. 미디어 연결은 TURN relay 경로를 지원하고 worker와 SDK·브라우저에 같은 ICE 설정을 전달한다. 외부 네트워크에서 relay candidate로 실제 연결하는 검증이 필요하다. 이 검증 전 운영 가능하다고 보고하지 않는다.
- segment 60초, instance당 미업로드 segment 10개/총 256 MiB 중 먼저 도달하는 상한, 업로드 3회 재시도 후 gap 기록·파일 제거. viewer는 최신 프레임만 유지해 느린 소비자가 메모리를 늘리지 않는다. 최대 동시 ingress/viewer 수는 설정으로 제한한다.
- 기존 ProjectChangeStreamManager에 질문 topic 추가. 알림은 앱이 열려 연결된 구독자에게 보내며, 재연결 시 미응답 질문 재조회. 질문 ID와 localStorage로 탭 간 중복 알림 억제. 닫힌 앱까지 알리는 Web Push는 구현했다고 주장하지 않는다.
- 구조 before/after 비교는 동일 model·prompt_version으로 실행하고, 새 prompt의 통합 검증을 별도 실행한다. 통합 결과를 순수 구조 개선 근거로 사용하지 않는다.
- Fast/medium 리뷰의 위 필수 사항을 반영했으며 heavy 리뷰에서 최종 확인한다.

## TC 판정 단위 수정

- 사용자 추가 결정: step은 참고 절차이며 독립 판정이나 완료 의무의 대상이 아니다.
- agent에 report_step/report_case를 노출하지 않는다. start_test_case와 report_test_case로 TC 검증 시도를 기록한다.
- step별 보고를 요구하는 실행 안내, finish_run의 step 완료 검사, 압축 후 step 진행 강제 문구를 제거한다.
- TC 미검증·판단 불가를 실패로 바꾸지 않는다. 각 검증 시도의 원래 결과와 최신 TC 결과를 분리하고 원본 시도는 보존한다.
- action의 step 번호는 기존 로그·macro 호환용 참고 위치일 뿐 판정 키가 아니다. 기존 QA history의 step 판정 원본은 유지한다.

## 최종 검증에서 확인한 수정

- 같은 scene 간 여러 조작이 있을 때 DB 조회 순서에 따라 대표 조작이 달라지는 문제를 수정한다. 정순·역순 rows를 주는 회귀 테스트로 동일한 결과를 확인한다.
- SDK 연결이 스트림 시작 중 끊기거나 SDK가 실패 상태를 보내면 START를 재시도한다. 협상이 끝나지 않는 연결은 60초 뒤 다시 만든다. 재연결의 늦은 시그널이 현재 연결을 방해하지 않도록 검증한다.
- 모바일 평가 화면에서 긴 선택 항목이 grid 최소 폭을 늘리는 문제를 수정한다. 전체 문서 폭뿐 아니라 내부 control의 실제 경계를 검사한다.
- 실제 Unity QA의 변경 전·후 비교는 LLM 복호화 설정이 없어 미실행이다. 자동 테스트와 합성 WebRTC·S3 검증 결과와 구분해 문서와 PR에 남긴다.

## 최종 제출 결과

- 서버 [PR #383](https://github.com/project-artel/artel-orchestration-server/pull/383): 중단 전·재개·수정 후 검증을 중복 제외해 257개 클래스·2,341개 항목 통과. worker 6개 통과.
- agent [PR #275](https://github.com/project-artel/artel-agent-server/pull/275): 전체 2,889개 통과, 마지막 prompt 정리 후 85개 통과.
- home [PR #228](https://github.com/project-artel/artel-home/pull/228): 전체 1,498개, 평가 모듈 12개, typecheck·lint·build 통과. 최종 실제 API 화면 캡처 10개를 PR에 포함했다.
- 사용자가 세 draft PR의 선제 생성을 승인했다. 서버 merge·API 배포 후 agent/home을 적용하는 순서는 유지하며 merge·배포·ready 전환은 하지 않았다.
