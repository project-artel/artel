# ARTEL 개발 명령어 추가

Windows PowerShell에서는 `./dev.ps1`, Git Bash와 WSL에서는 `./dev`를 사용합니다.
명령을 생략하면 사용 가능한 목록을 표시합니다.

```powershell
./dev.ps1 local status
./dev.ps1 local revisions
./dev.ps1 local logs agent --lines 40
./dev.ps1 game path
./dev.ps1 game build
```

## 로컬 실행 환경 조회

`local`은 이미 준비된 PR 실행 환경을 관리합니다. WSL Ubuntu의
`~/dev/artel/.work/latest-pr-local-*`에서 `pids.json`과 `server.env.json`이 있는
최신 폴더를 찾습니다. 다른 폴더는 `--runtime <WSL 경로>`로 지정합니다.
설정을 새로 만들거나 운영 데이터를 복사하지 않습니다.

`status`, `revisions`, `logs`는 프로세스를 시작하거나 중지하지 않습니다.
`up`은 기존 시작 스크립트를 사용하며, 모두 실행 중이면 PID를 유지합니다.
일부만 실행 중이거나 다른 서비스가 포트를 사용하면 중단합니다.
`down`은 실행 경로와 PID가 일치하는 서비스만 중지하며 게임과 DB container는 유지합니다.
로그인 URL은 로컬 테스트 사용자 세션을 발급합니다.

웹은 `http://127.0.0.1:5176`, 서버는 `8090`, agent는 `8000`입니다.
현재 로그인은 `http://127.0.0.1:5177/login`에서 시작할 수 있습니다.

## 게임 빌드 추가

`game build`는 `.work/latest-pr-local-*`에 준비된 게임 프로젝트와 SDK를 사용합니다.
Unity 버전은 프로젝트 설정에서 읽습니다. 빌드가 성공하면 바탕화면의
`Wordventure build` 아래 새 폴더에 실행 파일과 데이터를 복사합니다.
기존 게임·서버를 종료하거나 새 게임을 자동 실행하지 않습니다.
`game path`는 마지막으로 복사한 경로를 출력합니다.

Docker, WSL Ubuntu, Git for Windows, PowerShell 7, 프로젝트에 명시된 Unity Editor와 기존
로컬 실행 설정이 필요합니다. 이 명령은 소스 fetch나 rebase를 자동으로 수행하지 않습니다.

## 브랜치 조회와 변경

`branch`는 workspace의 submodule을 대상으로 합니다. Windows checkout은
PowerShell 또는 Git Bash에서 사용합니다. `branch show`로 변경 여부를 확인한 뒤
`branch use ... --dry-run`으로 이동 계획을 확인합니다. 미커밋 변경이 있는 경로는
자동 stash하지 않으며 실제 branch 이동도 거부합니다.

## 명령어 목록

이 표는 `./dev docs`로 생성합니다. 설명을 바꿀 때는 `.dev/commands/`를 수정한 뒤
같은 명령으로 갱신합니다.

<!-- dev:commands:start -->

### `./dev branch` — 여러 component 의 branch 를 한 번에 보고 맞춥니다

| 명령어 | 하는 일 |
| --- | --- |
| `./dev branch show` | 각 component 의 현재 branch 와 변경 여부를 보여줍니다 |
| `./dev branch use [branch] [c=branch] [--fallback <b>] [--fetch] [--dry-run]` | 이름을 댄 component 를 그 branch 로 옮깁니다. 기본 branch 를 같이 주면 나머지도 그 branch (없으면 fallback) 로 따라갑니다 |
| `./dev branch save <이름>` | 지금 각 component 의 branch 조합을 그 이름으로 저장합니다 |
| `./dev branch load <이름> [--fetch] [--dry-run]` | 저장한 조합대로 맞춥니다. 조합에 없는 component 는 건드리지 않습니다 |
| `./dev branch list` | 저장된 조합을 보여줍니다 |

### `./dev game` — ARTEL SDK를 포함한 WordVenture를 빌드하고 바탕화면 경로를 조회합니다

| 명령어 | 하는 일 |
| --- | --- |
| `./dev game build` | 준비된 게임 소스를 빌드해 바탕화면에 새 폴더로 복사합니다. 실행 중인 게임과 서버는 유지합니다 |
| `./dev game path` | 마지막으로 복사한 게임 빌드 경로를 조회합니다 |

### `./dev local` — 준비된 로컬 PR 환경의 실행 상태와 로그를 관리합니다

| 명령어 | 하는 일 |
| --- | --- |
| `./dev local status [--runtime <path>]` | 현재 PID, HTTP 응답과 실행 경로를 조회합니다 |
| `./dev local revisions [--runtime <path>]` | 로컬 환경에 고정한 저장소별 commit을 조회합니다 |
| `./dev local logs <server|agent|home|support> [--lines <n>] [--follow] [--runtime <path>]` | 지정한 서비스 로그를 조회합니다 |
| `./dev local up [--runtime <path>]` | 준비된 환경을 시작합니다. 이미 실행 중이면 유지하고 일부만 실행 중이면 중단합니다 |
| `./dev local down [--runtime <path>]` | 기록된 서비스 PID만 중지합니다. 게임과 DB container는 유지합니다 |

<!-- dev:commands:end -->

## 자동 완성 적용

Bash 또는 Zsh의 시작 파일에서 `.dev/completion.bash`를 source하면 command,
subcommand, long flag를 TAB으로 완성할 수 있습니다.

실행 설정과 토큰을 문서나 command 파일에 넣지 않습니다. 저장된 branch 조합은
gitignored 경로인 `.dev/branches/`에만 기록합니다.
