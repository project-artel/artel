# macro 의 require 와 실행 의미와 에러 보고

- Date: 2026-09-18
- 입구 문서:
  [`2026-09-18-store-and-replay-action-sequences-as-macros.md`](2026-09-18-store-and-replay-action-sequences-as-macros.md)
  — 머리말과 Goal, 실행기와 저장 자리, 첫 버전 범위, Non-goals, 열려 있는 질문, 그리고
  `## 쪼개는 방법` 이 거기 있다
- 이 파일이 드는 것: `require` 와 remedy, `flag` 와 `ask_verdict`, batch 로 쪼개지는 실행 의미,
  부분 실행 보고, `wait_until` 의 시간 초과 보고, 에러 코드 여덟 개, timeline
- 2026-10-13: `wait_until` 과 에러 코드 `WAIT_TIMEOUT` 을 더했다. `### wait_until 이 시간을
  다 쓰면` 과 `## 에러 코드 여덟 개` 가 그 자리다

## `require()` 가 macro 를 batch 여러 개로 쪼갠다

이것이 구조를 실제로 바꾸는 지점이다.

### action 결과는 게임이 반응했다는 증거가 아니다

`_press_outcome`(`tool_context.py:141`)의 docstring 이 이 사실을 직접 적어 뒀다. SDK 는
`SendMessage` 를 `DontRequireReceiver` 로 부르므로 **받는 handler 가 없어도 통과하고, 있어도
그것이 무엇을 했는지 돌려주지 않는다.** 게임이 지금 입력을 안 받는 상태여도 같은 줄이
나온다. 그래서 그 자리에 "반응했는지는 화면으로 확인할 것" 이 붙어 있다 (ARTEL-777).

**macro 가 action 결과만 보고 다음 단계로 넘어가면 아무것도 확인하지 않은 것이다.**
`require()` 는 있으면 좋은 것이 아니라, action 결과가 증명하는 것이 없기 때문에 필요한
것이다.

### 쪼개지는 모양

`ToolContext.run` 은 `JsonRpcAction` 배열을 한 번에 보내고 그 뒤에 쌓인 pulse 를 돌려준다.
중간에 아무것도 못 끼워넣는다. `require()` 는 화면을 다시 읽어야 하므로 macro 는 이렇게
쪼개진다.

```
batch → 관측 → require 판정 → batch → 관측 → require 판정 → ...
```

왕복 비용은 실제로 는다. **대신 model turn 수는 그대로다** — 이 순환이 tool 하나 안에서,
서버 쪽에서 돌기 때문이다. 이것이 이 계획의 핵심 주장이다: macro 의 이득은 action 을 덜
보내는 것이 아니라 model 을 덜 깨우는 것이다.

`ctx.run` 은 이미 한 번 부를 때마다 `act_and_look`(`channel.py:328`)으로 다음 pulse 를
기다린다. macro 가 `require` 하나마다 `ctx.run` 을 한 번 더 부르면 그 기다림이 그대로 관측
자리가 된다. 새로 지을 대기 장치가 없다. **`if` 의 조건도 그 자리에서 판정한다** — 문법이
`require` 의 첫 인자와 같으므로 평가기도 관측 자리도 하나다
(`macro-language-reference` 의 `### if 는 열고 for 와 while 은 안 연다`).

## require 두 종류 — selector 참조와 명시적 조건

selector 참조는 이미 암묵적인 require 다.
`click(selector("Root[0]/Canvas[1]/CombineButton[2]"))` 은 그 버튼이 지금 있다는 것을
전제하고, 없으면 SDK 가 `Nothing at selector: ...` 로 답한다.

명시적 `require()` 는 selector 가 못 잡는 것에 쓴다 — 지금 누를 수 있는가, 화면에 찍힌 글자가
무엇인가, 게임이 든 값이 얼마인가. 읽을 자리는 네 군데이고 **그중 셋이 pulse 다** —
`offers`(`pulse.py:734`), `PulseObject.text`(`pulse.py:148`), `statics`(`pulse.py:693`)와 객체
`members`(`pulse.py:757`). 넷째가 `observables` 를 `key = value` 로 찍는 scene view 이고,
**그것 하나만 `GAME_STATE` 를 켠 빌드에서 답한다.**

정의 예시는 이렇다.

```python
def attack_with_combined_card(card_a: string, card_b: string, target: object) -> None:
    require(scene() == "Battle", "전투 화면에서만 쓴다. 전투로 먼저 들어가라")
    a: object = find(label=card_a)
    b: object = find(label=card_b)
    drag(a, selector("Root[0]/Canvas[1]/CardSlot(Clone)[0]"))
    drag(b, selector("Root[0]/Canvas[1]/CardSlot(Clone)[1]"))
    require(actionable(selector("Root[0]/Canvas[1]/CombineButton[2]")),
            "두 슬롯이 다 차야 조합 버튼이 살아난다. 어느 카드가 안 들어갔는지 보고 다시 불러라")
    click(selector("Root[0]/Canvas[1]/CombineButton[2]"))
    require(observable("cards_in_hand") == 1,
            "조합이 카드 두 장을 안 먹었다. 손패를 보고 결함으로 적어라")
    click(target)
```

**statement 8 은 이 예시에서 유일하게 `GAME_STATE` 를 켠 빌드를 요구하는 줄이다.**
`observable()` 이 읽는 `SceneMemory.observables` 는 기본 빌드에서 끝까지 비어 있다 (`macro-language-reference` 의
`#### observable() 은 GAME_STATE 를 켠 빌드 전용이다`). 기본 빌드용으로 적으면 그 자리는
이렇게 된다 — 손패 객체의 member 를 직접 묻는다.

```python
    require(member(selector("Root[0]/Canvas[1]/Hand[2]"), "Hand.Count") == 1,
            "조합이 카드 두 장을 안 먹었다. 손패를 보고 결함으로 적어라")
```

**그리고 이 예시에 안 적힌 statement 하나가 실전에서 이것을 통째로 망칠 수 있다.** 대화창이
떠 있으면 카드 drag 가 통째로 취소되고, macro 는 model 을 안 깨우므로 그것을 성공으로
보고한다. 맨 앞에 한 줄을 더 두면 막힌다.

```python
    require(static("InteractionLock.IsLocked") == False,
            "대화창이 떠 있으면 카드 드래그가 통째로 취소된다. 대화창을 닫고 다시 불러라")
```

근거는 `macro-language-reference` 의 `#### static() 을 되살린다 — 래칭 플래그가 macro 를 조용히 망친다` 에 있다.

**selector 리터럴은 언제나 이 전체 형태로 적는다.** `ScenePathSelectorResolver` 가 되짚는
것은 `name[siblingIndex]` 를 `/` 로 이은 경로이므로 `selector("CardSlot/0")` 같은 짧은
형태는 애초에 안 풀린다. 예시가 길어지는 것은 받아들인다 — 예시에 안 풀리는 형태를 두면
읽는 사람이 그대로 베낀다.

statement 6 은 그 pulse 기록의 `offers` 하나로 답한다. 비어 있으면 거짓이고 물러날 자리는
없다 (`macro-targets-and-memory` 의 `### actionable() 은 offers 를 읽는다 — 물러날 자리가 없다`). statement 8 은
`observables` 의 값으로 답한다. **셋 다 서버가 이미 들고 있는 것이고, 새로 물을 frame 이
없다.**

### `require` 는 인자 둘을 받는다 — 조건과 remedy

**`require(<조건>, <remedy 문자열>)` 이고 둘째 인자는 필수다.**

이유는 payload 가 지금 말하지 못하는 것에 있다. `expected` 와 `observed` 는 조건에서 자동
생성한 값이라 **무엇이 틀렸는지는 말해도 그게 무슨 뜻인지는 못 말한다.**
`static("InteractionLock.IsLocked")` 가 `True` 였다는 문장을 받은 agent 는 그 플래그가
무엇을 막는지 모르고, 그것을 아는 것은 그 macro 를 적은 쪽이다.

필수로 두는 선례가 이 저장소에 있다. `app/agents/qa/tools/capability_tools.py:111` 의
`_rationale_problem` 이 빈 `rationale` 을 거절하면서 이 문장을 돌려준다.

> `rationale` is required, so nothing was recorded. Write what you saw in one or two
> sentences, with the identifiers in it — a verdict nobody can retrace is one nobody can
> later decide was wrong — and call this again.

그 docstring 이 여기서 먼저 거절하는 이유까지 적는다 — "왕복 하나를 아끼려는 것이자, 이
거절이 고칠 수 있는 것이기 때문이다 — 무엇을 봤는지 쓰면 된다." remedy 도 같다.

**규칙: remedy 는 무엇을 할지를 적지 조건을 다시 쓰지 않는다.** 조건은 payload 의 `expected`
가 이미 싣는다. 조건을 한국어로 옮겨 적은 remedy 는 줄 하나를 늘리고 아무것도 안 더한다.
이것은 거절 문장에 "받을 수 있는 것을 이름으로 댄다" 를 건 것과 같은 기준이다.

```python
require(static("InteractionLock.IsLocked") == False,
        "대화창이 떠 있으면 카드 드래그가 통째로 취소된다. 대화창을 닫고 다시 불러라")
```

- 에러 payload 에 필드가 하나 는다 — `expected` · `observed` 옆에 `remedy` 다. 사람이 읽는
  모양과 JSON 모양 둘 다 그것을 싣는다 (아래 `## 부분 실행을 반드시 보고한다`).
- 저장 JSON 의 `require` step 에도 칸이 하나 는다. 필수다.
- **statement 개수는 안 바뀐다.** 인자가 는 것뿐이므로 번호를 다시 셀 일이 없다.
- 빈 문자열은 거절한다. remedy 를 빠뜨린 `require` 도 저장 때 거절한다.

#### 함정 — `require(hp = 100)` 은 Python 문법 오류가 아니다

**Python 이 그것을 keyword 인자로 파싱해 `ast.keyword` 노드로 만든다.** `SyntaxError` 가 안
나고, 허용 node 표가 `ast.keyword` 를 받고 있으므로 아무 검사도 안 걸면 **조용히 통과한다.**
그리고 통과한 그것은 조건이 아니다 — 아무것도 판정하지 않는 statement 하나가 macro 에
앉는다.

그래서 **파서가 `require` 호출의 keyword 인자를 이름 대고 거절해야 한다.** 거절 문장이 `==`
를 대 줘야 model 이 한 번에 고친다. `=` 와 `==` 를 헷갈리는 것은 조건을 적는 자리에서 가장
흔한 실수이고, **model 이 제일 밟기 쉬운 함정이다.**

`macro-language-reference` 의 `### 허용하는 node 와 거절하는 node` 의 `keyword` 항목과 거절 메시지에 이 행이 든다.


## `flag` 와 `ask_verdict` — 알리는 것과 판정 의무를 세우는 것

macro 가 지나가다 본 것을 말할 자리가 둘이다. **의무가 붙는 것과 안 붙는 것은 다른 행위라
statement 를 둘로 가른다.**

**`flag(<메시지 문자열>)` 은 그냥 알린다.** step 을 지목하지 않고 판정 의무도 세우지 않는다.
`run_macro` 결과의 `flags` 목록에 실려 agent 에게 가고, **agent 가 무시해도 아무 일도
일어나지 않는다.** macro 가 지나가다 본 것을 말하는 자리다.

**`ask_verdict(<기대 문자열>)` 은 이 macro 를 부른 step 에 판정이 필요하다고 세운다.**
`run_macro` 결과의 `verdict_requests` 목록으로 `flags` 와 따로 돌아간다. 인자는
**기대** 하나다 — `"HP 가 0 이면 패배 화면으로 넘어가야 한다"` 처럼 언제 써도 참인 문장이다.
**본 것을 적으면 안 된다** — macro 글은 저작 시점에 고정이라 이번 런에서 본 것을 인용할 수
없고, 적으면 그 문장이 다음 런에서 거짓이 된다.

**둘 다 보고하지 않는다.** 판정은 QA agent 가 한다 (아래
`## report_step 과 report_case 가 문법에 없다`).

```python
if text(hp_label) == "0":
    flag("패배 화면이 안 떴다")
    ask_verdict("HP 가 0 이면 패배 화면으로 넘어가야 한다")
```

**step 번호를 적지 않는다.** 판정할 step 은 `run_macro` 가 받은 `step` 이다 — macro 안쪽
statement 가 그 값을 전부 물려받는다 (`macro-language-reference` 의
`### step 과 thought 는 macro 의 인자가 아니다`). 처음에는 `ask_verdict(5, ...)` 처럼 번호를
적게 했는데, 그 번호는 호출의 step 과 아무 관계가 없었다. `ask_verdict(4, ...)` 로 등록한
macro 를 `run_macro(step=7)` 로 부르면 agent 에게 4번 step 을 판정하라고 말했고, 같은 macro 를
다른 step 에서 다시 쓸 수도 없었다.

**그리고 강제가 공짜다.** `finish_run` 은 판정 없는 step 이 남은 채 끝내려는 첫 시도를 이미
되민다 — `QaRunState.unreported_steps` 를 세고 `finish_attempts` 가 1 일 때 되밀며 둘째 시도는
그대로 닫는다. 그 목록은 시나리오 step 중 판정이 없는 것을 센다. **`ask_verdict` 가 청한
step 은 `report_step` 이 올 때까지 그 목록에 남으므로 `finish_run` 이 그대로 되민다 — 새 강제
장치를 만들지 않는다.** `flag` 는 어느 step 도 지목하지 않으므로 그 목록에 아무것도 더하지 않는다.
**두 statement 의 차이가 이것이다.**

### `observed` — 감싼 `if` 조건이 읽은 값

runner 가 `flags` 와 `verdict_requests` 의 항목마다 `observed` 를 붙인다. **그 statement 를
감싼 `if` 조건 안의 reader 호출 값 전부다.** 위 예시면 `text(hp_label)` 이 실제로 무엇이었는지
가 그것이다. 감싼 `if` 가 여럿이면 그 조건 전부의 reader 호출 값을 든다.

**감싼 `if` 가 없으면 `observed` 는 비고, 그래도 statement 는 선다.**

**이 정의가 `if` 와 `flag` · `ask_verdict` 를 한 쌍으로 쓰게 만드는 이유다.** `if` 가 무엇을
읽을지 정하고 `flag` 나 `ask_verdict` 가 그것을 알린다. `ask_verdict` 쪽에서는 macro 가 적은
`expected` 와 runner 가 읽은 `observed` 가 짝이 되어야 agent 가 판정할 수 있고, **그것은 아래
`## 부분 실행을 반드시 보고한다` 의 payload 가 `expected` 와 `observed` 로 하는 일과 같은
기계다.**

`if` 가 안 간 분기의 `flag` 와 `ask_verdict` 는 거두지 않는다. `require` 가 실패해 멈춘
경우에는 그 앞에서 거둔 것을 에러 payload 에 같이 싣는다. 항목마다 어느 `def` 의 몇 번에서
섰는지를 들고, helper 안에서 선 것도 거둔다.

## `report_step` 과 `report_case` 가 문법에 없다

문법에서 빠뜨린 것이 아니라 **macro 가 쥐고 있지 않은 것이다.**

판정은 **시나리오와 앞 step 과 operator 의 말과 읽은 knowledge 를 쥔 QA agent 의 몫이다.**
근거는 `report_step` 의 docstring 이 `used_knowledge_ids` 를 정의하는 말이다 — 이 판정에
실제로 영향을 준 knowledge, 곧 읽고 나서 그 때문에 다르게 판정한 것이다. macro 는 그 넷을
하나도 쥐고 있지 않다. 지나가다 읽은 값 하나로 step 판정을 적으면 그 넷을 안 보고 적는 것이다.

`report_case` 는 더 간단하다. **step 판정에서 파생되는 값이다** — `QaRunState.case_units` 가
step 판정을 모아 case 단위를 만든다. 파생되는 값은 보고 대상이 아니다.

**macro 는 그냥 더 긴 `ctx.run` 이다.** `ctx.run` 이 결과를 agent 에게 돌려주고 agent 가
판정하는 기존 분업과 같은 모양이고, 이 한 문장이 이 설계 전체를 제일 짧게 요약한다. macro 가
더하는 것은 statement 여러 개를 agent 를 안 깨우고 잇는 것뿐이고, 판정이 어디서 나는지는
한 줄도 안 바꾼다.

## 부분 실행을 반드시 보고한다

statement 6 의 `require` 가 실패하면 앞의 두 `drag` 는 **이미 일어났다.** 되돌릴 방법이
없다. 그러니 돌아오는 값이 "실패" 가 아니라 "어디까지 갔고 지금 게임이 어떤 상태인지"
여야 한다.

**statement 번호가 곧 step 번호다.** 위 정의는 statement 아홉 개이고, 여섯 번째가 실패하면
이렇게 돌아온다.

```
REQUIRE_FAILED
  macro:    attack_with_combined_card
  args:     card_a=shoot, card_b=fire, target=.../Enemy(Clone)[2]
  bound:    a=#4821 (shoot), b=#4822 (fire)
  at:       attack_with_combined_card 의 step 6 of 9 —
                      require(actionable(selector("Root[0]/Canvas[1]/CombineButton[2]")),
                                  "두 슬롯이 다 차야 조합 버튼이 살아난다. 어느 카드가 안 들어갔는지 보고 다시 불러라")
  expected: actionable(selector("Root[0]/Canvas[1]/CombineButton[2]"))
  observed: Root[0]/Canvas[1]/CombineButton[2] offers nothing
  remedy:   두 슬롯이 다 차야 조합 버튼이 살아난다. 어느 카드가 안 들어갔는지 보고 다시 불러라
  applied:  steps 4-5 (drag #4821 → .../CardSlot(Clone)[0],
                       drag #4822 → .../CardSlot(Clone)[1])
  released: nothing was left pressed
  skipped:  none (this definition has no `if`)
  pending:  steps 7-9 (not sent)
```

**`at` 줄은 어느 `def` 의 몇 번째인지를 댄다.** 번호는 `def` 마다 1부터 세므로 함수 이름이
없으면 번호만으로는 어디인지 모른다 (`macro-language-reference` 의 `#### 펼치지 않는다 — step N of M 이 저자가 쓴 줄과
맞아야 한다`). 실패한 자리가 helper 안이면 호출 사슬이 한 줄씩 따라붙는다.

```
  at:       play_card 의 step 2 of 2 — drag(c, slot)
            attack_with_combined_card 의 step 3 에서 불림
```

JSON 쪽은 `at` 에 `fn` 을 더하고 `at.call_stack` 을 진입점부터 차례로 든다 —
`[{"fn": "attack_with_combined_card", "step": 3}]` 이다. `applied.detail[]` 의 항목마다도
`fn` 이 붙는다. `pending` 은 멈춘 frame 의 남은 statement 를 먼저 적고 그 다음에 부른 쪽의
남은 statement 를 바깥쪽으로 차례로 적는다 — 묶음마다 자기 `fn` 을 든다. `skipped` 도
`applied` · `pending` 과 같은 모양으로 `skipped.steps` 를 들고 번호마다 `fn` 을 든다.

`remedy` 줄은 그 `require` 의 둘째 인자를 그대로 싣는다. `expected` 와 `observed` 가 무엇이
틀렸는지를 말하고 `remedy` 가 그래서 무엇을 하라는지를 말한다 — 앞의 둘은 조건에서 자동
생성한 값이라 뒤엣것을 못 만든다 (위 `### require 는 인자 둘을 받는다 — 조건과 remedy`).
JSON 쪽에서도 `expected` · `observed` 옆에 `remedy` 가 문자열 하나로 든다.

`applied` 는 **실제로 게임에 나간 action statement 만 센다.** 여기서는 4-5 이다.
statement 1·2·3 도 통과했지만 `require` 와 대입이라 게임에 아무것도 안 보냈고, 그래서
`applied` 에 안 든다. 이 규칙에 예외는 없다 — **`require` · 대입 · `if` · `flag` ·
`ask_verdict` · `wait_until` 여섯은 batch 를 하나도 안 만들므로 `applied` 에 절대 안 오른다.** action
statement 하나만 `applied` 에 오른다. 실패한 statement 자체는 `at` 줄이 번호로 든다.

**`applied` 와 `pending` 을 합쳐도 1부터 전체 statement 수가 안 된다.** 통과한 `require` 와
성공한 대입은 어느 쪽에도 안 든다 — 게임에 아무것도 안 보냈으니 `applied` 가 아니고, 이미
지나갔으니 `pending` 도 아니다. 위 예시의 1·2·3번이 그렇다. 둘은 번호를 나눠 갖는 짝이 아니라
각자 다른 질문에 답하는 목록이다. `applied` 는 "무엇이 게임에 일어났나", `pending` 은
"무엇이 아직 안 나갔나" 다.

### `skipped` — 조건이 거짓이라 원래 안 가는 분기

**`applied` 와 `pending` 둘이던 것에 `skipped` 가 는다.** `skipped` 는 **`if` 의 조건이 거짓
으로 판정되어 가지 않은 분기 안의 statement 번호**다.

**실패해서 못 나간 것(`pending`)과 조건이 거짓이라 원래 안 가는 것은 전혀 다른 얘기다.**
구분하지 않으면 payload 를 읽는 쪽이 번호 하나를 볼 때마다 "이것은 막혀서 안 나간 건가 원래
안 가는 건가" 를 추측한다. 그 추측이 틀리면 agent 는 안 일어난 일을 되돌리려 들거나 일어난
일을 안 일어난 것으로 읽는다. **사람이 읽는 payload 와 JSON 둘 다 이 목록을 든다.**

**실패 지점 뒤에 있어서 `if` 가 아직 판정되지 않은 분기의 statement 는 `skipped` 가 아니라
`pending` 이다.** 조건을 판정한 적이 없으므로 안 간다고 말할 근거가 없고, 그 분기는 다시
불렀을 때 갈 수도 있다. 세 목록이 각자 답하는 질문이 이렇게 갈린다 — `applied` 는 "게임에
무엇이 일어났나", `skipped` 는 "무엇이 판정 결과 안 가기로 됐나", `pending` 은 "무엇이 아직
안 나갔나" 다.

`bound` 줄이 따로 있는 이유는 묶인 이름이 `args` 에도 `applied` 에도 안 나타나기 때문이다.
`applied` 의 `drag #4821` 만 보면 그 id 가 어디서 왔는지 알 수 없다. `STALE_BINDING` 일
때는 이 줄이 진단의 전부다.

`released` 줄은 멈추면서 자기가 푼 것을 든다. `hold_key` · `hold_mouse_button` ·
`set_input_axis` · `set_input_button` · `pause_game_time` 은 아무것도 자동으로 안 풀어
주므로 — 다섯 tool 의 docstring 이 전부 "Nothing releases this for you" 라고 적어 뒀다 —
macro 가 중간에 멈추면 그때까지 자기가 누른 것을 푸는 action 을 마지막 batch 한 번에 담아
보낸다. 이것이 없으면 `hold_key("W")` 다음 statement 에서 멈춘 macro 가 남은 런 내내 W 를
누른 상태로 둔다.

`applied` 줄이 없으면 agent 는 처음부터 macro 를 다시 부르고, 카드가 이미 슬롯에 올라가
있으니 두 번째 시도는 첫 번째와 다른 이유로 실패한다.

`pending` 은 `not sent` 라고 말할 수 있어야 한다. `store-and-replay-action-sequences-as-macros` 의
`### batch 는 중간 실패에서 안 멈춘다`
가 그 조건이다 — action statement 하나가 batch 하나여야 "안 보냈다" 가 참이 된다. 한 batch
에 action statement 둘을 담으면 뒤엣것을 보낸 뒤에야 실패를 알게 되고, 그때는 `pending` 이
거짓말이다.

### `wait_until` 이 시간을 다 쓰면

`macro-language-reference` 의 `### wait_until 은 조건이 참이 될 때까지 기다린다` 의
`enter_dungeon` 이 20초 안에 로딩을 못 끝내면 이렇게 돌아온다.

```
WAIT_TIMEOUT
  macro:    enter_dungeon
  args:     (none)
  bound:    loading=Root[0]/Canvas[1]/Loading[0], error_popup=Root[0]/Canvas[1]/ErrorPopup[0]
  at:       enter_dungeon 의 step 4 of 5 —
                      wait_until(loading_done(loading, error_popup), 20.0,
                                 "로딩이 20초 안에 안 끝났다. 화면을 관측하고 로딩 화면이 멈췄으면 결함으로 적어라")
  expected: loading_done(loading, error_popup)
  observed: absent(loading) = False, exists(error_popup) = False
            loading_done 의 step 5 — return False 로 끝남
  waited:   20.0s, readings: 37, evaluations: 38
  remedy:   로딩이 20초 안에 안 끝났다. 화면을 관측하고 로딩 화면이 멈췄으면 결함으로 적어라
  applied:  step 1 (click Root[0]/Canvas[1]/EnterButton[0])
  released: nothing was left pressed
  skipped:  none (this definition has no `if`)
  pending:  step 5 (not sent)
```

`require` 실패의 payload 와 다른 줄은 셋이다.

- **`observed` 는 마지막 평가에서 읽은 값이다.** 조건이 predicate 이면 그 안에서 읽은 값
  전부와, 어느 `return` 으로 끝났는지를 그 `def` 의 step 번호로 싣는다
  (`macro-language-reference` 의 `### predicate def 는 bool 을 돌려준다`). 위 예시면 두 `if`
  가 모두 거짓이라 맨 끝 `return False` 로 끝났다.
- **`waited` 는 기다린 시간과 두 개의 수를 싣는다.** `readings` 는 기다리는 동안 도착한 pulse
  수이고 `evaluations` 는 조건을 평가한 횟수다. 처음 한 번은 pulse 를 안 기다리고 평가하므로
  `evaluations` 가 `readings` 보다 하나 많다. **`readings` 가 0 이면 그동안 게임에서 pulse 가
  한 장도 안 왔다는 뜻이다** — 게임이 멈췄거나 연결이 끊긴 것이고, 조건이 틀린 것이 아니다.
- **`remedy` 는 `wait_until` 의 셋째 인자 그대로다.**

JSON 쪽은 `observed` 에 `returned_at: {"fn": "loading_done", "step": 5}` 를 더하고,
`waited` 를 `{"seconds": 20.0, "readings": 37, "evaluations": 38}` 로 싣는다.

**시간 안에 참이 된 `wait_until` 도 기다린 시간을 남긴다.** 실패하지 않았어도 기다린 시간은
런을 읽는 사람에게 필요한 정보다 — 로딩이 매번 19초 걸린다면 상한 20초가 곧 깨질 것이다.
`wait_until` 은 `ctx.run` 을 안 부르므로 `ACTION` frame 이 안 생긴다 (아래
`## macro 안쪽 단계를 timeline 에 남긴다`). 그래서 `run_macro` 가 돌려주는 결과에 `waits`
목록을 둔다. 항목 하나가 `wait_until` 하나이고 `fn` · `step` · `seconds` · `readings` 를
든다. 그 결과는 `TOOL_RESULT` frame 에 실리므로 timeline 에 남는다. 성공한 실행에도 실패한
실행에도 같은 목록이 붙는다.

## 에러 코드 여덟 개

코드를 나눈 기준은 **agent 가 macro 가 낡은 것과 게임이 잘못된 것을 구분할 수 있는가** 다.

| 코드 | 뜻 | agent 가 무엇을 의심해야 하나 |
|---|---|---|
| `SELECTOR_NOT_FOUND` | selector 나 `find` 가 **볼 목록은 있는데** 거기서 아무것도 못 찾았다 | **먼저 관측을 의심한다** — 그 객체의 첫 판독이 아직 안 왔을 수 있다. 그 다음이 낡은 macro 이고, 그 다음이 결함 |
| `SELECTOR_AMBIGUOUS` | `find` 가 둘 이상 잡았다 | macro 정의 문제. 게임 문제 아님 |
| `STALE_BINDING` | 묶어 둔 id 가 쓰는 순간 더는 안 풀린다 | macro 가 너무 일찍 묶었다. 다시 부르면 된다 |
| `REQUIRE_FAILED` | 명시적 조건이 거짓 | 게임이 다르게 동작한 것. 버그일 가능성이 높음 |
| `SCENE_MISMATCH` | action 이 하나도 나가기 전에 실패한 `require` | agent 가 엉뚱한 자리에서 불렀다 |
| `ACTION_REJECTED` | SDK 가 action 자체를 거절했거나, 포인터를 사람이 쥐고 있거나, `PulseMemory` 가 통째로 비어 있다 | 환경 문제. 게임도 macro 도 아님 |
| `COMPARISON_REJECTED` | 도착한 값의 모양에 그 연산자가 없다 | macro 정의 문제. 게임 문제 아님 |
| `WAIT_TIMEOUT` | `wait_until` 의 조건이 최대 대기 시간 안에 참이 되지 않았다 | **`readings` 를 먼저 본다.** 0이면 그동안 pulse 가 한 장도 안 왔다는 뜻이라 환경 문제다. 1 이상이면 게임이 그 상태로 안 갔거나 늦게 갔다. `observed` 로 어느 쪽인지 가린다 |

**일곱 번째 코드 `COMPARISON_REJECTED` 를 `macro-language-reference` 의 `#### 언제 검사하나 — 선언한 것은 저장 때,
게임이 내는 값은 평가 때` 가 제안한다.** 도착한 값의 모양에 그 연산자가 없을 때 나가는 것이고, 위 다른 여섯의
이름은 하나도 안 바뀐다.

**여덟 번째 코드 `WAIT_TIMEOUT` 은 `wait_until` 에서만 난다** (`macro-language-reference` 의
`### wait_until 은 조건이 참이 될 때까지 기다린다`). `REQUIRE_FAILED` 와 따로 두는 이유는
agent 가 할 일이 다르기 때문이다. `REQUIRE_FAILED` 는 게임이 다르게 동작했다는 뜻이고,
`WAIT_TIMEOUT` 은 게임이 그 상태로 **아직** 안 갔다는 뜻일 수도 있다 — 기다리는 시간이
짧았는지, 게임이 멈췄는지를 agent 가 관측해서 가려야 한다. 그래서 `WAIT_TIMEOUT` 은 그냥 넘어가도
안 되고 곧바로 step 실패로 적어도 안 된다. 관측한 뒤 판정한다. **`SCENE_MISMATCH` 같은 위치
구분은 없다.** `applied` 가 비어 있어도 `WAIT_TIMEOUT` 이다.

**여덟 코드에 `MACRO_` 접두를 안 붙인다.** 위 payload 의 첫 줄이 `REQUIRE_FAILED` 인 것이
그래서다. macro 가 내는 코드라는 것은 payload 의 `macro` 줄이 이미 말하고, 접두를 붙이면
같은 코드가 두 철자로 도는 자리가 생긴다.

**저장 때 거절되는 것은 이 여덟과 다른 무리다.** 문법에 없는 것을 썼거나 tool 이름이
틀렸거나 하는 것은 실행 전에 걸리고, 거기서 나가는 것은 `MACRO_SYNTAX_ERROR` 와
`MACRO_NODE_REJECTED` 둘이다. 앞엣것은 CPython 이 못 읽은 경우로 `SyntaxError` 의 줄과 칸을
그대로 싣고, 뒤엣것은 읽히기는 했는데 허용 node 가 아닌 경우로 **거절한 것과 대신 쓸 것을
한 줄씩 댄다.** 이 둘은 위 여덟에 접두를 붙인 이름이 아니라 그 자체로 다른 이름이고, 거절된
macro 는 이름이 안 생기므로 부를 수도 없다.

`SELECTOR_AMBIGUOUS` · `STALE_BINDING` · `ACTION_REJECTED` · `COMPARISON_REJECTED` 는 게임
얘기가 아니므로 agent 가 step 을 실패로 판정하면 안 되고, `REQUIRE_FAILED` 는 반대로 그냥 넘어가면 안 된다.

`SCENE_MISMATCH` 와 `REQUIRE_FAILED` 를 가르는 것은 **문법이 아니라 위치다.** 둘 다 실패한
`require` 하나에서 나고, `applied` 가 비어 있으면 `SCENE_MISMATCH`, 하나라도 나갔으면
`REQUIRE_FAILED` 다. 그래서 예전 `precondition` 문법이 없어져도 두 코드가 그대로 남는다.
**대신 개념이 하나 줄었다** — 적는 사람이 "이것은 precondition 인가 require 인가" 를 고를
일이 없다. 첫 `require` 를 맨 앞에 두면 그것이 precondition 이다.

두 코드가 지금 어디서 나오는지 적어 둔다.

- `ACTION_REJECTED` 는 이미 두 자리에서 난다. `parse_target` 이 세 형태 중 어디에도 안 맞는
  문자열을 **게임에 아무것도 보내기 전에** 거절하고, SDK 는 `ActionResultItem.success=false`
  와 `error` 문자열로 거절한다. 여기에 세 자리가 더 붙는다. `macro-language-reference` 의 `### target 자리에 오는 것은
  셋뿐이다` 의 호출 시점 인자 검사가 하나이고 — 좌표나 `#` id 가 target 자리 parameter 로
  들어오면 batch 가 하나도 안 나간 채로 거절한다 — `_press_outcome` 이 `pointerHeldByPerson`
  을 참으로 실어 보낸 경우가 둘이고, **pulse 를 한 장도 못 받은 경우**가 셋이다
  (`macro-targets-and-memory` 의 `### 읽을 자리가 아예 없을 때 — 하나 남는다`). 뒤의 둘을 여기 두는 이유는 agent 가 할 일이 같기
  때문이다: step 을 실패로 적지 않고 관측한 뒤 다시 부른다. 새 코드로 뗄지는 `store-and-replay-action-sequences-as-macros` 의
  열려 있는 질문에 남는다.
- `SELECTOR_NOT_FOUND` 는 SDK 의 `Nothing at selector: ...` 와
  `Selector was truncated by the scan and cannot be resolved: ...` 두 문장이다. 후자는 scan
  이 계층 깊이 한계 64 를 넘겨 `.../` 로 자른 selector 이고 **애초에 풀 수 없다** — 그런
  selector 는 macro 에 저장하지 않는 편이 맞다. 여기에 세 번째 자리가 붙는다. `find` 가
  `PulseMemory.held` 에서 아무것도 못 찾은 경우이고, 그것은 **게임에 아무것도 보내기 전에**
  그 대입 statement 에서 난다. **그 사전이 비어 있었으면 여기 안 든다** — 그때는
  `ACTION_REJECTED` 다 (`macro-targets-and-memory` 의 `### 읽을 자리가 아예 없을 때 — 하나 남는다`).
  **이 코드에서 agent 가 할 일의 첫 번째는 관측이다.** `find` 는 이미 도착한 판독만 보므로,
  그 객체의 첫 판독이 오기 전에 부른 macro 가 정확히 이 코드를 낸다 (`macro-targets-and-memory` 의
  `### find 는 이미 도착한 것만 본다`). 관측하고 다시 불러도 같은 코드가 나면 그때 macro 가
  낡았는지, 그 element 가 없는 것이 결함인지를 가린다.

**`SELECTOR_AMBIGUOUS` 는 경로 selector 로는 안 나고 `find` 에서 난다.**
`name[siblingIndex]` 경로는 한 번의 scan 안에서 정확히 하나를 가리키도록 만들어져 있다.
`find` 는 조건 검색이라 다르다 — 같은 글자 `shoot` 을 띄운 카드가 손패에 두 장이면 둘 다
걸리고, 어느 쪽을 집을지 macro 텍스트가 말한 적이 없다. **그때 하나를 골라 주면 안 된다.**
고르는 규칙이 정의에 없으므로 고른 것은 서버가 지어낸 것이다. 거절하고, 글자가 유일하지 않다고
말한다.

**`STALE_BINDING` 을 `REQUIRE_FAILED` 와 섞으면 안 된다.** 이 코드가 없으면 죽은 binding 은
"닿은 것 없음" 으로 나타나고, agent 는 그것을 게임이 다르게 동작한 것으로 읽어 **게임 버그가
아닌 것을 게임 버그로 보고한다.** `STALE_BINDING` 에서 agent 가 할 일은 macro 를 다시 부르는
것이지 step 을 실패로 적는 것이 아니다.

어디서 나는지도 못박아 둔다. **묶인 이름을 쓰는 statement 에서 그 id 가 안 풀리면
`SELECTOR_NOT_FOUND` 가 아니라 `STALE_BINDING` 이다.** 둘이 가리키는 것이 다르다 — 전자는
macro 텍스트에 적힌 selector 가 낡았다는 뜻이고, 후자는 이 런에서 몇 statement 전에 `find`
로 푼 값이 그 사이에 죽었다는 뜻이다. 전자는 정의를 고쳐야 하고 후자는 다시 부르면 된다.

**click 계열 statement 뒤에는 "닿았는가" 가 암묵적 require 로 붙는다.** `_press_outcome` 이
`reached` 가 빈 것을 셋 중 한 갈래로 내는데, macro 가 자기 판단으로 다음 statement 를 보내는
이상 직전 statement 가 아무 데도 안 닿았다는 사실을 안 묻고 넘어갈 수 없다. 그때 어느
코드가 나느냐를 **그 자리를 무엇으로 겨눴는지가 정한다** — 적어 둔 selector 로 겨눴으면
`REQUIRE_FAILED` 이고, 묶은 이름으로 겨눴으면 `STALE_BINDING` 이다. 그것은 macro 자신이 아는
사실이라 SDK 가 새 신호를 보낼 필요가 없다.

## macro 안쪽 단계를 timeline 에 남긴다

QA agent 에게 macro 를 주면 model turn 은 줄지만, 카드 drag 가 실제로 깨졌을 때 macro 가
그것을 한 번의 성공으로 뭉갤 수 있다. **macro 는 timeline 을 줄이는 것이 아니라 model turn
을 줄이는 것이다.**

지금 timeline 에 무엇이 남는지는 두 자리로 갈린다.

| frame | 언제 | 무엇을 싣나 |
|---|---|---|
| `TOOL` · `TOOL_RESULT` | model 의 tool 호출 하나마다 | `tool`, `tool_call_id`, `args` 전부 (`channel.py:246`) |
| `ACTION` | `ctx.run` 한 번마다 | `message`(요약), `step`, `actions` |

**그래서 macro step 하나가 `ctx.run` 한 번이면 `ACTION` frame 은 지금과 똑같이 step 마다
남는다.** 여기는 새로 할 일이 없다.

**`thought` 는 다르다.** 모든 action tool 이 `thought` 를 인자로 받지만 tool 본문은 그것을
안 읽는다 — `TOOL` frame 이 `args` 를 통째로 싣기 때문에 timeline 에 남는 것이다. 그러니
`run_macro` 한 번은 `thought` 하나다. **안쪽 아홉 statement 가 각자 model 이 쓴 thought 를
가질 길은 없다.**

그 자리에 들어가는 것은 statement 텍스트 자체다. **원문 한 줄을 그대로 쓴다** — 파싱된
JSON 이 statement 마다 그 줄의 텍스트를 들고 있고, `ctx.run` 의 `summary` 인자에 그것을 넣으면
`ACTION` frame 마다
`drag(a, selector("Root[0]/Canvas[1]/CardSlot(Clone)[0]"))` 이 남는다.

처음 떠오르는 `ast.unparse` 는 안 쓴다. 그것은 원문을 돌려주는 것이 아니라 tree 를 다시
찍는 것이라 **큰따옴표가 작은따옴표로 바뀌고 주석은 아예 없다.** timeline 에 agent 가 적은
글자와 다른 글자가 남을 이유가 없으므로, 저장할 때 statement 마다 원문 한 줄을 같이 넣어
두고 그것을 쓴다.

**`#` 주석은 `ast` 에 안 남는다.** 파서가 `#` 뒤를 버리므로 tree 에는 없다. 그래서 주석으로
단 한 줄 설명을 timeline 에 올리려면 **저장할 때 `tokenize` 로 한 번 더 훑어 줄 번호로 맞춰
붙여야 한다.** `ast.parse` 하나로 끝내려던 것을 두 번 훑게 만드는 비용이 있고, 대신 텍스트 한
판에 timeline 문장까지 들어간다. 붙은 뒤에는 저장된 JSON 의 것이 되고 그 다음부터 텍스트를
다시 안 본다. 주석이 없는 statement 는 원문 한 줄이 그 자리에 간다.

그리고 에러 코드는 **build 단위로 센다.** "이 build 에서 macro A 가 `SELECTOR_NOT_FOUND` 로
12번 깨졌다" 가 그 정의를 언제 버릴지 아는 유일한 방법이다.
