# 샘플 게임 판정 정확도

ArcaneCasters, Living Dead, Match3, Survivors, WordVenture의 TC를 게임당 20개씩 준비합니다. 같은 시작 상태와 조작으로 결과를 확인하는 10쌍을 구성합니다. 쌍마다 기대 결과 하나는 참이고 하나는 거짓입니다. 정답표의 관찰과 근거는 소스에서 작성했으므로 측정 전에 동일한 빌드에서 두 주장을 직접 대조합니다.

1. 샘플의 커밋, 빌드, 계정, 언어, 저장 데이터 상태를 기록합니다. 같은 쌍의 두 TC는 동일한 시작 상태에서 각각 재현합니다. 실행 전에 사람이 확인한 실제 관찰과 증거를 채점용으로 보관합니다.
2. 게임별 `cases.json`만 `artel case create --project <id> --file cases.json --json`으로 등록합니다. 반환된 순서와 `tc`로 매핑을 저장합니다. `answer-key.json`과 사람의 관찰 결과는 에이전트 입력, knowledge, content map에 넣지 않습니다.
3. 각 TC를 독립 실행하고 해당 결과의 명시적인 `PASS` 또는 `FAIL`과 증거를 수집합니다. 전제 조건에 도달하지 못하면 `BLOCKED`, 실행 오류는 `ERROR`로 기록합니다. 같은 쌍의 이전 실행 기록을 다음 실행에 전달하지 않습니다.
4. 판정 파일은 별도 디렉터리에 게임별 `<게임 디렉터리명>.json`으로 저장합니다. 각 파일은 `[{"tc": 10001, "verdict": "PASS"}]` 형태입니다. `python benchmarks/sample-game-accuracy/score.py <판정 디렉터리>`로 게임별 결과를 계산합니다.

정답이 거짓인데 에이전트가 PASS를 주면 오탐입니다. 정답이 참인데 FAIL을 주면 미탐입니다. 오탐률은 `FP / (FP + TN)`, 미탐률은 `FN / (FN + TP)`입니다. 20개 모두 PASS 또는 FAIL을 받은 게임만 비율을 출력합니다. 나머지는 집계와 판정 완료율을 확인할 수 있습니다.

WordVenture의 현재 커밋은 `Packages/manifest.json`에서 `file:../../../Packages/kr.artel.sdk`를 참조합니다. `samples/word-venture`에서 열려면 상위 저장소의 `Packages/kr.artel.sdk`에 SDK 패키지가 있어야 합니다. Windows에서 로컬 테스트를 실행할 때는 해당 경로에 `artel-sdk/Packages/kr.artel.sdk`를 가리키는 junction을 사용할 수 있습니다. 테스트에 사용한 SDK 커밋을 게임 빌드와 함께 기록합니다.
