dev_describe() {
  echo '준비된 로컬 PR 환경의 실행 상태와 로그를 관리합니다'
}

dev_verbs() {
  dev_verb status '[--runtime <path>]' '현재 PID, HTTP 응답과 실행 경로를 조회합니다'
  dev_verb revisions '[--runtime <path>]' '로컬 환경에 고정한 저장소별 commit을 조회합니다'
  dev_verb logs '<server|agent|home|support> [--lines <n>] [--follow] [--runtime <path>]' '지정한 서비스 로그를 조회합니다'
  dev_verb up '[--runtime <path>]' '준비된 환경을 시작합니다. 이미 실행 중이면 유지하고 일부만 실행 중이면 중단합니다'
  dev_verb down '[--runtime <path>]' '기록된 서비스 PID만 중지합니다. 게임과 DB container는 유지합니다'
}

dev_run() {
  local verb=$1
  shift
  case "${OSTYPE:-}" in
    msys*|cygwin*)
      dev_require wsl.exe
      dev_require cygpath
      local script
      script=$(wsl.exe -d "${ARTEL_WSL_DISTRO:-Ubuntu}" -- wslpath -u "$(cygpath -m "$DEV_ROOT/.dev/lib/local-runtime.py")")
      script=${script//$'\r'/}
      MSYS_NO_PATHCONV=1 wsl.exe -d "${ARTEL_WSL_DISTRO:-Ubuntu}" -- python3 "$script" "$verb" "$@"
      ;;
    *)
      dev_require python3
      python3 "$DEV_ROOT/.dev/lib/local-runtime.py" "$verb" "$@"
      ;;
  esac
}
