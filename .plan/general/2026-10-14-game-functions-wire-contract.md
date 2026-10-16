# 2026-10-14 — Game functions wire contract (ARTEL-1051)

- Date: 2026-10-14
- Jira: Story ARTEL-1051 under Epic ARTEL-1050. Subtasks: ARTEL-1052 (sdk), ARTEL-1053
  (orchestration-server), ARTEL-1054 (agent-server), ARTEL-1055 (home).
- Pull requests: project-artel/artel-sdk#142, project-artel/artel-orchestration-server#314,
  project-artel/artel-agent-server#231, project-artel/artel-home#153.
- Status: fixed for phase 1. The four repositories were built in parallel against this file.
  A change to anything here is made in this file first.
- Note: this file was lost from the untracked workspace twice (2026-10-14 and 2026-10-15) and
  rewritten from the session each time.
- Design: [`2026-10-13-game-registered-cheats-for-the-qa-agent.md`](2026-10-13-game-registered-cheats-for-the-qa-agent.md)
  and [`2026-10-13-game-registered-behaviors-the-agent-runs-in-background.md`](2026-10-13-game-registered-behaviors-the-agent-runs-in-background.md).
  This file only pins the shapes those plans describe.

"Function" below means a cheat or a behavior. Keys on the SDK wire are camelCase, like the
existing `DEVICE_CONTEXT` and action params.

## 1. Catalog entry

One object per cheat or behavior. Every key is one word, so the same object travels unchanged
from the SDK through orchestration to the agent.

```json
{
  "name": "give_gold",
  "description": "Adds gold to the player's wallet.",
  "params": [
    { "name": "amount", "type": "int", "min": 1, "max": 1000000, "default": null, "values": null }
  ],
  "target": null,
  "group": null
}
```

- `type`: `"int" | "float" | "bool" | "string" | "enum"`. `values` is the list of names for
  `enum`, `null` otherwise. `min` / `max` are `null` when no `[CheatRange]` is set. `default` is
  the C# default value or `null`.
- `target`: `null` for a static method, `{ "component": "PlayerController" }` for an instance
  method on a `MonoBehaviour`.
- `group`: behaviors only; `null` for cheats and for behaviors without a group.

## 2. SDK → server frames

### `GAME_FUNCTION_CATALOG` (new)

Sent right after `DEVICE_CONTEXT` on every connection, and again, at most once per second, when
the set of functions changes (a runtime `ArtelCheats.Register` / `Unregister`).

```json
{ "type": "GAME_FUNCTION_CATALOG", "revision": 3, "cheats": [ /* entries */ ], "behaviors": [ /* entries */ ] }
```

`revision` starts at 1 per process and increases on every change. (Implementation note from
ARTEL-1052: generated registrations at startup count as changes, so the first catalog usually
carries a revision above 1.)

### `BEHAVIOR_ENDED` (new)

Sent once when a behavior ends, for any reason.

```json
{
  "type": "BEHAVIOR_ENDED",
  "behaviorId": 7,
  "name": "auto_attack",
  "target": "Root[0]/Players[2]/Player(Clone)[1]",
  "reason": "completed",
  "detail": "no enemy in range",
  "seconds": 12.4,
  "frame": 18234
}
```

`reason` is one of `stopped`, `not_allowed`, `completed`, `failed`, `timeout`, `replaced`,
`target_gone`, `unavailable`, `run_ended`. `target` is `null` for a static behavior. `detail`
may be `null`.

### `PULSE` (existing, two new top-level fields)

Orchestration relays `PULSE` verbatim (`PulseMessageHandler`), so these need no server change.

```json
"functions": {
  "whole": true,
  "entries": [
    { "kind": "cheat", "name": "give_gold", "target": null, "available": true, "reason": null },
    { "kind": "behavior", "name": "flee", "target": "Root[0]/Players[2]/Player(Clone)[1]", "available": false, "reason": "InBattle returned false" },
    { "kind": "behavior", "name": "flee", "target": "Root[0]/Players[2]/Player(Clone)[2]", "removed": true }
  ]
},
"behaviors": [
  { "behaviorId": 7, "name": "auto_attack", "target": "Root[0]/Players[2]/Player(Clone)[1]", "seconds": 12.4, "maxSeconds": 60, "report": "target=Slime(Clone)[3] hp=4" }
]
```

- `functions` is present when `whole` is true (the first `PULSE` after connect and every `PULSE`
  that is itself whole) or when any entry changed; omitted otherwise. With `whole: false` only
  changed entries are listed. An entry is keyed by `(kind, name, target)`; `removed: true` deletes
  the key (the instance is gone).
- One entry per static function, and one per live instance for an instance function. An instance
  function with no live instance has one entry with `target: null`, `available: false`,
  `reason: "no active PlayerController"`.
- `behaviors` is the full list of running behaviors, present on every `PULSE` while the registry
  has at least one behavior; `[]` when none runs.
- Neither field is sent by a release build or by an SDK without this feature.

## 3. Server → SDK actions

All four use the existing `ACTION` / `ACTION_RESULT` path. Each takes one params object.

| method | params[0] | `returnValue` on success |
|---|---|---|
| `invoke_cheat` | `{ "name": "give_gold", "args": { "amount": 500 }, "target": null }` | `{ "message": "gold=1500" }` (`message` may be `null`) |
| `start_behavior` | `{ "name": "auto_attack", "args": { "range": 8 }, "target": null, "maxSeconds": 30 }` | `{ "behaviorId": 7, "report": null }` |
| `stop_behavior` | `{ "behaviorId": 7, "reason": "stopped" }` or `{ "all": true, "reason": "stopped" }` | `{ "stopped": [7] }` |
| `extend_behavior` | `{ "behaviorId": 7, "seconds": 60 }` | `{ "maxSeconds": 90 }` |

- `target` may be omitted or `null`. `maxSeconds` defaults to 30 and must be 1 to 300.
  `stop_behavior.reason` is `"stopped"` (default) or `"not_allowed"` and becomes the
  `BEHAVIOR_ENDED.reason`. `extend_behavior` fails when the total would pass 300 seconds from
  start.
- Failures use `ActionResultDto.Failure` with these error strings (prefix exactly as written,
  the rest is free text):
  - `cheats are not available in this build` / `behaviors are not available in this build`
  - `unknown cheat: <name>` / `unknown behavior: <name>`
  - `bad argument <param>: <why>`
  - `<name> is static and takes no target`
  - `Nothing at selector: <selector>` (from `ScenePathSelectorResolver`)
  - `<Component> is not on <selector>`
  - `no active <Component>`
  - `<n> <Component> objects; pass target as one of: <s1>, <s2>` (at most 5)
  - `unavailable: <reason>` (the `when` check)
  - `too many behaviors running: <names>` (cap 4)
  - `unknown behavior id: <id>`
  - `<ExceptionType>: <message>` (a cheat handler threw)
- Orchestration's allow-list rejection (ARTEL-1053) answers with
  `cheat not allowed in this run: <name>. Allowed: <list or "none">`, outside this list; readers
  treat it as free text.

## 4. Orchestration ↔ agent-server

### Session open (`QaSessionOpenRequest`)

- `context.cheats`: list of catalog entries, already filtered by the run's allowed list. Omitted
  when the effective list is empty or `cheatMode` is `off`.
- `context.behaviors`: the same for behaviors.
- `arch.cheats = "on"` is sent only when `context.cheats` is present; `arch.behaviors = "on"`
  only when `context.behaviors` is present. Absent means agent-server's default `off`. These two
  keys merge into whatever `arch` object the request already carries.

### Test case permission

`AgentCase` (orchestration) and `QaCaseRef` (agent-server) gain an optional `functions`:

```json
"functions": { "cheats": ["give_gold"], "behaviors": "all" }
```

Each of the two keys is `"all"`, `"none"`, or a list of names; a missing key or a missing
`functions` means `"all"`. It narrows the run-level list and never widens it.

### `BEHAVIOR_ENDED` relay

Orchestration relays the SDK frame to the agent session as an envelope of type
`BEHAVIOR_ENDED` whose payload is the SDK object above minus `type`, and writes one `qa_log` row
`SDK_TO_ORCHE` for it, the same way `ACTION_RESULT` is handled.

### Step status

`report_step`'s `STATUS` frame gains two optional fields, written by agent-server, never by the
model:

```json
"used_cheats": [ { "name": "give_gold", "args": { "amount": 500 }, "target": null, "success": true } ],
"active_behaviors": [ { "behaviorId": 7, "name": "auto_attack", "target": null, "seconds": 8.0 } ]
```

Orchestration keeps both wherever it stores the step's `STATUS` payload, and returns them on the
step result that artel-home reads, under the same snake_case names.

## 5. Orchestration ↔ artel-home

### Catalog

`GET /api/projects/:projectId/game-builds/:gameBuildId/game-functions`

```json
{ "revision": 3, "receivedAt": "2026-10-14T08:00:00Z", "cheats": [ /* entries */ ], "behaviors": [ /* entries */ ] }
```

A build that never sent a catalog answers `200` with `revision: 0`, `receivedAt: null` and two
empty lists.

### Run options

`CreateQaRunRequest` and `CreateQaTryRequest` gain:

| field | values | default |
|---|---|---|
| `cheatMode` | `"on"`, `"off"` | `"on"` |
| `behaviorMode` | `"on"`, `"off"` | `"on"` |
| `allowedCheats` | list of names or `null` | `null` (all in the catalog) |
| `allowedBehaviors` | list of names or `null` | `null` |

Stored in `qa_try.run_config` as `cheat_mode`, `behavior_mode`, `allowed_cheats`,
`allowed_behaviors`. The QA try detail response that already carries the try's run options adds
`cheatMode`, `behaviorMode`, `allowedCheats`, `allowedBehaviors`, plus `effectiveCheats` and
`effectiveBehaviors` (the names actually sent to the agent).

### Test case `functions`

The test case read and write API carries `functions` in the shape of section 4. Orchestration
passes it into `AgentCase.functions`.

### Timeline

No new endpoint. `invoke_cheat`, `start_behavior`, `stop_behavior` and `extend_behavior` appear as
the existing `ACTION` log rows, and `BEHAVIOR_ENDED` as its own log row type.
