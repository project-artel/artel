# 2026-10-13 — Game-registered cheats the QA agent can call

- Date: 2026-10-13
- Jira: Epic ARTEL-1050, Story ARTEL-1051 (phase 1), Subtasks ARTEL-1052 (sdk), ARTEL-1053
  (orchestration-server), ARTEL-1054 (agent-server), ARTEL-1055 (home).
- Pull requests: project-artel/artel-sdk#142, project-artel/artel-orchestration-server#314,
  project-artel/artel-agent-server#231, project-artel/artel-home#153.
- Status: design fixed; phase 1 in review. Wire shapes are pinned in
  [`2026-10-14-game-functions-wire-contract.md`](2026-10-14-game-functions-wire-contract.md).
- Note: this file was lost from the untracked workspace twice (2026-10-14 and 2026-10-15) and
  rewritten from the design conversation each time. Content is the final design as decided on
  2026-10-13.
- Repositories: `artel-sdk`, `artel-orchestration-server`, `artel-agent-server`, `artel-home`.
  `artel-cli` is not touched.

## Goal

A game developer registers cheat commands in the game through the SDK (give gold, set level,
unlock stage, teleport, god mode). ARTEL learns the list, and the QA agent calls a cheat to reach a
test case's precondition instead of playing up to it.

Measurable targets, on the WordVenture benchmark with cheats registered:

1. Steps reported with `SETUP-FAILED:` drop (baseline: count from a run with cheats off).
2. Tool calls spent before the first step of each test case drop.
3. Verdicts against `answer-key.md` do not get worse. A cheat must never make a wrong expectation
   pass.

## Non-goals

- Deterministic setup run before the agent starts (a test case field like
  `setup: [give_gold(1000)]`). That is phase 2 below; phase 1 only lets the agent call cheats.
- A "cheat button" a human presses in artel-home during a run. Decided on 2026-10-13: only the
  agent calls cheats.
- Cheats in release builds. They are compiled out.
- Game-semantic actions in the SDK vocabulary (`attack`, `buy_item`). ADR 0002 stays.

## Context / Constraints

- **SDK dispatch is a closed switch.** `ActionExecutor.Execute` (`Runtime/ActionExecutor.cs`)
  handles 17 methods; anything else returns `Unsupported method`. There is no registry, no public
  extension API, no capability handshake.
- **ADR 0002** (`artel-sdk/docs/adr/0002-action-vocabulary.md`) forbids game-meaning actions so
  the SDK contract does not grow per game. Generic methods whose payload names a cheat keep the
  contract fixed, but they need a new ADR that amends 0002.
- **`ArtelManager` and `ActionExecutor` are not compiled out of release builds**; only the
  auto-spawn is. A cheat registry must carry its own `#if UNITY_EDITOR || DEVELOPMENT_BUILD`, the
  way `scan_evidence` does.
- **`[ArtelState]` is removed (#132) and `[ArtelAction]` may be removed (ARTEL-429).** Do not
  build on either.
- **Method names pass through orchestration untouched.** `QaActionDispatchService` validates only
  the `ActionItemDto` shape.
- **SDK handshake carries no capabilities.** `DEVICE_CONTEXT` is sent once per connection and
  holds `sdkVersion`; orchestration does not store it.
- **The agent tool set is static per arch.** `build_tools` decides tools from `QaArchSpec` only,
  and `arch_fingerprint` hashes them at session open. Per-run tools are not possible without
  breaking that; a fixed generic tool is.
- **`ActionResultItem.returnValue` was typed `dict | None`** (`app/qa/envelope.py`), and
  `ToolContext.run` printed only `ok` / `FAILED — <error>` for non-press actions.
- **Preconditions are free text.** `_plan` puts `precondition` on a test case's first step, and
  the agent reports `SETUP-FAILED:` when it cannot reach it. This is the place cheats help.
- **Released prompt versions are locked** in `prompts-lock.json`; prompt changes go to a new
  version.
- **Per-run options follow `contentMapMode`**: a request field, validated against wire names,
  stored in `qa_try.run_config` JSONB, no migration.

## Design

### 1. SDK: attribute, generic actions, one catalog frame

A cheat is a method marked `[ArtelCheat]`. Parameters come from the method signature, so the
developer writes no parameter list by hand:

```csharp
public static class DebugCheats
{
    [ArtelCheat("Adds gold to the player's wallet.")]
    static string GiveGold([CheatRange(1, 1_000_000)] int amount)
    {
        Wallet.Add(amount);
        return $"gold={Wallet.Gold}";
    }
}

public class PlayerController : MonoBehaviour
{
    [ArtelCheat("Moves the player to a named spawn point.")]
    void Teleport(SpawnPoint to) { ... }   // enum parameter → Enum(values)
}
```

- **Discovery at compile time, no runtime reflection.** The SDK already runs IL post-processors
  (`Editor/CodeGen/ArtelILPostProcessor.cs`, `Editor/Affordance/CodeGen/AffordanceILPostProcessor.cs`).
  A new weaver in `Editor/CodeGen/` finds `[ArtelCheat]` methods and emits one generated
  registration class whose code calls each method directly. Because the generated code references
  the methods, managed stripping keeps them without `link.xml` or `[Preserve]`, and startup does
  not scan assemblies.
- **Same gate as discovery.** The weaver runs only in editor or `DEVELOPMENT_BUILD`. In a release
  build nothing is generated, the attribute stays inert, and `invoke_cheat` returns
  `Failure("cheats are not available in this build")`. The runtime registry also sits behind
  `#if UNITY_EDITOR || DEVELOPMENT_BUILD`.
- **Parameter types** from the signature: `int`, `float`, `bool`, `string`, any `enum`.
  `[CheatRange(min, max)]` and default values are optional. Any other parameter type is a compile
  error from the weaver with the method name, so a bad cheat fails the build instead of the run.
- **Return type**: `void`, `string` (becomes the result message), or `IEnumerator` for a cheat that
  waits (scene load). `ActionExecutor.Execute` is already an `IEnumerator`, so a coroutine fits.
- **Static and instance methods.**
  - A static method is always available and takes no target. A `target` sent to a static cheat is
    rejected (`give_gold is static and takes no target`).
  - An instance method on a `MonoBehaviour` runs on the object a **selector** names. The selector
    is the same Unity hierarchy path the agent already reads in the scene block and passes to
    `click` and `inspect_object` (`Root[0]/Players[2]/Player(Clone)[1]`). The SDK resolves it with
    `ScenePathSelectorResolver.TryResolve` at the moment the cheat runs, then calls
    `GetComponent<PlayerController>()` on that transform.
  - Resolution rules for an instance cheat:

    | `target` | Live instances | Result |
    |---|---|---|
    | given | — | runs on that object; `Nothing at selector: ...` or `PlayerController is not on <selector>` on failure |
    | omitted | 1 | runs on the only instance |
    | omitted | 0 | `Failure: no active PlayerController` |
    | omitted | 2 or more | `Failure: 2 PlayerController objects; pass target as one of: <selector>, <selector>` (at most 5 listed) |

    Omitting the target stays convenient for the common single-player case, and the failure with
    more than one instance hands the agent the selectors to retry with, instead of guessing.
  - Selectors are written with `ScenePath.SelectorOf`, the same function the scan and the pulse use,
    so a selector from a failure message, the scene block, or the content map all resolve the same
    way.
  - The catalog marks instance cheats with their component type
    (`"target": { "component": "PlayerController" }`), and `PULSE.functions` reports the live
    instances. This gives scene-scoped cheats without any `Register` / `Unregister` calls in game
    code.
- **Names**: `GiveGold` becomes `give_gold`. `[ArtelCheat(name: "...")]` overrides it. Duplicate
  names are a weaver error.
- **Escape hatch**: `ArtelCheats.Register(name, description, params, handler)` stays as a small
  runtime API for cheats built from data (one cheat per item ID in a table). The weaver output
  calls the same registry, so the rest of the pipeline sees one kind of cheat.
- **Do not reuse `[ArtelAction]`**: its weaver records calls but cannot invoke them, and it may be
  removed in ARTEL-429.

Protocol: `invoke_cheat` (`ACTION`), the `ACTION_RESULT` item with `returnValue.message`, and the new
`GAME_FUNCTION_CATALOG` frame. Exact shapes are in the wire contract.

- `GAME_FUNCTION_CATALOG` is sent right after `DEVICE_CONTEXT` on every connection, and again
  (debounced to one per second) whenever the set changes. `revision` increases on every change.
- The handler runs inside `try/catch`; an exception becomes `Failure(id, "invoke_cheat",
  "<ExceptionType>: <message>")` and never aborts the batch.
- New ADR (0007) amends 0002: the vocabulary gains generic methods whose meaning is supplied by the
  game at runtime; the SDK still defines no game-meaning action.

### 1b. SDK: when a cheat or behavior can be used now

Shared by cheats and behaviors. The game, not the agent, knows whether `give_gold` makes sense on
the title screen or whether `flee` makes sense outside a battle. The developer says so with `when`:

```csharp
[ArtelCheat("Adds gold to the player's wallet.", when: nameof(HasWallet))]
static string GiveGold(int amount) { ... }
static string HasWallet() => Wallet.Instance != null ? null : "no wallet loaded (title screen)";

public class PlayerController : MonoBehaviour
{
    [ArtelBehavior("Runs away from the nearest enemy.", group: "movement", when: nameof(InBattle))]
    IEnumerator Flee(ArtelBehaviorContext ctx) { ... }
    bool InBattle() => Battle.Active && hp > 0;
}
```

- `when` names a method with no parameters on the same type. It returns `bool`, or `string` where
  `null` means available and any other value is the reason it is not. A `bool` false reports
  `unavailable` with the method name as the reason (`InBattle returned false`). The weaver checks
  the name and the signature at build time.
- For an instance function the method runs on each live instance, so two players can differ.
- Availability in the game is checked in this order; the first one that says no gives the reason:
  build (release has none), target (live instance), `when`.
- **On invoke** the SDK checks all three before running the handler.
- **Continuously** the SDK evaluates every `when` once per `PULSE` (1 second) and sends only what
  changed in `PULSE.functions`, with the full set on the first `PULSE` after connect. A `when` that
  throws counts as unavailable with the exception message.
- **While a behavior runs**, its `when` is checked every `PULSE` too. When it turns false the
  behavior ends with `unavailable` and the reason.
- The agent sees the current lists in the scene block (`Cheats now: ...`, `Cheats not now: name
  (reason)`, the same for behaviors). `observe_scene` refreshes them from the latest `PULSE`.

### 1c. Test case permission: which functions a test case may use

Availability above is what the game *can* do now. Permission is what the QA author *allows* in a
given test case, and it is the place to stop a cheat from producing the value a step verifies.

- `AgentCase` (orchestration) and the agent's `QaCaseRef` gain an optional `functions` field:
  `cheats` and `behaviors`, each `"all"`, `"none"`, or a list of names. Absent means the run-level
  allowed list applies. A test case can only narrow the run list, never widen it.
- **agent-server enforces it** per test case; orchestration enforces the run-level list as the
  outer guard.
- The scene lines list only functions the current test case allows.
- **The scenario agent sets it** when it writes a test case, from the build's catalog and the
  case's `expected`. Decided on 2026-10-13: the agent decides, with no approval step. A human may
  edit it in artel-home. (Phase 1 left this out: the scenario agent writes only scenario steps and
  cannot see the catalog. Follow-up.)

Order of checks on a call, end to end:

| Order | Where | What | Example reason |
|---|---|---|---|
| 1 | build | release build | compiled out |
| 2 | SDK | live target (instance function) | `no active PlayerController` |
| 3 | SDK | `when` | `InBattle returned false` |
| 4 | orchestration | run allowed list | `cheat not allowed in this run: ...` |
| 5 | agent-server | test case `functions` | this case does not allow `give_gold` |

### 2. Orchestration: store the catalog, gate the run

- A handler for `GAME_FUNCTION_CATALOG` stores the catalog in JSONB columns on `game_build`,
  overwritten on each frame, like `scene_scan`.
- `GET /api/projects/:projectId/game-builds/:gameBuildId/game-functions` for artel-home.
- Run option `cheatMode` on `CreateQaTryRequest` / `CreateQaRunRequest`: `on` (default) or `off`,
  plus optional `allowedCheats`. Decided on 2026-10-13: default `on`, because a developer who
  registered cheats expects runs to use them without a setting.
- The default changes nothing for a build without cheats: its catalog is empty, so the session gets
  no `cheats` field and the agent gets no tool.
- **Orchestration decides the arch axis.** When the effective cheat list is not empty,
  orchestration sends `arch.cheats = "on"` in the session-open request; otherwise agent-server keeps
  its default `off` and today's fingerprint.
- Measurements set `cheatMode=off` explicitly for the baseline arm.
- `QaActionDispatchService` rejects an `invoke_cheat` whose `name` is not in the try's effective
  list. This is the server-side guard; the agent prompt is not trusted for it.

### 3. agent-server: one tool, one skill, one arch axis

- `QaArchSpec.cheats: "off" | "on"`. With `on`, `build_tools` appends `run_cheat`. Bump
  `QA_ARCH_LABEL` and update `tests/test_qa_arch.py`.
- `context.cheats` is rendered once into the first user message.
- `run_cheat` accepts a partial `target` and expands it through pulse memory; zero or several
  matches fail in the tool result. It sends `invoke_cheat` through `ctx.run`.
- `ActionResultItem.returnValue` is widened, and the tool result prints `returnValue.message`.
- `report_step` records `used_cheats` **by itself**; the model does not fill it in.
- New prompt version with `tool_run_cheat.md` and `skill_cheats.md`. The rules the skill states:
  1. Use a cheat only to reach a test case's precondition.
  2. Never use a cheat to produce the value a step verifies.
  3. After a cheat, look at the screen before the next step.
  4. Do not try a cheat listed under `not now`.
  5. If the needed cheat does not exist, play up to the precondition as today.

### 4. artel-home

- Build detail: the cheat list with name, description, parameters, and the last catalog time.
- Run start: `cheatMode` toggle and a multi-select over the build's catalog.
- Run page: `cheatMode` and the effective cheat list.
- Timeline: a badge on `invoke_cheat` rows and on steps whose `used_cheats` is not empty.
- Test case editor: the `functions` field.

## Phases

| Phase | Repository | Work |
|---|---|---|
| 1a | `artel-sdk` | attributes, weaver, `when`, `PULSE.functions`, registry, `invoke_cheat`, `GAME_FUNCTION_CATALOG`, ADR |
| 1b | `artel-orchestration-server` | catalog storage and endpoint, `cheatMode`, allowed-list guard, session-open `cheats`, test case `functions` |
| 1c | `artel-agent-server` | `cheats` arch axis, `run_cheat`, automatic `used_cheats`, test case `functions` check, scene lines, prompt version |
| 1d | `artel-home` | cheat list, run toggle, timeline badge, `functions` field |
| 1e | `benchmarks/wordventure` | register cheats in the WordVenture build, measure cheats off vs on |
| 2 | orchestration + agent | deterministic `setup` cheats written by the scenario agent, run before the case's first step |

## Phase 2 sketch: setup cheats written by the scenario agent

Decided on 2026-10-13: the scenario agent writes them, not the test case author.

- A test case gains `setup: [{ "cheat": "give_gold", "args": { "amount": 1000 } }]` next to
  `functions`. The scenario agent fills it from the catalog when the precondition names a state a
  cheat reaches.
- Saving validates `setup` against the build's catalog, and every setup cheat must also be in the
  case's `functions`.
- At run time agent-server sends the setup cheats before the case's first step, without a model
  turn. If one fails, the QA agent is told which one and reaches the precondition itself; it does
  not report `SETUP-FAILED:` just because setup failed.
- Phase 1 measurements decide whether this is worth it.

## Risks & Rollback

- **A cheat hides a real bug.** Mitigated by rule 2, the test case `functions` field, the
  automatic `used_cheats` record, and reading every run against the answer key.
- **Cheats leak into a shipped game.** Compiled out of release builds; tested.
- **The agent uses cheats everywhere.** Per-run tool call cap and the allowed list.
- **Old SDK.** It sends no catalog, so the agent gets no tool.
- **Default `on` changes runs on builds that gain a catalog.** artel-home shows `cheatMode` and the
  effective list on the run page.
- Rollback: send `cheatMode=off` per run, or flip the server default back to `off`.

## Open Questions

(none open)
