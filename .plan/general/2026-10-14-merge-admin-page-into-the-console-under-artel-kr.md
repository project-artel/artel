# 2026-10-14 — Merge admin-page into the console and serve it at artel.kr/console

- Date: 2026-10-14
- GitHub Issue: None
- Status: Draft

## Goal

1. Move every admin-page screen into artel-home under `/admin/*`, shown to `ADMIN` only.
   Today the five dashboards are open to every signed-in user; after the move `USER` and
   `DEVELOPER` see none of them (decided on 2026-10-14). Retire the admin-page repository and
   its deployment afterwards.
2. Serve the console under one origin with the public site: `artel.kr/` stays the onboarding
   site, `artel.kr/console/` is artel-home (admin screens included).

## Non-goals

- Merging the onboarding code into artel-home. Onboarding and the console share the origin,
  not the build. See "Decision: one origin, two builds" below.
- Any change to server-side authorization. `/api/admin/*` already answers `DEVELOPER` with
  403 `admin_required`. The dashboard APIs (`/api/qa-stats`, `/api/llm-usage/*`,
  `/api/knowledge-stats`, `/api/projects/{id}/knowledge-graph`) stay open as they are:
  artel-home's project usage section already calls `/api/llm-usage/stats`, so restricting it
  to `ADMIN` would break that section. Hiding the screens from `USER` and `DEVELOPER` is a
  console decision, not an access boundary.
- The `DEVELOPER` grade itself. It keeps opening every project's reads in the project
  workspace (`/projects?scope=all`); it only loses the admin screens.
- Redesigning the dashboards. They move as they are, then get i18n strings.

## Decision: one origin, two builds

Onboarding and the console stay two Vite builds behind one origin, routed by path.

- Onboarding is a public page with no session. The console is 47,293 lines of TypeScript
  behind a session. One bundle would make the landing page load or code-split the console.
- Self-hosting ships the console and the admin page (`deploy/docker-compose.yml`), but never
  the onboarding site. A merged build would put the marketing pages in every self-hosted
  install, or need a build flag to strip them.
- What the user sees (one address, one login, one theme cookie) comes from the shared origin,
  not from a shared codebase.

admin-page is the opposite case and does merge into artel-home: same audience (signed-in
users), same session cookie, same `DESIGN.md` (byte-identical), same `tokens.css`
(identical apart from whitespace), and duplicated code (knowledge graph, LLM usage).

## Facts checked on 2026-10-14

### admin-page today

- No router. `App.tsx` switches seven views by state: `qa`, `usage`, `knowledge`, `graph`,
  `labels` for every signed-in user, `users` and `settings` for `ADMIN` only.
- `USER` sees the five dashboards for their own projects; `DEVELOPER` and `ADMIN` see all
  projects (`seesAllProjects`).
- No own login. Sign-in and the forced password change link to artel-home (`VITE_HOME_URL`).
- No dependencies besides React. Hard-coded Korean strings, no i18n.
- Size by directory: `qaStats` 2,973 lines, `knowledgeGraph` 3,300, `admin` 2,218,
  `llmUsage` 1,321, `knowledgeStats` 919, `expectedLabels` 707, `projects` 493.
- API calls: `/api/qa-stats`, `/api/qa-stats/labels`, `/api/qa-tries`, `/api/llm-usage/stats`,
  `/api/llm-usage/qa-runs`, `/api/knowledge-stats`, `/api/projects/{id}/knowledge-graph`,
  `/api/projects?scope=`, `/api/auth/me`, and `/api/admin/*` (users, `settings/llm`,
  `settings/bedrock`, `llm-models`, `settings/llm/invalidate-cache`).

### artel-home today

- `react-router-dom` with routes at the root: `/projects`, `/projects/:projectId/...`,
  `/account`, `/login`, `/sdk-login`.
- i18n with `LOCALES = ['en', 'ko']`, one message file per feature under `src/i18n/messages/`.
- Already has `src/knowledge/` (its own graph simulation, layout, label placement, drag) and
  `src/usage/` (reads the same `/api/llm-usage/stats`, narrowed to one project).
- `platformRole` is already parsed in `src/auth/authApi.ts`; nothing in the UI reads it yet.
- 5 absolute `src="/..."` or `href="/..."` references in `src/` and `index.html`.

### Addresses and the server

- Production: onboarding at `artel.kr` (`onboarding/src/components/SiteLayout.tsx`), the console
  at `console.artel.kr`, the admin page at `admin.artel.kr` (per the comments in each repo's
  `theme.ts`). But the CLI default console is `https://artel.kr`
  (`artel-cli/src/config.ts`) and the SDK default is `https://home.stage.artel.kr`. Which app
  answers `artel.kr/sdk-login` today must be checked before Phase 2.
- `AuthProperties.frontendOrigin` is `frontendUrl.trimEnd('/')`. It is used two ways:
  as the prefix of redirects (`/login?error=...`, `/projects?tracker=failed`, the tracker
  issue run link) and as a CORS origin in `corsAllowedOrigins`. With
  `ARTEL_HOME_URL=https://artel.kr/console`, the redirects become correct but the CORS entry
  becomes `https://artel.kr/console`, which is not an origin. The server must split the two.
- The SDK (`ArtelLoopbackLogin.cs`, `LoginPath = "/sdk-login"`) and the CLI
  (`RELAY_PATH = '/sdk-login'`) open `<console origin>/sdk-login`. Unity builds already shipped
  keep that path forever, so `/sdk-login` at the root must keep working.
- Self-host Caddy serves the console at `:80` root and the admin page at `:8090`, with
  `x-admin-url` added to `ARTEL_ALLOWED_ORIGINS`.

## Approach (Checklist)

### Phase 1 — admin-page screens into artel-home (URL stays at the root)

- [ ] **Step 0: Recon**
  - Compare `admin-page/src/knowledgeGraph` with `artel-home/src/knowledge` feature by feature
    (cross-project picker, legend, relation list, detail panel). List what the admin copy
    has that artel-home's does not.
  - Compare `admin-page/src/llmUsage` with `artel-home/src/usage`.
  - List what `USER` and `DEVELOPER` lose: every number they read on admin-page today that
    the project workspace (`usage`, `knowledge`, `qa-history`) does not show. Report the list
    before the move; the decision to hide the screens stands either way.
- [ ] **Step 1: Role gate and the shell link**
  - A `RequireAdmin` route element in artel-home wrapping `/admin/*`: renders its children
    when `platformRole === 'ADMIN'`, `NotFoundPage` otherwise (not a redirect, so the route
    does not advertise itself).
  - An admin link in the `AppShell` top bar, shown only to `ADMIN`.
- [ ] **Step 2: Routes**

  Every route is `ADMIN` only. `/admin` redirects to `/admin/qa`.

  | Route | Source in admin-page |
  | --- | --- |
  | `/admin/qa` | `qaStats` |
  | `/admin/usage` | `llmUsage` |
  | `/admin/knowledge` | `knowledgeStats` |
  | `/admin/graph` | `knowledgeGraph`, reusing `src/knowledge` |
  | `/admin/labels` | `expectedLabels` |
  | `/admin/users` | `admin/UsersView` |
  | `/admin/settings` | `admin/SettingsView` and its sections |

  The dashboards always read across every project: the `seesAllProjects` switch in
  admin-page goes away, since only `ADMIN` reaches them.
- [ ] **Step 3: Move the code**, one track per directory, with disjoint write scopes:
  `src/admin/qa`, `src/admin/usage`, `src/admin/knowledge`, `src/admin/labels`,
  `src/admin/settings` (users and settings). Each track adds its own `src/i18n/messages/<feature>.ts` with `en` and `ko`.
  The graph track merges into `src/knowledge` instead of copying `admin-page/src/knowledgeGraph`.
  `src/projects/ProjectPicker` from admin-page moves once, into a shared place, before the
  dashboard tracks start.
- [ ] **Step 4: Tests** — move the `*.test.ts` files with their modules and convert them from
  vitest to `node:test`. artel-home already has `npm test` on Node's built-in runner
  (`scripts/node-test-hooks.mjs`); its `project.md` saying "Not configured" is out of date. There is
  no DOM renderer, so the `render.test.tsx` files do not move; the pull request lists what they
  covered.
- [ ] **Step 5: Docs and deploy**
  - Change every "admin page" mention to the console path: `deploy/docker-compose.yml`
    comments, `deploy/README.md`, `artel-orchestration-server/.env.example`,
    `artel-orchestration-server/docs/platform-role.md` (the section on admin-page and
    artel-home sharing a session), `onboarding/src/pages/selfHostingCommands.ts`.
  - Remove the `:8090` Caddy site, `x-admin-url`, and the `admin-page` service from
    `deploy/docker-compose.yml`.
  - Remove `admin-page` from `.agents/scripts/label-prs.sh`.
  - Archive `project-artel/admin-page` and drop the submodule. Keep `admin.artel.kr` as a
    redirect to the console for one release.

### Phase 2 — the console at `artel.kr/console`

- [ ] **Step 0: Recon** — find which app answers `artel.kr` and `artel.kr/sdk-login` today, and
  how the two Vercel projects (onboarding, artel-home) are set up.
- [ ] **Step 1: artel-home under a base path**
  - `vite.config.ts`: `base: '/console/'`. `BrowserRouter basename="/console"`.
  - The 5 absolute asset references use `import.meta.env.BASE_URL`.
  - `App.tsx` compares `window.location.pathname === SDK_LOGIN_PATH` twice; compare against
    the basename-relative path instead.
  - `vercel.json` rewrite becomes `/console/(.*)` → `/console/index.html`.
- [ ] **Step 2: Orchestration server**
  - Split `AuthProperties.frontendOrigin` in two: the redirect base
    (`https://artel.kr/console`) and the CORS origin (scheme, host and port only, derived with
    `URI`). Add a test that `ARTEL_HOME_URL=https://artel.kr/console` yields the CORS origin
    `https://artel.kr` and the redirect `https://artel.kr/console/login?error=oauth`.
  - Remove `https://admin.artel.kr` from the default `allowed-origins` in `application.yml`
    and from `CorsAllowedOriginIntegrationTest`.
- [ ] **Step 3: The shared origin**
  - Onboarding's `vercel.json` gets an external rewrite `/console/:path*` → the artel-home
    deployment, ahead of its own SPA rewrite.
  - A redirect `/sdk-login` → `/console/sdk-login` that keeps the query string (`port`,
    `state`, `challenge`). Shipped SDK builds depend on it.
  - `console.artel.kr/*` and `admin.artel.kr/*` redirect to `artel.kr/console/*`.
- [ ] **Step 4: Self-host** — one image, one base path: Caddy serves the console under
  `/console/*`, redirects `/` and `/sdk-login` to it, and `x-public-url` becomes
  `http://localhost:8088/console`.
- [ ] **Step 5: Clients** — CLI `DEFAULT_CONSOLE_BASE_URL` becomes `https://artel.kr/console`;
  SDK `frontendOrigin` default follows. Both keep working before the update because of the
  `/sdk-login` redirect.

## Validation

- **Commands to run:**
  - artel-home: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
  - orchestration: the `AuthProperties` and CORS tests, with `-Dkotlin.compiler.daemon=false`.
- **Expected output:** all pass. Then, against a local stack with a minted session
  (`artel-jwt` skill), screen captures of:
  - a `USER` and a `DEVELOPER`: no admin link; `/admin/qa` and `/admin/users` show not found;
    the project usage section still loads.
  - an `ADMIN`: the admin link and all seven screens, including saving and checking the
    OpenRouter and Bedrock keys.
  - Phase 2: the CLI `artel login` flow end to end through `/sdk-login` at the root.

## Risks & Rollback

- **Risks:**
  - The CORS origin bug above: deploying `ARTEL_HOME_URL` with a path before the server split
    breaks every console API call.
  - A missed `/sdk-login` redirect breaks login in every shipped Unity build.
  - `DEVELOPER` users bookmarked `admin.artel.kr`; covered by the redirect.
  - `DEVELOPER` users who read the dashboards today lose them. Tell them before Phase 1 ships.
  - Bundle size: the console grows by about 11,000 lines. Lazy-load the `/admin` routes.
- **Rollback steps:**
  - Phase 1: keep the admin-page deployment running until Phase 1 is live and checked; it
    needs no change to keep working. Revert the artel-home pull requests.
  - Phase 2: restore `ARTEL_HOME_URL` to the old origin and point the domains back. The server
    split is backward compatible with a path-less URL.

## Open Questions

- Does `artel.kr` currently serve onboarding or the console? The CLI default and the onboarding
  site both claim it.
