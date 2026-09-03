# 📗 문서 Index

> 설계·개발·일반 문서 29편. 결정의 배경과 구조를 찾는 곳.
> database `36e0bce5-474c-80de-9026-d310fa0884a5` / data source `36e0bce5-474c-808d-91e2-000b77669a97`
> 위치: `Artel` → `이동 경로 (삭제 X)` → `문서`
> 조사 기준일 2026-08-26.

`Category` 는 `설계` 11 · `개발` 12 · `일반` 6. `최종 편집자` 가
`ArtelNotionToken` 인 행은 agent 가 쓴 문서다.

## 설계 — 무엇을 만들기로 했는가

| 문서 | 언제 볼까 |
|---|---|
| 아키텍처 | 서버 구성과 경계를 처음 잡을 때 |
| DB Schema | 테이블·관계를 확인할 때 |
| Usecase | 사용자 흐름 단위로 기능을 볼 때 |
| 핵심 기능 | 무엇이 MVP 안에 있는지 |
| MVP 목표 | 범위를 자를 때 |
| Artel 기능 명세서 | 기능 목록. 단 안의 database 는 방치돼 있다 (아래 주의) |
| 명세서{MetaData}\| 설계 - | 명세 metadata 설계 |
| BM 설계 | 수익 모델 |
| 아르텔 기획 · 기획 초안 · [기획] Agent 게임 플랫폼 | 초기 기획 계보. 지금 결정과 다를 수 있다 |

## 개발 — 어떻게 만들었는가

| 문서 | 언제 볼까 |
|---|---|
| SDK WebSocket JSON-RPC 명세 | SDK 프로토콜을 다룰 때 |
| Artel SDK 적용 방식 서칭 | SDK 를 게임에 붙이는 방식 결정 배경 |
| 1주차 Artel SDK 개발 기록 | SDK 초기 구현 경위 |
| SDK 생각 해볼 것들 | 미해결 논점 |
| Keyboard Proxy에 대한 고민 · KeyCode 종류 | 입력 주입을 다룰 때 |
| Scene Block 구조 | 씬 구조 |
| GameContext Hadn off | 게임 컨텍스트 전달 |
| TestScenario 데이터 흐름 (FE↔Orche↔Agent) | 세 서버에 걸친 흐름을 볼 때 |
| Agent의 정량적 평가 | agent 품질 측정 |
| WordVenture 에이전트 성능 벤치마크 시나리오 | 성능 측정 기준 |
| API 명세 | **안에 `API 명세서` database 가 들어 있다.** 📘 API 명세서 Index 로 |

## 일반 — 팀·사용자·의사결정

| 문서 | 언제 볼까 |
|---|---|
| 결정이 필요한 안건 | 열린 결정 사항 |
| 설계 중 멘토링 질문 사항 | 설계 단계에서 막혔던 것 |
| FGI · 설문 조사 & 멘트 | 사용자 조사 |
| 멘토 매칭을 위한 팀 소개 | 대외 소개 |
| API 전체화면 | 화면 단위 API 정리 |

## 이 database 밖의 설계 문서

`문서` database 에 들어 있지 않지만 지금 가장 중요한 두 장:

- **중간 발표 대비 3주 스프린트 계획 (8/18~9/7)** — `Artel` 루트 바로 아래.
  파이프라인 `게임+SDK → evidence → 씬 명세 → TC → TS → QA 런 → 화면 명세`,
  단계별 담당, 그리고 제약 두 가지 (TC 입력은 씬 명세 단독 / 씬 전이는 런타임에서만
  관측된다) 가 여기 있다. **현재 진행 중인 작업의 기준 문서.**
- **content_map — 씬·화면·기능 스키마 설계** — `개발 문서` 페이지 아래.

## 주의

- **`Artel 기능 명세서` database (30행) 는 방치돼 있다.** `구현 완료` 가 30행 전부
  `false` 인데 같은 시점 `API 명세서` 는 118개를 `구현 완료` 로 기록한다. 계획 때
  채우고 유지하지 않았다. 구현 상태는 📘 API 명세서 Index 를 본다. 이 database 는
  초기 기능 목록의 흔적으로만 읽는다.
  - title 속성 이름이 `기능 ` 이다. **끝에 공백이 있다.**
  - `도메인` 옵션에 오타가 있다: `OrchastratorSDK`.
- **`설계 문서` database 는 integration 에 연결돼 있지 않다** (404). agent 가 읽어야
  하면 사람이 `... > 연결` 로 추가한다.
- 기획 계보 문서(`기획 초안`, `[기획] Agent 게임 플랫폼` 등) 는 지금 제품과 다르다.
  현행 결정의 근거로 인용하지 않는다.

## 새 문서 쓰기

```bash
ntn pages create --parent data-source:36e0bce5-474c-808d-91e2-000b77669a97 \
  --content '# 제목

본문'
```

`ntn pages create` 는 제목만 설정한다. `Category` 는 만든 뒤에 붙인다.

```bash
ntn api v1/pages/<page-id> -X PATCH -d '{"properties":{"Category":{"select":{"name":"개발"}}}}'
```
