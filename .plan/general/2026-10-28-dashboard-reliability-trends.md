# 2026-10-28 — 대시보드 QA 신뢰도 추이 추가

- Date: 2026-10-28
- GitHub Issue: None (기존 ARTEL-1271, home PR #232 후속)
- Status: Implemented

## Goal
프로젝트 대시보드에 오탐률·미탐률 날짜별 그래프와 검토 건수 막대, 기간 전체 검토 건수·검토율을 표시한다.

## Non-goals
서버 집계 정의 변경, 모델 학습, 임의 신뢰도 점수, 기존 QA history 제거, 이전 기간 대비 지표 추가.

## Context / Constraints
기존 /qa-evaluation/reliability API의 overall/daily 사용. 대시보드 7/30/90일 선택과 연동하며 Asia/Seoul 기준 오늘 포함 정확히 N일 조회한다. 날짜별 수치는 검증 시도 날짜 기준 현재 최종 평가 집계이며 평가 작성 건수와 구분한다. 기존 디자인 토큰·컴포넌트·copy 재사용. 사용자가 요청한 지표 label 외 새 홍보 문구는 추가하지 않는다.

## Approach (Checklist)
- [x] **Step 0: Recon** DashboardSection, 기존 ReliabilityPanel, API와 date helper·chart styles 확인.
- [x] **Step 1: Implementation** DashboardReliability 독립 section을 KPI 다음에 넣고 period와 안정된 now를 전달한다. 기존 API를 abort 가능한 effect로 호출하고 기간/프로젝트 변경 시 이전 데이터를 노출하지 않는다. loading/error/retry 처리. overall 검토 건수·검토율·FP/FN과 각 분자/분모 표시. 0 분모 null은 — 표시한다.
- [x] daily를 날짜순으로 정렬하고 선택 기간의 누락일을 채운다. 누락일 검토 건수0, rates null. FP/FN 고정0~100% 선 그래프(서로 다른 dash와 semantic 색), 검토 건수 별도 막대 그래프(독립 count 축), point title과 접근 가능한 날짜별 상세 표 제공. null 날짜는 선을 끊고 하루만 값이 있어도 점 표시한다. 현재 QA6 한 날짜 데이터도 확인한다. 그래프는 min-width/overflow로 모바일 페이지를 늘리지 않는다.
- [x] **Step 2: Tests** date period 경계, unsorted sparse daily/null vs zero, 선 단절, one-point와 reviewed count의 의미를 helper/SSR 테스트로 확인. 전체 test/build/변경 eslint, 실제 API 화면 기간 변경, 두 theme·모바일·화면 캡처 검증. fixture 수치를 실제 데이터로 주장하지 않는다.
- [x] **Step 3: Rollout / Rollback** 기존 branch/PR232에 commit/push, docs/images에 캡처와 검증기록 추가하고 PR 본문 보존하여 append. backend 변경 없음. rollback은 이번 commit revert.

## Validation
- **Commands to run:** npm test, npm run build, npx eslint 변경파일, git diff --check.
- **Expected output:** 대시보드에서 검토 건수·검토율·FP/FN과 날짜별 추이가 보인다. null은 0이 되지 않는다. 7/30/90일 선택 시 일관된 기간을 표시한다.

## Risks & Rollback
- **Risks:** 누락 날짜를 0%로 오인, 오래된 fetch 결과 덮어쓰기, 작은 표본 오해, 모바일 overflow.
- **Rollback steps:** home 변경 commit revert.

## Open Questions
없음. 신뢰도 추이와 검토 건수를 구현하라는 사용자 요청을 반영한다.

## 1차 검토 반영
FAST/MEDIUM PASS. 전체 시도0·검토0을 구분하여 검토 건수0, rates —를 검증한다. 기간 빠른 변경 시 늦은 success/error를 무시한다. 기존 evaluationCopy.bias를 그래프 바로 아래 표시한다. 공용 chart framework와 기존 history panel 재설계는 하지 않는다.

## 실행 결과
Fast/Medium/Heavy 계획 검토 PASS, 독립 pair-review PASS. 전체 테스트1556 PASS, build/ESLint PASS. 실제 프로젝트1의 검토4건·16%·오탐0/3·미탐0/0 확인. 7/30/90일, 빠른 기간 변경, 두 테마·390px 내부스크롤과 keyboard 상세표를 검증하고 캡처6개를 docs/images/dashboard-reliability에 보존했다.
