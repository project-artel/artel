---
name: qa-run-local
description: >-
  Stand up the whole ARTEL stack on this machine and drive a real QA run —
  orchestration, agent-server, a Unity build with the SDK attached, a content
  map from an `evidence` scan, and `knowledge` from an uploaded document. Use
  when the task needs a QA agent to actually play a game rather than a test to
  pass: measuring agent performance across config axes, reproducing a run that
  misbehaved on stage, or checking a change end to end. Also use when the user
  says "로컬에서 QA 런 돌려줘", "agent 성능 측정", "2x2 측정", "게임 띄워서
  확인", "벤치마크 돌려줘".
---

# Local QA run

## What this gets you

A QA agent playing a real game on this machine, with every axis the measurement
needs under your control. It is the only way to answer "does the agent actually
do better with X" — unit tests answer whether X is wired, not whether it helps.

Four processes and one game:

| | Port | What breaks without it |
|---|---|---|
| PostgreSQL (`pgvector`) | 5432 | Server will not start |
| Redis | 6379 | Server starts; SDK login code path 500s |
| MinIO | 9100 | Server starts; document upload fails at the `PUT` |
| orchestration-server | 8090 public, 8091 internal | — |
| agent-server | 8000 | Run start answers 503 `upstream_unavailable` |
| The game (Unity `.exe`) | — | Run start answers 409 `sdk_disconnected` |

## The three settings that are not in `local-stack.md`

**Read this before anything else.** Each fails in a way that does not name
itself, and two of them silently produce a run that measures nothing.

```bash
# artel-orchestration-server/.env
ARTEL_AGENT_BASE_URL=http://localhost:8000/internal      # agent routes moved under /internal
ARTEL_AGENT_WS_BASE_URL=ws://localhost:8000/internal     # SEPARATE setting; HTTP alone is not enough

# artel-agent-server/.env
ORCHESTRATION_BASE_URL="http://localhost:8091"           # the INTERNAL port, not 8090
```

- Miss the first and `POST /api/qa-runs` answers **503 `upstream_unavailable`**; the
  agent-server log shows `POST /qa-sessions → 404`.
- Miss the second and the session opens (`200`) but the WebSocket handshake is
  **403** and you still get 503. Fixing only the HTTP one looks like it should
  work and does not.
- Miss the third and **the run starts fine and measures nothing.**
  `fetch_scene_context` begins with `if not root: return None`, so the
  `<<scene context>>` block never appears — a `content_map_mode=frozen` arm
  becomes byte-identical to an `off` arm. `llm_usage` also stays empty, so cost
  cannot be read. This one is the dangerous default because nothing complains.

Verify the third before spending runs:

```bash
curl -s "http://localhost:8091/internal/projects/<p>/game-builds/<b>/scene-context" \
  | python3 -m json.tool | head -20
```

## Build the game

**A build that does not carry the launch session never registers.** `artel game
start` waits 60 seconds and fails with `game_registration_timeout`, and the game
log holds no `[Artel]` line at all — nothing points at the build.

```bash
strings -a <build>/WordVenture_Data/Managed/Artel.Runtime.dll | grep -c InstallLaunchSession
```

`0` means rebuild. Both `InstallLaunchSession` and `SpawnInDevelopmentBuilds`
must be present.

Clone the SDK fresh rather than building from a checkout someone is working in:

```bash
git clone --depth 1 --branch develop https://github.com/project-artel/artel-sdk.git SdkBench
cd SdkBench && git clone https://github.com/project-artel/word-venture.git samples/WordVenture
# then check out the revision the parent records for the submodule
```

`--recurse-submodules` with `--depth 1` fails here: the shallow parent records a
revision the shallow submodule clone cannot reach.

Put `references/ArtelBenchBuild.cs` in `samples/WordVenture/Assets/Editor/`, then:

```bash
"/mnt/c/Program Files/Unity/Hub/Editor/<version>/Editor/Unity.exe" \
  -batchmode -quit -nographics \
  -projectPath "C:\path\to\samples\WordVenture" \
  -executeMethod ArtelBenchBuild.BuildWindows64 \
  -artelBuildPath "C:\path\to\Build\WordVenture.exe" \
  -logFile "C:\path\to\Build\build.log"
```

Match the editor version in `ProjectSettings/ProjectVersion.txt`. First build
rebuilds the asset database and takes minutes; later ones take about twenty
seconds.

**`BuildOptions.Development` is the point of that script.**
`ArtelManager.SpawnInDevelopmentBuilds` only attaches in a development build, so
without the flag you get a game with no SDK and the failure above.

## Running several games at once

Parallel works, and it halves wall-clock on a matrix. Two facts make it work and
one makes it fail:

- **Input is injected in-process.** The SDK uses `VirtualMouseState` and
  `ExecuteEvents.Execute`, not `SendInput`. Two games do not fight over the
  cursor.
- **`bundleVersion` unchanged means one `game_build` row.** Both slots share a
  single content map, so an arm comparison carries no build difference.
- **`productName` must differ per slot.** `sdk_uuid` (`ArtelSdkIdentity`) and the
  game's own `StagePosition` (`SaveLoadController`) both live in `PlayerPrefs`,
  which on Windows is keyed by `companyName`/`productName`. Two builds with the
  same product name **collapse into one `game_instance` and overwrite each
  other's save.** Edit `productName` in `ProjectSettings.asset`, build to a second
  directory, put it back.

One build per slot, not per arm.

### Making the slots

Flip `productName`, build, put it back. The `.bak` dance matters — leaving the
project on a changed product name means the next person's build silently lands
in a different registry key than they expect.

```bash
P=<project>/ProjectSettings/ProjectSettings.asset
for S in B C D; do
  cp "$P" "$P.bak"
  sed -i "s/^  productName: WordVenture$/  productName: WordVenture$S/" "$P"
  "<Unity.exe>" -batchmode -quit -nographics \
    -projectPath "<project>" -executeMethod ArtelBenchBuild.BuildWindows64 \
    -artelBuildPath "C:\path\BuildBench$S\WordVenture.exe" \
    -logFile "C:\path\BuildBench$S\build.log"
  mv "$P.bak" "$P"
done
```

Twenty to thirty seconds each once the Library is warm. Keep `bundleVersion`
alone so they all stay one `game_build`.

### Build one more slot than you need

**Another session on the same machine will take your game.** Two sessions that
each launch "the" build register the same `sdk_uuid`, so the second one's SDK
connection replaces the first's, and the run that was already going dies with
`ERROR {"reason": "SDK connection closed."}` and no verdict — `steps_total` and
`steps_passed` come back NULL. It reads like a crash and is not one.

That happened here on 2026-09-04: two runs ended at exactly the same wall-clock
second with no verdict, which is the signature. Identical durations across
independent runs mean something outside them ended both.

So claim slots nobody else is using rather than sharing `BuildBench` and
`BuildBenchB` by convention. Naming them for the session or the experiment costs
nothing and the collision is silent until you read the frames.

## Seeding the benchmark

`benchmarks/wordventure/` in the monorepo holds the material; its `README.md`
carries the procedure. Summary:

```bash
artel case create --project <p> --file cases.json --json > build/created-cases.json
python3 tools/resolve-steps.py --created build/created-cases.json --out build
artel scenario create --project <p> --title '...' --steps build/<name>.steps.json --json
artel scenario expected-labels <id> --labels scenarios/<name>.labels.json
artel run create --project <p> --name '...' --json
artel run scenarios <run-id> --project <p> --set <scenario-id>
```

Check the labels landed — the counts are the benchmark's own claim about itself:

```sql
SELECT s.id, jsonb_array_length(s.steps) AS steps,
       count(*) FILTER (WHERE st->>'expected_passed' = 'false') AS expect_fail
FROM test_scenario s CROSS JOIN LATERAL jsonb_array_elements(s.steps) st
WHERE s.project_id = <p> GROUP BY s.id, s.steps ORDER BY s.id;
```

L1 must be 24 steps / 6 expect-fail, L2 9 / 0, L3 14 / 2, probe 9 / 1.

## Running the arms

`artel qa matrix` (ARTEL-820) does this. Before it lands, `POST /api/qa-runs`
takes the axes directly:

```json
{"testRunId":"2","gameInstanceId":"1","label":"<experiment name>",
 "contentMapMode":"off|frozen|on","knowledgeMode":"off|frozen|learning","force":true}
```

- **Relaunch the game between arms.** A finished run leaves the game wherever it
  stopped, and the next arm's first step ("observe the title screen") then starts
  from a battle scene. That difference is not the arm.
- **`frozen`, not `on`, for measurement runs.** `on` lets the run write
  `verdict` rows into the content map and `knowledge` into the store, so a second
  run of the same arm reads what the first one left. Repetition stops being
  repetition.
- **`label` carries the experiment name only.** What the arm *is* comes from
  `run_config`; writing it in the label too puts one fact in two places.

## Reading the result — and what you cannot read

```sql
SELECT qr.id, qr.label, qt.status, qt.steps_passed || '/' || qt.steps_total,
       qt.completed_at - qt.started_at AS took, qt.run_config->>'content_map_mode',
       qt.run_config->>'knowledge_mode'
FROM qa_run qr JOIN qa_try qt ON qt.qa_run_id = qr.id ORDER BY qr.id;
```

`qa_try.status = FAILED` is a verdict, not a crash. Read the closing `STATUS`
frame in `qa_log` for what the agent said about itself.

**Do not conclude anything from the absence of text in `qa_log`.**
`MAX_LOGGED_CHARS = 4000` (`app/agents/qa/runner.py`) clips tool results
*before* they are stored, so the DB holds the same truncated copy the console
does. The `<<scene context>>` block is appended at the **end** of the view, so it
is the first thing a clip removes — a large scene's block cannot fit at all.
Counting blocks in `qa_log` and concluding the feature did not run is a mistake
this skill exists to prevent; it was made once already. The compaction ledger is
worse: it never reaches `qa_log` at all, because `_TURN_PRODUCING_NODES` skips
middleware nodes.

To check what the agent actually saw, drive `SceneMemory` directly in a probe
script — that path is not clipped.

## Record it in Notion

**A measurement nobody wrote down did not happen.** Numbers in a terminal cannot
be compared against next month's numbers, and the conditions that produced them
are gone the moment the stack comes down. Write the run up in Notion before
cleaning up.

The database index is at `.plan/notion-index/`. Use the `notion-cli` skill; the
token is in `.notion.env` at the workspace root (`set -a && . ./.notion.env && set +a`).

**Record every one of these. A result without them cannot be read later, and a
result that omits one of them can be read wrongly:**

| | Why it has to be there |
|---|---|
| Date, and who ran it | The stack moves; a number is only about the day it was taken |
| Every axis value per arm — `content_map_mode`, `knowledge_mode`, knowledge scope | This is what the arm *is*. Copy from `run_config`, not from memory |
| The axes held constant — model, `reasoning`, `prompt_version`, `agent_arch`, `agent_fingerprint` | If one of these differed between arms, the comparison is not about the axis you think |
| `git` revision of each server, and the game build's date | "Same agent" is a claim; the fingerprint and sha are what back it |
| Scenario ids and their step counts, and expect-fail counts | Proves the material was the material |
| Content map size (scenes, capabilities) and `knowledge` count | An empty map makes `on` and `off` the same run. State the number that rules that out |
| Per run: `qa_run` id, steps passed / total, wall-clock, and the agent's closing message | The message says why it stopped, which the ratio does not |
| Repetitions per cell, or that there was only one | One run per cell is not a result; say so plainly rather than letting a table imply otherwise |
| What was NOT measured | Cost when `llm_usage` is empty, honesty when the scenario has no expect-fail steps, anything the stack could not reach |

Write the prediction **before** the numbers if there is one, and say which
predictions the result contradicts. A prediction recorded after the fact
explains everything and is worth nothing.

Say plainly what the run does not prove. A local run on one machine with one
build is not stage, and one repetition is not a signal.

## Cleaning up

```bash
taskkill.exe /F /IM WordVenture.exe
docker stop artel-local-postgres artel-local-redis artel-local-minio
rm artel-orchestration-server/.env      # it is read by ./mvnw test too
```

`stop`, not `rm`, for the two documented containers — deleting them means
rebuilding the schema next time. Removing `.env` matters: `DotenvPropertySource`
injects it into the test context, and values added to run the server make
unrelated tests fail with messages that do not mention `.env`.
