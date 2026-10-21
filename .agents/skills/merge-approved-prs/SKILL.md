---
name: merge-approved-prs
description: Merge approved GitHub pull requests, resolving CI failures and merge conflicts while preserving review approval and repository protections. Use when asked to merge approved PRs or keep monitoring them for merge readiness.
---

# Merge Approved PRs

Complete the user's authorized merge workflow. Use the specified repository or organization; for this user's ARTEL workflow, the organization is `project-artel`. Do not broaden other requests to that organization automatically.

## Scope and authorization

- A request to merge approved PRs authorizes necessary branch updates, focused CI fixes, conflict resolution, tests, pushes, and policy-compliant merges within that scope. Carry forward authorization already given; do not ask again for routine steps.
- Loading this skill for a status question does not itself authorize merges. Establish authorization from the user's request before mutations.
- Read each repository's `AGENTS.md` and referenced workflow instructions. Preserve existing local edits using a clean worktree or isolated clone. Never reset or force-push over someone else's work.
- Do not approve PRs yourself to make them eligible, bypass protections, disable checks, fabricate statuses, or weaken tests to obtain a green result.
- Do not send review requests, comments, or other messages to people unless explicitly authorized. Report needed human action in the current chat.

## Discover candidates and dependencies

1. Discover open, non-draft PRs with current approval. GitHub search `review:approved` is a candidate list, not the final gate; paginate rather than silently truncating results.
2. Read each candidate's current head SHA, base, effective reviews, aggregate review decision, check runs and commit statuses, mergeability, and applicable rules. A historical APPROVED event does not override a later dismissal or change request. If review state is ambiguous, leave it unmerged.
3. Inspect PR bodies and branch/stack relationships for dependencies, including cross-repository dependencies. Merge prerequisites first. Do not merge an unapproved dependency as a side effect of a stack merge.
4. Attach PRs being worked on to the current task when the app supports it. Track the repository, PR, head SHA, approval, CI result, dependency, and remaining blocker.

## Repair and verify

- For failed CI, inspect the failing job and relevant logs before editing. Distinguish code defects, infrastructure failures, flaky tests, queued builds, and missing status delivery. Rerun only when evidence supports a transient failure; do not retry the same failure indefinitely.
- Fix only what is necessary for the approved change to integrate. Preserve intended behavior from both sides of conflicts; inspect nearby code and callers rather than choosing all of one side.
- Fetch the current base. Use the provider's branch-update operation when supported, with the expected head SHA. Otherwise merge the base into an isolated checkout and push normally to the existing PR branch.
- Run repository-required checks and targeted tests appropriate to the change. Report actual coverage; a pipeline compiling tests with `-DskipTests` is not evidence that the full suite ran.
- After every push, refetch approval and statuses for the new head. If approval was dismissed or changes are requested, wait for reapproval. Do not treat old-head CI as validation of a new commit.
- Pending or missing required checks are not success. A skipped or neutral check is acceptable only when repository rules explicitly accept it and required validation is still satisfied.

### Missing Jenkins results

When relevant, trace GitHub delivery -> proxy -> Jenkins webhook -> branch indexing -> queue/executor -> build -> GitHub status publication. Check delivery method, response codes, event logs, credential permissions, and the SHA associated with each status.

An ARTEL incident in October 2026 involved HTTP-to-HTTPS 301 redirects turning webhook POSTs into GETs, followed by Jenkins 405 responses. Treat this as a diagnostic lead, not a permanent explanation. Prefer a canonical HTTPS webhook URL when authorized; if a redirect is required, verify method-preserving behavior. Confirm a real delivery, triggered build, and status on the current SHA after a fix.

Infrastructure changes need user authorization covering that scope; ordinary PR merge authorization alone does not authorize arbitrary proxy or Jenkins configuration changes. Use existing authenticated access, avoid exposing credentials, preserve a rollback copy, and verify the affected service after an authorized fix. Ask for a login method or credential-file path when access is missing, not a password pasted into chat.

## Merge gate

Immediately before each merge, refetch and require all of:

- PR remains open, non-draft, and approved under current review requirements.
- Expected head SHA matches the head whose checks were verified.
- Required CI has completed successfully for that head, and no relevant failing validation remains unexplained.
- Conflicts are resolved and base freshness, dependencies, and all repository rules are satisfied.

Use a repository-permitted merge method and pass the expected head SHA (`expected_head_sha`, REST `sha`, or CLI `--match-head-commit`). Never use admin/bypass options. If the head changed or GitHub rejects the gate, refresh and resolve the actual blocker; do not retry without the SHA guard.

Prefer an available GitHub connector. Use CLI/API fallback when the connector lacks the needed capability. Some stacked PRs reject the ordinary synchronous merge endpoint. Discover and verify the provider's currently supported stack/async operation before using it; include the expected SHA, disable rule bypass, inspect every PR it will merge, and poll the operation to completion. A queued or pending response is not a completed merge.

Confirm the merged state and resulting commit. After each merge, refresh remaining PRs: base changes can invalidate freshness or CI. Update and validate again as needed, preferably just in time to avoid needless rebuilds.

## Monitoring and reporting

- For a one-shot request, finish currently actionable work and report remaining blockers.
- For an explicit request to keep watching, use the app's automation tools. Reuse a matching automation instead of duplicating it; retain the authorized scope, merge gates, and quiet-notification preference. Do not schedule monitoring merely because this skill was loaded.
- On a recurring run, process actionable candidates, then yield while builds or reviews are pending. Notify only for completed merges, meaningful failures, or required user action; stay quiet for unchanged queued/running/healthy states. Follow the runtime heartbeat response format when provided.
- State merged PR links and any concrete blockers concisely in the user's language. Separate CI pending, reapproval needed, and access/configuration blockers. Do not promise background work unless an automation is active.
- Stop attempting a candidate when it needs new human approval, unavailable access, a substantive product decision, or repeated failure without new evidence. Continue independent candidates. End monitoring when the user cancels it or its requested finite scope is complete; ongoing organization monitoring stays active until canceled or obsolete.