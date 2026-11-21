# 2026-10-28 — orch 경유 WebSocket 영상 전송 추가

- Date: 2026-10-28
- Jira: ARTEL-1269, ARTEL-1271, SDK subtask to be linked
- Status: Complete

## Goal

Windows Unity에서 WSL orch로 영상이 오지 않는 문제를 고친다. 별도 TURN·worker와 UDP 의존 없이 기존 인증된 WebSocket으로 영상을 전송하고 orch JVM에서 브라우저 중계·H.264 MP4 변환·S3 저장을 수행한다.

## Non-goals

TC 평가 화면 재배치, 음성, 모델 판정 개선, 방화벽·WSL 전역 설정 변경은 포함하지 않는다.

## Context / Constraints

서버 PR #383과 home PR #228을 재사용한다. Claude의 최근 UI 변경을 보존한다. 전체 영상·30일 보관·10초 전/5초 후·대기 중 녹화 정책과 API·DB를 유지한다. WSL host LAN UDP 왕복 실패가 관찰됐으며 proxy를 127.0.0.1로 바꿔도 영상이 오지 않았다.

## Approach (Checklist)

- [x] **Step 0: Recon** 기존 SDK `/ws/sdk`, viewer `/ws/viewer`, QaMediaRelay와 recorder를 확인한다.
- [x] **Step 1: Implementation** Wire contract는 아래와 같다. 기존 SDK 인증·권한·소유권 검사를 재사용하며 새 서비스/미디어 포트는 만들지 않는다.
  - `STREAM_START`에 `transport: "JPEG_WS"`와 video `maxWidth:1280`, `maxFramerate:10`, `jpegQuality:65`, `maxFrameBytes:131072`를 전달한다. cap은 서버에서 강제한다.
  - SDK는 `STREAM_FRAME {streamId,frameId,jpeg}` JSON을 보낸다. jpeg는 JPEG byte의 base64이며 decoded 128KiB·JSON 184KiB 상한, width≤1920·height≤1080·pixel budget을 확인한다. 헤더 metadata를 decode 전에 검증한다. 프레임 ID는 stream별 증가하고 재전송/늦은 연결은 무시한다.
  - 서버는 `STREAM_FRAME_ACK {streamId,frameId,accepted}`를 SDK로 보낸다. SDK는 ACK 전 새 frame을 보내지 않고 최신 화면을 다음 tick에 잡는다. 네트워크 전송은 main thread를 막지 않으며 최대 전송 1개와 ACK 대기 1개만 허용한다. ACK 10초 미수신은 session 실패로 보고하고 서버가 새 streamId로 재시작한다. stop/reconnect 후 늦은 callback이 새 stream을 건드리지 않는다.
  - orch는 활성 owner의 stream·SDK session을 검사하고 bounded queue로 JPEG를 녹화 인코더에 전달한다. 디코드/인코드는 encoder thread에서만 실행하며 raw 3개/8MiB, JPEG 128KiB/frame, 영상 최대 1920×1080과 업로드 10개/256MiB 상한을 유지한다. frame timestamp는 서버 수신 Instant+monotonic clock을 사용한다.
  - viewer에는 `STREAM_FRAME {streamId:<viewer id>,frameId,jpeg}`를 전송한다. viewer별 최신 frame 1개만 대기시키며 control queue는 별도 bounded queue로 유지한다. 느린 viewer가 SDK/녹화·다른 owner를 막지 않는다. 영상 frame은 서버의 codec metadata 검증을 통과한 것만 중계한다.
  - 브라우저는 WebSocket JPEG를 decode하고 기존 게임 화면 영역에 표시한다. frame 하나만 decode하며 늦은 decode·object URL은 정리한다. 첫 frame 전 connecting, frame 갱신 중 live, 5초 frame 미수신은 stale/retry다. 기존 접근 권한·교체·lease·annotation·화면 디자인과 문구를 보존한다.
  - 별도 WebRTC ingress/egress peer·SDP/ICE를 제품 전송 경로에서 제거한다. 기존 WebRTC-only SDK와의 호환을 조용히 성공 처리하지 않는다. SDK 업데이트 필요 오류를 표시한다. 녹화는 H.264 MP4 JNI로 orch 내부에서 처리한다.
- [x] **Step 2: Tests** 잘못된 base64/JPEG/크기·metadata bomb·늦은 ID·권한·ACK·backpressure·slow viewer·연결 교체·viewer 없어도 녹화·종료 5초·업로드 실패·PTS 회귀를 검증한다. 실제 Unity→WSL orch→Windows 브라우저에서 움직이는 프레임과 저장 MP4 decode를 확인한다. 합성 클라이언트를 실제 Unity 검증으로 제시하지 않는다.
- [x] **Step 3: Rollout / Rollback** 서버·SDK·home 계약을 함께 배포한다. draft PR에 의존성과 새 검증을 기록하고 문서·Notion을 갱신한다. 이전 버전으로 동시 rollback하거나 스트리밍을 끄고 판정·평가 이력은 유지한다.

## Validation

### Review 반영

- 기존 SDK WebSocket 256KiB 메시지 상한을 유지한다. JPEG는 128KiB, frame JSON은 UTF-8 184KiB 상한으로 줄인다. fragment 합계·제한 초과·기존 일반 메시지 제한 회귀를 검증한다.
- SDK frame ACK는 기존 무제한 control sink에 넣지 않는다. 별도 replay-latest(1) sink와 merge prefetch=1로 마지막 ACK 하나+전송 중 하나만 유지한다. ACK를 소비하지 않는 SDK의 flood가 ACK 메모리를 늘리지 않는 테스트를 추가한다. frame rate 위반 시 추가 디코드 없이 거부한다.
- ACK는 전송 flow-control이며 active stream의 frame 검증·전송률 확인 결과다. recorder queue가 가득 차도 viewer는 갱신하고 ACK accepted=true로 다음 frame을 허용한다. 잘못된 형식은 accepted=false, stale·중복·rate limit도 false이며 이전 ACK 수신 여부와 관계없이 서버가 강제한다. false는 SDK의 다음 capture를 허용한다. 최대 10fps·약 1.3MiB/s decoded JPEG를 서버에서 제한한다.
- SDK는 STREAM_STATE CONNECTING에 transport=JPEG_WS capability를 보낸다. 구 SDK가 WEBRTC_OFFER를 보내거나 capability가 10초 이내 확인되지 않으면 SDK_UPDATE_REQUIRED를 recording error와 viewer STREAM_ERROR로 전달한다. home은 protocolVersion/transport 불일치를 재시도 루프로 숨기지 않고 signalling 오류 상태로 표시한다.
- SDK 수신은 Netty payload를 즉시 immutable 문자열로 복사한 뒤 concatMap한다. prefetch는 1로 제한하고 초과 크기는 복사 전에 거부한다. 같은 socket의 frame을 1개만 허용하는 SDK 구현과 별도로 서버의 byte/frame rate admission을 적용한다.
- raw decode budget은 queued+inflight pixel width×height×4에 JPEG 크기까지 합산해 ingress당 8MiB·3개 이하다. metadata 검사 후 decode와 encode는 단일 encoder thread에서 수행한다. viewer도 최신 frame 1개와 control 16개/64KiB만 보관한다.
- 실제 로컬 검증에서 JPEG encode 시간·평균/최대 bytes와 frame 전송 중 QA action 왕복 지연을 기록한다. 로컬 command action p95는 500ms 이하, main-thread JPEG encode p95는 33ms 이하를 목표로 하며 초과 시 fps/width를 줄여 재검증한다. 이는 네트워크 RTT가 큰 운영 환경의 보장값이 아니다. stop/reconnect는 느린 송신 callback을 기다리지 않는다.

- **Commands to run:** 영향 Kotlin/TS/Unity 테스트, package/typecheck/lint/build, 실제 Unity 세션의 viewer frame progression과 S3 MP4 decode.
- **Expected output:** 브라우저의 게임 화면이 갱신되고 저장 MP4의 장면이 실제 게임과 일치한다. orch 외 미디어 worker·TURN·인코더 자식 프로세스는 없다.

## Risks & Rollback

- **Risks:** JPEG over WebSocket은 WebRTC보다 대역폭·JPEG encode CPU를 더 사용한다. 1280px/10fps/quality65와 ACK·queue 상한으로 비용을 제한한다. 같은 SDK socket의 control head-of-line 지연을 실제 QA 액션과 함께 측정한다. 필요하면 별도 인증된 media WebSocket으로 분리하되 별도 프로세스는 만들지 않는다.
- **Rollback steps:** 서버·SDK·home을 함께 이전 버전으로 복원하거나 스트리밍만 비활성화한다. DB·S3 영상과 평가 이력은 보존한다.

## Open Questions

없음. 세부 구현에서 전송량·메인 스레드 지연은 실제 검증 결과와 함께 기록한다.

## 추가 요청: 여러 viewer와 QA history 링크

사용자는 2026-10-28 여러 화면에서 동시 스트리밍을 요청했다. ViewerSessionRegistry의 인스턴스별 최신 한 명 교체 정책을 최대 8명 독립 viewer로 바꾼다. 기존 프로젝트 멤버 권한 검사는 각각의 WebSocket에 그대로 적용한다. 전역 registry lock은 map 변경에만 쓰고 네트워크 전송·종료를 기다리지 않는다. 상한 초과 접속은 1013으로 닫고 기존 viewer를 유지한다. streamId는 각 viewer마다 다르다.

QaMediaRelay의 Owner는 viewer ID 집합을 관리한다. viewer가 하나라도 남거나 QA recording이 활성화된 동안 SDK ingress와 lease를 유지한다. 한 viewer가 닫히면 해당 ID만 정리하고, 모두 닫힌 뒤에도 녹화가 있으면 계속한다. 같은 owner의 재시작은 모든 등록 viewer에 새 STREAM_READY를 보내고 재등록하며, 이전 소켓의 늦은 close가 새 소켓을 제거하지 않게 한다. JPEG frame과 control 대기는 viewer별 독립 상한을 적용한다.

동일 instance의 두 viewer가 각자의 streamId로 frame을 받음, 한 viewer 종료 후 다른 viewer와 녹화 유지, 마지막 viewer 종료 시 stop, 8개 한도와 동시 admit/release·늦은 close를 검증한다. 실제 두 viewer 수신 client도 동시에 연결해 frame 증가를 확인한다. 이번에는 검증 client가 사용자의 시청을 대체하지 않는다.

QA history에서는 테스트 런 이름을 기존 목적지의 Link로 바꾸고 중복 열기 버튼을 제거한다. 실제 QA 실행의 액션·대화·활동 로그 화면으로 가는 링크 세 곳만 '실행 기록'으로 바꾼다. TC 배치·차트·다른 timeline 명칭은 바꾸지 않는다.

## 최종 구현과 검증

- 서버 commit 427d526f / PR #383, SDK commit 57114f4 / PR #174, home code aadcee2·문서 f43a51f / PR #228, agent 문서 fa30d69 / PR #275를 push했다. draft 상태를 유지한다.
- 서버 14개 클래스·83개와 JAR package, SDK GPU 670개, home 1509개 테스트·typecheck·build·수정파일 lint 통과. 계획 검토와 최종 pair review PASS.
- 실제 Windows Unity의 정상 방향 JPEG 40개 약9.37fps와 실제 QA6 S3 H.264472frames/약54.57초 decode를 확인했다. 실제 viewer2개 동시수신과 첫viewer종료후둘째1→13 frame 증가도통과했다.
- 최종Docker build와동일이미지 PID1 JPEG→H264 encode/decode·방향보존·자식프로세스0 통과. 로컬 orch PID136434에검증한최종JAR적용. 시작 전사용자실행중QA없음확인.
- Notion개인문서15절과저장소요구사항·프로토콜·검증문서를갱신했다. 실제FirefoxUI자동검증은도구의Windows브라우저지원제한으로중단했다.
- 운영장시간부하, JPEGencode p95·느린외부TCP의QAaction p95는미측정이다. 기존home전체lint오류5·경고4는수정범위밖이다. SDK·home·agent·서버의 최신 CI가 모두 통과했다.
