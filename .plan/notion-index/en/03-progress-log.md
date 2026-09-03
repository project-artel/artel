> What happened, day by day and week by week. 45 meetings · 95 standup entries · 10 mentoring question sets.
> Surveyed 2026-08-26.

## 개발 스탠드 업

Database `39f0bce5-474c-8061-bdd0-fe9c99dfe556` · data source `39f0bce5-474c-8081-9909-000ba0124546`
95 rows · 35 distinct days · 김태민 32 · 정의진 32 · 정윤성 31 · `작성 완료` on 26 of 95

**One row per person per day.** The title is `YY.MM.DD 한 일` (93 of 95 rows).
`태그` is the author.

Body format — agent-written rows follow this exactly:

```markdown
# 개요
- 조회(기준: 최근 1일, KST): Jira …건, GitHub PR …건.
- <one or two sentences on what the day was about>
## PR
- [merged] feat(scenario): … — artel-agent-server#101
- [open]   fix(scenario): … (ARTEL-508) — artel-orchestration-server#163
# 회고
회고 작성 필요
```

Rules the existing rows keep:

- State the evidence base explicitly, e.g.
  `GitHub 근거만으로 작성(Jira 근거 없음, 추측으로 채우지 않음)`.
- One line per PR: state (`[merged]` / `[open]` / `[closed]`), the
  conventional-commit subject, and `repo#number`.
- **`# 회고` is the human's.** An agent does not invent someone's retrospective.
- **`작성 완료` is ticked by the human.** An agent leaves it `false`.

## 회의록

Database `3850bce5-474c-801e-8dc7-cbc3ba8bb142` · data source `3850bce5-474c-80b4-bd39-000bd9c844f5`
45 rows · 2026-05-27 to 2026-08-26

`태그` is one of `팀 회의` / `멘토링` / `계획` / `일정`. `할 일` runs `없음` /
`할 일 있음` / `진행 중` / `완료` (a quoted `"할 일 있음"` option is mixed in).
`회의 요약본` is the CLOVA Note slot and is mostly empty.

### Sprint and planning meetings — start here for the arc

| Date | Meeting |
|---|---|
| 2026-08-17 | 중간 발표 목표 회의 — where the pipeline owners were assigned |
| 2026-08-05 | DB 스키마 최신화 (2026-08-05) |
| 2026-08-04 | 3차 스프린트 실행 계획 · 3번째 스프린트 회의록 |
| 2026-07-31 | SDK 개발 마무리 |
| 2026-07-29 | MVP 1차 목표(?) |
| 2026-07-28 | 2번째 스프린트 회의록 |
| 2026-07-27 | 7월 4주차 일정 계획 |
| 2026-07-21 | Agent-Server 고도화 |
| 2026-07-19 | 7월 3주차 일정 계획1 |
| 2026-07-15 | 개발 시작 회의 · 개발 시작 |
| 2026-07-13 | 시퀀셜 다이어그램 회의 |
| 2026-07-01 | 설계 스프린트 |
| 2026-06-30 | 기획서 심의 이후 할 일 정하기 |
| 2026-06-06 | 기획 결정 회의 |
| 2026-05-27 | 첫 회의 |

### Mentoring sessions

박재범 (6/07 · 6/14 · 7/03 · 7/24 · 8/10 · 8/17) · 강한규 (6/21 · 7/19 · 7/25 ·
8/07) · 홍윤석 (6/12 · 7/19) · 김동우 (6/11) · 배권한 (6/11) · 장상현 (6/15)

Bodies are free-form: `## 목표` followed by ownership arrows
(`evidence ← 의진`), whiteboard photos, and code fences. Some meeting rows carry
their own inline `할 일` database — `3번째 스프린트 회의록` and `오늘 회의록`,
whose schemas differ from each other.

**Writing meeting notes is a human act.** An agent writes one only on request.

## 질문

Database `3900bce5-474c-80d6-bd6c-dd65be002fd2` · data source `3900bce5-474c-80ea-8708-000bc8a8389e`
10 rows

The title property is named `질문 내용` but actually holds the mentor and the date
(`박재범 멘토님 멘토링 (8/17)`). `상태` runs `시작 전` / `진행 중` / `완료`. The
body holds the questions and answers, sometimes with an answer table keyed by
mentor.

| Date | Subject | 상태 |
|---|---|---|
| 2026-08-17 | 박재범 멘토님 멘토링 (8/17) | 진행 중 |
| 2026-08-16 | 홍윤석 멘토님 | 완료 |
| 2026-08-10 | 박재범 멘토님 멘토링 (8/10) | 완료 |
| 2026-07-25 | 강한규 멘토님(7/25~7/26) | 완료 |
| 2026-07-21 | 박재범 멘토님 (2026/07/24) | 완료 |
| 2026-07-19 | 강한규 멘토님 (2026/07/19) | 완료 |
| 2026-07-16 | 홍윤석 멘토님(2026/07/19) | 완료 |
| 2026-07-12 | 박재범 멘토님 멘토링(2026/07/12) | 완료 |
| 2026-07-09 | 강한규 멘토님 멘토링(2026/07/09) | 완료 |
| 2026-07-03 | 박재범 멘토님 멘토링(2026/07/03) | 완료 |

## Meeting notes carry photos

Several meetings hold whiteboard and handwriting photos in the body. Image URLs
returned by the Notion API are presigned and **expire after about an hour.**
Never paste one into another document or an issue — fetch it again when needed.
