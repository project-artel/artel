# 2026-11-03 — TC 명세 등급 status 제거

- Date: 2026-11-03
- GitHub Issue: None
- Jira: ARTEL-1320 (하위 ARTEL-1321, ARTEL-1322, ARTEL-1323, ARTEL-1324)
- Status: Implemented (draft PR 준비)

## Goal
TC의 명세 등급 `status`를 저장·생성·전송·표시하는 경로 제거.

## Non-goals
QA 결과 `verificationStatus`, content map capability의 `status`, HTTP 및 로딩 상태 변경.

## Context / Constraints
여러 하위 저장소와 수정 대상 파일에 기존 미커밋 변경이 있다. 이를 보존한다. 기존 Flyway SQL은 수정하지 않고 새 migration으로 `test_case.status`, `test_case_version.status`를 삭제한다.

## Approach (Checklist)
- [x] **Step 0: Recon**: 서버 DTO·엔티티·명세 ingest/export·생성기·SQL, 콘솔 및 CLI·MCP·agent 출력 참조 확인.
- [x] **Step 1: Implementation**: TC status 필드·생성 계산·매핑 제거. 콘솔 등급 열·chip·번역·CSS 제거. agent specs_v2 CSV 열·정렬·등급별 counts와 서버 SpecXlsxWriter의 XLSX 열 및 관련 계약도 제거한다. 관련 현재 문서와 fixture 정리. evidence gaps는 독립적인 근거 정보로 유지.
- [x] **Step 2: Tests**: status 없는 API 계약, 생성·적재·조회·버전·폴더 경로 검증. migration은 실제 Postgres에서 기존 데이터를 보존하며 두 컬럼을 제거하는지 확인. 기존 golden fixture도 새 계약에 맞게 갱신.
- [x] **Step 3: Rollout / Rollback**: 서버와 소비자 변경을 함께 준비하고 DB 변경은 해당 서버 배포 시 Flyway로 적용. 실행 중인 구 서버와 DROP COLUMN을 혼용하지 않는다. 운영 배포 상태와 로컬 구현 상태를 구분해서 보고한다.

## Validation
- **Commands to run:** 서버 Maven compile 및 TC 관련 integration/generator tests, 콘솔 typecheck·test·build, CLI typecheck·test, agent의 test-case 출력 계약 테스트, TC status 잔여 검색. 가능한 경우 콘솔 TC 목록과 상세를 light/dark 및 desktop/mobile에서 확인.
- **Expected output:** TC JSON과 타입 및 최신 DB에 명세 등급 status가 없고 기존 QA 판정과 TC 데이터는 유지된다.

## Risks & Rollback
- **Risks:** 구 서버는 삭제된 컬럼에 접근하므로 서버/DB 동시 전환이 필요하다. 과거 명세 등급 값은 삭제되며 복원되지 않는다.
- **Rollback steps:** 필요하면 nullable status 컬럼을 새 migration으로 복구하고 이전 서버로 되돌린다. 등급 값 복구는 별도 DB 백업이 필요하다.

## Open Questions
없음. 로컬 실행 도구와 DB 접근 가능 여부는 확인 중이다.

최신 develop/main의 별도 worktree는 `.worktrees/tc-spec-status/`에 있다. V163 migration으로 최신 번호와 충돌을 피했다. 콘솔 1590, CLI 460, agent 74개 테스트 통과. 서버는 256개 중 244개 통과했고 나머지 12개는 기존 벡터 테스트 fixture의 project FK 오류다. 화면은 status 없는 mock API로 light/dark, 1280px/360px에서 확인했다.

CI migration 검사에서 다른 미병합 브랜치의 V156과 충돌해, 전체 remote branch의 최대 예약 번호 V162 다음인 V163로 이동했다.
추가 remote fetch에서 V162도 예약된 것을 확인했으므로 최종 번호는 V163이다.
