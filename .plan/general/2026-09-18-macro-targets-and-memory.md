# macro 가 무엇을 겨누나 — selector 와 pulse memory

- Date: 2026-09-18
- 입구 문서:
  [`2026-09-18-store-and-replay-action-sequences-as-macros.md`](2026-09-18-store-and-replay-action-sequences-as-macros.md)
  — 머리말과 Goal, 실행기와 저장 자리, 첫 버전 범위, Non-goals, 열려 있는 질문, 그리고
  `## 쪼개는 방법` 이 거기 있다
- 이 파일이 드는 것: macro 에 selector 를 저장하는 이유, `PulseMemory` 가 유일 출처라는 것, `find`, 묶인 이름, 보조인 `SceneMemory`

## macro 에 id 와 좌표 대신 selector 를 저장한다

`target_id` 는 지금 보고 있는 scene 안에서만 산다. `reset_game` 의 docstring 이 그것을
적어 뒀다 — "Every target id you have is dead afterwards; observe before you act again."
좌표는 해상도와 레이아웃을 탄다. **id 나 좌표를 macro 에 굳혀 넣으면 그 macro 는 저장되는
순간 이미 깨져 있다.**

저장하는 것은 값이 아니라 그 값을 다시 찾는 방법, 즉 selector 다. 호출 시점에 현재 scene
에서 풀어 쓰는 late binding 이다.

### late binding 은 이미 wire 에 있다

#179 가 `click` · `double_click` · `drag` · `move_pointer` 의 `target` 을 문자열 하나로
바꿨고, `parse_target`(`action_tools.py:25`)이 세 형태를 가른다.

| 형태 | 모양 | 예 |
|---|---|---|
| screen point | 쉼표 하나 사이의 숫자 둘, 엄격하게 | `640,360` |
| instance id | `#` 뒤의 정수 | `#12345` |
| selector | 나머지 전부 — Unity hierarchy path | `Root[0]/Canvas[1]/Card(Clone)[3]` |

selector 는 agent-server 가 안 푼다. 문자열 그대로 `move_mouse` 의 params 에 실려 나가고
SDK 의 `SelectorAim` 이 **그 action 이 실제로 도는 순간** 푼다. `click` 의 docstring 이 그
값을 이미 적어 뒀다 — 마지막 관측 뒤에 움직였거나 animate in 한 것도 지금 있는 자리에서
맞는다.

**그러니 macro 가 selector 를 저장하면 서버가 해석표를 들 필요가 없다.** 저장한 문자열이
그대로 나간다.

이 handle 은 content map 쪽에도 있다. `app/specs_v2/graph.py:261` 이 evidence 의 object 를
`obj.get("selector") or obj.get("path")` 로 키 잡고, `capability.control_selector`(V40)가 같은
문자열을 든다.

### selector 가 조용히 다른 것을 가리키는 한 경우

`ScenePathSelectorResolver` 는 `name[siblingIndex]` 를 `/` 로 이은 것을 되짚는다. 세그먼트마다
`GetChild(index)` 로 내려가고 **이름이 다르면 거절한다** — 그 자리의 주석이 이유를 적어 뒀다:
"자리만 맞고 이름이 다르면 엉뚱한 것을 겨눈 것이므로, 조용히 넘어가지 않고 여기서 거절한다."

그래서 남는 구멍은 하나다. **이름이 같은 형제가 여럿이고 그 중 하나가 사라져 index 가
밀리는 경우.** `Card(Clone)[3]` 은 앞의 카드 한 장이 빠지면 `Card(Clone)[4]` 였던 카드를
가리키고, 이름이 같으니 resolver 가 통과시킨다. 에러도 안 나고 다른 카드를 집는다.

**이것이 정확히 이 macro 가 겨누는 경우다.** 손패의 카드는 런타임에 spawn 되는 목록이고,
V40 의 `control_selector` 주석이 그 경우를 이미 지목해 뒀다 — "런타임에 스폰되는 목록에는
채우지 않는 편이 맞다."

`Root[0]/...` 형태의 selector 만으로 `attack_with_combined_card(card_a, card_b, target)` 을
쓸 수 없다는 뜻이다. `card_a` 는 위치가 아니라 **"label 이 `shoot` 인 카드"** 를 가리켜야
한다.

`macro-language-reference` 의 `### 이름 하나에 find() 결과를 묶는다` 가 `find` 를 더해 그 절반을 메운다. 어디까지
메워지는지 정확히 세 갈래다.

1. **경로 selector 로는 못 가리킨다.** `Card(Clone)[3]` 을 macro 에 적으면 앞의 카드 한
   장이 빠졌을 때 여전히 조용히 다른 카드를 집는다. resolver 가 이름만 보고 index 는 안
   따지기 때문이고, 표기법을 바꿔도 이것은 그대로다. **런타임에 spawn 되는 목록에는 경로
   selector 를 안 쓴다** 가 규칙으로 남는다.
2. **`find(label="shoot")` 으로 가리킨다 — 화면에 그 글자를 띄운 것이 한 장뿐일 때.** 서버가
   `PulseMemory` 에서 `PulseObject.text` 로 풀므로 index 를 안 탄다. 범위를 좁혀야 하면
   `find(label="shoot", under=selector("Root[0]/Canvas[1]/Hand[2]"))` 이다.
3. **같은 글자를 띄운 것이 둘 이상이면 v1 에서 못 가리킨다.** `SELECTOR_AMBIGUOUS` 가 나고
   거기서 멈춘다. `under=` 로도 한 장으로 못 좁혀지면 둘 중 하나를 고를 순번 문법이 v1 에
   없다. `shoot` 을 두 장 든 손패는 이 macro 로 못 다룬다.

**3번의 구멍이 좁아졌다.** 이 문서의 앞선 판에서 이 자리는 "이름이 같은 카드 두 장" 이었다.
이제 `Card(Clone)` 두 개가 각각 `shoot` 과 `fire` 를 띄우고 있으면 **갈린다** — 이름이 같아도
글자가 다르면 `find(label=)` 이 하나로 푼다. 남는 것은 **같은 글자를 띄운 두 장**이다.
**좁아진 것이지 풀린 것이 아니다.**

3번을 열려면 무엇이 필요한지는 `store-and-replay-action-sequences-as-macros` 의 열려 있는 질문 첫 항목에 적었다. **지금 정하지 않은 것을
정해진 것처럼 읽으면 안 되므로 여기 못박아 둔다 — v1 의 `find` 는 글자가 유일한 경우만
다룬다.**

## 출처는 `PulseMemory` 하나다 — `SceneMemory` 는 보조다

서버가 게임에 대해 아는 것은 두 군데이지만, **기본 빌드에서 차 있는 것은 한 군데다.**

| | `PulseMemory`(`pulse.py:298`) | `SceneMemory`(`scene.py:193`) |
|---|---|---|
| 출처 | pulse frame | `GAME_STATE` scan frame |
| 기본 빌드에서 | 찬다 | **끝까지 빈다** |
| 주소 | `씬/selector`(`pulse.py:174`) | instance `id` |
| 드는 것 | `id` · `selector` · `path` · `rect` · `tag` · `text` · `members` · `offers`(`pulse.py:128~150`) | `id` · `name` · `type` · `label` · `placeholder` · `rect` · `onScreen`(`envelope.py:249`) |
| "지금 누를 수 있나" | `offers`(`pulse.py:734` 의 `actionable = bool(obj.offers)`) | `you can act on:` 목록(`scene.py:435`) |

`PulseMemory` 는 `SceneMemory` 의 필드이므로(`scene.py:238` 의 `pulse: PulseMemory`) 한 객체
안에 둘이 다 있다. 그래도 **macro 의 조회는 `PulseMemory` 한 군데만 본다.** 이유가 셋이다.

1. **`GAME_STATE` 는 꺼져 있을 뿐 아니라 없어질 채널이다.** `ArtelManager.SendsGameState`
   (`ArtelManager.cs:50`)의 요약이 "기본은 끔이다" 라고 적고(ARTEL-513), 그 remarks 가
   **"임시 스위치다. 실제로 지우는 것은 ARTEL-400 이고, 그때 이 속성도 함께 사라진다"** 고
   적는다. 그 위에 세운 문법은 지금 반쯤 안 돌고 ARTEL-400 뒤에는 통째로 안 돈다.
2. **실측이 그 말을 받는다.** `scene.py:386` 의 주석이 한 런에서 `GAME_STATE` 0장, `PULSE`
   14489장이라고 적는다.
3. **pulse 기록 하나가 필요한 것을 다 든다.** `PulseObject`(`pulse.py:125`)는 `id` ·
   `selector` · `path` · `text` · `tag` · `offers` · `members` 를 **한 기록에** 싣는다.
   겨눌 값도 맞출 글자도 판정할 `offers` 도 같은 자리에 있다.

**그래서 이 문서의 앞선 판이 정한 "`find` 는 `SceneMemory`, `selector` 는 `PulseMemory`,
instance `id` 로 합친다" 를 버린다.** 합칠 것이 없다. 출처가 하나다.

### 조회 넷이 전부 pulse 기록을 본다

| 문법 | 무엇에 맞추나 | 어디 |
|---|---|---|
| `selector(<문자열>)` | pulse 키의 selector 부분 | `pulse.py:174` 의 `씬/selector` |
| `find(label=...)` | `PulseObject.text` | `pulse.py:148` |
| `find(name=...)` | `path` 의 마지막 세그먼트 | `pulse.py:132` |
| `find(under=...)` | selector 의 prefix | `pulse.py:174` |

넷 다 돌려주는 것은 **pulse 기록 하나**다.

**`find(label=)` 이 `PulseObject.text` 를 맞춘다.** 그 필드는 라벨을 위해 있는 것이다 — 그
자리의 주석이 적는다(ARTEL-678): "라벨은 멤버도 offer 도 없어서, 이 값이 없으면 판독에 실려
와도 그릴 것이 없는 객체가 된다." 손패 카드가 띄우고 있는 글자도 여기 실린다. 그리고 그 값이
**지금 화면에 그려지고 있는 글자와 같은 문자열**이라는 것을 화면의 글자 절이 보장한다 —
`pulse.py:638~676` 이 `live` 이고 글자가 빈 문자열이 아닌 기록만 골라 `the screen reads:`
아래에 찍고, 그 자리의 주석이 순서까지 적는다: "글자가 앞, 주소가 뒤다. 읽을 것은 글자이고
주소는 그것을 `inspect_object` 로 펴거나 겨누기 위한 것이다." **agent 가 화면에서 읽은 글자를
그대로 적으면 맞는다.**

`find` 도 그 절과 같은 두 조건으로 거른다 — `live` 인 기록만 보고, 글자가 빈 문자열인 기록은
안 본다. 꺼진 객체의 글자는 화면에 없는데 SDK 는 꺼진 객체에도 글자를 싣는다고 그 자리 주석이
적으므로, 거르는 것은 이쪽 몫이다.

**`find(name=)` 은 `path` 의 마지막 세그먼트를 맞춘다.** `ScenePath.Of` 가 만드는 `path` 는
이름만 `/` 로 이은 것이라 마지막 세그먼트가 곧 GameObject 이름이다 — `Root/Canvas/Card(Clone)`
의 `Card(Clone)` 이다. `path` 가 안 실려 온 기록에서는 `selector` 의 마지막 세그먼트에서 뒤의
`[<숫자>]` 하나를 떼어 낸 것을 쓴다. `SelectorOf` 가 붙이는 index 는 세그먼트의 **마지막**
대괄호이므로 이름 안에 대괄호가 있어도 안 깨진다. 맞추는 방법은 `label` 과 같다 — 정확히 같은
글자이고, 부분 일치도 대소문자 무시도 없다.

### `under=` 를 v1 에 넣는다

앞선 판은 `under=` 를 열려 있는 질문에 두었고, 이유는 **커버리지가 두 memory 에서 갈린다**는
것이었다 — prefix 로 좁힐 수 있는 것은 pulse 가 실은 객체뿐인데 `find` 는 `SceneMemory` 에서
찾으니 좁혀지지 않는다는 것. **출처가 하나가 되면서 그 이유가 없어졌다.** 좁히는 것도 찾는
것도 같은 `held` 사전이라 갈릴 것이 없다.

pulse 키가 전체 selector 경로이므로 prefix 하나면 된다.

```python
a: object = find(label=card_a, under=selector("Root[0]/Canvas[1]/Hand[2]"))
```

- 맞추는 방법은 **prefix 다.** 기록의 `selector` 가 그 문자열로 시작하고 **바로 뒤가 `/`**
  일 때 범위 안이다. 그래서 `under=` 가 이름 댄 객체 자신은 범위에 안 든다.
- `under=` 의 값은 `selector(<문자열>)` 이거나 selector kind parameter 다. **묶인 이름은 안
  받는다** — 그 자리는 겨누는 자리가 아니라 범위이고, 범위가 이 런에서 방금 찾은 것에
  매달리면 `STALE_BINDING` 이 범위에서도 나야 한다. v1 은 그 갈래를 안 만든다.
- `under=` 혼자서는 못 쓴다. `label=` 이나 `name=` 중 최소 하나는 있어야 한다.

선례도 있다. `inspect`(`pulse.py:773`)가 이미 같은 문자열에 부분 일치를 걸고 있다. `find` 는
거기서 한 걸음 좁혀 prefix 로만 맞춘다 — `inspect` 는 사람이 주소를 옮겨 적는 왕복을 줄이려고
느슨하지만, `find` 가 무엇을 겨눴는지는 조용히 틀리면 안 되는 값이다.

**`find` 의 인자는 `label=` · `name=` · `under=` 셋이다.**

### `actionable()` 은 `offers` 를 읽는다 — 물러날 자리가 없다

앞선 판은 `offers` 를 먼저 보고 `you can act on:` 으로 물러나는 순서 셋을 세웠다. **그 순서를
없앤다.** 기본 빌드에 `you can act on:` 이 한 줄도 안 찍히기 때문이다 — `SceneMemory.scene`
이 끝까지 `None` 이라 `render` 가 pulse 만 그리는 갈래(`scene.py:371`)로 가고, 그 목록을 찍는
`scene.py:435` 를 지나가지 않는다. **있지도 않은 목록은 물러날 자리가 아니다.**

그래서 `actionable(<target>)` 은 그 기록의 `offers` 하나로 답한다. 비어 있으면 거짓이다.
`pulse.py:734` 가 이미 같은 판정을 쓰고 있고, 그 자리의 주석이 `id` 로 가르면 안 되는 이유까지
적어 뒀다: "id 는 거의 모든 객체에 실리므로 그것으로 가르면 아무것도 안 걸러진다 — offers 가
그 선이다."

**여기 붙던 유보도 같이 없어진다.** `Interactable` 모델에 `interactable` 이라는 boolean 이
없다는 것은 `you can act on:` 으로 답할 때만 문제였다. `offers` 는 게임이 그 객체에 무엇을
배선해 뒀는지를 직접 말한다 — `_offered`(`pulse.py:917`)가 `click → <컴포넌트>.<메서드>` 와
`keys: ...` 와 `pointer: ...` 로 찍는다.

`SendsGameState` 를 켠 빌드에서는 `SceneMemory` 가 그 위에 더 있다. macro 는 그것을 안 읽고,
v1 문법에 그것을 읽는 자리가 없다.

### `text()` 는 `PulseObject.text` 를 읽는다

`text()` 를 v1 에 되살린 결정이 여기서 뒷받침된다. 앞선 판에서 그것은 `SceneMemory` 의
`item.label or item.placeholder` 하나로만 답하는 읽기였고, 기본 빌드에서는 답할 자리가 아예
없었다. **이제 `PulseObject.text` 를 그대로 읽는다** — `find(label=)` 이 맞추는 그 값이고,
화면의 글자 절이 그리는 그 값이다. 세 자리가 한 문자열을 본다.

값이 둘로 접히던 것도 같이 풀린다. `item.label or item.placeholder or ""` 는 label 과
placeholder 를 접은 값이라 `find(label="Enter name")` 이 라벨과 입력 칸을 같이 잡았다.
`PulseObject.text` 는 그 객체가 **지금 화면에 띄우고 있는 글자** 하나다.

**`text()` 가 답하기 쉬운 값이 된 것이 이 반전의 덤이다.** "라벨이 무엇으로 바뀌었나" 는 QA
에서 자주 묻는 질문이고, 그것을 `SceneMemory` 에 걸어 두면 기본 빌드에서 못 묻는다.

### 묶인 이름이 드는 값은 id 가 아니라 pulse 기록이다

앞선 판은 `find` 와 `selector` 가 각각 다른 memory 에서 instance `id` 를 뽑아 그 숫자로
합쳤다. 이제 둘 다 pulse 기록 하나를 얻으므로 **묶인 이름이 드는 것도 그 기록이다.**

그 기록이 `id` 와 `selector` 를 둘 다 들고 있으므로(`pulse.py:131`·`133`, 그리고
`LiveState.Object`(`LiveState.cs:540~544`)가 매 기록에 둘 다 싣는다) **action 이 어느 쪽으로도
겨눌 수 있다.** `parse_target`(`action_tools.py:25`)이 `#12345` 와 selector 문자열을 둘 다
받으므로 wire 도 그대로다.

v1 은 `#id` 로 내보낸다. `_press_outcome` 의 `reached` 와 맞대기 쉬운 값이고 `STALE_BINDING`
판정이 거기 걸려 있기 때문이다(`macro-errors-and-reporting` 의 `## 에러 코드 여덟 개`). **selector 로 내보내는 길이
열려 있다는 것만 적어 둔다** — 한 기록이 둘을 다 들고 있어서 생긴 여지이고, 앞선 판에는 없던
것이다.

`id` 가 프로세스 안에서만 산다는 것(`pulse.py:129` 의 "It does not survive the process, which
is why `selector` rides along")은 그대로다. 대신 **`ObjectIds` 의 하위 32비트가 두 memory
에서 같은 숫자여야 한다는 요구가 없어졌다.** 합치기를 안 하므로 join 키가 없고, 앞선 판이
"지금 맞는 선택이지 보장된 선택이 아니다" 라고 적어 둔 위험이 이 설계에서 빠진다.

### 읽을 자리가 아예 없을 때 — 하나 남는다

앞선 판은 "한쪽에만 있을 때" 를 세 경우로 갈랐다. 출처가 하나가 되면서 그중 둘이 뜻을 잃는다
— 한쪽에만 있다는 말이 성립하려면 쪽이 둘이어야 한다. **남는 것은 하나이고, 그것이
`ACTION_REJECTED` 라는 결정은 그대로 선다.**

| 무엇이 없나 | 왜 일어나나 | 나가는 것 |
|---|---|---|
| `PulseMemory` 가 통째로 비어 있다 | 런이 막 시작해 pulse 를 한 장도 못 받았다, 또는 게임이 그 채널을 안 보낸다 | `ACTION_REJECTED`. batch 는 하나도 안 나간다 |

**`ACTION_REJECTED` 인 이유.** "그 자리에 없다" 가 아니라 **"볼 자리가 없다"** 이고, 그 둘은
agent 가 할 일이 다르다. 없는 것을 본 것은 macro 를 고치거나 결함을 적을 일이지만, 못 본 것은
관측하고 다시 부를 일이다. `macro-errors-and-reporting` 의 `## 에러 코드 여덟 개` 의 `ACTION_REJECTED` 행이 그 뜻 그대로다 —
환경 문제이고 step 을 실패로 적지 않는다. 포인터를 사람이 쥔 경우를 같은 코드에 둔 것도 같은
기준이었다. **payload 는 pulse 를 한 장도 못 받았다고 말한다.**

**비어 있는 memory 에서 못 찾은 것은 `SELECTOR_NOT_FOUND` 가 아니다.** `SELECTOR_NOT_FOUND` 는
**볼 목록이 있었고 거기 없었을 때만** 나간다.

### pulse 에 안 들어오는 객체 — 이것이 남는 커버리지 구멍이다

`find` 와 `selector` 가 같은 사전을 보므로 둘의 커버리지가 갈릴 일은 없다. 대신 **그 사전에
애초에 안 들어오는 객체**가 있고, 그것이 이 설계가 지는 커버리지 제한이다.

거르는 자리는 `Worth.Writing`(`Worth.cs:76`)이고 판정은 `Worth.Ask`(`Worth.cs:117`)다. 객체가
판독에 들어오려면 계기가 아니면서 아래 셋 중 하나여야 한다.

1. **글자를 띄울 수 있다** — `Legible.CanCarry` 가 참이다. 그 자리의 주석이 이 조건을 왜
   따로 뒀는지 적는다: "라벨은 근거를 굽지도 인스펙터로 무엇을 부르지도 않아 셋 중 어느
   조건에도 걸리지 않는데, 명세가 묻는 것은 그 라벨에 적힌 글자인 경우가 흔하다."
2. **watch list 에 든 컴포넌트나 `AffordanceCatalog` 에 든 컴포넌트가 붙어 있다.**
3. **인스펙터 persistent call 이 걸려 있다.**

SDK 자신의 계기는 `Instrument.Marks` 가 먼저 걸러 낸다 — 무엇을 들었든 안 싣는다(ARTEL-698).

**셋 중 어느 것도 아닌 객체는 `find` 로도 `selector(...)` 로도 못 찾는다.** 배경 이미지, 빈
컨테이너, 순수 장식이 그렇다. 그런 객체를 겨누는 절차는 macro 로 못 묶는다. 앞선 판은 그
자리를 `SceneMemory` 쪽 커버리지로 메우려 했는데, 기본 빌드에서 `SceneMemory` 가 끝까지 비어
있으므로 **메워진 적이 없었다.** 구멍이 늘어난 것이 아니라 드러난 것이다.

`Worth` 의 답은 기억된다. 긍정은 그대로 쥐고 부정만 1초(`StaleDenial`)마다 다시 묻는다 —
런타임에 컴포넌트가 붙는 객체가 영영 못 들어오던 결함을 그것이 고쳤다(ARTEL-840). 그래서
조건을 뒤늦게 갖춘 객체는 최대 1초 늦게 들어온다.

**`LiveState.cs:680` 의 `if (written == 0 && !moved) return false;` 는 이 커버리지와 다른
것이다.** 그것은 **판독 한 장**에서 뺄지를 정하는 델타 게이트다 — 이번에 아무것도 안 움직이고
쓸 멤버도 없는 객체를 그 한 장에서 뺀다. `PulseMemory` 는 판독을 접어 쌓으므로 한 번이라도
실린 객체는 `held` 사전에 남는다. 그리고 `Where`(`LiveState.cs:1056`)가 객체마다 world 와
rect 를 쓰는데 처음 보는 객체에서는 그것이 언제나 소식이므로, **`Worth` 를 지난 객체는 첫
판독에서 반드시 한 번 실린다.** 커버리지를 정하는 것은 `Worth` 하나다.

### `find` 는 이미 도착한 것만 본다

여기서 나오는 제약이 하나 더 있고, 그것이 실전에서 더 자주 걸린다. **`find` 가 보는 것은
`PulseMemory.held` 에 이미 들어온 기록뿐이다.** 그 객체의 첫 판독이 아직 안 왔으면 게임에
객체가 멀쩡히 있어도 `find` 는 못 찾고 `SELECTOR_NOT_FOUND` 를 낸다.

**이것은 macro 의 문제가 아니라 관측 순서의 문제다.** 화면이 방금 바뀐 직후가 정확히 이
경우다 — scene 을 넘어간 직후, 카드를 새로 뽑은 직후, 창이 막 열린 직후.

그래서 규칙이 하나 붙는다. **`run_macro` 를 부르기 전에 화면을 한 번 관측한다.** 그것이 이
실패를 막는 유일한 길이므로, `run_macro` 의 tool 설명에 그 한 줄이 들어가야 한다.

`SELECTOR_NOT_FOUND` 를 받은 agent 가 할 일도 이 순서로 바뀐다. **먼저 관측하고 다시 부른다.**
macro 가 낡았는지는 그 다음에 따진다 — 관측을 건너뛴 호출이 낡은 정의보다 흔할 것이기
때문이다.
