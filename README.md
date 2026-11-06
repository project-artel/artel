# ARTEL

ARTEL은 QA agent가 Unity 게임을 직접 플레이해 테스트하는 도구입니다. 테스트 케이스를 실행하면 agent가 화면과 게임 상태를 확인해 클릭과 키 입력을 보냅니다. 실행이 끝나면 Replay Studio에서 케이스별 판정을 보고, 녹화가 남아 있는 구간은 해당 시점의 게임 화면과 로그를 함께 확인할 수 있습니다.

이 저장소는 ARTEL의 서비스와 Unity SDK를 Git submodule로 모아 둔 루트 저장소입니다.

[ARTEL 서비스](https://artel.kr) · [Unity SDK 설치](https://github.com/project-artel/artel-sdk#install) · [Docker 설치](deploy/README.md)

## ARTEL로 할 수 있는 일

- **실제 게임 빌드에서 테스트합니다.** QA agent가 게임 화면과 Unity 상태를 읽고 입력을 보냅니다. 메뉴에서 새 게임을 시작하거나 전투 도중 설정을 열고 닫는 것처럼 여러 화면에 걸친 동작을 테스트할 수 있습니다.
- **판정이 나온 시점으로 이동합니다.** Replay Studio의 타임라인에서 케이스별 검증 구간으로 이동해 당시 게임 화면과 로그를 함께 확인할 수 있습니다.
- **Unity 패키지로 연결합니다.** Unity Package Manager에서 SDK를 설치합니다. SDK는 Unity 에디터와 개발 빌드에서 동작하며, 출시 빌드에는 포함되지 않습니다.

## WordVenture QA 실행 사례

2026년 11월 4일에 실행한 WordVenture의 QA run 12에서는 타이틀 화면에서 시작해 전투 중 설정 메뉴, 스테이지 첫 클리어 보상, 플레이어 HP가 소진된 뒤 게임 오버 전환 등을 포함한 테스트 케이스 16개를 검증했습니다. agent가 케이스 순서를 정하는 방식으로 실행했으며, 케이스 9개가 통과했고 전체 실행 상태는 실패로 기록됐습니다.

Replay Studio에는 타이틀 화면 녹화와 케이스별 검증 구간, 실행 로그가 남았습니다. 예를 들어 타임라인에서 `TC-001`의 0:31–1:49 구간으로 이동해 해당 시점의 화면과 로그를 살펴볼 수 있습니다.

## 샘플 게임

| 게임 | 프로젝트 | 설명 |
| --- | --- | --- |
| ArcaneCasters | [Unity 클라이언트](samples/arcanecasters/arcanecasters-client) · [Lobby 서버](samples/arcanecasters/arcanecasters-lobby) · [Game 서버](samples/arcanecasters/arcanecasters-game) | 카드 기반 대전 게임 |
| Match 3 Unity | [Unity 프로젝트](https://github.com/project-artel/match3-unity) | 같은 종류의 타일을 맞추는 매치 3 퍼즐 |
| Survivors Roguelike Kit | [Unity 프로젝트](https://github.com/project-artel/survivors-roguelike-kit) | 생존형 로그라이크 게임 템플릿 |
| Living Dead FPS | [Unity 프로젝트](https://github.com/project-artel/living-dead-fps-3d-shooting-game) | 3D 좀비 FPS |
| WordVenture | [Unity 프로젝트](https://github.com/project-artel/word-venture) | 단어와 카드를 사용하는 턴제 전투 게임 |

## 설치와 로컬 개발

- **내 Unity 게임에 연결**하려면 [Unity SDK 설치 안내](https://github.com/project-artel/artel-sdk#install)를 따릅니다.
- **ARTEL을 직접 운영**하려면 [Docker 설치 안내](deploy/README.md)를 따릅니다.
- **이 저장소에서 개발**하려면 루트에서 submodule을 초기화한 뒤 [개발 명령어 안내](DEV_TOOL.md)를 확인합니다.

```sh
git submodule update --init --recursive
```

Console에서 QA를 요청하면 Orchestration Server가 테스트 케이스를 QA Agent Server에 전달합니다. QA agent는 Orchestration Server를 통해 Unity 게임의 상태를 읽고 입력을 보내며, 팀은 Replay Studio에서 실행 기록을 확인합니다.

| 구성 요소 | 역할 |
| --- | --- |
| [artel-home](artel-home) | 테스트 케이스 관리, QA 실행, Replay Studio |
| [artel-orchestration-server](artel-orchestration-server) | QA 실행 관리, SDK와 QA agent 간 요청 중계 |
| [artel-agent-server](artel-agent-server) | 게임 상태 관찰, 다음 행동과 테스트 결과 판단 |
| [artel-sdk](artel-sdk) | Unity 상태 수집, 화면 캡처, 클릭과 키 입력 전달 |
| [artel-cli](artel-cli) | 터미널에서 QA 실행과 결과 조회 |
