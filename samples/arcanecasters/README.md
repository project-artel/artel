# ArcaneCasters 로컬 QA 스택

WSL에서 이 디렉터리를 열고 실행합니다. Docker Compose, Python 3, OpenSSL이 필요합니다.

```bash
bash qa/up.sh
docker compose ps -a
```

`qa/up.sh`는 첫 실행에 `.env.example`을 `.env`로 복사하고, `.qa/`에 로컬 RSA 키와 서버용 JWT를 만듭니다. Compose는 Postgres, Redis, Account, Lobby, Game을 띄우고, Flyway가 Game 스키마를 적용한 뒤 테스트 계정 두 개와 시작 덱을 준비합니다. `migrate` 컨테이너의 정상 종료 코드는 0입니다.

`GAME_MIGRATIONS`는 ArcaneCasters DB 저장소의 `migration/` 경로입니다. 기본 경로를 사용하면 첫 실행에 DB 저장소의 `dev`를 `.qa/database`로 가져옵니다. 기존 DB 체크아웃이 있다면 `.env`에서 그 경로를 지정할 수 있습니다.

Account 기본 이미지는 `ghcr.io/apptive-game-team/account-server:dev`입니다. GHCR 접근 권한이 없고 로컬에 Account 소스가 있다면 아래 명령으로 빌드한 뒤 `.env`의 `ACCOUNT_IMAGE`를 `arcanecasters-qa-account:local`로 설정합니다.

```bash
docker build -t arcanecasters-qa-account:local ../../../ArcaneCasters/account
```

## Unity 로컬 QA 접속

Windows에서 Unity Editor 또는 Development Build를 실행할 프로세스에 `ARCANECASTERS_LOCAL_QA=1`을 설정합니다. PowerShell에서 실행하는 예입니다.

```powershell
$env:ARCANECASTERS_LOCAL_QA = '1'
& "C:\Program Files\Unity\Hub\Editor\2022.3.34f1\Editor\Unity.exe" -projectPath (Resolve-Path .\arcanecasters-client)
```

이 모드의 Unity는 Lobby `127.0.0.1:6209`와 Account `127.0.0.1:6210`을 사용합니다. Game은 기본적으로 `127.0.0.1:7777`에서 접속을 받습니다. 로그인 계정은 `qa1@arcanecasters.test`와 `qa2@arcanecasters.test`이며 비밀번호는 `.env`의 `QA_ACCOUNT_PASSWORD`에 있습니다. 듀얼은 각 클라이언트에서 상대 `memberId`인 `2`와 `1`을 입력합니다.

`docker compose down`으로 스택을 내립니다. Postgres 데이터는 Compose 볼륨에 유지됩니다.

## Workflow 기대값 검증 결과 (2026-11-24)

[Stage 실행 #466](https://home.stage.artel.kr/projects/53/qa-runs/466)에서는 ordered 시나리오 #311의 행동과 사전조건을 유지하고, TC 17개 중 8개의 기대값만 반대로 바꿨습니다. 게임 1.6.5(빌드 #71), [SDK #212](https://github.com/project-artel/artel-sdk/pull/212)의 커밋 `c8b4d79`, Workflow(`engine=agent`), Anthropic 직접 연결 Sonnet 5.5로 한 번 실행했습니다. 추정 비용은 $38.75였습니다.

| 실제 입력과 게임 상태로 확인한 결과 | Agent PASS | Agent FAIL | Agent 판정 보류 | 합계 |
|---|---:|---:|---:|---:|
| 기대값과 일치 | 5 | 0 | 0 | 5 |
| 기대값과 불일치 | 0 | 5 | 1 | 6 |
| 행동·사전조건·관찰 근거 부족 | 2 | 1 | 3 | 6 |
| **합계** | **7** | **6** | **4** | **17** |

- **오탐**은 실제로 기대값과 일치한 5건 중 0건이었습니다.
- **미탐**은 실제 불일치를 PASS로 처리한 경우만 세면 0건입니다. 실패 알림을 놓친 경우까지 포함하면 6건 중 1건입니다. 로그인 TC #3308에서 실제로 로비가 열려 “로그인 화면에 남는다”는 기대값이 틀렸지만 Agent는 판정을 보류했습니다.
- **실패 검출률은 5/6(83%)**이었습니다. 전체 17건 중 독립적으로 결과를 확인한 건 11건이고, 올바른 PASS·FAIL까지 확인한 건 10건(59%)입니다. TC #3194·#3195에서는 다른 덱을 편집했고, #3314에서는 앞서 거절된 동일 카드로 재시도했는지 확인하지 못했습니다. 한 시나리오를 한 번 실행한 수치입니다.

후속 빌드 1.6.6(#72)에는 실제 카드 시전 요청 ID와 응답을 대조하는 관찰값을 추가했습니다. 별도 로컬 서버 검증에서 마나 부족 응답을 확인했고, 마나를 채워 같은 적에게 다시 시전했을 때 HP가 20에서 −180으로 줄었습니다. 빌드 #72에서 Unity UI를 통한 최종 타격·승리와 전체 Workflow 재실행은 아직 검증 전입니다.
