# 2026-10-13 — Game-registered behaviors the QA agent starts and stops

- Date: 2026-10-13
- Jira: Epic ARTEL-1050, Story ARTEL-1051 (phase 1, together with cheats).
- Status: design fixed; phase 1 in review. Wire shapes are pinned in
  [`2026-10-14-game-functions-wire-contract.md`](2026-10-14-game-functions-wire-contract.md).
- Note: this file was lost from the untracked workspace twice (2026-10-14 and 2026-10-15) and
  rewritten from the design conversation each time.
- Depends on: [`2026-10-13-game-registered-cheats-for-the-qa-agent.md`](2026-10-13-game-registered-cheats-for-the-qa-agent.md)
  — attribute discovery, selector `target` rules, availability (section 1b), test case permission
  (section 1c), the catalog frame, the allowed list and the arch axis.

## Goal

A game developer writes a **behavior**, a routine that keeps running in the game every frame until
it is stopped: keep attacking the nearest enemy, run away from enemies, keep the character at full
health, strafe left and right. The QA agent starts a behavior with one tool call, keeps thinking
and observing while the behavior plays, and stops it or lets it end by itself.

Why: game time keeps running while the agent thinks (it stops only on `pause_game_time`), and the
agent can send only one batch of inputs per turn. In a real-time fight the character stands still
between turns. A behavior hands the per-frame part to game code and keeps the decisions with the
agent.

Measurable targets on a real-time scene: test cases that need sustained input reach a verdict
instead of `SETUP-FAILED:` or a timeout, and verdicts against the answer key do not get worse.

## How it differs from a cheat and from a macro

| | Cheat | Behavior | Macro (ARTEL-914) |
|---|---|---|---|
| Written by | game developer, in C# | game developer, in C# | QA agent, at run time |
| Runs | once, returns | every frame until stopped | finite input sequence |
| Where | in the game | in the game | agent-server sends batches |
| Agent turn | waits for the result | returns at once, game keeps going | waits for the sequence |
| Plays by game rules | no, it changes state directly | yes, it calls the code the player's input calls | yes, through input |

## Non-goals

- Behaviors written by the agent or in a script language.
- Behaviors that change state the player cannot reach (that is a cheat).
- Generic SDK behaviors that need no game code — phase 2.
- Release builds.
- Changing a running behavior's arguments. Decided on 2026-10-13: the agent stops it and starts it
  again; `group` replacement makes that one call.
- A human starting a behavior from artel-home.

## Design

### 1. SDK: writing a behavior

```csharp
public class PlayerController : MonoBehaviour
{
    [ArtelBehavior("Attacks the nearest enemy until none are in range.", group: "combat")]
    IEnumerator AutoAttack([CheatRange(1, 20)] float range, ArtelBehaviorContext ctx)
    {
        try
        {
            while (true)
            {
                var enemy = Enemies.Nearest(transform.position, range);
                if (enemy == null) { ctx.Complete("no enemy in range"); yield break; }
                Attack(enemy);                       // the same method the attack button calls
                ctx.Report($"target={enemy.name} hp={enemy.Hp}");
                yield return null;                   // next frame
            }
        }
        finally { StopAttackAnimation(); }          // runs on stop, timeout, scene change
    }
}
```

- Discovery, parameters, names, static versus instance, `target` and `when` are the same as for
  cheats. `ArtelBehaviorContext` is an optional last parameter, not shown to the agent.
- `ctx.Report(text)` sets the line the agent sees (at most 200 characters). `ctx.Complete` and
  `ctx.Fail` end it with a reason.
- **The SDK drives the iterator itself** with `MoveNext()` and calls `Dispose()`, so `finally` runs
  on every end. `StopCoroutine` would not run it.
- `yield return null` and `WaitForSeconds` are supported. An exception ends the behavior with
  `failed`.

### 2. SDK: lifecycle

| Ends because | Reason sent | Who triggers it |
|---|---|---|
| the agent stops it | `stopped` | `stop_behavior` |
| the next test case's `functions` does not allow it | `not_allowed` | agent-server sends `stop_behavior` |
| the method finished or called `ctx.Complete` | `completed` + reason | game code |
| `ctx.Fail` or an exception | `failed` + reason | game code |
| `max_seconds` passed (required, default 30, cap 300) | `timeout` | SDK |
| another behavior in the same `group` started | `replaced` | SDK |
| its instance was destroyed or its scene unloaded | `target_gone` | SDK |
| its `when` turned false | `unavailable` + reason | SDK |
| `reset_game`, run end, socket closed | `run_ended` | SDK |

- `group` makes behaviors exclusive; no group means no replacement.
- At most 4 behaviors at once.
- The timeout is required. `extend_behavior(id, seconds)` extends it up to 300 seconds from start;
  whether 300 is enough across test cases is measured in phase 1e first.
- A behavior advances with game time, so `pause_time` freezes it.

### 3. Protocol

`start_behavior`, `stop_behavior`, `extend_behavior` (`ACTION`), `PULSE.behaviors`, and the new
`BEHAVIOR_ENDED` frame. Exact shapes are in the wire contract. `start_behavior` returns after the
first `MoveNext()`, so the agent's turn is not held.

### 4. Orchestration

- `BEHAVIOR_ENDED`: one `qa_log` row and a relay to the agent session.
- Behaviors share the catalog column with cheats.
- Run option `behaviorMode` (`on` default, decided on 2026-10-13) and `allowedBehaviors`, separate
  from `cheatMode` so the two can be measured apart. The dispatch guard rejects a disallowed
  `start_behavior`.
- `arch.behaviors = "on"` is sent only when the effective list is not empty.

### 5. agent-server

- Tools when the axis is on: `start_behavior`, `stop_behavior`, `extend_behavior`.
- `BEHAVIOR_ENDED` is appended to the next tool result.
- The scene block shows one line per running behavior from `PULSE`.
- **Steps and test cases.** Decided on 2026-10-13: a behavior runs across steps and across test
  cases. agent-server stops it at a test case boundary only when the next test case's `functions`
  does not allow it (`not_allowed`). Between scenarios `reset_game` ends every behavior.
- `report_step` lists still-running behaviors, and records `active_behaviors` by itself.
- `skill_behaviors.md` rules: use behaviors for per-frame input and keep the decisions; keep
  observing; never use one for a step that verifies the controls themselves; a behavior left over
  from the previous test case is part of this case's starting state; do not start one listed under
  `not now`.

### 6. artel-home

- Build detail lists behaviors with group and parameters.
- Run start: `behaviorMode` toggle and allowed list.
- Run timeline: one lane per behavior, a bar from start to end coloured by end reason.

## Phases

| Phase | Repository | Work |
|---|---|---|
| 1a | `artel-sdk` | `[ArtelBehavior]`, iterator runner, lifecycle, `PULSE.behaviors`, `BEHAVIOR_ENDED` |
| 1b | `artel-orchestration-server` | `BEHAVIOR_ENDED` handler, `behaviorMode`, allowed guard |
| 1c | `artel-agent-server` | three tools, end events, scene lines, `not_allowed` stop, `active_behaviors` |
| 1d | `artel-home` | catalog list, run toggle, behavior lanes |
| 1e | benchmark | a real-time scene, `behaviorMode` off vs on |
| 2 | `artel-sdk` | generic behaviors without game code |

## Risks & Rollback

- **A behavior hides an input bug** — skill rule, test case `functions`, `active_behaviors`.
- **A runaway behavior** — bounded by `max_seconds`, `not_allowed`, `unavailable`, `run_ended`.
- **Developer cleanup missing** — the SDK runs `finally`; documentation shows `try/finally`.
- **Frame cost** — at most 4 `MoveNext()` per frame plus game code.
- **Default `on`** — the run page shows `behaviorMode` and the effective list.
- Rollback: `behaviorMode=off` per run, or flip the server default.

## Open Questions

1. Phase 2 generic behaviors: which two or three do real-time test cases need first?
