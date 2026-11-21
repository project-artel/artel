# 2026-10-22 — 웹 화면 모바일 반응형 수정

- Date: 2026-10-22
- GitHub Issue: None
- Status: Implemented

## Goal
온보딩, 콘솔, 관리자 화면을 좁혀도 페이지가 가로로 늘어나거나 기능이 잘리지 않도록 수정한다.
사용자 추가 요청에 따라 모바일 여백, 메뉴, 설치 단계와 프로젝트 목록의 시각적 간격도 정돈한다. 기존 색과 서체를 유지한다.

## Non-goals
제품 문구, API, 테마 변경과 배포는 포함하지 않는다.

## Context / Constraints
기존 작업 파일을 보존한다. 공통 shell의 고정 높이와 자식의 스크롤을 함께 확인한다. 표와 code는 자체 영역에서 스크롤한다. 그래프 좌표계는 유지한다.

## Approach (Checklist)
- [x] **Step 0: Recon** — 세 앱의 shell, navigation, 고정 grid와 기존 breakpoint 확인.
- [x] **Step 1: Implementation** — header와 filter 줄바꿈, grid 최소 폭 수정, 모바일 다단 화면 세로 배치. 기능을 숨겨서 overflow를 해결하지 않는다. `.qh`, `.st-edit`, `.se-row-main`의 고정 열과 고정 높이를 함께 수정한다. 열린 popover와 dialog는 필요하면 JS 위치 계산도 수정한다.
- [x] **Step 2: Tests** — 320, 390, 768, 1024, 1440px, 두 테마에서 실제 화면과 로컬 스크롤 확인. 긴 이름과 populated table도 포함한다.
- [x] **Step 3: Rollout / Rollback** — 변경 diff와 검증 결과를 정리하고 배포는 별도로 진행한다.

## Validation
- **Commands to run:** 각 앱의 build, typecheck 및 브라우저 너비 검사.
- **Expected output:** page overflow 없음. 내비게이션, 편집기, inspector, dialog 접근 가능. mock API로 확인한 화면은 실제 서버 검증과 구분한다.
- 긴 목록과 대화에서 최하단 버튼, composer와 inspector까지 스크롤로 접근되는지 확인한다. 선택 메뉴를 열어 좌우 위치와 키보드 접근도 확인한다.
- 직접 URL 및 내부 navigation 후 lazy CSS 순서, desktop → mobile → desktop 전환 상태, 관리자 내부 7개 탭을 확인한다.

## Risks & Rollback
- **Risks:** lazy stylesheet의 우선순위, 고정 높이 안의 중첩 스크롤, 기존 모바일 숨김 규칙.
- **Rollback steps:** 이번 CSS, import 및 popup 크기 계산 변경만 되돌린다.

## 검증 결과
- 세 앱의 `npm run build` 통과. 콘솔 `npm run typecheck`, 변경한 TSX의 ESLint, 세 저장소 변경 파일의 `git diff --check` 통과.
- 브라우저: 44개 화면·탭 × 5개 너비 × 2개 테마, 총 440개 조합에서 page overflow와 pageerror 없음. 최종 QA 선택창 간격 변경 후 해당 화면의 10개 조합 재검증 통과.
- QA 실행 선택창의 양쪽 목록과 실제 선택 동작 확인. 320px에서 시나리오 chat composer의 하단이 화면 안에 들어오는 것을 확인. 입력 후 desktop → mobile 전환에도 입력값 유지. 영어 모바일 header overflow 없음.
- 테스트는 로컬 앱과 mock API 응답을 사용했다. 프로젝트 목록, 사용자 표, 15개 시나리오 step을 포함한다. 실제 서버 데이터와 모든 업무 상태의 end-to-end 검증은 하지 않았다.
- CSS와 TSX의 독립 검토 PASS. 화면 이미지로 SDK 설치 안내, 프로젝트 목록, 시나리오 편집기, 선택창과 chat composer 확인.
- 상세 검사 결과: `.work/responsive-full-results.json`, `.work/responsive-results.json`. 검증 스크립트: `.work/responsive-check.cjs`.
- 배포하지 않았다. 기존 사용자 변경은 보존했다.

## Open Questions
- Jira 검색에서 Epic과 기존 반응형 이슈가 조회되지 않아 추적 이슈를 아직 선택하지 못했다.
