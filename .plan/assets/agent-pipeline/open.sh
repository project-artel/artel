#!/usr/bin/env bash
# 이 폴더의 산출물을 Windows 탐색기로 연다.
#   ./open.sh          폴더를 열고 PDF 를 선택한다
#   ./open.sh pdf      PDF 를 기본 뷰어로 연다
#   ./open.sh deck     발표자료 HTML 을 기본 브라우저로 연다
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-select}" in
  select) explorer.exe /select,"$(wslpath -w "$here/artel-agent-pipeline.pdf")" || true ;;
  pdf)    explorer.exe "$(wslpath -w "$here/artel-agent-pipeline.pdf")" || true ;;
  deck)   explorer.exe "$(wslpath -w "$here/deck.html")" || true ;;
  dir)    explorer.exe "$(wslpath -w "$here")" || true ;;
  *) echo "사용법: $0 [select|pdf|deck|dir]" >&2; exit 2 ;;
esac
