> 23 personal research, measurement, and trade-off notes. **The "why" behind the decisions.**
> Database `37c0bce5-474c-80d4-b4fc-efecef3832dc` · data source `37c0bce5-474c-805e-8c1d-000bd6c455bc`
> Location: `Artel` → `개인 페이지`
> Surveyed 2026-08-26.

If the `문서` database says what we decided to build, this one says why we chose
it that way. Before re-arguing a design, check whether someone already measured it.

`페이지 소유자` is a **status** property, not a select — the filter syntax
differs. `다중 선택` offers `Infrastructure` and `Orchestraion` (typo as-is).

## Design trade-offs — read before reopening one

| Note | Owner | Covers |
|---|---|---|
| TestCase/TestScenario/TestRun 3중 구조 — 관계 저장 방식 트레이드오프 (junction vs JSON) | 김태민 | How the three-way relation is stored |
| QA 저작 3중 구조(케이스·시나리오·런) 전환 — 쉬운 설명 · 트레이드오프 · 잠재 문제 | 김태민 | The same migration, its reasoning and residual risk |
| Embedding · 벡터 검색 구조와 트레이드오프 (ARTEL-206) | 김태민 | Vector search structure |
| QA Agent 임베딩 모델 선정 근거 (ARTEL-184) | 정윤성 | Embedding model choice |
| 파일 해시 중복검증 — 검증 시점 트레이드오프 (Orche 업로드) | 김태민 | When to run duplicate detection |
| 코루틴(Coroutine) 전환 주의점 & 우리가 겪은 함정 | 김태민 | Mines we actually stepped on |

## Cost and performance measurements

| Note | Owner |
|---|---|
| 저작 토큰 비용 실측 (2026-08-13) — 전수 판정을 넣어도 되는가 | 김태민 |
| 저작 요금 실측 (2026-08-13) — 섹터별·모델별 원가와 요금제 시사점 | 김태민 |

The first holds an inline `토큰 실측치 (2026-08-13)` database — 21 rows, data
source `2f28c331-e02c-413a-96dd-f70348fbec0f`. It exists only to chart that
write-up, along the axes `규모` (wordventure 66 / 평균 300 / 최대 1000) and
`항목` (입력 · 전수판정 · 스텝출력 · 저작 · 무캐시 · 캐시 적용).

## Cycle summaries and technical research

| Note | Owner |
|---|---|
| QA 저작 Step E2E 완성 · 런 종료 라이프사이클 · 관측 격차 — 이번 사이클 정리 | 김태민 |
| Kotlin - coroutine Study step | 김태민 |
| CSV →.XSL 파일 변경 라이브러리 탐색 | 김태민 |
| AWS | 정의진 |

## Planning-era and meeting memos

| Note | Owner |
|---|---|
| 엑스퍼트미팅(8/21) · 엑스퍼트 미팅 2차 | 김태민 |
| 액스퍼트 미팅 | 정윤성 |
| 멘토 서치 | 정윤성 |
| [기획 구체화] Agent 마피아 게임 | 정윤성 |
| [기획 구체화] Codebase 분석기 | 정윤성 |
| 프로젝트 정리 | 김태민 · 정윤성 (one each) |
| 2026/07/26 · (untitled) · ㅇㅇ | 정의진 · 정의진 · 김태민 |

## Etiquette

These rows belong to individuals.

- **Read freely. Do not edit someone else's row.**
- Create a row only when asked, and only under the requester's `페이지 소유자`.
- When promoting something from here into a team document, link the original
  note as the source. Do not copy it and drop the attribution.
