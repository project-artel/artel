# content map 과 기획서 지식을 2×2 로 재는 벤치마크

- Date: 2026-09-04
- Status: 설계 (스위치 구현 중, 실행 전)
- 대상 저장소: `artel-orchestration-server` · `artel-agent-server` · `admin-page`
- 시나리오 정의: `benchmarks/wordventure/` (ARTEL-807 이 `origin/main` 에 올려 뒀다). 초안이던 워크스페이스 루트의 `benchmark-source.md` 는 그것으로 대체됐다
- 기획서 원본: `.plan/assets/wordventure/wordventure-기획서.pdf`

## 재려는 것

QA agent 에게 런 시작 전에 사전 정보를 주면 실제로 더 잘하는가. 사전 정보는 두 종류이고,
둘을 각각 끄고 켜서 네 arm 을 만든다.

| arm | content map | 기획서 지식 | 무엇을 답하나 |
|---|---|---|---|
| A. 맨몸 | off | off | 아무것도 안 주면 어디까지 가나. 나머지 셋의 기준선 |
| B. 지도만 | on | off | 조작할 수 있는 것의 목록이 도움이 되나 |
| C. 기획서만 | off | on | 게임의 규칙을 글로 알려 주면 도움이 되나 |
| D. 둘 다 | on | on | 둘이 겹치나, 아니면 서로 다른 구멍을 메우나 |

## 왜 한 축씩 재면 안 되나

두 축이 **서로 다른 종류의 정보**를 담고 있고, 그래서 각각의 효과를 더한 것보다 둘 다 켠
쪽이 나을 수 있다. 그것을 보려면 네 칸이 다 필요하다.

근거는 이 게임에 이미 있다. `benchmarks/wordventure/game-facts.md` 가 적어 둔 두 사실이다.

- **속성 상성표는 `Magic Affinity Table.asset` 에 있고 어느 스캔에도 안 잡힌다.** content map
  은 정적 분석이 읽어 낸 것을 담는 곳이라, 이 표를 담을 방법이 없다. agent 는 때려 보고 HP 를
  읽어야만 안다.
- **보스 스테이지는 한 속성으로 밀 수 없다.** 앞 세 웨이브가 `Holy` 타입이라 `Holy` 로 때리면
  −2.0 배율로 **회복시킨다.** 최종 보스 `SlimeKing2` 는 `Undead` 80HP 라 `Holy` 면 두 방,
  나머지는 여섯 방이다. 상성을 실제로 학습하지 않으면 못 넘는다.

반대로 content map 은 기획서가 못 주는 것을 준다 — 어느 `screen` 의 어느 control 이 무엇을
하는지, 실측 빌드 기준으로. 기획서는 만들려던 게임을 적은 것이고 지도는 만들어진 게임을 읽은
것이라, 둘은 원리적으로 다른 것을 안다.

**그래서 사전 예측을 여기 적어 둔다.** 결과를 보고 나서 세운 설명은 무엇이든 맞출 수 있으므로,
돌리기 전에 적어야 값이 있다.

- B(지도만)는 초반이 빠르고 **보스에서 막힌다.** 조작은 아는데 상성을 모른다.
- C(기획서만)는 초반이 느리고 보스에는 닿으면 넘는다. 규칙은 아는데 어느 버튼인지 모른다.
- D 는 둘의 단순 합보다 낫다. 서로의 구멍이 다르기 때문이다.
- A 는 L1(상세 지시)에서는 B·C 와 큰 차이가 없고 **L3(추상)에서 벌어진다.** 지시가 촘촘하면
  사전 정보가 할 일이 없다.

이 예측 중 어느 것이 빗나가는지가 이 측정의 실제 산출물이다.

## 두 축의 스위치

### 지식 축 — `knowledge_mode` (이미 있다)

`KnowledgeMode`(ARTEL-256)가 `learning` · `frozen` · `off` 셋을 이미 갖고 있다. 새로 만들 것이
없다.

### content map 축 — `content_map_mode` (신설 중)

`knowledge_mode` 와 **같은 자리에 같은 모양으로** 만든다. `qa_try.run_config` 에 남고,
`SceneContextService.read` 가 막는다 — 그 메서드는 이미 `qaTryId` 를 받아 그 런의 knowledge
scope 를 읽고 있어서, 같은 행의 `run_config` 를 읽는 것이 자연스럽다.

**agent-server 는 한 줄도 안 고친다.** `KnowledgeMode` 의 KDoc 이 그 이유를 이미 논증해 뒀고,
그대로 성립한다 — agent 쪽 프롬프트나 tool 목록을 arm 마다 바꾸면 달라진 변수가 "사전 정보의
유무" 하나가 아니게 된다. 서버에서 막으면 arm 마다 agent 프롬프트가 바이트 단위로 동일하고,
남는 차이는 `/scene-context` 응답이 비어 있다는 것뿐이다.

`off` 는 **`evidence` 를 한 번도 올리지 않은 빌드와 같은 답**을 낸다. 없는 상태를 흉내 내는
것이 아니라, `InternalSceneContextController` 가 이미 정상으로 문서화해 둔 그 답을 그대로
낸다 — `contentMapId` 가 null, `capabilities` 와 `notAStepCapabilities` 가 빈 리스트,
`knownToContentMap` 이 false.

**앵커 지식은 `off` 에서도 그대로 나온다.** `/scene-context` 응답은 두 반쪽이 붙어 있는데,
`capability` 는 content map 에서 오고 `knowledge` 는 지식창고에서 온다. 여기서 앵커 지식까지
함께 지우면 두 축이 섞여 2×2 가 성립하지 않는다. 지식 쪽은 `knowledge_mode` 가 따로 끈다.

### 두 축 모두 `frozen` 이 필요하다

반복 측정이 성립하려면 arm 이 자기가 읽는 것을 바꾸면 안 된다.

- `knowledge_mode=learning` 인 런은 지식을 쓴다. 두 번째 런의 출발점이 첫 번째와 달라진다.
- content map 도 같다. `record_capability_verdict` 와 `record_new_capability` 가 지도를 바꾸므로,
  B·D arm 을 두 번 돌리면 두 번째가 첫 번째의 결과를 읽는다.

그래서 **측정 런은 전부 읽기 전용이다.** 지도와 지식을 실제로 채우는 것은 측정과 별개의
런에서 하고, 측정은 고정된 출발점에서 돈다.

이것이 `ContentMapMode` 에 `frozen` 이 필요한 이유다. `on`/`off` 둘만으로는 "읽되 쓰지 않는다"
를 말할 수 없다.

## arm 설정표

| arm | `content_map_mode` | `knowledge_mode` | knowledge scope |
|---|---|---|---|
| A. 맨몸 | `off` | `off` | — (검색이 언제나 빈 결과다) |
| B. 지도만 | `frozen` | `off` | — |
| C. 기획서만 | `off` | `frozen` | `PRODUCTION` |
| D. 둘 다 | `frozen` | `frozen` | `PRODUCTION` |

`knowledge_mode=off` 인 A·B 는 scope 가 무엇이든 검색이 빈 결과라, 별도의 빈 scope 를 만들 필요가
없다. C·D 가 `PRODUCTION` 인 것은 문서에서 나온 지식이 거기로만 들어가기 때문이다 — 아래
"지금 없는 것" 3번 참조. 그 제약 때문에 C 를 "기획서만" 이라고 부를 수 있는지는 운영
지식창고를 세어 본 뒤에 정한다.

나머지 축 — model, reasoning, `prompt_version`, `agent_arch` — 은 **네 arm 이 전부 같아야
한다.** 하나라도 다르면 차이가 어느 축에서 온 것인지 말할 수 없다.

## 무엇을 돌리나

`benchmarks/README.md` 가 난이도 사다리를 test run 넷으로 쪼개 뒀다.

| test run | 시나리오 | 스텝 | 실패 기대 |
|---|---|---|---|
| 9011 | 프로브 — 세이브와 리셋 | 9 | 1 |
| 9012 | L1 상세 — 평원 클리어 | 24 | 6 |
| 9013 | L2 중간 — 평원 + 바다 | 9 | 0 |
| 9014 | L3 추상 — 엔딩까지 | 14 | 2 |

**프로브(9011)는 이 측정에서 뺀다.** 재는 것이 세이브 규칙 관찰이라 사다리와 별개 축이고,
사전 정보와 상관이 없다. 게다가 첫 스텝이 "한 번도 플레이한 적 없는 설치"를 전제해서 arm 마다
`PlayerPrefs` 를 비워야 하는데, 그 비용이 이 측정에 기여하는 것이 없다.

남는 셋(9012·9013·9014)은 타이틀의 새 게임 버튼이 세이브를 먼저 지우므로 서로 순서가 없다.

**파일럿: 4 arm × 3 run = 12 런, 각 1회.** 반복은 파일럿 다음에 정한다. LLM 은 확률적이라 같은
설정도 런마다 다르고, 반복 횟수를 미리 정하면 신호 크기를 모른 채 비용을 정하는 것이 된다.
파일럿에서 arm 간 차이가 런 간 흔들림보다 큰지 보고, 그 다음에 몇 번 반복할지 정한다.

가장 먼저 반복해야 할 것은 **9013(L2)** 이다. `benchmarks/README.md` 가 자율성을 9012 와 9013 의
평원 구간 차이로 읽기로 했고, 그 비교가 이 측정의 핵심 지표다.

## 측정 항목

측정 항목은 `benchmark-source.md` 초안에만 있고 `benchmarks/` 로 옮겨지지 않았다. 그 다섯을 그대로 쓴다.

- **깊이** — 완료한 스텝 번호와 도달한 스테이지
- **비용** — 소요 시간, tool 호출 수, token, 압축 횟수
- **정직성** — 보고한 판정 vs `expected_passed` 라벨. 실패 기대 스텝을 통과라고 보고하면 미탐
- **자율성** — 9012 와 9013 의 평원 구간 결과 차이
- **지식** — 상성을 `record_knowledge` 로 남겼는지, 보스에서 그 지식을 실제로 썼는지

content map 축 때문에 둘을 더한다.

- **지도 사용률** — `list_scene_capabilities` 를 몇 번 불렀나. 씬 문맥 블록에 실린 `capability`
  중 실제로 시도한 것이 몇 개인가. 블록을 읽고도 안 쓰면 정보가 아니라 부피다.
- **지도 기여** — `record_capability_verdict` 로 확인된 행이 몇 개 늘었나. 프롬프트 v15 가
  실측 수치를 적어 뒀다 — `artel_integration` 빌드의 `capability` 472 행 중 `verification =
  'confirmed'` 가 2 행이다. 런이 그 수를 올리는지가 지도가 살아 있는지의 지표다.

  단, 측정 런은 `frozen` 이라 실제로 쓰지 않는다. 이 항목은 쓰기를 켠 별도 런에서 재거나,
  런이 **쓰려고 시도한** 호출 수로 센다. 어느 쪽으로 할지는 파일럿에서 정한다.

## 실험 묶음 이름

arm 은 `run_config` 가 이미 말한다 — `content_map_mode=frozen` · `knowledge_mode=off` 가 곧
"지도만" arm 이다. 그것을 이름에 또 적으면 같은 사실이 두 군데 적히고 언젠가 어긋난다.

빠져 있는 것은 arm 이 아니라 **묶음**이다. 같은 설정으로 다음 달에 다시 돌리면 config 는 같은데
다른 실험이다. 그래서 `qa_run` 에 자유 문자열 `label` 하나를 둔다. 거기 적는 것은 실험 이름
뿐이다 — `content-map-2x2-파일럿`. arm 은 적지 않는다.

화면의 입력은 자유 입력이 아니라 **이미 쓰인 `label` 목록에서 고르는 자리**로 둔다. 자유
문자열의 실질 위험은 `content map 1차` 와 `content map 1차 실험` 이 두 칸으로 갈리는 것인데,
고르게 만들면 tag 체계를 만들지 않고도 그것이 막힌다.

화면에서는 `label` 로 묶고 config 축으로 쪼갠다. 그러면 한 실험의 네 arm 이 한 표에 나란히
선다.

## 지금 없는 것

측정을 시작하기 전에 이 넷이 해결돼야 한다.

1. **`content_map_mode`** — `artel-orchestration-server` 에 구현 중.
2. **`qa_run.label` 과 화면 필터** — `admin-page` 의 test run 필터와 같은 자리에 함께 붙인다.
   지금 `GET /api/qa-stats` 는 test run 넷을 구분하지 못하고 한 덩어리로 접는다.
3. **기획서를 지식 항목으로 넣기** — 서버 경로는 **이미 다 있다.** 새로 만들 것이 없다.

   ```
   POST /api/projects/{projectId}/documents/upload-url   (presigned URL 발급)
   → S3 업로드
   → POST /api/projects/{projectId}/documents            (등록)
   → DocumentKnowledgeExtractionService.extractAndStoreForDocument
   → agent-server 의 추출 호출
   → KnowledgeService.store(source = DOCS)
   ```

   그래서 `artel-cli` 에 붙일 명령은 **이 두 엔드포인트를 감싸는 client 하나**이지 서버 작업이
   아니다. 다만 그 저장소가 지금 브랜치 일곱 개(ARTEL-782 · 789 · 798 · 799 · 800 · 801 · 804)로
   동시에 만들어지는 중이라 지금 끼우면 부딪힌다. 그 브랜치들이 정리된 뒤에 붙인다. 그때까지는
   화면이나 `curl` 로 올려도 결과가 같다.

   **제약 하나가 축의 이름을 바꾼다.** 문서에서 나온 지식은 언제나
   `KnowledgeScope.PRODUCTION` 으로 들어간다. `DocumentKnowledgeExtractionService` 가 그렇게
   못박아 뒀고 이유도 적혀 있다 — "사람이 올린 문서에서 나온 지식은 언제나 운영 지식창고의
   것이다(ARTEL-256). 실험 arm이 문서를 올리는 경로는 없고, 있어도 그 문서는 프로젝트의
   사실이지 그 arm의 산물이 아니다."

   그래서 **기획서만 든 scope 를 만들 수 없다.** C·D arm 이 읽는 것은 운영 지식창고이고, 거기에는
   그동안 QA 런이 써 넣은 것도 함께 있다. 그 상태로 재면 C 는 "기획서만" 이 아니라 "기획서 +
   과거 런이 배운 것" 이다.

   측정 전에 운영 지식창고에 이 프로젝트 지식이 무엇이 얼마나 있는지 먼저 세어라. 그 다음
   둘 중 하나다.

   - 비어 있거나 무시할 양이면 그대로 간다.
   - 아니면 **축 이름을 사실대로 바꾼다** — "기획서 지식" 이 아니라 "지식창고". 이 설계 결정을
     측정 편의를 위해 뒤집지 마라. 축 이름을 고치는 쪽이 옳고, 그래도 재려던 질문("사전
     지식이 도움이 되나")은 그대로 성립한다.
4. **WordVenture 빌드에 content map 이 실제로 채워져 있는지 확인** — `evidence` 가 안 올라간
   빌드면 `on` 과 `off` 가 같은 런이 되고, 측정 전체가 아무것도 재지 못한다. **이것이 가장 먼저
   확인할 것이다.** stage 기준 WordVenture 는 project 5 다 (project 1 도 이름이 같지만
   `deleted_at` 이 찍혀 있다).

## 실행 전 준비

`benchmarks/README.md` 의 준비 사항이 그대로 유효하다.

- **SDK 가 빌드 씬에 없다.** `ArtelManager` 가 `Assets/Scenes/Test/RemoteControlPoC.unity` 에만
  있고 그 씬은 Build Settings 에 없다. `ArtelManager` + `ArtelOverlayController` 를
  `TitleScene`(build index 0)에 넣어야 한다. `DontDestroyOnLoad` 라 한 번만 넣으면 된다.
- 네 arm 의 model · reasoning · `prompt_version` · `agent_arch` 를 같게 맞춘다.

## 주의: 튜토리얼이 런을 영구 정지시킬 수 있다

`TutorialCondition` 의 `FLAG_001`~`014` 가 첫 전투 진행에 물려 있다. 가장 위험한 지점은 발동
직후다 — 슬롯이 비워지며 `FLAG_008` 대사가 뜨고 `InteractionLock.IsLocked = true` 가 되는데,
`CastSpell` 은 `while (target == null)` 로 무한 대기 중이고 적을 클릭해도
`SelectableObject.OnMouseDown` 이 걸러 낸다. `FLAG_009` · `010` · `011` 까지 넘겨야 클릭이
먹는다.

여기서 멈춘 런은 arm 의 성능이 아니라 이 구간에 걸린 것이다. **깊이를 읽을 때 이 지점에서
멈춘 런을 따로 세어라.** 네 arm 에 고르게 발생하면 노이즈이고, 한 arm 에 몰리면 그것 자체가
결과다 — 사전 정보가 이 함정을 넘게 해 줬다는 뜻이므로.
