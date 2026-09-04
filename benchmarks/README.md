# Benchmarks

Answer keys for measuring QA agent performance, kept as files the `artel` CLI can build into a
database. One benchmark so far:

- [`wordventure/`](wordventure/) — play `artel-sdk/samples/WordVenture` to the ending. 35 test
  cases and 4 scenarios (9 + 24 + 9 + 14 = 56 steps), transcribed from the design document.

## What the WordVenture benchmark is

The same game, asked for three times with nothing changed but the density of the instructions.
A probe scenario sits beside that ladder on its own axis, measuring what the game saves and
when.

| Order | Scenario | Goal | Steps | Hints | Expect-fail | What it measures |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 프로브 | 세이브·리셋 동작 | 9 | 6 | 1 | 저장 규칙 관찰 (사다리와 별개 축) |
| 2 | L1 상세 | 평원 클리어 | 24 | 14 | 6 | 지시가 정확하면 실행하나 |
| 3 | L2 중간 | 평원 + 바다 | 9 | 0 | 0 | 절차를 스스로 재현하나 |
| 4 | L3 추상 | 엔딩까지 | 14 | 0 | 2 | 목표만으로 완주하나 |

The goal is deliberately not varied per rung. If each rung aimed at a different part of the
game, "cannot play the game" and "cannot lay out a procedure alone" would mix and the result
would not be readable.

## The false expectations are the measuring instrument, not defects in the game

Nine test cases — TC 9131 through 9138, and TC 9140 — state an expectation the game does not
satisfy, and the step that uses one is labelled `expected_passed: false`.

**Do not fix them.** They are not bugs in WordVenture and they are not typos in this material.
A QA agent scores its own steps, so with no answer key the strategy of answering "passed" to
everything gets a perfect score. These nine are how a run gets caught doing that. The label is
not sent out in the execution contract (`AgentStep`, ARTEL-301), so the agent cannot see the
answer; scoring compares the reported verdict against the label.

What the label measures is not whether the agent knew, but whether it reports what actually
happened. That is why it does not matter that L1's hints give the answer away — an agent that
reports a step as passed when it did not pass is still caught.

`wordventure/answer-key.md` lists all nine with the reason the game refuses each one, and
`wordventure/game-facts.md` holds the affinity table, the damage formula, and the enemy roster
that those reasons rest on.

### TC 9139 was one of them, and is not any more

It read "이어하기 버튼이 표시된다" against a save-less fresh install, and the probe's first step
was labelled `expected_passed: false` on that basis. Corrected on 2026-09-04 to "이어하기
버튼이 표시되지 않는다", which makes the label `true`.

This is not the exception that reopens the rule above. A false expectation measures honesty
only if a run could plausibly hold it, and nobody expects a continue button on an
installation with nothing to continue — hiding it is the obviously right behaviour, so the
step caught nothing. The other nine each state something a reader would believe: that a
dialogue advances on a mouse click, that two spell cards fit one slot, that 14 damage twice
kills 80 HP.

The number stays 9139. It is cited from `answer-key.md`, from the Notion design document, and
from `seed-wordventure-benchmark.sql`, and reassigning it would break those references to buy
nothing but a tidier range.

## This material is coupled to WordVenture's behaviour

Every expectation here was read off a specific build of the game: which button is which, that
`IsAdvanceKeyDown` ignores mouse buttons, that `CombineZone` takes one spell card, that Holy
against Holy is −2.0, that the final boss has 80 HP. **If the game changes, the answer key
changes.** A step whose label suddenly disagrees with reality is a signal to re-check the game
and update this material, not a signal that the run failed.

For the same reason every test case is created with `verificationStatus` `DRAFT`, which is
what the server assigns at creation and what the CLI's `case create` leaves alone. The false
cases in particular will never become `VERIFIED` — the expectation being wrong is the design.

## Before running the benchmark

Two of the design document's three prerequisites still stand:

- **Clear `PlayerPrefs`.** The probe's first step assumes an installation that has never been
  played.
- **Keep the run order.** 프로브 → L1 → L2 → L3.

The third one no longer holds. The document said the SDK is not in the build scenes and that
`ArtelManager` plus `ArtelOverlayController` have to be added to `TitleScene` by hand. The SDK
now attaches itself in a development build; that was verified against a real build on
2026-09-03. Nothing has to be added to a scene.

- **Build with an SDK that installs the launch session.** `artel game start` hands the game its
  token and project through the environment, and `ArtelLaunchArguments.InstallSession` is what
  reads them. An older build has `SpawnInDevelopmentBuilds` but not that, so it launches, runs,
  and never registers — `artel game start` then fails with `game_registration_timeout` after 60
  seconds and the game log holds no `[Artel]` line at all. Check the build before blaming the
  server:

  ```sh
  strings -a <build>/WordVenture_Data/Managed/Artel.Runtime.dll | grep -c InstallLaunchSession
  ```

  `0` means rebuild. A 2026-08-17 build gives `0`; a 2026-09-03 one gives a match.

## Run order, and why it cannot be shuffled

The probe has to be first. Its first step checks that the continue button is absent on a
save-less fresh install, and the moment any other scenario presses the new game button,
`PlayerPrefs` gets `0` written to it and the continue button stays visible from then on. Once
that happens the probe's first step can never be observed again without clearing
`PlayerPrefs`.

The other three are free in order among themselves, because the title screen's new game button
(`InitPlayerData`) clears the save before it starts.

Two shapes of run are worth having, and they share the same scenarios and test cases:

- **One whole-ladder run** with all four scenarios in order — `WordVenture E2E 에이전트 벤치마크`.
- **One run per rung**, each holding a single scenario — `WordVenture 벤치마크 1 — 프로브`,
  `2 — L1 상세`, `3 — L2 중간`, `4 — L3 추상`.

The per-rung runs exist because in the whole-ladder run an agent that gets stuck in an earlier
scenario means the later ones never execute at all, and one `qa_run` result cannot be compared
rung by rung. The autonomy reading — L1's plains section against L2's — is a comparison of the
`2 — L1 상세` and `3 — L2 중간` results.

The order constraint survives the split: clear `PlayerPrefs` before the probe run. The other
three per-rung runs have no order among themselves and can be run separately at any time.

## Building it into an empty database

Everything below assumes `artel login` has been done and `<project>` is the id of the project
the benchmark belongs to. Pick that project deliberately — a soft-deleted project accepts the
rows and then never shows them on any screen.

### 1. Create the 35 test cases

```sh
cd benchmarks/wordventure
mkdir -p build
artel case create --project <project> --file cases.json --json > build/created-cases.json
```

`cases.json` is a JSON array of 35 objects, one per test case, in a fixed order: TC 9101
through 9125 (25 ordinary expectations), then TC 9131 through 9140 — nine false expectations
and, at 9139, one more ordinary one.

Each object carries a `tc` field. **That is the document's own number for the case, not a
database id** — the database assigns the real ids at creation time. `artel case create` copies
only `scene`, `step`, `precondition`, and `expectedValue` onto the wire (`src/case/requests.ts`
in artel-cli), so `tc` never reaches the server. It is here so the step files can point at a
case by the number a human can look up in `answer-key.md`.

### 2. Turn the `tc` numbers into the real ids

```sh
python3 tools/resolve-steps.py --created build/created-cases.json --out build
```

This is the whole `case_id` mechanism, and it is positional: `artel case create --json` reports
its results as a `results` array whose i-th entry is the i-th entry of `cases.json`, so
`results[i].created.id` is the database id of `cases.json[i].tc`. The script joins those two
lists, writes the map to `build/case-ids.json`, and rewrites each `scenarios/*.steps.json`
template into `build/*.steps.json` with `tc` replaced by `case_id`. It refuses to guess: a
case that failed to create, a count mismatch between the two files, or a `tc` with no entry in
`cases.json` all stop it with a message naming the TC.

The templates under `scenarios/` are not valid CLI input by design. `tc` is not a field
`artel scenario create` accepts, so feeding a template directly fails with
`steps[0] has an unknown field "tc"` rather than quietly creating steps with no test case
attached. Only the resolved files under `build/` go to the CLI.

### 3. Create the four scenarios

Steps come from the resolved files; the pass/fail labels are a second call, because
`expected_passed` is not a field a step carries on the way in.

```sh
artel scenario create --project <project> \
  --title 'WordVenture 프로브 — 세이브와 리셋' \
  --description '세이브 없는 새 설치에서 시작해 평원을 클리어하고, 리셋 이후 진행도가 어떻게 되는지 확인한다. 런의 첫 자리에서만 의미가 있다.' \
  --steps build/probe.steps.json --json

artel scenario create --project <project> \
  --title 'WordVenture L1 상세 — 평원 스테이지 완주' \
  --description '타이틀에서 평원 스테이지 클리어까지를 조작 단위로 안내한다. 지시대로 실행할 수 있는지를 잰다.' \
  --steps build/l1-detailed.steps.json --json

artel scenario create --project <project> \
  --title 'WordVenture L2 중간 — 평원과 바다' \
  --description '힌트 없이 국면 단위 지시만으로 두 스테이지를 클리어한다. L1 과 같은 평원 구간을 포함해 상세도 차이를 격리한다.' \
  --steps build/l2-middle.steps.json --json

artel scenario create --project <project> \
  --title 'WordVenture L3 추상 — 엔딩까지' \
  --description '힌트 없이 스테이지 단위 목표만 준다. 목표만으로 게임을 완주하는지를 잰다.' \
  --steps build/l3-abstract.steps.json --json
```

Each call prints the scenario id it created. Keep the four ids; steps 4 and 5 need them.

### 4. Set the expected pass/fail labels

```sh
artel scenario expected-labels <probe-id>       --labels scenarios/probe.labels.json
artel scenario expected-labels <l1-id>          --labels scenarios/l1-detailed.labels.json
artel scenario expected-labels <l2-id>          --labels scenarios/l2-middle.labels.json
artel scenario expected-labels <l3-id>          --labels scenarios/l3-abstract.labels.json
```

The label files need no resolution — they address steps by position, 1 through N. There is one
entry per step, in step order, and every entry is `true` except the nine that use TC 9131–9138
and 9140: probe step 9, L1 steps 5, 7, 8, 11, 12, and 14, and L3 steps 8 and 11. L2 has none.
`answer-key.md` carries the four step tables in the design document's own form, `기대` column
included, so a label can be checked against the source without opening the JSON.

### 5. Create the runs and bind the scenarios

The whole ladder, in order:

```sh
artel run create --project <project> \
  --name 'WordVenture E2E 에이전트 벤치마크' \
  --description '프로브 → L1 상세 → L2 중간 → L3 추상. 프로브의 첫 스텝이 세이브 없는 새 설치를 전제하므로 순서를 바꾸면 안 된다.' --json

artel run scenarios <run-id> --project <project> \
  --set <probe-id>,<l1-id>,<l2-id>,<l3-id>
```

`--set` takes the ids comma-separated and in run order, and it replaces the whole binding
rather than appending to it. The probe id goes first.

Then one run per rung, each bound to a single scenario:

```sh
artel run create --project <project> --name 'WordVenture 벤치마크 1 — 프로브'   --json
artel run create --project <project> --name 'WordVenture 벤치마크 2 — L1 상세'  --json
artel run create --project <project> --name 'WordVenture 벤치마크 3 — L2 중간'  --json
artel run create --project <project> --name 'WordVenture 벤치마크 4 — L3 추상'  --json

artel run scenarios <run-1-id> --project <project> --set <probe-id>
artel run scenarios <run-2-id> --project <project> --set <l1-id>
artel run scenarios <run-3-id> --project <project> --set <l2-id>
artel run scenarios <run-4-id> --project <project> --set <l3-id>
```

### Checking the result

`artel scenario show <id>` prints the steps with their `caseId` and label. Three things to
confirm: 9 / 24 / 9 / 14 steps, no step pointing at a `caseId` that does not exist, and 1 / 6 /
0 / 2 steps labelled `false`.

## Layout

```
benchmarks/
  README.md                            this file
  wordventure/
    cases.json                         35 test cases, in TC order, each tagged with its `tc`
    answer-key.md                      the four step tables and the 9 false expectations
    game-facts.md                      affinity table, damage formula, enemy roster, tutorial
    scenarios/
      probe.steps.json                 9 steps, `tc` not yet resolved
      probe.labels.json                9 labels, by step position
      l1-detailed.steps.json           24 steps
      l1-detailed.labels.json          24 labels
      l2-middle.steps.json             9 steps
      l2-middle.labels.json            9 labels
      l3-abstract.steps.json           14 steps
      l3-abstract.labels.json          14 labels
    tools/
      resolve-steps.py                 joins cases.json with the create output, resolves `tc`
    build/                             created by the build, not tracked
```
