# 2026-08-18 — content map 구조 확장 (schema v7)

- Date: 2026-08-18
- GitHub Issue: None
- Jira: 에픽 ARTEL-444 / 신규 ARTEL-470 · ARTEL-473 · ARTEL-478 · ARTEL-479
- Status: Draft

## Goal

content map v6 은 SDK 리포트 원본이 **이미 산출한 사실**을 요약 과정에서 버린다.
버려진 것 중 시나리오 저작·TC 생성에 실제로 쓰이는 값만 골라 v7 에 **덧붙이기(additive)** 로 싣는다.

성공 기준은 하나다. 골든 맵의 capability 18 건이 기존 TC 66 건과 **같은 입도**가 되는 것.
지금 차이는 분석력 부족이 아니라 **전달 손실**이다.

## Non-goals

- content map 에 새 분석 기능을 추가하지 않는다. 원본에 있는 값을 옮기는 것이 전부다.
- v6 소비자를 깨지 않는다. 기존 키를 지우거나 의미를 바꾸지 않는다.
- `app/specs_v2` (agent-server) 파이프라인을 content map 으로 대체하지 않는다. 둘은 같은 원본의 두 소비자다.
- "TC 를 몇 건 뽑을 것인가" 정책 논쟁은 여기서 다루지 않는다. 이 문서는 **표현 가능성**만 연다.

## Context / Constraints

측정한 사실 (`~/Downloads/content-map-vs-sdk-report.md`, `.parallel-inputs/golden-content-map.json`,
`.parallel-inputs/wv-editor-latest.json`, `artel-agent-server/app/specs_v2/model.py`):

| 항목 | 실측 |
|---|---|
| 골든 맵 capability | 18 건 (기존 TC 66 건) |
| `offset` `proof` `resolution` `observable_by` `supportingState` `arms` `repeat` | 골든 맵에 0 회 |
| `methodId` | 18 건 중 2 건만 |
| `callPath` | 18 건 중 1 건만 |
| `scenes[].screens` | 전 씬 `[]` (빈 채로 예약된 자리) |
| 원본 `objects[]` | 27 개 / **20.5 KB** (직렬화 실측) |
| 원본 `types{}` | 493 KB — 이쪽은 옮길 대상이 아님 |
| StoryScene · EndingScene | `capabilities: []` — 조작이 "아무 키를 대사가 끝날 때까지 반복" 이라 v6 스키마에 담을 자리가 없다 |

소유와 기존 백로그 (2026-08-18 확인):

content map 은 **orchestration-server** 소유이며 에픽 [ARTEL-444](https://artel-asm.atlassian.net/browse/ARTEL-444)
아래에 이미 백로그가 있다. 이 기획의 절반은 그 백로그가 덮는다.

| 이 문서의 항목 | 기존 이슈 |
|---|---|
| P1 `observableBy` | ARTEL-452 — watch 목록과 대조해 관측 가능 여부를 정한다 |
| P1 대상을 씬 경로로 해석 | ARTEL-464 |
| P2 `folded` · `alsoReachedBy` | ARTEL-465 — 중복 접기, 접힌 진입점 보존 |
| P3 `objects[].active` 초기 표시 상태 | ARTEL-462 |
| 조건식 수준 갈래 쪼개기 | ARTEL-463 |
| 스키마 본체 | ARTEL-440 (검토 중) · ARTEL-442 (적재) |

덮이지 않아 새로 만든 이슈:

| 항목 | 이슈 |
|---|---|
| P0 `offset` · `methodId`/`callPath` 필수화 · 안정 키 | [ARTEL-470](https://artel-asm.atlassian.net/browse/ARTEL-470) |
| P0 `repeatUntilDone` | [ARTEL-473](https://artel-asm.atlassian.net/browse/ARTEL-473) |
| P2 `proof` 사슬 + 단계별 `resolution` | [ARTEL-478](https://artel-asm.atlassian.net/browse/ARTEL-478) |
| P2 `readiness` 3분할 | [ARTEL-479](https://artel-asm.atlassian.net/browse/ARTEL-479) |

제약:

- 네 이슈 모두 ARTEL-440 (스키마) 이 먼저 자리를 잡은 뒤에 얹힌다. 병합 순서상 440 이 앞이다.
- `.parallel-inputs/golden-content-map.json` 은 적재기 회귀 기준이다. 스키마가 바뀌면 이 파일이 함께 간다.
- 기존 백로그의 실측 수치(407건, `SelectableObject.ChangeSize` 등)는 **다른 게임**의 content map 기준이다.
  이 문서의 수치는 WordVenture 골든 맵 기준이므로 두 숫자를 섞지 않는다.

## 설계 원칙

1. **덧붙이기만 한다.** v6 키는 그대로 두고 새 키를 추가한다. `schemaVersion: 7`.
2. **요약값은 남기고 원값을 옆에 둔다.** `status` 를 지우고 `readiness` 로 바꾸지 않는다. 둘 다 싣고,
   `status` 는 `readiness` 에서 유도된 값이라고 정의한다. `analysisConfidence` 와 `proof` 도 같다.
3. **주소는 `(entryId, offset)` 이 1급이다.** `capabilityId` 는 순번이라 재캡처마다 흔들린다.
   갈래를 펼치면 번호가 통째로 밀리므로, 흔들리지 않는 키를 함께 싣는다.
4. **모르는 값은 `null`, 없는 값은 `[]`.** 둘을 섞지 않는다. "관측 수단이 없음" 과 "관측 수단을 못 알아냄" 은 다른 사실이다.

## 층위 — 이 문서의 JSON 은 DB 의 직렬화 표현이다

아래 확장안은 JSON 으로 적었지만 **실물은 Postgres 스키마**다. 두 층이 함께 간다.

| 층 | 무엇 | 어디 |
|---|---|---|
| 입력 | SDK 근거 문서 | `wv-editor-latest.json` — 이미 값을 갖고 있다. 바꿀 것 없음 |
| 저장 | content_map 테이블 12개 + 뷰 2개 | `V40__create_content_map.sql` (ARTEL-440, **아직 main 에 없음**) |
| 출력 | 조회 응답 · 회귀 정답지 | `golden-content-map.json`, ARTEL-446 조회 API |

JSON 키와 컬럼의 대응은 각 이슈 본문의 "어디를 고치나" 표에 적었다.
컬럼명은 JSON 키를 그대로 쓰지 않는다 — `offset` 은 Postgres 예약어라 `il_offset` 으로 간다.

## 확장안

### P0 — 원본에 이미 있는 3종을 옮긴다 (가장 싸고 가장 크게 남는다)

#### (a) `offset` — 한 메서드 안의 갈래를 구분한다

원본 `types[].effects[].offset` · `types[].calls[].offset` (IL 위치). `specs_v2` 는 `SourceRef.offset` 으로 이미 보존한다.

```jsonc
"then": [
  { "origin": "evidence", "category": "state", "kind": "write",
    "target": "MapMove.position", "detail": "1", "watchable": true,
    "offset": 47 }                                   // 신규
],
"evidence": {
  "entryId": "Assembly-CSharp|MapMove|Update|System.Void()",
  "methodId": "Assembly-CSharp|MapMove|Update|System.Void()",   // 필수화 (현재 2/18)
  "callPath": ["System.Void MapMove::Update()"],                // 필수화 (현재 1/18)
  "branchOffset": 41                                            // 신규: 이 갈래가 갈라진 지점
}
```

없어서 못 하던 것: `CharacterMove` 한 메서드가 capability 1 건으로 눌린다. 기존 TC 는 9 건.

#### (b) `repeatUntilDone` — 반복 구간을 표현한다

원본이 아니라 `specs_v2` 가 이미 만든 값 (`model.py:43`, `discovery.py:1533`, `render.py:202`).
v6 `when.interaction` 은 `click` / `press` / `none` 뿐이라 담길 자리가 없다.

```jsonc
"when": {
  "interaction": "press",
  "inputKey": "AnyKey",
  "inputPhase": "down",
  "control": null,
  "repeatUntilDone": true          // 신규. 기본값 false — v6 소비자는 무시하면 그만
}
```

`interaction` enum 을 건드리지 않고 형제 필드로 붙인다. enum 확장은 소비자를 깨지만 이건 안 깬다.

없어서 못 하던 것: StoryScene · EndingScene 이 통째로 `capabilities: []`. 기존 TC 13 건.

#### (c) `branchFamilies` — 조건 갈래를 합치지 않고 보존한다

원본 `BranchFamily.arms` · `condition_kinds`.

```jsonc
"scenes": [{
  "name": "Map_scene",
  "branchFamilies": [{                                  // 신규 (씬 단위)
    "familyId": "Map_scene:MapMove.Update:key-RightArrow",
    "feature": "CharacterMove",
    "conditionKinds": ["test", "test", "test", "test"],
    "arms": ["cap-10", "cap-10b", "cap-10c", "cap-10d"]  // capabilityKey 참조
  }],
  "capabilities": [{
    "capabilityId": 10,
    "capabilityKey": "cap-10",                           // 신규: 재캡처에 안 흔들리는 키
    "familyId": "Map_scene:MapMove.Update:key-RightArrow" // 신규: 역참조
  }]
}]
```

`capabilityKey` 는 `sha1(entryId + branchOffset + given.tree 정규화)` 앞 8 자 같은 **내용 기반 키**를 제안한다.
정수 `capabilityId` 는 표시용으로 남긴다.

없어서 못 하던 것: `MapMove.position == 0` 갈래만 남고 1·2·3 이 사라진다. 골든 맵 cap 12 는
`given.tree` 가 아예 `null` 이고 자연어에 "village 로 되돌아갈 수 있는 값" 이라고 뭉개져 있다.

**P0 만으로 얻는 것:** 18 → 대략 50 건 대. 세 필드 모두 원본/`specs_v2` 에 이미 존재하므로 새로 만들 분석은 없다.

---

### P1 — 기대 결과를 사람 말로 쓸 수 있게 한다

`watchable: true` 는 "볼 수 있다" 까지만 말하고 **무엇을 보라는지** 말하지 않는다.
실행 에이전트도 사람도 이걸로는 스텝 문장을 못 쓴다.

```jsonc
"then": [{
  "category": "observable", "kind": "scene", "target": "StoryScene",
  "watchable": true,
  "observableBy": "scene-load",     // 신규: scene-load | ui-text | sprite | active-state | audio | none
  "targetLabel": "Play",            // 신규: 원본 objects[].label
  "targetSprite": "Sprite_Start_Button_0"  // 신규: 원본 objects[].sprite / visuals[].role=="sprite"
}],
"when": {
  "control": {
    "path": "Canvas/MapSceneButton",
    "selector": "TitleScene/Canvas[2]/MapSceneButton[1]",  // 신규: 씬 포함 전체 경로
    "label": "Play",                                        // 신규
    "sprite": "Sprite_Start_Button_0",
    "active": true
  }
},
"supportingState": [{                                       // 신규: 원본 SupportingState
  "target": "InteractionLock.IsLocked", "operation": "write", "value": "0",
  "source": { "entryId": "...", "offset": 12 }
}]
```

`observableBy` 는 원본 `visuals[].role` (visual-roles-v1) 과 `effects[].kind` 에서 유도된다. 새 분석이 아니다.

주의: 원본 `objects[].label` 은 27 개 중 2 개에만 있다. `targetLabel` 은 대부분 `null` 이 정상이다.
`null` 을 결함으로 읽지 않도록 스키마 문서에 명시한다.

---

### P2 — 근거 사슬과 3분할 상태

```jsonc
"then": [{
  "resolution": "derived",          // 신규: 단계별 확실성 (exact|derived|ambiguous|unresolved)
  "proof": [                        // 신규: 원본 ProofEdge 사슬
    { "source": "MapMove.Update", "relation": "calls", "target": "MapMove.MoveTo",
      "resolution": "exact", "rule": "direct-call" },
    { "source": "MapMove.MoveTo", "relation": "writes", "target": "MapMove.position",
      "resolution": "derived", "rule": "field-store-from-arg" }
  ]
}],
"readiness": {                      // 신규: status 한 값으로 눌려 있던 세 축
  "actionability": "actionable",
  "observability": "indirect",
  "applicability": "applies"
},
"status": "runnable",               // 유지 — readiness 에서 유도된 값이라고 정의
"folded": false,                    // 신규: 경로를 접었는지
"evidence": {
  "analysisConfidence": "derived",  // 유지 — proof 사슬 resolution 의 최솟값이라고 정의
  "alsoReachedBy": [                // 신규: 같은 기능의 다른 진입점
    "Assembly-CSharp|Map.MapUI|OnMoveButton|System.Void()"
  ]
}
```

`proof` 는 부피가 크다. 기본은 싣되, 소비자가 끌 수 있도록 생성 옵션 `includeProof` 를 둔다.
"틀렸을 때 어느 단계가 틀렸는지" 를 되짚는 용도이므로 **디버깅 경로에서 제일 값이 크다.**

`readiness` 를 넣는 이유는 하나다. 지금은 "실행은 되는데 관측이 안 됨" 과 "이 빌드엔 적용 안 됨" 이
둘 다 `status` 한 값으로 눌려 구분되지 않는다. 앞은 TC 로 쓸 수 있고 뒤는 쓸 수 없다.

---

### P3 — 씬 오브젝트 트리 (`screens[]` 의 빈자리를 채운다)

v6 는 **클릭된 컨트롤 6 개**만 싣는다. "버튼이 화면에 보이는가" 류의 표시 확인 TC 는 근거가 통째로 없다.

```jsonc
"scenes": [{
  "name": "TitleScene",
  "objects": [{                                   // 신규 (기존 screens[] 는 빈 채 유지 또는 폐기 예고)
    "path": "Canvas/MapSceneButton",
    "selector": "Canvas[2]/MapSceneButton[1]",
    "active": true,
    "label": null,
    "sprite": "Sprite_Start_Button_0",
    "visuals": [{ "role": "sprite", "value": "Sprite_Start_Button_0", "type": "UnityEngine.UI.Image" }],
    "components": [{
      "type": "UnityEngine.UI.Button",
      "calls": [{ "event": "m_OnClick", "targetType": "Scenes.TitleSceneManager", "method": "InitPlayerData" }]
    }]
  }]
}]
```

부피 걱정은 실측으로 해소된다. WordVenture 전체 `objects[]` 가 **20.5 KB** 다.
옮기지 말아야 할 것은 `types{}` (493 KB) 쪽이고, 그건 이 확장의 대상이 아니다.

`components[].calls[]` 는 **인스펙터 배선**이다. 어떤 컨트롤이 어느 코드에 붙는지를 이것 없이는 못 따라간다.
지금은 `evidence.bindingEvent` 로 이벤트 이름 한 조각만 남는다.

---

### 요약: 원본 → v7 자리 대응

| 원본 필드 | v7 자리 | 단계 |
|---|---|---|
| `effects[].offset` · `calls[].offset` | `then[].offset` · `evidence.branchOffset` | P0 |
| `Trigger.repeat_until_done` | `when.repeatUntilDone` | P0 |
| `BranchFamily.arms` · `condition_kinds` | `scenes[].branchFamilies[]` · `capabilities[].familyId` | P0 |
| `methodId` · `callPath` | `evidence.*` (필수화) | P0 |
| `Assertion.observable_by` | `then[].observableBy` | P1 |
| `Assertion.target_label` · `target_sprite` | `then[].targetLabel` · `targetSprite` | P1 |
| `objects[].selector` · `label` | `when.control.selector` · `label` | P1 |
| `SupportingState` | `capabilities[].supportingState[]` | P1 |
| `ProofEdge` (+ `rule`) | `then[].proof[]` | P2 |
| `Resolution` (단계별) | `then[].resolution` | P2 |
| `actionability` · `observability` · `applicability` | `capabilities[].readiness{}` | P2 |
| `Contract.folded_path` | `capabilities[].folded` | P2 |
| `alsoReachedBy[]` | `evidence.alsoReachedBy[]` | P2 |
| `objects[]` (+`active`, `components[].calls[]`) | `scenes[].objects[]` | P3 |

## Approach (Checklist)

- [x] **Step 0: Recon** — 소유 확인 완료. `artel-orchestration-server`, 에픽 ARTEL-444.
      기존 백로그와 대조해 덮이지 않은 4건만 이슈로 끊었다.
- [ ] **Step 1: V40 상태 확인** — `V40__create_content_map.sql` 이 main 에 머지됐는지 본다.
      **전이면 V40 본문에 컬럼을 넣는다. 후면 V41 로 `ALTER TABLE` 한다.** 이 갈림이 네 이슈 모두의 전제다.
- [ ] **Step 2: enum 합의** — `analysis_confidence` (`verified|derived|partial`) 와 `specs_v2` 의
      `Resolution` (`exact|derived|ambiguous|unresolved`) 중 어느 어휘로 갈지 정한다. ARTEL-478 의 선행 조건.
- [ ] **Step 3: 골든 케이스 선행 작성** — `.parallel-inputs/golden-content-map.json` 을 손으로 갱신.
      적재기보다 **먼저** 정답을 못 박아야 회귀 기준이 선다. Map_scene `CharacterMove` 9 갈래,
      StoryScene · EndingScene 반복 조작을 실제로 적어 스키마가 담기는지 검증한다.
- [ ] **Step 4: 마이그레이션 + 엔티티** — 이슈 단위로. ARTEL-470 → ARTEL-473 → ARTEL-479 → ARTEL-478 순.
      앞의 둘이 건수를 늘리고, 뒤의 둘이 그 건수에 판정과 근거를 붙인다.
- [ ] **Step 5: 적재기(ARTEL-442) 반영** — 새 컬럼을 채운다. 못 채우면 `gaps` 에 사유를 남긴다.
- [ ] **Step 6: 뷰 갱신** — `v_content_map_capability` 에 노출할 것만 얹는다. 사슬은 조인하지 않는다(행 곱셈).
      `v_spec_gap` 의 분기가 바뀐 컬럼을 읽는지 확인한다.
- [ ] **Step 7: 건수 대조** — 씬별 `capability` 행 수를 기존 TC 66 건과 대조.

## Validation

- **Commands to run:**
  - `artel-orchestration-server` 에서 `./mvnw test` — `ContentMapSchemaTest` 가 불변식을 잡는다
  - 마이그레이션 적용 후 `status` 와 세 축이 어긋난 행을 세는 질의 (0건이어야 한다)
  - 적재기 회귀: 골든 맵을 정답으로 적재 결과 대조
  - 건수 대조: 씬별 `capability` 행 수 vs 기존 TC 66 건
- **Expected output:**

| 씬 | 기존 TC | v6 실측 | v7 목표 | 무엇이 열어주나 |
|---|---:|---:|---:|---|
| TurnBattleScene | 24 | 5 | 20+ | offset · arms |
| Map_scene | 21 | 5 | 18+ | offset · arms |
| EndingScene | 7 | 0 | 7 | repeatUntilDone |
| StoryScene | 6 | 0 | 6 | repeatUntilDone |
| TitleScene | 5 | 5 | 5 | — |
| GameClearScene | 3 | 2 | 3 | arms |
| **합계** | **66** | **18** | **60±** | |

  - v6 소비자를 v7 문서에 물려도 예외 없이 동작 (덧붙이기 검증)
  - content map 1 개 크기: 현재 29 KB → P3 포함 200 KB 미만

## Risks & Rollback

- **부피:** `proof` 사슬이 capability 당 수 단계씩 붙으면 커진다. 완화: `includeProof` 생성 옵션, P2 를 마지막에서 두 번째로 배치.
- **`capabilityId` 불안정:** 갈래를 펼치면 번호가 밀려 기존 참조가 전부 깨진다.
  **P0 에서 `capabilityKey` 를 같이 넣지 않으면 P0 자체가 파괴적 변경이 된다.** 이 순서를 지킨다.
- **갈래 폭발:** 조건이 많은 메서드에서 arms 가 과하게 늘 수 있다. 완화: `branchFamilies` 로 묶어 두었으므로
  소비자가 family 단위로 접어 볼 수 있다. 생성기에서 자르지 않는다 — 자르면 지금 문제의 반복이다.
- **`objects[]` 규모:** WordVenture 는 27 개지만 큰 게임은 다르다. 완화: 이미 SDK 가 visual-roles 로 걸러낸
  결과만 싣는다. 상한 초과 시 `gaps` 에 `objects-truncated` 를 남긴다 — **조용히 자르지 않는다.**
- **Rollback:** 생성기를 `schemaVersion: 6` 산출로 되돌린다. 적재기는 Step 3 에서 tolerant 로 만들어 두므로
  소비자 쪽 롤백은 필요 없다.

## Open Questions

- `capabilityKey` 해시 입력에 무엇을 넣을지 (entryId + branchOffset + 조건 정규화형) 합의 필요.
  ARTEL-465 가 필요로 하는 "같은 행동의 갈래를 묶는 키" 와 같은 뿌리이므로 한 번에 정한다.
- 소비자는 `branchFamilies` 를 씬 단위 배열로 받는 쪽과 capability 를 평면으로 펼친 쪽 중 어느 쪽이 편한가.
- `screens[]` (전 씬 `[]`) 는 `objects[]` 로 대체하고 폐기하는가, 다른 용도로 예약된 자리인가.
- `then[].proof` 를 기본 포함할지, 옵션으로 둘지.
