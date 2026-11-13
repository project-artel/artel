# Pull Request Completion

Run the repository's relevant local checks, push the changes, and open or update the PR.
For every affected repository, watch the required CI checks on the latest PR head
until they pass. Recheck the head after each push.

If a check fails, inspect the failing job and its logs. Fix failures within scope,
push the fix, and watch the new run. Retry transient infrastructure failures when
possible. If an external blocker prevents progress, report the failing or missing
check, link to the run when available, and state what remains unverified.

Opening a draft or passing local checks does not satisfy the CI requirement.
