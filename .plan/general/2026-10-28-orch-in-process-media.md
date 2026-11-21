# orch 프로세스 내부 영상 중계·저장 적용

## Goal

사용자가 거부한 별도 media-worker를 삭제한다. orch JVM 프로세스 안에서 WebRTC 수신·viewer 중계와 H.264 MP4 변환·S3 저장을 수행한다. 별도 서비스·HTTP worker·FFmpeg 자식 프로세스를 만들지 않는다.

## Approach

- 기존 PR #383/ARTEL-1269를 수정하며 UI·agent 계약과 DB migration은 유지한다.
- webrtc-java의 JNI peer와 CustomVideoSource로 수신 프레임을 viewer에 중계한다. JavaCV/FFmpeg JNI로 MP4를 인코딩한다. native 라이브러리는 orch 프로세스에 로드한다.
- QaMediaRelay의 worker HTTP 호출을 타입 있는 내부 서비스 호출로 교체한다. 기존 SDK·viewer offer/answer/ICE 계약을 유지한다.
- SDK ingress의 녹화 소유권과 viewer 소유권을 분리한다. 접속 지연, 끊김, 재연결, 늦은 시그널, QA 종료 후 5초, shutdown을 검증한다.
- native callback에서 프레임을 retain하고 bounded queue를 통해 전용 인코딩 thread에 넘긴다. 모든 성공·실패·drop·close에서 release한다. 영상은 최대 60초/32MiB segment, 업로드 대기 최대 10개/256MiB, 업로드 3회 재시도 후 gap 기록을 유지한다. 느린 viewer가 프레임을 무제한 쌓지 않게 한다.
- QaRecordingStore와 DocumentStorage를 직접 호출해 segment·gap·S3 객체를 기록한다. 업로드 실패로 QA를 중단하지 않는다. 30일 삭제와 접근 권한은 유지한다.
- media-worker 폴더, compose.media.yml, worker URL 설정·전용 업로드 HTTP API 및 관련 테스트를 제거/대체한다. 필요한 native 런타임과 임시 저장 공간만 기존 orch 배포 설정에 포함한다.
- 저장소 문서, 기존 PR 본문, 개인 Notion 문서를 수정해 분리 구조 설명을 현재 구현으로 교체한다. 과거 검증을 새 구조의 증거로 제시하지 않는다.

## Validation

- 완료: commit `e45569cff64a5ffd5d9673c73573980b45c0a4c7`, 서버 PR #383에 push. Jenkins PR CI 통과, draft 유지.
- 계획 검토와 최종 pair review PASS. Kotlin 회귀 10개 클래스·55개 항목, JAR package 및 실제 Docker build 통과.
- 실제 orch WebSocket→viewer→S3 경로에서 757 frames MP4 decode, 같은 JVM 재접속 후 590 frames 저장 통과. orch 자식 프로세스 없음과 Docker PID 1의 native WebRTC·H.264 인코딩 확인.
- 서버·agent·home 요구사항 및 개인 Notion 문서 수정 완료. home의 다른 작업은 보존했다.
- 실제 Unity QA 비교, 외부 TURN과 운영 장시간 부하는 이번 검증 범위에 포함하지 않았다.

## Review 반영

- 동시 ingress 8개, ingress당 viewer 8개, ingress당 raw frame 3개/8MiB 중 먼저 도달하는 상한, 입력 최대 1920×1080으로 제한한다. 초과 프레임은 즉시 drop/release한다. ingress별 인코딩 thread 1개와 FFmpeg thread 1개, 업로드 thread는 전역 2개로 제한한다. 종료 중 ingress도 동시 연결 수에 포함한다.
- 업로드 대기열은 서버 전체 10개/256MiB로 제한하고 포화 시 segment gap을 기록한다. 전체 실행 영상은 메모리에 누적하지 않는다. segment 한 개의 업로드 데이터도 최대 32MiB다.
- 스트리밍이 활성화되면 반드시 orch 내부 relay를 사용한다. native 초기화는 lazy이며 실패해도 Spring 서버 자체는 시작하고 QA는 계속한다. 실패를 표시하고 SDK↔브라우저 직접 P2P로 자동 전환하지 않는다.
- 종료는 callback 입력 차단 → retain한 queue drain/release → 마지막 segment finalize → 제한 시간 내 업로드 drain 및 실패 gap → peer/track/source 해제 → factory 해제 순이다. close는 멱등이며 부분 초기화 실패도 정리한다. 종료 중인 작업의 native 객체를 강제로 해제하지 않는다.
- recorder는 HTTP나 presigned URL을 통해 자기 서버로 업로드하지 않는다. QaRecordingStore의 내부 저장 메서드에서 기존 segment 검증/멱등성을 재사용하고 DocumentStorage에 직접 저장한다. S3 확인 후 READY로 바꾸며 실패/종료 시 gap과 임시 파일 정리를 수행한다.
- Linux 런타임 classifier를 명시하고 실제 배포 Docker 이미지에서 .so 로딩·디렉터리 쓰기와 H.264 MP4 encode를 검증한다.
- 첫 수신 프레임의 서버 Instant와 monotonic nanoTime을 함께 고정한다. 후속 프레임의 도착 간격을 MP4 PTS로 전달하고 segment endedAt은 마지막 PTS와 한 프레임 길이로 계산한다. 프레임 drop·입력 정지 시간을 프레임 수로 압축하지 않는다. 재연결·해상도/회전 변경은 새 segment를 시작하며 정지·drop 합성 입력으로 metadata와 decode한 시간축을 비교한다.

## 최종 검증 항목

- 의존성 API와 Linux native 로딩을 실제 확인하고 버전을 고정한다.
- 실제 WebRTC SDK 합성 track → orch WebSocket/JVM → viewer, browser 종료 뒤 녹화, MP4 decode 및 S3 저장·재생을 검증한다. 재연결과 종료·실패 경로, 대기열 상한을 테스트한다.
- 영향받은 Kotlin 테스트 및 회귀 테스트, package/Docker runtime 검증과 diff review를 수행한다. 무관한 전체 suite는 동일 코드 재검증을 반복하지 않는다.
- 실행 중 별도 media-worker/미디어 자식 프로세스가 없음을 확인한다.
- PR #383에 commit/push하고 관련 PR #275/#228의 배포 설명을 필요한 범위만 갱신한다. Claude의 UI 작업은 건드리지 않는다.
