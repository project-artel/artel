# 2026-07-22 — 게임 화면 WebRTC 스트리밍

- Date: 2026-07-22
- GitHub Issue: None
- Jira: ARTEL-97 (orchestration-server), ARTEL-98 (sdk), ARTEL-99 (home)
- Status: Draft

## Goal

Let a signed-in user open a game instance in `artel-home` and watch that game's
live screen. The Unity SDK captures the composited screen and publishes it as a
WebRTC video track; the orchestration server relays signalling only (no media);
the browser renders the track. The stream exists only while a viewer holds a
lease, so a game with nobody watching pays nothing.

Build the viewer as a standalone component so the future QA screen can mount it
without change.

## Non-goals

- Recording, seeking, or replay of past frames. Live only.
- Audio.
- Viewer-to-game input (clicking on the video does nothing). Actions keep going
  through the existing `ACTION` path.
- TURN infrastructure. The game runs on a developer's own PC and the browser may
  be a **different** PC. See the connectivity note below for why STUN alone
  covers that and where it stops.
- Multi-viewer. **One viewer per instance**; the newest connection wins and the
  previous one is closed. See the decision note below.

### Connectivity: STUN yes, TURN deferred

The game runs on a developer's PC; the browser may be on a different PC.

**Same LAN works without any server.** Unity is a native app, so its ICE host
candidates are real LAN addresses. The browser dials one directly. (The reverse
direction would not work — Chrome obfuscates its own host candidates as
`*.local` mDNS names, and Unity's libwebrtc is not relied on to resolve them.
It does not matter: ICE needs one working candidate pair, and the
browser→Unity pair is it.)

**Different networks need STUN**, which supplies the server-reflexive candidate
for hole punching. That covers the large majority of NATs but not symmetric NAT
or a firewall that blocks UDP outright; those need TURN, where the entire video
stream is relayed through a server we would have to run and pay for.

Decision: ship with STUN configured, no TURN. Add coturn only when a real
failure is observed, because until then it is bandwidth cost and an extra
deployable bought against a maybe.

For development the default is Google's public STUN. That host is not a service
Google offers — it is infrastructure for their own products that happens to be
unauthenticated, with no terms, no SLA, and no notice if it changes. The
practical hazard is not an outage but rate limiting, and with no TURN to fall
back to a throttled STUN surfaces as a plain connection failure. Acceptable for
development; not something to deploy on.

For deployment, run coturn in STUN-only mode next to the orchestration server.
STUN-only is genuinely cheap — no media is relayed, so it is one stateless UDP
port answering "here is your address". It is also where TURN would later be
switched on, if the failure above ever shows up.

This makes one design detail load-bearing: `iceServers` is delivered from
server configuration inside `STREAM_START`, never compiled into the SDK. The
SDK ships to customers, so a hardcoded default would have every customer's
game phoning a third-party STUN host. Configuration keeps that a deployment
choice.

The failure mode must be legible. When ICE gives up, the UI says the game could
not be reached over the network — not a generic error — or a NAT problem gets
filed as a broken stream.

### Decision: P2P, not an SFU

Considered routing media through the server so the game encodes once and the
server fans out. The orchestration server cannot do that itself — RTP/UDP
forwarding is not a WebFlux concern — so it would mean deploying a separate
media service (LiveKit being the obvious one, which would actually *shrink* the
orchestration code to a token endpoint and would come with TURN).

Rejected for v1 because the viewer cap is 1. With a single viewer there is
nothing to fan out, and the SFU's whole benefit is fan-out. P2P costs no new
infrastructure. If concurrent viewers ever become a requirement, the move is to
LiveKit rather than a hand-rolled SFU, and the signalling layer built here is
what gets discarded — that is the accepted cost of this choice.

## Context / Constraints

Existing pieces this builds on:

- `artel-orchestration-server/src/main/kotlin/kr/artel/orchestration/sdk/` —
  WebFlux WebSocket at `/ws/sdk?instanceKey=`, `SessionManager` keyed by game
  instance id, and `SdkMessageHandler` strategies dispatched on a `type` field.
  One connection per instance is enforced; a second is refused with 4002.
- `artel-sdk/Packages/kr.artel.sdk/Runtime/ArtelManager.cs` — owns the
  transport, drains inbound messages in `Update()`, and sends text JSON.
- `artel-home/src/projects/GameInstancePanel.tsx` — instance rows. No realtime
  anywhere on this screen today; connection state is a snapshot.

Constraints:

- Unity 2022.3 (`Packages/kr.artel.sdk/package.json`). `com.unity.webrtc`
  supports 2021.3+ on Windows/macOS/Linux/iOS/Android standalone and the Editor.
  **No WebGL** — a WebGL build of a customer game cannot stream.
- Auth is the `artel_access_token` JWT cookie with `SameSite=Lax`
  (`SecurityConfig.kt:155`). That works for the viewer WebSocket handshake only
  while `artel-home` and the orchestration server stay on the same registrable
  domain (true in dev: `localhost:5173` / `localhost:8080`). Bearer-in-query is
  not introduced — it would put a credential in server logs.
- `SecurityConfig` currently `permitAll`s `/ws/sdk`. `/ws/viewer` must **not**
  be added to that list; `anyExchange().authenticated()` already covers it.
- The SDK connection is one-per-instance. The viewer connection is now also
  one-per-instance, so the whole path is a single chain: one game, one socket,
  one peer connection, one browser.

### Resolving the capture choice

Full-screen capture was chosen, which rules out the usual
`camera.CaptureStreamTrack()` path — a Camera render does not contain Screen
Space Overlay UI, which is most of what QA needs to see. The workable
combination is:

`ScreenCapture.CaptureScreenshotIntoRenderTexture(rt)` in a
`WaitForEndOfFrame` coroutine → `Graphics.Blit` with a Y-flip correction →
that RenderTexture backs a `VideoStreamTrack`.

The flip is not optional: `CaptureScreenshotIntoRenderTexture` writes in
framebuffer orientation, which is upside down under D3D relative to what the
encoder expects. Getting this wrong produces a working-but-inverted stream,
which reads as "it works" in a smoke test.

## Approach (Checklist)

### Step 0: Recon — done

Findings recorded above. Files that will change are named per step.

### Step 1: Signalling protocol (contract first)

Write `artel-orchestration-server/docs/streaming-protocol.md` before code, so
all three repos implement one agreed contract.

`streamId` identifies **one watching session**, not the instance. With a cap of
one viewer there is at most one live at a time, but it is still carried on every
message: it is what lets both ends drop signalling that belongs to a session
that has already ended. Without it, an ICE candidate arriving late from a torn
-down peer is indistinguishable from one belonging to the new peer, and it
corrupts the new negotiation.

Orchestrator → SDK (over the existing `/ws/sdk`):

| type | payload |
|---|---|
| `STREAM_START` | `streamId`, `iceServers[]`, `video:{maxWidth,maxFramerate}`, `leaseSeconds` |
| `STREAM_RENEW` | `streamId` |
| `STREAM_STOP` | `streamId` |
| `WEBRTC_ANSWER` | `streamId`, `sdp` |
| `WEBRTC_ICE` | `streamId`, `candidate` |

SDK → Orchestrator:

| type | payload |
|---|---|
| `WEBRTC_OFFER` | `streamId`, `sdp` |
| `WEBRTC_ICE` | `streamId`, `candidate` |
| `STREAM_STATE` | `streamId`, `state: CONNECTING\|LIVE\|FAILED\|STOPPED`, `error?` |

The **SDK offers**. The browser answering avoids it having to declare a
`recvonly` transceiver up front, and keeps the media direction decision on the
side that owns the source.

Browser ↔ Orchestrator (new `/ws/viewer?instanceId=`): `RENEW`, `STOP`,
`WEBRTC_ANSWER`, `WEBRTC_ICE` up; `STREAM_READY`, `WEBRTC_OFFER`,
`WEBRTC_ICE`, `STREAM_STATE`, `ERROR` down.

**Lease.** `STREAM_START` carries `leaseSeconds` (default 15). The browser sends
`RENEW` every 10s. The orchestrator forwards it as `STREAM_RENEW`. The SDK runs
its own dead-man timer per `streamId` and tears the peer down when it expires —
so the game stops capturing even if the orchestrator dies or a laptop lid
closes, not only on a clean disconnect. This is the "10초마다 계속 달라고 하면
계속 보여준다" behaviour, enforced at the source rather than trusted from above.

### Step 2: SDK — capture and publish

`artel-sdk/Packages/kr.artel.sdk/`

- `package.json`: add `com.unity.webrtc` dependency.
- `Runtime/Artel.Runtime.asmdef`: reference `Unity.WebRTC`.
- `Runtime/Streaming/ScreenVideoSource.cs` — owns one RenderTexture and the
  end-of-frame capture coroutine. Allocates on start, releases on stop.
  Applies the Y-flip blit.
- `Runtime/Streaming/ArtelStreamSession.cs` — the single `RTCPeerConnection`,
  its offer/ICE lifecycle, its `streamId`, and its lease timer. Owns the
  `ScreenVideoSource` outright: the source starts when the session starts and
  is released when it ends, so there is no state in which capture runs with no
  peer attached. That is what keeps a non-QA build free of cost.
- `Runtime/Streaming/ArtelStreamHost.cs` — holds at most one
  `ArtelStreamSession`. A `STREAM_START` arriving while one is live **replaces**
  it: tear the old peer down, then start the new one. The orchestrator does not
  send a preceding `STREAM_STOP`, so replacement is not an ordering assumption
  about two messages. Signalling whose `streamId` does not match the current
  session is dropped, and this is what makes takeover safe — the displaced
  browser's last ICE candidates are in flight while the new peer is negotiating,
  and applying them would corrupt the new negotiation. Also the single place
  that emits `STREAM_STATE`.
- `Runtime/Protocol/Dto/` — DTOs for the five message types above.
- `Runtime/ArtelManager.cs` — route the new `type` values in `HandleMessage`
  to `ArtelStreamHost`. `Update()` pumps `WebRTC.Update()` only while a session
  is live.

### Step 3: Orchestration server — signalling relay

`artel-orchestration-server/src/main/kotlin/kr/artel/orchestration/stream/`

- `config/StreamProperties.kt` — `artel.stream.ice-servers`,
  `lease-seconds`, bound from `application.yml` with a STUN default and empty
  TURN.
- `service/ViewerSessionRegistry.kt` — `instanceId → the one viewer session`,
  plus its `streamId` and lease deadline. Admitting **replaces** and returns the
  displaced session so the handler can close it; releasing is remove-if-same.

  Remove-if-same is load-bearing here, not merely prudent. A displaced session's
  `doFinally` runs *after* its replacement is already registered, so a plain
  `remove(instanceId)` would clear the live viewer's slot on its way out and
  leave a connected browser that the relay can no longer find. This is the exact
  failure `SessionManager` documents for duplicate SDK connections; the takeover
  policy makes it the normal path rather than a rare one, so it needs a test,
  not just a comment.
- `service/ViewerWebSocketHandler.kt` — reads the authenticated principal from
  `session.handshakeInfo.principal`, resolves `instanceId`, and refuses unless
  the user is a member of the owning project. Reuse the access rule in
  `GameInstanceService.requireAccessibleProject` rather than restating it —
  membership must not have two definitions. Refuses when the SDK is not
  connected (close 4404).

  When a viewer already holds the instance, the newcomer wins: the incumbent is
  closed with 4009 and told it was taken over, and the new session gets a fresh
  `streamId`. This deliberately differs from `SdkWebSocketHandler`, which
  refuses duplicate *SDK* connections — there, the incumbent is a running game
  whose session is expensive to lose. A viewer is a browser tab. The common case
  is one person reloading or reopening the page, and making them wait out a
  stale lease to see their own game is the worse failure.
- `service/StreamSignalRelay.kt` — the only component that knows both maps.
  Forwards SDP/ICE both ways by `streamId`.
- `service/handler/{WebRtcOfferHandler,WebRtcIceHandler,StreamStateHandler}.kt`
  — thin `SdkMessageHandler` implementations delegating to the relay. Three
  small classes rather than widening `SdkMessageHandler.messageType` to a set,
  which would touch the two existing handlers for no gain.
- `service/StreamLeaseReaper.kt` — `@Scheduled` sweep every 5s; an expired
  lease sends `STREAM_STOP` and closes the viewer.
- `sdk/config/WebSocketConfig.kt` — add `/ws/viewer` to the existing url map.

Frames never enter the server. If that ever changes, it is a different design.

### Step 4: Client — viewer route and reusable view

`artel-home/src/streaming/` (new module, deliberately outside `projects/`):

- `streamTypes.ts` — the signalling message union.
- `streamApi.ts` — `viewerStreamUrl(instanceId)`, built through
  `orchestrationUrlFor` with the `http`→`ws` swap.
- `useGameStream.ts` — owns the WebSocket, the `RTCPeerConnection`, the 10s
  renew ticker, and a `connecting | live | reconnecting | takenOver | offline |
  error` status. Returns `{ status, stream, retry }`.

  `takenOver` (close 4009) and `offline` (4404, game not running) are separate
  states because they need different words and different affordances. `offline`
  waits for the game and may retry on its own; `takenOver` must **not**
  auto-retry — two tabs that both reconnect on being displaced would evict each
  other forever. It ends the session and offers an explicit "다시 보기" button.
- `GameStreamView.tsx` — `<video autoPlay muted playsInline>` in a fixed
  aspect box with a status overlay. Props are `instanceId` plus an optional
  `className` and an overlay slot. **No project or route knowledge**, so the
  QA screen can mount it beside a timeline unchanged.

`artel-home/src/projects/`:

- `GameInstanceDetailPage.tsx` — new route
  `/projects/:projectId/instances/:instanceId`, renders `GameStreamView` plus
  the instance's identity and key.

  **This page is deliberately thin.** The QA screen will sit alongside it, not
  grow out of it, so design effort goes into `GameStreamView` and this page
  stays a frame around it. That is not a guess: `TestScenarioEntity` carries
  only `projectId` and the agent session sends `unity_context`/`game_context`
  as empty objects (`AgentSessionDtos.kt`), so scenarios today are an authoring
  surface with no run to watch. Whatever the QA screen turns out to be, it will
  be built on a scenario *run* that does not exist yet — which is exactly why
  this route should not pretend to be its prototype. It answers one question:
  "is the SDK actually connected and rendering".
- `GameInstancePanel.tsx` — instance name becomes a `<Link>` to that route.
- `App.tsx` — register the route inside the existing `AppShell` subtree.

Follow `.agents/docs/DESIGN.md` for tokens, states, and the disconnected /
waiting-for-game empty states.

### Step 5: Tests and manual verification

- Orchestration: unit tests for `ViewerSessionRegistry` — takeover replaces and
  returns the incumbent; **the displaced session closing afterwards does not
  clear its replacement's slot**; lease expiry. Plus the relay dropping
  signalling whose `streamId` is stale. `WebSocketClient`-driven tests that a
  viewer with no SDK connected closes 4404, and that a second viewer takes over
  while the first receives 4009.
- SDK: edit-mode tests for the lease timer, for `ArtelStreamHost` replacing a
  live session on `STREAM_START` and ignoring stale-`streamId` signalling, and
  for `ScreenVideoSource` releasing its RenderTexture when the session ends.
  WebRTC itself is not unit-testable here; cover the state machine, not the
  media.
- Client: `npm run lint` and `npm run typecheck`.
- Manual: run `samples/WordVenture`, open the instance route, confirm video
  within ~3s; close the tab and confirm the Unity console reports the peer torn
  down within `leaseSeconds`; kill the orchestration server mid-stream and
  confirm the SDK still tears down on its own timer.

### Step 6: Rollout

- `artel.stream.enabled` (default off in prod config, on in dev) gates the
  `/ws/viewer` mapping and the `STREAM_START` path. Flag off = today's
  behaviour exactly.
- The SDK ignores unknown message types already, so an old SDK against a new
  server degrades to "stream never becomes live", not a crash.

## Validation

- **Commands to run:**
  - `artel-orchestration-server`: `./mvnw test`
  - `artel-home`: `npm run lint && npm run typecheck && npm run build`
  - `artel-sdk`: Unity Test Runner (EditMode), `Artel.Runtime.Tests`
- **Expected output:** all green; manual checks in Step 5 observed, not assumed.

## Risks & Rollback

- **Risks:**
  - **NAT.** Without TURN, a viewer and a game on different networks will
    negotiate and then fail with no media. The status must say
    `연결 실패` rather than spin on `연결 중`, or this looks like a hang.
  - **No WebGL.** `com.unity.webrtc` has no WebGL backend. A customer shipping
    a WebGL build cannot use this at all; the SDK must say so at
    `STREAM_START` instead of failing silently.
  - **Y-flip.** Wrong orientation still "works", so it survives a smoke test.
    Verify against readable on-screen text, not a screenshot of a logo.
  - **Capture cost.** `CaptureScreenshotIntoRenderTexture` stalls the frame.
    Cap `maxFramerate` and confirm the game's own frame rate under stream.
  - **Takeover is silent to the taker.** Someone opening the page has no
    signal that they just cut off a colleague. With a cap of one that is
    accepted, but the displaced side must say plainly that it was taken over
    rather than showing a generic disconnect — otherwise it reads as a bug in
    the stream.
  - **Takeover loops.** Two tabs that both auto-reconnect after being displaced
    will evict each other indefinitely, burning a peer setup on the game each
    round. This is why `takenOver` is a terminal state with a manual retry.
  - **Replacement drops the picture briefly.** The new session allocates its own
    RenderTexture, so a takeover releases and re-allocates the capture target.
    Acceptable because takeover is rare; do not "optimise" it into a shared
    source without a reason, since the shared lifetime is what would let capture
    outlive its peer.
  - **SameSite.** If the client is ever served from a different registrable
    domain than the server, the handshake cookie disappears and every viewer
    connection 401s. Same-site is a deployment constraint, not an accident.
  - **Package weight.** `com.unity.webrtc` adds native plugins to every build
    that installs the SDK, including builds that never stream.
- **Rollback steps:** set `artel.stream.enabled=false` (server stops offering
  streams; SDK never starts capture). Full revert is three independent commits,
  one per repo, in any order — the feature is additive everywhere.

## Decisions taken

- **P2P, no SFU.** Reasoning in "Decision: P2P, not an SFU" above.
- **Viewer cap: 1 per instance, newest wins.** A second connection takes over
  and the incumbent is closed with 4009. Not queued, not refused.

- **ICE: STUN only, injected from server config.** Google's public STUN in
  development, coturn STUN-only on deployment. No TURN until a failure is
  observed.
- **QA screen sits alongside, not on top.** `GameInstanceDetailPage` is a thin
  frame; the design investment goes into `GameStreamView`.

## Open Questions

- None blocking. Revisit TURN when a cross-network attempt actually fails.
