# macro 표기법 — 문법과 함수와 상한

- Date: 2026-09-18
- 입구 문서:
  [`2026-09-18-store-and-replay-action-sequences-as-macros.md`](2026-09-18-store-and-replay-action-sequences-as-macros.md)
  — 머리말과 Goal, 실행기와 저장 자리, 첫 버전 범위, Non-goals, 열려 있는 질문, 그리고
  `## 쪼개는 방법` 이 거기 있다
- 이 파일이 드는 것: 표기법, 함수 전체 목록, 타입 선언, helper `def`, predicate `def`,
  연산자 dispatch, 대입, `if`, `wait_until`, 허용·거절 node, 상한
- 2026-10-13: `wait_until` 과 predicate `def`(`-> bool`)를 더했다. `### statement 는 일곱
  가지다`, `### wait_until 은 조건이 참이 될 때까지 기다린다`,
  `### predicate def 는 bool 을 돌려준다`, `### 세는 상한 일곱` 이 그 자리다

## 표기법 — Python 함수 하나를 `ast.parse` 로 읽고 실행은 안 한다

macro 정의 하나는 `macro-errors-and-reporting` 의 `## require 두 종류` 예시처럼 Python 함수로 보이는 텍스트다 — 진입점 하나와, 있으면
helper `def` 몇 개다. 그것을 `ast.parse` 로
읽고, 나온 tree 에서 **허용 node 만 통과시키고 나머지는 전부 거절한다.** 통과한 것도
실행하지 않는다 — `eval` 도 `exec` 도 쓰지 않는다. tree 를 아래 JSON 으로 옮기고, 그 JSON 을
`macro-runner` 가 해석한다.

`ast.parse` 를 쓰는 이유는 셋이다. 문법 오류 메시지가 공짜다 — `SyntaxError` 의 줄과 칸을
그대로 거절 사유로 돌려주면 되고, 괄호를 안 닫은 model 이 그 자리를 바로 본다. 편집기와
문서 코드 블록의 highlighting 이 공짜다. 그리고 파서를 새로 안 만들어도 된다.

대가는 하나이고 작지 않다. **Python 처럼 보이지만 Python 이 아니다.** model 은 `if` 로
분기하고 `for` 로 반복하고 아무 값이나 변수에 대입하려 든다. **`if` 는 든다** (아래
`### if 는 열고 for 와 while 은 안 연다`). `for` 와 `while` 은 없고, 대입은 `find(...)` ·
`selector(...)` · 리터럴 셋에만 열려 있다. 그래서 허용 node 를 아래에 못박고, 거절 문장은
`parse_target` 의 선례대로 **받을 수 있는 것을 이름으로 전부 댄다.**

### 이 언어의 함수 전체 목록

이 언어가 이름으로 부를 수 있는 것이 전부 여기 있다. 네 묶음이고, 묶음마다 그 이름이 어느
자리에 서는지가 다르다. 각 묶음의 규칙은 아래 절들이 든다.

**(A) action 함수 열네 개 — 게임으로 나가는 statement.** 아래가 macro 안에서 적는 모양이다.
실제 tool 시그니처에서 `step` 과 `thought` 를 뺐다 — 그 둘은 `run_macro` 호출이 받아 자기가
보내는 batch 에 전부 싣는다 (아래 `### step 과 thought 는 macro 의 인자가 아니다`). **타입
이름은 이 언어의 것이다** (아래 `### 타입은 선언한다`) — Python 쪽 시그니처는 `str` 과 `int`
로 적혀 있고, 겨누는 자리를 이 언어는 `object` 라고 부른다.

| 함수 | 짝을 맞춰 풀어야 하나 | 메모 |
|---|---|---|
| `click(target: object, button: int = 0)` | 아니오 | |
| `double_click(target: object, button: int = 0)` | 아니오 | |
| `move_pointer(target: object)` | 아니오 | 누르지 않고 포인터만 옮긴다 |
| `drag(from_target: object, to_target: object, button: int = 0)` | 아니오 | **양 끝이 서로 독립이다** |
| `enter_text(target: object, value: string)` | 아니오 | tool 의 `target_id: int` 자리가 macro 문법에서는 `target` 이다. 아래 참조 |
| `press_key(key_code: string, duration_seconds: float)` | 아니오 | `duration_seconds` 는 0보다 커야 한다 |
| `hold_key(key_code: string)` | **예** — `release_key(같은 key_code)` | |
| `release_key(key_code: string)` | 푸는 쪽 | |
| `hold_mouse_button(button: int = 0)` | **예** — `release_mouse_button(같은 button)` | |
| `release_mouse_button(button: int = 0)` | 푸는 쪽 | |
| `set_input_axis(axis_name: string, value: float)` | **예** — 같은 `axis_name` 에 `0` 을 다시 넣는다 | `value` 는 -1 에서 1 |
| `set_input_button(axis_name: string, pressed: bool)` | **예** — 같은 `axis_name` 에 `pressed=False` | |
| `pause_game_time()` | **예** — `resume_game_time()` | |
| `resume_game_time()` | 푸는 쪽 | |

**짝은 다섯이다** — `hold_key`/`release_key`, `hold_mouse_button`/`release_mouse_button`,
`set_input_axis`(0 으로 되돌림), `set_input_button`(`pressed=False`),
`pause_game_time`/`resume_game_time`. 마지막 statement 뒤에 안 풀린 것이 하나라도 남으면
저장 때 거절한다 (아래 `### 눌러 둔 것이 macro 끝에 남으면 거절한다`).

**`target` 자리에 올 수 있는 것은 셋이다** — `selector(<문자열 리터럴>)`, `def` 줄의
parameter, 그리고 대입이 묶은 이름. 맨문자열은 못 온다 (아래 `### target 자리에 오는 것은
셋뿐이다`). `find(...)` 는 그 자리에 직접 못 선다 — 대입으로 이름에 묶고 그 이름을 쓴다.

**`drag` 의 양 끝은 서로 독립이다.** develop 의 docstring 이 "Each end is independently one
of the three forms" 라고 적는다. 한쪽을 `selector(...)` 로 다른 쪽을 묶은 이름으로 둘 수
있고, 양끝을 둘 다 묶은 이름으로 두어도 된다.

**(B) macro 에서 못 쓰는 action tool 둘.** `action_tools.py` 의 tool 열여섯 개 중 둘이
빠진다.

| tool | 왜 빠지나 |
|---|---|
| `click_button(target_id: int)` | develop 의 docstring 첫 줄이 `DEPRECATED` 다. `onClick` 을 직접 불러 포인터도 EventSystem 도 안 지나므로 **occlusion 을 안 본다** — 위에 대화창이 덮여 있어도 "눌린다" — 그리고 `Button` 말고는 아무것도 못 닿는다. `click` 이 대신이다 |
| `reset_game(clear_player_prefs: bool = False)` | 금지다. 이유는 아래 `### statement 는 일곱 가지다` 의 `reset_game` 항목에 있다 |

**`enter_text` 는 안 빠진다.** `target_id` 가 `int` 라는 것은 macro 를 막는 이유가 못 된다 —
`find(...)` 와 `selector(...)` 가 내는 것은 pulse 기록 하나이고, 그 기록이 `id` 와
`selector` 를 **둘 다** 든다 (`pulse.py:131`·`133`). macro 가 `enter_text(t, "hello")` 라고
적으면 runner 가 `t` 를 풀어 그 기록의 `id` 를 `target_id` 자리에 넣는다. **wire 도 tool 도
한 줄 안 고친다.** 기본 빌드에서도 서는 것은 `SceneScanner.TryGetTarget` 의 remarks 가
받는다 — `ObjectIds` 가 내보낸 id 를 기억하는 표를 **"비우지 않으므로 스캔이 멈춰도 조준은
풀리지 않는다"** 고 적고, 스캔이 멈추는 빌드로 `GAME_STATE` 가 꺼진 빌드를 이름 댄다
(ARTEL-513).

**`click_button` 과 가르는 선이 여기다.** 같은 방법이 `click_button(target_id)` 에도
기술적으로는 통한다 — runner 가 같은 식으로 id 를 넣을 수 있다. 그래도 빠지는 이유는 주소가
아니라 **deprecated** 라는 것이고, occlusion 을 안 보는 성질은 id 를 어떻게 넣든 그대로다.

**(C) 겨누는 함수 둘.**

| 함수 | 돌려주는 것 | 규칙 |
|---|---|---|
| `selector(<문자열 리터럴>)` | object 하나 | pulse 키(`씬/selector`)로 정확히 하나. 문자열은 `name[siblingIndex]` 를 `/` 로 이은 전체 경로다 |
| `find(label=..., name=..., under=...)` | object 하나 | pulse 에서 하나. **keyword 인자만** 받고 `label` · `name` 중 최소 하나가 있어야 한다. `under` 는 selector 의 prefix 로 범위를 좁힌다 |

`find(...)` 는 대입의 오른쪽에만 선다. 둘 이상 잡히면 `SELECTOR_AMBIGUOUS` 로 그 자리에서
멈춘다.

**(D) 읽는 함수 여덟 — `require` 의 왼쪽.**

| 함수 | 돌려주는 것 | 어느 memory 가 답하나 | 기본 빌드에서 |
|---|---|---|---|
| `scene()` | string | pulse. `SceneMemory.scene` 이 없으면 `PulseMemory.scene` | 선다 |
| `static(<문자열>)` | 임의 | `PulseMemory.statics`(`pulse.py:693`)의 `Type.member` | 선다 |
| `member(<target>, <문자열>)` | 임의 | 그 pulse 기록의 `members`(`pulse.py:757`)의 `Type.member` | 선다 |
| `text(<target>)` | string | 그 pulse 기록의 `text`(`pulse.py:148`) | 선다 |
| `actionable(<target>)` | bool | 그 pulse 기록의 `offers`(`pulse.py:734`) | 선다 |
| `exists(<target>)` | bool | `PulseMemory.held` 에 `live` 로 있나 | 선다 |
| `absent(<target>)` | bool | 같은 사전 | 선다 |
| `observable(<문자열>)` | 임의 | `SceneMemory.observables`(`scene.py:314`) | **안 선다 — `GAME_STATE` 전용이라 기본 빌드에 답할 자리가 없다** |

**`member()` 는 v1 에 넣는다.** 안 넣으면 기본 빌드에서 수를 읽을 자리가 아예 없다 —
`observable()` 은 안 서고 `static()` 은 래칭 플래그 열한 개라 `require(... == 1, ...)` 같은
조건을 적을 데가 남지 않는다. target 을 함께 받는 것은 pulse 가 인스턴스 값을 하나로 접기를
일부러 거부하기 때문이다. 근거는 아래 `#### member() 도 v1 에 넣는다` 에 있다.

**(E) 저자가 정의하는 함수 — 진입점 하나와 helper 여럿.** 한 source 안에 `def` 를 여럿
둔다. macro 이름과 같은 `def` 가 진입점이고 나머지가 helper 다.

| | 진입점 | helper | predicate |
|---|---|---|---|
| 이름 | macro 이름과 같아야 한다 | 아무 이름 | 아무 이름 |
| 누가 부르나 | `run_macro` | **그 source 안의 다른 `def` 만** | **그 source 안의 조건 자리만** — `require` 의 첫 인자, `if` 의 조건, `wait_until` 의 첫 인자 |
| 시그니처 | parameter 마다 타입, 반환은 `-> None` | 같다 | parameter 마다 타입, 반환은 **`-> bool`** |
| 본문 | statement 일곱 종류 | 같다 | **타입 적은 대입, `if`, `return` 셋뿐이다.** action 도 `require` 도 `wait_until` 도 못 쓴다 |
| 재귀 | 금지 | **금지. 저장 시점에 정적으로 거절한다** | 같다 |

helper 규칙은 아래 `### 저자가 helper def 를 둘 수 있다` 에 있다. **helper 를 펼치지 않는
것**과 그래서 payload 가 호출 자리를 싣는 것이 그 절의 핵심이다. predicate 규칙은 아래
`### predicate def 는 bool 을 돌려준다` 에 있다.

**(F) statement 일곱 형태.** action 또는 helper 호출, `require(<조건>, <remedy>)`, 타입 적은
대입, `if`, `flag(<메시지>)`, `ask_verdict(<기대>)`, `wait_until(<조건>, <초>, <remedy>)`. 아래
`### statement 는 일곱 가지다` 와 `### if 는 열고 for 와 while 은 안 연다` 와
`### wait_until 은 조건이 참이 될 때까지 기다린다` 와
`### 이름 하나에 find() 결과를 묶는다`, 그리고 `macro-errors-and-reporting` 의
`### require 는 인자 둘을 받는다 — 조건과 remedy` 와 `## flag 와 ask_verdict` 와 위
`### 타입은 선언한다 — parameter 와 반환과 대입 전부` 가 각각 정한다.

**`flag` 와 `ask_verdict` 는 게임에 아무것도 안 보내고 보고도 하지 않는다.** 앞엣것은 알리고
뒤엣것은 그 step 에 판정이 필요하다고 세운다. 둘의 차이와 `observed` 가 무엇인지는
`macro-errors-and-reporting` 의 `## flag 와 ask_verdict` 에 있다.

### statement 는 일곱 가지다

`def` 줄 아래의 statement 는 아래 일곱 중 하나다. predicate `def` 는 이 목록을 안 따르고 자기 목록을 따른다 (아래 `### predicate def 는 bool 을 돌려준다`). 어느 것인지 표시하는 문법이 따로 없다 —
**함수 이름과 대입 기호와 `if` 키워드가 그것을 정한다.**

- **tool 호출.** 이름은 `action_tools.py` 의 tool 이름 그대로이고, 위 (A) 의 열네 개다.
  인자는 그 tool 의 인자에서 `step` 과 `thought` 를 뺀 것이고, 뒤에서 그 둘이 왜 빠지는지
  적는다.
- **`require()` 호출.** 인자 둘 — 조건 하나와 remedy 문자열 하나다. `macro-errors-and-reporting` 의
  `### require 는 인자 둘을 받는다 — 조건과 remedy`.
- **대입.** `<이름>: <타입> = ...` 이고 오른쪽에 `find(...)` · `selector(...)` · 리터럴
  하나가 온다. **타입을 안 적으면 거절이다** (위 `### 타입은 선언한다`). 규칙은 아래
  `### 이름 하나에 find() 결과를 묶는다` 에 있다.
- **`if`.** 조건은 `require` 의 첫 인자와 같은 문법이고, 몸통은 이 일곱 종류를 그대로 받는다.
  `else` 와 `elif` 도 받는다. 규칙은 아래 `### if 는 열고 for 와 while 은 안 연다` 에 있다.
- **`flag()` 호출.** 인자 하나 — 비어 있지 않은 메시지 문자열 리터럴이다. 그냥 알린다.
  step 을 지목하지 않고 판정 의무도 세우지 않는다.
- **`ask_verdict()` 호출.** 인자 하나 — 비어 있지 않은 기대 문자열 리터럴이다. 이 macro 를
  부른 step 에 판정이 필요하다고 세운다. step 번호는 적지 않는다 — `run_macro` 가 받은
  `step` 을 물려받는다. 둘의 차이는
  `macro-errors-and-reporting` 의 `## flag 와 ask_verdict` 가 정한다.
- **`wait_until()` 호출.** 인자 셋 — 조건 하나, 최대 대기 시간(초) 숫자 리터럴 하나, remedy
  문자열 하나다. 조건이 참이 될 때까지 다음 statement 로 안 넘어간다. 규칙은 아래
  `### wait_until 은 조건이 참이 될 때까지 기다린다` 에 있다.

**게임에 나가는 것은 첫 번째뿐이다.** 나머지 여섯은 서버가 자기 `PulseMemory` 로 판정하거나
거둘 뿐이고, 그 차이가 `macro-errors-and-reporting` 의 `## 부분 실행을 반드시 보고한다` 의
`applied` 를 정한다. `if` 의 조건이 거짓이면 그 분기 안의 statement 는 같은 절의 `skipped`
로 간다.

목록에 없는 이름은 거절한다. **`action_tools.py` 의 tool 열여섯 개 중 둘이 빠졌다.**

- **`click_button`.** develop 의 docstring 첫 줄이 `DEPRECATED` 다. 빠지는 이유는 주소가
  아니라 그것이다 — 위 `### 이 언어의 함수 전체 목록` 의 (B) 에 적었다.
- **`reset_game`.** 첫 scene 을 다시 불러 계층을 통째로 갈아 치우므로 뒤따르는 statement 의
  selector 가 검증된 적 없는 계층에 던져지고, 묶어 둔 이름도 전부 죽는다. 그 docstring 이
  요구하는 "observe before you act again" 의 관측이 곧 model turn 이라, macro 안에서 부르면
  macro 가 줄이려던 것을 도로 늘린다. agent 가 직접 부르고 관측한 뒤에 macro 를 부른다.

### `if` 는 열고 `for` 와 `while` 은 안 연다

`ast.If` 를 허용 node 에 넣는다. **조건 문법은 `require` 의 첫 인자와 같다** — 위
`### 연산자 dispatch` 의 표를 찾는 평가기가 하나이고, 평가 시점의 연산자 거절도 한 곳에서
난다. 그래서 `and` · `or` · `not` 은 `if` 의 조건에서도 거절이다. 몸통은 위
`### statement 는 일곱 가지다` 의 일곱 종류를 그대로 받고 `else` 도 받는다.

**`elif` 는 막을 수 없다.** Python AST 가 `elif` 를 중첩된 `If` 로 표현하므로 `If` 를
허용하면 `elif` 가 따라온다. 거절하려면 `orelse` 가 `If` 하나인 경우를 따로 집어내야 하고,
그렇게 막아 봐야 저자가 `else` 안에 `if` 를 적으면 같은 tree 가 나온다. **허용으로 적는다.**

**`for` 와 `while` 은 계속 거절하고, 이유는 `if` 와 나란히 둔다.** `if` 는 statement 총수를
바꾸지 않는다 — 적힌 statement 를 세면 총수가 정해지고, 분기 안의 statement 도 센다. 반복은
몇 번 도는지 저장 시점에 모르므로 총수를 모르게 된다. 그러면 payload 의 `step N of M` 의
`M` 과 아래 `### 세는 상한 일곱` 의 statement 상한이 둘 다 뜻을 잃는다. 아래
`### 허용하는 node 와 거절하는 node` 의 거절 목록이 그 두 키워드를 들고 있고, 이유로 이
문단을 가리킨다.

**`if` 몸통 안에서 묶은 이름은 몸통 밖에서 못 쓴다.** 맨이름은 언제나 `def` 줄의 parameter
이거나 묶인 이름이라는 불변식(아래 `### 맨이름은 언제나 그 macro 안에서 묶인 이름이다`)을
지키려는 것이다. 분기가 안 간 채로 몸통 밖에서 그 이름을 쓰면 묶이지 않은 이름이 된다.
반대 방향 — 몸통 밖에서 묶은 이름을 몸통 안에서 쓰는 것 — 은 된다.

- **형제 분기가 같은 이름을 묶는 것은 된다.** `if` 몸통과 `else` 몸통은 겹치지 않고 어느
  쪽도 밖으로 안 나간다.
- **안쪽 몸통이 바깥에서 이미 묶인 이름을 다시 묶는 것은 거절이다.** 가리기(shadowing)이고,
  parameter 이름을 가리는 대입을 거절하는 것과 같은 이유다 — 한 `def` 안에서 맨이름 하나는
  한 가지만 뜻해야 한다. 규칙은 아래 `### 이름 하나에 find() 결과를 묶는다` 에 있다.

### `wait_until` 은 조건이 참이 될 때까지 기다린다

**`wait_until(<조건>, <최대 대기 시간(초)>, <remedy>)` 이고 인자 셋이 전부 필수다.** 조건이
참이면 다음 statement 로 넘어가고, 최대 대기 시간이 지나도 거짓이면 `WAIT_TIMEOUT` 으로
멈춘다 (`macro-errors-and-reporting` 의 `## 에러 코드 여덟 개`).

```python
def loading_done(loading: object, error_popup: object) -> bool:
    if absent(loading):
        return True
    if exists(error_popup):
        return True
    return False

def enter_dungeon() -> None:
    click(selector("Root[0]/Canvas[1]/EnterButton[0]"))
    loading: object = selector("Root[0]/Canvas[1]/Loading[0]")
    error_popup: object = selector("Root[0]/Canvas[1]/ErrorPopup[0]")
    wait_until(loading_done(loading, error_popup), 20.0,
               "로딩이 20초 안에 안 끝났다. 화면을 관측하고 로딩 화면이 멈췄으면 결함으로 적어라")
    require(absent(error_popup), "던전 입장에 실패했다. 팝업 글자를 읽고 결함으로 적어라")
```

**왜 필요한가.** `require` 는 직전 batch 뒤에 도착한 관측 하나로 판정한다. 로딩이나 연출처럼
게임이 몇 초 걸려 다음 상태로 가는 자리에서는 그 관측이 아직 이전 상태라, `require` 가 게임이
틀리지 않았는데도 실패한다. 지금은 그 자리에서 macro 를 끊고 agent 가 `observe_scene` 의
`wait_seconds` 로 기다린 뒤 다음 macro 를 불러야 하고, 그만큼 model turn 이 는다.

**인자 규칙.**

- **조건** 은 `require` 의 첫 인자와 같은 문법이다. 평가기도 하나다 (위
  `### if 는 열고 for 와 while 은 안 연다`). predicate 호출도 여기 선다 (아래
  `### predicate def 는 bool 을 돌려준다`).
- **최대 대기 시간** 은 숫자 리터럴이어야 한다. **parameter 나 묶은 이름은 안 받는다.**
  아래 `### 세는 상한 일곱` 의 대기 시간 합계를 저장 때 계산하려면 값이 텍스트에 적혀 있어야
  한다. 0 보다 크고 30 이하여야 한다. 생략하면 저장 때 거절한다 — 끝없이 기다리는
  `wait_until` 을 적을 문법을 두지 않는다.
- **remedy** 는 `require` 의 remedy 와 같은 규칙이다. 비어 있지 않은 문자열 리터럴이고,
  조건을 다시 쓰지 않고 시간이 다 됐을 때 agent 가 무엇을 할지를 적는다.
- keyword 인자는 안 받는다. `require` 와 같은 이유다 (`macro-errors-and-reporting` 의
  `#### 함정 — require(hp = 100) 은 Python 문법 오류가 아니다`).

**평가 시점.** 처음 한 번은 지금 `PulseMemory` 로 바로 평가한다 — 직전 action batch 뒤의
관측이 이미 도착해 있으므로 참이면 기다리지 않고 넘어간다. 거짓이면 **새 pulse 가 도착할
때마다** 다시 평가한다. 정해진 간격으로 polling 하지 않는다. pulse 가 안 오는 동안에는 평가할
새 값이 없기 때문이다. `app/qa/channel.py` 의 `look()` 이 pulse 도착을 기다리는
`_reading_arrived` 이벤트를 이미 쓰고 있고, `wait_until` 도 같은 이벤트를 기다린다. 새로 만들
대기 장치가 없다.

**`for` · `while` 을 막은 이유와 충돌하지 않는다.** 그 이유는 반복 횟수를 모르면 statement
총수를 모른다는 것이었다 (위 `### if 는 열고 for 와 while 은 안 연다`). `wait_until` 이
반복하는 것은 조건 평가뿐이고, 조건 안에는 action 이 들어갈 수 없다. 그래서

- 기다리는 동안 게임에 아무것도 안 보낸다. `applied` 에 오르지 않는다.
- 몇 번 평가하든 `wait_until` 은 statement 1개로 센다. `step N of M` 의 `M` 이 그대로다.
- 오래 걸릴 수 있는 것은 시간뿐이고, 시간은 최대 대기 시간이 막는다. 실행 경로마다 그 합계를
  저장 때 계산할 수 있다 (아래 `### 세는 상한 일곱`).

**게임 시간을 멈춘 채로 기다리면 저장 때 거절한다.** `pause_game_time` 을 부른 뒤
`resume_game_time` 전에 `wait_until` 이 오는 경로가 하나라도 있으면 거절이다. 게임 시간이
멈춘 동안에는 게임 상태가 안 바뀌므로 그 `wait_until` 은 최대 대기 시간을 다 쓰고 실패할
뿐이다. 판정은 아래 `### 눌러 둔 것이 macro 끝에 남으면 거절한다` 의 경로별 카운터를 그대로
쓴다.

**기다린 시간은 런 전체 deadline 에도 들어간다.** `app/agents/qa/runner.py:684` 의
`asyncio.wait_for` 가 런 하나의 시간을 자르고, macro 가 기다린 시간도 그 안에서 흐른다.

### predicate `def` 는 bool 을 돌려준다

**반환 타입이 `-> bool` 인 `def` 가 predicate 다.** 조건 자리 셋 — `require` 의 첫 인자,
`if` 의 조건, `wait_until` 의 첫 인자 — 에서 읽는 함수처럼 불린다. 위
`### wait_until 은 조건이 참이 될 때까지 기다린다` 의 `loading_done` 이 그 예다.

**본문에 쓸 수 있는 statement 는 셋뿐이다.**

- **타입 적은 대입.** 일반 `def` 와 같은 규칙이다 (아래 `### 이름 하나에 find() 결과를
  묶는다`).
- **`if`.** 조건 문법은 같고, 몸통도 이 세 종류만 받는다.
- **`return <조건>`.** 조건 문법은 `require` 의 첫 인자와 같다. `return True` 와
  `return False` 도 여기 든다 — bool 리터럴도 조건으로 받는다.

action, `require`, `flag`, `ask_verdict`, `wait_until`, helper 호출은 전부 거절한다.
`wait_until` 이 predicate 를 여러 번 평가하므로, 그 안에 게임에 나가는 것이나 무엇을 거두는
것이 있으면 평가할 때마다 그것이 반복된다. 판독만 하는 함수로 두어야 몇 번 평가해도 결과가
같다.

**모든 경로가 `return` 으로 끝나야 한다.** `return` 없이 끝나는 경로가 하나라도 있으면 저장 때
거절한다. 거절 문장은 그 경로의 마지막 statement 의 줄 번호를 댄다. `return` 뒤에 오는
statement 도 거절한다 — 실행되지 않는 줄이다. `-> None` 인 `def` 안의 `return` 은 계속
거절이다.

**predicate 가 predicate 를 부를 수 있다.** 조건 자리에 서는 것이므로 predicate 의 `if` 와
`return` 의 조건에서도 불린다. 재귀 금지와 호출 깊이 3 은 helper 와 같은 규칙으로 센다.

**`or` 가 필요한 조건은 이것으로 적는다.** `and` · `or` · `not` 연산자는 계속 거절이다 (아래
`### 허용하는 node 와 거절하는 node`). 대신 `if` 를 나란히 두고 각각 `return True` 하면 `or`
이고, 맨 끝의 `return False` 가 나머지다. 위 `loading_done` 이 "로딩이 끝났거나 에러 팝업이
떴다" 를 그렇게 적는다. 이렇게 적으면 어느 `if` 가 참이었는지가 줄 번호로 남는다 — 연산자 하나로
묶었으면 남지 않는 정보다.

**`find` 가 아무것도 못 찾으면 그 평가는 거짓이다. `wait_until` 안에서만 그렇다.**
`wait_until` 은 아직 안 나타난 것을 기다리는 자리이므로, 일반 대입처럼 `SELECTOR_NOT_FOUND`
로 멈추면 기다릴 수가 없다. 그래서 `wait_until` 이 평가하는 predicate 안의 `find` 가 아무것도
못 찾으면 그 평가를 거짓으로 보고 다음 pulse 를 기다린다. `require` 나 `if` 가 부른 predicate
안에서는 지금처럼 `SELECTOR_NOT_FOUND` 다. `SELECTOR_AMBIGUOUS` 와 `COMPARISON_REJECTED` 는
어디서든 그대로 멈춘다 — 기다려도 안 고쳐지는 정의 문제다.

**payload 는 predicate 안쪽을 싣는다.** `WAIT_TIMEOUT` 이나 `REQUIRE_FAILED` 의 `observed`
는 마지막 평가에서 predicate 가 읽은 값 전부이고, 어느 `return` 으로 끝났는지를 그 줄 번호로
든다 (`macro-errors-and-reporting` 의 `### wait_until 이 시간을 다 쓰면`).

### target 자리에 오는 것은 셋뿐이다

`parse_target`(`action_tools.py:25`)은 target 문자열을 세 형태로 받는다 — 화면 좌표
(`"640,360"`), instance id (`"#12345"`), selector. macro 는 앞의 둘을 금지한다. 문제는 그
금지를 어디서 거느냐다.

target 을 맨문자열로 두면 금지가 정규식 검사에 달린다. `click("640,360")` 은 문법으로는 멀쩡한
macro 이고, 파서가 문자열 안을 들여다보고 거절해야 한다. **`selector(...)` 로 감싸면 금지가
문법으로 성립한다.** 감싸지 않은 문자열은 target 자리에 올 수 없으므로 좌표와 id 를 적을
문법 자체가 없다.

그래서 target 자리에 오는 것은 셋뿐이다.

- `selector(<문자열 리터럴>)` — 그 문자열이 SDK 로 그대로 나가는 Unity hierarchy path 다.
- `def` 줄의 parameter.
- 아래 `find()` 절이 묶은 이름.

셋 다 맨문자열이 아니다. **좌표와 id 를 적을 문법이 어느 자리에도 없다.**

**리터럴 대입이 이 구멍을 다시 열지 않게 한 줄을 못박는다.** 대입의 오른쪽에 리터럴이
오게 되면서 `t: string = "640,360"` 을 적을 수 있게 됐지만, **문자열 리터럴을 묶은 이름은 target
자리에 못 선다.** target 자리에 서는 묶인 이름은 `find(...)` 나 `selector(...)` 를 묶은
것뿐이고, 그 둘은 object 를 든다. 그래서 위의 셋은 그대로 셋이다 — 리터럴을 묶은 이름을
target 자리에 쓰면 저장 때 거절한다 (아래 `### 이름 하나에 find() 결과를 묶는다`).

`drag` 는 인자 둘이 서로 독립이다. develop 의 시그니처는
`drag(step, from_target, to_target, thought, button=0)` 이고 그 docstring 이 "Each end is
independently one of the three forms" 라고 적어 뒀다. macro 에서는 **양끝이 각각 독립으로
위 셋 중 하나다** — `macro-errors-and-reporting` 의 `## require 두 종류` 예시의
`drag(a, selector("Root[0]/Canvas[1]/CardSlot(Clone)[0]"))` 이
묶인 이름과 `selector(...)` 를 한 자리씩 쓴 것이고, 양끝을 둘 다 묶인 이름으로 두어도 된다.

**parameter 는 문법으로 못 막는다.** `click(target)` 의 `target` 에 `run_macro` 가 `"640,360"`
을 묶으면 좌표가 그대로 나간다. 그러니 `run_macro` 는 target 자리에 묶이는 인자를 호출
시점에 검사하고, 좌표나 `#` id 면 게임에 아무것도 보내기 전에 `ACTION_REJECTED` 로 거절해야
한다. 문법이 막는 것은 **저장된 정의 안의** 좌표와 id 이고, 호출 인자는 별도 검사다.

`find` 의 `under=` 도 target 자리가 아니다. 겨누는 것이 아니라 범위를 좁히는 것이라, 받는
것은 `selector(<문자열>)` 과 selector kind parameter 둘뿐이고 묶인 이름은 안 받는다. 이유는
`macro-targets-and-memory` 의 `### under= 를 v1 에 넣는다` 에 있다.

`observable(...)` 은 target 자리가 아니다. 인자가 selector 가 아니라 scene view 의
`observables` 가 찍는 key 이름이라 맨문자열로 적는다 — `observable("cards_in_hand")` 이고
`observable(selector("cards_in_hand"))` 이 아니다.

**parameter 하나가 target 인지 아닌지는 쓰인 자리가 정한다.** `macro-errors-and-reporting` 의 `## require 두 종류` 예시의
`target` 은 target
자리에 쓰였으니 selector 문자열이어야 하고, `card_a` 는 `find(label=...)` 자리에 쓰였으니
label 문자열이다. 같은 `def` 줄에 둘이 나란히 있어도 검사는 자리마다 다르다.

### 타입은 선언한다 — parameter 와 반환과 대입 전부

**`def` 의 모든 parameter 에, 반환에, 그리고 모든 대입에 타입을 적는다. 안 적으면 저장 때
거절한다.** 앞선 판은 쓰인 자리를 보고 kind 를 추론했고, 비교의 오른쪽 하나를 못 정해 기본값
규칙을 따로 뒀다. 그 추론을 버린다.

```python
def attack_with_combined_card(card_a: string, card_b: string, target: object) -> None:
    slot0: object = selector("Root[0]/Canvas[1]/CardSlot(Clone)[0]")
    a: object = find(label=card_a)
```

대입은 Python 의 annotated assignment 를 그대로 쓴다 — `ast.AnnAssign` 이고, 허용 node 표가
`ast.Assign` 자리에 그것을 받는다. 반환 타입은 `None` 과 `bool` 둘뿐이다. `-> None` 이
진입점과 helper 이고, `-> bool` 이 predicate 다 (아래 `### 저자가 helper def 를 둘 수 있다` 와
`### predicate def 는 bool 을 돌려준다`).

**타입 이름은 일곱이다** — `int` · `float` · `string` · `bool` · `vector2` · `vector3` ·
`object`. 아래 `### 연산자 dispatch` 의 표가 쓰는 이름과 같은 이름이다. 다만 **`vector2` 와
`vector3` 는 v1 에서 선언 자리에 못 선다** — vector 를 만들 문법도 비교할 연산자도 없으므로
선언해 봐야 그 이름으로 할 수 있는 일이 없다. 선언에 쓸 수 있는 것은 나머지 다섯이고, 두
이름은 게임에서 **도착한 값의 모양** 이름으로만 산다.

**`object` 는 game object 하나를 가리키는 값이다** — pulse 기록 하나이고 `id` · `selector` ·
`text` · `offers` 를 든다. `find(...)` 와 `selector(...)` 가 내는 것이 그것이고, target 자리에
서는 것이 그것이다. `run_macro` 가 `object` parameter 에 넘기는 값은 selector 문자열이고,
runner 가 그것을 실행 전에 풀어 기록 하나로 만든다.

#### 선언한 타입과 도착한 값의 모양은 다른 층이다

둘을 헷갈리면 표가 두 가지 일을 하는 것처럼 보인다. 갈라 둔다.

| | 선언한 타입 | 도착한 값의 모양 |
|---|---|---|
| 어디 적혀 있나 | macro 텍스트의 annotation | 아무 데도. 판독이 실어 온 값을 보고 안다 |
| 무엇에 쓰나 | `run_macro` 의 인자 검사, 그리고 **저장 시점 연산자 검사** | **평가 시점 연산자 dispatch** |
| `int` 와 `float` | 가른다 | **안 가른다. 둘 다 `number` 다** |
| 언제 판정하나 | 저장 때와 호출 때 | 그 statement 가 도는 때 |

**`int` 와 `float` 를 선언에서는 가르고 연산자에서는 안 가르는 이유.** wire 가 모든 수를 네
자리로 반올림해 보내므로 `3.0` 이 `3` 으로 도착하고, **도착한 값으로는 둘을 못 가른다** (아래
`### 연산자 dispatch`). 가르는 것이 뜻을 갖는 자리는 호출 인자 검사 하나다 — `button: int` 에
`0.5` 를 넘긴 호출은 거절해야 하고, 그것은 wire 를 안 거친 값이라 가를 수 있다.

#### 선언이 저장 시점 검사를 크게 늘린다

**앞선 판이 "파서는 값을 영영 못 본다" 로 미뤄 둔 것의 대부분이 저장 때로 당겨진다.**
`card_a: string` 이 적혀 있으면 `require(card_a > 5, "...")` 를 평가까지 기다릴 이유가 없다 —
왼쪽이 string 이고 string 에 `>` 가 없으므로 그 자리에서 `MACRO_NODE_REJECTED` 다.

| 무엇 | 선언 전 | 선언 후 |
|---|---|---|
| parameter 가 낀 비교 | 평가 때 | **저장 때** |
| 묶은 이름이 낀 비교 | 평가 때 | **저장 때** — 대입에 타입이 적혀 있다 |
| `scene()` · `text()` · `actionable()` · `exists()` · `absent()` 가 낀 비교 | 저장 때 (읽기가 내는 모양이 고정이다) | 그대로 |
| tool 인자의 종류 | 자리로 추론 | **선언과 대조** |
| `static()` · `observable()` 가 낀 비교 | 평가 때 | **그대로 평가 때** |

**런타임까지 모르는 것은 `static()` 과 `observable()` 둘뿐이다.** 그 둘이 내는 값의 모양은
게임이 정하고 문법이 적은 적이 없다. `member()` 도 같은 처지로 보일 수 있지만 그것도 그
둘과 같은 자리이므로 셋으로 읽어도 틀리지 않는다 — 셋 다 판독이 실어 온 값을 그대로 낸다.
**그래서 `COMPARISON_REJECTED` 는 사실상 이 읽기들에만 남는다.** 나머지는 저장 때 걸린다.

#### `let` 같은 키워드는 안 쓴다

이유가 둘이다. 하나, `let` 은 Python 문법이 아니라 `ast.parse` 가 `SyntaxError` 를 내고, 그
순간 파서를 공짜로 얻은 이득이 없어진다. 둘, **재대입을 금지했으므로 모든 대입이 선언이다** —
`let` 이 가를 구분 자체가 없다. 나중에 다시 물을 자리라 적어 둔다.

### 저자가 helper `def` 를 둘 수 있다

**한 source 안에 `def` 를 여럿 둔다.** macro 이름과 같은 `def` 가 **진입점**이고 — `write_macro`
가 이미 `name` 과 `def` 이름이 맞기를 요구한다 — 나머지는 **helper** 다.

```python
def play_card(card: string, slot: object) -> None:
    c: object = find(label=card)
    drag(c, slot)

def attack_with_combined_card(card_a: string, card_b: string, target: object) -> None:
    require(scene() == "Battle", "전투 화면에서만 쓴다. 전투로 먼저 들어가라")
    play_card(card_a, selector("Root[0]/Canvas[1]/CardSlot(Clone)[0]"))
    play_card(card_b, selector("Root[0]/Canvas[1]/CardSlot(Clone)[1]"))
```

- **helper 는 그 source 안에서만 부를 수 있다.** 다른 macro 가 이름으로 부를 수 없고, 저장된
  macro 목록에도 안 올라간다.
- **재귀는 거절한다.** 자기 호출도 상호 재귀도 **저장 시점에** 거절한다 — 호출 그래프가 그
  텍스트 안에 전부 있으므로 순환을 그 자리에서 찾을 수 있다.
- 이름 규칙과 타입 규칙은 진입점과 같다. parameter 와 반환에 타입을 적고, 묶는 이름은 그
  `def` 안에서만 산다.

**이것은 `macro 가 macro 를 못 부른다` 와 다른 얘기다.** 두 문장이 모순으로 읽히기 쉬우니
차이를 적어 둔다.

| | 한 source 안의 helper | 저장된 macro 끼리 |
|---|---|---|
| 호출 그래프가 어디 있나 | **그 텍스트 안에 전부** | 저장소 전체에 흩어져 있다 |
| 순환을 언제 찾나 | 저장 때. 정적으로 끝난다 | 런타임에 풀어야 한다 |
| 정의가 바뀌면 | 같은 텍스트를 다시 등록하는 일이다 | 부르는 쪽 모르게 바뀐다 |

앞엣것은 lexical 이라 저장 때 끝나고, 뒤엣것은 그렇지 않다. **그래서 helper 는 열고 macro 간
호출은 막는다.** `store-and-replay-action-sequences-as-macros` 의 `## 첫 버전 범위 — tool 다섯 개` 의 금지는 뒤엣것에 대한 것이다.

#### 펼치지 않는다 — `step N of M` 이 저자가 쓴 줄과 맞아야 한다

helper 를 저장 시점에 펼쳐 평평하게 둘 수도 있다. **안 한다.** helper 를 세 번 부르면 펼친
결과에 복사본이 셋이고, 그 순간 payload 의 `step N of M` 이 저자가 쓴 줄과 대응을 잃는다.
이 문서의 에러 보고 설계 전체가 **"실패를 저자가 쓴 source 로 되짚을 수 있다"** 에 기대고
있으므로 그 대응을 깨면 안 된다.

대신 **payload 가 호출 자리를 싣는다.**

```
  at:       play_card 의 step 2 of 2 — drag(c, slot)
            attack_with_combined_card 의 step 3 에서 불림
```

번호는 `def` 마다 1부터 센다. 위 예시의 `step 2 of 2` 는 `play_card` 안의 번호이고, 그것을
부른 줄이 진입점의 3번이다. 사람이 읽는 모양과 JSON 모양 둘 다 이 줄을 든다 (`macro-errors-and-reporting` 의 `## 부분 실행을 반드시 보고한다`).


#### 기본값은 그대로 리터럴 하나다

`def` 줄의 `=` 는 `int` · `float` · `string` · `bool` 에만 붙는다. **`object` 에는 기본값을
안 받는다** — 어느 호출도 이름 댄 적 없는 주소이고, 그것이 안 잡혔을 때 에러가 agent 가 쓴
적 없는 argument 를 가리킨다.

### 맨이름은 언제나 그 macro 안에서 묶인 이름이다

이것이 이 표기법의 불변식이다. **맨이름은 `def` 줄의 parameter 이거나 아래 `find()` 절의
대입이 묶은 이름이고, 그 둘 말고 맨이름이 뜻하는 것은 없다.** 어느 쪽이든 이름이 어디서
왔는지가 같은 텍스트 안에 적혀 있고, **맨이름이 selector 문자열을 뜻하는 경우는 없다.**
그래서 이 표기법이 이름을 가진 호출은 아홉 개다.

| 호출 | 돌려주는 것 | 어디서 읽나 | 기본 빌드에서 |
|---|---|---|---|
| `selector(<문자열>)` | target 하나 | 저장된 문자열 그대로. SDK 가 푼다 | 선다 |
| `scene()` | 지금 scene 이름 | `SceneMemory.scene`, 없으면 `PulseMemory.scene` | 선다 |
| `actionable(<target>)` | 지금 누를 수 있나 | 그 pulse 기록의 `offers`(`pulse.py:734`) | 선다 |
| `text(<target>)` | 지금 화면에 띄우고 있는 글자 | 그 pulse 기록의 `text`(`pulse.py:148`) | 선다 |
| `exists(<target>)` | 화면에 있나 | `PulseMemory.held` 에 `live` 로 있나 | 선다 |
| `absent(<target>)` | 화면에 없나 | 같은 사전 | 선다 |
| `static(<문자열>)` | static 하나의 값 | `PulseMemory.statics`(`pulse.py:693`)의 `Type.member` | 선다 |
| `member(<target>, <문자열>)` | 그 객체의 member 하나의 값 | 그 pulse 기록의 `members`(`pulse.py:757`)의 `Type.member` | 선다 |
| `observable(<문자열>)` | observable 하나의 값 | `SceneMemory.observables`(`scene.py:314`) | **안 선다** |

**`require()` 의 왼쪽에 설 수 있는 것은 `selector(...)` 를 뺀 여덟이다.** `selector(...)` 는
값을 읽는 것이 아니라 target 하나를 만드는 것이라 조건의 왼쪽에 혼자 못 선다.

#### `observable()` 은 `GAME_STATE` 를 켠 빌드 전용이다

**빼지 않고 남기되, 기본 빌드에서 안 된다고 못박는다.** 읽는 값이
`SceneMemory.observables` 이고 그것을 채우는 것은 `GAME_STATE` frame 하나뿐이다 —
`GameState.observables`(`envelope.py:314`)를 `scene.py:314` 가 받아 넣는다. 그래서
`SendsGameState` 가 꺼진 기본 빌드에서 그 사전은 끝까지 비어 있고, **ARTEL-400 뒤에는 영구히
없다.** `scene.py:234` 의 주석이 그것을 그대로 적는다 — "지금은 두 출처가 공존하고 판독이
우선인데 … `states` 를 걷어내 하나로 만드는 것은 ARTEL-400 이다."

**`find(label=)` 을 `SceneMemory` 에 걸어 뒀던 것과 정확히 같은 실수다.** 같은 원인이 세
번째이므로 여기서는 물러나는 규칙을 만들지 않고 자리를 나눈다.

- `observable()` 은 남는다. 게임이 QA 를 위해 **이름 붙여 내놓은** 값이고, 그것을 pulse 가
  대신 낼 길이 없다 — 게임이 static 이나 watch list 로 내놓지 않은 값은 판독에도 없다.
- **대신 기본 빌드용 macro 는 `static()` 과 `member()` 로 적는다.** 아래 두 항목이 그
  자리다.
- `observable()` 을 쓴 macro 를 기본 빌드에서 부르면 읽을 자리가 없으므로
  `ACTION_REJECTED` 다 (`macro-targets-and-memory` 의 `### 읽을 자리가 아예 없을 때 — 하나 남는다` 와 같은 기준이다).
  **`REQUIRE_FAILED` 가 아니다** — 게임이 다르게 동작한 것이 아니라 채널이 안 온 것이다.

#### `static()` 을 되살린다 — 래칭 플래그가 macro 를 조용히 망친다

`static(<문자열>)` 은 `PulseMemory.statics` 에서 `Type.member` 하나를 읽는다. 이름의 모양은
그 절이 찍는 것과 같다 — `pulse.py:697` 이 `declaring` 의 마지막 마디와 `member` 를 점으로
잇는다.

이 읽기가 v1 에 드는 이유는 `pulse.py:681~692` 의 주석이 든 실제 사건이다. **statics 절은
창을 안 타고 매번 전부 그리는데, 그렇게 만든 이유가 그 사건이다.**

> 샘플 게임의 `InteractionLock.IsLocked` 가 그렇다: 대화창이 떠 있는 동안 카드 드래그가
> 통째로 취소되는데, 그 사실이 잠기는 순간 한 번만 보이고 사라졌다. 다음 턴의 에이전트는
> 잠긴 줄 모르고 끌었고, 카드가 튕기는 것을 좌표가 틀린 것으로 읽었다(ARTEL-573).

**`require(static("InteractionLock.IsLocked") == False, "대화창을 닫고 다시 불러라")` 가
정확히 이 실패를 막는 statement 다.** 그리고 이것이 `require` 가 왜 필요한지를 `DontRequireReceiver` 논거보다 더
잘 보여 준다 — 저기서는 action 결과가 아무것도 증명하지 않는다는 것이었고, 여기서는
**action 이 통째로 취소됐는데 그 사실이 화면 어디에도 없다.** macro 는 model 을 안 깨우고
statement 를 잇달아 보내므로, 이런 값을 안 물으면 취소된 네 statement 를 성공으로 보고한다.

static 으로 뽑히는 값이 대체로 래칭이라는 것도 그 주석이 적는다 — 한 번 켜지면 꺼질 때까지
유지되고 그 사이 내내 무엇을 할 수 있는지를 결정한다. **macro 의 precondition 에 딱 맞는
성질이다.** 값이 열한 개라는 실측도 같은 자리에 있다.

#### `member()` 도 v1 에 넣는다

`member(<target>, "<Type>.<member>")` 은 그 pulse 기록의 `members` 에서 값 하나를 읽는다.
이름의 모양은 판독 블록이 찍는 것과 같다(`pulse.py:757`).

**이것이 없으면 기본 빌드에서 수를 읽을 자리가 아예 없다.** `observable()` 은 안 서고
`static()` 은 래칭 플래그 열한 개라, `require(... == 1)` 같은 조건을 적을 데가 남지 않는다.

`member()` 가 target 을 받는 이유는 **pulse 가 인스턴스 값을 하나로 접기를 일부러 거부하기
때문이다.** `LiveState` 의 remarks 가 그것을 적는다 — 만들어진 적 다섯은 `hp` 에 대한 답
다섯이고, 그것들을 하나로 접는 것은 두 객체에 대한 조건을 한 문장에 쓰는 것과 같은 실수다.
그래서 이름만으로는 인스턴스 값을 못 가리키고, **어느 객체의 값인지를 target 으로 함께
적어야 한다.**

이 둘을 넣어도 attribute access 는 그대로 거절이다. 예전 `selector(S).<Component>.<member>`
가 `member(selector(S), "<Component>.<member>")` 로 바뀌었을 뿐 자리 규칙은 안 깨진다.

`text()` 가 여기 드는 이유는 **"라벨이 무엇으로 바뀌었나" 를 못 묻게 되는 것이 QA 에서 너무
비싸기 때문이다.** 읽는 값은 `find(label=...)` 이 맞추는 그 값과 같고 화면의 글자 절이 그리는
그 값과도 같다 — 셋 다 `PulseObject.text` 하나를 본다. 앞선 판이 적어 둔 label 과 placeholder
의 접힘은 여기서 없어진다.

`text()` · `scene()` · `observable()` · `static()` · `member()` 는 boolean 이 아니므로 비교를
반드시 달아야 한다. 비교 없이 설 수 있는 것은 boolean 을 내는 `actionable` · `exists` ·
`absent` 셋이다. `static()` 과 `member()` 가 boolean 값을 들고 있어도 마찬가지다 — 그 값이
무슨 종류인지는 게임이 정하지 이 문법이 정하지 않으므로, `== False` 를 적게 한다.

`scene` 을 `scene()` 로 적는 것이 이 불변식 때문이다. 맨이름 `scene` 은 그 macro 가 묶은
이름이어야 하므로 scene 이름을 읽는 데 못 쓴다. 같은 이유로 `not` 이 없는 자리를
`absent()` 가 메운다.

예전 `{card_a}` 치환 문법은 없어진다. parameter 는 중괄호 없이 그 자리에 그냥 적는다 —
`click(target)` 이고 `click("{target}")` 이 아니다.

### 연산자 dispatch — 값의 모양이 되는 연산자를 정한다

`require` 의 조건은 `<읽기> <연산자> <피연산자>` 하나다. **`if` 의 조건도 같은 문법이고 같은
표를 찾는다** (위 `### if 는 열고 for 와 while 은 안 연다`) — 평가기가 하나다. 어느 연산자가
되는지는 **읽힌 값의 모양**이 정하고, 그 대응을 표 하나로 둔다. **표로 두는 이유는 새 타입이 들어오면 행이 하나
느는 일이 되고 빠뜨린 칸이 눈에 보이기 때문이다** — 조건문으로 흩어 놓으면 어느 조합을 안
정했는지 읽어서는 알 수 없다.

| 값의 모양 | `==` `!=` | `>` `>=` `<` `<=` |
|---|---|---|
| number — int 와 float 를 **안 가린다** | 됨 | 됨 |
| string | 됨 | **거절** |
| bool | 됨 | **거절** |
| object — pulse 기록 하나 | 됨 — **pulse 키가 같으면 같다** | **거절** |
| vector2 · vector3 | **거절** | **거절** |
| 그 밖의 shape — 참조 · sprite · animator state · `{"unread": "not-a-number"}` | **거절** | **거절** |

**number 가 한 행인 것은 선택이 아니다 — 값만 보고 int 와 float 를 가릴 수가 없다.**
`LiveState.cs:1533` 의 `Number` 가 모든 수를 이렇게 찍는다.

```csharp
text.Append("\"value\":").Append(Math.Round(value, Decimals).ToString("0.####", Invariant));
```

`Decimals` 는 4 다(`LiveState.cs:1531`). `0.####` 는 쓸데없는 0 을 떼므로 **float `3.0` 이
`3` 으로 나가고 JSON 에서 int 로 읽힌다.** 두 행으로 나눈 표는 평가 시점에 집행할 수가
없다 — 집행하려면 도착한 값이 원래 어느 쪽이었는지를 알아야 하는데 그 정보가 wire 에 없다.

**같은 반올림이 `==` 를 거절할 이유도 없앤다.** `Decimals` 의 remarks 가 그것을 적는다 —
"변화 게이트가 이 문서를 해싱하므로, 날것의 float 은 숨 쉬는 idle 애니메이션을 상태 변화로
만들고 페이로드가 매 틱 나간다. 반올림이 게이트를 쓸 수 있게 만드는 것이고, **네 자리는
근거가 하는 어떤 비교보다도 곱다.**" 소수 마지막 자리가 영원히 달라지는 값은 agent-server 에
닿기 전에 이미 네 자리로 잘려 있다. 그래서 `require(member(t, "Hp.Value") == 3, "...")` 는
쓸 수 있는 조건이다.

**권고가 하나 붙는다. 끊임없이 변하는 연속값 — 위치, 타이머 — 을 `==` 로 묻는 것은 네 자리
반올림 뒤에도 위태롭다.** 네 자리 안쪽에서 흔들리는 값은 그대로 흔들린다. 그럴 때의 관용구는
`<` 와 `>` 를 `require` 둘로 쓰는 것이고, `and` 가 없는 자리를 `require` 둘로 메우는 것과
같은 방식이다. **거절이 아니라 권고다.** 문법은 안 막는다.

정황이 하나 더 있다. SDK 에 `Restless`
(`artel-sdk/Packages/kr.artel.sdk/Runtime/Affordance/Scan/Live/Restless.cs`)가 있고, 그
remarks 가 위치 값이 **"있던 자리에 정확히 그대로 앉아 있으면서 마지막 소수 자리가 영원히
달라진다"** 고 적는다. 다만 **그 클래스는 비교를 위한 것이 아니다** — 판독의 변화 게이트가
무의미해지지 않게 값이 마지막으로 멈춘 자리에 격자를 고정하는 양자화기이고, 격자는 기본
0.001, 화면 픽셀은 1 이다. `==` 가 서는 직접 근거는 위의 네 자리 반올림이고, `Restless` 는
연속값을 `==` 로 묻지 말라는 **권고 쪽의 보조 정황**이다.

**string 의 `>` 를 거절하는 이유.** 사전순이라 `"10" < "9"` 가 참이다. QA 조건으로 쓸 자리가
없고, 쓰면 읽는 사람이 수 비교로 읽는다. 대안은 수를 수로 읽는 것이다 — `member()` 나
`static()` 이 내는 값을 쓴다. **bool 의 `>` 는 뜻이 없다.** 대안은 `== True` 와 `== False`
다.

**object 의 같음은 pulse 키다.** `find` 와 `selector(...)` 가 내는 값은 pulse 기록 하나이고,
그 기록을 가르는 기준은 `PulseMemory` 자신이 이미 정해 뒀다 — `PulseObject.key`
(`pulse.py:174`)가 `씬/selector` 이고 `selector` 가 없으면 `path` 로 떨어진다. **비교도 그
키를 따른다. 같은 키면 같은 객체다.** `id` 로 안 가르는 이유는 `PulseObject.id` 가
`int | None` 이라 **없는 기록이 있기 때문이고**, 그러면 그 경우에 규칙이 없다. memory 의
정체성 기준과 비교의 기준이 다르면 둘이 어긋나는 자리가 반드시 생긴다.

**object 에 속성 접근은 안 연다.** `t.id` 도 `t.selector` 도 없다. 값을 읽는 것은 함수가
한다 — `text(t)` · `actionable(t)` · `exists(t)` · `member(t, "Type.member")` 다. 아래
`### 허용하는 node 와 거절하는 node` 의 attribute access 거절이 그대로 서고, object 가 타입이
된다고 해서 거기 예외가 생기지 않는다.

**vector 의 비교를 전부 거절하는 이유.** `>` 는 성분별인지 크기인지 추측이고, macro 를 쓰는
쪽이 그 둘을 가릴 수 없다. `==` 는 wire 모양이
`"world":{"x":...,"y":...,"z":...}`(`LiveState.cs:933`)인 복합값이라 "같다" 가 세 성분
전부를 뜻하는지가 적힌 적이 없고, 성분 셋이 각각 위의 number 권고를 그대로 진다. **v1 에서
vector 비교는 전부 거절한다.** 쓸모 있는 vector 질문은 근접 하나뿐이고 — `near(a, b, 거리)`
— 그것을 v1 에서 안 연다. `store-and-replay-action-sequences-as-macros` 의 열려 있는 질문에 적었다.

**`{"unread": "not-a-number"}` 가 "그 밖의 shape" 행에 든다.** `Number` 가 `NaN` 과
`Infinity` 를 수로 안 보내고 그 모양으로 바꿔 보낸다 — 그 자리의 주석이 "숫자가 아니고 JSON
으로 쓸 수도 없다. 0 으로 바꾸지 않고 그렇다고 말한다" 고 적는다. 그 값과의 비교는 **조용히
거짓이 되면 안 되고 거절해야 한다.** 거짓으로 보면 게임이 멀쩡한데 `REQUIRE_FAILED` 가
나가고, 그것이 `macro-errors-and-reporting` 의 에러 코드 표가 막으려던 바로 그 실패다.

#### 언제 검사하나 — 선언한 것은 저장 때, 게임이 내는 값은 평가 때

위 `### 타입은 선언한다` 가 이 질문의 절반을 이미 답했다. **저자가 타입을 적으므로 표의
대부분이 저장 시점에 집행된다** — parameter 가 낀 비교도, 묶은 이름이 낀 비교도, 리터럴이
한쪽에 있는 비교도 전부 저장 때 걸린다. 거기서 나가는 것은 `MACRO_NODE_REJECTED` 이고,
거절 문장이 그 모양에 되는 연산자를 이름 댄다.

**남는 것은 게임이 내는 값 하나다.** `static()` · `observable()` · `member()` 가 내는 값의
모양은 게임이 정하고 문법이 적은 적이 없다. `PulseMember.value` 가 일부러 `Any` 이고 그
docstring 이 이유를 적는다(`pulse.py:74~82`).

> `value` is deliberately `Any`. The channel carries scalars as well as the shapes the SDK
> uses for a reference (`{"path": ..., "world": ...}`), a sprite, an animator state, a
> label, or a bare count — and a reader that narrowed this to a scalar would drop the half
> that names what a step is pointing at.

| 언제 | 무엇으로 아나 | 무엇이 나가나 |
|---|---|---|
| **저장 때** | annotation 과 읽기의 고정된 반환 모양으로 안다. `require(card_a > 5, "...")` 는 `card_a: string` 이 적혀 있으므로 그 자리에서 걸리고, `require(text(t) > "abc", "...")` 는 `text()` 가 string 을 내므로 걸린다 | `MACRO_NODE_REJECTED`. 거절 문장이 그 모양에 되는 연산자를 이름 댄다 |
| **평가 때** | `static()` · `observable()` · `member()` 가 낀 비교만. 도착한 값을 보고 표를 찾는다 | `COMPARISON_REJECTED` — 아래 |

**평가 때 나가는 것은 `REQUIRE_FAILED` 가 아니다.** 게임이 틀린 것이 아니라 macro 가 못 묻는
것을 물은 것이다. `macro-errors-and-reporting` 의 다른 여섯 중 맞는 것이 없다 — `REQUIRE_FAILED` 는 게임 결함을 가리키고,
`ACTION_REJECTED` 는 "환경 문제. 게임도 macro 도 아님" 이라 뜻이 반대이고,
`SELECTOR_AMBIGUOUS` 는 macro 정의 문제라는 점은 맞지만 이름이 selector 를 가리킨다. 그래서
**일곱 번째 코드 `COMPARISON_REJECTED` 를 둔다.**

- 뜻: 도착한 값의 모양에 그 연산자가 없다.
- agent 가 할 일: **step 을 실패로 적지 않는다.** macro 정의를 고친다. payload 의
  `observed.type` 이 실제로 온 모양을 적고, 문장이 그 모양에 되는 연산자를 이름 댄다.
- 무리: `SELECTOR_AMBIGUOUS` · `STALE_BINDING` · `ACTION_REJECTED` 와 같은 쪽이다. 게임
  얘기가 아니다.
- **`macro-errors-and-reporting` 의 다른 여섯의 이름은 하나도 안 바뀌고 `MACRO_` 접두를 안 붙이는 규칙도 그대로다.** 이것은
  그 여섯에 접두를 붙인 이름이 아니라 일곱 번째 이름이다.

### 이름 하나에 `find()` 결과를 묶는다

경로 selector 로는 손패 카드를 못 가리킨다 (`macro-targets-and-memory` 의 `### selector 가 조용히 다른 것을 가리키는
한 경우`). 그 자리를 메우는 것이 `find()` 이고, 그 결과를 이름에 묶는 **대입 statement
하나**가 문법에 든다.

```python
a: object = find(label=card_a)
```

대입은 `<이름>: <타입> = <오른쪽>` 이고 타입은 반드시 적는다 (위 `### 타입은 선언한다`).
오른쪽에 올 수 있는 것은 넷이다.

| 오른쪽 | 적는 타입 | 이름이 갖는 것 |
|---|---|
| `find(...)` | `object` | pulse 기록 하나. `id` 와 `selector` 를 다 든다 |
| `selector(...)` | `object` | 적어 둔 주소에 붙인 이름이다. 아래 |
| int · float · string · bool 리터럴 | 그 리터럴의 타입 | 그 값. **target 자리에는 못 선다** |
| reader 호출 하나 | `int` · `float` · `string` · `bool` | 그 줄이 돈 순간에 읽은 값. 다시 읽지 않는다. **target 자리에는 못 선다** |

reader 여덟 밖의 호출도, 산술도, 중첩도 안 된다. **리터럴에 bind 한 이름을 target 자리에 쓰면 저장 때
거절한다** — 그러지 않으면 `t: string = "640,360"` 이 좌표를 target 자리로 들여보내고, 위
`### target 자리에 오는 것은 셋뿐이다` 가 문법으로 막아 둔 것이 도로 열린다.

**reader 호출을 오른쪽에 받는 이유는 조작 전후의 비교다.** "눌렀더니 숫자가 움직였나" 가
QA 가 가장 많이 하는 확인인데, 처음 판은 오른쪽을 `find` · `selector` · 리터럴 셋으로 두어
이것을 쓸 수 없었다. 그 셋을 고른 이유는 손패 카드를 가리킬 이름과 긴 selector 의 반복을
줄일 이름이었고, 읽은 값을 bind 하는 것에 반대한 적은 없다 — 논의되지 않았을 뿐이다. 그래서
예시 macro 가 `starting_health: float = 100` 처럼 기준값을 리터럴로 적어야 했고, 그 macro 는
체력이 100 인 적에게만 맞았다.

```python
before: float = member(enemy, "Enemy.Hp")
click(enemy)
require(member(enemy, "Enemy.Hp") < before, "공격이 체력을 안 깎았다")
```

**이 언어에서 late binding 이 아닌 것은 이것 하나다.** selector 는 action 이 도는 프레임에
풀리고, `find` 는 bind 한 순간의 기록을 들되 쓸 때마다 살아 있는지 다시 본다(`STALE_BINDING`).
읽은 값은 다시 보지 않는다 — 다시 읽으면 위 비교가 성립하지 않는다. 늙은 숫자는 죽은 handle 이
아니라 그냥 옛 숫자이므로 새 에러 코드도 필요 없다.

`object` 로 선언하면 거절한다. 도착 모양이 정해진 reader(`text` · `scene` 은 문자열,
`actionable` · `exists` · `absent` 는 bool)는 저장 때 선언과 맞추고, 게임이 모양을 정하는
`member` · `observable` · `static` 은 실행 때 맞춰 다르면 **그 대입 statement 에서**
`COMPARISON_REJECTED` 로 멈춘다. `find` 대입이 그 자리에서 `SELECTOR_NOT_FOUND` 를 내는 것과
같은 자리다.

이름을 bind 하는 규칙은 넷이고 그대로다.

- 이름은 **한 번만 묶인다.** 재대입은 거절한다. 세는 범위는 `def` 하나다.
- 쓰기 전에 묶여 있어야 한다.
- parameter 이름을 가리는 대입은 거절한다.
- **`if` 몸통 안에서 묶은 이름은 그 몸통 밖에서 못 쓴다.** 형제 분기가 같은 이름을 묶는 것은
  되고, 안쪽 몸통이 바깥에서 이미 묶인 이름을 다시 묶는 것은 거절이다. 위
  `### if 는 열고 for 와 while 은 안 연다` 가 그 셋을 정한다.
- 묶인 이름은 target 자리와 `require()` 의 피연산자 자리와 **tool 의 인자 자리**에 온다 —
  `click(t, btn)` 처럼 수를 받는 인자 자리에도 선다. kind 는 쓰인 자리가 정하고(위
  `### 타입은 선언한다 — parameter 와 반환과 대입 전부`), 묶인 값의 종류와 그 자리가 요구하는
  종류가 다르면 저장 때 거절한다.

**리터럴 대입을 여는 실질적 이유는 반복이다.** selector 는 언제나 전체 형태로 적어야 하고
(`Root[0]/Canvas[1]/CardSlot(Clone)[0]`), 같은 주소를 한 macro 안에서 두 번 세 번 적는 일이
흔하다. `macro-errors-and-reporting` 의 `## require 두 종류` 예시의 `CombineButton[2]` 가 `require` 와 `click` 에
한 번씩 나온다. 이름에
묶으면 반복과 오타가 준다.

```python
combine: object = selector("Root[0]/Canvas[1]/CombineButton[2]")
require(actionable(combine), "조합 버튼이 아직 안 살아 있다. 두 슬롯이 다 찼는지 보고 다시 불러라")
click(combine)
```

**이것이 주된 쓸모이고 숫자 리터럴 대입은 덤이다.** `btn = 1` 을 묶어 `click(t, btn)` 으로
쓰는 것이 읽기 좋은 자리가 있지만, selector 반복을 없애는 쪽이 이 변경의 값이다.

**`selector(...)` 를 묶은 이름은 `find` 를 묶은 이름과 다르게 산다.** `find` 는 그 자리에서
풀어 pulse 기록 하나를 고정하지만, `selector(...)` 대입은 **적어 둔 문자열에 이름을 붙이는
것뿐이다** — 그 자리에서 아무것도 안 풀고, 쓰는 statement 가 그 문자열을 그대로 wire 에 얹어
SDK 가 action 프레임에 푼다. late binding 을 하나도 안 잃는다. 그래서 그 이름으로 겨눠서
아무 데도 안 닿으면 나가는 것은 `STALE_BINDING` 이 아니라 `REQUIRE_FAILED` 다 — `macro-errors-and-reporting` 의
`## 에러 코드 여덟 개` 가 가르는 기준이 "적어 둔 주소인가 이 런에서 찾은 값인가" 이고, 이
이름은 적어 둔 주소다. 대입 자리에서 `SELECTOR_NOT_FOUND` 나 `SELECTOR_AMBIGUOUS` 가 나는
것도 `find` 대입뿐이다.

`find` 는 keyword 인자만 받는다. **v1 이 받는 것은 셋이고, `label` 과 `name` 중 최소 하나는
있어야 한다.**

| keyword | 값 | 무엇에 맞추나 |
|---|---|---|
| `label` | 문자열 리터럴 또는 parameter | `PulseObject.text`(`pulse.py:148`) — 그 객체가 지금 화면에 띄우고 있는 글자 |
| `name` | 문자열 리터럴 또는 parameter | `PulseObject.path`(`pulse.py:132`)의 마지막 세그먼트 — GameObject 이름 |
| `under` | `selector(<문자열>)` 또는 selector kind parameter | 기록의 `selector` 가 이 문자열로 시작하고 바로 뒤가 `/` 다 |

`label` 과 `name` 을 둘 다 적으면 둘 다 맞아야 한다. **맞추는 방법은 정확히 같은 글자다** —
부분 일치도 대소문자 무시도 없다. agent 가 화면에서 읽은 글자를 그대로 적으면 맞는다는 뜻이고,
한 글자라도 다르면 `SELECTOR_NOT_FOUND` 다. `under` 만 적은 `find` 는 거절한다 — 범위는
조건이 아니다.

**`find` 는 서버가 이미 들고 있는 `PulseMemory` 에 대고 푼다. SDK 는 한 줄도 안 고친다.**
`PulseObject` 가 `text` 와 `path` 와 `selector` 를 한 기록에 다 들고 있고 `find` 는 그 값을
본다. 규칙의 근거와 `under` 의 prefix 맞추기는 `macro-targets-and-memory` 의 `### 조회 넷이 전부 pulse 기록을 본다` 와
`macro-targets-and-memory` 의 `### under= 를 v1 에 넣는다` 에 있다.

**`label` 이 label 과 placeholder 로 접히던 것이 없어졌다.** 앞선 판은 `SceneMemory` 의
`item.label or item.placeholder or ""` 를 맞췄고, 그래서 `find(label="Enter name")` 이 라벨과
입력 칸을 같이 잡았다. `PulseObject.text` 는 그 객체가 지금 띄우고 있는 글자 하나다.

**묶기 실패가 곧 에러다.** 하나도 못 찾으면 `SELECTOR_NOT_FOUND`, 둘 이상 잡히면
`SELECTOR_AMBIGUOUS` 가 **그 대입 statement 에서** 난다. 그래서 뒤에 `require(exists(...))`
를 따로 적을 필요가 없다.

**대입 statement 는 게임에 아무것도 안 보낸다.** `require` 와 같다. batch 를 안 만들고,
`macro-errors-and-reporting` 의 `## 부분 실행을 반드시 보고한다` 의 `applied` 에도 안 든다.

#### 대가 — 묶는 순간 late binding 을 그만큼 잃는다

#179 가 selector 해석을 **action 이 실제로 도는 프레임으로** 옮긴 이유는, 마지막으로 본 뒤에
대상이 움직이거나 animate in 해도 닿게 하려는 것이었다 (`click` 의 docstring 이 그 값을
적어 뒀다). 이름에 instance id 를 묶어 두면 그 성질을 그만큼 되돌린다. **묶은 순간과 쓰는
순간 사이에 대상이 죽을 수 있고**, 이 macro 가 정확히 그런 경우다 — combine 은 원래 카드 두
장을 없앤다.

그래서 여섯 번째 에러 코드 `STALE_BINDING` 을 둔다. `macro-errors-and-reporting` 의 `## 에러 코드 여덟 개` 에 있다.

### 허용하는 node 와 거절하는 node

허용하는 것.

| 무엇 | 모양 |
|---|---|
| 함수 정의 | `def <name>(<params>) -> None:` 하나 이상과 `def <name>(<params>) -> bool:` 0개 이상, 전부 맨 위, 본문은 들여쓰기. **parameter 마다 annotation 이 있어야 하고 반환 annotation 도 있어야 한다**, 기본값은 리터럴 하나. `-> None` 중 이름이 macro 이름과 같은 것이 진입점, 나머지가 helper, `-> bool` 이 predicate 다. 진입점은 `-> bool` 일 수 없다 (위 `### 저자가 helper def 를 둘 수 있다` 와 `### predicate def 는 bool 을 돌려준다`) |
| tool 호출 statement | 위 `### 이 언어의 함수 전체 목록` (A) 의 열네 이름, 또는 같은 source 안의 helper `def` 이름 |
| `require()` statement | **인자 둘** — 조건 하나와 비어 있지 않은 문자열 리터럴 remedy 하나. keyword 인자는 안 받는다 |
| 대입 statement | **`ast.AnnAssign`** 중 target 이 `ast.Name` 하나이고 annotation 이 타입 이름 하나이고 값이 `find` 호출 · `selector` 호출 · `Constant` 리터럴 하나인 것. **annotation 없는 `ast.Assign` 은 거절한다** (위 `### 타입은 선언한다`) |
| `if` statement | **`ast.If`**. `test` 는 아래 `조건` 행과 같은 모양, `body` 와 `orelse` 는 이 표의 statement 일곱 종류이고 predicate 안에서는 대입 · `if` · `return` 셋이다. `orelse` 가 `If` 하나인 것이 `elif` 이고 그것도 받는다 (위 `### if 는 열고 for 와 while 은 안 연다`) |
| `flag()` statement | **인자 하나** — 비어 있지 않은 메시지 문자열 리터럴. keyword 인자는 안 받는다 |
| `ask_verdict()` statement | **인자 하나** — 비어 있지 않은 기대 문자열 리터럴. keyword 인자는 안 받는다. 숫자 리터럴을 앞에 하나 더 적으면 step 번호를 빼라는 거절이 난다 |
| `wait_until()` statement | **인자 셋** — 조건 하나, 0 보다 크고 30 이하인 숫자 리터럴 하나, 비어 있지 않은 문자열 리터럴 remedy 하나. keyword 인자는 안 받는다. predicate 안에서는 거절이다 (위 `### wait_until 은 조건이 참이 될 때까지 기다린다`) |
| `return` statement | **predicate 안에서만.** `ast.Return` 의 `value` 가 아래 `조건` 행과 같은 모양이어야 하고 `value` 없는 `return` 은 거절한다. 모든 경로가 `return` 으로 끝나야 하고 `return` 뒤의 statement 는 거절한다 (위 `### predicate def 는 bool 을 돌려준다`) |
| 조건 | 비교 하나 (`==` `!=` `>` `<` `>=` `<=`), boolean 을 내는 읽기 하나, predicate 호출 하나, 또는 `True` · `False` 리터럴 하나. `require` 의 첫 인자, `if` 의 `test`, `wait_until` 의 첫 인자, `return` 의 값이 같은 이 모양이다. 어느 연산자가 되는지는 위 `### 연산자 dispatch` 표가 정한다 |
| 값 | 문자열·숫자·bool·`None` 리터럴, 맨이름(parameter 나 묶인 이름), 위 아홉 호출 |

거절하는 것: `for` · `while`, `and` · `or` · `not`, attribute access (`scene.name`,
그리고 object 에 대한 `t.id`), 중첩 `def` (`def` 는 전부 맨 위에 있어야 한다), `import`,
`lambda`, f-string, `-> None` 인 `def` 안의 `return`, docstring, **annotation 없는 대입(`ast.Assign`)**, 타입 이름이
아닌 annotation, 오른쪽이 `find` · `selector` · 리터럴 중 어느 것도 아닌 대입, 그 밖 전부.

**`if` 는 이 목록에서 빠졌고 `for` 와 `while` 은 남았다.** 두 결정을 가르는 근거는 위
`### if 는 열고 for 와 while 은 안 연다` 에 있다 — `if` 는 적힌 statement 를 세면 총수가
정해지고, 반복은 몇 번 도는지 저장 시점에 모른다. `and` · `or` · `not` 은 `require` 의
조건에서든 `if` 의 조건에서든 똑같이 거절이다.

두 가지는 목록에 넣을지 따로 정했다.

- **keyword argument 를 받는다.** `drag(a, b, button=1)` 을 keyword 없이 적으면
  `drag(a, b, 1)` 이고, 그 `1` 이 오른쪽 버튼이라는 것을 알려면 tool 표를 봐야 한다. 읽는
  사람에게 그것은 비용이다. `find` 는 아예 keyword 로만 받는다. 그래서 `ast.keyword` 를
  **tool 호출 statement 와 `find` 호출 둘 다에서** 받는다. 이름은 그 tool 의 인자 이름이거나
  `find` 의 `label` · `name` · `under` 여야 하고, 그 밖의 이름은 거절한다. **`require()` 는
  keyword 인자를 아예 안 받는다** — 조건 안에서도, `require` 호출 자체에서도. 뒤엣것이
  `require(hp = 100)` 이고, `macro-errors-and-reporting` 의
  `#### 함정 — require(hp = 100) 은 Python 문법 오류가 아니다`
  가 그 자리다. 거절 문장이 `==` 를 이름 대야 한다.
- **숫자 앞의 부호 하나만 `UnaryOp` 를 받는다.** Python 에서 `-1` 은 리터럴이 아니라 `USub`
  이고, `set_input_axis("Horizontal", -1)` 이 그것 없이는 안 써진다. 그 tool 의 값 범위가
  -1 부터 1 이라 음수를 못 적으면 축 하나가 한쪽으로만 움직인다. 숫자 `Constant` 를
  피연산자로 하는 `USub` 과 `UAdd` 만 받아 파싱 자리에서 부호 붙은 상수로 접고, 그 밖의
  연산자는 전부 거절한다. `not` 은 `UnaryOp(Not)` 이라 여기 안 들고, 거절이다.

bool 은 Python 것을 쓴다 — `True` 와 `False` 다. **소문자 `true` 는 리터럴이 아니라
`ast.Name` 이라 위 불변식대로 묶인 이름으로 읽히고, 묶인 적이 없으니 거절된다.** 거절 문장이
`True` 를 이름으로 대야 model 이 한 번에 고친다.

`and` 를 안 받는 것은 손해가 아니다. `require()` 를 잇따라 둘 두면 같은 뜻이고 — 나란한
`require` 는 같은 관측 위에서 판정되므로 결과가 같다 — 그러면 어느 조건이 깨졌는지도
statement 번호로 나온다. `not` 도 마찬가지로 `absent()` 와 `!=` 가 받는다. **`if` 의
조건에서도 같다** — 조건 둘이 필요하면 `if` 를 중첩한다. `or` 는 predicate `def` 로 적는다 —
`if` 를 나란히 두고 각각 `return True` 한다 (위 `### predicate def 는 bool 을 돌려준다`).
그래서 `or` 연산자를 열 이유가 남지 않는다.

### 세는 상한 일곱

| 무엇 | 값 | 언제 판정 |
|---|---|---|
| source 하나의 statement 수 | **1개 이상 32개 이하** — 진입점과 helper 와 predicate 를 **합쳐서** 센다 | 저장 때 |
| `def` 하나의 parameter 수 | 8개까지 | 저장 때 |
| `def` 하나가 묶는 이름 수 | 8개까지 | 저장 때 |
| 호출 깊이 | **3** — 진입점을 1로 센다 | 저장 때 |
| 한 실행에서 도는 statement 총수 | **128** | 저장 때 |
| `wait_until` 하나의 최대 대기 시간 | **0초 초과 30초 이하** | 저장 때 |
| 한 실행 경로의 최대 대기 시간 합계 | **60초** | 저장 때 |

앞의 셋은 앞선 판에서 그대로다. statement 32개는 `require` 와 대입과 `if` 와 `flag` 와
`ask_verdict` 와 `wait_until` 도 세고 — 일곱 종류를 다 센다 — predicate 의 statement 도 센다. action statement 하나가 batch 하나이므로 32개가
전부 action 이면 게임과 32번 왕복한다. `if` 는 자기 한 줄도 세고 몸통 안의 statement 도 센다.
parameter 8 과 묶는 이름 8 은 한 `def` 를 읽는 사람이 머리에 들고 있어야 하는 이름을 16개로
묶는다.

**호출 깊이 3 — 얕게 둔다.** helper 한 겹이 흔한 경우이고(카드 한 장을 슬롯에 놓는 절차),
두 겹이면 이미 빡빡하다. 얕게 두는 이유는 payload 가 호출 사슬을 그대로 찍기 때문이다 (위
`#### 펼치지 않는다`) — 네 겹짜리 사슬은 한 payload 에서 읽히지 않는다. 호출 그래프가 저장
시점에 전부 보이므로 깊이도 저장 때 판정한다.

**도는 statement 총수 128 — 32 의 네 배다.** source 는 32개까지인데 helper 를 여러 번 부르면
도는 statement 는 그보다 많아지므로 상한이 따로 필요하다. 128 은 "진입점 하나에 32개짜리
helper 세 벌" 이고, 그보다 긴 것은 macro 를 나누는 쪽이 맞다. **이 수는 천장이지 목표가
아니다** — 128개가 전부 action 이면 게임과 128번 왕복한다.

**이것도 저장 때 판정한다.** 반복도 재귀도 없으므로 호출 트리를 펴서 세면 실행될 statement
수의 최대값이 정확히 나온다 — 아래 `### 눌러 둔 것이 macro 끝에 남으면 거절한다` 의 정적
카운터와 같은 근거다. **`if` 가 있어도 최대값은 가지들 중 큰 쪽이라 여전히 정적이다** (위
`### if 는 열고 for 와 while 은 안 연다`). 그래서 이 상한을 위해 런타임 에러 코드를 새로 둘 일이 없고, 넘긴
macro 는 `MACRO_NODE_REJECTED` 로 등록 자체가 안 된다. **세는 것은 펴서 세는 것뿐이고, 실행은
그대로 안 편다** (위 `#### 펼치지 않는다`).

**predicate 는 부르는 자리마다 한 번으로 센다.** `wait_until` 이 predicate 를 몇 번 평가하든
그 횟수는 이 총수에 안 든다. 다시 평가하는 것은 판독뿐이라 게임과 왕복하지 않고, 평가가
늘어나는 정도는 아래 대기 시간 상한이 막는다.

**`wait_until` 하나는 30초까지 — 기다림이 그보다 길면 macro 를 나눈다.** 30초를 넘게 기다릴
자리는 장면 전환이나 긴 연출 정도이고, 그때는 agent 가 직접 관측하는 편이 무엇이 멈췄는지 더
잘 본다. 수치는 첫 구현에서 정한 값이고, 실제 게임의 로딩 시간을 재 보고 조정한다.

**한 실행 경로의 합계는 60초 — macro 하나를 한 번 실행할 때 최대로 기다릴 수 있는 시간이다.**
`wait_until` 의 최대 대기 시간을 경로를 따라 더한다. `if` 는 한 번 실행에 분기 하나만 가므로
분기들을 다 더하지 않고 분기마다 더해서 큰 쪽을 쓴다. helper 안의 `wait_until` 은 그 helper 를
부른 횟수만큼 더한다. statement 총수 128 을 세는 방식과 같고, 같은 이유로 저장 때 정확히
나온다. 예를 들어 `wait_until(..., 20.0, ...)` 뒤에 `if` 가 있고 한쪽 분기에 30초, 다른 쪽에
10초가 있으면 합계는 `20 + max(30, 10) = 50` 초이고 통과한다. 다른 쪽 분기가 45초면
`20 + 45 = 65` 초라 거절이다. 넘긴 macro 는 `MACRO_NODE_REJECTED` 이고, 거절 문장이 합계가 가장
큰 경로의 `wait_until` 줄 번호를 전부 댄다.

### 눌러 둔 것이 macro 끝에 남으면 거절한다

`hold_key` · `hold_mouse_button` · `set_input_axis` · `set_input_button` ·
`pause_game_time` 은 게임에 상태를 남기고 아무것도 자동으로 안 풀어 준다. **반복이 없어 경로가
유한하므로 저장 시점에 세어서 정확히 판정할 수 있다** — `key_code` · `button` · `axis_name`
마다 카운터를 하나 두고 statement 를 순서대로 훑어서, 마지막 statement 뒤에 0이 아닌 카운터가
있으면 거절한다. `if` 가 경로를 여럿으로 가르므로 **경로마다 따로 세고 어느 경로에서든 끝에
0이 아닌 카운터가 남으면 거절한다.** 짝 없는 release 로 시작하는 것도 거절한다. macro 밖에서 눌린 것을 macro 가 푸는
것은 부작용이고, 그것을 허용하면 macro 를 한 번 부를 때와 두 번 부를 때가 달라진다.

**같은 카운터가 `wait_until` 도 검사한다.** `wait_until` 에 이르렀을 때 `pause_game_time` 의
카운터가 0이 아닌 경로가 하나라도 있으면 거절한다. 이유는 위
`### wait_until 은 조건이 참이 될 때까지 기다린다` 에 있다.

### `step` 과 `thought` 는 macro 의 인자가 아니다

모든 action tool 이 `step` 과 `thought` 를 받지만 macro statement 는 둘 다 안 적는다.
`step` 은 `run_macro` 호출이 받은 값을 안쪽 statement 가 전부 물려받는다 — macro 하나가
시나리오 step 하나에 속한다. `thought` 는 `run_macro` 한 번에 하나뿐이고, 그 이유는 `macro-errors-and-reporting` 의
`## macro 안쪽 단계를 timeline 에 남긴다` 에 있다.

### 저장은 텍스트와 JSON 둘 다 한다

authoring surface 는 텍스트다. agent 가 적는 것도 사람이 읽는 것도 위 함수 텍스트이고, 그것을
그대로 저장한다. **동시에 파싱 결과 JSON 도 저장한다.**

- **텍스트를 저장하는 이유.** `ast.parse` 는 주석과 공백을 버린다. JSON 에서 텍스트를 다시
  찍어내면 agent 가 적은 그대로가 아니고, 정의가 바뀌었을 때 사람이 보는 diff 가 실제로
  바뀐 줄을 안 가리킨다.
- **JSON 을 저장하는 이유.** 실행할 때마다 다시 파싱하면, 저장된 뒤에 허용 목록이 좁아진
  정의가 런 한복판에서 처음 거절된다. 파싱은 `register_macro` 한 번뿐이고 실행은 JSON 만
  본다.

JSON 은 `def` 마다 한 항목이고 — helper 가 있으면 항목이 여럿이다 — 항목마다 자기
`params` · `bindings` · `steps` 를 든다. **번호는 항목마다 1부터 센다.** 그리고 statement
마다 **그 줄의 원문 텍스트도 같이 든다.** 에러 payload 의 `at` 줄과
timeline 의 한 줄이 그 값을 그대로 싣고, 그래서 실행 쪽이 텍스트 전체를 다시 파싱할 일이
없다.

**텍스트가 원본이고 JSON 은 거기서 나온 것이다.** 그래서 정의를 고치는 길은 텍스트를 고쳐
다시 등록하는 것 하나뿐이다 — `write_macro` 나 `edit_macro` 로 초안을 바꾸고
`register_macro` 를 부른다 (`store-and-replay-action-sequences-as-macros` 의 `## 첫 버전 범위 — tool 다섯 개`).
JSON 만 고치는 경로를
열면 둘이 어긋난다.
