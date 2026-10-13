# 성공한 action 시퀀스를 macro 로 저장하고 다시 부른다

- Date: 2026-09-18
- Jira: Epic `ARTEL-914` — [QA] agent 가 성공한 조작을 macro 로 저장하고 다시 부른다
  (https://artel-asm.atlassian.net/browse/ARTEL-914). 아래 `## 쪼개는 방법` 의 작업 단위
  12개가 그 Epic 아래에 달린다. 개별 key 는 여기 안 적는다 — 표의 label 이 이슈와 이 문서를
  잇는 끈이고, Epic 을 열면 12개가 다 보인다.
- Status: 설계. 구현 전.
- 대상 저장소: `artel-agent-server` (tool 둘과 실행 loop), `artel-orchestration-server`
  (저장 자리와 frame 둘). `artel-sdk` 는 **한 줄도 안 고친다** — 이유는 아래
  `## 실행기는 이미 있다` 에 있다.
- 기준: `artel-agent-server` 의 `origin/develop`, `e63fc47` (#195, ARTEL-913 머지) 까지.
  **action tool 열여섯 개의 시그니처는 `9cd382b` (#179) 와 같다** —
  `git diff 9cd382b origin/develop -- app/agents/qa/tools/action_tools.py` 가 빈 출력이다.
  #179 가 pointer tool 의 겨누는 법을 바꾼 판이고 이 문서는 그 뒤를 딛는다. 워크스페이스에
  체크아웃된 submodule 은 `ARTEL-884` 브랜치라 #179 앞이고 pointer tool 이름이 옛것
  (`click_at` · `drag_pointer`)이다. **이 문서의 tool 이름과 인자는 전부 develop 것이다.**
  SDK 쪽은 `artel-sdk` 의 `ARTEL-881` 브랜치에서 `Packages/kr.artel.sdk/Runtime/Pointer/`
  와 `ArtelManager.ExecuteActionRequest` 를 읽었다. orchestration 쪽은
  `ARTEL-816` 브랜치이고 migration 은 `V92` 까지 있다.

## 이 계획은 파일 넷이다

본 문서가 입구다. 세부는 같은 날짜 접두를 쓰는 파일 셋에 있다.

| 파일 | 무엇이 있나 |
|---|---|
| [`2026-09-18-macro-language-reference.md`](2026-09-18-macro-language-reference.md) | 표기법, 함수 전체 목록, 타입 선언, helper `def`, predicate `def`, 연산자 dispatch, 대입, `if`, `wait_until`, 허용·거절 node, 상한 |
| [`2026-09-18-macro-targets-and-memory.md`](2026-09-18-macro-targets-and-memory.md) | `PulseMemory` 가 유일 출처라는 것, selector, `find`, 묶인 이름, 보조인 `SceneMemory` |
| [`2026-09-18-macro-errors-and-reporting.md`](2026-09-18-macro-errors-and-reporting.md) | `require` 와 remedy, `flag` 와 `ask_verdict`, batch 로 쪼개지는 실행 의미, 부분 실행 보고, `wait_until` 의 시간 초과 보고, 에러 코드 여덟 개, timeline |

본 문서에 남는 것은 머리말과 Goal, 실행기와 저장 자리, 첫 버전 범위, Non-goals, 열려 있는
질문, 그리고 `## 쪼개는 방법` 이다. 셋 사이의 참조는 파일 이름으로 쓴다 —
`macro-language-reference` 의 `### 연산자 dispatch` 처럼.

## Goal — action 네 개를 tool 호출 한 번으로

QA agent 가 성공한 action 시퀀스에 이름과 parameter 를 붙여 저장했다가, 나중에 tool 호출 한
번으로 다시 실행한다. 그것을 macro 라 부른다.

카드 게임 예로: `shoot` 카드와 `fire` 카드를 슬롯에 올리고 combine 버튼을 눌러 합친 뒤 첫
번째 슬라임을 공격하는 action 네 개를, `attack_with_combined_card(card_a, card_b, target)` 한
번으로 부른다.

**이득은 action 을 덜 보내는 것이 아니라 model 을 덜 깨우는 것이다.** 지금 그 네 action 은
model turn 네 개다 — 각 turn 이 화면을 읽고 tool 을 하나 고르고 결과를 받는다. macro 는
그것을 turn 하나로 줄인다. 게임에 나가는 action 수는 그대로이고, `macro-errors-and-reporting` 의 `## require()` 절이
보이듯 왕복은 오히려 는다.

## 실행기는 이미 있다 — `ctx.run` 이 batch 를 보낸다

`app/agents/qa/tools/action_tools.py` 의 tool 열여섯 개가 전부
`ToolContext.run`(`tool_context.py:67`)을 지나고, 거기서 `JsonRpcAction` 목록 하나가 ACTION
frame 한 장에 실려 나간다. 여러 개짜리가 이미 있다.

| tool | batch 안의 action | 무엇으로 |
|---|---|---|
| `click` | 3 | `move_mouse` → `mouse_down` → `mouse_up` |
| `double_click` | 5 | `move_mouse` → 누름·뗌 두 벌 |
| `drag` | 4 | `move_mouse` → `mouse_down` → `move_mouse` → `mouse_up` |

게임이 batch 를 순서대로 도는 것도 이미 보장돼 있다. `ArtelManager.ExecuteActionRequest` 가
`request.Actions` 를 `foreach` 로 돌며 하나씩 `yield return` 하고, 전부 끝난 뒤에 결과
목록과 `Time.frameCount` 를 한 장으로 답한다.

**그래서 macro 는 새 실행기도 새 wire protocol 도 아니다.** 이미 있는 batch 에 이름과
파라미터를 붙여 저장하는 층 하나다. SDK 를 안 고치는 이유가 이것이다.

### batch 는 중간 실패에서 안 멈춘다

같은 `foreach` 가 실패한 action 의 결과를 `results` 에 담고 **다음 action 으로 계속 간다.**
`drag` 의 첫 `move_mouse` 가 selector 를 못 풀어도 `mouse_down` · `move_mouse` · `mouse_up`
이 그대로 돌아, 포인터가 있던 자리에서 엉뚱한 drag 가 일어난다.

이것은 macro 가 만드는 문제가 아니라 지금 `drag` 에도 있는 것이다. 다만 macro 의 batch
경계를 어디에 두는지가 이 사실에 걸린다 — **한 batch 안에서는 중단할 수 없으므로, 중단
지점은 batch 경계여야 한다.**


## macro 를 어디에 저장하나

`.plan/general/2026-09-09-run-the-qa-loop-as-a-phase-cycle.md` 의 memory 표가 근거다. 그
표의 여섯 중 런을 넘어 사는 것은 knowledge base 와 content map 의 `capability` 행 둘뿐이다.

- **knowledge base 는 자연어다.** 실행 가능한 형태가 아니다.
- **`capability` 는 "이 버튼 하나가 무슨 일을 하나" 의 기록이다.** V40 의 주석이 그 한 줄을
  given / when / then 세 칸으로 정의하고, `interaction` 은 `click` · `type` · `press` ·
  `axis` · `none` 중 하나다. 시퀀스를 담을 칸이 없다.

그래서 content map 쪽에 새 그릇이 필요하다. 붙는 자리는 `content_map` 이다.

- V63 이 유일 키를 `game_build_id` 하나로 바꿨다. **지도가 build 당 하나**라 macro 도 build
  당으로 붙고, **게임이 바뀌면 macro 도 같이 죽는다.** 그것이 이 선택의 이유다.
- 같은 migration 이 `content_map.rooted_by` 를 더해 evidence 문서 없이도 지도 행이 서게
  했다. **evidence scan 을 안 돌린 build 에서도 macro 를 적을 자리가 있다**는 뜻이다.
- `scene` 이 아니라 `content_map` 에 매다는 것은 macro 가 scene 을 넘을 수 있기 때문이다.
  첫 `require` 가 `scene()` 이름을 들지만 안쪽 statement 가 화면을 넘기면 끝나는 scene 이
  다르다.

`capability` 행과 같은 격리 문제를 그대로 물려받는다. `ContentMapMode` 의 KDoc 이 적어 둔
것 — `capability` 행은 `content_map` → `game_build` 에 바로 매달려 있고 `knowledge.scope_id`
같은 격리 축이 없다 — 이 macro 표에도 똑같이 걸린다. 벤치마크 arm 을 나눠 도는 런은
`ContentMapMode.FROZEN` 을 써야 하고, 그 mode 가 macro 쓰기도 함께 막아야 한다.

## 첫 버전 범위 — tool 다섯 개

**macro 를 초안으로 두고 고쳐 쓰다가 등록한다.** tool 둘(`define_macro` · `run_macro`)로
두었던 것을 다섯으로 나눈다. 이유가 둘이다 — 스무 줄짜리 macro 의 한 줄을 고치려고 전문을
다시 보내는 것은 낭비이고, **문법이 깨진 것이 macro 로 등록되면 안 된다.**

| tool | 무엇 |
|---|---|
| `write_macro(name, source)` | 초안을 만들거나 통째로 바꾼다. 파싱해서 **결과를 말해 주되 등록하지는 않는다** |
| `edit_macro(name, old_text, new_text)` | 초안의 일부를 바꾼다. **줄 번호가 아니라 문자열 치환이다** |
| `read_macro(name)` | 초안이나 등록된 macro 의 원문을 돌려준다 |
| `register_macro(name)` | 검사해서 통과하면 부를 수 있게 만든다 |
| `run_macro(name, args)` | 등록된 정의를 지금 판독에 대고 풀어 실행하고 단계별 결과를 돌려준다 |

**`edit_macro` 가 줄 번호를 안 받는 이유.** model 은 줄 번호를 틀리고, **틀린 줄 번호는
조용히 엉뚱한 줄을 고친다.** 문자열 치환은 그렇지 않다 — `old_text` 가 원문에 없으면
아무것도 안 바뀌고 거절이 나간다. 원문에 두 번 이상 나오는 `old_text` 도 거절한다. **시끄럽게
실패하는 쪽을 고른다.**

`read_macro` 가 있어야 하는 이유도 거기 있다. 고치려면 먼저 읽어야 하고, 기억으로 적은
`old_text` 는 한 글자만 달라도 안 맞는다.

**`register_macro` 가 거절하는 것.** 문법이 깨졌거나(`MACRO_SYNTAX_ERROR`), 허용 node 가
아니거나 모르는 tool 이름이 있거나(`MACRO_NODE_REJECTED`), 눌러 둔 것이 끝에 남았거나, `macro-language-reference` 의
`### 세는 상한 일곱` 을 넘겼거나다 — 여기에 `wait_until` 의 최대 대기 시간 30초와 한 실행 경로의 합계 60초가 든다. **거절되면 이름이 안 생기고 `run_macro` 가 못 부른다.**
초안은 그대로 남으므로 `edit_macro` 로 고쳐 다시 등록한다.

**텍스트가 원본이라는 규칙이 여기서 값을 한다** (`macro-language-reference` 의 `### 저장은 텍스트와 JSON 둘 다 한다`).
**초안은 텍스트만 든다. JSON 은 `register_macro` 가 만든다.** 그래서 파싱이 실패하는 동안에도
들고 있을 것이 있고, 등록된 뒤에는 텍스트와 JSON 이 같은 한 번의 파싱에서 나온 짝이다.

**`macro-selector-lift` 가 여기로 이어진다.** 그 작업이 내놓는 것은 완성된 macro 가 아니라
**초안**이다 — dispatch 기록의 id 와 좌표를 지금 판독의 selector 로 바꿔 올린 텍스트이고,
무엇을 parameter 로 뺄지도 remedy 에 무엇을 적을지도 안 정해져 있다. agent 가 그것을
`read_macro` 로 읽고 `edit_macro` 로 고쳐 `register_macro` 한다. 아래 `## 쪼개는 방법` 의 그
행이 이미 "macro 텍스트 초안을 만든다" 라고 적고 있고, 그 말이 여기서 제자리를 찾는다.

**`run_macro` 의 설명에 "부르기 전에 화면을 한 번 관측한다" 가 들어간다** — `find` 는 이미
도착한 판독만 보므로 화면이 방금 바뀐 직후에 부르면 있는 객체도 못 찾는다 (`macro-targets-and-memory` 의 `### find 는 이미 도착한 것만 본다`).

**저장된 macro 가 다른 저장된 macro 를 부르는 것은 첫 버전에서 막는다.** 재귀 depth 와 순환
참조를 런타임에 다뤄야 하기 때문이다. 필요해지면 나중에 연다. **한 source 안의 helper `def`
는 다르고 그것은 연다** — `macro-language-reference` 의 `### 저자가 helper def 를 둘 수 있다` 가 두 금지의 차이를
적는다.

### `write_macro` 는 지금 기록으로 "마지막 N 개" 를 못 만든다

이 항목이 이 계획에서 가장 먼저 확인해야 할 사실이다.

`ToolContext.run` 은 매번 `state.remember_dispatch(actions)`(`state.py:185`)를 부르고, 그것이
하는 일은 이렇다.

```python
for action in actions:
    self.dispatched_action_params[action.method] = list(action.params)
```

**method 이름을 키로 한 dict 이고, method 하나당 마지막 인자 한 벌만 남는다.** 그 method
docstring 이 그렇게 만든 이유까지 적어 뒀다 — 이 값의 소비자는
`capability_tools.py:52` 의 `_action_record` 이고, 그것이 답하는 질문은 "방금 무엇으로
눌렀나" 하나다.

그래서 카드 두 장을 연달아 drag 하면 `move_mouse` 키에는 **두 번째 drag 의 목적지만** 남는다.
`mouse_down` 과 `mouse_up` 도 마찬가지로 한 벌씩이다. 순서도 없고, 어느 action 이 어느 tool
호출에 속했는지도 없다.

**"마지막 N 개 action 을 이 이름으로 저장" 은 이 기록 위에 세울 수 없다.** 세 갈래가 있다.

1. `QaRunState` 에 순서 있는 dispatch log 를 새로 둔다 — `(tool, step, summary, actions)` 를
   append 로 쌓는다. `dispatched_action_params` 는 그대로 두고 옆에 둔다 (그 dict 의 소비자는
   다른 질문에 답하고 있으므로 뜻을 바꾸면 `capability_observation` 의 재현 칸이 틀어진다).
2. agent 에게 step 을 통째로 적게 한다 — 기록을 안 쓴다. 대신 model 이 selector 를 지어낼
   수 있다. `_action_record` 의 docstring 이 그 위험을 이미 이름 붙여 뒀다.
3. 둘을 붙인다 — dispatch log 로 초안을 만들어 agent 에게 보여 주고, agent 가 어느 것을
   파라미터로 뺄지만 말한다.

**갈래 1 이 갈래 3 의 선행이고, 갈래 2 는 단독으로 쓰지 않는다.** 아래 `## 쪼개는 방법` 의
첫 작업 단위가 갈래 1 이다.

거기에 더해, dispatch log 가 들고 있는 것은 **좌표로 풀린 값**이다. `click("#12345")` 는
`move_mouse` 의 params 에 `[12345]` 를 싣고, `click("640,360")` 은 `[640.0, 360.0]` 을 싣는다.
**그 둘은 macro 에 그대로 넣으면 안 되는 값이다** (`macro-targets-and-memory` 의 `## macro 에 id 와 좌표 대신 selector
를 저장한다`). 그러니 `macro-selector-lift` 는 dispatch log 를 그대로 굳히는 것이 아니라, 거기 든
id·좌표를 지금 판독의 selector 로 바꿔 올리는 단계를 반드시 거쳐야 한다. 그 변환의 입력은
`PulseMemory.held` 다 — 기록 하나가 `id` 와 `selector` 와 `text` 를 다 들고 있으므로, 올릴
값을 찾는 조회가 dispatch log 의 id 로도 좌표로도 선다.

바꿔 올릴 자리는 둘이다. 경로가 안 밀리는 객체는 `selector("...")` 로 올리고, 런타임에 spawn
되는 객체는 그 기록의 `text` 를 읽어 `find(label="...")` 로 올린다. **둘 다 안 되면 못
올린다고 말한다** — 좌표를 그대로 굳히는 것보다 정의가 하나 덜 생기는 편이 낫다.

## Non-goals

- **SDK 를 고치는 것. 이 판에서 더 확실해졌다.** batch 실행도 selector 해석도 이미 있고,
  조회 넷이 전부 서버가 이미 든 `PulseMemory` 로 선다. `LiveState.Object`(501~544행)가 객체마다
  `id` · `path` · `selector` · `text` · `tag` · `offers` 를 한 기록에 싣고 `PulseMemory` 가
  그것을 `씬/selector` 로 키 잡는다(`pulse.py:174`). **`find(label=)` 도 `find(name=)` 도
  `under=` 도 그 기록 안에서 끝난다** — 앞선 판이 `SceneMemory` 를 끌어들여야 했던 자리가
  전부 없어졌으므로, 이 계획이 요구하는 SDK 변경은 없다.
- **새 wire protocol.** macro 는 ACTION frame 을 여러 장 보내는 것이고, frame 모양은 그대로다.
- **저장된 macro 가 다른 저장된 macro 를 부르는 것.** 첫 버전에서 막는다. **한 source 안의
  helper `def` 는 다르다** — 호출 그래프가 그 텍스트 안에 전부 있어 저장 시점에 끝나므로
  연다 (`macro-language-reference` 의 `### 저자가 helper def 를 둘 수 있다`).
- **부분 실행을 되돌리는 것.** 되돌릴 방법이 없다. 대신 어디까지 갔는지 보고한다.
- **macro 를 timeline 에서 한 줄로 접는 것.** 안쪽 step 이 전부 남는다.
- **macro 텍스트를 Python 으로 실행하는 것.** Python 문법으로 적고 `ast.parse` 로 읽지만
  `eval` 도 `exec` 도 쓰지 않는다. 허용 node 를 지나온 tree 만 JSON 으로 옮겨 해석한다.
- **`dispatched_action_params` 의 뜻을 바꾸는 것.** 그 dict 는 `capability_observation` 의
  재현 칸에 답하고 있고, 순서 있는 기록은 옆에 새로 둔다.

## 열려 있는 질문

- **같은 글자를 띄운 것이 둘 이상일 때 어느 것을 집나.** v1 의 `find` 는 여기서 멈춘다 (`macro-targets-and-memory` 의
  `### selector 가 조용히 다른 것을 가리키는 한 경우` 의 3번). `under=` 로 대부분 좁혀지지만
  한 부모 아래 같은 글자 두 장은 그것으로도 안 갈린다. 가장 싼 해법은 이미 이 저장소에 있는
  순번 규칙일 수 있다 — `_visual_keys`(`scene.py:146`)의 docstring 이 이름 중복을 이미 다루고
  있고 ("Names do repeat — a scene with five `Enemy` sprites"), 같은 이름을 나열 순서대로
  `Enemy#2` 로 번호 매긴다. **다만 그 규칙은 지금 `visuals` 에만 있고**, 번호가 나열 순서를
  타므로 카드 한 장이 빠지면 경로 selector 의 index 와 똑같이 밀린다. 정하지 않는다.
- **`under=` 의 범위를 묶인 이름으로도 받나.** v1 은 `selector(<문자열>)` 과 selector kind
  parameter 둘만 받는다 (`macro-targets-and-memory` 의 `### under= 를 v1 에 넣는다`). 묶인 이름을 받으면 "방금 찾은
  것 아래에서 찾는다" 를 적을 수 있는데, 그러면 범위가 죽었을 때도 `STALE_BINDING` 이 나야
  하고 그 코드가 겨눔과 범위 두 뜻을 지게 된다. 값이 그만큼인지 안 정했다.
- **`find` 가 `tag` 로도 거르나.** pulse 기록이 `tag` 를 이미 들고 있고(`pulse.py:142`,
  ARTEL-631), 그 주석이 샘플 게임에서 **어느 카드가 어느 조합 칸에 들어가는지가 이것으로
  갈린다**고 적는다. `find(tag="fire", under=...)` 은 글자가 같은 두 장도 가를 수 있는
  경우가 있다. 다만 `Untagged` 는 SDK 가 안 보내므로 "태그 없음" 을 조건으로 적을 문법이
  따로 필요하다. 정하지 않는다.
- **`find` 가 맞추는 글자가 agent 가 본 글자보다 많다.** 화면의 글자 절은 `MAX_SCREEN_TEXT`
  30줄에서 자르고 (`pulse.py:65`), 넘치면 바뀐 줄을 먼저 살리고 나머지는 `(+N more labels on
  screen)` 로 접는다. `find` 는 `held` 사전 전체를 보므로 **그 절에 한 번도 안 찍힌 글자도
  맞춘다.** 화면에 서른 개 넘는 라벨이 있는 게임에서 agent 는 자기가 못 본 글자를 `find` 에
  못 적고, 반대로 macro 를 저장할 때 올린 글자가 부를 때는 안 보인다. 둘을 맞출지, 맞춘다면
  어느 쪽으로 맞출지 안 정했다.
- **`observable()` 의 값을 무슨 타입으로 비교하나.** 거절할지 거짓으로 볼지는 `macro-language-reference` 의
  `### 연산자 dispatch` 가 정했다 — 거절이고, 평가 시점이면 `COMPARISON_REJECTED` 다.
  **남은 것은 scene view 가 `key = value` 로 찍은 글자를 무슨 모양으로 읽느냐다.**
  `observable("cards_in_hand") == 1` 의 왼쪽이 문자열 `"1"` 로 도착했을 때 그것을 수로
  읽을지, 아니면 모양이 다르다고 거절할지 안 정했다. 수로 읽으면 `== "1"` 과 `== 1` 이
  둘 다 참이 되어 표의 행이 둘로 갈라진다.
- **`vector2` 와 `vector3` 를 선언 자리에 들일 것인가.** `macro-language-reference` 의 `### 타입은 선언한다` 가 v1
  에서 그 둘을 선언 자리에서 거절했다 — vector 를 만들 문법도 비교할 연산자도 없어서다.
  아래 `near()` 를 열면 그 둘이 동시에 뜻을 가지므로 **한 번에 정하는 편이 맞다.**
- **vector 를 쓸모 있게 묻는 길 — `near(a, b, 거리)`.** `macro-language-reference` 의 `### 연산자 dispatch` 가 v1 에서
  vector 비교를 전부 거절했다. 남는 쓸모 있는 질문은 근접 하나뿐이고 — "이 카드가 저 슬롯
  위에 있나" — 그것은 비교가 아니라 세 번째 인자로 거리를 받는 읽기여야 한다.
  `Restless` 의 `_bound` 가 월드 단위의 기본값을 추측이라고 못박고 화면 픽셀에서만 1 이
  제 뜻을 말한다고 적으므로, **거리를 무슨 단위로 받을지가 이 항목의 어려운 자리다.** v1 은
  안 연다.
- **`COMPARISON_REJECTED` 를 일곱 번째 코드로 두는 것이 맞나.** `macro-language-reference` 의
  `#### 언제 검사하나 — 선언한 것은 저장 때, 게임이 내는 값은 평가 때` 가 그것을 제안했다. 코드 이름을 하나 더
  두는 값만큼인지, 아니면 저장 때 거절과 같은 무리로 보고 `MACRO_NODE_REJECTED` 를 실행
  중에도 내보낼지 안 정했다. 뒤엣것은 "저장 때 거절되는 것과 실행 때 실패하는 것은 다르다"
  를 깨므로 지금은 앞엣것을 고른다.
- **사람이 macro 정의를 미리 적어 넣는 길을 여나.** 지금 설계는 agent 가 성공한 뒤에만
  만든다. 사람이 적어 두면 첫 런부터 쓸 수 있지만, 검증 안 된 정의가 지도에 앉는다.
  `capability.origin` 이 `evidence` · `observed` · `inferred` · `human` 넷을 이미 가르고
  있으므로 같은 축을 쓸 수 있다.
- **content map 의 새 그릇이 정확히 어떤 schema 인가.** 정해야 하는 것은 최소한 이것들이다 —
  `content_map_id` 외래 키, `name` 의 유일 범위, macro 텍스트 원본을 담는 칸, 파싱된 JSON 을
  담는 칸, 그 JSON 안의 statement 표현(action · `require` · 대입 · `if` · `flag` ·
  `ask_verdict` · `wait_until` 일곱과 predicate 의 `return` 이 한 목록에 섞이나 갈리나 — `if` 는 몸통을 중첩해서 든다),
  `def` 줄에서 읽은 parameter 목록을 **순서 있게** 두는 방법, 그리고 build 단위 에러
  코드 집계를 어디에 쌓나. **`precondition` 칸은 없다** — 첫 `require` 가 그 자리다. 다음
  migration 번호는 `V93` 이다.
- **`POINTER_HELD_BY_PERSON` 을 아홉 번째 코드로 두나.** v1 은 그것을 `ACTION_REJECTED` 로
  보낸다 (`macro-errors-and-reporting` 의 `## 에러 코드 여덟 개`). agent 가 할 일이 같기 때문이다 — step 을 실패로 적지
  않고 다시 부른다. **그 코드에 이제 셋이 산다** — SDK 의 거절, 사람이 쥔 포인터, 그리고
  pulse 를 한 장도 못 받은 경우(`macro-targets-and-memory` 의 `### 읽을 자리가 아예 없을 때 — 하나 남는다`)다. 쪼갠다면 어디를
  어떻게 쪼갤지가 이 항목의 질문이 된다. 따로 두면 "operator 에게 말하라" 를 코드 자체에 실을 수 있고, 환경 문제
  둘이 한 이름 아래 접혀 있는 것도 풀린다. 코드 이름 하나를 더 두는 값만큼인지는 안 정했다.
- **조건에서 못 읽게 된 값 둘을 읽기로 되살리나.** `require()` 의 왼쪽을 호출로만 좁히면서
  다섯을 못 읽게 됐고, 이 판에서 그중 셋을 되살렸다 — `text()` · `static()` · `member()` 다.
  **남은 둘은 `active` 와 `tag` 다.** 예전에는 `selector(S).active` 와 `selector(S).tag`
  였고 attribute access 는 거절이므로 지금 문법으로는 적을 자리가 없다. `active(t)` ·
  `tag(t)` 로 두면 attribute 를 안 쓰고 자리 규칙도 안 깬다. `active` 는 `exists()` 가
  `live` 로 답하는 것과 겹치는 부분이 있어 둘의 경계를 먼저 정해야 하고, `tag` 는 위
  `find` 의 `tag=` 항목과 한 번에 정하는 편이 맞다.
- **`observable()` 을 언제 뗄 것인가.** `macro-language-reference` 의 `#### observable() 은 GAME_STATE 를 켠 빌드
  전용이다` 가 v1 의 선택을 적었다 — 남기되 못박는다. ARTEL-400 이 `states` 를 걷어내면 그
  읽기는 답할 자리가 영영 없어지므로, 그때 문법에서 뺄지 이름만 남기고 거절 문장을 낼지
  안 정했다. **거절 문장을 내는 쪽이 낫다는 근거가 하나 있다** — 저장된 macro 가 그 읽기를
  쓰고 있을 수 있고, 문법에서 지우면 그 macro 는 실행이 아니라 파싱에서 죽는다.

## 쪼개는 방법

저장소별로, 각 줄이 자기 이슈 하나다. 앞의 label 로 grep 한다.

### `artel-agent-server`

| label | 무엇 | 선행 |
|---|---|---|
| `macro-dispatch-log` | `QaRunState` 에 순서 있는 dispatch 기록을 더한다. `(tool, step, summary, actions)` 를 append. `dispatched_action_params` 는 안 건드린다 | 없음. **먼저 간다** |
| `macro-selector-lift` | dispatch 기록의 `target_id` 와 좌표를 `PulseMemory` 에서 찾아 그 기록의 `selector` 를 꺼내 macro 텍스트 초안을 만든다. `PulseObject` 가 `id` 와 `selector` 를 한 기록에 들고 있어 id 는 바로 풀리고, **좌표는 `rect` 로 맞춰야 해서 이 작업에서 제일 불확실한 자리다.** 못 올리는 값은 못 올린다고 말한다 — 지어낸 selector 가 저장되면 그 macro 는 조용히 틀린 것을 겨눈다 | `macro-dispatch-log` |
| `macro-source-parser` | macro 텍스트를 `ast.parse` 로 읽고 허용 node 만 통과시킨다. parameter · 반환 · 대입의 annotation 을 요구하고, `def` 여럿을 읽어 진입점과 helper 를 가르고, 호출 그래프에서 재귀와 깊이와 statement 총수를 정적으로 판정한다. predicate `def`(`-> bool`)의 본문 제한과 모든 경로가 `return` 으로 끝나는지, `wait_until` 의 인자와 경로별 최대 대기 시간 합계, 게임 시간을 멈춘 채 기다리는 경로도 여기서 판정한다. 거절 문장이 받을 수 있는 것을 이름으로 댄다. 실행은 안 한다 | 없음. **먼저 간다** |
| `macro-definition-model` | 통과한 tree 의 pydantic 모델과 JSON 표현, 텍스트 칸과 JSON 칸의 앞뒤 | `macro-source-parser` |
| `macro-find-binding` | `selector(...)` · `find(label=)` · `find(name=)` · `find(under=)` 넷을 전부 `PulseMemory` 에 대고 푸는 조회 하나. 돌려주는 것은 pulse 기록이고, `live` 인 기록만 본다. 읽을 자리가 아예 없을 때(pulse 를 한 장도 못 받음)를 가른다. 묶인 이름의 평가도 여기다. `SELECTOR_NOT_FOUND` · `SELECTOR_AMBIGUOUS` · `STALE_BINDING` 이 여기서 난다 | `macro-source-parser` |
| `macro-runner` | 정의 하나를 batch 여러 개로 쪼개 `ctx.run` 을 여러 번 부르고, 부분 실행 보고를 만든다. helper 호출 frame 을 쌓고 payload 에 호출 사슬을 싣는다. `wait_until` 은 새 pulse 가 올 때마다 조건을 다시 평가하고 `waits` 목록을 결과에 싣는다. 나머지 에러 코드 셋과 `COMPARISON_REJECTED` 와 `WAIT_TIMEOUT` 이 여기서 난다 | 위 셋 |
| `macro-tools` | `write_macro` · `edit_macro` · `read_macro` · `register_macro` · `run_macro` 다섯 tool 과 그 설명. 초안은 텍스트만 들고 JSON 은 `register_macro` 가 만든다. `edit_macro` 는 줄 번호가 아니라 문자열 치환이고 유일하지 않은 `old_text` 는 거절한다 | `macro-runner` |
| `macro-arch-knob` | `QaArchSpec` 에 macro 축을 더하고 `QA_ARCH_LABEL` 을 올린다. tool 다섯이 목록에 드는 것만으로 `arch_fingerprint` 가 모든 런에서 움직이므로 label bump 는 선택이 아니다 | `macro-tools` |

### `artel-orchestration-server`

| label | 무엇 | 선행 |
|---|---|---|
| `macro-schema` | `V93` migration — `content_map` 에 매다는 macro 표와 step 표 | 없음 |
| `macro-write-frames` | macro 를 적고 읽는 frame 둘과 라우터. `docs/capability-write-frames.md` 가 정한 것과 같은 모양으로 | `macro-schema` |
| `macro-frozen-mode` | `ContentMapMode.FROZEN` 이 macro 쓰기도 막는다 | `macro-write-frames` |
| `macro-error-counters` | build 당 에러 코드 집계 | `macro-schema` |

### 순서

`macro-dispatch-log` · `macro-source-parser` · `macro-schema` 셋은 쓰는 파일이 안 겹쳐
동시에 간다. 나머지는 위 표의 선행을 따른다.

`under=` 는 이제 열려 있는 질문이 아니라 문법이다 (`macro-targets-and-memory` 의 `### under= 를 v1 에 넣는다`). 그래서
`macro-source-parser` 는 `find` 의 keyword 세 개를 처음부터 받고, `macro-find-binding` 은
prefix 맞추기를 처음부터 든다.

`macro-tools` 전에 **열려 있는 질문의 첫 항목(같은 글자를 띄운 것이 둘 이상일 때)을 정한다.**
그 답이 `macro-source-parser` 와 `macro-find-binding` 을 둘 다 바꾼다. 그 항목 말고는
`macro-tools` 를 막는 것이 없다.

`macro-tools` 는 `run_macro` 의 설명에 **"부르기 전에 화면을 한 번 관측한다"** 를 넣는다 (`macro-targets-and-memory` 의
`### find 는 이미 도착한 것만 본다`). tool 설명 한 줄이 이 실패를 막는 유일한 자리다.
