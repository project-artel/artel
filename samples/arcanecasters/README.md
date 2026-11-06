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
