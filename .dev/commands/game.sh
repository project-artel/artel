dev_describe() {
  echo 'ARTEL SDK를 포함한 WordVenture를 빌드하고 바탕화면 경로를 조회합니다'
}

dev_verbs() {
  dev_verb build '' '준비된 게임 소스를 빌드해 바탕화면에 새 폴더로 복사합니다. 실행 중인 게임과 서버는 유지합니다'
  dev_verb path '' '마지막으로 복사한 게임 빌드 경로를 조회합니다'
}

dev_run() {
  local verb=$1 script
  shift
  [ "$#" -eq 0 ] || die 'game 명령에는 추가 인자가 없습니다'
  case "${OSTYPE:-}" in
    msys*|cygwin*)
      dev_require pwsh.exe 'PowerShell 7이 필요합니다'
      dev_require cygpath
      script=$(cygpath -m "$DEV_ROOT/scripts/dev/build-wordventure.ps1")
      ;;
    *)
      dev_require pwsh.exe 'PowerShell 7이 필요합니다'
      dev_require wslpath
      script=$(wslpath -w "$DEV_ROOT/scripts/dev/build-wordventure.ps1")
      ;;
  esac
  MSYS_NO_PATHCONV=1 pwsh.exe -NoProfile -File "$script" -Action "$verb"
}
